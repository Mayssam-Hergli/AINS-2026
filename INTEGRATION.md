# Integration Contract — Shared `project_profiles`

This document is the merge interface between my work (File Parser + **MS2 Scoring
Agent**) and my teammates' agents (**MS1 Diagnostic**, **MS3 Retrieval**). Everyone
integrates through the shared PostgreSQL + pgvector table `project_profiles` — **no
service calls another service directly**. Each stage reads what the previous stage
wrote.

## Workflow

```
MS1 Agent (teammate)        writes  diagnostic_answers  ─┐
                                                         ▼
MS2 Scoring Agent (mine)    reads   diagnostic_answers
                            writes  scores  (5 score objects)
                                                         │
                                                         ▼
MS3 Agent (teammate)        reads   scores  → decides what to retrieve from the KB
```

Ordering is **MS1 → MS2 → MS3**. MS2 refuses to run before MS1 has written
(`DiagnosticNotReadyError`).

## Column ownership on `project_profiles`

| Column                  | Type          | Owner        | MS2 access |
|-------------------------|---------------|--------------|------------|
| `project_id`            | `UUID` (PK)   | MS1 (creator)| read       |
| `tenant_id`             | `UUID`        | MS1          | read       |
| `diagnostic_answers`    | `JSONB`       | **MS1**      | **read only** |
| `scores`                | `JSONB`       | **MS2 (me)** | **write only** |
| `scores_schema_version` | `TEXT`        | MS2 (me)     | write      |
| `scores_updated_at`     | `TIMESTAMPTZ` | MS2 (me)     | write      |

**Merge-safety rules I follow so nothing clobbers a teammate's work:**

- MS2's migration is **additive only** (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`). It
  never `CREATE`s or redefines the table that MS1 owns. Run order between MS1's and
  MS2's `ensure_schema()` does not matter.
- MS2 writes with `UPDATE ... WHERE project_id = $1` touching **only** `scores*`
  columns — never an upsert, never another column. MS1's `diagnostic_answers` is never
  overwritten.
- Auxiliary tables are namespaced per owner: MS2 owns `project_scores_history`
  (append-only audit), MS1 owns `project_profiles_history`. No collisions.

## Read contract — `diagnostic_answers` (produced by MS1)

MS2 reads via `DiagnosticAnswersView.from_raw(...)`, which is **tolerant**: every field
below is read with `.get()` and a safe default, so an additive change on the MS1 side
won't break scoring. The minimal fields MS2 depends on:

```jsonc
{
  "schema_version": "ms1.diagnostic.v1",
  "overall": { "score": 0.07, "maturity_level": 1 },
  "questionnaire": { "coverage": 1.0 },
  "domains": [
    { "domain": "environmental", "perceived_score": 0.9, "evidenced_score": 0.2,
      "gap": 0.7, "direction": "overclaim", "maturity_level": 1 }
  ],
  "gap_report": {
    "overall_gap": 0.8,
    "domain_gaps": [
      { "domain": "environmental", "evidence_count": 3, "severity": "high",
        "supporting_signal_ids": ["sig_..."] }
    ]
  },
  "blockers": [
    { "domain": "compliance", "title": "...", "category": "data_gap", "priority": 88.2 }
  ],
  "evidence": { "signal_count": 12 }
}
```

> If MS1's payload uses different field names, the only change needed is in
> `services/scoring_agent/contracts.py::DiagnosticAnswersView.from_raw` — one place.

## Write contract — `scores` (consumed by MS3)

MS2 always writes exactly **five** score objects, keyed `environmental`, `social`,
`governance`, `compliance`, `overall`. Stored shape (`schema_version: ms2.scores.v1`):

```jsonc
{
  "schema_version": "ms2.scores.v1",
  "project_id": "…",
  "generated_at": "2026-06-20T…Z",
  "method": "rule" | "rule+llm",
  "diagnostic_schema_version": "ms1.diagnostic.v1",
  "overall_score": 14.0,
  "overall_band": "at_risk",
  "scores": [
    {
      "key": "environmental",
      "label": "Environmental",
      "score": 12.0,                       // 0–100
      "band": "at_risk",                   // at_risk | developing | established | leading
      "confidence": 0.78,                  // 0–1
      "justification": "…",                // LLM-written, or deterministic fallback
      "drivers": ["…"],
      "evidence_refs": ["sig_…"],          // signal ids from MS1's diagnostic
      "inputs": { "evidenced_score": 0.2, "gap": 0.7, "coverage": 1.0 },
      "tool": "environmental_score",
      "computed_at": "2026-06-20T…Z"
    }
    // …social, governance, compliance, overall
  ]
}
```

**Guarantees for MS3:** `scores` is either absent (MS2 hasn't run) or contains all five
keys; `overall_score`/`overall_band` are mirrored at the top level for a cheap read.

## How each side calls it

```python
# MS2 (me) — once at startup
await ScoreRepository(pool).ensure_schema()      # additive; safe alongside MS1's

# MS2 — per project, after MS1 has written
agent = ScoringAgent(repository=ScoreRepository(pool),
                     justifier=JustificationWriter())   # justifier optional
await agent.score_project(project_id=pid, tenant_id=tid)

# MS3 (teammate) — read my output
SELECT scores FROM project_profiles WHERE project_id = $1;
```
