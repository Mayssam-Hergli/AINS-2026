"""
Live integration tests for run_scoring_agent.

Requires GROQ_API_KEY in the environment (or .env file).
If not set, all tests are skipped with a clear message so the
deterministic suite (test_engine.py, test_tools.py, etc.) still
runs key-free.

Test 1 (critical): numeric scores from the agent must EXACTLY match
engine.compute_all_scores for the same input. The tool layer is
deterministic — any mismatch is an orchestration bug in agent.py or
llm_client.py, not a math error.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env before checking for the key
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
    )
    load_dotenv(_env_path)
except ImportError:
    pass

if not os.environ.get("GROQ_API_KEY"):
    print("SKIP  test_agent.py -- GROQ_API_KEY not set.")
    print("      To run live tests, add to backend/.env:")
    print("        GROQ_API_KEY=gsk_...")
    print("        LLM_PROVIDER=groq   (optional, groq is the default)")
    sys.exit(0)

from scoring.agent import run_scoring_agent
from scoring.engine import compute_all_scores

# -----------------------------------------------------------------------
# OVERCONFIDENT profile — same profile used in test_engine.py and
# test_tools.py. Expected deterministic values:
#   market=42.0 (LOW), commercial=82.0, innovation=100.0,
#   scalability=73.0, green=50.0
#   anomaly codes: [market_no_validation, scalability_manual_conflict,
#                   product_built_unvalidated]
# -----------------------------------------------------------------------
OVERCONFIDENT = {
    "market_size":               "very_large",
    "customer_interviews":       "0",
    "has_loi":                   0,
    "has_paying_customers":      False,
    "revenue_model_documented":  "draft",
    "revenue_model_type":        "undefined",
    "value_proposition_clarity": "differentiated",
    "product_maturity":          "product",
    "pricing_strategy":          "defined",
    "offer_need_alignment":      "none",
    "local_novelty":             "unique",
    "technology_intensity":      "high",
    "barrier_to_entry":          "high",
    "has_ip_protection":         "none",
    "replicability":             "automated",
    "manual_dependency":         "high",
    "geographic_potential":      "global",
    "energy_source":             "grid_steg",
    "energy_consumption":        "moderate",
    "transport_activity":        "regional",
    "water_volume":              "moderate",
    "water_origin":              "municipal_uncontrolled",
    "wastewater_treatment":      "partial_treatment",
    "zone_type":                 "rural_agricultural",
    "surface_impacted":          "medium",
    "ecosystem_disruption":      "moderate_reversible",
    "raw_material_consumption":  "moderate_partial",
    "waste_volume":              "moderate_partial",
    "recycling_strategy":        "partial",
}

# -----------------------------------------------------------------------
# Shared agent result — called once, reused across all three tests
# -----------------------------------------------------------------------
_AGENT_RESULT: dict | None = None


def _run_once() -> dict:
    global _AGENT_RESULT
    if _AGENT_RESULT is None:
        print("Calling Groq API (may take 15-30 seconds) ...")
        _AGENT_RESULT = run_scoring_agent(OVERCONFIDENT)
        print("API call complete.\n")
    return _AGENT_RESULT


# -----------------------------------------------------------------------
# Test 1 — Numeric consistency with engine.py  (THE CRITICAL TEST)
# Every composite and every anomaly code must be identical.
# If this fails, the agent is inventing or skipping tool calls.
# -----------------------------------------------------------------------
def test_scores_match_engine():
    agent_result  = _run_once()
    engine_result = compute_all_scores(OVERCONFIDENT)

    mismatches = []
    for dim in ("market", "commercial", "innovation", "scalability", "green"):
        agent_c  = agent_result["scores"].get(dim, {}).get("composite")
        engine_c = engine_result["scores"][dim]["composite"]
        if agent_c != engine_c:
            mismatches.append(f"  {dim}: agent={agent_c}, engine={engine_c}")

    assert not mismatches, (
        "Numeric scores diverged — agent did not use the tools faithfully:\n"
        + "\n".join(mismatches)
    )

    agent_codes  = sorted(f["code"] for f in agent_result["anomaly_flags"])
    engine_codes = sorted(f["code"] for f in engine_result["anomaly_flags"])
    assert agent_codes == engine_codes, (
        f"Anomaly codes differ: agent={agent_codes}, engine={engine_codes}"
    )

    print("PASS  Test 1 -- numeric consistency | agent == engine.py on all dimensions")
    for dim in ("market", "commercial", "innovation", "scalability", "green"):
        c = agent_result["scores"][dim]["composite"]
        print(f"        {dim}: {c}")
    print(f"      anomaly_flags: {agent_codes}")


# -----------------------------------------------------------------------
# Test 2 — Justifications present for all 5 dimensions
# Each must have a non-empty "text" field.
# -----------------------------------------------------------------------
def test_justifications_present():
    agent_result   = _run_once()
    justifications = agent_result.get("justifications", {})

    assert isinstance(justifications, dict), \
        f"justifications must be a dict, got {type(justifications).__name__}"

    for dim in ("market", "commercial", "innovation", "scalability", "green"):
        assert dim in justifications, \
            f"justifications missing '{dim}'. Keys: {list(justifications.keys())}"
        entry = justifications[dim]
        assert isinstance(entry, dict), \
            f"justifications['{dim}'] must be a dict, got {type(entry).__name__}"
        text = entry.get("text", "")
        assert isinstance(text, str) and len(text) > 20, \
            f"justifications['{dim}']['text'] too short or absent: {text!r}"

    print("PASS  Test 2 -- justifications present for all 5 dimensions")
    for dim in ("market", "commercial", "innovation", "scalability", "green"):
        preview = justifications[dim]["text"][:80].replace("\n", " ")
        print(f"        {dim}: {preview!r}")


# -----------------------------------------------------------------------
# Test 3 — Anomaly results correct, derived signals correct
# anomaly_flags must be non-empty and anomaly_summary non-empty
# (OVERCONFIDENT triggers 3 anomalies).
# low_scoring_dimensions and green_pillars_flagged must match engine.
# -----------------------------------------------------------------------
def test_anomaly_and_derived_signals():
    agent_result = _run_once()

    # anomaly_flags must exist — detect_all_anomalies must have been called
    assert agent_result["anomaly_flags"], \
        "anomaly_flags is empty — detect_all_anomalies may have been skipped"

    # anomaly_summary must be non-empty for a profile with 3 anomalies
    summary = agent_result.get("anomaly_summary", "")
    assert isinstance(summary, str) and len(summary) > 10, \
        f"anomaly_summary too short or absent: {summary!r}"

    # Derived signals must match engine.py values
    assert agent_result["low_scoring_dimensions"] == ["market"], (
        f"low_scoring_dimensions: expected ['market'], "
        f"got {agent_result['low_scoring_dimensions']}"
    )
    assert set(agent_result["green_pillars_flagged"]) == {
        "climat_air", "eau", "sols_biodiversite", "ressources_dechets"
    }, f"green_pillars_flagged: {agent_result['green_pillars_flagged']}"

    print("PASS  Test 3 -- anomaly results and derived signals")
    print(f"      anomaly_flags: {[f['code'] for f in agent_result['anomaly_flags']]}")
    print(f"      anomaly_summary: {summary[:100]!r}")
    print(f"      low_scoring: {agent_result['low_scoring_dimensions']}")
    print(f"      green_pillars: {agent_result['green_pillars_flagged']}")


if __name__ == "__main__":
    test_scores_match_engine()
    test_justifications_present()
    test_anomaly_and_derived_signals()
    print("\nAll agent tests passed.")
