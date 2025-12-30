"""Vector store exceptions for F1 Penalty Agent."""

from .base import F1AgentError


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
