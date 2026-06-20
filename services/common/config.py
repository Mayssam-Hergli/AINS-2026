"""Centralised, environment-driven configuration.

All tunables live here behind a single immutable :class:`Settings` tree, loaded once
from the environment (prefix ``APP_``) and cached. This keeps deployment knobs out of
the code, makes behaviour reproducible per environment, and gives every service one
place to read limits, timeouts, and feature flags from.

Implemented on plain ``pydantic.BaseModel`` + an explicit env loader so the platform
pulls in no extra runtime dependency beyond pydantic.
"""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel, Field

from services.common.exceptions import ConfigurationError

_DEFAULT_CONTENT_TYPES = (
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)


def _str(key: str, default: str) -> str:
    value = os.environ.get(key)
    return value if value not in (None, "") else default


def _int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{key} must be an integer, got {raw!r}") from exc


def _float(key: str, default: float) -> float:
    raw = os.environ.get(key)
    if raw in (None, ""):
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{key} must be a number, got {raw!r}") from exc


def _bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key)
    if raw in (None, ""):
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class DatabaseConfig(BaseModel):
    dsn: str | None = None
    min_pool_size: int = 2
    max_pool_size: int = 10
    command_timeout: float = 30.0


class ParserConfig(BaseModel):
    max_file_bytes: int = 25 * 1024 * 1024  # 25 MiB
    max_concurrency: int = 8
    allowed_content_types: tuple[str, ...] = _DEFAULT_CONTENT_TYPES
    embedding_cache_size: int = 4096


class LLMConfig(BaseModel):
    enabled: bool = True
    model: str = "claude-opus-4-8"
    max_tokens: int = 2048
    timeout_seconds: float = 45.0
    max_retries: int = 2


class ResilienceConfig(BaseModel):
    circuit_failure_threshold: int = 5
    circuit_reset_seconds: float = 30.0
    retry_base_delay: float = 0.2
    retry_max_delay: float = 5.0


class ObservabilityConfig(BaseModel):
    log_level: str = "INFO"
    log_json: bool = True
    metrics_enabled: bool = True


class ScoringConfig(BaseModel):
    """Tunables for the MS2 Scoring Agent."""

    # Score-band cut points on a 0-100 scale.
    band_at_risk_max: float = 40.0
    band_developing_max: float = 60.0
    band_established_max: float = 80.0
    # How hard an overclaim (perceived > evidenced) drags a pillar score down.
    overclaim_penalty: float = 0.4
    # Relative weights of the four ESG/compliance pillars in the composite score.
    pillar_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "environmental": 0.25,
            "social": 0.20,
            "governance": 0.25,
            "compliance": 0.30,
        }
    )


class Settings(BaseModel):
    """Root configuration tree."""

    model_config = {"frozen": True}

    environment: str = "development"
    service_name: str = "assessment-platform"
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    parser: ParserConfig = Field(default_factory=ParserConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    resilience: ResilienceConfig = Field(default_factory=ResilienceConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)

    @classmethod
    def from_env(cls, prefix: str = "APP_") -> "Settings":
        p = prefix
        return cls(
            environment=_str(f"{p}ENVIRONMENT", "development"),
            service_name=_str(f"{p}SERVICE_NAME", "assessment-platform"),
            database=DatabaseConfig(
                dsn=os.environ.get(f"{p}DATABASE_DSN") or None,
                min_pool_size=_int(f"{p}DATABASE_MIN_POOL", 2),
                max_pool_size=_int(f"{p}DATABASE_MAX_POOL", 10),
                command_timeout=_float(f"{p}DATABASE_COMMAND_TIMEOUT", 30.0),
            ),
            parser=ParserConfig(
                max_file_bytes=_int(f"{p}PARSER_MAX_FILE_BYTES", 25 * 1024 * 1024),
                max_concurrency=_int(f"{p}PARSER_MAX_CONCURRENCY", 8),
                embedding_cache_size=_int(f"{p}PARSER_EMBEDDING_CACHE_SIZE", 4096),
            ),
            llm=LLMConfig(
                enabled=_bool(f"{p}LLM_ENABLED", True),
                model=_str(f"{p}LLM_MODEL", "claude-opus-4-8"),
                max_tokens=_int(f"{p}LLM_MAX_TOKENS", 2048),
                timeout_seconds=_float(f"{p}LLM_TIMEOUT_SECONDS", 45.0),
                max_retries=_int(f"{p}LLM_MAX_RETRIES", 2),
            ),
            resilience=ResilienceConfig(
                circuit_failure_threshold=_int(f"{p}CIRCUIT_FAILURE_THRESHOLD", 5),
                circuit_reset_seconds=_float(f"{p}CIRCUIT_RESET_SECONDS", 30.0),
                retry_base_delay=_float(f"{p}RETRY_BASE_DELAY", 0.2),
                retry_max_delay=_float(f"{p}RETRY_MAX_DELAY", 5.0),
            ),
            observability=ObservabilityConfig(
                log_level=_str(f"{p}LOG_LEVEL", "INFO"),
                log_json=_bool(f"{p}LOG_JSON", True),
                metrics_enabled=_bool(f"{p}METRICS_ENABLED", True),
            ),
            scoring=ScoringConfig(
                overclaim_penalty=_float(f"{p}SCORING_OVERCLAIM_PENALTY", 0.4),
            ),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings, loaded once from the environment."""
    return Settings.from_env()
