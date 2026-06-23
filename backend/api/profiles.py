"""
Profile management routes.

MS1 (Diagnostic Engine) will own the diagnostic flow and call
PATCH /profiles/{id}/answers when a diagnostic is complete.
Until MS1 is integrated, the frontend stub diagnostic submits
answers through the same endpoint.
"""
import json
import sqlite3
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import get_db
from security.auth import get_current_user

router = APIRouter(prefix="/profiles", tags=["Profiles"])


class CreateProfile(BaseModel):
    name: str


class UpdateAnswers(BaseModel):
    diagnostic_answers: dict


# ---------------------------------------------------------------------------
# POST /profiles  — create a new project profile
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
def create_profile(
    body: CreateProfile,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    profile_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        """
        INSERT INTO project_profiles (id, user_id, name, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (profile_id, current_user["id"], body.name, now, now),
    )
    return {"id": profile_id, "name": body.name, "created_at": now}


# ---------------------------------------------------------------------------
# GET /profiles  — list all profiles owned by the current user
# ---------------------------------------------------------------------------

@router.get("")
def list_profiles(
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    rows = db.execute(
        """
        SELECT id, name, diagnostic_answers, market_score, created_at, updated_at
        FROM project_profiles
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (current_user["id"],),
    ).fetchall()
    return [_summary(r) for r in rows]


# ---------------------------------------------------------------------------
# GET /profiles/{profile_id}  — single profile (full row)
# ---------------------------------------------------------------------------

@router.get("/{profile_id}")
def get_profile(
    profile_id: str,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = db.execute(
        "SELECT * FROM project_profiles WHERE id = ? AND user_id = ?",
        (profile_id, current_user["id"]),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return dict(row)


# ---------------------------------------------------------------------------
# PATCH /profiles/{profile_id}/answers  — set diagnostic answers
# MS1 will call this endpoint when a diagnostic run completes.
# The frontend diagnostic stub calls it too.
# ---------------------------------------------------------------------------

@router.patch("/{profile_id}/answers")
def set_answers(
    profile_id: str,
    body: UpdateAnswers,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = db.execute(
        "SELECT id FROM project_profiles WHERE id = ? AND user_id = ?",
        (profile_id, current_user["id"]),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "UPDATE project_profiles SET diagnostic_answers = ?, updated_at = ? WHERE id = ?",
        (json.dumps(body.diagnostic_answers), now, profile_id),
    )
    return {"profile_id": profile_id, "status": "answers_saved"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _summary(row: sqlite3.Row) -> dict:
    has_answers = bool(row["diagnostic_answers"])
    has_scores = bool(row["market_score"])
    if has_scores:
        status = "scored"
    elif has_answers:
        status = "diagnostic_complete"
    else:
        status = "pending"
    return {
        "id": row["id"],
        "name": row["name"] or "Sans titre",
        "status": status,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
