from __future__ import annotations

from scoring.green import compute_green_score
from scoring.market import compute_market_score
from scoring.commercial import compute_commercial_score
from scoring.innovation import compute_innovation_score
from scoring.scalability import compute_scalability_score
from scoring.anomaly import detect_all_anomalies as _detect_anomalies

_SCORE_DIMENSIONS = frozenset({"market", "commercial", "innovation", "scalability", "green"})

_SCORING_FNS: dict = {
    "compute_market_score":      compute_market_score,
    "compute_commercial_score":  compute_commercial_score,
    "compute_innovation_score":  compute_innovation_score,
    "compute_scalability_score": compute_scalability_score,
    "compute_green_score":       compute_green_score,
}

TOOLS: list[dict] = [
    {
        "name": "compute_market_score",
        "description": (
            "Calcule le score Marché (0-100) à partir de la taille du marché, "
            "la validation client et le modèle de revenus. Retourne le composite "
            "et les 3 sous-scores pondérés : taille_marche (30%), "
            "validation_client (40%), modele_revenus (30%). "
            "La validation client est pondérée le plus fortement — un grand marché "
            "ne compense pas l'absence de preuves client. "
            "À appeler une fois par profil, avant detect_all_anomalies."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "market_size": {
                    "type": "string",
                    "enum": ["small", "medium", "large", "very_large"],
                    "description": "Taille estimée du marché adressable",
                },
                "customer_interviews": {
                    "type": "string",
                    "enum": ["0", "1-5", "6-10", "10+"],
                    "description": "Nombre d'entretiens clients réalisés",
                },
                "has_loi": {
                    "type": "integer",
                    "description": "Nombre de lettres d'intention signées (0, 1, ou 2+)",
                },
                "has_paying_customers": {
                    "type": "boolean",
                    "description": "True si le projet a déjà des clients payants",
                },
                "revenue_model_documented": {
                    "type": "string",
                    "enum": ["none", "draft", "documented"],
                    "description": "Niveau de documentation du modèle de revenus",
                },
                "revenue_model_type": {
                    "type": "string",
                    "description": "Type de modèle de revenus (ex: recurring, one_time, undefined). Requis même si revenue_model_documented=draft.",
                },
            },
            "required": [
                "market_size",
                "customer_interviews",
                "has_loi",
                "has_paying_customers",
                "revenue_model_documented",
                "revenue_model_type",
            ],
        },
    },
    {
        "name": "compute_commercial_score",
        "description": (
            "Calcule le score Offre Commerciale (0-100) à partir de la clarté de "
            "la proposition de valeur, la maturité produit, la stratégie de pricing "
            "et l'alignement offre-besoin. Retourne le composite et les 4 sous-scores "
            "pondérés : proposition_valeur (30%), maturite_produit (25%), "
            "strategie_pricing (25%), alignement_besoin (20%). "
            "À appeler une fois par profil, avant detect_all_anomalies."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "value_proposition_clarity": {
                    "type": "string",
                    "enum": ["none", "vague", "clear", "differentiated"],
                    "description": "Clarté et différenciation de la proposition de valeur",
                },
                "product_maturity": {
                    "type": "string",
                    "enum": ["idea", "prototype", "mvp", "product"],
                    "description": "Stade de maturité du produit ou service",
                },
                "pricing_strategy": {
                    "type": "string",
                    "enum": ["none", "draft", "defined"],
                    "description": "État de définition de la stratégie tarifaire",
                },
                "offer_need_alignment": {
                    "type": "string",
                    "enum": ["none", "partial", "validated"],
                    "description": "Degré de validation de l'alignement offre-besoin client",
                },
            },
            "required": [
                "value_proposition_clarity",
                "product_maturity",
                "pricing_strategy",
                "offer_need_alignment",
            ],
        },
    },
    {
        "name": "compute_innovation_score",
        "description": (
            "Calcule le score Innovation (0-100) à partir de la nouveauté locale, "
            "l'intensité technologique et la barrière à l'entrée. "
            "Un bonus IP est appliqué sur barriere_entree : +5 si brevet en cours "
            "(pending), +15 si brevet accordé (granted), plafonné à 100. "
            "Retourne le composite et les 3 sous-scores pondérés : "
            "nouveaute_locale (35%), intensite_technologique (30%), "
            "barriere_entree (35%, après bonus IP). "
            "À appeler une fois par profil, avant detect_all_anomalies."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "local_novelty": {
                    "type": "string",
                    "enum": ["existing", "similar", "new", "unique"],
                    "description": "Degré de nouveauté de la solution sur le marché local tunisien",
                },
                "technology_intensity": {
                    "type": "string",
                    "enum": ["none", "low", "medium", "high"],
                    "description": "Intensité technologique de la solution",
                },
                "barrier_to_entry": {
                    "type": "string",
                    "enum": ["none", "low", "medium", "high"],
                    "description": "Force de la barrière à l'entrée (hors protection IP)",
                },
                "has_ip_protection": {
                    "type": "string",
                    "enum": ["none", "pending", "granted"],
                    "description": "Statut de protection de la propriété intellectuelle. Optionnel — défaut: none si absent.",
                },
            },
            "required": ["local_novelty", "technology_intensity", "barrier_to_entry"],
        },
    },
    {
        "name": "compute_scalability_score",
        "description": (
            "Calcule le score Scalabilité (0-100) à partir de la réplicabilité, "
            "la dépendance manuelle et le potentiel géographique. "
            "ATTENTION : dependance_manuelle utilise une échelle inversée — "
            "moins d'intervention humaine requise = score plus élevé "
            "(high=10, medium=40, low=70, none=100). "
            "Retourne le composite et les 3 sous-scores pondérés : "
            "replicabilite (35%), dependance_manuelle (30%), "
            "potentiel_geographique (35%). "
            "À appeler une fois par profil, avant detect_all_anomalies."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "replicability": {
                    "type": "string",
                    "enum": ["manual", "semi_auto", "automated"],
                    "description": "Degré d'automatisation du processus de réplication",
                },
                "manual_dependency": {
                    "type": "string",
                    "enum": ["high", "medium", "low", "none"],
                    "description": "Niveau de dépendance à l'accompagnement humain — échelle inversée : high=10, none=100",
                },
                "geographic_potential": {
                    "type": "string",
                    "enum": ["local", "national", "regional", "global"],
                    "description": "Potentiel géographique d'expansion",
                },
            },
            "required": ["replicability", "manual_dependency", "geographic_potential"],
        },
    },
    {
        "name": "compute_green_score",
        "description": (
            "Calcule le score Impact Environnemental (0-100, affichage) selon la "
            "méthodologie UNDP à 4 piliers. Score d'affichage élevé = faible impact "
            "négatif. Évalue : climat_air (35%), eau (25%), sols_biodiversite (20%), "
            "ressources_dechets (20%). Retourne le composite (affichage), "
            "undp_raw_total (4–20), undp_classification (texte) et les scores par "
            "pilier. Les piliers avec score >= 3 sont signalés dans "
            "green_pillars_flagged par engine.py pour MS3. "
            "À appeler une fois par profil, avant detect_all_anomalies."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "energy_source": {
                    "type": "string",
                    "enum": ["solar_wind", "mixed_renewable_grid", "grid_steg", "grid_diesel", "diesel_only"],
                    "description": "Source d'énergie principale",
                },
                "energy_consumption": {
                    "type": "string",
                    "enum": ["minimal", "low", "moderate", "high", "very_high"],
                    "description": "Niveau de consommation énergétique",
                },
                "transport_activity": {
                    "type": "string",
                    "enum": ["none", "local", "regional", "national", "international"],
                    "description": "Portée de l'activité de transport",
                },
                "water_volume": {
                    "type": "string",
                    "enum": ["none", "low_controlled", "moderate", "high", "very_high"],
                    "description": "Volume d'eau consommé",
                },
                "water_origin": {
                    "type": "string",
                    "enum": ["rainwater_recycled", "municipal_controlled", "municipal_uncontrolled", "groundwater", "natural_body"],
                    "description": "Origine de l'eau utilisée",
                },
                "wastewater_treatment": {
                    "type": "string",
                    "enum": ["none_generated", "full_treatment", "partial_treatment", "discharged_untreated", "discharged_environment"],
                    "description": "Mode de traitement des eaux usées",
                },
                "zone_type": {
                    "type": "string",
                    "enum": ["urban_industrial", "suburban", "rural_agricultural", "near_protected", "inside_protected"],
                    "description": "Type de zone d'implantation",
                },
                "surface_impacted": {
                    "type": "string",
                    "enum": ["none", "small", "medium", "large", "very_large"],
                    "description": "Surface impactée par l'activité",
                },
                "ecosystem_disruption": {
                    "type": "string",
                    "enum": ["none", "negligible", "moderate_reversible", "significant", "irreversible"],
                    "description": "Degré de perturbation des écosystèmes",
                },
                "raw_material_consumption": {
                    "type": "string",
                    "enum": ["none_minimal", "low_recycled", "moderate_partial", "high_virgin", "very_high_no_recycling"],
                    "description": "Consommation de matières premières",
                },
                "waste_volume": {
                    "type": "string",
                    "enum": ["none", "low_managed", "moderate_partial", "high", "very_high_unmanaged"],
                    "description": "Volume de déchets générés",
                },
                "recycling_strategy": {
                    "type": "string",
                    "enum": ["full_circular", "active_program", "partial", "minimal", "none"],
                    "description": "Stratégie de recyclage et d'économie circulaire",
                },
            },
            "required": [
                "energy_source", "energy_consumption", "transport_activity",
                "water_volume", "water_origin", "wastewater_treatment",
                "zone_type", "surface_impacted", "ecosystem_disruption",
                "raw_material_consumption", "waste_volume", "recycling_strategy",
            ],
        },
    },
    {
        "name": "detect_all_anomalies",
        "description": (
            "Détecte les anomalies inter-modules dans le profil d'un projet. "
            "DOIT être appelé APRÈS les 5 outils de scoring — jamais avant. "
            "Appelle cet outil SANS paramètres (objet vide {}) : le pipeline "
            "injecte automatiquement les réponses et les 5 scores depuis les "
            "résultats des outils précédents. Inutile de les repasser manuellement. "
            "Identifie des contradictions invisibles dans les scores individuels "
            "(ex: scalabilité élevée déclarée malgré forte dépendance manuelle, "
            "ou produit entièrement développé sans validation du besoin). "
            "Retourne une liste de flags avec code, message et sévérité (high/medium)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


def execute_tool(tool_name: str, tool_input: dict) -> dict:
    """
    Dispatch a Claude tool_use block to the real underlying Python function.

    For the 5 scoring tools, tool_input IS the diagnostic_answers dict —
    each function reads only the fields it needs and ignores the rest, so
    passing the full answers dict is safe and is the expected agent pattern.

    For detect_all_anomalies, tool_input must have:
        {"diagnostic_answers": {...}, "all_scores": {"market": ..., ...}}

    Scoring tool errors (missing fields) return an error stub matching
    engine.py's degradation behavior:
        {"composite": None, "error": "<message>", "sub_scores": {}}

    detect_all_anomalies raises ValueError if all_scores is incomplete —
    this enforces the "call anomaly last, with everything" contract at the
    execution level rather than relying solely on the system prompt.
    """
    if tool_name in _SCORING_FNS:
        try:
            return _SCORING_FNS[tool_name](tool_input)
        except Exception as exc:
            return {"composite": None, "error": str(exc), "sub_scores": {}}

    if tool_name == "detect_all_anomalies":
        all_scores = tool_input.get("all_scores", {})
        missing = _SCORE_DIMENSIONS - set(all_scores.keys())
        if missing:
            raise ValueError(
                f"detect_all_anomalies requires all 5 score dimensions. "
                f"Missing: {sorted(missing)}. Call all 5 scoring tools first."
            )
        return _detect_anomalies(
            tool_input["diagnostic_answers"],
            all_scores,
        )

    raise ValueError(
        f"Unknown tool: {tool_name!r}. "
        f"Valid tools: {sorted(_SCORING_FNS) + ['detect_all_anomalies']}"
    )
