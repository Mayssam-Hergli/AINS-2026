"""
MS3 — Roadmap generation logic, ported from MS3/backend/main.py and
adapted to read MS2's actual score shape instead of the placeholder
ScoringData/DiagnosticData shape MS3 was originally built against.

Adapter section below is the answer to "what does MS3 expect to read vs
what does MS2 actually write" — see build_diagnostic_data() and
build_scoring_data() docstrings for the exact mismatches and how each
field is derived instead of changing MS2's output.
"""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any

from rag.llm_client import call_llm_structured, call_llm_chat
from rag.retrieval import retrieve_chunks

ROADMAP_SCHEMA = {
    "type": "object",
    "properties": {
        "project_id": {"type": "string"},
        "generated_at": {"type": "string"},
        "maturity_stage": {"type": "string"},
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "order": {"type": "integer"},
                    "title": {"type": "string"},
                    "title_en_short": {"type": "string"},
                    "time_horizon": {"type": "string"},
                    "icon": {"type": "string","description": "e.g., clipboard-check, building-bank, target-arrow"},
                    "addresses": {
                       "type": "array",
                        "items": {"type": "string"},
                        "description": "Tableau contenant 2 à 3 IDs de la base de connaissances (ex: ['kb_0042', 'kb_0017'])"
                    },
                    "explanation": {
                        "type": "string", 
                        "description": "Explication approfondie: Pourquoi cette étape est cruciale, basée sur le diagnostic."
                    },
                    "resources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "source_id": {"type": "string"},
                                "title": {"type": "string"},
                                "type": {"type": "string"},
                                "link": {"type": "string"},
                                "downloadable": {"type": "boolean"},
                            },
                            "required": ["source_id", "title", "type", "link", "downloadable"],
                        },
                    },
                },
                "required": [
                    "id", "order", "title", "title_en_short", "time_horizon",
                    "icon", "addresses", "explanation", "resources",
                ],
            },
        },
    },
    "required": ["project_id", "generated_at", "maturity_stage", "steps"],
}
_SYSTEM_PROMPT = """
Tu es un conseiller expert en entrepreneuriat et innovation (spécialiste de l'écosystème tunisien : Startup Act, BFPME, APII, RNE).
Ta mission est de générer une feuille de route hyper-personnalisée en te basant STRICTEMENT sur le diagnostic de l'utilisateur.

RÈGLES DE GÉNÉRATION (À SUIVRE IMPÉRATIVEMENT) :

1. LANGUE ET TON :
   - Rédige l'intégralité du contenu en Français professionnel, clair et encourageant.
   - Ne donne jamais de conseils génériques (ex: "Trouver de l'argent"). Sois précis (ex: "Valider le modèle économique avant d'approcher la BFPME").

2. EXPLICATION CONTEXTUELLE (Le "Pourquoi") :
   - Dans le champ `description`, tu dois expliquer POURQUOI l'utilisateur doit faire cette étape en faisant référence à ses faiblesses détectées dans le diagnostic.
   - Exemple : "Le diagnostic montre un manque de preuve de traction. Cette étape comble cet écart avant toute démarche de financement."

3. RESSOURCES MULTIPLES :
   - Chaque étape DOIT faire référence à au moins 2 ressources de la base de connaissances (Knowledge Base) qui sont pertinentes.
   - Retourne uniquement les identifiants dans le tableau `referenced_kb_ids` (ex: "kb_0041").

4. HORIZON TEMPOREL STRICT :
   - Classe les étapes de manière chronologique logique.
   - Utilise EXCLUSIVEMENT les valeurs : "immediate", "short_term", ou "medium_term". N'invente pas de nouveaux horizons comme "Horizon 1".

5. ACTIONNABILE ET MESURABLE :
   - Le `title` doit commencer par un verbe d'action à l'infinitif (ex: "Valider", "Enregistrer", "Structurer", "Pivoter").
6. etapes doivent être concrètes et réalisables, pas des concepts abstraits et essaie de diviser les étapes trop longues en sous-étapes pour atteindre au moyen 5 à 7 étapes concrètes par feuille de route.
"""
PROGRESS_SCHEMA = {
    "type": "object",
    "properties": {
        "progress_score": {"type": "integer"},
        "reasoning": {"type": "string"},
        "momentum": {
            "type": "string",
            "enum": ["stagnant", "steady", "accelerating", "breakthrough"],
        },
    },
    "required": ["progress_score", "reasoning", "momentum"],
}

# The 6 maturity stages — confirmed against knowledge_base.json's
# stage_relevance vocabulary (Ideation, Market Validation, Structuration,
# Launch Planning, Growth, Fundraising) so retrieval tags line up exactly.
_STAGE_THRESHOLDS = (
    (30, "Ideation"),
    (50, "Market Validation"),
    (70, "Structuration"),
    (85, "Launch Planning"),
)

_ANOMALY_SEVERITY_TO_GAP_SEVERITY = {
    "high": "CRITICAL",
    "medium": "HIGH",
    "low": "MEDIUM",
}

_DIMENSION_DOMAIN = {
    "market": "market",
    "commercial": "market",
    "innovation": "innovation",
    "scalability": "organisational",
    "green": "environmental",
}


# ---------------------------------------------------------------------------
# Adapter: our diagnostic_answers + MS2 scores  ->  MS3's expected shapes
# ---------------------------------------------------------------------------

def LLM_chat(system_prompt: str, messages: list[dict], max_tokens: int = 1500, temperature: float = 0.4) -> str:
    """Provider-agnostic plain-text conversational call (used by /roadmap/chat)."""
    return call_llm_chat(system_prompt=system_prompt, messages=messages, max_tokens=max_tokens, temperature=temperature)

def derive_maturity_stage(scores: dict[str, Any], diagnostic_answers: dict[str, Any]) -> str:
    """
    MS1's classifier.py (the real "6-stage maturity classifier") is an
    empty stub — not implemented yet. This is a deterministic stand-in
    derived from the 5 real composite scores, so the pipeline isn't
    blocked on that module landing. Replace this function's body with a
    call into classifier.py the day it ships; callers (build_diagnostic_data)
    don't need to change.
    """
    composites = [
        s.get("composite") for s in scores.values()
        if isinstance(s, dict) and s.get("composite") is not None
    ]
    avg = mean(composites) if composites else 0
    stage = "Growth"
    for threshold, label in _STAGE_THRESHOLDS:
        if avg < threshold:
            stage = label
            break
    # Fundraising is cross-cutting in the KB's vocabulary, not strictly
    # above "Growth" — surface it when the founder has signaled active
    # fundraising regardless of where the composite average lands.
    if diagnostic_answers.get("has_pitch_deck") and diagnostic_answers.get("funding_needed"):
        stage = "Fundraising"
    return stage


def build_diagnostic_data(diagnostic_answers: dict[str, Any], anomaly_flags: list[dict]) -> dict:
    """
    MS3 expects `DiagnosticData = {project_metadata: {sector, current_stage,
    legal_form}, identified_gaps: [{gap_id, domain, description, severity}]}`.

    Mismatch: MS1's actual diagnostic_answers (backend/diagnostic/schema.py)
    is a flat 31-key questionnaire — it never collects `sector` or
    `legal_form`, and produces no narrative "gaps" list at all. Rather than
    inventing those fields:
      - sector / legal_form -> "Non renseigné" (honestly absent, not guessed)
      - current_stage       -> derive_maturity_stage() above
      - identified_gaps     -> derived from MS2's real anomaly_flags, which
                                DO carry a message + severity. This is a
                                real translation of real output, not
                                fabricated data.
    """
    gaps = []
    for flag in anomaly_flags:
        code = flag.get("code", "")
        domain = next(
            (d for dim, d in _DIMENSION_DOMAIN.items() if code.startswith(dim)),
            "organisational",
        )
        gaps.append({
            "gap_id": code,
            "domain": domain,
            "description": flag.get("message") or code,
            "severity": _ANOMALY_SEVERITY_TO_GAP_SEVERITY.get(flag.get("severity"), "MEDIUM"),
        })

    return {
        "project_metadata": {
            "sector": "Non renseigné",
            "current_stage": derive_maturity_stage({}, diagnostic_answers),
            "legal_form": "Non renseigné",
        },
        "identified_gaps": gaps,
    }


def build_scoring_data(scores: dict[str, Any], anomaly_flags: list[dict]) -> dict:
    """
    MS3 expects `ScoringData = {maturity_scores: {overall_score,
    financial_readiness, legal_compliance, technical_execution, market_fit},
    flags: {is_eligible_for_startup_act, requires_immediate_capital_injection}}`.

    Mismatch: MS2 produces 5 completely different dimensions (market,
    commercial, innovation, scalability, green) — none of which is named
    "legal_compliance" or "technical_execution". MS1 doesn't collect any
    legal data either (no incorporation status, no IP litigation, etc.),
    so "legal_compliance" has no real signal to draw from. Mapping used,
    documented rather than silently invented:
      - overall_score         = mean of the 5 real composites
      - financial_readiness   = mean(market, commercial)      — closest
                                 semantic match: revenue model + market validation
      - legal_compliance      = NOT MEASURED by current diagnostic/scoring.
                                 Defaulted to 50 (neutral) with a flag in
                                 the returned dict so callers can tell this
                                 apart from a real measurement.
      - technical_execution   = mean(innovation, scalability)  — closest
                                 match: technical capability + ability to execute
      - market_fit            = market composite directly (already MS2's
                                 closest equivalent concept)
      - is_eligible_for_startup_act       = heuristic proxy (innovation >= 50
                                             and no "high" severity anomaly) —
                                             NOT a legal determination
      - requires_immediate_capital_injection = market composite < 50 OR
                                             'market_no_validation' flagged
    """
    def comp(dim: str) -> float:
        return (scores.get(dim) or {}).get("composite") or 0

    composites = [comp(d) for d in ("market", "commercial", "innovation", "scalability", "green")]
    overall = mean(composites) if composites else 0
    financial_readiness = mean([comp("market"), comp("commercial")])
    technical_execution = mean([comp("innovation"), comp("scalability")])
    market_fit = comp("market")

    high_severity_codes = {f["code"] for f in anomaly_flags if f.get("severity") == "high"}

    return {
        "maturity_scores": {
            "overall_score": round(overall, 1),
            "financial_readiness": round(financial_readiness, 1),
            "legal_compliance": 50.0,  # not measured — see docstring
            "technical_execution": round(technical_execution, 1),
            "market_fit": round(market_fit, 1),
        },
        "flags": {
            "is_eligible_for_startup_act": comp("innovation") >= 50 and not high_severity_codes,
            "requires_immediate_capital_injection": comp("market") < 50 or "market_no_validation" in high_severity_codes,
        },
        "_unmeasured_fields": ["legal_compliance"],  # transparency, not part of MS3's schema
    }


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------




def generate_roadmap(
    profile_id: str,
    diagnostic_answers: dict[str, Any],
    scores: dict[str, Any],
    anomaly_flags: list[dict],
    low_scoring_dimensions: list[str],
) -> dict:
    """Full pipeline: adapt MS2/MS1 data -> retrieve real KB chunks -> call the LLM."""
    diagnostic_data = build_diagnostic_data(diagnostic_answers, anomaly_flags)
    scoring_data = build_scoring_data(scores, anomaly_flags)
    stage = diagnostic_data["project_metadata"]["current_stage"]

    chunks = retrieve_chunks(
        low_scoring_dimensions=low_scoring_dimensions,
        anomaly_codes=[f.get("code", "") for f in anomaly_flags],
        stage=stage,
    )

    user_prompt = f"""
    Execute roadmap building using these precise modules:

    1. DIAGNOSTIC INPUT:
    {diagnostic_data}

    2. SCORING INPUT:
    {scoring_data}

    3. RETRIEVED KNOWLEDGE BASE CHUNKS:
    {chunks}

    Construct the final JSON plan containing:
    - roadmap summary
    - sequential milestones grouped by Horizon 1 (immediate), 2 (short term), or 3 (medium term)
    - explicit map links using 'addresses.ref_id' and 'resources', citing only
      the kb_id values present in the retrieved chunks above.
    project_id = "{profile_id}"
    generated_at = "{datetime.now(timezone.utc).isoformat()}"
    maturity_stage = "{stage}"
    """

    try:
        structured = call_llm_structured(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema=ROADMAP_SCHEMA,
            tool_name="generate_roadmap_json",
            tool_description="Generates the final structured JSON roadmap.",
            max_tokens=5000,
            temperature=0.1,
        )
    except Exception:
        # Smaller/faster models (e.g. Groq's Llama) occasionally still drift
        # on the nested "addresses" object shape even with the example above.
        # One retry with a sharper correction note recovers most of the time
        # without paying for a slower/larger model on every call.
        structured = call_llm_structured(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt + '\n\nREMINDER: "addresses" must be a JSON OBJECT ({"type":..., "ref_id":..., "label":...}), NEVER an array. Your previous attempt failed schema validation on this exact field.',
            schema=ROADMAP_SCHEMA,
            tool_name="generate_roadmap_json",
            tool_description="Generates the final structured JSON roadmap.",
            max_tokens=5000,
            temperature=0.1,
        )

    structured = _coerce_addresses(structured)
    # Some providers occasionally drift on the literal fields we already
    # know deterministically — pin them rather than trusting the model.
    structured["project_id"] = profile_id
    structured["maturity_stage"] = stage
    return structured


def _coerce_addresses(roadmap: dict) -> dict:
    """Defensive normalization: if a step's "addresses" still comes back as
    a list despite the prompt + retry above, take the first element rather
    than failing the whole roadmap on one malformed field."""
    for step in roadmap.get("steps", []):
        addr = step.get("addresses")
        if isinstance(addr, list):
            step["addresses"] = addr[0] if addr else {"type": "gap", "ref_id": "", "label": ""}
    return roadmap


def evaluate_progress(latest_update: str, current_stage: str, previous_score: float | None, remaining_gaps: list[dict]) -> dict:
    system_prompt = """
    You are an expert startup evaluator for the Tunisian ecosystem.
    Your job is to evaluate the absolute progress of a startup project from 0 to 100.
    0 = Just an idea in the entrepreneur's head.
    100 = Fully funded, legally structured, and operational.

    Analyze the entrepreneur's current stage, their remaining gaps, and their latest action.
    Weigh the impact of their latest action heavily: administrative tasks add little progress,
    while proving market traction, securing legal status, or locking funding add massive progress.

    Return your evaluation using ONLY the provided structured tool.
    """
    user_prompt = f"""
    Evaluate the new progress score for this project.

    CURRENT STATUS:
    - Stage: {current_stage}
    - Previous Score: {previous_score if previous_score is not None else 'N/A (Initial Calculation)'}

    WHAT THE ENTREPRENEUR JUST DID:
    - {latest_update}

    REMAINING GAPS WEIGHING THE PROJECT DOWN:
    {remaining_gaps}
    """
    return call_llm_structured(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        schema=PROGRESS_SCHEMA,
        tool_name="record_progress_evaluation",
        tool_description="Records the evaluated progress score and reasoning.",
        max_tokens=1000,
        temperature=0.2,
    )


def contextual_chat(
    session_history: list[dict],
    new_message: str,
    sector: str,
    current_stage: str,
    key_weakness: str,
    component_title: str,
    component_description: str,
) -> str:
    system_prompt = f"""
    You are a highly helpful and expert startup advisor for the Tunisian ecosystem.
    You are directly assisting an entrepreneur in a contextual chat window.

    OVERALL PROJECT CONTEXT:
    - Sector: {sector}
    - Current Maturity Stage: {current_stage}
    - Key Vulnerabilities: {key_weakness}

    CURRENT FOCUS (What the user is looking at right now):
    - Component Title: {component_title}
    - Component Details: {component_description}

    RULES:
    - Keep answers concise, actionable, and encouraging.
    - Reference their specific sector or stage if it adds value.
    - If they ask a general question, gently bring it back to their current focus.
    """
    session_history.append({"role": "user", "content": new_message})
    reply = call_llm_chat(system_prompt=system_prompt, messages=session_history, max_tokens=1500, temperature=0.4)
    session_history.append({"role": "assistant", "content": reply})
    return reply
