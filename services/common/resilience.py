"""Resilience primitives: retry-with-backoff, circuit breaker, timeout, concurrency gate.

External dependencies (the database, the LLM API) fail transiently and sometimes go
hard down. These primitives keep the platform stable under those conditions:

* :func:`retry_call` / :func:`retry_async` — exponential backoff with jitter for
  transient failures.
* :class:`AsyncCircuitBreaker` — stops hammering a dependency that is down, failing
  fast until a cooldown elapses.
* :func:`with_timeout` — bounds any awaitable so a hung call can't block a worker.
* :class:`BoundedGate` — caps in-flight concurrency (e.g. parallel document parses).
"""

from __future__ import annotations

import asyncio
import enum
import logging
import random
import time
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

from services.common.exceptions import CircuitOpenError, RetryExhaustedError

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------

async def retry_call(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    attempts: int = 3,
    base_delay: float = 0.2,
    max_delay: float = 5.0,
    jitter: float = 0.1,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    give_up_on: tuple[type[BaseException], ...] = (),
    on_retry: Callable[[int, BaseException], None] | None = None,
    **kwargs: Any,
) -> T:
    """Call ``func`` with exponential backoff, raising :class:`RetryExhaustedError`."""
    last_error: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await func(*args, **kwargs)
        except give_up_on:
            raise
        except retry_on as exc:
            last_error = exc
            if attempt >= attempts:
                break
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay += random.uniform(0.0, jitter)
            if on_retry is not None:
                on_retry(attempt, exc)
            logger.warning(
                "Retry %d/%d after %.2fs due to %s", attempt, attempts, delay, exc
            )
            await asyncio.sleep(delay)
    raise RetryExhaustedError(
        f"{getattr(func, '__name__', 'operation')} failed after {attempts} attempts",
        attempts=attempts,
        last_error=last_error,
    )


def retry_async(
    *,
    attempts: int = 3,
    base_delay: float = 0.2,
    max_delay: float = 5.0,
    jitter: float = 0.1,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    give_up_on: tuple[type[BaseException], ...] = (),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator form of :func:`retry_call`."""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await retry_call(
                func,
                *args,
                attempts=attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                jitter=jitter,
                retry_on=retry_on,
                give_up_on=give_up_on,
                **kwargs,
            )

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------

class CircuitState(str, enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class AsyncCircuitBreaker:
    """A minimal async circuit breaker.

    After ``failure_threshold`` consecutive failures the circuit opens and calls
    fast-fail with :class:`CircuitOpenError` for ``reset_seconds``. One trial call is
    then allowed (half-open); success closes the circuit, failure re-opens it.
    """

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        reset_seconds: float = 30.0,
        name: str = "circuit",
    ) -> None:
        self._failure_threshold = max(failure_threshold, 1)
        self._reset_seconds = reset_seconds
        self._name = name
        self._failures = 0
        self._state = CircuitState.CLOSED
        self._opened_at = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    async def call(self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        await self._before_call()
        try:
            result = await func(*args, **kwargs)
        except Exception:
            await self._on_failure()
            raise
        await self._on_success()
        return result

    async def _before_call(self) -> None:
        async with self._lock:
            if self._state is CircuitState.OPEN:
                if time.monotonic() - self._opened_at >= self._reset_seconds:
                    self._state = CircuitState.HALF_OPEN
                    logger.info("Circuit %s half-open; allowing trial call", self._name)
                else:
                    raise CircuitOpenError(f"Circuit {self._name!r} is open")

    async def _on_success(self) -> None:
        async with self._lock:
            self._failures = 0
            if self._state is not CircuitState.CLOSED:
                logger.info("Circuit %s closed", self._name)
            self._state = CircuitState.CLOSED

    async def _on_failure(self) -> None:
        async with self._lock:
            self._failures += 1
            if (
                self._state is CircuitState.HALF_OPEN
                or self._failures >= self._failure_threshold
            ):
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                logger.warning(
                    "Circuit %s opened after %d failure(s)", self._name, self._failures
                )


# ---------------------------------------------------------------------------
# Timeout & concurrency
# ---------------------------------------------------------------------------

async def with_timeout(awaitable: Awaitable[T], seconds: float) -> T:
    """Await ``awaitable`` with a hard deadline (raises :class:`asyncio.TimeoutError`)."""
    return await asyncio.wait_for(awaitable, timeout=seconds)


class BoundedGate:
    """Caps the number of concurrent operations passing through it."""

    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._semaphore = asyncio.Semaphore(limit) if limit and limit > 0 else None

    async def __aenter__(self) -> "BoundedGate":
        if self._semaphore is not None:
            await self._semaphore.acquire()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._semaphore is not None:
            self._semaphore.release()
