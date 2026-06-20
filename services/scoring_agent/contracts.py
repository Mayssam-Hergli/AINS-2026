"""Shared data contracts for the MS2 Scoring Agent — the merge interface.

This module is the single source of truth for how the Scoring Agent integrates with
its teammates over the shared ``project_profiles`` table:

* **Read contract** — :class:`DiagnosticAnswersView` is a *tolerant* reader over the
  ``diagnostic_answers`` JSON that MS1 writes. It depends only on a documented subset
  of fields and degrades to safe defaults if a field is absent, so a schema tweak on
  the MS1 side can't crash scoring.
* **Write contract** — :class:`ScoreObject` / :class:`ScoreSet` define exactly what the
  agent writes back to the ``scores`` column for MS3 to consume.

Column ownership on ``project_profiles`` (see INTEGRATION.md):
    diagnostic_answers  → owned by MS1 (we only READ)
    scores              → owned by MS2 / this agent (we only WRITE)
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# --- Column / version constants (shared vocabulary for the merge) -----------
PROFILE_TABLE = "project_profiles"
DIAGNOSTIC_COLUMN = "diagnostic_answers"
SCORES_COLUMN = "scores"
SCORES_SCHEMA_VERSION = "ms2.scores.v1"

# The five score keys MS3 can rely on always being present, in this order.
PILLAR_KEYS = ("environmental", "social", "governance", "compliance")
OVERALL_KEY = "overall"
SCORE_KEYS = (*PILLAR_KEYS, OVERALL_KEY)


class ScoreBand(str, Enum):
    AT_RISK = "at_risk"
    DEVELOPING = "developing"
    ESTABLISHED = "established"
    LEADING = "leading"


# ---------------------------------------------------------------------------
# Read contract: a tolerant view over MS1's diagnostic_answers
# ---------------------------------------------------------------------------

class DomainView(BaseModel):
    """Per-domain slice of the diagnostic, merged from ``domains`` + ``gap_report``."""

    domain: str
    perceived_score: float = 0.0
    evidenced_score: float = 0.0
    gap: float = 0.0
    direction: str = "aligned"
    maturity_level: int = 1
    evidence_count: int = 0
    supporting_signal_ids: list[str] = Field(default_factory=list)
    severity: str = "none"


class BlockerView(BaseModel):
    domain: str = "unclassified"
    title: str = ""
    category: str = ""
    priority: float = 0.0


class DiagnosticAnswersView(BaseModel):
    """Read-only projection of MS1's ``diagnostic_answers`` payload.

    Construct via :meth:`from_raw` with whatever dict was stored in the DB. Only the
    fields listed here are relied upon; everything else is ignored.
    """

    schema_version: str = "unknown"
    coverage: float = 0.0
    overall_score: float = 0.0
    overall_maturity_level: int = 1
    overall_gap: float = 0.0
    domains: dict[str, DomainView] = Field(default_factory=dict)
    blockers: list[BlockerView] = Field(default_factory=list)
    signal_count: int = 0

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "DiagnosticAnswersView":
        raw = raw or {}
        overall = raw.get("overall", {}) or {}
        questionnaire = raw.get("questionnaire", {}) or {}
        evidence = raw.get("evidence", {}) or {}
        gap_report = raw.get("gap_report", {}) or {}

        # Merge per-domain maturity (domains[]) with per-domain evidence (gap_report).
        domains: dict[str, DomainView] = {}
        for entry in raw.get("domains", []) or []:
            name = str(entry.get("domain", "")).lower()
            if not name:
                continue
            domains[name] = DomainView(
                domain=name,
                perceived_score=_f(entry.get("perceived_score")),
                evidenced_score=_f(entry.get("evidenced_score")),
                gap=_f(entry.get("gap")),
                direction=str(entry.get("direction", "aligned")),
                maturity_level=_i(entry.get("maturity_level"), 1),
            )
        for entry in gap_report.get("domain_gaps", []) or []:
            name = str(entry.get("domain", "")).lower()
            if not name:
                continue
            view = domains.get(name) or DomainView(domain=name)
            view.perceived_score = _f(entry.get("perceived_score"), view.perceived_score)
            view.evidenced_score = _f(entry.get("evidenced_score"), view.evidenced_score)
            view.gap = _f(entry.get("gap"), view.gap)
            view.direction = str(entry.get("direction", view.direction))
            view.evidence_count = _i(entry.get("evidence_count"), 0)
            view.supporting_signal_ids = list(entry.get("supporting_signal_ids", []) or [])
            view.severity = str(entry.get("severity", "none"))
            domains[name] = view

        blockers = [
            BlockerView(
                domain=str(b.get("domain", "unclassified")).lower(),
                title=str(b.get("title", "")),
                category=str(b.get("category", "")),
                priority=_f(b.get("priority")),
            )
            for b in raw.get("blockers", []) or []
        ]

        return cls(
            schema_version=str(raw.get("schema_version", "unknown")),
            coverage=_f(questionnaire.get("coverage")),
            overall_score=_f(overall.get("score")),
            overall_maturity_level=_i(overall.get("maturity_level"), 1),
            overall_gap=_f(gap_report.get("overall_gap")),
            domains=domains,
            blockers=blockers,
            signal_count=_i(evidence.get("signal_count"), 0),
        )

    def domain(self, key: str) -> DomainView:
        return self.domains.get(key, DomainView(domain=key))

    def blockers_for(self, key: str) -> list[BlockerView]:
        return sorted(
            (b for b in self.blockers if b.domain == key),
            key=lambda b: b.priority,
            reverse=True,
        )


# ---------------------------------------------------------------------------
# Write contract: what MS3 reads
# ---------------------------------------------------------------------------

class ScoreObject(BaseModel):
    """A single scored dimension written to ``project_profiles.scores``."""

    key: str = Field(description="Stable machine key, e.g. 'environmental'.")
    label: str
    score: float = Field(ge=0.0, le=100.0)
    band: ScoreBand
    confidence: float = Field(ge=0.0, le=1.0)
    justification: str
    drivers: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)
    tool: str = Field(description="Name of the scoring tool that produced this object.")
    computed_at: str


class ScoreSet(BaseModel):
    """The full Scoring Agent output stored in ``project_profiles.scores``."""

    schema_version: str = SCORES_SCHEMA_VERSION
    project_id: str
    generated_at: str
    method: str = Field(description="'rule' or 'rule+llm'.")
    diagnostic_schema_version: str = "unknown"
    overall_score: float = Field(ge=0.0, le=100.0)
    overall_band: ScoreBand
    scores: list[ScoreObject]

    def by_key(self) -> dict[str, ScoreObject]:
        return {s.key: s for s in self.scores}


# ---------------------------------------------------------------------------
# Tool-internal result (pre-justification, pre-band)
# ---------------------------------------------------------------------------

class ToolResult(BaseModel):
    """A scoring tool's numeric output before justification/band assignment."""

    key: str
    label: str
    score: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)
    drivers: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)
    default_justification: str = ""
    tool: str = ""


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _i(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
