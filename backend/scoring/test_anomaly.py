import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.anomaly import detect_all_anomalies

# ---------------------------------------------------------------------------
# Minimal score stubs — only populate fields each check actually reads
# ---------------------------------------------------------------------------
_EMPTY_SCORES = {"market": {}, "commercial": {}, "innovation": {}, "scalability": {}, "green": {}}

def _green_stub(undp_raw_total: float) -> dict:
    return {**_EMPTY_SCORES, "green": {"undp_raw_total": undp_raw_total}}


# ---------------------------------------------------------------------------
# Test 1a — market_no_validation fires when market_size large + zero validation
# ---------------------------------------------------------------------------
def test_market_no_validation_fires():
    answers = {
        "market_size": "large",
        "customer_interviews": "0",
        "has_paying_customers": False,
        "revenue_model_documented": "draft",  # not documented — keeps (b) silent
        "has_loi": 0,
    }
    r = detect_all_anomalies(answers, _EMPTY_SCORES)
    codes = [f["code"] for f in r["anomaly_flags"]]
    assert "market_no_validation" in codes, f"expected flag market_no_validation, got: {codes}"
    flag = next(f for f in r["anomaly_flags"] if f["code"] == "market_no_validation")
    assert flag["severity"] == "high", f"expected severity=high, got {flag['severity']}"
    print(f"PASS  Test 1a — market_no_validation fires | flags: {codes}")


def test_market_no_validation_silent_when_small():
    answers = {
        "market_size": "small",
        "customer_interviews": "0",
        "has_paying_customers": False,
        "revenue_model_documented": "none",
        "has_loi": 0,
    }
    r = detect_all_anomalies(answers, _EMPTY_SCORES)
    codes = [f["code"] for f in r["anomaly_flags"]]
    assert "market_no_validation" not in codes, f"unexpected flag: {codes}"
    print(f"PASS  Test 1b — market_no_validation silent for small market")


def test_market_no_validation_silent_when_paying():
    answers = {
        "market_size": "very_large",
        "customer_interviews": "0",
        "has_paying_customers": True,   # has paying customers → no flag
        "revenue_model_documented": "none",
        "has_loi": 0,
    }
    r = detect_all_anomalies(answers, _EMPTY_SCORES)
    codes = [f["code"] for f in r["anomaly_flags"]]
    assert "market_no_validation" not in codes, f"unexpected flag: {codes}"
    print(f"PASS  Test 1c — market_no_validation silent when paying customers exist")


# ---------------------------------------------------------------------------
# Test 2a — revenue_no_clients fires when documented + no paying + no LOI
# ---------------------------------------------------------------------------
def test_revenue_no_clients_fires():
    answers = {
        "market_size": "small",        # keeps (a) silent
        "customer_interviews": "0",
        "has_paying_customers": False,
        "revenue_model_documented": "documented",
        "has_loi": 0,
    }
    r = detect_all_anomalies(answers, _EMPTY_SCORES)
    codes = [f["code"] for f in r["anomaly_flags"]]
    assert "revenue_no_clients" in codes, f"expected flag revenue_no_clients, got: {codes}"
    flag = next(f for f in r["anomaly_flags"] if f["code"] == "revenue_no_clients")
    assert flag["severity"] == "high"
    print(f"PASS  Test 2a — revenue_no_clients fires | flags: {codes}")


def test_revenue_no_clients_silent_when_loi_present():
    answers = {
        "market_size": "small",
        "customer_interviews": "0",
        "has_paying_customers": False,
        "revenue_model_documented": "documented",
        "has_loi": 1,                  # has LOI → no flag
    }
    r = detect_all_anomalies(answers, _EMPTY_SCORES)
    codes = [f["code"] for f in r["anomaly_flags"]]
    assert "revenue_no_clients" not in codes, f"unexpected flag: {codes}"
    print(f"PASS  Test 2b — revenue_no_clients silent when LOI present")


def test_revenue_no_clients_silent_when_draft():
    answers = {
        "market_size": "small",
        "customer_interviews": "0",
        "has_paying_customers": False,
        "revenue_model_documented": "draft",  # not "documented" → no flag
        "has_loi": 0,
    }
    r = detect_all_anomalies(answers, _EMPTY_SCORES)
    codes = [f["code"] for f in r["anomaly_flags"]]
    assert "revenue_no_clients" not in codes, f"unexpected flag: {codes}"
    print(f"PASS  Test 2c — revenue_no_clients silent when model is draft")


# ---------------------------------------------------------------------------
# Test 3a — scalability_manual_conflict fires when high scale + high manual
# ---------------------------------------------------------------------------
def test_scalability_conflict_fires_automated_high():
    answers = {
        "replicability": "automated",
        "geographic_potential": "local",   # replicability alone is enough
        "manual_dependency": "high",
    }
    r = detect_all_anomalies(answers, _EMPTY_SCORES)
    codes = [f["code"] for f in r["anomaly_flags"]]
    assert "scalability_manual_conflict" in codes, f"expected flag, got: {codes}"
    flag = next(f for f in r["anomaly_flags"] if f["code"] == "scalability_manual_conflict")
    assert flag["severity"] == "medium"
    print(f"PASS  Test 3a — scalability_manual_conflict fires (automated + high) | flags: {codes}")


def test_scalability_conflict_fires_regional_medium():
    answers = {
        "replicability": "partial",
        "geographic_potential": "regional",  # geo alone triggers high_scale
        "manual_dependency": "medium",
    }
    r = detect_all_anomalies(answers, _EMPTY_SCORES)
    codes = [f["code"] for f in r["anomaly_flags"]]
    assert "scalability_manual_conflict" in codes, f"expected flag, got: {codes}"
    print(f"PASS  Test 3b — scalability_manual_conflict fires (regional + medium)")


def test_scalability_conflict_silent_when_low_manual():
    answers = {
        "replicability": "automated",
        "geographic_potential": "global",
        "manual_dependency": "low",
    }
    r = detect_all_anomalies(answers, _EMPTY_SCORES)
    codes = [f["code"] for f in r["anomaly_flags"]]
    assert "scalability_manual_conflict" not in codes, f"unexpected flag: {codes}"
    print(f"PASS  Test 3c — scalability_manual_conflict silent when manual_dependency=low")


# ---------------------------------------------------------------------------
# Test 4a — green_fundraising_risk fires when undp_raw_total >= 16 + fundraising
# ---------------------------------------------------------------------------
def test_green_fundraising_risk_fires():
    answers = {
        "has_pitch_deck": True,
        "funding_needed": "500000",   # truthy
    }
    scores = _green_stub(undp_raw_total=17.0)  # Impact élevé
    r = detect_all_anomalies(answers, scores)
    codes = [f["code"] for f in r["anomaly_flags"]]
    assert "green_fundraising_risk" in codes, f"expected flag, got: {codes}"
    flag = next(f for f in r["anomaly_flags"] if f["code"] == "green_fundraising_risk")
    assert flag["severity"] == "medium"
    print(f"PASS  Test 4a — green_fundraising_risk fires (undp=17, fundraising active) | flags: {codes}")


def test_green_fundraising_risk_silent_when_low_impact():
    answers = {
        "has_pitch_deck": True,
        "funding_needed": "500000",
    }
    scores = _green_stub(undp_raw_total=11.0)  # Faible impact → below threshold
    r = detect_all_anomalies(answers, scores)
    codes = [f["code"] for f in r["anomaly_flags"]]
    assert "green_fundraising_risk" not in codes, f"unexpected flag: {codes}"
    print(f"PASS  Test 4b — green_fundraising_risk silent when undp=11 (below 16)")


def test_green_fundraising_risk_silent_when_no_pitch_deck():
    answers = {
        "has_pitch_deck": False,      # not fundraising → no flag
        "funding_needed": "500000",
    }
    scores = _green_stub(undp_raw_total=18.0)
    r = detect_all_anomalies(answers, scores)
    codes = [f["code"] for f in r["anomaly_flags"]]
    assert "green_fundraising_risk" not in codes, f"unexpected flag: {codes}"
    print(f"PASS  Test 4c — green_fundraising_risk silent when has_pitch_deck=False")


# ---------------------------------------------------------------------------
# Test 5 — multiple flags fire together (realistic combined profile)
# ---------------------------------------------------------------------------
def test_multiple_flags_combined():
    answers = {
        "market_size": "very_large",
        "customer_interviews": "0",
        "has_paying_customers": False,
        "revenue_model_documented": "documented",
        "has_loi": 0,
        "replicability": "automated",
        "geographic_potential": "global",
        "manual_dependency": "high",
        "has_pitch_deck": True,
        "funding_needed": "1000000",
    }
    scores = _green_stub(undp_raw_total=19.0)
    r = detect_all_anomalies(answers, scores)
    codes = [f["code"] for f in r["anomaly_flags"]]
    assert len(r["anomaly_flags"]) == 4, f"expected 4 flags, got {len(r['anomaly_flags'])}: {codes}"
    assert "market_no_validation"      in codes
    assert "revenue_no_clients"        in codes
    assert "scalability_manual_conflict" in codes
    assert "green_fundraising_risk"    in codes
    print(f"PASS  Test 5 — all 4 flags fire together | codes: {codes}")


# ---------------------------------------------------------------------------
# Test 6 — product_built_unvalidated: product fully built, need never validated
# Distinct from market_no_validation: a founder can have done customer
# interviews (passing check a) while still never validating THIS SPECIFIC
# product against a real need (failing this one). They are not redundant.
# ---------------------------------------------------------------------------
def test_product_built_unvalidated_fires():
    answers = {
        "product_maturity":     "product",
        "offer_need_alignment": "none",
    }
    r = detect_all_anomalies(answers, _EMPTY_SCORES)
    codes = [f["code"] for f in r["anomaly_flags"]]
    assert "product_built_unvalidated" in codes, \
        f"expected flag product_built_unvalidated, got: {codes}"
    flag = next(f for f in r["anomaly_flags"] if f["code"] == "product_built_unvalidated")
    assert flag["severity"] == "medium", f"expected severity=medium, got {flag['severity']}"
    print(f"PASS  Test 6a — product_built_unvalidated fires (product + none) | flags: {codes}")


def test_product_built_unvalidated_silent_when_validated():
    answers = {
        "product_maturity":     "product",
        "offer_need_alignment": "validated",  # aligned with real need → no flag
    }
    r = detect_all_anomalies(answers, _EMPTY_SCORES)
    codes = [f["code"] for f in r["anomaly_flags"]]
    assert "product_built_unvalidated" not in codes, f"unexpected flag: {codes}"
    print(f"PASS  Test 6b — product_built_unvalidated silent when alignment=validated")


def test_product_built_unvalidated_silent_when_prototype():
    answers = {
        "product_maturity":     "prototype",  # not fully built yet → different risk profile
        "offer_need_alignment": "none",
    }
    r = detect_all_anomalies(answers, _EMPTY_SCORES)
    codes = [f["code"] for f in r["anomaly_flags"]]
    assert "product_built_unvalidated" not in codes, f"unexpected flag: {codes}"
    print(f"PASS  Test 6c — product_built_unvalidated silent when maturity=prototype")


if __name__ == "__main__":
    test_market_no_validation_fires()
    test_market_no_validation_silent_when_small()
    test_market_no_validation_silent_when_paying()
    test_revenue_no_clients_fires()
    test_revenue_no_clients_silent_when_loi_present()
    test_revenue_no_clients_silent_when_draft()
    test_scalability_conflict_fires_automated_high()
    test_scalability_conflict_fires_regional_medium()
    test_scalability_conflict_silent_when_low_manual()
    test_green_fundraising_risk_fires()
    test_green_fundraising_risk_silent_when_low_impact()
    test_green_fundraising_risk_silent_when_no_pitch_deck()
    test_multiple_flags_combined()
    test_product_built_unvalidated_fires()
    test_product_built_unvalidated_silent_when_validated()
    test_product_built_unvalidated_silent_when_prototype()
    print("\nAll anomaly tests passed.")
