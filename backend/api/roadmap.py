"""
MS3 — Roadmap API routes, now backed by Supabase's normalized roadmap
tables (roadmaps -> roadmap_steps, chat_sessions -> chat_messages)
instead of a single JSON blob column.

  POST /roadmap/generate/{profile_id}   — build a roadmap from the
                                           project's latest diagnostic +
                                           scores, persist it normalized
  GET  /roadmap/{profile_id}            — read the latest roadmap back,
                                           joining roadmap_steps + knowledge_base
  POST /roadmap/chat                    — contextual chat, persisted in
                                           chat_sessions/chat_messages
  POST /roadmap/evaluate-progress       — progress score (see SCHEMA GAP below)

SCHEMA GAP, flagged rather than silently dropped: there is no
scores_history table in Supabase, so "previous_score" (the entrepreneur's
score before their latest action) has no source of truth — it's always
None here. The old SQLite version read scores_history for this. Ask your
teammate for a history table keyed on diagnostic_id if you want it back.

SCHEMA GAP #2: roadmap_steps.referenced_kb_id is a SINGLE FK, but a step
can legitimately cite multiple KB resources (our LLM output's resources[]
is a list). Only the first resource is stored as referenced_kb_id; the
rest are folded into the step's description text so nothing is silently
dropped. A roadmap_step_resources join table would fix this properly —
flagging it rather than guessing your teammate wants extra rows per step.

SCHEMA GAP #3: roadmap_steps.status has no documented enum/default —
defaulted to "pending" here; confirm the real allowed values.

Owner-protected throughout via a join through projects.user_id.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

import psycopg2.extensions
import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import get_db, db_cursor
from security.auth import get_current_user
from rag.roadmap import generate_roadmap, evaluate_progress, contextual_chat, derive_maturity_stage,LLM_chat

router = APIRouter(prefix="/roadmap", tags=["Roadmap (MS3)"])


DEFAULT_STEP_STATUS = "pending"  # see SCHEMA GAP #3 above


def _load_project_and_diagnostic(cur, profile_id: str, user_id: str):
    cur.execute(
        "SELECT id FROM projects WHERE id = %s AND user_id = %s",
        (profile_id, user_id),
    )
    if cur.fetchone() is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    cur.execute(
        """
        SELECT id AS diagnostic_id, raw_responses, scores
        FROM diagnostics
        WHERE project_id = %s
        ORDER BY completed_at DESC NULLS LAST
        LIMIT 1
        """,
        (profile_id,),
    )
    return cur.fetchone()


# ---------------------------------------------------------------------------
# POST /roadmap/generate/{profile_id}
# ---------------------------------------------------------------------------

@router.post("/generate/{profile_id}")
def generate(
    profile_id: str,
    db: psycopg2.extensions.connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    with db_cursor(db) as cur:
        diagnostic = _load_project_and_diagnostic(cur, profile_id, current_user["id"])

        if diagnostic is None or not diagnostic["raw_responses"]:
            raise HTTPException(status_code=400, detail="Profile has no diagnostic answers. Complete the diagnostic first.")
        if not diagnostic["scores"]:
            raise HTTPException(status_code=400, detail="Profile has no scores yet. POST /scores/compute/{profile_id} first.")

        diagnostic_answers = diagnostic["raw_responses"]
        bundle = diagnostic["scores"]
        scores = {
            "market": bundle.get("market"),
            "commercial": bundle.get("commercial"),
            "innovation": bundle.get("innovation"),
            "scalability": bundle.get("scalability"),
            "green": bundle.get("green"),
        }
        anomaly_flags = bundle.get("anomaly_flags", [])
        low_scoring_dimensions = bundle.get("low_scoring_dimensions", [])

        try:
            roadmap_json = generate_roadmap(
                profile_id=profile_id,
                diagnostic_answers=diagnostic_answers,
                scores=scores,
                anomaly_flags=anomaly_flags,
                low_scoring_dimensions=low_scoring_dimensions,
            )
            print(f"Generated roadmap for profile {profile_id}: {roadmap_json}")
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Roadmap generation failed: {exc}")
        print(f"Generated roadmap for profile {profile_id}: {roadmap_json}")
        roadmap_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO roadmaps (id, project_id, diagnostic_id, maturity_stage_snapshot, generated_at) VALUES (%s, %s, %s, %s, %s)",
            (roadmap_id, profile_id, diagnostic["diagnostic_id"], roadmap_json["maturity_stage"], datetime.now(timezone.utc)),
        )

        for step in roadmap_json.get("steps", []):
            # No more hacking the text together! The LLM now provides a clean array
            # of IDs, and a rich explanation inside the "description" field.
            
            kb_ids_array = step.get("addresses", [])
            if not isinstance(kb_ids_array, list):
                kb_ids_array = [kb_ids_array]  # Ensure it's a list

            cur.execute(
                """
                INSERT INTO roadmap_steps 
                    (id, roadmap_id, step_order, title, title_en_short, time_horizon, icon, description, status, referenced_kb_ids) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(uuid.uuid4()),
                    roadmap_id,
                    step.get("order"),      # Updated to match our new schema
                    step.get("title"),
                    step.get("title_en_short"),
                    step.get("time_horizon"),
                    step.get("icon"),            # Now saving the icon correctly!
                    step.get("explanation"),     # The rich AI explanation goes straight in
                    DEFAULT_STEP_STATUS,         # usually "pending"
                    kb_ids_array                 # Psycopg2 automatically converts this Python list to a PostgreSQL array!
                ),
            )

    return {"profile_id": profile_id, "status": "success", "data": roadmap_json}


# ---------------------------------------------------------------------------
# GET /roadmap/{profile_id}
# ---------------------------------------------------------------------------

@router.get("/{profile_id}")
def get_cached(
    profile_id: str,
    db: psycopg2.extensions.connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    with db_cursor(db) as cur:
        # 1. Verify project belongs to user
        cur.execute(
            "SELECT id FROM projects WHERE id = %s AND user_id = %s",
            (profile_id, current_user["id"]),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Profile not found")

        # 2. Get the latest roadmap for this project
        cur.execute(
            "SELECT id, maturity_stage_snapshot, generated_at FROM roadmaps WHERE project_id = %s ORDER BY generated_at DESC LIMIT 1",
            (profile_id,),
        )
        roadmap_row = cur.fetchone()
        if roadmap_row is None:
            raise HTTPException(status_code=404, detail="Roadmap not yet generated. POST /roadmap/generate/{profile_id} first.")

        # 3. Fetch steps and JOIN the knowledge base using the ANY() array operator.
        # Added rs.icon here!
        cur.execute(
            """
            SELECT rs.id AS step_id, rs.step_order, rs.title, rs.time_horizon, rs.icon, rs.description, rs.status,
                   kb.kb_id, kb.title AS kb_title, kb.type AS kb_type, kb.source_url
            FROM roadmap_steps rs
            LEFT JOIN knowledge_base kb ON kb.kb_id = ANY(rs.referenced_kb_ids)
            WHERE rs.roadmap_id = %s
            ORDER BY rs.step_order
            """,
            (roadmap_row["id"],),
        )
        step_rows = cur.fetchall()

        # 4. Fold the flat SQL rows back into a nested dictionary
        steps_dict = {}
        for row in step_rows:
            step_id = row["step_id"]
            
            # If we haven't seen this step yet, create its base structure
            if step_id not in steps_dict:
                steps_dict[step_id] = {
                    "id": step_id,
                    "order": row["step_order"],
                    "title": row["title"],
                    "time_horizon": row["time_horizon"],
                    "icon": row["icon"],
                    "explanation": row["description"], # Frontend looks for 'explanation' or 'description'
                    "status": row["status"],
                    "resources": []
                }
            
            # If there is a joined KB resource attached to this row, append it
            if row["kb_id"]:
                steps_dict[step_id]["resources"].append({
                    "source_id": row["kb_id"],
                    "title": row["kb_title"],
                    "type": row["kb_type"],
                    "link": row["source_url"]
                })

        # Convert the dictionary back to a list, sorted by step_order
        steps_list = sorted(list(steps_dict.values()), key=lambda x: x["order"])

        # 5. Return the clean, nested JSON
        return {
            "status": "success",
            "data": {
                "project_id": profile_id,
                "generated_at": roadmap_row["generated_at"],
                "maturity_stage": roadmap_row["maturity_stage_snapshot"],
                "steps": steps_list
            }
        }


# ---------------------------------------------------------------------------
# POST /roadmap/evaluate-progress
# ---------------------------------------------------------------------------

class ProgressPayload(BaseModel):
    profile_id: str
    latest_update: str


@router.post("/evaluate-progress")
def evaluate(
    payload: ProgressPayload,
    db: psycopg2.extensions.connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    with db_cursor(db) as cur:
        diagnostic = _load_project_and_diagnostic(cur, payload.profile_id, current_user["id"])

    diagnostic_answers = (diagnostic["raw_responses"] if diagnostic else None) or {}
    bundle = (diagnostic["scores"] if diagnostic else None) or {}
    scores = {k: bundle.get(k) for k in ("market", "commercial", "innovation", "scalability", "green")}
    anomaly_flags = bundle.get("anomaly_flags", [])

    current_stage = derive_maturity_stage(scores, diagnostic_answers)
    # No scores_history table in Supabase — see module docstring SCHEMA GAP.
    previous_score = None

    remaining_gaps = [
        {"domain": f.get("code"), "description": f.get("message", ""), "severity": f.get("severity", "medium")}
        for f in anomaly_flags
    ]

    try:
        result = evaluate_progress(payload.latest_update, current_stage, previous_score, remaining_gaps)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Progress evaluation failed: {exc}")

    return {"status": "success", "data": result}


# ---------------------------------------------------------------------------
# POST /roadmap/chat
# ---------------------------------------------------------------------------

class ComponentContext(BaseModel):
    title: str
    description: str
    step_id: Optional[str] = None


class ChatPayload(BaseModel):
    session_id: str
    profile_id: str
    clicked_component: ComponentContext
    new_message: str


@router.post("/chat")
def chat(
    payload: ChatPayload,
    db: psycopg2.extensions.connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    with db_cursor(db) as cur:
        diagnostic = _load_project_and_diagnostic(cur, payload.profile_id, current_user["id"])
        diagnostic_answers = (diagnostic["raw_responses"] if diagnostic else None) or {}
        bundle = (diagnostic["scores"] if diagnostic else None) or {}
        scores = {k: bundle.get(k) for k in ("market", "commercial", "innovation", "scalability", "green")}
        anomaly_flags = bundle.get("anomaly_flags", [])

        current_stage = derive_maturity_stage(scores, diagnostic_answers)
        key_weakness = anomaly_flags[0]["message"] if anomaly_flags else "Aucune faiblesse critique identifiée."

        # session_id from the client must be a UUID to satisfy chat_sessions.id —
        # create the row on first use, then replay prior messages for context.
        try:
            uuid.UUID(payload.session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="session_id must be a UUID")

        cur.execute("SELECT id FROM chat_sessions WHERE id = %s", (payload.session_id,))
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO chat_sessions (id, project_id, roadmap_step_id) VALUES (%s, %s, %s)",
                (payload.session_id, payload.profile_id, payload.clicked_component.step_id),
            )

        cur.execute(
            "SELECT role, content FROM chat_messages WHERE session_id = %s ORDER BY created_at",
            (payload.session_id,),
        )
        history: List[Dict[str, str]] = [dict(r) for r in cur.fetchall()]

        try:
            reply = contextual_chat(
                session_history=history,
                new_message=payload.new_message,
                sector="Non renseigné",
                current_stage=current_stage,
                key_weakness=key_weakness,
                component_title=payload.clicked_component.title,
                component_description=payload.clicked_component.description,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Chat failed: {exc}")

        now = datetime.now(timezone.utc)
        cur.execute(
            "INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (%s, %s, %s, %s)",
            (payload.session_id, "user", payload.new_message, now),
        )
        cur.execute(
            "INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (%s, %s, %s, %s)",
            (payload.session_id, "assistant", reply, now),
        )

    return {"status": "success", "data": {"reply": reply}}
class AskLLMRequest(BaseModel):
    profile_id: str
    question: str
@router.post("/ask-llm")
def ask_llm(
    payload: AskLLMRequest,
    db: psycopg2.extensions.connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    with db_cursor(db) as cur:
        diagnostic = _load_project_and_diagnostic(cur, payload.profile_id, current_user["id"])
        diagnostic_answers = (diagnostic["raw_responses"] if diagnostic else None) or {}
        bundle = (diagnostic["scores"] if diagnostic else None) or {}
        scores = {k: bundle.get(k) for k in ("market", "commercial", "innovation", "scalability", "green")}
        anomaly_flags = bundle.get("anomaly_flags", [])
        current_stage = derive_maturity_stage(scores, diagnostic_answers)
        key_weakness = anomaly_flags[0]["message"] if anomaly_flags else "Aucune faiblesse critique identifiée."
    try:
        reply = LLM_chat(
            system_prompt="You are a helpful assistant for entrepreneurs, providing advice based on their diagnostic answers and scores.my project have those {key_weakness} and my current maturity stage is {current_stage} and those anomaly flags {anomaly_flags}.",
            messages=[{"role": "user", "content": payload.question}],
            max_tokens=1500,
            temperature=0.4
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Chat failed: {exc}")
    return {"status": "success", "data": {"reply": reply}}
