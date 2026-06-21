"""An in-memory stand-in for an asyncpg pool.

It implements just enough of asyncpg's surface (`acquire`, `execute`, `executemany`,
`fetchrow`, `fetchval`, `transaction`) for the repositories to run unchanged, backed
by a plain dict. This lets the demo and the test suite exercise the *real* persistence
code — including the merge-safe `project_profiles` contract — without a live database.

It dispatches on SQL keywords, mirroring the exact statements the repositories issue:
  - `executemany(... document_signals ...)`      → store signals
  - `fetchval(INSERT INTO project_profiles ...)`  → MS1 upsert, returns revision
  - `fetchval(UPDATE project_profiles ...)`       → MS2 scores write, returns project_id
  - `fetchrow(SELECT diagnostic_answers ...)`     → read MS1 output
  - `fetchrow(SELECT scores ...)`                 → read MS2 output
"""

from __future__ import annotations

from typing import Any


class _Tx:
    async def __aenter__(self) -> "_Tx":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None


class _Conn:
    def __init__(self, store: dict[str, Any]) -> None:
        self._store = store

    def transaction(self) -> _Tx:
        return _Tx()

    async def execute(self, query: str, *args: Any) -> str:
        q = query.strip()
        if q.startswith("INSERT INTO project_profiles_history"):
            self._store["ms1_history"].append(args)
        elif q.startswith("INSERT INTO project_scores_history"):
            self._store["ms2_history"].append(args)
        elif q.startswith("INSERT INTO project_answers_history"):
            self._store.setdefault("answers_history", []).append(args)
        # DDL (CREATE/ALTER/EXTENSION) and "SELECT 1" health checks are no-ops.
        return "OK"

    async def executemany(self, query: str, records: list[tuple]) -> None:
        if "document_signals" in query:
            self._store["signals"].extend(records)
        return None

    async def fetchval(self, query: str, *args: Any) -> Any:
        q = query.strip()
        profiles = self._store["profiles"]
        if q.startswith("INSERT INTO project_profiles"):
            project_id = args[0]
            row = profiles.setdefault(project_id, {"revision": 0})
            if len(args) >= 6:
                # MS1 ESG diagnostic upsert ... RETURNING revision
                _, tenant_id, diag, level, label, schema = args[:6]
                row.update(tenant_id=tenant_id, diagnostic_answers=diag,
                           maturity_level=level, maturity_label=label, schema_version=schema)
            else:
                # MS1 intake answers upsert: (project_id, tenant_id, diag, schema)
                _, tenant_id, diag, schema = args
                row.update(tenant_id=tenant_id, diagnostic_answers=diag,
                           answers_schema_version=schema)
            row["revision"] += 1
            return row["revision"]
        if q.startswith("UPDATE project_profiles"):
            # MS2 scores write ... RETURNING project_id (None if row missing)
            project_id, scores, schema = args
            if project_id not in profiles:
                return None
            profiles[project_id].update(scores=scores, scores_schema_version=schema)
            return project_id
        return None

    async def fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
        q = query.strip()
        project_id = args[0]
        row = self._store["profiles"].get(project_id)
        if row is None:
            return None
        if "diagnostic_answers" in q:
            return {"diagnostic_answers": row.get("diagnostic_answers")}
        if "scores" in q:
            return {"scores": row.get("scores")}
        return None


class _Acquire:
    def __init__(self, store: dict[str, Any]) -> None:
        self._store = store

    async def __aenter__(self) -> _Conn:
        return _Conn(self._store)

    async def __aexit__(self, *exc: Any) -> None:
        return None


class InMemoryPool:
    """Minimal asyncpg-pool-compatible object backed by a dict."""

    def __init__(self) -> None:
        self.store: dict[str, Any] = {
            "profiles": {},
            "signals": [],
            "ms1_history": [],
            "ms2_history": [],
        }

    def acquire(self) -> _Acquire:
        return _Acquire(self.store)
