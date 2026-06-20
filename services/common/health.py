"""Liveness and readiness probes for orchestrators (Kubernetes, load balancers).

Liveness answers "is the process alive?"; readiness answers "can it serve traffic?"
— principally, can it reach its database. Readiness checks are bounded by a timeout so
a slow dependency can't wedge the probe itself.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from services.common.resilience import with_timeout

logger = logging.getLogger(__name__)


class HealthStatus(BaseModel):
    status: str  # "ok" | "degraded" | "down"
    checks: dict[str, str] = Field(default_factory=dict)


class HealthCheck:
    """Aggregates dependency checks into a single readiness verdict."""

    def __init__(self, *, pool=None, probe_timeout: float = 2.0) -> None:
        self._pool = pool
        self._probe_timeout = probe_timeout

    async def liveness(self) -> HealthStatus:
        return HealthStatus(status="ok", checks={"process": "ok"})

    async def readiness(self) -> HealthStatus:
        checks: dict[str, str] = {}
        healthy = True

        if self._pool is not None:
            try:
                await with_timeout(self._check_database(), self._probe_timeout)
                checks["database"] = "ok"
            except Exception as exc:  # noqa: BLE001 - any failure means not ready
                logger.warning("Readiness DB check failed: %s", exc)
                checks["database"] = "down"
                healthy = False
        else:
            checks["database"] = "not_configured"

        return HealthStatus(status="ok" if healthy else "down", checks=checks)

    async def _check_database(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("SELECT 1;")
