"""File Parser Service — pipeline orchestration.

Ties the extractors, the normalizer, an embedding provider, and the pgvector
persistence layer into a single async entry point:

    extract → normalize → embed → persist

The output (a :class:`~services.file_parser.normalizer.NormalizedDocument` whose
signals carry embeddings) is the evidence base that MS1 reads. Signals are written
to the shared PostgreSQL + pgvector ``document_signals`` table, keyed by project.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import struct
import uuid
from collections import OrderedDict
from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable

from services.common.config import Settings, get_settings
from services.common.exceptions import (
    DocumentTooLargeError,
    PersistenceError,
    UnsupportedDocumentError,
)
from services.common.observability import (
    MetricsSink,
    bind_correlation_id,
    get_metrics,
    track,
)
from services.common.resilience import BoundedGate, retry_call
from services.file_parser.extractors import ExtractorRegistry, RawExtraction
from services.file_parser.extractors import (
    UnsupportedDocumentError as _ExtractorUnsupportedError,
)
from services.file_parser.normalizer import (
    EMBEDDING_DIM,
    ExtractedSignal,
    NormalizedDocument,
    Normalizer,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class Embedder(Protocol):
    """Pluggable embedding provider so the pipeline isn't tied to one vendor."""

    dimension: int

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding vector per input text, order-preserving."""
        ...


class HashingEmbedder:
    """Deterministic, dependency-free embedder.

    A real deployment injects a transformer/API-backed embedder; this default keeps
    the pipeline fully functional offline and in tests by hashing token n-grams into
    a fixed-width vector. Values are L2-normalised so cosine distance is meaningful.
    """

    def __init__(self, dimension: int = EMBEDDING_DIM) -> None:
        self.dimension = dimension

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = text.lower().split()
        for token in tokens:
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            bucket = struct.unpack("<Q", digest)[0] % self.dimension
            sign = 1.0 if bucket % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = sum(component * component for component in vector) ** 0.5
        if norm == 0.0:
            return vector
        return [component / norm for component in vector]


class CachingEmbedder:
    """Wraps any :class:`Embedder` with a bounded LRU cache keyed on text.

    Sustainability/compliance corpora are highly repetitive (boilerplate clauses,
    repeated table headers, the same disclosure across documents), so caching avoids
    recomputing — or re-billing, for an API-backed embedder — identical fragments.
    """

    def __init__(self, inner: "Embedder", *, max_size: int = 4096) -> None:
        self._inner = inner
        self.dimension = inner.dimension
        self._max_size = max(max_size, 0)
        self._cache: "OrderedDict[str, list[float]]" = OrderedDict()

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        missing = [t for t in texts if t not in self._cache]
        if missing:
            # De-duplicate misses before delegating so we never embed the same text twice.
            unique_missing = list(dict.fromkeys(missing))
            vectors = await self._inner.embed(unique_missing)
            for text, vector in zip(unique_missing, vectors):
                self._store(text, vector)
        results: list[list[float]] = []
        for text in texts:
            vector = self._cache[text]
            self._cache.move_to_end(text)
            results.append(vector)
        return results

    def _store(self, text: str, vector: list[float]) -> None:
        if self._max_size == 0:
            self._cache[text] = vector
            return
        self._cache[text] = vector
        self._cache.move_to_end(text)
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)


def to_vector_literal(embedding: Sequence[float]) -> str:
    """Format an embedding as a pgvector text literal: ``[0.1,0.2,...]``."""
    return "[" + ",".join(f"{value:.6f}" for value in embedding) + "]"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

_SCHEMA_DDL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS document_signals (
    id              TEXT PRIMARY KEY,
    tenant_id       UUID,
    project_id      UUID NOT NULL,
    document_id     TEXT NOT NULL,
    source_document TEXT NOT NULL,
    domain          TEXT NOT NULL,
    signal_type     TEXT NOT NULL,
    label           TEXT NOT NULL,
    raw_text        TEXT NOT NULL,
    value           DOUBLE PRECISION,
    unit            TEXT,
    confidence      DOUBLE PRECISION NOT NULL,
    source_locator  TEXT NOT NULL DEFAULT '',
    keywords        TEXT[] NOT NULL DEFAULT '{{}}',
    embedding       VECTOR({dim}),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS document_signals_project_idx
    ON document_signals (project_id);
CREATE INDEX IF NOT EXISTS document_signals_tenant_idx
    ON document_signals (tenant_id, project_id);
CREATE INDEX IF NOT EXISTS document_signals_domain_idx
    ON document_signals (project_id, domain);
"""


class SignalRepository:
    """Persists extracted signals to the pgvector ``document_signals`` table.

    Accepts any object exposing asyncpg's pool interface (``acquire`` /
    ``executemany``) so it can be unit-tested with a fake pool.
    """

    def __init__(self, pool, *, metrics: MetricsSink | None = None) -> None:
        self._pool = pool
        self._metrics = metrics or get_metrics()

    async def ensure_schema(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(_SCHEMA_DDL.format(dim=EMBEDDING_DIM))

    async def upsert_signals(
        self,
        *,
        project_id: uuid.UUID,
        document_id: str,
        signals: Sequence[ExtractedSignal],
        tenant_id: uuid.UUID | None = None,
    ) -> int:
        if not signals:
            return 0

        records = [
            (
                signal.id,
                tenant_id,
                project_id,
                document_id,
                signal.source_document,
                signal.domain.value,
                signal.signal_type.value,
                signal.label,
                signal.raw_text,
                signal.value,
                signal.unit,
                signal.confidence,
                signal.source_locator,
                list(signal.keywords),
                to_vector_literal(signal.embedding) if signal.embedding else None,
            )
            for signal in signals
        ]

        query = """
            INSERT INTO document_signals (
                id, tenant_id, project_id, document_id, source_document, domain,
                signal_type, label, raw_text, value, unit, confidence, source_locator,
                keywords, embedding
            )
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15::vector)
            ON CONFLICT (id) DO UPDATE SET
                confidence = EXCLUDED.confidence,
                label = EXCLUDED.label,
                embedding = EXCLUDED.embedding,
                created_at = now();
        """

        async def _write() -> None:
            async with self._pool.acquire() as conn:
                await conn.executemany(query, records)

        try:
            # Transient DB errors (connection resets, deadlocks) are retried; a
            # persistent failure surfaces as a typed PersistenceError.
            await retry_call(_write, attempts=3, base_delay=0.2)
        except Exception as exc:  # noqa: BLE001 - normalise to a domain error
            self._metrics.increment("parser.persist.errors")
            raise PersistenceError("failed to persist document signals") from exc

        self._metrics.increment("parser.signals.persisted", float(len(records)))
        return len(records)


@dataclass(slots=True)
class ParseRequest:
    """Inputs for a single parse operation."""

    project_id: uuid.UUID
    filename: str
    data: bytes
    content_type: str | None = None
    document_id: str | None = None
    tenant_id: uuid.UUID | None = None


class FileParserService:
    """Async orchestrator for the extract → normalize → embed → persist pipeline.

    Enterprise behaviour layered in: per-document input validation (size + type),
    content-hash idempotency, a cached embedder, bounded batch concurrency, and
    correlation-scoped structured logging/metrics.
    """

    def __init__(
        self,
        *,
        registry: ExtractorRegistry | None = None,
        normalizer: Normalizer | None = None,
        embedder: Embedder | None = None,
        repository: SignalRepository | None = None,
        settings: Settings | None = None,
        metrics: MetricsSink | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._registry = registry or ExtractorRegistry()
        self._normalizer = normalizer or Normalizer()
        base_embedder = embedder or HashingEmbedder()
        self._embedder: Embedder = CachingEmbedder(
            base_embedder, max_size=self._settings.parser.embedding_cache_size
        )
        self._repository = repository
        self._metrics = metrics or get_metrics()
        self._gate = BoundedGate(self._settings.parser.max_concurrency)

    def _validate(self, request: ParseRequest) -> None:
        limit = self._settings.parser.max_file_bytes
        if len(request.data) > limit:
            raise DocumentTooLargeError(
                f"{request.filename!r} is {len(request.data)} bytes; limit is {limit}"
            )
        allowed = self._settings.parser.allowed_content_types
        if request.content_type and allowed and request.content_type not in allowed:
            raise UnsupportedDocumentError(
                f"content type {request.content_type!r} is not allowed"
            )

    async def parse(self, request: ParseRequest, *, persist: bool = True) -> NormalizedDocument:
        """Run the full pipeline for one document and return its normalized form."""
        self._validate(request)
        # Default the document id to a content hash so re-parsing identical bytes is
        # idempotent: the same fragments yield the same signal ids on upsert.
        document_id = request.document_id or hashlib.sha256(request.data).hexdigest()[:32]

        with bind_correlation_id() as cid, track("parser.parse"):
            try:
                extractor = self._registry.resolve(
                    filename=request.filename, content_type=request.content_type
                )
            except _ExtractorUnsupportedError as exc:
                raise UnsupportedDocumentError(str(exc)) from exc

            logger.info(
                "Parsing %s (%s) with %s [cid=%s]",
                request.filename, document_id, type(extractor).__name__, cid,
            )

            extraction: RawExtraction = await extractor.extract(
                document_id=document_id,
                filename=request.filename,
                content_type=request.content_type or "",
                data=request.data,
            )

            document = self._normalizer.normalize(extraction)
            document = await self._attach_embeddings(document)
            self._metrics.increment("parser.signals.extracted", float(len(document.signals)))

            if persist:
                if self._repository is None:
                    raise RuntimeError("persist=True requires a SignalRepository")
                written = await self._repository.upsert_signals(
                    project_id=request.project_id,
                    document_id=document.document_id,
                    signals=document.signals,
                    tenant_id=request.tenant_id,
                )
                logger.info("Persisted %d signals for project %s", written, request.project_id)

            self._metrics.increment("parser.documents.parsed")
            return document

    async def parse_many(
        self, requests: Sequence[ParseRequest], *, persist: bool = True
    ) -> list[NormalizedDocument]:
        """Parse a batch of documents with bounded concurrency."""

        async def _guarded(req: ParseRequest) -> NormalizedDocument:
            async with self._gate:
                return await self.parse(req, persist=persist)

        return list(await asyncio.gather(*(_guarded(req) for req in requests)))

    async def _attach_embeddings(self, document: NormalizedDocument) -> NormalizedDocument:
        if not document.signals:
            return document
        texts = [signal.raw_text for signal in document.signals]
        vectors = await self._embedder.embed(texts)
        embedded = [
            signal.model_copy(update={"embedding": tuple(vector)})
            for signal, vector in zip(document.signals, vectors)
        ]
        return document.model_copy(update={"signals": embedded})
