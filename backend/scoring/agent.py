"""
MS2 scoring agent loop.

run_scoring_agent(diagnostic_answers) orchestrates the full pipeline:
  - Drives the LLM to call all 6 tools in the prescribed order
  - Executes each tool via the real deterministic functions (tools.execute_tool)
  - Enforces the detect_all_anomalies ordering guard at the code level
  - Parses the LLM's final JSON justification output
  - Merges deterministic tool numbers with the LLM language layer

The numeric scores always come from the tools. The LLM's only
contribution is the natural-language justification text.
"""
from __future__ import annotations

import json
import re

from scoring.system_prompt import SCORING_SYSTEM_PROMPT
from scoring.tools import TOOLS, execute_tool
from scoring.llm_client import run_agent_turn

_SCORE_TOOL_TO_DIM: dict[str, str] = {
    "compute_market_score":      "market",
    "compute_commercial_score":  "commercial",
    "compute_innovation_score":  "innovation",
    "compute_scalability_score": "scalability",
    "compute_green_score":       "green",
}

_ALL_DIMENSIONS = frozenset(_SCORE_TOOL_TO_DIM.values())

# 6 tool calls + 1 final response = 7 turns; ceiling of 12 absorbs any retries
_MAX_TURNS = 12


# ---------------------------------------------------------------------------
# JSON extraction helpers
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict | None:
    """
    Three-attempt JSON extraction:
      1. Direct parse of the trimmed text
      2. Strip markdown code fences (```json ... ```)
      3. Find the first { ... } spanning the full blob
    Returns None if all three fail.
    """
    text = (text or "").strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def _parse_final_response(
    text: str,
    messages: list[dict],
) -> dict:
    """
    Parse the agent's final JSON justification text.
    If malformed, re-prompts once asking for raw JSON only.
    Returns {} if both attempts fail — caller surfaces the gap.
    """
    parsed = _extract_json(text)
    if parsed is not None:
        return parsed

    retry_messages = messages + [
        {"role": "assistant", "content": text},
        {
            "role": "user",
            "content": (
                "Ta réponse n'est pas du JSON valide. "
                "Réponds UNIQUEMENT avec le JSON brut, sans markdown ni préambule. "
                "Utilise exactement le format demandé dans les instructions."
            ),
        },
    ]
    retry_turn = run_agent_turn(SCORING_SYSTEM_PROMPT, retry_messages, [])
    parsed = _extract_json(retry_turn.get("text") or "")
    return parsed if parsed is not None else {}


# ---------------------------------------------------------------------------
# Main agent loop
# ---------------------------------------------------------------------------

def run_scoring_agent(diagnostic_answers: dict) -> dict:
    """
    Run the full MS2 scoring agent for one project profile.

    Guardrails applied at the code level (double-enforcement with system prompt):
    - detect_all_anomalies is blocked until all 5 scoring tools have returned.
      A refused call returns an error message to the model; the model must call
      the missing scoring tools and retry detect_all_anomalies.

    Returns:
        {
            "scores":                 {<5 dimension results or error stubs>},
            "anomaly_flags":          [{code, message, severity}],
            "low_scoring_dimensions": [<names where composite < 50>],
            "green_pillars_flagged":  [<pillar names where score >= 3>],
            "justifications":         {<per-dimension text + improvement_action>},
            "anomaly_summary":        "<plain-French anomaly summary or ''>",
        }
    """
    all_scores: dict[str, dict] = {}
    anomaly_result: dict | None = None
    final_text = ""

    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                "Voici les réponses au questionnaire de diagnostic :\n\n"
                + json.dumps(diagnostic_answers, ensure_ascii=False, indent=2)
                + "\n\nÉvalue ce projet en appelant les outils dans l'ordre prescrit, "
                "puis fournis ta justification au format JSON."
            ),
        }
    ]

    for _turn in range(_MAX_TURNS):
        turn = run_agent_turn(SCORING_SYSTEM_PROMPT, messages, TOOLS)

        if not turn["tool_calls"]:
            # No more tool calls — this is the final JSON justification
            final_text = turn.get("text") or ""
            break

        # ---- Append assistant turn (OpenAI message format) ----
        messages.append({
            "role": "assistant",
            "content": turn.get("text"),   # None when the turn is tool-calls-only
            "tool_calls": [
                {
                    "id": tc["call_id"],
                    "type": "function",
                    "function": {
                        "name": tc["tool_name"],
                        "arguments": json.dumps(tc["tool_input"], ensure_ascii=False),
                    },
                }
                for tc in turn["tool_calls"]
            ],
        })

        # ---- Execute each requested tool call ----
        for tc in turn["tool_calls"]:
            tool_name  = tc["tool_name"]
            tool_input = tc["tool_input"]
            call_id    = tc["call_id"]

            # Code-level guard: reject detect_all_anomalies until all 5 scores exist
            if tool_name == "detect_all_anomalies":
                missing = _ALL_DIMENSIONS - set(all_scores.keys())
                if missing:
                    refused = {
                        "error": (
                            f"Appel refusé par le contrôleur de pipeline. "
                            f"Scores manquants : {sorted(missing)}. "
                            f"Appelle les outils correspondants, puis rappelle "
                            f"detect_all_anomalies."
                        )
                    }
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": json.dumps(refused, ensure_ascii=False),
                    })
                    continue
                # Model calls detect_all_anomalies with no args ({}).
                # Inject tracked state here so execute_tool gets a complete input.
                # This avoids passing the full score payload through the model's
                # function-call arguments, which can trip provider size limits.
                tool_input = {
                    "diagnostic_answers": diagnostic_answers,
                    "all_scores": all_scores,
                }

            # Execute the real deterministic function
            try:
                result = execute_tool(tool_name, tool_input)
            except ValueError as exc:
                result = {"error": str(exc)}

            # Track results
            if tool_name in _SCORE_TOOL_TO_DIM:
                all_scores[_SCORE_TOOL_TO_DIM[tool_name]] = result
            elif tool_name == "detect_all_anomalies":
                anomaly_result = result

            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    # ---- Parse the LLM's justification JSON ----
    justification_data = _parse_final_response(final_text, messages)

    # ---- Compute derived signals (mirrors engine.py) ----
    low_scoring = [
        name for name, score in all_scores.items()
        if score.get("composite") is not None and score["composite"] < 50
    ]

    green = all_scores.get("green", {})
    green_flagged = [
        pillar
        for pillar, data in green.get("pillars", {}).items()
        if data.get("score", 0) >= 3
    ]

    return {
        "scores":                 all_scores,
        "anomaly_flags":          (anomaly_result or {}).get("anomaly_flags", []),
        "low_scoring_dimensions": low_scoring,
        "green_pillars_flagged":  green_flagged,
        "justifications":         justification_data.get("justifications", {}),
        "anomaly_summary":        justification_data.get("anomaly_summary", ""),
    }
