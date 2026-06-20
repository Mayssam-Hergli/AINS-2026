"""Multi-criteria priority blocker matrix for MS1.

Turns the structured findings of the diagnostic — domain gaps, weak evidence, and
unanswered high-weight questions — into a ranked list of *blockers*: the concrete
issues standing between the organisation and a compliant, mature posture.

Each blocker is scored across several criteria (impact, regulatory exposure,
time-sensitivity, effort, dependency). The criteria are combined with configurable
weights into a single 0–100 priority, with effort treated as a *cost* (higher
effort lowers priority). This is a transparent weighted-sum decision matrix — every
input score is preserved on the blocker so the ranking is fully auditable.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator

from services.file_parser.normalizer import SignalDomain
from services.ms1_diagnostic.gap_detector import (
    DomainGap,
    GapDirection,
    GapReport,
    GapSeverity,
)


class BlockerCategory(str, Enum):
    EVIDENCE_GAP = "evidence_gap"  # claims without documentary backing
    DATA_GAP = "data_gap"  # missing measurement / tracking
    DISCLOSURE_GAP = "disclosure_gap"  # under-reporting real performance
    UNANSWERED = "unanswered"  # diagnostic left incomplete


class CriteriaScores(BaseModel):
    """Normalised 0–1 scores for each decision criterion."""

    impact: float = Field(ge=0.0, le=1.0)
    regulatory_exposure: float = Field(ge=0.0, le=1.0)
    time_sensitivity: float = Field(ge=0.0, le=1.0)
    effort: float = Field(ge=0.0, le=1.0, description="Cost to remediate; higher = harder.")
    dependency: float = Field(
        ge=0.0, le=1.0, description="Degree to which other work is blocked by this."
    )


class CriteriaWeights(BaseModel):
    """Relative importance of each criterion. Need not sum to 1 (normalised at use)."""

    impact: float = 0.30
    regulatory_exposure: float = 0.25
    time_sensitivity: float = 0.20
    dependency: float = 0.15
    effort: float = 0.10  # applied as a penalty

    @field_validator("*")
    @classmethod
    def _non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("weights must be non-negative")
        return value


class Blocker(BaseModel):
    """A single prioritised obstacle."""

    id: str
    domain: SignalDomain
    category: BlockerCategory
    title: str
    description: str
    criteria: CriteriaScores
    priority: float = Field(ge=0.0, le=100.0)
    rank: int = 0
    related_signal_ids: list[str] = Field(default_factory=list)


# Regulatory exposure baseline per domain — compliance and environmental issues
# carry the most direct legal/financial risk under CSRD-era regimes.
_REGULATORY_BASELINE: dict[SignalDomain, float] = {
    SignalDomain.COMPLIANCE: 0.95,
    SignalDomain.ENVIRONMENTAL: 0.85,
    SignalDomain.GOVERNANCE: 0.7,
    SignalDomain.SOCIAL: 0.6,
    SignalDomain.FINANCIAL: 0.55,
    SignalDomain.OPERATIONAL: 0.4,
    SignalDomain.UNCLASSIFIED: 0.3,
}

_SEVERITY_WEIGHT: dict[GapSeverity, float] = {
    GapSeverity.NONE: 0.0,
    GapSeverity.LOW: 0.25,
    GapSeverity.MODERATE: 0.5,
    GapSeverity.HIGH: 0.75,
    GapSeverity.CRITICAL: 1.0,
}


class BlockerRanker:
    """Builds and ranks blockers from a :class:`GapReport`."""

    def __init__(self, weights: CriteriaWeights | None = None) -> None:
        self._weights = weights or CriteriaWeights()

    def rank(
        self,
        *,
        gap_report: GapReport,
        unanswered_required: list[tuple[str, SignalDomain]] | None = None,
        limit: int | None = None,
    ) -> list[Blocker]:
        """Derive, score, and order blockers (highest priority first)."""
        blockers: list[Blocker] = []

        for gap in gap_report.domain_gaps:
            blocker = self._blocker_from_gap(gap)
            if blocker is not None:
                blockers.append(blocker)

        for question_id, domain in unanswered_required or []:
            blockers.append(self._blocker_from_unanswered(question_id, domain))

        blockers.sort(key=lambda b: b.priority, reverse=True)
        for index, blocker in enumerate(blockers, start=1):
            blocker.rank = index

        return blockers if limit is None else blockers[:limit]

    # -- blocker construction -------------------------------------------------

    def _blocker_from_gap(self, gap: DomainGap) -> Blocker | None:
        if gap.severity is GapSeverity.NONE:
            return None

        severity = _SEVERITY_WEIGHT[gap.severity]
        regulatory = _REGULATORY_BASELINE.get(gap.domain, 0.4)

        if gap.direction is GapDirection.OVERCLAIM:
            category = (
                BlockerCategory.DATA_GAP
                if gap.evidence_count == 0
                else BlockerCategory.EVIDENCE_GAP
            )
            impact = severity
            time_sensitivity = min(1.0, 0.5 + 0.5 * severity)
            # No measurement at all is a deeper (higher-effort) fix than poor evidence.
            effort = 0.75 if gap.evidence_count == 0 else 0.5
            dependency = 0.8 if category is BlockerCategory.DATA_GAP else 0.5
            title = f"Unsubstantiated {gap.domain.value} self-assessment"
        elif gap.direction is GapDirection.UNDERCLAIM:
            category = BlockerCategory.DISCLOSURE_GAP
            impact = 0.4 * severity  # lower stakes: it's an under-report, not a false claim
            time_sensitivity = 0.3
            effort = 0.3
            dependency = 0.2
            title = f"Under-reported {gap.domain.value} performance"
        else:
            return None

        criteria = CriteriaScores(
            impact=round(impact, 4),
            regulatory_exposure=round(regulatory * (0.6 + 0.4 * severity), 4),
            time_sensitivity=round(time_sensitivity, 4),
            effort=effort,
            dependency=dependency,
        )

        return Blocker(
            id=f"blk_{category.value}_{gap.domain.value}",
            domain=gap.domain,
            category=category,
            title=title,
            description=gap.rationale,
            criteria=criteria,
            priority=self._priority(criteria),
            related_signal_ids=list(gap.supporting_signal_ids),
        )

    def _blocker_from_unanswered(self, question_id: str, domain: SignalDomain) -> Blocker:
        regulatory = _REGULATORY_BASELINE.get(domain, 0.4)
        criteria = CriteriaScores(
            impact=0.5,
            regulatory_exposure=round(regulatory * 0.7, 4),
            time_sensitivity=0.4,
            effort=0.2,  # answering a question is cheap
            dependency=0.6,  # but it blocks the rest of the assessment
        )
        return Blocker(
            id=f"blk_unanswered_{question_id}",
            domain=domain,
            category=BlockerCategory.UNANSWERED,
            title=f"Incomplete diagnostic input ({question_id})",
            description=(
                f"Required diagnostic question '{question_id}' is unanswered; the "
                f"{domain.value} assessment is provisional until it is completed."
            ),
            criteria=criteria,
            priority=self._priority(criteria),
        )

    # -- scoring --------------------------------------------------------------

    def _priority(self, criteria: CriteriaScores) -> float:
        weights = self._weights
        benefit_weight = (
            weights.impact
            + weights.regulatory_exposure
            + weights.time_sensitivity
            + weights.dependency
        )
        total_weight = benefit_weight + weights.effort
        if total_weight == 0:
            return 0.0

        benefit = (
            weights.impact * criteria.impact
            + weights.regulatory_exposure * criteria.regulatory_exposure
            + weights.time_sensitivity * criteria.time_sensitivity
            + weights.dependency * criteria.dependency
        )
        # Effort is a cost: low effort (cheap to fix) raises priority.
        penalty = weights.effort * (1.0 - criteria.effort)
        score = (benefit + penalty) / total_weight
        return round(max(0.0, min(score, 1.0)) * 100.0, 2)
