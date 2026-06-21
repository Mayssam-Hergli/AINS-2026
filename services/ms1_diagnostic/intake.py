"""MS1 intake — validate a venture questionnaire and write ``diagnostic_answers``.

This is the active MS1 path for the Massar workflow: it takes a founder's raw
questionnaire answers, validates them against the :mod:`answer_schema` contract, and
writes the flat key/value object into ``project_profiles.diagnostic_answers`` for the
scoring agent (MS2) to read directly.

It mirrors the team's endpoint shape — ``PATCH /profiles/{id}/answers`` with body
``{"diagnostic_answers": {...all keys...}}`` — so wiring it behind that route is a
thin adapter. Persistence is additive and column-scoped (writes only the answer
columns), so it composes with whatever owns the rest of ``project_profiles``.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from services.common.config import Settings, get_settings
from services.common.exceptions import AnswerValidationError, PersistenceError
from services.common.observability import (
    MetricsSink,
    bind_correlation_id,
    get_metrics,
    track,
)
from services.common.resilience import retry_call
from services.ms1_diagnostic.answer_schema import (
    ANSWERS_SCHEMA_VERSION,
    build_diagnostic_answers,
    validate_answers,
)

logger = logging.getLogger(__name__)

# Additive only — does not redefine project_profiles. Writes only the answer columns.
_ANSWERS_DDL = """
CREATE TABLE IF NOT EXISTS project_profiles (
    project_id UUID PRIMARY KEY
);
ALTER TABLE project_profiles ADD COLUMN IF NOT EXISTS tenant_id UUID;
ALTER TABLE project_profiles ADD COLUMN IF NOT EXISTS diagnostic_answers JSONB;
ALTER TABLE project_profiles ADD COLUMN IF NOT EXISTS answers_schema_version TEXT;
ALTER TABLE project_profiles ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1;
ALTER TABLE project_profiles ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE TABLE IF NOT EXISTS project_answers_history (
    id                  BIGSERIAL PRIMARY KEY,
    project_id          UUID NOT NULL,
    tenant_id           UUID,
    diagnostic_answers  JSONB NOT NULL,
    schema_version      TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS project_answers_history_idx
    ON project_answers_history (project_id, created_at DESC);
"""


def _as_dict(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        return json.loads(value)
    return None


class AnswerRepository:
    """Upserts the flat ``diagnostic_answers`` object for MS2 to read."""

    def __init__(self, pool, *, metrics: MetricsSink | None = None) -> None:
        self._pool = pool
        self._metrics = metrics or get_metrics()

    async def ensure_schema(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(_ANSWERS_DDL)

    async def upsert_answers(
        self,
        project_id: uuid.UUID,
        diagnostic_answers: dict[str, Any],
        *,
        tenant_id: uuid.UUID | None = None,
    ) -> int:
        """Write the answers, append a history revision, and return the revision."""
        payload = json.dumps(diagnostic_answers)
        upsert = """
            INSERT INTO project_profiles (project_id, tenant_id, diagnostic_answers,
                                          answers_schema_version)
            VALUES ($1, $2, $3::jsonb, $4)
            ON CONFLICT (project_id) DO UPDATE SET
                tenant_id = EXCLUDED.tenant_id,
                diagnostic_answers = EXCLUDED.diagnostic_answers,
                answers_schema_version = EXCLUDED.answers_schema_version,
                revision = project_profiles.revision + 1,
                updated_at = now()
            RETURNING revision;
        """
        history = """
            INSERT INTO project_answers_history (project_id, tenant_id,
                                                 diagnostic_answers, schema_version)
            VALUES ($1, $2, $3::jsonb, $4);
        """

        async def _persist() -> int:
            async with self._pool.acquire() as conn:
                async with conn.transaction():
                    revision = await conn.fetchval(
                        upsert, project_id, tenant_id, payload, ANSWERS_SCHEMA_VERSION
                    )
                    await conn.execute(
                        history, project_id, tenant_id, payload, ANSWERS_SCHEMA_VERSION
                    )
                    return int(revision)

        try:
            revision = await retry_call(_persist, attempts=3, base_delay=0.2)
        except Exception as exc:  # noqa: BLE001 - normalise to a domain error
            self._metrics.increment("ms1.answers.persist_errors")
            raise PersistenceError("failed to persist diagnostic_answers") from exc

        self._metrics.increment("ms1.answers.saved")
        return revision

    async def read_answers(self, project_id: uuid.UUID) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT diagnostic_answers FROM project_profiles WHERE project_id = $1;",
                project_id,
            )
        if row is None:
            return None
        return _as_dict(row["diagnostic_answers"])


class IntakeService:
    """Validates a questionnaire submission and persists the MS1 → MS2 contract."""

    def __init__(
        self,
        *,
        repository: AnswerRepository | None = None,
        settings: Settings | None = None,
        metrics: MetricsSink | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings or get_settings()
        self._metrics = metrics or get_metrics()

    async def submit(
        self,
        *,
        project_id: uuid.UUID,
        answers: dict[str, Any],
        tenant_id: uuid.UUID | None = None,
        persist: bool = True,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Validate + build + (optionally) persist. Returns the diagnostic_answers dict."""
        with bind_correlation_id(correlation_id), track("ms1.intake"):
            issues = validate_answers(answers)
            if issues:
                self._metrics.increment("ms1.intake.rejected")
                raise AnswerValidationError(
                    f"{len(issues)} invalid answer(s) for project {project_id}",
                    issues=issues,
                )

            diagnostic_answers = build_diagnostic_answers(answers)

            if persist:
                if self._repository is None:
                    raise RuntimeError("persist=True requires an AnswerRepository")
                revision = await self._repository.upsert_answers(
                    project_id, diagnostic_answers, tenant_id=tenant_id
                )
                logger.info(
                    "Stored diagnostic_answers for project %s (rev %d, %d keys)",
                    project_id, revision, len(diagnostic_answers),
                )

            self._metrics.increment("ms1.intake.completed")
            return diagnostic_answers
