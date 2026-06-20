"""Perception-vs-Reality analytics engine for MS1.

Compares two independent views of the organisation's posture, per domain:

* **Perception** — derived from the self-reported questionnaire answers
  (:mod:`services.ms1_diagnostic.questions`).
* **Reality** — derived from the typed evidence the File Parser Service extracted
  from uploaded documents (:class:`~services.file_parser.normalizer.ExtractedSignal`).

A positive gap (perception > reality) flags an *overclaim* — a confident answer the
documents don't back up, which is the highest-value finding for a compliance audit.
A negative gap flags a *hidden strength* the organisation under-reports.
"""

from __future__ import annotations

from enum import Enum
from typing import Sequence

from pydantic import BaseModel, Field

from services.file_parser.normalizer import ExtractedSignal, SignalDomain
from services.ms1_diagnostic.questions import QuestionGraph


class GapSeverity(str, Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class GapDirection(str, Enum):
    ALIGNED = "aligned"
    OVERCLAIM = "overclaim"  # perceived > evidenced
    UNDERCLAIM = "underclaim"  # perceived < evidenced (hidden strength)


class DomainGap(BaseModel):
    """The perception/reality comparison for a single domain."""

    domain: SignalDomain
    perceived_score: float = Field(ge=0.0, le=1.0)
    evidenced_score: float = Field(ge=0.0, le=1.0)
    gap: float = Field(description="perceived - evidenced, in [-1, 1].")
    direction: GapDirection
    severity: GapSeverity
    evidence_count: int
    answered_count: int
    supporting_signal_ids: list[str] = Field(default_factory=list)
    rationale: str = ""


class GapReport(BaseModel):
    """Full perception-vs-reality output, plus convenience rollups."""

    domain_gaps: list[DomainGap]
    overall_perceived: float
    overall_evidenced: float
    overall_gap: float

    def overclaims(self) -> list[DomainGap]:
        return [g for g in self.domain_gaps if g.direction is GapDirection.OVERCLAIM]

    def by_domain(self) -> dict[SignalDomain, DomainGap]:
        return {g.domain: g for g in self.domain_gaps}


# Domains we always assess, even when no question/evidence exists for them.
_ASSESSED_DOMAINS = (
    SignalDomain.ENVIRONMENTAL,
    SignalDomain.SOCIAL,
    SignalDomain.GOVERNANCE,
    SignalDomain.COMPLIANCE,
)


def _severity_for(gap_magnitude: float) -> GapSeverity:
    if gap_magnitude < 0.1:
        return GapSeverity.NONE
    if gap_magnitude < 0.25:
        return GapSeverity.LOW
    if gap_magnitude < 0.45:
        return GapSeverity.MODERATE
    if gap_magnitude < 0.65:
        return GapSeverity.HIGH
    return GapSeverity.CRITICAL


class GapDetector:
    """Computes perceived vs. evidenced maturity per domain.

    Parameters
    ----------
    evidence_saturation:
        Number of distinct, confident signals at which a domain's evidenced score
        approaches its ceiling. Keeps a single document from maxing out "reality".
    confidence_floor:
        Minimum signal confidence to count a signal as real evidence.
    """

    def __init__(
        self,
        *,
        graph: QuestionGraph,
        evidence_saturation: int = 6,
        confidence_floor: float = 0.4,
    ) -> None:
        self._graph = graph
        self._evidence_saturation = max(evidence_saturation, 1)
        self._confidence_floor = confidence_floor

    def detect(
        self, *, answers: dict[str, object], signals: Sequence[ExtractedSignal]
    ) -> GapReport:
        perceived = self._perceived_scores(answers)
        evidenced, evidence_index = self._evidenced_scores(signals)

        domains = set(_ASSESSED_DOMAINS) | set(perceived) | set(evidenced)
        domains.discard(SignalDomain.UNCLASSIFIED)

        domain_gaps: list[DomainGap] = []
        for domain in sorted(domains, key=lambda d: d.value):
            p_score, answered = perceived.get(domain, (0.0, 0))
            e_score = evidenced.get(domain, 0.0)
            evidence = evidence_index.get(domain, [])
            gap = round(p_score - e_score, 4)
            magnitude = abs(gap)

            if magnitude < 0.1:
                direction = GapDirection.ALIGNED
            elif gap > 0:
                direction = GapDirection.OVERCLAIM
            else:
                direction = GapDirection.UNDERCLAIM

            domain_gaps.append(
                DomainGap(
                    domain=domain,
                    perceived_score=round(p_score, 4),
                    evidenced_score=round(e_score, 4),
                    gap=gap,
                    direction=direction,
                    severity=_severity_for(magnitude),
                    evidence_count=len(evidence),
                    answered_count=answered,
                    supporting_signal_ids=[s.id for s in evidence[:10]],
                    rationale=self._rationale(direction, domain, answered, len(evidence)),
                )
            )

        overall_perceived = _mean(g.perceived_score for g in domain_gaps)
        overall_evidenced = _mean(g.evidenced_score for g in domain_gaps)
        return GapReport(
            domain_gaps=domain_gaps,
            overall_perceived=round(overall_perceived, 4),
            overall_evidenced=round(overall_evidenced, 4),
            overall_gap=round(overall_perceived - overall_evidenced, 4),
        )

    def _perceived_scores(
        self, answers: dict[str, object]
    ) -> dict[SignalDomain, tuple[float, int]]:
        """Weighted-average normalized answer score per domain."""
        weighted: dict[SignalDomain, list[tuple[float, float]]] = {}
        for question in self._graph.active_questions(answers):
            score = question.normalized_score(answers.get(question.id))
            if score is None:
                continue
            weighted.setdefault(question.domain, []).append((score, question.weight))

        result: dict[SignalDomain, tuple[float, int]] = {}
        for domain, pairs in weighted.items():
            total_weight = sum(weight for _, weight in pairs)
            if total_weight == 0:
                continue
            avg = sum(score * weight for score, weight in pairs) / total_weight
            result[domain] = (max(0.0, min(avg, 1.0)), len(pairs))
        return result

    def _evidenced_scores(
        self, signals: Sequence[ExtractedSignal]
    ) -> tuple[dict[SignalDomain, float], dict[SignalDomain, list[ExtractedSignal]]]:
        index: dict[SignalDomain, list[ExtractedSignal]] = {}
        for signal in signals:
            if signal.confidence < self._confidence_floor:
                continue
            if signal.domain is SignalDomain.UNCLASSIFIED:
                continue
            index.setdefault(signal.domain, []).append(signal)

        scores: dict[SignalDomain, float] = {}
        for domain, domain_signals in index.items():
            domain_signals.sort(key=lambda s: s.confidence, reverse=True)
            # Evidence strength = saturating sum of signal confidences.
            confidence_mass = sum(s.confidence for s in domain_signals)
            saturated = confidence_mass / (confidence_mass + self._evidence_saturation)
            # Reward diversity of signal types (a metric + a target + a policy beats
            # three of the same kind).
            type_diversity = len({s.signal_type for s in domain_signals}) / 5.0
            score = 0.7 * saturated + 0.3 * min(type_diversity, 1.0)
            scores[domain] = max(0.0, min(score, 1.0))
        return scores, index

    @staticmethod
    def _rationale(
        direction: GapDirection, domain: SignalDomain, answered: int, evidence: int
    ) -> str:
        name = domain.value
        if direction is GapDirection.OVERCLAIM:
            return (
                f"Self-assessment for {name} is more favourable than the {evidence} "
                f"supporting document signal(s) justify — verify before disclosure."
            )
        if direction is GapDirection.UNDERCLAIM:
            return (
                f"Documents evidence stronger {name} performance ({evidence} signal(s)) "
                f"than the questionnaire reflects — capture this in reporting."
            )
        return f"Perception and evidence are aligned for {name}."


def _mean(values) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 0.0
