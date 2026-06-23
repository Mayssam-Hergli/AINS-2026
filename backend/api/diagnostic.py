"""MS1 — Diagnostic API routes.

The diagnostic side of the platform: serves the questionnaire contract and writes the
validated 31-key `diagnostic_answers` into project_profiles, which MS2's
POST /scores/compute/{id} then reads.

  GET  /diagnostic/schema          → the 31-field contract (drives the founder form)
  POST /diagnostic/answers/{id}    → validate the answers + write diagnostic_answers

The write is owner-protected (same auth as profiles/scoring) and validates against the
MS1 schema before storing, so MS2 never scores malformed input. It writes only the
`diagnostic_answers` column — the score columns belong to MS2.
"""

import json
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import get_db
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
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Validate the founder's answers and write the flat 31-key diagnostic_answers."""
    row = db.execute(
        "SELECT id FROM project_profiles WHERE id = ? AND user_id = ?",
        (profile_id, current_user["id"]),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    issues = validate_answers(body.answers)
    if issues:
        raise HTTPException(status_code=422, detail={"errors": issues})

    diagnostic_answers = build_diagnostic_answers(body.answers)
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "UPDATE project_profiles SET diagnostic_answers = ?, updated_at = ? WHERE id = ?",
        (json.dumps(diagnostic_answers), now, profile_id),
    )
    return {
        "profile_id": profile_id,
        "status": "answers_saved",
        "diagnostic_answers": diagnostic_answers,
    }
