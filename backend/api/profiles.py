"""
Profile (project) management routes — now backed by Supabase's normalized
schema: "projects" (one row per founder project) + "diagnostics" (one row
per diagnostic run, holding raw_responses/scores JSONB).

SCHEMA MISMATCH, flagged rather than worked around silently: "projects"
has no created_at/updated_at column. The previous SQLite project_profiles
table did, and the frontend's dashboard sorts/displays by creation date.
Until that column is added, list_profiles() can't order by recency and
returns created_at: None — see the docstring on list_profiles().
"""
import uuid
from datetime import datetime, timezone

import psycopg2.extensions
import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import get_db, db_cursor
from security.auth import get_current_user

router = APIRouter(prefix="/profiles", tags=["Profiles"])


class CreateProfile(BaseModel):
    name: str
    sector: str | None = None
    description: str | None = None


class UpdateAnswers(BaseModel):
    diagnostic_answers: dict


# ---------------------------------------------------------------------------
# POST /profiles  — create a new project
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
def create_profile(
    body: CreateProfile,
    db: psycopg2.extensions.connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    profile_id = str(uuid.uuid4())
    with db_cursor(db) as cur:
        cur.execute(
            "INSERT INTO projects (id, user_id, name, sector, description) VALUES (%s, %s, %s, %s, %s)",
            (profile_id, current_user["id"], body.name, body.sector, body.description),
        )
    return {"id": profile_id, "name": body.name}


# ---------------------------------------------------------------------------
# GET /profiles  — list all projects owned by the current user
# ---------------------------------------------------------------------------

@router.get("")
def list_profiles(
    db: psycopg2.extensions.connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    NOTE: "projects" has no created_at column, so this can't sort by
    recency like the old SQLite version did — ordered by id instead.
    Each project's most recent diagnostic (if any) is pulled via a
    LATERAL join to derive status (pending / diagnostic_complete / scored).
    """
    with db_cursor(db) as cur:
        cur.execute(
            """
            SELECT p.id, p.name,
                   d.raw_responses, d.scores
            FROM projects p
            LEFT JOIN LATERAL (
                SELECT raw_responses, scores
                FROM diagnostics
                WHERE diagnostics.project_id = p.id
                ORDER BY completed_at DESC NULLS LAST
                LIMIT 1
            ) d ON true
            WHERE p.user_id = %s
            ORDER BY p.id
            """,
            (current_user["id"],),
        )
        rows = cur.fetchall()
    return [_summary(r) for r in rows]


# ---------------------------------------------------------------------------
# GET /profiles/{profile_id}  — single project (full row)
# ---------------------------------------------------------------------------

@router.get("/{profile_id}")
def get_profile(
    profile_id: str,
    db: psycopg2.extensions.connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    with db_cursor(db) as cur:
        cur.execute(
            "SELECT * FROM projects WHERE id = %s AND user_id = %s",
            (profile_id, current_user["id"]),
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return dict(row)


# ---------------------------------------------------------------------------
# PATCH /profiles/{profile_id}/answers  — upsert the project's diagnostic
# ---------------------------------------------------------------------------

@router.patch("/{profile_id}/answers")
def set_answers(
    profile_id: str,
    body: UpdateAnswers,
    db: psycopg2.extensions.connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    with db_cursor(db) as cur:
        cur.execute(
            "SELECT id FROM projects WHERE id = %s AND user_id = %s",
            (profile_id, current_user["id"]),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Profile not found")

        now = datetime.now(timezone.utc)
        cur.execute(
            "SELECT id FROM diagnostics WHERE project_id = %s ORDER BY completed_at DESC NULLS LAST LIMIT 1",
            (profile_id,),
        )
        existing = cur.fetchone()

        if existing:
            cur.execute(
                "UPDATE diagnostics SET raw_responses = %s, completed_at = %s WHERE id = %s",
                (psycopg2.extras.Json(body.diagnostic_answers), now, existing["id"]),
            )
        else:
            cur.execute(
                "INSERT INTO diagnostics (id, project_id, raw_responses, completed_at) VALUES (%s, %s, %s, %s)",
                (str(uuid.uuid4()), profile_id, psycopg2.extras.Json(body.diagnostic_answers), now),
            )

    return {"profile_id": profile_id, "status": "answers_saved"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _summary(row: dict) -> dict:
    has_answers = bool(row["raw_responses"])
    has_scores = bool(row["scores"])
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
        "created_at": None,  # "projects" has no created_at column — see module docstring
    }
