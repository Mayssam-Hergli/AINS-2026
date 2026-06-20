"""Domain exception hierarchy shared across the platform.

A single rooted hierarchy lets callers (API handlers, workers, tests) catch broad
``PlatformError`` for a 500-style fallback while still distinguishing the cases that
map to specific HTTP statuses (validation → 4xx, persistence/LLM → 5xx, circuit
open → 503).
"""

from __future__ import annotations


class PlatformError(Exception):
    """Base class for every error raised by platform services."""


class ConfigurationError(PlatformError):
    """Invalid or missing configuration."""


class ValidationError(PlatformError):
    """Caller-supplied input failed validation (maps to HTTP 4xx)."""

    def __init__(self, message: str, issues: list[str] | None = None) -> None:
        super().__init__(message)
        self.issues = issues or []


class AnswerValidationError(ValidationError):
    """Questionnaire answers did not conform to the question schema."""


class DocumentTooLargeError(ValidationError):
    """An uploaded document exceeded the configured size limit."""


class UnsupportedDocumentError(ValidationError):
    """No extractor can handle the supplied file type."""


class PersistenceError(PlatformError):
    """A database operation failed after exhausting retries."""


class LLMUnavailableError(PlatformError):
    """The structured-LLM layer could not be reached or returned no result."""


class DiagnosticNotReadyError(PlatformError):
    """Scoring was requested before MS1 wrote ``diagnostic_answers`` for the project.

    Maps naturally to HTTP 409/425 — the upstream agent has not produced its output
    yet, so the caller should retry once the diagnostic is available.
    """


class ScoringError(PlatformError):
    """A scoring tool failed to produce a valid result."""


class RetryExhaustedError(PlatformError):
    """A retried operation failed on every attempt."""

    def __init__(self, message: str, attempts: int, last_error: BaseException | None) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


class CircuitOpenError(PlatformError):
    """A circuit breaker is open and is fast-failing calls to protect a dependency."""
