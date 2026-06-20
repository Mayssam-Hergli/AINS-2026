"""MS2 Scoring Agent — orchestration.

Implements the team workflow step that sits between MS1 and MS3:

    read project_profiles.diagnostic_answers (MS1)
        → run the 5 scoring tools (deterministic numbers)
        → write justifications (LLM, with deterministic fallback)
        → assemble 5 score objects
        → write project_profiles.scores (for MS3)

The agent reads the shared DB contract — it never calls the MS1 agent directly — so it
works whether MS1 is an LLM agent or a plain service, as long as the
``diagnostic_answers`` contract is honoured.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from services.common.config import Settings, get_settings
from services.common.exceptions import DiagnosticNotReadyError
from services.common.observability import (
    MetricsSink,
    bind_correlation_id,
    get_metrics,
    track,
)
from services.scoring_agent.contracts import (
    SCORES_SCHEMA_VERSION,
    DiagnosticAnswersView,
    ScoreObject,
    ScoreSet,
    ToolResult,
)
from services.scoring_agent.justifier import JustificationWriter
from services.scoring_agent.repository import ScoreRepository
from services.scoring_agent.tools import ScoringContext, ScoringTool, band_for, default_tools

logger = logging.getLogger(__name__)


class ScoringAgent:
    """Reads MS1's diagnostic, scores it across five tools, writes scores for MS3."""

    def __init__(
        self,
        *,
        repository: ScoreRepository | None = None,
        tools: list[ScoringTool] | None = None,
        justifier: JustificationWriter | None = None,
        settings: Settings | None = None,
        metrics: MetricsSink | None = None,
    ) -> None:
        self._repository = repository
        self._tools = tools or default_tools()
        self._justifier = justifier
        self._settings = settings or get_settings()
        self._metrics = metrics or get_metrics()

    async def score_project(
        self,
        *,
        project_id: uuid.UUID,
        tenant_id: uuid.UUID | None = None,
        persist: bool = True,
        diagnostic_answers: dict | None = None,
        correlation_id: str | None = None,
    ) -> ScoreSet:
        """Score one project. Provide ``diagnostic_answers`` to bypass the DB read."""
        with bind_correlation_id(correlation_id), track("scoring.score_project"):
            raw = diagnostic_answers
            if raw is None:
                if self._repository is None:
                    raise RuntimeError("score_project needs a repository or diagnostic_answers")
                raw = await self._repository.read_diagnostic_answers(project_id)
            if raw is None:
                self._metrics.increment("scoring.diagnostic_not_ready")
                raise DiagnosticNotReadyError(
                    f"diagnostic_answers not available for project {project_id}"
                )

            view = DiagnosticAnswersView.from_raw(raw)
            results = self._run_tools(view)
            justifications = await self._justify(results, view)
            score_set = self._assemble(project_id, view, results, justifications)

            if persist:
                if self._repository is None:
                    raise RuntimeError("persist=True requires a ScoreRepository")
                await self._repository.write_scores(
                    project_id, score_set, tenant_id=tenant_id
                )
                logger.info(
                    "Wrote %d scores for project %s (overall %.0f, %s)",
                    len(score_set.scores), project_id,
                    score_set.overall_score, score_set.method,
                )

            self._metrics.increment(
                "scoring.completed", band=score_set.overall_band.value, method=score_set.method
            )
            return score_set

    def _run_tools(self, view: DiagnosticAnswersView) -> list[ToolResult]:
        ctx = ScoringContext(view=view, config=self._settings.scoring)
        prior: dict[str, ToolResult] = {}
        results: list[ToolResult] = []
        for tool in self._tools:
            result = tool.score(ctx, prior)
            prior[result.key] = result
            results.append(result)
        return results

    async def _justify(
        self, results: list[ToolResult], view: DiagnosticAnswersView
    ) -> dict[str, str]:
        if self._justifier is None or not self._justifier.enabled:
            return {}
        return await self._justifier.write(results, view)

    def _assemble(
        self,
        project_id: uuid.UUID,
        view: DiagnosticAnswersView,
        results: list[ToolResult],
        justifications: dict[str, str],
    ) -> ScoreSet:
        cfg = self._settings.scoring
        now = datetime.now(timezone.utc).isoformat()
        score_objects = [
            ScoreObject(
                key=r.key,
                label=r.label,
                score=r.score,
                band=band_for(r.score, cfg),
                confidence=r.confidence,
                justification=justifications.get(r.key) or r.default_justification,
                drivers=r.drivers,
                evidence_refs=r.evidence_refs,
                inputs=r.inputs,
                tool=r.tool,
                computed_at=now,
            )
            for r in results
        ]
        overall = next((s for s in score_objects if s.key == "overall"), score_objects[-1])
        method = "rule+llm" if justifications else "rule"

        return ScoreSet(
            schema_version=SCORES_SCHEMA_VERSION,
            project_id=str(project_id),
            generated_at=now,
            method=method,
            diagnostic_schema_version=view.schema_version,
            overall_score=overall.score,
            overall_band=overall.band,
            scores=score_objects,
        )
