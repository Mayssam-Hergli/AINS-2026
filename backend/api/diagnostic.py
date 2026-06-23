"""MS1 — Diagnostic API routes.

The diagnostic side of the platform: serves the questionnaire contract and writes the
validated 31-key answers into Supabase's "diagnostics.raw_responses" (JSONB), which
MS2's POST /scores/compute/{id} then reads.

  GET  /diagnostic/schema          → the 31-field contract (drives the founder form)
  POST /diagnostic/answers/{id}    → validate the answers + upsert the project's diagnostic row

The write is owner-protected (same auth as profiles/scoring) and validates against the
MS1 schema before storing, so MS2 never scores malformed input.

Same upsert behavior as api/profiles.py's PATCH /profiles/{id}/answers (this route and
that one are two entry points into the same diagnostics row — MS1 will eventually own
this one exclusively).
"""

import uuid
from datetime import datetime, timezone

import psycopg2.extensions
import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import get_db, db_cursor
from diagnostic.schema import (
    ANSWERS_SCHEMA_VERSION,
    FIELD_SPECS,
    build_diagnostic_answers,
    validate_answers,
)
from security.auth import get_current_user

router = APIRouter(prefix="/diagnostic", tags=["Diagnostic (MS1)"])


class AnswersIn(BaseModel):
    answers: dict


@router.get("/schema")
def get_schema():
    """The 31-field questionnaire contract — drives the founder form (no auth needed)."""
    return {
        "schema_version": ANSWERS_SCHEMA_VERSION,
        "fields": [
            {
                "key": s.key,
                "group": s.group,
                "type": s.kind,
                "options": list(s.allowed) if s.allowed else None,
                "required": s.required,
            }
            for s in FIELD_SPECS
        ],
    }


@router.post("/answers/{profile_id}")
def submit_answers(
    profile_id: str,
    body: AnswersIn,
    db: psycopg2.extensions.connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Validate the founder's answers and upsert the project's diagnostics row."""
    with db_cursor(db) as cur:
        cur.execute(
            "SELECT id FROM projects WHERE id = %s AND user_id = %s",
            (profile_id, current_user["id"]),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Profile not found")

        issues = validate_answers(body.answers)
        if issues:
            raise HTTPException(status_code=422, detail={"errors": issues})

        diagnostic_answers = build_diagnostic_answers(body.answers)
        now = datetime.now(timezone.utc)

        cur.execute(
            "SELECT id FROM diagnostics WHERE project_id = %s ORDER BY completed_at DESC NULLS LAST LIMIT 1",
            (profile_id,),
        )
        existing = cur.fetchone()

        if existing:
            cur.execute(
                "UPDATE diagnostics SET raw_responses = %s, completed_at = %s WHERE id = %s",
                (psycopg2.extras.Json(diagnostic_answers), now, existing["id"]),
            )
        else:
            cur.execute(
                "INSERT INTO diagnostics (id, project_id, raw_responses, completed_at) VALUES (%s, %s, %s, %s)",
                (str(uuid.uuid4()), profile_id, psycopg2.extras.Json(diagnostic_answers), now),
            )

    return {
        "profile_id": profile_id,
        "status": "answers_saved",
        "diagnostic_answers": diagnostic_answers,
    }
