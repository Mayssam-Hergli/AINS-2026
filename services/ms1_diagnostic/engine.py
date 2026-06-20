"""MS1 Diagnostic Engine — maturity classifier (Rule Engine + Structured LLM).

This is the top of the MS1 stack. It composes the question graph, the gap detector,
and the blocker ranker, then classifies overall maturity with a two-layer approach:

1. **Rule engine** — a deterministic, fully auditable classifier anchored on the
   *evidenced* (reality) scores, tempered by questionnaire coverage and penalised
   for overclaims. This is the source of truth for the numeric maturity level, which
   matters for a compliance product where every score must be explainable.
2. **Structured LLM** — Claude (``claude-opus-4-8``) produces a schema-validated
   second opinion: a narrative, key risks, and recommended actions. It enriches the
   result and acts as a divergence check, but never silently overrides the rule
   engine. The LLM layer degrades gracefully — if it is unavailable, the diagnostic
   still completes on the rule engine alone.

The final result is serialised into the shared **PostgreSQL data contract**: the
``diagnostic_answers`` JSONB column of the ``project_profiles`` table, which MS2
reads downstream.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from enum import IntEnum

from pydantic import BaseModel, Field

from services.common.config import Settings, get_settings
from services.common.exceptions import (
    AnswerValidationError,
    CircuitOpenError,
    PersistenceError,
)
from services.common.observability import (
    MetricsSink,
    bind_correlation_id,
    get_metrics,
    track,
)
from services.common.resilience import (
    AsyncCircuitBreaker,
    retry_call,
    with_timeout,
)
from services.file_parser.normalizer import ExtractedSignal, SignalDomain
from services.ms1_diagnostic.blocker_ranker import Blocker, BlockerRanker
from services.ms1_diagnostic.gap_detector import (
    GapDetector,
    GapDirection,
    GapReport,
)
from services.ms1_diagnostic.questions import QuestionGraph, build_default_graph

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "ms1.diagnostic.v1"
_LLM_MODEL = "claude-opus-4-8"


class MaturityLevel(IntEnum):
    """Five-stage capability maturity scale."""

    INITIAL = 1
    DEVELOPING = 2
    DEFINED = 3
    MANAGED = 4
    OPTIMIZED = 5

    @property
    def label(self) -> str:
        return self.name.title()

    @classmethod
    def from_score(cls, score: float) -> "MaturityLevel":
        if score < 0.2:
            return cls.INITIAL
        if score < 0.4:
            return cls.DEVELOPING
        if score < 0.6:
            return cls.DEFINED
        if score < 0.8:
            return cls.MANAGED
        return cls.OPTIMIZED


# ---------------------------------------------------------------------------
# Result contract (serialised to project_profiles.diagnostic_answers)
# ---------------------------------------------------------------------------

class OverallMaturity(BaseModel):
    maturity_level: int = Field(ge=1, le=5)
    maturity_label: str
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


class DomainMaturity(BaseModel):
    domain: SignalDomain
    maturity_level: int = Field(ge=1, le=5)
    maturity_label: str
    perceived_score: float
    evidenced_score: float
    gap: float
    direction: GapDirection


class LLMAssessment(BaseModel):
    """Schema the structured LLM call is constrained to return."""

    maturity_level: int = Field(ge=1, le=5, description="LLM's independent 1-5 rating.")
    maturity_label: str = Field(description="Human label for the level.")
    confidence: float = Field(ge=0.0, le=1.0)
    key_risks: list[str] = Field(default_factory=list, description="Top compliance risks.")
    recommended_actions: list[str] = Field(default_factory=list)
    narrative: str = Field(description="Concise executive summary of the posture.")


class DiagnosticAnswers(BaseModel):
    """The full MS1 output written to ``project_profiles.diagnostic_answers``."""

    schema_version: str = SCHEMA_VERSION
    project_id: str
    generated_at: str
    method: str
    overall: OverallMaturity
    domains: list[DomainMaturity]
    gap_report: GapReport
    blockers: list[Blocker]
    questionnaire: dict[str, object]
    evidence: dict[str, object]
    llm_assessment: LLMAssessment | None = None
    divergence_note: str | None = None


# ---------------------------------------------------------------------------
# Rule engine
# ---------------------------------------------------------------------------

class RuleAssessment(BaseModel):
    score: float
    level: MaturityLevel
    confidence: float
    rationale: str


class RuleEngine:
    """Deterministic maturity classifier anchored on evidenced reality."""

    def classify(self, *, gap_report: GapReport, coverage: float) -> RuleAssessment:
        evidenced = gap_report.overall_evidenced
        overclaim_penalty = sum(
            max(g.gap, 0.0) for g in gap_report.domain_gaps
        ) / max(len(gap_report.domain_gaps), 1)

        # Reality is the anchor; unbacked confidence drags the score down.
        score = max(0.0, evidenced - 0.5 * overclaim_penalty)
        level = MaturityLevel.from_score(score)

        # Confidence rises with questionnaire coverage and the amount of evidence,
        # and falls when perception and reality disagree.
        alignment = 1.0 - min(abs(gap_report.overall_gap), 1.0)
        confidence = round(
            max(0.1, min(0.35 + 0.4 * coverage + 0.25 * alignment, 1.0)), 3
        )

        rationale = (
            f"Evidenced maturity {evidenced:.2f} anchors the score; overclaim penalty "
            f"{overclaim_penalty:.2f} applied across {len(gap_report.domain_gaps)} domains. "
            f"Questionnaire coverage {coverage:.0%}, perception/evidence alignment "
            f"{alignment:.0%}."
        )
        return RuleAssessment(
            score=round(score, 4), level=level, confidence=confidence, rationale=rationale
        )


# ---------------------------------------------------------------------------
# Structured LLM classifier
# ---------------------------------------------------------------------------

class LLMMaturityClassifier:
    """Wraps an async Claude call that returns a schema-validated assessment.

    The client is created lazily and the whole call is defensive: any failure
    (missing SDK, no API key, transport error, refusal) returns ``None`` so the
    engine falls back to the rule engine without interrupting the diagnostic.
    """

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        metrics: MetricsSink | None = None,
        circuit_breaker: AsyncCircuitBreaker | None = None,
    ) -> None:
        cfg = (settings or get_settings())
        self._enabled = cfg.llm.enabled
        self._model = cfg.llm.model or _LLM_MODEL
        self._max_tokens = cfg.llm.max_tokens
        self._timeout = cfg.llm.timeout_seconds
        self._max_retries = cfg.llm.max_retries
        self._metrics = metrics or get_metrics()
        self._breaker = circuit_breaker or AsyncCircuitBreaker(
            failure_threshold=cfg.resilience.circuit_failure_threshold,
            reset_seconds=cfg.resilience.circuit_reset_seconds,
            name="llm-classifier",
        )
        self._client = None

    def _get_client(self):
        if self._client is None:
            from anthropic import AsyncAnthropic  # lazy import; optional dependency

            self._client = AsyncAnthropic()
        return self._client

    async def classify(
        self,
        *,
        gap_report: GapReport,
        blockers: list[Blocker],
        rule_assessment: RuleAssessment,
    ) -> LLMAssessment | None:
        """Return a schema-validated LLM assessment, or ``None`` to fall back.

        The call is bounded by a timeout, retried on transient failure, and guarded
        by a circuit breaker so a sustained LLM outage fast-fails instead of adding
        latency to every diagnostic. Any failure degrades gracefully to ``None``.
        """
        if not self._enabled:
            return None
        try:
            client = self._get_client()
        except Exception:  # noqa: BLE001 - optional dependency / config absent
            logger.info("LLM classifier unavailable; using rule engine only.")
            return None

        system = (
            "You are a senior ESG and regulatory-compliance assessor. You receive the "
            "deterministic output of a diagnostic engine (per-domain perceived vs. "
            "evidenced maturity, prioritised blockers, and a rule-based maturity level). "
            "Provide an independent, conservative second opinion. Anchor your rating on "
            "documentary evidence, not self-assessment. Be specific and audit-minded."
        )
        payload = {
            "rule_based_level": int(rule_assessment.level),
            "rule_based_score": rule_assessment.score,
            "overall_perceived": gap_report.overall_perceived,
            "overall_evidenced": gap_report.overall_evidenced,
            "domain_gaps": [
                {
                    "domain": g.domain.value,
                    "perceived": g.perceived_score,
                    "evidenced": g.evidenced_score,
                    "direction": g.direction.value,
                    "severity": g.severity.value,
                }
                for g in gap_report.domain_gaps
            ],
            "top_blockers": [
                {"title": b.title, "priority": b.priority, "category": b.category.value}
                for b in blockers[:5]
            ],
        }
        user = (
            "Assess overall sustainability/compliance maturity (1=Initial .. 5=Optimized) "
            "from this diagnostic data and return the structured schema.\n\n"
            f"{json.dumps(payload, indent=2)}"
        )

        async def _invoke() -> LLMAssessment | None:
            response = await with_timeout(
                client.messages.parse(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    thinking={"type": "adaptive"},
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    output_format=LLMAssessment,
                ),
                self._timeout,
            )
            assessment = getattr(response, "parsed_output", None)
            if assessment is None and getattr(response, "stop_reason", None) == "refusal":
                logger.warning("LLM declined the classification request.")
            return assessment

        try:
            with track("ms1.llm.classify"):
                result = await self._breaker.call(
                    retry_call, _invoke, attempts=self._max_retries + 1, base_delay=0.5
                )
        except CircuitOpenError:
            self._metrics.increment("ms1.llm.circuit_open")
            logger.warning("LLM circuit open; skipping classification this run.")
            return None
        except Exception as exc:  # noqa: BLE001 - degrade gracefully on any API error
            self._metrics.increment("ms1.llm.errors")
            logger.warning("LLM maturity classification failed: %s", exc)
            return None

        self._metrics.increment("ms1.llm.success" if result is not None else "ms1.llm.empty")
        return result


# ---------------------------------------------------------------------------
# Persistence — the project_profiles data contract
# ---------------------------------------------------------------------------

_PROFILE_DDL = """
CREATE TABLE IF NOT EXISTS project_profiles (
    project_id          UUID PRIMARY KEY,
    tenant_id           UUID,
    diagnostic_answers  JSONB NOT NULL,
    maturity_level      INTEGER,
    maturity_label      TEXT,
    schema_version      TEXT NOT NULL,
    revision            INTEGER NOT NULL DEFAULT 1,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS project_profiles_tenant_idx
    ON project_profiles (tenant_id);

-- Append-only audit trail: every diagnostic run is retained for compliance review.
CREATE TABLE IF NOT EXISTS project_profiles_history (
    id                  BIGSERIAL PRIMARY KEY,
    project_id          UUID NOT NULL,
    tenant_id           UUID,
    revision            INTEGER NOT NULL,
    diagnostic_answers  JSONB NOT NULL,
    maturity_level      INTEGER,
    method              TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS project_profiles_history_idx
    ON project_profiles_history (project_id, revision DESC);
"""


class ProjectProfileRepository:
    """Upserts the diagnostic result into ``project_profiles`` for MS2 to read.

    Each save is transactional and tenant-scoped, and also appends an immutable row
    to ``project_profiles_history`` — every diagnostic run is retained for audit,
    which is a hard requirement for a regulated-disclosure workflow.
    """

    def __init__(self, pool, *, metrics: MetricsSink | None = None) -> None:
        self._pool = pool
        self._metrics = metrics or get_metrics()

    async def ensure_schema(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(_PROFILE_DDL)

    async def save(
        self,
        project_id: uuid.UUID,
        answers: DiagnosticAnswers,
        *,
        tenant_id: uuid.UUID | None = None,
    ) -> int:
        """Persist the current profile and append a history revision. Returns the revision."""
        payload = json.dumps(answers.model_dump(mode="json"))
        upsert = """
            INSERT INTO project_profiles (
                project_id, tenant_id, diagnostic_answers, maturity_level,
                maturity_label, schema_version
            )
            VALUES ($1, $2, $3::jsonb, $4, $5, $6)
            ON CONFLICT (project_id) DO UPDATE SET
                tenant_id = EXCLUDED.tenant_id,
                diagnostic_answers = EXCLUDED.diagnostic_answers,
                maturity_level = EXCLUDED.maturity_level,
                maturity_label = EXCLUDED.maturity_label,
                schema_version = EXCLUDED.schema_version,
                revision = project_profiles.revision + 1,
                updated_at = now()
            RETURNING revision;
        """
        history = """
            INSERT INTO project_profiles_history (
                project_id, tenant_id, revision, diagnostic_answers, maturity_level, method
            )
            VALUES ($1, $2, $3, $4::jsonb, $5, $6);
        """

        async def _persist() -> int:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    revision = await conn.fetchval(
                        upsert,
                        project_id,
                        tenant_id,
                        payload,
                        answers.overall.maturity_level,
                        answers.overall.maturity_label,
                        answers.schema_version,
                    )
                    await conn.execute(
                        history,
                        project_id,
                        tenant_id,
                        revision,
                        payload,
                        answers.overall.maturity_level,
                        answers.method,
                    )
                    return int(revision)

        try:
            revision = await retry_call(_persist, attempts=3, base_delay=0.2)
        except Exception as exc:  # noqa: BLE001 - normalise to a domain error
            self._metrics.increment("ms1.profile.persist_errors")
            raise PersistenceError("failed to persist project profile") from exc

        self._metrics.increment("ms1.profile.saved")
        return revision

    async def get(self, project_id: uuid.UUID):
        """Fetch the current ``diagnostic_answers`` for a project (or ``None``)."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT diagnostic_answers FROM project_profiles WHERE project_id = $1;",
                project_id,
            )
        return row["diagnostic_answers"] if row else None


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class DiagnosticEngine:
    """Orchestrates the full MS1 diagnostic and persists the result contract."""

    def __init__(
        self,
        *,
        graph: QuestionGraph | None = None,
        gap_detector: GapDetector | None = None,
        blocker_ranker: BlockerRanker | None = None,
        rule_engine: RuleEngine | None = None,
        llm_classifier: LLMMaturityClassifier | None = None,
        repository: ProjectProfileRepository | None = None,
        max_blockers: int = 10,
        settings: Settings | None = None,
        metrics: MetricsSink | None = None,
    ) -> None:
        self._graph = graph or build_default_graph()
        self._gap_detector = gap_detector or GapDetector(graph=self._graph)
        self._blocker_ranker = blocker_ranker or BlockerRanker()
        self._rule_engine = rule_engine or RuleEngine()
        self._llm_classifier = llm_classifier
        self._repository = repository
        self._max_blockers = max_blockers
        self._settings = settings or get_settings()
        self._metrics = metrics or get_metrics()

    async def diagnose(
        self,
        *,
        project_id: uuid.UUID,
        answers: dict[str, object],
        signals: list[ExtractedSignal],
        persist: bool = True,
        tenant_id: uuid.UUID | None = None,
        correlation_id: str | None = None,
    ) -> DiagnosticAnswers:
        """Run the diagnostic and (optionally) write the project_profiles contract."""
        # Reject malformed answers up front so bad input can't silently skew scores.
        issues = self._graph.validate_answers(answers)
        if issues:
            raise AnswerValidationError(
                f"{len(issues)} invalid answer(s) for project {project_id}", issues=issues
            )

        with bind_correlation_id(correlation_id), track("ms1.diagnose"):
            return await self._run(
                project_id=project_id,
                answers=answers,
                signals=signals,
                persist=persist,
                tenant_id=tenant_id,
            )

    async def _run(
        self,
        *,
        project_id: uuid.UUID,
        answers: dict[str, object],
        signals: list[ExtractedSignal],
        persist: bool,
        tenant_id: uuid.UUID | None,
    ) -> DiagnosticAnswers:
        # Keep only answers on active branches so abandoned paths don't skew scoring.
        clean_answers = self._graph.filter_answers(answers)
        coverage = self._graph.coverage(clean_answers)
        complete = self._graph.is_complete(clean_answers)

        gap_report = self._gap_detector.detect(answers=clean_answers, signals=signals)

        unanswered_required = [
            (q.id, q.domain)
            for q in self._graph.next_questions(clean_answers)
            if q.required
        ]
        blockers = self._blocker_ranker.rank(
            gap_report=gap_report,
            unanswered_required=unanswered_required,
            limit=self._max_blockers,
        )

        rule_assessment = self._rule_engine.classify(
            gap_report=gap_report, coverage=coverage
        )

        llm_assessment: LLMAssessment | None = None
        if self._llm_classifier is not None:
            llm_assessment = await self._llm_classifier.classify(
                gap_report=gap_report,
                blockers=blockers,
                rule_assessment=rule_assessment,
            )

        overall, divergence = self._reconcile(rule_assessment, llm_assessment)
        method = "rule_engine+llm" if llm_assessment is not None else "rule_engine"

        result = DiagnosticAnswers(
            project_id=str(project_id),
            generated_at=datetime.now(timezone.utc).isoformat(),
            method=method,
            overall=overall,
            domains=self._domain_maturities(gap_report),
            gap_report=gap_report,
            blockers=blockers,
            questionnaire={
                "coverage": coverage,
                "complete": complete,
                "active": len(self._graph.active_questions(clean_answers)),
                "answered": len(clean_answers),
                "unanswered_required": [qid for qid, _ in unanswered_required],
            },
            evidence={
                "signal_count": len(signals),
                "domains_with_evidence": sorted(
                    {
                        s.domain.value
                        for s in signals
                        if s.domain is not SignalDomain.UNCLASSIFIED
                    }
                ),
            },
            llm_assessment=llm_assessment,
            divergence_note=divergence,
        )

        if persist:
            if self._repository is None:
                raise RuntimeError("persist=True requires a ProjectProfileRepository")
            revision = await self._repository.save(
                project_id, result, tenant_id=tenant_id
            )
            logger.info(
                "Saved diagnostic for project %s rev %d: level %d (%s)",
                project_id, revision, overall.maturity_level, overall.maturity_label,
            )

        self._metrics.increment(
            "ms1.diagnose.completed", maturity=str(overall.maturity_level), method=method
        )
        return result

    def _reconcile(
        self, rule: RuleAssessment, llm: LLMAssessment | None
    ) -> tuple[OverallMaturity, str | None]:
        """Rule engine is authoritative; the LLM tunes confidence and flags divergence."""
        level = rule.level
        confidence = rule.confidence
        divergence: str | None = None

        if llm is not None:
            delta = abs(llm.maturity_level - int(rule.level))
            if delta == 0:
                confidence = round(min(1.0, confidence + 0.1), 3)
            elif delta == 1:
                divergence = (
                    f"LLM rated level {llm.maturity_level} vs. rule engine "
                    f"{int(rule.level)} (minor divergence)."
                )
                confidence = round(max(0.1, confidence - 0.05), 3)
            else:
                divergence = (
                    f"Material divergence: LLM level {llm.maturity_level} vs. rule "
                    f"engine {int(rule.level)}. Rule engine retained; manual review advised."
                )
                confidence = round(max(0.1, confidence - 0.15), 3)

        rationale = rule.rationale
        if llm is not None and llm.narrative:
            rationale = f"{rule.rationale} LLM summary: {llm.narrative}"

        return (
            OverallMaturity(
                maturity_level=int(level),
                maturity_label=level.label,
                score=rule.score,
                confidence=confidence,
                rationale=rationale,
            ),
            divergence,
        )

    @staticmethod
    def _domain_maturities(gap_report: GapReport) -> list[DomainMaturity]:
        domains: list[DomainMaturity] = []
        for gap in gap_report.domain_gaps:
            level = MaturityLevel.from_score(gap.evidenced_score)
            domains.append(
                DomainMaturity(
                    domain=gap.domain,
                    maturity_level=int(level),
                    maturity_label=level.label,
                    perceived_score=gap.perceived_score,
                    evidenced_score=gap.evidenced_score,
                    gap=gap.gap,
                    direction=gap.direction,
                )
            )
        return domains
