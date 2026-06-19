from __future__ import annotations

SCORE_MAPS: dict[str, dict[str, int]] = {
    "energy_source": {
        "solar_wind": 1,
        "mixed_renewable_grid": 2,
        "grid_steg": 3,
        "grid_diesel": 4,
        "diesel_only": 5,
    },
    "energy_consumption": {
        "minimal": 1,
        "low": 2,
        "moderate": 3,
        "high": 4,
        "very_high": 5,
    },
    "transport_activity": {
        "none": 1,
        "local": 2,
        "regional": 3,
        "national": 4,
        "international": 5,
    },
    "water_volume": {
        "none": 1,
        "low_controlled": 2,
        "moderate": 3,
        "high": 4,
        "very_high": 5,
    },
    "water_origin": {
        "rainwater_recycled": 1,
        "municipal_controlled": 2,
        "municipal_uncontrolled": 3,
        "groundwater": 4,
        "natural_body": 5,
    },
    "wastewater_treatment": {
        "none_generated": 1,
        "full_treatment": 2,
        "partial_treatment": 3,
        "discharged_untreated": 4,
        "discharged_environment": 5,
    },
    "zone_type": {
        "urban_industrial": 1,
        "suburban": 2,
        "rural_agricultural": 3,
        "near_protected": 4,
        "inside_protected": 5,
    },
    "surface_impacted": {
        "none": 1,
        "small": 2,
        "medium": 3,
        "large": 4,
        "very_large": 5,
    },
    "ecosystem_disruption": {
        "none": 1,
        "negligible": 2,
        "moderate_reversible": 3,
        "significant": 4,
        "irreversible": 5,
    },
    "raw_material_consumption": {
        "none_minimal": 1,
        "low_recycled": 2,
        "moderate_partial": 3,
        "high_virgin": 4,
        "very_high_no_recycling": 5,
    },
    "waste_volume": {
        "none": 1,
        "low_managed": 2,
        "moderate_partial": 3,
        "high": 4,
        "very_high_unmanaged": 5,
    },
    "recycling_strategy": {
        "full_circular": 1,
        "active_program": 2,
        "partial": 3,
        "minimal": 4,
        "none": 5,
    },
}

_PILLARS: dict[str, dict] = {
    "climat_air": {
        "fields": ["energy_source", "energy_consumption", "transport_activity"],
        "weight": 0.35,
    },
    "eau": {
        "fields": ["water_volume", "water_origin", "wastewater_treatment"],
        "weight": 0.25,
    },
    "sols_biodiversite": {
        "fields": ["zone_type", "surface_impacted", "ecosystem_disruption"],
        "weight": 0.20,
    },
    "ressources_dechets": {
        "fields": ["raw_material_consumption", "waste_volume", "recycling_strategy"],
        "weight": 0.20,
    },
}

_CLASSIFICATION_THRESHOLDS = [
    (7,  "Très faible impact"),
    (11, "Faible impact"),
    (15, "Impact modéré"),
    (18, "Impact élevé"),
    (20, "Impact très élevé"),
]


def _classify(total: float) -> str:
    for threshold, label in _CLASSIFICATION_THRESHOLDS:
        if total <= threshold:
            return label
    return "Impact très élevé"


def compute_green_score(answers: dict[str, str]) -> dict:
    pillar_results: dict[str, dict] = {}
    undp_raw_total = 0.0

    for pillar_name, pillar_def in _PILLARS.items():
        scores = [SCORE_MAPS[field][answers[field]] for field in pillar_def["fields"]]
        pillar_score = sum(scores) / len(scores)
        pillar_results[pillar_name] = {
            "score": pillar_score,
            "weight": pillar_def["weight"],
        }
        undp_raw_total += pillar_score

    display_score = round(100 - ((undp_raw_total - 4) / 16 * 100), 1)

    return {
        "composite": display_score,
        "undp_raw_total": undp_raw_total,
        "undp_classification": _classify(undp_raw_total),
        "pillars": pillar_results,
        "anomaly_flags": [],
    }
