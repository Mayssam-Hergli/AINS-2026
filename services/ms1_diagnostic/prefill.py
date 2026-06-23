"""Document-driven pre-fill & verification for the MS1 questionnaire.

Parses an uploaded document (pitch deck / business plan — PDF, DOCX, CSV, XLSX via the
File Parser) and maps its content onto the venture questionnaire keys, so the founder's
form can be **pre-filled** and their submitted answers **cross-checked** against the
evidence in the document.

This runs *before* submission and does NOT change the `diagnostic_answers` contract MS2
reads — it produces suggestions and verification flags for the intake UI/reviewer. The
deterministic rule extractor needs no API key; an optional structured-LLM extractor can
be injected for richer inference.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from services.file_parser.extractors import ExtractorRegistry
from services.ms1_diagnostic.answer_schema import _coerce_bool, _coerce_int, _SPEC_BY_KEY

logger = logging.getLogger(__name__)


class AnswerSuggestion(BaseModel):
    key: str
    suggested_value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str = Field(description="Snippet of the document that triggered the suggestion.")
    source: str = "rule"


class Verification(BaseModel):
    key: str
    answered_value: Any = None
    suggested_value: Any
    confidence: float
    status: str  # "match" | "mismatch" | "prefill" (suggested but unanswered)


@dataclass(frozen=True)
class _Rule:
    key: str
    value: Any
    patterns: tuple[str, ...]
    confidence: float


# Deterministic evidence → answer mappings. Multiple rules per key are allowed; the
# highest-confidence match wins. Patterns are matched case-insensitively.
_RULES: tuple[_Rule, ...] = (
    _Rule("has_pitch_deck", True,
          (r"pitch deck", r"\bproblem\b.{0,60}\bsolution\b", r"\btraction\b",
           r"go[- ]to[- ]market", r"market opportunity"), 0.7),
    _Rule("funding_needed", "series_a", (r"series\s*a\b",), 0.85),
    _Rule("funding_needed", "seed", (r"\bpre[- ]?seed\b", r"\bseed\b", r"\bfundrais", r"raising\s*\$"), 0.7),
    _Rule("market_size", "very_large", (r"\$\s*\d+(\.\d+)?\s*(b\b|bn\b|billion)", r"tam[^.]{0,40}billion"), 0.6),
    _Rule("market_size", "large", (r"\$\s*\d+\s*(m\b|million)[^.]{0,20}(market|tam)", r"large market"), 0.5),
    _Rule("customer_interviews", "10+", (r"\b(\d{2,})\s+(customer\s+)?interviews", r"interviewed\s+\d{2,}"), 0.6),
    _Rule("has_loi", 1, (r"letters? of intent", r"\bLOIs?\b"), 0.75),
    _Rule("has_paying_customers", True,
          (r"paying customers", r"\bARR\b", r"\bMRR\b", r"recurring revenue"), 0.75),
    _Rule("revenue_model_documented", "documented",
          (r"revenue model", r"business model", r"monetiz", r"subscription"), 0.5),
    _Rule("revenue_model_type", "subscription", (r"\bsaas\b", r"software as a service", r"subscription"), 0.7),
    _Rule("revenue_model_type", "transactional", (r"marketplace", r"two[- ]sided", r"commission", r"per[- ]transaction"), 0.7),
    _Rule("revenue_model_type", "freemium", (r"freemium", r"free tier", r"free plan"), 0.7),
    _Rule("product_maturity", "product",
          (r"in production", r"live product", r"\blaunched\b", r"generally available"), 0.7),
    _Rule("product_maturity", "mvp", (r"\bmvp\b", r"minimum viable"), 0.7),
    _Rule("product_maturity", "prototype", (r"prototype", r"proof of concept", r"\bpoc\b"), 0.6),
    _Rule("pricing_strategy", "defined",
          (r"pricing (model|plan|strategy)", r"\$\s*\d+\s*/\s*(mo|month|year|user|seat)"), 0.6),
    _Rule("offer_need_alignment", "validated",
          (r"product[- ]market fit", r"customer validation", r"validated.{0,20}(need|demand)"), 0.6),
    _Rule("local_novelty", "unique", (r"first[- ]of[- ]its[- ]kind", r"\bpatented\b", r"proprietary"), 0.6),
    _Rule("technology_intensity", "high",
          (r"\bAI\b", r"artificial intelligence", r"machine learning", r"deep tech",
           r"proprietary (algorithm|technology)"), 0.7),
    _Rule("barrier_to_entry", "high",
          (r"\bpatent", r"proprietary", r"network effect", r"regulatory barrier"), 0.6),
    _Rule("has_ip_protection", "granted", (r"patent granted", r"granted patent", r"registered trademark"), 0.8),
    _Rule("has_ip_protection", "pending", (r"patent[- ]pending", r"patent application", r"\bpatent\b", r"\btrademark\b"), 0.6),
    _Rule("replicability", "automated", (r"fully automated", r"automated process", r"\bautomation\b"), 0.6),
    _Rule("geographic_potential", "global", (r"\bglobal\b", r"worldwide", r"international expansion"), 0.6),
    _Rule("energy_source", "solar_wind", (r"\bsolar\b", r"wind power", r"photovoltaic"), 0.7),
    _Rule("energy_source", "mixed_renewable_grid", (r"renewable energy", r"green energy", r"clean energy"), 0.55),
    _Rule("recycling_strategy", "full_circular", (r"circular economy", r"fully circular"), 0.7),
    _Rule("recycling_strategy", "active_program", (r"\brecycl",), 0.5),
)


def _context(text: str, start: int, end: int, window: int = 35) -> str:
    snippet = text[max(0, start - window): min(len(text), end + window)]
    return re.sub(r"\s+", " ", snippet).strip()


class RuleBasedExtractor:
    """Deterministic keyword/pattern extractor — no external dependencies."""

    def extract(self, text: str) -> list[AnswerSuggestion]:
        best: dict[str, AnswerSuggestion] = {}
        for rule in _RULES:
            for pattern in rule.patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if not match:
                    continue
                candidate = AnswerSuggestion(
                    key=rule.key,
                    suggested_value=rule.value,
                    confidence=rule.confidence,
                    evidence=_context(text, match.start(), match.end()),
                    source="rule",
                )
                if rule.key not in best or candidate.confidence > best[rule.key].confidence:
                    best[rule.key] = candidate
                break  # first matching pattern for this rule is enough
        return sorted(best.values(), key=lambda s: s.key)


async def extract_document_text(
    *, data: bytes, filename: str, content_type: str | None = None,
    registry: ExtractorRegistry | None = None,
) -> str:
    """Run the File Parser's extractor and return the document's plain text."""
    registry = registry or ExtractorRegistry()
    extractor = registry.resolve(filename=filename, content_type=content_type)
    raw = await extractor.extract(
        document_id="prefill", filename=filename,
        content_type=content_type or "", data=data,
    )
    parts = [block.text for block in raw.text_blocks]
    for table in raw.tables:
        for row in table.rows:
            parts.append(" ".join(cell for cell in row if cell))
    return "\n".join(parts)


def _values_match(answer: Any, suggested: Any) -> bool:
    if isinstance(suggested, bool):
        return _coerce_bool(answer) == suggested
    if isinstance(suggested, int):
        return _coerce_int(answer) == suggested
    return str(answer).strip().lower() == str(suggested).strip().lower()


class DocumentPrefillService:
    """Suggests answers from a document and verifies submitted answers against it."""

    def __init__(self, *, extractor: RuleBasedExtractor | None = None, llm_extractor=None) -> None:
        self._extractor = extractor or RuleBasedExtractor()
        self._llm_extractor = llm_extractor  # optional, structured-LLM; injected by caller

    def suggest_from_text(self, text: str) -> list[AnswerSuggestion]:
        suggestions = {s.key: s for s in self._extractor.extract(text)}
        # Only keep suggestions whose value is valid for that key's enum (if enumerated).
        valid: list[AnswerSuggestion] = []
        for key, suggestion in suggestions.items():
            spec = _SPEC_BY_KEY.get(key)
            if spec and spec.kind == "enum" and suggestion.suggested_value not in (spec.allowed or ()):
                continue
            valid.append(suggestion)
        return sorted(valid, key=lambda s: s.key)

    async def suggest_from_document(
        self, *, data: bytes, filename: str, content_type: str | None = None,
    ) -> list[AnswerSuggestion]:
        text = await extract_document_text(data=data, filename=filename, content_type=content_type)
        return self.suggest_from_text(text)

    def verify(
        self, *, answers: dict[str, Any], suggestions: list[AnswerSuggestion]
    ) -> list[Verification]:
        """Cross-check submitted answers against the document's suggestions."""
        results: list[Verification] = []
        for suggestion in suggestions:
            answered = answers.get(suggestion.key)
            if answered is None:
                status = "prefill"
            elif _values_match(answered, suggestion.suggested_value):
                status = "match"
            else:
                status = "mismatch"
            results.append(
                Verification(
                    key=suggestion.key,
                    answered_value=answered,
                    suggested_value=suggestion.suggested_value,
                    confidence=suggestion.confidence,
                    status=status,
                )
            )
        return results

    def prefilled_answers(
        self, *, answers: dict[str, Any], suggestions: list[AnswerSuggestion],
        min_confidence: float = 0.6,
    ) -> dict[str, Any]:
        """Fill unanswered keys with confident suggestions (founder can still override)."""
        merged = dict(answers)
        for suggestion in suggestions:
            if merged.get(suggestion.key) is None and suggestion.confidence >= min_confidence:
                merged[suggestion.key] = suggestion.suggested_value
        return merged
