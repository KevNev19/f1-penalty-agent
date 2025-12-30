"""Vector Store Port Interface."""

from abc import ABC, abstractmethod
from typing import Any

from ..domain import Document, SearchResult


class VectorStorePort(ABC):
    """Abstract interface for vector stores."""

    # Standard collection names
    REGULATIONS_COLLECTION = "regulations"
    STEWARDS_COLLECTION = "stewards_decisions"
    RACE_DATA_COLLECTION = "race_data"

    @abstractmethod
    def add_documents(self, documents: list[Document], collection_name: str) -> int:
        """Add documents to a collection."""
        ...

    @abstractmethod
    def search(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Search for relevant documents."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset/clear the vector store."""
        ...

    @abstractmethod
    def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """Get statistics for a collection."""
        ...
