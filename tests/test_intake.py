"""Tests for the MS1 intake — the diagnostic_answers contract MS2 reads."""

from __future__ import annotations

import asyncio
import uuid

import pytest

from services.common.exceptions import AnswerValidationError
from services.ms1_diagnostic.answer_schema import (
    ALL_KEYS,
    REQUIRED_KEYS,
    build_diagnostic_answers,
    validate_answers,
)
from services.ms1_diagnostic.intake import AnswerRepository, IntakeService
from tests.fakepg import InMemoryPool


def _run(coro):
    return asyncio.run(coro)


# A complete, valid founder submission (every required key answered).
VALID_ANSWERS = {
    "market_size": "large",
    "customer_interviews": "6-10",
    "has_loi": 1,
    "has_paying_customers": True,
    "revenue_model_documented": "documented",
    "revenue_model_type": "saas",
    "value_proposition_clarity": "differentiated",
    "product_maturity": "mvp",
    "pricing_strategy": "defined",
    "offer_need_alignment": "validated",
    "local_novelty": "new",
    "technology_intensity": "high",
    "barrier_to_entry": "medium",
    "has_ip_protection": "pending",
    "replicability": "semi_auto",
    "manual_dependency": "low",
    "geographic_potential": "regional",
    "energy_source": "mixed_renewable_grid",
    "energy_consumption": "moderate",
    "transport_activity": "regional",
    "water_volume": "low_controlled",
    "water_origin": "municipal_controlled",
    "wastewater_treatment": "partial_treatment",
    "zone_type": "urban_industrial",
    "surface_impacted": "small",
    "ecosystem_disruption": "negligible",
    "raw_material_consumption": "low_recycled",
    "waste_volume": "low_managed",
    "recycling_strategy": "active_program",
    "has_pitch_deck": True,
    "funding_needed": "seed",
}


def test_valid_submission_has_every_contract_key():
    assert validate_answers(VALID_ANSWERS) == []
    payload = build_diagnostic_answers(VALID_ANSWERS)
    # MS2 reads keys directly — all of them must be present.
    assert set(payload) == set(ALL_KEYS)
    assert payload["has_loi"] == 1 and isinstance(payload["has_loi"], int)
    assert payload["has_paying_customers"] is True


def test_optional_keys_get_defaults_when_absent():
    answers = {k: v for k, v in VALID_ANSWERS.items()
               if k not in ("has_ip_protection", "revenue_model_type",
                            "has_pitch_deck", "funding_needed")}
    assert validate_answers(answers) == []  # optional keys aren't required
    payload = build_diagnostic_answers(answers)
    assert payload["has_ip_protection"] == "none"
    assert payload["revenue_model_type"] == "undefined"
    assert payload["has_pitch_deck"] is False
    assert payload["funding_needed"] == ""
    assert set(payload) == set(ALL_KEYS)  # defaults fill every key


def test_invalid_values_and_missing_required_are_rejected():
    bad = dict(VALID_ANSWERS)
    bad["market_size"] = "huge"          # not a valid enum
    bad["has_loi"] = 5                    # out of {0,1,2}
    del bad["energy_source"]              # required, now missing
    issues = validate_answers(bad)
    assert any("market_size" in i for i in issues)
    assert any("has_loi" in i for i in issues)
    assert any("energy_source" in i for i in issues)


def test_intake_service_persists_and_round_trips():
    pool = InMemoryPool()
    repo = AnswerRepository(pool)
    _run(repo.ensure_schema())
    service = IntakeService(repository=repo)

    pid, tid = uuid.uuid4(), uuid.uuid4()
    payload = _run(service.submit(
        project_id=pid, answers=VALID_ANSWERS, tenant_id=tid, persist=True))

    # Exactly the contract keys were written.
    assert set(payload) == set(ALL_KEYS)
    stored = _run(repo.read_answers(pid))
    assert stored is not None
    assert all(k in stored for k in REQUIRED_KEYS)
    assert stored["market_size"] == "large"
    # Audit history recorded.
    assert len(pool.store.get("answers_history", [])) == 1


def test_intake_service_rejects_bad_submission():
    service = IntakeService()  # no repo needed; validation happens first
    with pytest.raises(AnswerValidationError) as exc:
        _run(service.submit(
            project_id=uuid.uuid4(), persist=False,
            answers={"market_size": "large"},  # almost everything missing
        ))
    assert len(exc.value.issues) >= 20  # most required keys missing
