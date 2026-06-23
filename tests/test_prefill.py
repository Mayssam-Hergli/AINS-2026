"""Tests for document-driven pre-fill & verification of the questionnaire."""

from __future__ import annotations

from services.ms1_diagnostic.answer_schema import _SPEC_BY_KEY
from services.ms1_diagnostic.prefill import DocumentPrefillService

DECK = """
GreenLoop Pitch Deck. Problem and solution.
A fully automated, AI-driven water recycling platform (circular economy).
Proprietary technology with a patent pending, running on solar power.
We interviewed 24 customers and signed 2 letters of intent.
We have paying customers generating recurring revenue (ARR).
Business model: SaaS subscription, pricing model defined at $499 / month.
Product is live and in production, validated for product-market fit.
Market opportunity: a $12 billion TAM with global expansion.
We are raising a Series A round.
"""


def test_suggestions_cover_expected_keys_with_valid_enums():
    svc = DocumentPrefillService()
    suggestions = {s.key: s for s in svc.suggest_from_text(DECK)}

    assert suggestions["funding_needed"].suggested_value == "series_a"
    assert suggestions["has_pitch_deck"].suggested_value is True
    assert suggestions["has_paying_customers"].suggested_value is True
    assert suggestions["energy_source"].suggested_value == "solar_wind"
    assert suggestions["market_size"].suggested_value == "very_large"
    assert suggestions["product_maturity"].suggested_value == "product"
    assert suggestions["has_ip_protection"].suggested_value == "pending"
    assert suggestions["revenue_model_type"].suggested_value == "subscription"

    # Every enum suggestion is a legal value for its key (won't break the contract).
    for key, s in suggestions.items():
        spec = _SPEC_BY_KEY[key]
        if spec.kind == "enum":
            assert s.suggested_value in spec.allowed
        # And carries supporting evidence.
        assert s.evidence


def test_verify_flags_mismatches_and_prefills():
    svc = DocumentPrefillService()
    suggestions = svc.suggest_from_text(DECK)
    answers = {
        "market_size": "small",          # deck says very_large
        "energy_source": "solar_wind",   # agrees
        # everything else blank
    }
    verifications = {v.key: v for v in svc.verify(answers=answers, suggestions=suggestions)}
    assert verifications["market_size"].status == "mismatch"
    assert verifications["energy_source"].status == "match"
    assert verifications["funding_needed"].status == "prefill"


def test_prefilled_answers_fills_confident_blanks_only():
    svc = DocumentPrefillService()
    suggestions = svc.suggest_from_text(DECK)
    answers = {"market_size": "small"}
    merged = svc.prefilled_answers(answers=answers, suggestions=suggestions, min_confidence=0.6)
    assert merged["market_size"] == "small"           # existing answer not overwritten
    assert merged["funding_needed"] == "series_a"     # confident blank filled
    assert "energy_source" in merged
