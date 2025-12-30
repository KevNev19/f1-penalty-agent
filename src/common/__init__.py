"""Common utilities and shared functionality.

This package contains helper functions and classes used across multiple
modules in the F1 Penalty Agent application.
"""

from .exception_handler import format_exception_json, handle_exception, log_exception
from .exceptions import (
    ConfigurationError,
    DataIngestionError,
    EmbeddingError,
    F1AgentError,
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
    QdrantConnectionError,
    QdrantQueryError,
    ValidationError,
    VectorStoreError,
)
from .utils import chunk_text, normalize_text, sanitize_text

__all__ = [
    # Utilities
    "normalize_text",
    "sanitize_text",
    "chunk_text",
    # Base exception
    "F1AgentError",
    # Exception categories
    "ConfigurationError",
    "VectorStoreError",
    "QdrantConnectionError",
    "QdrantQueryError",
    "EmbeddingError",
    "LLMError",
    "LLMConnectionError",
    "LLMRateLimitError",
    "DataIngestionError",
    "ValidationError",
    # Exception handlers
    "format_exception_json",
    "log_exception",
    "handle_exception",
]
