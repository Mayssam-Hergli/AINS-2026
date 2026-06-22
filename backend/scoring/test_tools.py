import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.tools import TOOLS, execute_tool
from scoring.market import compute_market_score
from scoring.commercial import compute_commercial_score
from scoring.innovation import compute_innovation_score
from scoring.scalability import compute_scalability_score
from scoring.green import compute_green_score
from scoring.anomaly import detect_all_anomalies
from scoring.engine import compute_all_scores

# -----------------------------------------------------------------------
# Shared profiles
# -----------------------------------------------------------------------

# Complete profile used in tests 2 and 4
# Same as OVERCONFIDENT in test_engine.py — copied here so test_tools.py
# has no dependency on another test file.
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
# Test 1 — Schema shape validation
# Every tool in TOOLS must have name, description, and a valid input_schema
# with type="object" and a non-empty properties dict.
# detect_all_anomalies must declare diagnostic_answers and all_scores.
# -----------------------------------------------------------------------
def test_schema_shape():
    assert len(TOOLS) == 6, f"Expected 6 tools, got {len(TOOLS)}"

    tool_names = [t["name"] for t in TOOLS]
    expected_names = [
        "compute_market_score",
        "compute_commercial_score",
        "compute_innovation_score",
        "compute_scalability_score",
        "compute_green_score",
        "detect_all_anomalies",
    ]
    assert tool_names == expected_names, \
        f"Tool names/order: expected {expected_names}, got {tool_names}"

    for tool in TOOLS:
        name = tool["name"]
        assert isinstance(tool.get("description"), str) and len(tool["description"]) > 20, \
            f"{name}: missing or too-short description"
        schema = tool.get("input_schema", {})
        assert schema.get("type") == "object", \
            f"{name}: input_schema.type must be 'object'"
        assert "properties" in schema, \
            f"{name}: input_schema must have 'properties' key"
        assert "required" in schema, \
            f"{name}: input_schema must have 'required' key"
        # detect_all_anomalies intentionally has empty properties —
        # agent.py injects data from tracked state, not from model args
        if name != "detect_all_anomalies":
            assert len(schema["properties"]) > 0, \
                f"{name}: input_schema.properties must be non-empty"
            assert len(schema["required"]) > 0, \
                f"{name}: input_schema.required must be non-empty"

    # detect_all_anomalies takes no parameters from the model —
    # agent.py injects diagnostic_answers + all_scores from tracked state.
    anomaly_tool = next(t for t in TOOLS if t["name"] == "detect_all_anomalies")
    props = anomaly_tool["input_schema"]["properties"]
    assert props == {}, \
        f"detect_all_anomalies schema should have no properties, got: {list(props.keys())}"

    # detect_all_anomalies must be last (called after all 5 scores exist)
    assert TOOLS[-1]["name"] == "detect_all_anomalies", \
        "detect_all_anomalies must be the last tool in TOOLS"

    print(f"PASS  Test 1 — schema shape | {len(TOOLS)} tools, all valid")
    for t in TOOLS:
        n_props = len(t["input_schema"]["properties"])
        n_req   = len(t["input_schema"]["required"])
        print(f"        {t['name']}: {n_props} properties, {n_req} required")


# -----------------------------------------------------------------------
# Test 2 — execute_tool routing
# Each of the 6 tool names must dispatch to the right function and return
# the identical result as calling the function directly with the same input.
# -----------------------------------------------------------------------
def test_execute_tool_routing():
    answers = OVERCONFIDENT

    # 5 scoring tools — tool_input IS the answers dict
    routing_cases = [
        ("compute_market_score",      compute_market_score),
        ("compute_commercial_score",  compute_commercial_score),
        ("compute_innovation_score",  compute_innovation_score),
        ("compute_scalability_score", compute_scalability_score),
        ("compute_green_score",       compute_green_score),
    ]
    for tool_name, fn in routing_cases:
        via_tool   = execute_tool(tool_name, answers)
        direct     = fn(answers)
        assert via_tool == direct, \
            f"{tool_name}: execute_tool returned {via_tool}, direct call returned {direct}"
        print(f"      {tool_name}: composite={via_tool['composite']} [routes correctly]")

    # detect_all_anomalies — tool_input has diagnostic_answers + all_scores
    all_scores = {
        "market":      compute_market_score(answers),
        "commercial":  compute_commercial_score(answers),
        "innovation":  compute_innovation_score(answers),
        "scalability": compute_scalability_score(answers),
        "green":       compute_green_score(answers),
    }
    via_tool = execute_tool("detect_all_anomalies", {
        "diagnostic_answers": answers,
        "all_scores": all_scores,
    })
    direct = detect_all_anomalies(answers, all_scores)
    assert via_tool == direct, \
        f"detect_all_anomalies: execute_tool returned {via_tool}, direct returned {direct}"

    print(f"PASS  Test 2 — routing | all 6 tools route correctly")
    print(f"      anomaly flags: {[f['code'] for f in via_tool['anomaly_flags']]}")


# -----------------------------------------------------------------------
# Test 3 — detect_all_anomalies guard
# execute_tool must raise ValueError when all_scores is incomplete.
# It must also raise for unknown tool names.
# -----------------------------------------------------------------------
def test_anomaly_guard():
    # 3a — all_scores missing 3 dimensions
    try:
        execute_tool("detect_all_anomalies", {
            "diagnostic_answers": {},
            "all_scores": {"market": {}, "commercial": {}},
        })
        assert False, "Should have raised ValueError"
    except ValueError as exc:
        msg = str(exc)
        assert "Missing" in msg, f"Expected 'Missing' in error, got: {msg}"
        # The 3 missing dims should be named
        for dim in ("green", "innovation", "scalability"):
            assert dim in msg, f"Expected '{dim}' in error message, got: {msg}"
        print(f"PASS  Test 3a — guard fires for partial all_scores | {msg}")

    # 3b — all_scores key entirely absent
    try:
        execute_tool("detect_all_anomalies", {"diagnostic_answers": {}})
        assert False, "Should have raised ValueError"
    except ValueError as exc:
        msg = str(exc)
        assert "Missing" in msg, f"Expected 'Missing' in error, got: {msg}"
        print(f"PASS  Test 3b — guard fires when all_scores key absent | {msg[:60]}...")

    # 3c — unknown tool name
    try:
        execute_tool("invent_a_score", {})
        assert False, "Should have raised ValueError"
    except ValueError as exc:
        assert "Unknown tool" in str(exc), f"Expected 'Unknown tool', got: {exc}"
        print(f"PASS  Test 3c — unknown tool raises ValueError")


# -----------------------------------------------------------------------
# Test 4 — Tool layer consistency with engine.py
# Call all 6 tools through execute_tool, then compare every composite and
# every anomaly code against compute_all_scores() for the same input.
# This is the bridge test: if execute_tool is faithful to the underlying
# functions, and engine.py calls the same functions, they must agree exactly.
# -----------------------------------------------------------------------
def test_tool_layer_matches_engine():
    answers = OVERCONFIDENT

    # Step 1: call all 5 scoring tools through execute_tool
    all_scores: dict = {}
    for tool_name, dim in [
        ("compute_market_score",      "market"),
        ("compute_commercial_score",  "commercial"),
        ("compute_innovation_score",  "innovation"),
        ("compute_scalability_score", "scalability"),
        ("compute_green_score",       "green"),
    ]:
        all_scores[dim] = execute_tool(tool_name, answers)

    # Step 2: call anomaly detection through execute_tool
    anomaly_result = execute_tool("detect_all_anomalies", {
        "diagnostic_answers": answers,
        "all_scores": all_scores,
    })

    # Step 3: call the deterministic engine directly
    engine_result = compute_all_scores(answers)

    # Step 4: every composite must match exactly
    mismatches = []
    for dim in ("market", "commercial", "innovation", "scalability", "green"):
        tool_composite   = all_scores[dim]["composite"]
        engine_composite = engine_result["scores"][dim]["composite"]
        if tool_composite != engine_composite:
            mismatches.append(
                f"{dim}: tool={tool_composite}, engine={engine_composite}"
            )
    assert not mismatches, \
        f"Composite mismatches between tool layer and engine: {mismatches}"

    # Step 5: anomaly codes must match exactly (same order)
    tool_codes   = [f["code"] for f in anomaly_result["anomaly_flags"]]
    engine_codes = [f["code"] for f in engine_result["anomaly_flags"]]
    assert tool_codes == engine_codes, \
        f"Anomaly codes: tool={tool_codes}, engine={engine_codes}"

    print(f"PASS  Test 4 — consistency | tool layer == engine.py on all dimensions")
    for dim in ("market", "commercial", "innovation", "scalability", "green"):
        print(f"        {dim}: {all_scores[dim]['composite']} == {engine_result['scores'][dim]['composite']}")
    print(f"        anomaly codes match: {tool_codes}")


if __name__ == "__main__":
    test_schema_shape()
    test_execute_tool_routing()
    test_anomaly_guard()
    test_tool_layer_matches_engine()
    print("\nAll tools tests passed.")
