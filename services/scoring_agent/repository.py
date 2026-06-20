"""Persistence for the Scoring Agent — strictly additive and column-scoped.

Merge safety is the priority here. ``project_profiles`` is shared with MS1 (which owns
``diagnostic_answers``); this repository:

* provisions only **additive** schema (``ADD COLUMN IF NOT EXISTS``), never redefining
  the table, so it composes with whatever MS1's migration created;
* reads ``diagnostic_answers`` (MS1's column) and writes only ``scores`` /
  ``scores_*`` (our columns) via an ``UPDATE`` — it never inserts a bare row or touches
  another team's columns;
* refuses to write if MS1 hasn't produced a diagnostic yet
  (:class:`DiagnosticNotReadyError`), matching the MS1 → MS2 → MS3 ordering;
* keeps an append-only ``project_scores_history`` audit trail of every scoring run.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from services.common.exceptions import DiagnosticNotReadyError, PersistenceError
from services.common.observability import MetricsSink, get_metrics
from services.common.resilience import retry_call
from services.scoring_agent.contracts import ScoreSet

# Additive only — does NOT own or redefine project_profiles. The minimal CREATE keeps
# standalone use working; the ALTERs are no-ops once MS1's migration has run.
_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS project_profiles (
    project_id UUID PRIMARY KEY
);
ALTER TABLE project_profiles ADD COLUMN IF NOT EXISTS diagnostic_answers JSONB;
ALTER TABLE project_profiles ADD COLUMN IF NOT EXISTS scores JSONB;
ALTER TABLE project_profiles ADD COLUMN IF NOT EXISTS scores_schema_version TEXT;
ALTER TABLE project_profiles ADD COLUMN IF NOT EXISTS scores_updated_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS project_scores_history (
    id              BIGSERIAL PRIMARY KEY,
    project_id      UUID NOT NULL,
    tenant_id       UUID,
    scores          JSONB NOT NULL,
    overall_score   DOUBLE PRECISION,
    schema_version  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS project_scores_history_idx
    ON project_scores_history (project_id, created_at DESC);
"""


def _as_dict(value: Any) -> dict[str, Any] | None:
    """asyncpg may hand back JSONB as str, bytes, or an already-decoded dict."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        return json.loads(value)
    return None


class ScoreRepository:
    """Reads MS1's diagnostic and writes MS2's scores on ``project_profiles``."""

    def __init__(self, pool, *, metrics: MetricsSink | None = None) -> None:
        self._pool = pool
        self._metrics = metrics or get_metrics()

    async def ensure_schema(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(_SCHEMA_DDL)

    async def read_diagnostic_answers(
        self, project_id: uuid.UUID
    ) -> dict[str, Any] | None:
        """Read the MS1 contract for a project (``None`` if not yet produced)."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT diagnostic_answers FROM project_profiles WHERE project_id = $1;",
                project_id,
            )
        if row is None:
            return None
        return _as_dict(row["diagnostic_answers"])

    async def write_scores(
        self,
        project_id: uuid.UUID,
        score_set: ScoreSet,
        *,
        tenant_id: uuid.UUID | None = None,
    ) -> None:
        """Write the score set into our columns only; append a history row.

        Uses ``UPDATE`` (not upsert): the project row must already exist because MS1
        writes ``diagnostic_answers`` first. A missing row means scoring ran out of
        order → :class:`DiagnosticNotReadyError`.
        """
        payload = json.dumps(score_set.model_dump(mode="json"))

        async def _persist() -> bool:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    updated = await conn.fetchval(
                        """
                        UPDATE project_profiles
                        SET scores = $2::jsonb,
                            scores_schema_version = $3,
                            scores_updated_at = now()
                        WHERE project_id = $1
                        RETURNING project_id;
                        """,
                        project_id,
                        payload,
                        score_set.schema_version,
                    )
                    if updated is None:
                        return False
                    await conn.execute(
                        """
                        INSERT INTO project_scores_history (
                            project_id, tenant_id, scores, overall_score, schema_version
                        )
                        VALUES ($1, $2, $3::jsonb, $4, $5);
                        """,
                        project_id,
                        tenant_id,
                        payload,
                        score_set.overall_score,
                        score_set.schema_version,
                    )
                    return True

        try:
            persisted = await retry_call(_persist, attempts=3, base_delay=0.2)
        except Exception as exc:  # noqa: BLE001 - normalise to a domain error
            self._metrics.increment("scoring.persist.errors")
            raise PersistenceError("failed to persist scores") from exc

        if not persisted:
            raise DiagnosticNotReadyError(
                f"no project_profiles row for {project_id}; MS1 diagnostic not written yet"
            )
        self._metrics.increment("scoring.scores.persisted")

    async def read_scores(self, project_id: uuid.UUID) -> dict[str, Any] | None:
        """Read back the stored scores (symmetry / MS3-side testing)."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT scores FROM project_profiles WHERE project_id = $1;",
                project_id,
            )
        if row is None:
            return None
        return _as_dict(row["scores"])
