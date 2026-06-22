# Massar — Architecture

> Living document. Update this whenever a module's structure or contract changes.
> Every Claude Code session should read this file before continuing work.

---

## System overview

```
React Frontend (FR/AR/Darija)
        |
   REST / JSON
        |
   API Gateway — FastAPI
   Auth · CORS · Rate limiting
        |
        |-- File Upload --> File Parser Service (pdfplumber, python-docx, pandas)
        |
        v
   MS1 — Diagnostic Engine (agent)
        |
        v
   PostgreSQL — shared database
        |
        v
   MS2 — Scoring Engine (agent)   <-- this is what I own
        |
        v
   MS3 — RAG & Roadmap (agent)
        |
        v
   Export Service — PDF / PNG reports
```

Each module (MS1, MS2, MS3) is built as an **agent**: a Claude model
constrained by a system prompt to only call deterministic tool functions.
The agent never invents a score, a classification, or a retrieved
resource — it orchestrates tool calls and writes natural-language
explanations from the tool outputs. This keeps every number traceable
and auditable, which is required by the judging criteria (Explainability
& Scoring Rigour, Evaluation & Rigour).

---

## Shared database — PostgreSQL

5 tables, this is the integration point between all modules. Modules
do not call each other directly — they read and write to these tables.

| Table | Written by | Read by | Contents |
|---|---|---|---|
| `project_profiles` | MS1, MS2 | MS2, MS3, Frontend | JSON shared state: diagnostic_answers, all 5 score objects |
| `diagnostic_outputs` | MS1 | MS2, MS3, Frontend | stage, blockers, gaps |
| `scores_history` | MS2 | MS3, Frontend | dimensions, timestamp — tracks score evolution over time |
| `roadmaps` | MS3 | Frontend, Export Service | actions, horizon (immediate/short/medium term) |
| `knowledge_base` | Person 2 (ingestion) | MS3 | pgvector embeddings of 41+ Tunisian resources |

---

## MS2 — Scoring Engine (owned by Person 1 / me)

### Data contract

**Reads from `project_profiles.diagnostic_answers`** — written by MS1.
Exact field names confirmed with MS1 owner (see open questions below
if not yet confirmed).

**Writes to `project_profiles`** — 5 separate keys:
`market_score`, `commercial_score`, `innovation_score`,
`scalability_score`, `green_score`.

Important detail discovered while building anomaly checks: raw
categorical answers (e.g. `offer_need_alignment`, `product_maturity`)
live in `diagnostic_answers` as strings. The score objects in
`all_scores` only hold **numeric** sub-score values — they do not
preserve the original category string. Any anomaly check that needs
the raw category (not just the numeric score) must read it from
`diagnostic_answers`, not reverse-engineer it from `all_scores`.
This is documented inline in `anomaly.py`.

### File structure

```
backend/scoring/
  green.py          DONE — pure function, UNDP formula
                     validated against 2 UNDP workshop examples
                     (Kilim tissage -> 7.0 total / 81.2 display /
                     "Très faible impact"; Briques ciment -> 15.0 total /
                     31.2 display / "Impact modéré")

  market.py          DONE — pure function, 3 weighted sub-criteria
                     (taille_marche 30%, validation_client 40%,
                     modele_revenus 30%). Validation is weighted
                     highest by design — a strong market_size score
                     cannot mask zero customer validation.

  commercial.py        DONE — pure function, 4 weighted sub-criteria
                       (proposition_valeur 30%, maturite_produit 25%,
                       strategie_pricing 25%, alignement_besoin 20%).
                       Tested with strong, weak, and a deliberately
                       contradictory profile (product fully built,
                       never validated) that fed directly into a new
                       anomaly check.

  innovation.py         DONE — pure function, 3 weighted sub-criteria
                        (nouveaute_locale 35%, intensite_technologique 30%,
                        barriere_entree 35%). IP protection bonus on
                        barrier_to_entry: pending+5, granted+15, capped at
                        100. 5 tests including IP cap verification and
                        banker's rounding checks (71.8, 75.2).

  scalability.py         DONE — pure function, 3 weighted sub-criteria
                         (replicabilite 35%, dependance_manuelle 30%,
                         potentiel_geographique 35%). manual_dependency
                         uses an inverted scale (high=10, none=100) — less
                         human intervention required = higher score.
                         4 tests including contradiction profile (73.0
                         composite masks dep_man=10, caught by anomaly.py)
                         and explicit inversion verification.

  anomaly.py               DONE — centralized cross-module anomaly
                           detection. Runs ONCE, after all 5 scores
                           exist, not duplicated per-module. Takes
                           diagnostic_answers + all_scores dict.
                           5 checks implemented (16 tests, all passing):
                             - market_no_validation (high)
                             - revenue_no_clients (high)
                             - scalability_manual_conflict (medium) —
                               cross-module: high scalability claim +
                               high manual dependency
                             - green_fundraising_risk (medium) —
                               cross-module: undp_raw_total >= 16 +
                               actively fundraising (pitch deck +
                               funding declared)
                             - product_built_unvalidated (medium) —
                               product_maturity == "product" AND
                               offer_need_alignment == "none".
                               Reads offer_need_alignment from
                               diagnostic_answers directly (see data
                               contract note above). Distinct from
                               market_no_validation: a founder can
                               pass (a) via general customer interviews
                               while still failing (e) because they
                               never validated THIS product against a
                               real need.

  engine.py         DONE — compute_all_scores(diagnostic_answers) -> dict.
                   Pure deterministic aggregator, zero LLM calls.
                   Calls all 5 modules in fixed order, then anomaly
                   detection. Returns:
                     "scores": {5 dimension results or error stubs}
                     "anomaly_flags": flat list from detect_all_anomalies
                     "low_scoring_dimensions": names with composite < 50
                     "green_pillars_flagged": pillar names with score >= 3
                   Partial-failure safe: missing fields in one dimension
                   return {composite: None, error: "...", sub_scores: {}}
                   without crashing the pipeline. Serves as regression
                   baseline — agent.py must produce identical composites.
                   3 tests: strong (no anomalies), overconfident founder
                   (3 anomalies, market LOW), incomplete (2 dims error,
                   engine survives).

  tools.py                   DONE — TOOLS list (6 Claude tool schemas)
                             + execute_tool(tool_name, tool_input) dispatcher.
                             Tool input for the 5 scoring tools IS the flat
                             diagnostic_answers dict — each function ignores
                             extra keys, so the agent passes the full dict
                             to every tool. detect_all_anomalies input:
                             {"diagnostic_answers": {...}, "all_scores": {...}}.
                             Guard: raises ValueError if all_scores missing
                             any of the 5 expected dimension keys — enforces
                             "call anomaly last" at execution level, not just
                             in the prompt. Error isolation mirrors engine.py:
                             missing fields -> {composite: None, error: ...}.
                             7 tests: schema shape, routing (all 6 tools),
                             guard (3 cases), consistency vs engine.py.

  system_prompt.py             DONE — SCORING_SYSTEM_PROMPT constant
                               (French, provider-agnostic, 5408 chars).
                               Constraint layer: agent forbidden from
                               inventing scores — every number comes
                               from a tool call. Fixed call order
                               enforced (market -> commercial ->
                               innovation -> scalability -> green ->
                               anomaly). JSON-only output: justifications
                               dict (text + improvement_action per dim)
                               + anomaly_summary. Null composite handling:
                               agent surfaces the uncertainty, never
                               fills with a made-up value. Tone:
                               professional French, addressed to a
                               Tunisian entrepreneur.

  llm_client.py                  DONE — single-function abstraction
                                 run_agent_turn(system, messages, tools).
                                 Only file that knows the active provider.
                                 Switch with LLM_PROVIDER env var (default
                                 "groq", also "anthropic"). For groq: uses
                                 openai library with Groq base_url, model
                                 llama-3.3-70b-versatile. For anthropic:
                                 uses anthropic library, claude-sonnet-4-6.
                                 Converts TOOLS from Anthropic schema shape
                                 (input_schema) to OpenAI shape (parameters)
                                 for Groq — one converter, zero duplication.
                                 Converts OpenAI message history to Anthropic
                                 format when provider=anthropic (groups tool
                                 results into single user message as required
                                 by Anthropic API). Returns normalized dict
                                 {text, tool_calls, stop_reason} regardless
                                 of provider — agent.py never sees a
                                 provider-specific object.

  agent.py                         DONE — run_scoring_agent(diagnostic_answers).
                                   Drives LLM to call 6 tools in fixed order,
                                   executes each via execute_tool (real
                                   deterministic code), enforces the anomaly
                                   guard at the CODE level too (not just in
                                   the prompt): detect_all_anomalies blocked
                                   until all 5 scores collected. Parses
                                   LLM's final JSON justification, retries
                                   once if malformed. Merges tool results
                                   (deterministic numbers) with LLM output
                                   (language layer). Returns same shape as
                                   engine.py plus justifications +
                                   anomaly_summary. _MAX_TURNS=12 safety cap.

  test_agent.py                      DONE — live integration test (3 tests).
                                     Skips gracefully if GROQ_API_KEY unset.
                                     Calls agent once, caches result, reuses
                                     across all 3 tests. Test 1 (critical):
                                     all 5 composites + anomaly codes must
                                     exactly match engine.compute_all_scores.
                                     Test 2: justifications present + non-
                                     empty for all 5 dims. Test 3: anomaly_
                                     summary present, low_scoring + green_
                                     pillars_flagged match engine values.

backend/api/
  auth.py                          DONE — POST /auth/register,
                                   POST /auth/login (OAuth2 form),
                                   GET /auth/me.

  scoring.py                       DONE — FastAPI router, 2 routes:
                                   POST /scores/compute/{profile_id}
                                     Reads diagnostic_answers, runs
                                     run_scoring_agent(), writes all 5
                                     score objects + anomaly data to
                                     project_profiles, appends a row to
                                     scores_history. Atomic: either the full
                                     result is written or nothing is (SQLite
                                     transaction). Returns full payload
                                     immediately (no second DB read needed).
                                     HTTP 502 if agent fails — DB untouched.
                                   GET /scores/{profile_id}
                                     Returns cached scores from DB without
                                     re-running the agent. 404 if not yet
                                     scored.
                                   Both routes owner-protected (user_id in
                                   WHERE clause) + require Bearer JWT.

backend/
  database.py                      DONE — SQLite via built-in sqlite3.
                                   get_db() dependency + init_db() on
                                   startup. Tables: users, project_profiles,
                                   scores_history. Swap for PostgreSQL by
                                   replacing only this file.

  security/auth.py                 DONE — JWT + pbkdf2_sha256 password
                                   hashing. get_current_user() dependency
                                   used by all protected routes.
```

### Output JSON shape — common to all 5 score modules

Pure scoring functions (green, market, commercial, innovation,
scalability) return ONLY their own numbers. No anomaly_flags key —
that was a mistake initially made in market.py and has been removed.
Anomaly detection is centralized in anomaly.py and runs after all 5
scores are computed.

```json
{
  "composite": 67.0,
  "sub_scores": {
    "criterion_name": {"value": 20, "weight": 0.40, "max": 100}
  }
}
```

Green Score has additional fields on top of this shape (undp_raw_total,
undp_classification, pillars instead of sub_scores — see green.py).

The anomaly check output (added separately, after all 5 scores exist):

```json
{
  "anomaly_flags": [
    {"code": "market_no_validation", "message": "...", "severity": "high"}
  ]
}
```

The NL justification text is added by the agent layer (agent.py), not
by the pure scoring functions — those stay deterministic and testable
in isolation.

---

## Integration points — who needs what from MS2

**MS1 (Diagnostic Engine)** — feeds MS2. I read
`diagnostic_answers` from `project_profiles`, written by them. I do
not call their agent directly.

Open question to confirm with MS1 owner: exact field names in
`diagnostic_answers`, and whether the Green Score specific fields
(energy_source, water_volume, zone_type, etc — 12 fields total) are
already collected by their questionnaire or need to be added.

**MS3 (RAG & Roadmap)** — reads MS2's output. They need two derived
signals, computed from my 5 score objects:
  - `low_scoring_dimensions` — any composite score below 50
  - `green_pillars_flagged` — any Green pillar with score >= 3

I have shared my exact output JSON shape with whoever owns MS3 so
they can build their retrieval query logic against the real contract,
not a guess.

**Frontend / Export Service** — renders my 5 score objects directly.
Needs: composite (for progress bars), sub_scores (for expandable
breakdowns), justification text, anomaly_flags (for warning badges),
and for Green Score specifically the undp_classification label with
color-coding:
  - undp_raw_total <= 7 -> success (green)
  - <= 11 -> warning (yellow)
  - <= 15 -> orange
  - <= 18 -> danger (red)
  - else -> critical (dark red)

---

## Testing approach

Every pure scoring function is validated BEFORE being wrapped as an
agent tool. Test files live alongside the module
(`test_green.py`, `test_market.py`, `test_commercial.py`,
`test_anomaly.py`). This is intentional — it proves the math is
correct independent of the agent, so when the agent is added on top,
any bug found is in the orchestration layer, not the formula.

green.py, market.py, and commercial.py are validated. anomaly.py has
16 tests covering all 5 checks, including a combined "overconfident
founder" profile where multiple anomalies fire together — useful
evidence for the "perception-reality gap detection is non-trivial"
judging bonus point.

---

## Status

| Module | Status |
|---|---|
| green.py | Done, tested, validated against UNDP examples |
| market.py | Done, tested |
| commercial.py | Done, tested |
| anomaly.py | Done, tested (16 tests, 5 checks) |
| innovation.py | Done, tested (5 tests, IP bonus + banker's rounding verified) |
| scalability.py | Done, tested (4 tests, inversion + contradiction verified) |
| engine.py | Done, tested (3 tests: strong / overconfident-founder / incomplete) |
| tools.py | Done, tested (7 tests: schema / routing / guard / consistency vs engine) |
| system_prompt.py | Done (5408 chars, French, all 6 rules verified) |
| llm_client.py | Done (Groq + Anthropic branches, normalized output) |
| agent.py | Done (loop + guard + JSON parse + merge) |
| test_agent.py | Done (3 tests, skips without key, API called once) |
| api/auth.py | Done (register, login, me) |
| api/scoring.py | Done (POST compute + GET cached) |
| database.py | Done (SQLite, swappable) |
| security/auth.py | Done (JWT + pbkdf2_sha256) |
