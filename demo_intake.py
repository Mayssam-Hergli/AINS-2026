"""Demo: MS1 intake → the diagnostic_answers object MS2 reads.

Submits a sample founder questionnaire, validates it, and prints the flat
diagnostic_answers JSON exactly as it lands in project_profiles. No DB or API key
needed (uses the in-memory pool).

Run:  python demo_intake.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from services.ms1_diagnostic.answer_schema import ALL_KEYS, GROUPS, keys_for_group
from services.ms1_diagnostic.intake import AnswerRepository, IntakeService
from tests.fakepg import InMemoryPool

# A green-tech startup's questionnaire answers (raw, as a founder would submit them).
FOUNDER_ANSWERS = {
    "market_size": "large",
    "customer_interviews": "10+",
    "has_loi": 2,
    "has_paying_customers": True,
    "revenue_model_documented": "documented",
    "revenue_model_type": "subscription",
    "value_proposition_clarity": "clear",
    "product_maturity": "mvp",
    "pricing_strategy": "defined",
    "offer_need_alignment": "validated",
    "local_novelty": "unique",
    "technology_intensity": "high",
    "barrier_to_entry": "high",
    "has_ip_protection": "granted",
    "replicability": "automated",
    "manual_dependency": "low",
    "geographic_potential": "global",
    "energy_source": "solar_wind",
    "energy_consumption": "low",
    "transport_activity": "local",
    "water_volume": "low_controlled",
    "water_origin": "rainwater_recycled",
    "wastewater_treatment": "full_treatment",
    "zone_type": "suburban",
    "surface_impacted": "small",
    "ecosystem_disruption": "negligible",
    "raw_material_consumption": "low_recycled",
    "waste_volume": "low_managed",
    "recycling_strategy": "full_circular",
    "has_pitch_deck": True,
    "funding_needed": "series_a",
}


async def main() -> None:
    pool = InMemoryPool()
    repo = AnswerRepository(pool)
    await repo.ensure_schema()
    service = IntakeService(repository=repo)

    project_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    print("=" * 72)
    print("MS1 INTAKE — writing diagnostic_answers for MS2")
    print("=" * 72)

    diagnostic_answers = await service.submit(
        project_id=project_id, answers=FOUNDER_ANSWERS, tenant_id=tenant_id, persist=True,
    )

    print(f"\nValidated and stored {len(diagnostic_answers)} keys "
          f"for project {project_id}\n")
    for group in GROUPS:
        keys = keys_for_group(group)
        print(f"  {group:11} ({len(keys)} keys): "
              + ", ".join(f"{k}={diagnostic_answers[k]}" for k in keys[:3])
              + (" ..." if len(keys) > 3 else ""))

    print("\n--- diagnostic_answers JSON (what MS2 reads as-is) ---")
    print(json.dumps(diagnostic_answers, indent=2))

    # Prove MS2 can read it back from the shared column.
    stored = await repo.read_answers(project_id)
    assert stored is not None and set(stored) == set(ALL_KEYS)
    print(f"\n✓ Read back {len(stored)} keys from project_profiles.diagnostic_answers")
    print("✓ Every contract key present — MS2 will find all of them.")


if __name__ == "__main__":
    asyncio.run(main())
