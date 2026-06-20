"""LLM-backed justification writer for the Scoring Agent.

The agent computes the *numbers* deterministically; this component asks Claude to
turn each numeric :class:`ToolResult` into an audit-quality, human-readable
justification in one structured call. It reuses the platform's resilience stack
(timeout → retry → circuit breaker) and degrades gracefully: if the LLM is disabled
or unavailable, the agent falls back to each tool's deterministic
``default_justification``.
"""

from __future__ import annotations

import json
import logging

from pydantic import BaseModel, Field

from services.common.config import Settings, get_settings
from services.common.exceptions import CircuitOpenError
from services.common.observability import MetricsSink, get_metrics, track
from services.common.resilience import AsyncCircuitBreaker, retry_call, with_timeout
from services.scoring_agent.contracts import DiagnosticAnswersView, ToolResult

logger = logging.getLogger(__name__)


class _JustificationItem(BaseModel):
    key: str = Field(description="The score key this justification is for.")
    justification: str = Field(description="2-4 sentence audit-minded rationale.")


class _JustificationBundle(BaseModel):
    items: list[_JustificationItem] = Field(default_factory=list)


class JustificationWriter:
    """Produces per-score justifications via one structured Claude call."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        metrics: MetricsSink | None = None,
        circuit_breaker: AsyncCircuitBreaker | None = None,
    ) -> None:
        cfg = settings or get_settings()
        self._enabled = cfg.llm.enabled
        self._model = cfg.llm.model
        self._max_tokens = cfg.llm.max_tokens
        self._timeout = cfg.llm.timeout_seconds
        self._max_retries = cfg.llm.max_retries
        self._metrics = metrics or get_metrics()
        self._breaker = circuit_breaker or AsyncCircuitBreaker(
            failure_threshold=cfg.resilience.circuit_failure_threshold,
            reset_seconds=cfg.resilience.circuit_reset_seconds,
            name="scoring-justifier",
        )
        self._client = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _get_client(self):
        if self._client is None:
            from anthropic import AsyncAnthropic  # lazy, optional dependency

            self._client = AsyncAnthropic()
        return self._client

    async def write(
        self, results: list[ToolResult], view: DiagnosticAnswersView
    ) -> dict[str, str]:
        """Return ``{score_key: justification}``; empty dict means "use defaults"."""
        if not self._enabled or not results:
            return {}
        try:
            client = self._get_client()
        except Exception:  # noqa: BLE001 - SDK / credentials absent
            logger.info("Justifier LLM unavailable; using deterministic justifications.")
            return {}

        system = (
            "You are an ESG and regulatory-compliance analyst writing the rationale "
            "behind a set of pre-computed maturity scores. Do NOT change any score. "
            "For each score, write 2-4 sentences that explain the number using the "
            "provided drivers and inputs, in a precise, audit-minded tone."
        )
        payload = {
            "overall_diagnostic": {
                "coverage": view.coverage,
                "overall_gap": view.overall_gap,
            },
            "scores": [
                {
                    "key": r.key,
                    "label": r.label,
                    "score": r.score,
                    "confidence": r.confidence,
                    "drivers": r.drivers,
                    "inputs": r.inputs,
                }
                for r in results
            ],
        }
        user = (
            "Write one justification per score key and return the structured schema.\n\n"
            + json.dumps(payload, indent=2)
        )

        async def _invoke() -> _JustificationBundle | None:
            response = await with_timeout(
                client.messages.parse(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    thinking={"type": "adaptive"},
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    output_format=_JustificationBundle,
                ),
                self._timeout,
            )
            return getattr(response, "parsed_output", None)

        try:
            with track("scoring.justify"):
                bundle = await self._breaker.call(
                    retry_call, _invoke, attempts=self._max_retries + 1, base_delay=0.5
                )
        except CircuitOpenError:
            self._metrics.increment("scoring.justify.circuit_open")
            return {}
        except Exception as exc:  # noqa: BLE001 - degrade gracefully
            self._metrics.increment("scoring.justify.errors")
            logger.warning("Justification generation failed: %s", exc)
            return {}

        if bundle is None:
            return {}
        self._metrics.increment("scoring.justify.success")
        valid_keys = {r.key for r in results}
        return {
            item.key: item.justification
            for item in bundle.items
            if item.key in valid_keys and item.justification.strip()
        }
