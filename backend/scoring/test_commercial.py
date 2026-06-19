import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.commercial import compute_commercial_score

# -----------------------------------------------------------------------
# Test 1 — Strong profile
# VP=differentiated(100), maturity=product(100), pricing=defined(100),
# alignment=validated(100)
# composite = 100*0.30 + 100*0.25 + 100*0.25 + 100*0.20
#           = 30.0 + 25.0 + 25.0 + 20.0 = 100.0
# -----------------------------------------------------------------------
STRONG = {
    "value_proposition_clarity": "differentiated",
    "product_maturity":          "product",
    "pricing_strategy":          "defined",
    "offer_need_alignment":      "validated",
}

# -----------------------------------------------------------------------
# Test 2 — Weak profile
# VP=none(10), maturity=idea(15), pricing=none(10), alignment=none(10)
# composite = 10*0.30 + 15*0.25 + 10*0.25 + 10*0.20
#           = 3.0 + 3.75 + 2.5 + 2.0 = 11.25 → 11.2 (banker's rounding)
# -----------------------------------------------------------------------
WEAK = {
    "value_proposition_clarity": "none",
    "product_maturity":          "idea",
    "pricing_strategy":          "none",
    "offer_need_alignment":      "none",
}

# -----------------------------------------------------------------------
# Test 3 — "Built before validating" mixed profile
# VP=differentiated(100), maturity=product(100), pricing=defined(100),
# alignment=none(10)
# composite = 100*0.30 + 100*0.25 + 100*0.25 + 10*0.20
#           = 30.0 + 25.0 + 25.0 + 2.0 = 82.0
#
# CANDIDATE anomaly for anomaly.py:
#   product_maturity="product" + offer_need_alignment="none"
#   → "Produit entièrement construit sans validation du besoin client"
#   This is the classic "build first, ask later" founder mistake.
#   The composite (82.0) looks healthy but masks a critical structural flaw:
#   the product was built without validating that the need is real.
# -----------------------------------------------------------------------
BUILT_BEFORE_VALIDATING = {
    "value_proposition_clarity": "differentiated",
    "product_maturity":          "product",
    "pricing_strategy":          "defined",
    "offer_need_alignment":      "none",
}


def test_strong_profile():
    r = compute_commercial_score(STRONG)
    s = r["sub_scores"]

    assert s["proposition_valeur"]["value"] == 100, \
        f"proposition_valeur: expected 100, got {s['proposition_valeur']['value']}"
    assert s["maturite_produit"]["value"]   == 100, \
        f"maturite_produit: expected 100, got {s['maturite_produit']['value']}"
    assert s["strategie_pricing"]["value"]  == 100, \
        f"strategie_pricing: expected 100, got {s['strategie_pricing']['value']}"
    assert s["alignement_besoin"]["value"]  == 100, \
        f"alignement_besoin: expected 100, got {s['alignement_besoin']['value']}"
    assert r["composite"] == 100.0, \
        f"composite: expected 100.0, got {r['composite']}"

    print(f"PASS  Test 1 — Strong  | composite={r['composite']} "
          f"(VP={s['proposition_valeur']['value']}, "
          f"maturite={s['maturite_produit']['value']}, "
          f"pricing={s['strategie_pricing']['value']}, "
          f"alignement={s['alignement_besoin']['value']})")


def test_weak_profile():
    r = compute_commercial_score(WEAK)
    s = r["sub_scores"]

    assert s["proposition_valeur"]["value"] == 10,  \
        f"proposition_valeur: expected 10, got {s['proposition_valeur']['value']}"
    assert s["maturite_produit"]["value"]   == 15,  \
        f"maturite_produit: expected 15, got {s['maturite_produit']['value']}"
    assert s["strategie_pricing"]["value"]  == 10,  \
        f"strategie_pricing: expected 10, got {s['strategie_pricing']['value']}"
    assert s["alignement_besoin"]["value"]  == 10,  \
        f"alignement_besoin: expected 10, got {s['alignement_besoin']['value']}"
    assert r["composite"] == 11.2, \
        f"composite: expected 11.2, got {r['composite']}"

    print(f"PASS  Test 2 — Weak    | composite={r['composite']} "
          f"(VP={s['proposition_valeur']['value']}, "
          f"maturite={s['maturite_produit']['value']}, "
          f"pricing={s['strategie_pricing']['value']}, "
          f"alignement={s['alignement_besoin']['value']})")


def test_built_before_validating():
    r = compute_commercial_score(BUILT_BEFORE_VALIDATING)
    s = r["sub_scores"]

    assert s["proposition_valeur"]["value"] == 100, \
        f"proposition_valeur: expected 100, got {s['proposition_valeur']['value']}"
    assert s["maturite_produit"]["value"]   == 100, \
        f"maturite_produit: expected 100, got {s['maturite_produit']['value']}"
    assert s["strategie_pricing"]["value"]  == 100, \
        f"strategie_pricing: expected 100, got {s['strategie_pricing']['value']}"
    assert s["alignement_besoin"]["value"]  == 10,  \
        f"alignement_besoin: expected 10, got {s['alignement_besoin']['value']}"
    assert r["composite"] == 82.0, \
        f"composite: expected 82.0, got {r['composite']}"

    print(f"PASS  Test 3 — Mixed   | composite={r['composite']} "
          f"(VP={s['proposition_valeur']['value']}, "
          f"maturite={s['maturite_produit']['value']}, "
          f"pricing={s['strategie_pricing']['value']}, "
          f"alignement={s['alignement_besoin']['value']})")
    print(f"      [CANDIDATE ANOMALY] product_maturity=product + "
          f"offer_need_alignment=none — built before validating")


if __name__ == "__main__":
    test_strong_profile()
    test_weak_profile()
    test_built_before_validating()
    print("\nAll tests passed.")
