"""The Scoring Agent's five scoring tools.

Each tool turns the diagnostic view into one numeric :class:`ToolResult`. The four
pillar tools (E/S/G/Compliance) score a domain from its evidenced maturity, penalised
for overclaims and weighted by questionnaire coverage; the fifth (overall) composes
the pillar scores into a single readiness number.

Tools are *deterministic and auditable* — every number is derived from explicit inputs
recorded on the result. The LLM is used only to phrase justifications (see
:mod:`services.scoring_agent.justifier`), never to produce the scores themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from services.common.config import ScoringConfig
from services.scoring_agent.contracts import (
    OVERALL_KEY,
    PILLAR_KEYS,
    DiagnosticAnswersView,
    ScoreBand,
    ToolResult,
)

_PILLAR_LABELS = {
    "environmental": "Environmental",
    "social": "Social",
    "governance": "Governance",
    "compliance": "Compliance",
}


@dataclass(slots=True)
class ScoringContext:
    """Everything a tool needs: the diagnostic view plus tuning config."""

    view: DiagnosticAnswersView
    config: ScoringConfig


class ScoringTool(Protocol):
    key: str
    label: str

    def score(self, ctx: ScoringContext, prior: dict[str, ToolResult]) -> ToolResult: ...


def band_for(score: float, config: ScoringConfig) -> ScoreBand:
    if score < config.band_at_risk_max:
        return ScoreBand.AT_RISK
    if score < config.band_developing_max:
        return ScoreBand.DEVELOPING
    if score < config.band_established_max:
        return ScoreBand.ESTABLISHED
    return ScoreBand.LEADING


def _confidence(coverage: float, evidence_count: int) -> float:
    evidence_factor = min(evidence_count / 5.0, 1.0)
    return round(max(0.05, min(0.25 + 0.4 * coverage + 0.35 * evidence_factor, 1.0)), 3)


class PillarScoringTool:
    """Scores one ESG/compliance pillar from its domain view."""

    def __init__(self, key: str) -> None:
        if key not in PILLAR_KEYS:
            raise ValueError(f"unknown pillar key: {key}")
        self.key = key
        self.label = _PILLAR_LABELS[key]

    def score(self, ctx: ScoringContext, prior: dict[str, ToolResult]) -> ToolResult:
        domain = ctx.view.domain(self.key)
        overclaim = max(domain.gap, 0.0)
        # Reality-anchored: evidenced maturity, reduced by any unsubstantiated claim.
        normalized = max(0.0, domain.evidenced_score - ctx.config.overclaim_penalty * overclaim)
        score = round(min(normalized, 1.0) * 100.0, 2)
        confidence = _confidence(ctx.view.coverage, domain.evidence_count)

        drivers: list[str] = []
        if overclaim >= 0.1:
            drivers.append(
                f"Self-assessment exceeds documented evidence by {overclaim:.2f} "
                f"(overclaim risk)."
            )
        if domain.direction == "underclaim":
            drivers.append("Documented performance is stronger than self-reported.")
        for blocker in ctx.view.blockers_for(self.key)[:2]:
            drivers.append(f"Blocker: {blocker.title} (priority {blocker.priority:.0f}).")
        if not drivers:
            drivers.append(
                f"Evidenced maturity {domain.evidenced_score:.2f} with no material gap."
            )

        default_justification = (
            f"{self.label} scored {score:.0f}/100 ({band_for(score, ctx.config).value}). "
            f"Anchored on evidenced maturity {domain.evidenced_score:.2f}"
            + (
                f", reduced for an overclaim gap of {overclaim:.2f}." if overclaim >= 0.1
                else "."
            )
        )

        return ToolResult(
            key=self.key,
            label=self.label,
            score=score,
            confidence=confidence,
            drivers=drivers,
            evidence_refs=domain.supporting_signal_ids[:10],
            inputs={
                "perceived_score": domain.perceived_score,
                "evidenced_score": domain.evidenced_score,
                "gap": domain.gap,
                "direction": domain.direction,
                "evidence_count": domain.evidence_count,
                "coverage": ctx.view.coverage,
            },
            default_justification=default_justification,
            tool=f"{self.key}_score",
        )


class OverallScoringTool:
    """Composes the four pillar scores into a single readiness score."""

    key = OVERALL_KEY
    label = "Overall Readiness"

    def score(self, ctx: ScoringContext, prior: dict[str, ToolResult]) -> ToolResult:
        weights = ctx.config.pillar_weights
        weighted_sum = 0.0
        weight_total = 0.0
        confidences: list[float] = []
        for key in PILLAR_KEYS:
            result = prior.get(key)
            if result is None:
                continue
            weight = float(weights.get(key, 0.0))
            weighted_sum += weight * result.score
            weight_total += weight
            confidences.append(result.confidence)

        base = weighted_sum / weight_total if weight_total else 0.0
        # Systemic risk: many high-priority blockers depress overall readiness.
        critical = sum(1 for b in ctx.view.blockers if b.priority >= 80.0)
        penalty = min(critical * 3.0, 15.0)
        score = round(max(0.0, min(base - penalty, 100.0)), 2)
        confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.1

        weakest = min(
            (prior[k] for k in PILLAR_KEYS if k in prior),
            key=lambda r: r.score,
            default=None,
        )
        drivers = [f"Weighted ESG/compliance composite = {base:.1f}/100."]
        if weakest is not None:
            drivers.append(f"Weakest pillar: {weakest.label} ({weakest.score:.0f}/100).")
        if critical:
            drivers.append(f"{critical} high-priority blocker(s) reduced overall score.")

        default_justification = (
            f"Overall readiness {score:.0f}/100 ({band_for(score, ctx.config).value}), "
            f"a weighted composite of the four pillars"
            + (f" less a {penalty:.0f}-point systemic-risk penalty." if penalty else ".")
        )

        return ToolResult(
            key=self.key,
            label=self.label,
            score=score,
            confidence=confidence,
            drivers=drivers,
            evidence_refs=[],
            inputs={
                "pillar_scores": {k: prior[k].score for k in PILLAR_KEYS if k in prior},
                "pillar_weights": dict(weights),
                "critical_blockers": critical,
                "diagnostic_overall_score": ctx.view.overall_score,
            },
            default_justification=default_justification,
            tool="overall_score",
        )


def default_tools() -> list[ScoringTool]:
    """The five scoring tools, in dependency order (pillars before overall)."""
    return [
        PillarScoringTool("environmental"),
        PillarScoringTool("social"),
        PillarScoringTool("governance"),
        PillarScoringTool("compliance"),
        OverallScoringTool(),
    ]
