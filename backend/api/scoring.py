"""
MS2 Scoring API routes — now backed by Supabase's "diagnostics" table
instead of SQLite's "project_profiles". The scoring engine itself
(scoring/agent.py, scoring/engine.py, etc.) is UNTOUCHED — only how this
route reads diagnostic answers and writes results changed.

POST /scores/compute/{profile_id}
    Reads diagnostics.raw_responses (JSONB) for the project's most recent
    diagnostic row, runs the scoring agent unchanged, writes the full
    result bundle into diagnostics.scores (JSONB) on that same row, plus
    a derived diagnostics.maturity_stage and diagnostics.key_weaknesses.

GET /scores/{profile_id}
    Returns the cached bundle from diagnostics.scores without re-running
    the agent.

SCHEMA GAP, flagged rather than silently dropped: Supabase's schema has
no "scores_history" table (SQLite's project_profiles had one, tracking
score evolution over time, read by /roadmap/evaluate-progress for
"previous_score"). Every POST /scores/compute now overwrites the single
diagnostics.scores value — there is no longer any history to look back
at. If you want that back, ask your teammate for a scores_history table
keyed on diagnostic_id; nothing here invents one.

Both routes are owner-protected via a join through projects.user_id.

Error contract (unchanged):
- 400  no diagnostic / no raw_responses yet
- 404  profile not found (or wrong owner)
- 502  agent failed OR agent returned no valid composites
        → in both 502 cases, NOTHING is written to the DB
"""
import logging
import uuid

import psycopg2.extensions
import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException

from database import get_db, db_cursor
from security.auth import get_current_user
from scoring.agent import run_scoring_agent
from rag.roadmap import derive_maturity_stage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scores", tags=["Scoring"])


def _load_latest_diagnostic(cur, profile_id: str, user_id: str):
    """Owner-checked fetch of the project's most recent diagnostic row."""
    cur.execute(
        """
        SELECT d.id AS diagnostic_id, d.raw_responses, d.scores
        FROM diagnostics d
        JOIN projects p ON p.id = d.project_id
        WHERE d.project_id = %s AND p.user_id = %s
        ORDER BY d.completed_at DESC NULLS LAST
        LIMIT 1
        """,
        (profile_id, user_id),
    )
    return cur.fetchone()


# ---------------------------------------------------------------------------
# POST /scores/compute/{profile_id}
# ---------------------------------------------------------------------------

@router.post("/compute/{profile_id}")
def compute_scores(
    profile_id: str,
    db: psycopg2.extensions.connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Run the MS2 scoring agent for this project.

    Expensive call (LLM): 30-60 s depending on provider.
    Only call this after the diagnostic is complete and raw_responses have
    been written to diagnostics by MS1.
    """
    try:
        uuid.UUID(profile_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid profile_id format")

    with db_cursor(db) as cur:
        # Ownership check first — projects must exist and belong to this user,
        # independent of whether a diagnostic row exists yet.
        cur.execute(
            "SELECT id FROM projects WHERE id = %s AND user_id = %s",
            (profile_id, current_user["id"]),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Profile not found")

        diagnostic = _load_latest_diagnostic(cur, profile_id, current_user["id"])

    if diagnostic is None or not diagnostic["raw_responses"]:
        raise HTTPException(
            status_code=400,
            detail="Profile has no diagnostic answers. Complete the MS1 diagnostic first.",
        )

    diagnostic_answers = diagnostic["raw_responses"]  # psycopg2 decodes JSONB to dict already
    if not diagnostic_answers:
        raise HTTPException(
            status_code=400,
            detail="Profile diagnostic answers are empty. Complete the diagnostic first.",
        )

    # Run the scoring agent (blocking; FastAPI runs sync routes in a thread pool) — UNCHANGED
    try:
        agent_result = run_scoring_agent(diagnostic_answers)
    except Exception as exc:
        logger.exception("Scoring agent failed for profile %s", profile_id)
        raise HTTPException(
            status_code=502,
            detail=f"Scoring agent failed: {exc}. No data was written.",
        )

    scores = agent_result.get("scores", {})
    if not scores or not any(s.get("composite") is not None for s in scores.values()):
        raise HTTPException(
            status_code=502,
            detail="Scoring agent returned no valid composite scores. No data was written.",
        )

    scores_bundle = {
        **scores,
        "anomaly_flags": agent_result.get("anomaly_flags", []),
        "low_scoring_dimensions": agent_result.get("low_scoring_dimensions", []),
        "green_pillars_flagged": agent_result.get("green_pillars_flagged", []),
        "justifications": agent_result.get("justifications", {}),
        "anomaly_summary": agent_result.get("anomaly_summary", ""),
    }
    maturity_stage = derive_maturity_stage(scores, diagnostic_answers)
    # "key_weaknesses" has no declared type in the schema given — assumed TEXT,
    # storing the anomaly summary sentence. If it's actually an array column,
    # this insert will fail; tell your teammate which type it really is.
    key_weaknesses = agent_result.get("anomaly_summary") or None

    with db_cursor(db) as cur:
        cur.execute(
            "UPDATE diagnostics SET scores = %s, maturity_stage = %s, key_weaknesses = %s WHERE id = %s",
            (psycopg2.extras.Json(scores_bundle), maturity_stage, key_weaknesses, diagnostic["diagnostic_id"]),
        )

    return {
        "profile_id": profile_id,
        "scores": scores,
        "anomaly_flags": agent_result.get("anomaly_flags", []),
        "low_scoring_dimensions": agent_result.get("low_scoring_dimensions", []),
        "green_pillars_flagged": agent_result.get("green_pillars_flagged", []),
        "justifications": agent_result.get("justifications", {}),
        "anomaly_summary": agent_result.get("anomaly_summary", ""),
    }


# ---------------------------------------------------------------------------
# GET /scores/{profile_id}
# ---------------------------------------------------------------------------

@router.get("/{profile_id}")
def get_scores(
    profile_id: str,
    db: psycopg2.extensions.connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return cached scores without re-running the agent."""
    try:
        uuid.UUID(profile_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid profile_id format")

    with db_cursor(db) as cur:
        diagnostic = _load_latest_diagnostic(cur, profile_id, current_user["id"])

    if diagnostic is None:
        raise HTTPException(status_code=404, detail="Profile not found or has no diagnostic yet")

    bundle = diagnostic["scores"]
    if not bundle:
        raise HTTPException(
            status_code=404,
            detail="Scores not yet computed for this profile. POST to /scores/compute/{profile_id} first.",
        )

    return {
        "profile_id": profile_id,
        "scores": {
            "market": bundle.get("market"),
            "commercial": bundle.get("commercial"),
            "innovation": bundle.get("innovation"),
            "scalability": bundle.get("scalability"),
            "green": bundle.get("green"),
        },
        "anomaly_flags": bundle.get("anomaly_flags", []),
        "low_scoring_dimensions": bundle.get("low_scoring_dimensions", []),
        "green_pillars_flagged": bundle.get("green_pillars_flagged", []),
        "justifications": bundle.get("justifications", {}),
        "anomaly_summary": bundle.get("anomaly_summary", ""),
    }
