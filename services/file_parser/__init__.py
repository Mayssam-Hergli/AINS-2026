"""File Parser Service.

Public surface for ingesting sustainability / compliance documents and turning them
into typed, embedded signals that MS1 consumes as ground-truth evidence.
"""

from services.file_parser.core import (
    CachingEmbedder,
    Embedder,
    FileParserService,
    HashingEmbedder,
    ParseRequest,
    SignalRepository,
)
from services.file_parser.extractors import (
    DocxExtractor,
    ExtractorRegistry,
    PDFExtractor,
    RawExtraction,
    TabularExtractor,
    UnsupportedDocumentError,
)
from services.file_parser.normalizer import (
    EMBEDDING_DIM,
    ExtractedSignal,
    NormalizedDocument,
    Normalizer,
    SignalDomain,
    SignalType,
)

__all__ = [
    "CachingEmbedder",
    "Embedder",
    "FileParserService",
    "HashingEmbedder",
    "ParseRequest",
    "SignalRepository",
    "DocxExtractor",
    "ExtractorRegistry",
    "PDFExtractor",
    "RawExtraction",
    "TabularExtractor",
    "UnsupportedDocumentError",
    "EMBEDDING_DIM",
    "ExtractedSignal",
    "NormalizedDocument",
    "Normalizer",
    "SignalDomain",
    "SignalType",
]
