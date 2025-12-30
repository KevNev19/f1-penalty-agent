"""Custom exception hierarchy for F1 Penalty Agent.

This package provides structured exceptions with automatic context capture,
similar to Java's exception handling patterns. Each exception includes:
- Error codes for quick identification
- Automatic capture of class, method, file, and line number
- Cause chaining for underlying exceptions
- JSON serialization for structured logging

All exceptions are re-exported here for backward compatibility.
Import from this package directly:

    from src.core.domain.exceptions import F1AgentError, QdrantConnectionError
"""

# Base classes
from .base import ExceptionContext, F1AgentError

# Configuration exceptions
from .configuration import (
    ConfigurationError,
    InvalidConfigurationError,
    MissingAPIKeyError,
)

# Data ingestion exceptions
from .data_ingestion import (
    DataIngestionError,
    DataValidationError,
    PDFExtractionError,
    ScrapingError,
)

# Embedding exceptions
from .embedding import (
    EmbeddingAPIError,
    EmbeddingError,
    EmbeddingRateLimitError,
)

# LLM exceptions
from .llm import (
    LLMConnectionError,
    LLMError,
    LLMGenerationError,
    LLMRateLimitError,
)

# Retrieval exceptions
from .retrieval import (
    NoResultsError,
    RetrievalError,
)

# Validation exceptions
from .validation import (
    EmptyQueryError,
    QueryTooLongError,
    ValidationError,
)

# Vector store exceptions
from .vector_store import (
    CollectionNotFoundError,
    QdrantConnectionError,
    QdrantQueryError,
    VectorStoreError,
)

__all__ = [
    # Base
    "ExceptionContext",
    "F1AgentError",
    # Configuration
    "ConfigurationError",
    "MissingAPIKeyError",
    "InvalidConfigurationError",
    # Vector Store
    "VectorStoreError",
    "QdrantConnectionError",
    "QdrantQueryError",
    "CollectionNotFoundError",
    # Embedding
    "EmbeddingError",
    "EmbeddingAPIError",
    "EmbeddingRateLimitError",
    # LLM
    "LLMError",
    "LLMConnectionError",
    "LLMRateLimitError",
    "LLMGenerationError",
    # Data Ingestion
    "DataIngestionError",
    "ScrapingError",
    "PDFExtractionError",
    "DataValidationError",
    # Validation
    "ValidationError",
    "EmptyQueryError",
    "QueryTooLongError",
    # Retrieval
    "RetrievalError",
    "NoResultsError",
]
