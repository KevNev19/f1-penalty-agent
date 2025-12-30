"""Custom exception hierarchy for F1 Penalty Agent.

This module provides structured exceptions with automatic context capture,
similar to Java's exception handling patterns. Each exception includes:
- Error codes for quick identification
- Automatic capture of class, method, file, and line number
- Cause chaining for underlying exceptions
- JSON serialization for structured logging
"""

import inspect
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class ExceptionContext:
    """Captures location and context where exception occurred."""

    class_name: str
    method_name: str
    file_name: str
    line_number: int
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for JSON serialization."""
        return {
            "class": self.class_name,
            "method": self.method_name,
            "file": self.file_name,
            "line": self.line_number,
            "timestamp": self.timestamp,
        }


class F1AgentError(Exception):
    """Base exception for all F1 Agent errors.

    All custom exceptions should inherit from this class to ensure
    consistent error handling and JSON output format.

    Example:
        try:
            connect_to_qdrant()
        except SomeError as e:
            raise QdrantConnectionError(
                "Failed to connect to Qdrant",
                cause=e,
                context={"url": qdrant_url}
            )
    """

    error_code: str = "F1_ERR_001"

    def __init__(
        self,
        message: str,
        *,
        cause: Exception | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the exception with message and optional context.

        Args:
            message: Human-readable error message.
            cause: The underlying exception that caused this error.
            context: Additional context as key-value pairs for debugging.
        """
        super().__init__(message)
        self.message = message
        self.cause = cause
        self.extra_context = context or {}
        self.location = self._capture_location()
        self.stack_trace = traceback.format_exc() if cause else None

    def _capture_location(self) -> ExceptionContext:
        """Automatically capture class/method/file/line from call stack."""
        # Walk up the stack to find the actual caller
        frame = inspect.currentframe()
        # Skip: _capture_location -> __init__ -> raise site
        for _ in range(3):
            if frame and frame.f_back:
                frame = frame.f_back

        if frame:
            class_instance = frame.f_locals.get("self", None)
            return ExceptionContext(
                class_name=type(class_instance).__name__ if class_instance else "<module>",
                method_name=frame.f_code.co_name,
                file_name=frame.f_code.co_filename.split("\\")[-1].split("/")[-1],
                line_number=frame.f_lineno,
            )
        return ExceptionContext("<unknown>", "<unknown>", "<unknown>", 0)

    def to_dict(self, include_trace: bool = False) -> dict[str, Any]:
        """Convert exception to structured dictionary for JSON output.

        Args:
            include_trace: If True, include full stack trace (debug mode).

        Returns:
            Dictionary with error details, location, and optional trace.
        """
        result: dict[str, Any] = {
            "error": {
                "type": type(self).__name__,
                "code": self.error_code,
                "message": self.message,
            },
            "location": self.location.to_dict(),
        }

        if self.extra_context:
            result["context"] = self.extra_context

        if include_trace and self.stack_trace:
            result["stack_trace"] = [line for line in self.stack_trace.split("\n") if line.strip()]

        if self.cause:
            result["cause"] = {
                "type": type(self.cause).__name__,
                "message": str(self.cause),
            }

        return result


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigurationError(F1AgentError):
    """Configuration or environment variable errors.

    Raised when required configuration is missing or invalid.
    """

    error_code = "F1_CFG_001"


class MissingAPIKeyError(ConfigurationError):
    """Required API key is not configured."""

    error_code = "F1_CFG_002"


class InvalidConfigurationError(ConfigurationError):
    """Configuration value is invalid."""

    error_code = "F1_CFG_003"


# =============================================================================
# Vector Store Errors
# =============================================================================


class VectorStoreError(F1AgentError):
    """Base error for vector store operations."""

    error_code = "F1_VEC_001"


class QdrantConnectionError(VectorStoreError):
    """Failed to connect to Qdrant.

    Common causes:
    - Invalid URL or API key
    - Network connectivity issues
    - Qdrant service is down
    """

    error_code = "F1_VEC_002"


class QdrantQueryError(VectorStoreError):
    """Failed to query Qdrant.

    Common causes:
    - Collection does not exist
    - Invalid query parameters
    - Embedding dimension mismatch
    """

    error_code = "F1_VEC_003"


class CollectionNotFoundError(VectorStoreError):
    """Requested collection does not exist."""

    error_code = "F1_VEC_004"


# =============================================================================
# Embedding Errors
# =============================================================================


class EmbeddingError(F1AgentError):
    """Failed to generate embeddings."""

    error_code = "F1_EMB_001"


class EmbeddingAPIError(EmbeddingError):
    """Embedding API returned an error."""

    error_code = "F1_EMB_002"


class EmbeddingRateLimitError(EmbeddingError):
    """Embedding API rate limit exceeded."""

    error_code = "F1_EMB_003"


# =============================================================================
# LLM Errors
# =============================================================================


class LLMError(F1AgentError):
    """Base error for LLM operations."""

    error_code = "F1_LLM_001"


class LLMConnectionError(LLMError):
    """Failed to connect to LLM provider.

    Common causes:
    - Invalid API key
    - Network issues
    - Service unavailable
    """

    error_code = "F1_LLM_002"


class LLMRateLimitError(LLMError):
    """Rate limit exceeded on LLM provider.

    The free tier has limited requests per minute.
    Wait a moment and try again.
    """

    error_code = "F1_LLM_003"


class LLMGenerationError(LLMError):
    """Failed to generate LLM response.

    Common causes:
    - Content filtered by safety settings
    - Token limit exceeded
    - Invalid prompt format
    """

    error_code = "F1_LLM_004"


# =============================================================================
# Data Ingestion Errors
# =============================================================================


class DataIngestionError(F1AgentError):
    """Error during data scraping/loading."""

    error_code = "F1_DAT_001"


class ScrapingError(DataIngestionError):
    """Failed to scrape data from source."""

    error_code = "F1_DAT_002"


class PDFExtractionError(DataIngestionError):
    """Failed to extract text from PDF."""

    error_code = "F1_DAT_003"


class DataValidationError(DataIngestionError):
    """Ingested data failed validation."""

    error_code = "F1_DAT_004"


# =============================================================================
# Validation Errors
# =============================================================================


class ValidationError(F1AgentError):
    """Input validation failed."""

    error_code = "F1_VAL_001"


class EmptyQueryError(ValidationError):
    """Query cannot be empty or whitespace only."""

    error_code = "F1_VAL_002"


class QueryTooLongError(ValidationError):
    """Query exceeds maximum allowed length."""

    error_code = "F1_VAL_003"


# =============================================================================
# Retrieval Errors
# =============================================================================


class RetrievalError(F1AgentError):
    """Error during document retrieval."""

    error_code = "F1_RET_001"


class NoResultsError(RetrievalError):
    """No relevant documents found for query."""

    error_code = "F1_RET_002"
