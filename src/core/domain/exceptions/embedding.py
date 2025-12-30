"""Embedding exceptions for F1 Penalty Agent."""

from .base import F1AgentError


class EmbeddingError(F1AgentError):
    """Failed to generate embeddings."""

    error_code = "F1_EMB_001"


class EmbeddingAPIError(EmbeddingError):
    """Embedding API returned an error."""

    error_code = "F1_EMB_002"


class EmbeddingRateLimitError(EmbeddingError):
    """Embedding API rate limit exceeded."""

    error_code = "F1_EMB_003"
