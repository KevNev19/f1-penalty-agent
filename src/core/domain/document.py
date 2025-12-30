"""Document and search result models for the RAG system."""

from dataclasses import dataclass
from typing import Any


@dataclass
class Document:
    """A document chunk with content and metadata.

    This represents a piece of text that can be indexed and searched
    in the vector store. Each document has content, associated metadata,
    and an optional unique identifier.

    Attributes:
        content: The text content of the document chunk.
        metadata: Key-value pairs of metadata (source, type, etc.).
        doc_id: Optional unique identifier for the document.
    """

    content: str
    metadata: dict[str, Any]
    doc_id: str | None = None


@dataclass
class SearchResult:
    """A search result with document and relevance score.

    Returned by vector store searches, combining the matched
    document with its relevance score.

    Attributes:
        document: The matched Document.
        score: Relevance score (0.0 to 1.0, higher is more relevant).
    """

    document: Document
    score: float
