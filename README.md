# Sustainability & Compliance Assessment Platform — Backend Services

Backend services for an enterprise sustainability / compliance assessment platform.
This repository contains **my** part of a multi-agent system: the document ingestion
pipeline, the diagnostic engine, and the scoring agent that sits between two
teammate-owned agents. All services are async, typed (Pydantic), and integrate through
a shared **PostgreSQL + pgvector** database rather than by calling each other directly.

---

## What this delivers

Three production-grade services plus a shared platform layer:

| Service | What it does |
|---|---|
| **File Parser** (`services/file_parser`) | Ingests uploaded documents (PDF / DOCX / CSV / XLSX) → extracts and normalizes them into typed, embedded **signals** (the documentary "reality") |
| **MS1 — Diagnostic Engine** (`services/ms1_diagnostic`) | Runs a branching questionnaire (perception), compares it against the parsed signals (reality), ranks blockers, and classifies maturity → writes `diagnostic_answers` |
| **MS2 — Scoring Agent** (`services/scoring_agent`) | Reads `diagnostic_answers`, runs 5 scoring tools, writes 5 score objects → `scores` |
| **Common platform** (`services/common`) | Cross-cutting concerns: config, structured observability, resilience, health, typed errors |

### Where this fits in the team workflow

```
MS1 Agent (teammate)     writes  diagnostic_answers ─┐
                                                     ▼
MS2 Scoring Agent (mine) reads   diagnostic_answers
                         writes  scores (5 objects)  ─┐
                                                      ▼
MS3 Agent (teammate)     reads   scores  → decides KB retrieval
```

No service calls another directly — each stage reads what the previous wrote to the
shared `project_profiles` table. The exact column ownership and JSON shapes are pinned
down in **[INTEGRATION.md](INTEGRATION.md)** (the merge contract).

---

## Architecture

```
                ┌─────────────────────────────────────────────────────────┐
   documents ──▶│ File Parser:  extract → normalize → embed → persist      │
  (PDF/DOCX/    │   pdfplumber / python-docx / pandas  →  ExtractedSignal  │
   CSV/XLSX)    └───────────────┬─────────────────────────────────────────┘
                                │ document_signals (pgvector)
                                ▼
   questionnaire ──▶ ┌──────────────────────────────────────────────────┐
   answers           │ MS1 Diagnostic Engine                            │
                     │   QuestionGraph (DAG) → GapDetector              │
                     │   → BlockerRanker → RuleEngine + structured LLM  │
                     └───────────────┬──────────────────────────────────┘
                                     │ diagnostic_answers (JSONB)
                                     ▼
                     ┌──────────────────────────────────────────────────┐
                     │ MS2 Scoring Agent                                │
                     │   5 tools → justifier (LLM) → 5 score objects   │
                     └───────────────┬──────────────────────────────────┘
                                     │ scores (JSONB)  →  consumed by MS3
                                     ▼
                            project_profiles  (PostgreSQL + pgvector)
```

---

## Repository layout

```
services/
├── common/                 # Cross-cutting platform layer
│   ├── config.py           #   env-driven Settings tree (APP_* vars)
│   ├── exceptions.py       #   rooted PlatformError hierarchy
│   ├── observability.py    #   JSON logging, correlation IDs, metrics sink
│   ├── resilience.py       #   retry, circuit breaker, timeout, concurrency gate
│   └── health.py           #   liveness / readiness probes
│
├── file_parser/            # Document ingestion → typed, embedded signals
│   ├── extractors.py       #   async pdfplumber / python-docx / pandas extractors
│   ├── normalizer.py       #   signal taxonomy + value parsing (shared contract)
│   └── core.py             #   pipeline orchestration + pgvector persistence
│
├── ms1_diagnostic/         # Perception-vs-reality diagnostic
│   ├── questions.py        #   branching DAG questionnaire + answer validation
│   ├── gap_detector.py     #   perception vs. evidenced reality per domain
│   ├── blocker_ranker.py   #   multi-criteria priority blocker matrix
│   └── engine.py           #   maturity classifier (RuleEngine + structured LLM)
│
└── scoring_agent/          # MS2: reads diagnostic, writes 5 scores
    ├── contracts.py        #   THE merge interface (read view + write schema)
    ├── tools.py            #   5 scoring tools (4 pillars + overall)
    ├── justifier.py        #   LLM justification writer (resilient, optional)
    ├── repository.py       #   merge-safe, additive, column-scoped persistence
    └── agent.py            #   ScoringAgent orchestration

INTEGRATION.md              # Shared-DB merge contract (column ownership + schemas)
requirements.txt
```

---

## The services in detail

### 1. File Parser (`services/file_parser`)

Turns messy documents into clean, typed evidence.

- **Extractors** (`extractors.py`) — one per file type (`pdfplumber`, `python-docx`,
  `pandas`), all behind a uniform async `extract()` that offloads the blocking
  libraries to threads. An `ExtractorRegistry` resolves by content-type or extension.
- **Normalizer** (`normalizer.py`) — classifies each fragment into a domain
  (`environmental / social / governance / compliance / …`) and type
  (`metric / target / policy / certification / statement / date`), parses numeric
  values **only when attached to a recognized unit** (so years/ISO codes don't become
  fake metrics), and deduplicates by content hash. Produces `ExtractedSignal` objects —
  **the shared contract** that MS1 consumes.
- **Pipeline** (`core.py`) — `extract → normalize → embed → persist`. Signals get
  1536-dim embeddings (pluggable `Embedder`, cached, with a deterministic offline
  default) and are written to the pgvector `document_signals` table.

Enterprise hardening: file-size + content-type validation, content-hash idempotency,
bounded batch concurrency, embedding cache, resilient persistence, and
correlation-scoped logging/metrics.

### 2. MS1 — Diagnostic Engine (`services/ms1_diagnostic`)

Compares what an organisation *claims* against what its documents *prove*.

- **`questions.py`** — a DAG of branching questions (answering "CSRD in scope?" = yes
  unlocks ESRS follow-ups). Cycle detection at build time; traversal computes active /
  next / coverage; `validate_answers` rejects malformed input.
- **`gap_detector.py`** — per domain, computes **perceived** maturity (from answers)
  vs. **evidenced** maturity (from signals) → flags **overclaims** (confident but
  unsupported) and **hidden strengths** (under-reported).
- **`blocker_ranker.py`** — a transparent weighted decision matrix
  (impact / regulatory exposure / urgency / effort / dependency) turning gaps into a
  ranked, auditable blocker list.
- **`engine.py`** — a deterministic `RuleEngine` produces the authoritative maturity
  level (1–5), and a structured **Claude** call (`claude-opus-4-8`) adds an enriching
  second opinion + divergence check. The result is serialized to the
  `diagnostic_answers` JSONB contract on `project_profiles`, with an append-only
  history table for audit.

### 3. MS2 — Scoring Agent (`services/scoring_agent`)

Sits between teammate-owned MS1 and MS3.

- **`contracts.py`** — the merge interface: a **tolerant** `DiagnosticAnswersView`
  reader over MS1's payload, and the `ScoreObject` / `ScoreSet` write schema for MS3.
- **`tools.py`** — the **5 scoring tools**: four ESG/compliance pillar scorers
  (reality-anchored, penalized for overclaims, weighted by coverage) and one composite
  `overall` scorer with a systemic-risk penalty for high-priority blockers. Scores are
  deterministic and auditable.
- **`justifier.py`** — Claude writes audit-quality justifications for the numbers in one
  structured call; falls back to deterministic text if the LLM is unavailable.
- **`repository.py`** — **merge-safe**: additive-only schema, `UPDATE`-only writes that
  touch *only* the `scores*` columns, ordering enforcement
  (`DiagnosticNotReadyError` if MS1 hasn't run), and an audit-history table.

### 4. Common platform (`services/common`)

- **`config.py`** — one immutable, env-driven `Settings` tree (`APP_*`).
- **`observability.py`** — JSON structured logging, a `correlation_id` that flows
  through async chains into every log line, and a pluggable `MetricsSink`
  (in-memory default; swap for Prometheus/OTel without touching call sites).
- **`resilience.py`** — `retry`/`retry_async`, `AsyncCircuitBreaker`, `with_timeout`,
  `BoundedGate`.
- **`health.py`** — liveness + DB-backed readiness probes.
- **`exceptions.py`** — a rooted `PlatformError` hierarchy mapping cleanly to HTTP codes.

---

## Data contracts (shared `project_profiles` table)

| Column | Owner | Written by |
|---|---|---|
| `diagnostic_answers` (JSONB) | MS1 | MS1 Diagnostic Engine |
| `scores` (JSONB) | MS2 (mine) | MS2 Scoring Agent |
| `document_signals` (separate pgvector table) | File Parser | File Parser |

Full field-level schemas and merge rules: see **[INTEGRATION.md](INTEGRATION.md)**.

---

## Installation

```bash
python -m pip install -r requirements.txt
```

Runtime dependencies: `pydantic`, `pdfplumber`, `python-docx`, `pandas`, `openpyxl`,
`asyncpg`, `anthropic`. The `anthropic` and `asyncpg` packages are **lazy-loaded** —
the in-memory logic (parsing, diagnosis, scoring) runs and is testable without them.

Set your Anthropic key to enable the structured-LLM layers (both degrade gracefully if
absent):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

---

## Quickstart

### Parse a document into signals

```python
import asyncio, uuid
from services.file_parser import FileParserService, ParseRequest, SignalRepository

async def main(pool):
    repo = SignalRepository(pool)
    await repo.ensure_schema()
    parser = FileParserService(repository=repo)
    doc = await parser.parse(ParseRequest(
        project_id=uuid.uuid4(),
        filename="sustainability_report.pdf",
        data=open("report.pdf", "rb").read(),
        content_type="application/pdf",
    ))
    print(len(doc.signals), "signals extracted")
```

### Run the diagnostic (MS1)

```python
from services.ms1_diagnostic import DiagnosticEngine, ProjectProfileRepository, LLMMaturityClassifier

engine = DiagnosticEngine(
    repository=ProjectProfileRepository(pool),
    llm_classifier=LLMMaturityClassifier(),   # optional; omit for rule-engine only
)
result = await engine.diagnose(
    project_id=pid,
    answers={"c_csrd_scope": True, "e_emissions_tracking": True, ...},
    signals=doc.signals,
    tenant_id=tenant_id,
)
print(result.overall.maturity_level, result.overall.maturity_label)
```

### Score a project (MS2)

```python
from services.scoring_agent import ScoringAgent, ScoreRepository, JustificationWriter

repo = ScoreRepository(pool)
await repo.ensure_schema()                      # additive; safe alongside MS1's schema
agent = ScoringAgent(repository=repo, justifier=JustificationWriter())
score_set = await agent.score_project(project_id=pid, tenant_id=tenant_id)
print(score_set.overall_score, score_set.overall_band)   # consumed by MS3
```

---

## Configuration

All tunables are environment variables under the `APP_` prefix (see
`services/common/config.py`). Common ones:

| Variable | Default | Purpose |
|---|---|---|
| `APP_DATABASE_DSN` | – | PostgreSQL connection string |
| `APP_PARSER_MAX_FILE_BYTES` | `26214400` | Upload size limit (25 MiB) |
| `APP_PARSER_MAX_CONCURRENCY` | `8` | Parallel document parses |
| `APP_LLM_ENABLED` | `true` | Toggle the structured-LLM layers |
| `APP_LLM_MODEL` | `claude-opus-4-8` | Model id |
| `APP_LLM_TIMEOUT_SECONDS` | `45` | Per-LLM-call timeout |
| `APP_CIRCUIT_FAILURE_THRESHOLD` | `5` | Failures before a circuit opens |
| `APP_SCORING_OVERCLAIM_PENALTY` | `0.4` | How hard overclaims lower a pillar score |
| `APP_LOG_JSON` | `true` | JSON vs. human logs |

---

## Operational notes

- Call `configure_logging(...)` once at process startup.
- Call each repository's `ensure_schema()` once at startup. The Scoring Agent's
  migration is **additive** and composes safely with MS1's, in any order.
- Health probes: `HealthCheck(pool=pool).readiness()` for Kubernetes/load balancers.
- Every service is tenant-aware (`tenant_id`) and keeps an append-only history table,
  for multi-tenant isolation and regulated-disclosure audit.

---

## Status

All three services and the platform layer compile and pass end-to-end smoke tests
(document parsing, branching diagnostic, perception/reality gap detection, blocker
ranking, five-band scoring, merge-safe persistence, retry/circuit-breaker/validation,
JSON logging with correlation IDs). The LLM layers are optional and degrade to the
deterministic engines when the API is unavailable.
