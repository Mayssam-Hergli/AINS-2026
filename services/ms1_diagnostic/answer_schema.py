"""Authoritative MS1 → MS2 questionnaire-answer contract.

This module is the single source of truth for the keys MS1 writes into the
``diagnostic_answers`` JSONB column. MS2 reads these **raw** keys directly (no
transformation layer), so every key here must match the scorer's spec exactly,
including the enum values.

Field groups mirror the scoring agent's modules:
    market · commercial · innovation · scalability · green · anomaly

``validate_answers`` checks a submitted answer set against this schema, and
``build_diagnostic_answers`` produces the flat dict to persist — with defaults
applied so **every** contract key is always present for MS2 to read.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ANSWERS_SCHEMA_VERSION = "ms1.answers.v1"


@dataclass(frozen=True)
class FieldSpec:
    key: str
    group: str
    kind: str  # "enum" | "int" | "bool" | "string"
    allowed: tuple[Any, ...] | None  # enum/int allowed values; None = free value
    required: bool
    default: Any


def _enum(key, group, values, *, required=True, default=None) -> FieldSpec:
    return FieldSpec(key, group, "enum", tuple(values), required, default or values[0])


# --- The contract -----------------------------------------------------------
FIELD_SPECS: tuple[FieldSpec, ...] = (
    # Market
    _enum("market_size", "market", ("small", "medium", "large", "very_large")),
    _enum("customer_interviews", "market", ("0", "1-5", "6-10", "10+")),
    FieldSpec("has_loi", "market", "int", None, required=True, default=0),  # count of signed LOIs (>= 0)
    FieldSpec("has_paying_customers", "market", "bool", None, required=True, default=False),
    _enum("revenue_model_documented", "market", ("none", "draft", "documented")),
    _enum("revenue_model_type", "market",
          ("subscription", "transactional", "freemium", "undefined"),
          required=False, default="undefined"),
    # Commercial
    _enum("value_proposition_clarity", "commercial", ("none", "vague", "clear", "differentiated")),
    _enum("product_maturity", "commercial", ("idea", "prototype", "mvp", "product")),
    _enum("pricing_strategy", "commercial", ("none", "draft", "defined")),
    _enum("offer_need_alignment", "commercial", ("none", "partial", "validated")),
    # Innovation
    _enum("local_novelty", "innovation", ("existing", "similar", "new", "unique")),
    _enum("technology_intensity", "innovation", ("none", "low", "medium", "high")),
    _enum("barrier_to_entry", "innovation", ("none", "low", "medium", "high")),
    _enum("has_ip_protection", "innovation", ("none", "pending", "granted"),
          required=False, default="none"),
    # Scalability
    _enum("replicability", "scalability", ("manual", "semi_auto", "automated")),
    _enum("manual_dependency", "scalability", ("high", "medium", "low", "none")),
    _enum("geographic_potential", "scalability", ("local", "national", "regional", "global")),
    # Green
    _enum("energy_source", "green",
          ("solar_wind", "mixed_renewable_grid", "grid_steg", "grid_diesel", "diesel_only")),
    _enum("energy_consumption", "green", ("minimal", "low", "moderate", "high", "very_high")),
    _enum("transport_activity", "green", ("none", "local", "regional", "national", "international")),
    _enum("water_volume", "green", ("none", "low_controlled", "moderate", "high", "very_high")),
    _enum("water_origin", "green",
          ("rainwater_recycled", "municipal_controlled", "municipal_uncontrolled",
           "groundwater", "natural_body")),
    _enum("wastewater_treatment", "green",
          ("none_generated", "full_treatment", "partial_treatment",
           "discharged_untreated", "discharged_environment")),
    _enum("zone_type", "green",
          ("urban_industrial", "suburban", "rural_agricultural",
           "near_protected", "inside_protected")),
    _enum("surface_impacted", "green", ("none", "small", "medium", "large", "very_large")),
    _enum("ecosystem_disruption", "green",
          ("none", "negligible", "moderate_reversible", "significant", "irreversible")),
    _enum("raw_material_consumption", "green",
          ("none_minimal", "low_recycled", "moderate_partial",
           "high_virgin", "very_high_no_recycling")),
    _enum("waste_volume", "green",
          ("none", "low_managed", "moderate_partial", "high", "very_high_unmanaged")),
    _enum("recycling_strategy", "green",
          ("full_circular", "active_program", "partial", "minimal", "none")),
    # Anomaly detection (read cross-module by the anomaly detector)
    FieldSpec("has_pitch_deck", "anomaly", "bool", None, required=False, default=False),
    FieldSpec("funding_needed", "anomaly", "string", None, required=False, default=""),
)

_SPEC_BY_KEY: dict[str, FieldSpec] = {s.key: s for s in FIELD_SPECS}
ALL_KEYS: tuple[str, ...] = tuple(s.key for s in FIELD_SPECS)
REQUIRED_KEYS: tuple[str, ...] = tuple(s.key for s in FIELD_SPECS if s.required)
GROUPS: tuple[str, ...] = ("market", "commercial", "innovation", "scalability", "green", "anomaly")


def keys_for_group(group: str) -> tuple[str, ...]:
    return tuple(s.key for s in FIELD_SPECS if s.group == group)


# --- Coercion ---------------------------------------------------------------
def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return None


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "y")
    return bool(value)


# --- Validation -------------------------------------------------------------
def validate_answers(answers: dict[str, Any]) -> list[str]:
    """Return a list of contract violations (empty list = valid)."""
    issues: list[str] = []
    for spec in FIELD_SPECS:
        present = spec.key in answers and answers[spec.key] is not None
        if not present:
            if spec.required:
                issues.append(f"{spec.key}: required (group '{spec.group}')")
            continue
        value = answers[spec.key]
        if spec.kind == "enum":
            if value not in (spec.allowed or ()):
                issues.append(f"{spec.key}: {value!r} not in {list(spec.allowed)}")
        elif spec.kind == "int":
            coerced = _coerce_int(value)
            if coerced is None:
                issues.append(f"{spec.key}: expected an integer, got {value!r}")
            elif spec.allowed is not None and coerced not in spec.allowed:
                issues.append(f"{spec.key}: {coerced} not in {list(spec.allowed)}")
            elif spec.allowed is None and coerced < 0:
                issues.append(f"{spec.key}: count must be >= 0, got {coerced}")
        elif spec.kind == "bool":
            if not isinstance(value, (bool, int)) and not isinstance(value, str):
                issues.append(f"{spec.key}: expected a boolean, got {value!r}")
        elif spec.kind == "string":
            if not isinstance(value, str):
                issues.append(f"{spec.key}: expected a string, got {value!r}")
    return issues


# --- Build ------------------------------------------------------------------
def build_diagnostic_answers(answers: dict[str, Any]) -> dict[str, Any]:
    """Produce the flat ``diagnostic_answers`` dict MS2 reads.

    Every contract key is present: provided values are coerced to their canonical
    type; absent optional keys fall back to their documented default.
    """
    out: dict[str, Any] = {}
    for spec in FIELD_SPECS:
        if spec.key in answers and answers[spec.key] is not None:
            value = answers[spec.key]
            if spec.kind == "int":
                value = _coerce_int(value)
                if value is None:
                    value = spec.default
            elif spec.kind == "bool":
                value = _coerce_bool(value)
            elif spec.kind in ("enum", "string"):
                value = str(value)
            out[spec.key] = value
        else:
            out[spec.key] = spec.default
    return out
