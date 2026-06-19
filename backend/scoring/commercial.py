from __future__ import annotations

_SCORE_MAPS: dict[str, dict[str, int]] = {
    "value_proposition_clarity": {
        "none":           10,
        "vague":          40,
        "clear":          70,
        "differentiated": 100,
    },
    "product_maturity": {
        "idea":      15,
        "prototype": 45,
        "mvp":       70,
        "product":   100,
    },
    "pricing_strategy": {
        "none":    10,
        "draft":   50,
        "defined": 100,
    },
    "offer_need_alignment": {
        "none":      10,
        "partial":   50,
        "validated": 100,
    },
}

_SUB_CRITERIA = [
    ("proposition_valeur", "value_proposition_clarity", 0.30),
    ("maturite_produit",   "product_maturity",          0.25),
    ("strategie_pricing",  "pricing_strategy",          0.25),
    ("alignement_besoin",  "offer_need_alignment",      0.20),
]


def compute_commercial_score(answers: dict) -> dict:
    sub_scores: dict[str, dict] = {}
    composite_raw = 0.0

    for key, field, weight in _SUB_CRITERIA:
        value = _SCORE_MAPS[field][answers[field]]
        sub_scores[key] = {"value": value, "weight": weight, "max": 100}
        composite_raw += value * weight

    return {
        "composite": round(composite_raw, 1),
        "sub_scores": sub_scores,
    }
