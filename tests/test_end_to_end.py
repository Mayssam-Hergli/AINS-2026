"""End-to-end and contract tests for the platform.

Run with:  ``pytest -q``

These use the in-memory fake pool (`tests/fakepg.py`) so they need no Postgres and no
Anthropic key — they exercise the real parsing, diagnostic, scoring, and persistence
code, including the merge-safe `project_profiles` contract.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest

from services.common.exceptions import AnswerValidationError, DiagnosticNotReadyError
from services.ms1_diagnostic.engine import DiagnosticEngine, ProjectProfileRepository
from services.scoring_agent.agent import ScoringAgent
from services.scoring_agent.contracts import SCORE_KEYS, ScoreBand
from services.scoring_agent.repository import ScoreRepository
from tests.fakepg import InMemoryPool

from demo import run_demo


def _run(coro):
    return asyncio.run(coro)


def test_full_pipeline_demo():
    """The demo runs all four stages and produces the contract MS3 expects."""
    artifacts = _run(run_demo())
    score_set = artifacts["score_set"]
    pool = artifacts["pool"]

    # Exactly five score objects, in the fixed, documented order.
    assert tuple(s.key for s in score_set.scores) == SCORE_KEYS
    assert all(0.0 <= s.score <= 100.0 for s in score_set.scores)
    assert score_set.overall_band in set(ScoreBand)

    # Both columns are populated and MS1's data survived MS2's write.
    project_id = uuid.UUID(score_set.project_id)
    row = pool.store["profiles"][project_id]
    assert row["diagnostic_answers"] is not None
    assert row["scores"] is not None
    # Audit trails recorded for both stages.
    assert len(pool.store["ms1_history"]) == 1
    assert len(pool.store["ms2_history"]) == 1


def test_scoring_reads_ms1_and_writes_scores():
    """MS2 reads the diagnostic MS1 wrote and writes five scores back."""
    pool = InMemoryPool()
    pid, tid = uuid.uuid4(), uuid.uuid4()

    engine = DiagnosticEngine(repository=ProjectProfileRepository(pool))
    _run(engine.diagnose(
        project_id=pid, tenant_id=tid, persist=True,
        answers={"c_csrd_scope": True, "e_emissions_tracking": True, "g_ethics_policy": True},
        signals=[],
    ))

    agent = ScoringAgent(repository=ScoreRepository(pool))
    score_set = _run(agent.score_project(project_id=pid, tenant_id=tid, persist=True))

    stored = _run(ScoreRepository(pool).read_scores(pid))
    assert stored is not None
    assert [s["key"] for s in stored["scores"]] == list(SCORE_KEYS)
    assert score_set.diagnostic_schema_version == "ms1.diagnostic.v1"


def test_scoring_before_diagnostic_is_rejected():
    """MS2 refuses to score a project MS1 hasn't written yet (ordering)."""
    pool = InMemoryPool()
    agent = ScoringAgent(repository=ScoreRepository(pool))
    with pytest.raises(DiagnosticNotReadyError):
        _run(agent.score_project(project_id=uuid.uuid4(), persist=True))


def test_invalid_answers_rejected():
    """Malformed questionnaire answers are rejected before scoring."""
    engine = DiagnosticEngine()
    with pytest.raises(AnswerValidationError) as exc:
        _run(engine.diagnose(
            project_id=uuid.uuid4(), persist=False, signals=[],
            answers={"c_csrd_scope": "maybe", "c_esrs_datapoints": 99, "nope": 1},
        ))
    assert len(exc.value.issues) == 3


def test_band_differentiation():
    """The scorer spreads across bands given varied evidence/overclaim per domain."""
    diag = {
        "schema_version": "ms1.diagnostic.v1",
        "overall": {"score": 0.6, "maturity_level": 3},
        "questionnaire": {"coverage": 1.0},
        "domains": [
            {"domain": "environmental", "perceived_score": 0.85, "evidenced_score": 0.85,
             "gap": 0.0, "direction": "aligned", "maturity_level": 5},
            {"domain": "social", "perceived_score": 0.7, "evidenced_score": 0.3,
             "gap": 0.4, "direction": "overclaim", "maturity_level": 2},
            {"domain": "governance", "perceived_score": 0.65, "evidenced_score": 0.65,
             "gap": 0.0, "direction": "aligned", "maturity_level": 4},
            {"domain": "compliance", "perceived_score": 0.55, "evidenced_score": 0.5,
             "gap": 0.05, "direction": "aligned", "maturity_level": 3},
        ],
        "gap_report": {"overall_gap": 0.1, "domain_gaps": [
            {"domain": "environmental", "evidence_count": 6, "supporting_signal_ids": ["s1"]},
            {"domain": "social", "evidence_count": 1, "supporting_signal_ids": []},
            {"domain": "governance", "evidence_count": 4, "supporting_signal_ids": ["s3"]},
            {"domain": "compliance", "evidence_count": 3, "supporting_signal_ids": ["s4"]},
        ]},
        "blockers": [{"domain": "social", "title": "No diversity metrics",
                      "category": "data_gap", "priority": 82.0}],
        "evidence": {"signal_count": 14},
    }
    score_set = _run(ScoringAgent().score_project(
        project_id=uuid.uuid4(), diagnostic_answers=diag, persist=False))
    by_key = score_set.by_key()
    assert by_key["environmental"].band == ScoreBand.LEADING
    assert by_key["social"].band == ScoreBand.AT_RISK
    bands = {s.band for s in score_set.scores}
    assert len(bands) >= 3  # at least three distinct bands present
