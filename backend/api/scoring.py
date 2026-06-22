"""
MS2 Scoring API routes.

POST /scores/compute/{profile_id}
    Reads diagnostic_answers from project_profiles, runs the scoring agent,
    writes all 5 score objects + anomaly data back to project_profiles, and
    appends a row to scores_history. Returns the full payload immediately so
    the frontend can render without a second DB read.

GET /scores/{profile_id}
    Returns the already-computed scores from project_profiles without re-running
    the agent. Use this for page loads — never pays the LLM cost again.

Both routes are owner-protected: the WHERE clause includes user_id = current_user,
so a user can only access their own profiles.

Error contract:
- 400  profile has no diagnostic_answers
- 404  profile not found (or wrong owner)
- 502  agent failed OR agent returned no valid composites
        → in both 502 cases, NOTHING is written to the DB (atomic: all or nothing)
"""
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from database import get_db
from security.auth import get_current_user
from scoring.agent import run_scoring_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scores", tags=["Scoring"])

# ---------------------------------------------------------------------------
# POST /scores/compute/{profile_id}
# ---------------------------------------------------------------------------

@router.post("/compute/{profile_id}")
def compute_scores(
    profile_id: str,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Run the MS2 scoring agent for this profile.

    Expensive call (LLM): 30-60 s depending on provider.
    Only call this after the diagnostic is complete and diagnostic_answers
    have been written to project_profiles by MS1.
    """
    # 1. Validate UUID format
    try:
        uuid.UUID(profile_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid profile_id format")

    # 2. Fetch profile — user_id check baked into the query (no separate ownership check)
    row = db.execute(
        "SELECT * FROM project_profiles WHERE id = ? AND user_id = ?",
        (profile_id, current_user["id"]),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    # 3. Validate diagnostic_answers
    raw_answers = row["diagnostic_answers"]
    if not raw_answers:
        raise HTTPException(
            status_code=400,
            detail=(
                "Profile has no diagnostic_answers. "
                "Complete the MS1 diagnostic first."
            ),
        )
    try:
        diagnostic_answers = json.loads(raw_answers)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500, detail="Profile diagnostic_answers is not valid JSON"
        )
    if not diagnostic_answers:
        raise HTTPException(
            status_code=400,
            detail="Profile diagnostic_answers is empty. Complete the diagnostic first.",
        )

    # 4. Run the scoring agent (blocking; FastAPI runs sync routes in a thread pool)
    try:
        agent_result = run_scoring_agent(diagnostic_answers)
    except Exception as exc:
        logger.exception("Scoring agent failed for profile %s", profile_id)
        raise HTTPException(
            status_code=502,
            detail=f"Scoring agent failed: {exc}. No data was written.",
        )

    # 5. Guard: at least one valid composite must exist before we touch the DB
    scores = agent_result.get("scores", {})
    if not scores or not any(
        s.get("composite") is not None for s in scores.values()
    ):
        raise HTTPException(
            status_code=502,
            detail=(
                "Scoring agent returned no valid composite scores. "
                "No data was written."
            ),
        )

    # 6. Write atomically — sqlite3 connection is in a transaction via get_db()
    #    Either both the UPDATE and the INSERT succeed, or get_db() rolls back both.
    now = datetime.now(timezone.utc).isoformat()

    db.execute(
        """
        UPDATE project_profiles SET
            market_score           = ?,
            commercial_score       = ?,
            innovation_score       = ?,
            scalability_score      = ?,
            green_score            = ?,
            anomaly_flags          = ?,
            low_scoring_dimensions = ?,
            green_pillars_flagged  = ?,
            justifications         = ?,
            anomaly_summary        = ?,
            updated_at             = ?
        WHERE id = ?
        """,
        (
            json.dumps(scores.get("market")),
            json.dumps(scores.get("commercial")),
            json.dumps(scores.get("innovation")),
            json.dumps(scores.get("scalability")),
            json.dumps(scores.get("green")),
            json.dumps(agent_result.get("anomaly_flags", [])),
            json.dumps(agent_result.get("low_scoring_dimensions", [])),
            json.dumps(agent_result.get("green_pillars_flagged", [])),
            json.dumps(agent_result.get("justifications", {})),
            agent_result.get("anomaly_summary", ""),
            now,
            profile_id,
        ),
    )

    db.execute(
        """
        INSERT INTO scores_history
            (id, profile_id, market, commercial, innovation, scalability, green)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            profile_id,
            _composite(scores, "market"),
            _composite(scores, "commercial"),
            _composite(scores, "innovation"),
            _composite(scores, "scalability"),
            _composite(scores, "green"),
        ),
    )
    # Commit happens in get_db() when the dependency exits cleanly

    return {
        "profile_id": profile_id,
        "scores": scores,
        "anomaly_flags":          agent_result.get("anomaly_flags", []),
        "low_scoring_dimensions": agent_result.get("low_scoring_dimensions", []),
        "green_pillars_flagged":  agent_result.get("green_pillars_flagged", []),
        "justifications":         agent_result.get("justifications", {}),
        "anomaly_summary":        agent_result.get("anomaly_summary", ""),
    }


# ---------------------------------------------------------------------------
# GET /scores/{profile_id}
# ---------------------------------------------------------------------------

@router.get("/{profile_id}")
def get_scores(
    profile_id: str,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Return cached scores without re-running the agent.

    Returns 404 if the profile has never been scored yet —
    the caller should POST to /scores/compute/{profile_id} first.
    """
    try:
        uuid.UUID(profile_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid profile_id format")

    row = db.execute(
        "SELECT * FROM project_profiles WHERE id = ? AND user_id = ?",
        (profile_id, current_user["id"]),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    if row["market_score"] is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Scores not yet computed for this profile. "
                "POST to /scores/compute/{profile_id} first."
            ),
        )

    return {
        "profile_id": profile_id,
        "scores": {
            "market":      _parse_json(row["market_score"]),
            "commercial":  _parse_json(row["commercial_score"]),
            "innovation":  _parse_json(row["innovation_score"]),
            "scalability": _parse_json(row["scalability_score"]),
            "green":       _parse_json(row["green_score"]),
        },
        "anomaly_flags":          _parse_json(row["anomaly_flags"]) or [],
        "low_scoring_dimensions": _parse_json(row["low_scoring_dimensions"]) or [],
        "green_pillars_flagged":  _parse_json(row["green_pillars_flagged"]) or [],
        "justifications":         _parse_json(row["justifications"]) or {},
        "anomaly_summary":        row["anomaly_summary"] or "",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _composite(scores: dict, dim: str) -> float | None:
    return (scores.get(dim) or {}).get("composite")


def _parse_json(value: str | None):
    if value is None:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None
