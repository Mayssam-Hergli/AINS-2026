from __future__ import annotations


def detect_all_anomalies(
    diagnostic_answers: dict,
    all_scores: dict,
) -> dict:
    """
    Cross-module anomaly detection. Runs once after all 5 scores are computed.

    Args:
        diagnostic_answers: raw questionnaire answer dict
        all_scores: dict with keys "market", "commercial", "innovation",
                    "scalability", "green" — each the output of its compute function
    """
    flags: list[dict] = []

    # (a) Large market declared + zero client validation
    if (
        diagnostic_answers.get("market_size") in ("large", "very_large")
        and diagnostic_answers.get("customer_interviews") == "0"
        and not diagnostic_answers.get("has_paying_customers", False)
    ):
        flags.append({
            "code": "market_no_validation",
            "message": "Marché jugé important sans aucune preuve de validation client",
            "severity": "high",
        })

    # (b) Documented revenue model + no paying customers + no LOI
    if (
        diagnostic_answers.get("revenue_model_documented") == "documented"
        and not diagnostic_answers.get("has_paying_customers", False)
        and int(diagnostic_answers.get("has_loi", 0)) == 0
    ):
        flags.append({
            "code": "revenue_no_clients",
            "message": "Modèle de revenus documenté mais aucun client ni LOI",
            "severity": "high",
        })

    # (c) High scalability claim + high manual dependency (cross-module)
    high_scale = (
        diagnostic_answers.get("replicability") == "automated"
        or diagnostic_answers.get("geographic_potential") in ("global", "regional")
    )
    high_manual = diagnostic_answers.get("manual_dependency") in ("high", "medium")
    if high_scale and high_manual:
        flags.append({
            "code": "scalability_manual_conflict",
            "message": (
                "Scalabilité élevée déclarée malgré une forte dépendance "
                "à l'accompagnement manuel"
            ),
            "severity": "medium",
        })

    # (d) High environmental impact (green) + active fundraising (cross-module)
    green = all_scores.get("green", {})
    fundraising_active = (
        diagnostic_answers.get("has_pitch_deck") is True
        and diagnostic_answers.get("funding_needed")
    )
    if green.get("undp_raw_total", 0) >= 16 and fundraising_active:
        flags.append({
            "code": "green_fundraising_risk",
            "message": (
                "Profil en recherche de financement avec un impact "
                "environnemental élevé — risque de blocage pour financements verts"
            ),
            "severity": "medium",
        })

    # (e) Product fully built + offer-need alignment never validated
    # Both fields are raw questionnaire keys in diagnostic_answers.
    # all_scores["commercial"] only carries numeric scores — not the original
    # category strings — so we read directly from diagnostic_answers here.
    if (
        diagnostic_answers.get("product_maturity") == "product"
        and diagnostic_answers.get("offer_need_alignment") == "none"
    ):
        flags.append({
            "code": "product_built_unvalidated",
            "message": (
                "Produit entièrement développé sans validation du besoin "
                "client — risque de construire quelque chose que le marché ne veut pas"
            ),
            "severity": "medium",
        })

    return {"anomaly_flags": flags}
