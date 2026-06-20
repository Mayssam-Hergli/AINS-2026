"""Signal structuring and JSON-schema alignment for the File Parser Service.

This module defines the *shared data contract* between the File Parser Service and
MS1 (the Diagnostic Engine). Raw, messy fragments coming out of the extractors
(PDF text blocks, DOCX paragraphs, spreadsheet rows) are normalized here into a
flat list of :class:`ExtractedSignal` objects — typed, deduplicated evidence that
represents the "reality" half of MS1's perception-vs-reality analysis.

The taxonomy (:class:`SignalDomain`) is imported by ``services.ms1_diagnostic`` so
both services agree on how sustainability / compliance evidence is bucketed.
"""

from __future__ import annotations

import hashlib
import re
from enum import Enum
from typing import TYPE_CHECKING, Iterable

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:  # avoid an import cycle; extractors import nothing from here at runtime
    from services.file_parser.extractors import RawExtraction


# Dimensionality of the pgvector embedding column shared with the database.
EMBEDDING_DIM = 1536


class SignalDomain(str, Enum):
    """Top-level dimensions of an enterprise sustainability / compliance posture."""

    ENVIRONMENTAL = "environmental"
    SOCIAL = "social"
    GOVERNANCE = "governance"
    COMPLIANCE = "compliance"
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    UNCLASSIFIED = "unclassified"


class SignalType(str, Enum):
    """The shape of evidence a signal carries, independent of its domain."""

    METRIC = "metric"  # a measured quantity (e.g. 1,240 tCO2e)
    TARGET = "target"  # a forward-looking commitment (e.g. net-zero by 2040)
    POLICY = "policy"  # reference to a documented policy or procedure
    CERTIFICATION = "certification"  # ISO 14001, B-Corp, etc.
    STATEMENT = "statement"  # qualitative claim with no hard number
    DATE = "date"  # a deadline / reporting period


# Keyword taxonomy used to classify a fragment into a domain. Ordered roughly by
# specificity so that COMPLIANCE framework hits win over generic environmental terms.
_DOMAIN_KEYWORDS: dict[SignalDomain, tuple[str, ...]] = {
    SignalDomain.COMPLIANCE: (
        "csrd", "esrs", "gdpr", "tcfd", "sasb", "iso 14001", "iso 27001", "iso 50001",
        "sox", "eu taxonomy", "disclosure", "audit trail", "regulatory", "non-financial reporting",
    ),
    SignalDomain.ENVIRONMENTAL: (
        "scope 1", "scope 2", "scope 3", "ghg", "co2", "tco2e", "emission", "carbon",
        "renewable", "energy intensity", "water withdrawal", "waste", "biodiversity",
        "net zero", "net-zero", "decarbon",
    ),
    SignalDomain.SOCIAL: (
        "diversity", "inclusion", "gender pay", "human rights", "health and safety",
        "lost time injury", "labor", "labour", "community", "training hours", "turnover",
        "well-being", "wellbeing",
    ),
    SignalDomain.GOVERNANCE: (
        "board", "anti-corruption", "anti-bribery", "whistleblow", "code of conduct",
        "ethics", "remuneration", "risk management", "independent director", "data governance",
    ),
    SignalDomain.FINANCIAL: (
        "revenue", "capex", "opex", "green bond", "sustainable finance", "ebitda",
        "cost of capital",
    ),
    SignalDomain.OPERATIONAL: (
        "supply chain", "supplier", "procurement", "logistics", "facility", "fleet",
        "production volume",
    ),
}

_CERTIFICATION_HINTS = ("iso ", "b-corp", "b corp", "leed", "ecovadis", "certified", "accredit")
_TARGET_HINTS = ("target", "goal", "commit", "by 20", "ambition", "pledge", "roadmap")
_POLICY_HINTS = ("policy", "procedure", "framework", "charter", "code of", "guideline")

# A number *immediately followed by a recognised unit*. Requiring the unit avoids
# false metrics from years ("by 2040"), standard codes ("ISO 14001"), or ordinals
# ("Scope 1") — for a compliance tool, precision on numeric evidence beats recall.
# The number alternation lists comma-grouped thousands first, then a plain digit run,
# with look-arounds so "14001" matches fully instead of as a partial "140".
_VALUE_UNIT_RE = re.compile(
    r"(?P<number>-?(?<!\d)\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?(?<!\d)\d+(?:\.\d+)?)\s*"
    r"(?P<unit>%|tco2e|tco₂e|tonnes?|kwh|mwh|gwh|kg|m3|m³|years?|hours?|fte)(?![a-zA-Z])",
    re.IGNORECASE,
)

_DATE_RE = re.compile(r"\b(?:19|20)\d{2}\b")


class ExtractedSignal(BaseModel):
    """A single, typed piece of evidence pulled from a source document.

    Instances are persisted to the pgvector-backed ``document_signals`` table and
    consumed by MS1's :mod:`gap_detector` as the ground-truth "reality" signal set.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Stable content hash; doubles as a dedup key.")
    domain: SignalDomain
    signal_type: SignalType
    label: str = Field(..., description="Short human-readable summary of the evidence.")
    raw_text: str = Field(..., description="The originating fragment, verbatim.")
    value: float | None = Field(default=None, description="Parsed numeric value, if any.")
    unit: str | None = None
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="How strongly this fragment supports a real, measurable claim.",
    )
    source_document: str
    source_locator: str = Field(
        default="", description="Where in the document (e.g. 'page:3', 'sheet:Emissions')."
    )
    keywords: tuple[str, ...] = ()
    embedding: tuple[float, ...] | None = Field(
        default=None, description="Vector representation for pgvector similarity search."
    )


class NormalizedDocument(BaseModel):
    """The fully processed output of the parser pipeline for one source file."""

    document_id: str
    filename: str
    content_type: str
    signals: list[ExtractedSignal]
    full_text: str
    metadata: dict[str, str] = Field(default_factory=dict)

    def signals_by_domain(self) -> dict[SignalDomain, list[ExtractedSignal]]:
        grouped: dict[SignalDomain, list[ExtractedSignal]] = {}
        for signal in self.signals:
            grouped.setdefault(signal.domain, []).append(signal)
        return grouped


def _classify_domain(text: str) -> tuple[SignalDomain, tuple[str, ...]]:
    """Return the best-matching domain and the keywords that triggered the match."""
    lowered = text.lower()
    best_domain = SignalDomain.UNCLASSIFIED
    best_hits: tuple[str, ...] = ()
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        hits = tuple(kw for kw in keywords if kw in lowered)
        if len(hits) > len(best_hits):
            best_domain, best_hits = domain, hits
    return best_domain, best_hits


def _classify_type(text: str, value: float | None) -> SignalType:
    lowered = text.lower()
    if any(hint in lowered for hint in _CERTIFICATION_HINTS):
        return SignalType.CERTIFICATION
    if any(hint in lowered for hint in _TARGET_HINTS):
        return SignalType.TARGET
    if any(hint in lowered for hint in _POLICY_HINTS):
        return SignalType.POLICY
    if value is not None:
        return SignalType.METRIC
    if _DATE_RE.search(text) and len(text) < 80:
        return SignalType.DATE
    return SignalType.STATEMENT


def _parse_value(text: str) -> tuple[float | None, str | None]:
    """Return a (value, unit) pair only when a number carries a recognised unit."""
    match = _VALUE_UNIT_RE.search(text)
    if not match:
        return None, None
    number = match.group("number")
    unit = match.group("unit").lower()
    try:
        return float(number.replace(",", "")), unit
    except ValueError:
        return None, unit


def _score_confidence(signal_type: SignalType, value: float | None, hit_count: int) -> float:
    """Heuristic: hard numbers + certifications are stronger evidence than prose."""
    base = {
        SignalType.METRIC: 0.75,
        SignalType.CERTIFICATION: 0.8,
        SignalType.TARGET: 0.55,
        SignalType.POLICY: 0.55,
        SignalType.DATE: 0.45,
        SignalType.STATEMENT: 0.35,
    }[signal_type]
    if value is not None:
        base += 0.1
    base += min(hit_count, 3) * 0.05
    return round(min(base, 1.0), 3)


def _signal_id(source_document: str, locator: str, text: str) -> str:
    digest = hashlib.sha256(f"{source_document}|{locator}|{text}".encode()).hexdigest()
    return f"sig_{digest[:24]}"


class Normalizer:
    """Turns raw extraction fragments into a clean, typed, deduplicated signal set."""

    def __init__(self, min_fragment_length: int = 12) -> None:
        self._min_fragment_length = min_fragment_length

    def normalize(self, extraction: "RawExtraction") -> NormalizedDocument:
        """Build a :class:`NormalizedDocument` from a single file's raw extraction."""
        seen: set[str] = set()
        signals: list[ExtractedSignal] = []
        text_parts: list[str] = []

        for fragment, locator in self._iter_fragments(extraction):
            text_parts.append(fragment)
            cleaned = fragment.strip()
            if len(cleaned) < self._min_fragment_length:
                continue

            domain, hits = _classify_domain(cleaned)
            if domain is SignalDomain.UNCLASSIFIED and not hits:
                # Skip noise that maps to nothing in our taxonomy.
                continue

            value, unit = _parse_value(cleaned)
            signal_type = _classify_type(cleaned, value)
            signal_id = _signal_id(extraction.document_id, locator, cleaned)
            if signal_id in seen:
                continue
            seen.add(signal_id)

            signals.append(
                ExtractedSignal(
                    id=signal_id,
                    domain=domain,
                    signal_type=signal_type,
                    label=self._make_label(cleaned),
                    raw_text=cleaned,
                    value=value,
                    unit=unit,
                    confidence=_score_confidence(signal_type, value, len(hits)),
                    source_document=extraction.filename,
                    source_locator=locator,
                    keywords=hits,
                )
            )

        return NormalizedDocument(
            document_id=extraction.document_id,
            filename=extraction.filename,
            content_type=extraction.content_type,
            signals=signals,
            full_text="\n".join(text_parts),
            metadata=dict(extraction.metadata),
        )

    @staticmethod
    def _iter_fragments(extraction: "RawExtraction") -> Iterable[tuple[str, str]]:
        for block in extraction.text_blocks:
            # Split paragraphs into sentence-ish fragments so one number → one signal.
            for piece in re.split(r"(?<=[.;\n])\s+", block.text):
                piece = piece.strip()
                if piece:
                    yield piece, block.locator
        for table in extraction.tables:
            header = table.rows[0] if table.rows else []
            for row in table.rows[1:] if header else table.rows:
                # Pair each cell with its column header to preserve meaning.
                cells = (
                    [f"{h}: {c}" for h, c in zip(header, row) if c]
                    if header
                    else [c for c in row if c]
                )
                line = " | ".join(cells)
                if line:
                    yield line, table.locator

    @staticmethod
    def _make_label(text: str, max_len: int = 90) -> str:
        collapsed = re.sub(r"\s+", " ", text).strip()
        return collapsed if len(collapsed) <= max_len else collapsed[: max_len - 1] + "…"
