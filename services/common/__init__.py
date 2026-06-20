"""Cross-cutting platform concerns shared by all services.

Configuration, structured observability, resilience primitives, health probes, and a
common exception hierarchy. Imports nothing from the feature services, so it can be a
dependency of any of them without creating a cycle.
"""

from services.common.config import (
    DatabaseConfig,
    LLMConfig,
    ObservabilityConfig,
    ParserConfig,
    ResilienceConfig,
    ScoringConfig,
    Settings,
    get_settings,
)
from services.common.exceptions import (
    AnswerValidationError,
    CircuitOpenError,
    ConfigurationError,
    DiagnosticNotReadyError,
    DocumentTooLargeError,
    LLMUnavailableError,
    PersistenceError,
    PlatformError,
    RetryExhaustedError,
    ScoringError,
    UnsupportedDocumentError,
    ValidationError,
)
from services.common.health import HealthCheck, HealthStatus
from services.common.observability import (
    InMemoryMetrics,
    MetricsSink,
    NullMetrics,
    bind_correlation_id,
    configure_logging,
    get_correlation_id,
    get_metrics,
    set_metrics,
    timed,
    track,
)
from services.common.resilience import (
    AsyncCircuitBreaker,
    BoundedGate,
    CircuitState,
    retry_async,
    retry_call,
    with_timeout,
)

__all__ = [
    "DatabaseConfig",
    "LLMConfig",
    "ObservabilityConfig",
    "ParserConfig",
    "ResilienceConfig",
    "ScoringConfig",
    "Settings",
    "get_settings",
    "AnswerValidationError",
    "CircuitOpenError",
    "ConfigurationError",
    "DiagnosticNotReadyError",
    "DocumentTooLargeError",
    "LLMUnavailableError",
    "PersistenceError",
    "PlatformError",
    "RetryExhaustedError",
    "ScoringError",
    "UnsupportedDocumentError",
    "ValidationError",
    "HealthCheck",
    "HealthStatus",
    "InMemoryMetrics",
    "MetricsSink",
    "NullMetrics",
    "bind_correlation_id",
    "configure_logging",
    "get_correlation_id",
    "get_metrics",
    "set_metrics",
    "timed",
    "track",
    "AsyncCircuitBreaker",
    "BoundedGate",
    "CircuitState",
    "retry_async",
    "retry_call",
    "with_timeout",
]
