"""Structured logging, correlation IDs, and a pluggable metrics sink.

Enterprise services need every log line and metric to be traceable to a single
request across service boundaries. This module provides:

* a :data:`correlation_id` context variable + :func:`bind_correlation_id` so one
  identifier flows through async call chains and into every log record;
* JSON-structured logging (:func:`configure_logging`) suitable for log aggregators;
* a :class:`MetricsSink` protocol with an in-memory default, so counters/timers can
  be redirected to Prometheus/OpenTelemetry in production without touching call sites.
"""

from __future__ import annotations

import contextlib
import json
import logging
import time
import uuid
from contextvars import ContextVar
from functools import wraps
from typing import Any, Awaitable, Callable, Iterator, Protocol, TypeVar

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Correlation IDs
# ---------------------------------------------------------------------------

def get_correlation_id() -> str | None:
    return _correlation_id.get()


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


@contextlib.contextmanager
def bind_correlation_id(value: str | None = None) -> Iterator[str]:
    """Bind a correlation id for the duration of the block (generating one if absent)."""
    cid = value or uuid.uuid4().hex
    token = _correlation_id.set(cid)
    try:
        yield cid
    finally:
        _correlation_id.reset(token)


# ---------------------------------------------------------------------------
# Structured logging
# ---------------------------------------------------------------------------

class _CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id() or "-"
        return True


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key, value in getattr(record, "extra_fields", {}).items():
            payload[key] = value
        return json.dumps(payload, default=str)


def configure_logging(*, level: str = "INFO", json_output: bool = True) -> None:
    """Configure root logging once for the process."""
    handler = logging.StreamHandler()
    handler.addFilter(_CorrelationFilter())
    if json_output:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(correlation_id)s] %(name)s: %(message)s"
            )
        )
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

class MetricsSink(Protocol):
    """Minimal counter/histogram interface, tag-aware."""

    def increment(self, name: str, value: float = 1.0, **tags: str) -> None: ...

    def observe(self, name: str, value: float, **tags: str) -> None: ...


class NullMetrics:
    """No-op sink used when metrics are disabled."""

    def increment(self, name: str, value: float = 1.0, **tags: str) -> None:  # noqa: D401
        return None

    def observe(self, name: str, value: float, **tags: str) -> None:
        return None


class InMemoryMetrics:
    """In-process counters/observations — useful for tests and a /metrics endpoint."""

    def __init__(self) -> None:
        self.counters: dict[str, float] = {}
        self.observations: dict[str, list[float]] = {}

    @staticmethod
    def _key(name: str, tags: dict[str, str]) -> str:
        if not tags:
            return name
        rendered = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}{{{rendered}}}"

    def increment(self, name: str, value: float = 1.0, **tags: str) -> None:
        self.counters[self._key(name, tags)] = (
            self.counters.get(self._key(name, tags), 0.0) + value
        )

    def observe(self, name: str, value: float, **tags: str) -> None:
        self.observations.setdefault(self._key(name, tags), []).append(value)

    def snapshot(self) -> dict[str, Any]:
        return {
            "counters": dict(self.counters),
            "observations": {k: list(v) for k, v in self.observations.items()},
        }


_metrics: MetricsSink = InMemoryMetrics()


def get_metrics() -> MetricsSink:
    return _metrics


def set_metrics(sink: MetricsSink) -> None:
    global _metrics
    _metrics = sink


@contextlib.contextmanager
def track(name: str, *, metrics: MetricsSink | None = None, **tags: str) -> Iterator[None]:
    """Time a block and record ``<name>.duration_ms`` plus success/error counters."""
    sink = metrics or _metrics
    start = time.perf_counter()
    status = "ok"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        sink.observe(f"{name}.duration_ms", elapsed_ms, status=status, **tags)
        sink.increment(f"{name}.calls", status=status, **tags)


def timed(name: str) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator that times an async function via :func:`track`."""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            with track(name):
                return await func(*args, **kwargs)

        return wrapper

    return decorator
