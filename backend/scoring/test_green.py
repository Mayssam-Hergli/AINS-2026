import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.green import compute_green_score

# -------------------------------------------------------------------
# Test 1 — Atelier de tissage artisanal (Kilim)
# Expected pillar scores: climat_air=2, eau=2, sols_biodiversite=1, ressources_dechets=2
# Expected undp_raw_total=7, classification="Très faible impact"
# -------------------------------------------------------------------
KILIM = {
    "energy_source":           "mixed_renewable_grid",  # 2
    "energy_consumption":      "low",                   # 2
    "transport_activity":      "local",                 # 2  → climat_air avg = 2.0
    "water_volume":            "low_controlled",        # 2
    "water_origin":            "municipal_controlled",  # 2
    "wastewater_treatment":    "full_treatment",        # 2  → eau avg = 2.0
    "zone_type":               "urban_industrial",      # 1
    "surface_impacted":        "none",                  # 1
    "ecosystem_disruption":    "none",                  # 1  → sols_biodiversite avg = 1.0
    "raw_material_consumption":"low_recycled",          # 2
    "waste_volume":            "low_managed",           # 2
    "recycling_strategy":      "active_program",        # 2  → ressources_dechets avg = 2.0
}

# -------------------------------------------------------------------
# Test 2 — Unité de production de briques en ciment
# Expected pillar scores: climat_air=4, eau=3, sols_biodiversite=4, ressources_dechets=4
# Expected undp_raw_total=15, classification="Impact modéré"
# -------------------------------------------------------------------
CIMENT = {
    "energy_source":           "grid_diesel",           # 4
    "energy_consumption":      "high",                  # 4
    "transport_activity":      "national",              # 4  → climat_air avg = 4.0
    "water_volume":            "moderate",              # 3
    "water_origin":            "municipal_uncontrolled",# 3
    "wastewater_treatment":    "partial_treatment",     # 3  → eau avg = 3.0
    "zone_type":               "near_protected",        # 4
    "surface_impacted":        "large",                 # 4
    "ecosystem_disruption":    "significant",           # 4  → sols_biodiversite avg = 4.0
    "raw_material_consumption":"high_virgin",           # 4
    "waste_volume":            "high",                  # 4
    "recycling_strategy":      "minimal",               # 4  → ressources_dechets avg = 4.0
}


def test_kilim():
    r = compute_green_score(KILIM)
    p = r["pillars"]
    assert p["climat_air"]["score"]       == 2.0, f"climat_air: expected 2.0, got {p['climat_air']['score']}"
    assert p["eau"]["score"]              == 2.0, f"eau: expected 2.0, got {p['eau']['score']}"
    assert p["sols_biodiversite"]["score"]== 1.0, f"sols_biodiversite: expected 1.0, got {p['sols_biodiversite']['score']}"
    assert p["ressources_dechets"]["score"]== 2.0, f"ressources_dechets: expected 2.0, got {p['ressources_dechets']['score']}"
    assert r["undp_raw_total"]            == 7.0, f"undp_raw_total: expected 7.0, got {r['undp_raw_total']}"
    assert r["undp_classification"]       == "Très faible impact", f"classification: got {r['undp_classification']}"
    assert r["composite"]                 == 81.2, f"composite: expected 81.2, got {r['composite']}"
    print(f"PASS  Test 1 — Kilim | composite={r['composite']} | total={r['undp_raw_total']} | {r['undp_classification']}")


def test_ciment():
    r = compute_green_score(CIMENT)
    p = r["pillars"]
    assert p["climat_air"]["score"]       == 4.0, f"climat_air: expected 4.0, got {p['climat_air']['score']}"
    assert p["eau"]["score"]              == 3.0, f"eau: expected 3.0, got {p['eau']['score']}"
    assert p["sols_biodiversite"]["score"]== 4.0, f"sols_biodiversite: expected 4.0, got {p['sols_biodiversite']['score']}"
    assert p["ressources_dechets"]["score"]== 4.0, f"ressources_dechets: expected 4.0, got {p['ressources_dechets']['score']}"
    assert r["undp_raw_total"]            == 15.0, f"undp_raw_total: expected 15.0, got {r['undp_raw_total']}"
    assert r["undp_classification"]       == "Impact modéré", f"classification: got {r['undp_classification']}"
    assert r["composite"]                 == 31.2, f"composite: expected 31.2, got {r['composite']}"
    print(f"PASS  Test 2 — Ciment | composite={r['composite']} | total={r['undp_raw_total']} | {r['undp_classification']}")


if __name__ == "__main__":
    test_kilim()
    test_ciment()
    print("\nAll tests passed.")
