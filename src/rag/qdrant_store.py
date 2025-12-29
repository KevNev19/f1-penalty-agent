"""Qdrant vector store for production deployment.

This module provides a Qdrant-based vector store that implements the same interface
as the previous Pinecone store for seamless switching between backends.
"""

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)

# Constants
EMBEDDING_BATCH_SIZE = 20
MAX_EMBEDDING_RETRIES = 3
EMBEDDING_DIMENSION = 768


@dataclass
class Document:
    """A document chunk with content and metadata."""

    content: str
    metadata: dict[str, Any]
    doc_id: str | None = None


@dataclass
class SearchResult:
    """A search result with document and relevance score."""

    document: Document
    score: float


class GeminiEmbeddingFunction:
    """Custom embedding function using Google Gemini API.

    Shared embedding function for consistent embeddings across the application.
    """

    def __init__(self, api_key: str, model_name: str = "models/text-embedding-004"):
        self.api_key = api_key
        self.model_name = model_name

    def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a single query text."""
        embeddings = self._embed_texts([text], task_type="RETRIEVAL_QUERY")
        return embeddings[0] if embeddings else [0.0] * EMBEDDING_DIMENSION

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple documents."""
        return self._embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")

    def _embed_texts(self, texts: list[str], task_type: str) -> list[list[float]]:
        """Generate embeddings using Google Gemini REST API."""
        import requests

        api_url = f"https://generativelanguage.googleapis.com/v1beta/{self.model_name}:batchEmbedContents?key={self.api_key}"
        embeddings = []

        for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch_texts = texts[i : i + EMBEDDING_BATCH_SIZE]

            requests_payload = []
            for text in batch_texts:
                requests_payload.append(
                    {
                        "model": self.model_name,
                        "content": {"parts": [{"text": text}]},
                        "taskType": task_type,
                        "title": "Document" if task_type == "RETRIEVAL_DOCUMENT" else None,
                    }
                )

            payload = {"requests": requests_payload}

            for attempt in range(MAX_EMBEDDING_RETRIES):
                try:
                    response = requests.post(api_url, json=payload, timeout=30)

                    if response.status_code == 200:
                        data = response.json()
                        if "embeddings" in data:
                            for emb in data["embeddings"]:
                                embeddings.append(emb.get("values", [0.0] * EMBEDDING_DIMENSION))
                        else:
                            embeddings.extend([[0.0] * EMBEDDING_DIMENSION] * len(batch_texts))
                        break
                    elif response.status_code == 429:
                        wait_time = 2**attempt
                        logger.warning("Rate limit hit, retrying in %ds...", wait_time)
                        time.sleep(wait_time)
                    else:
                        if attempt == MAX_EMBEDDING_RETRIES - 1:
                            embeddings.extend([[0.0] * EMBEDDING_DIMENSION] * len(batch_texts))
                        time.sleep(1)
                except Exception as e:
                    logger.warning(f"Embedding request failed: {e}")
                    if attempt == MAX_EMBEDDING_RETRIES - 1:
                        embeddings.extend([[0.0] * EMBEDDING_DIMENSION] * len(batch_texts))
                    time.sleep(1)

        return embeddings


class QdrantVectorStore:
    """Qdrant-based vector store for F1 documents.

    Uses collections to separate different document types (regulations, stewards, race_data).
    Uses Gemini API for embeddings to maintain consistency.
    """

    # Collection names for different document types
    REGULATIONS_NAMESPACE = "regulations"
    STEWARDS_NAMESPACE = "stewards_decisions"
    RACE_DATA_NAMESPACE = "race_data"

    # Aliases for backward compatibility
    REGULATIONS_COLLECTION = REGULATIONS_NAMESPACE
    STEWARDS_COLLECTION = STEWARDS_NAMESPACE
    RACE_DATA_COLLECTION = RACE_DATA_NAMESPACE

    # Embedding dimension for Gemini text-embedding-004
    EMBEDDING_DIMENSION = 768

    def __init__(
        self,
        url: str,
        api_key: str,
        embedding_api_key: str,
    ) -> None:
        """Initialize the Qdrant vector store.

        Args:
            url: Qdrant Cloud cluster URL.
            api_key: Qdrant API key.
            embedding_api_key: Google API key for embeddings.
        """
        self.url = url
        self.api_key = api_key
        self._client = None
        self._embedding_fn = GeminiEmbeddingFunction(embedding_api_key)

    def _get_client(self) -> "QdrantClient":
        """Get or create Qdrant client connection."""
        if self._client is None:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(
                url=self.url,
                api_key=self.api_key,
            )
            logger.info("Connected to Qdrant at: %s", self.url)

            # Ensure collections exist
            self._ensure_collections()

        return self._client

    def _ensure_collections(self) -> None:
        """Ensure all required collections exist."""
        from qdrant_client.models import Distance, VectorParams

        for collection_name in [
            self.REGULATIONS_NAMESPACE,
            self.STEWARDS_NAMESPACE,
            self.RACE_DATA_NAMESPACE,
        ]:
            try:
                collections = self._client.get_collections().collections
                exists = any(c.name == collection_name for c in collections)

                if not exists:
                    self._client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=self.EMBEDDING_DIMENSION,
                            distance=Distance.COSINE,
                        ),
                    )
                    logger.debug("Created collection: %s", collection_name)
            except Exception as e:
                logger.warning(f"Could not ensure collection {collection_name}: {e}")

    def reset(self) -> None:
        """Reset the vector store by deleting all collections and recreating them."""
        client = self._get_client()

        for collection_name in [
            self.REGULATIONS_NAMESPACE,
            self.STEWARDS_NAMESPACE,
            self.RACE_DATA_NAMESPACE,
        ]:
            try:
                client.delete_collection(collection_name=collection_name)
                logger.debug("Deleted collection: %s", collection_name)
            except Exception as e:
                logger.debug(f"Collection {collection_name} deletion skipped: {e}")

        # Recreate collections
        self._ensure_collections()
        logger.info("Qdrant vector store reset complete")

    def add_documents(
        self,
        documents: list[Document],
        collection_name: str = REGULATIONS_NAMESPACE,
    ) -> int:
        """Add documents to the vector store.

        Args:
            documents: List of documents to add.
            collection_name: Collection to add to.

        Returns:
            Number of documents added.
        """
        if not documents:
            return 0

        from qdrant_client.models import PointStruct

        client = self._get_client()

        # Generate embeddings
        contents = [doc.content for doc in documents]
        logger.debug("Generating embeddings for %d documents...", len(documents))
        embeddings = self._embedding_fn.embed_documents(contents)

        # Prepare points for upsert
        points = []
        for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
            # Generate a unique integer ID from doc_id or index
            if doc.doc_id:
                # Use hash of doc_id for consistent integer ID
                point_id = abs(hash(doc.doc_id)) % (10**18)
            else:
                point_id = abs(hash(f"{collection_name}_{i}_{time.time()}")) % (10**18)

            # Store content in payload along with metadata
            payload = {
                "content": doc.content,
                "doc_id": doc.doc_id,
                **doc.metadata,
            }

            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
            )

        # Upsert in batches
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            client.upsert(
                collection_name=collection_name,
                points=batch,
            )

        logger.info("Added %d documents to %s", len(documents), collection_name)
        return len(documents)

    def search(
        self,
        query: str,
        collection_name: str = REGULATIONS_NAMESPACE,
        top_k: int = 5,
        filter_metadata: dict | None = None,
    ) -> list[SearchResult]:
        """Search for relevant documents.

        Args:
            query: Search query.
            collection_name: Collection to search in.
            top_k: Number of results to return.
            filter_metadata: Optional metadata filter.

        Returns:
            List of SearchResult objects.
        """
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        client = self._get_client()

        # Generate query embedding
        query_embedding = self._embedding_fn.embed_query(query)

        # Build filter if provided
        qdrant_filter = None
        if filter_metadata:
            conditions = []
            for key, value in filter_metadata.items():
                if isinstance(value, dict) and "$eq" in value:
                    conditions.append(FieldCondition(key=key, match=MatchValue(value=value["$eq"])))
            if conditions:
                qdrant_filter = Filter(must=conditions)

        # Search using query_points (qdrant-client 1.16+ API)
        results = client.query_points(
            collection_name=collection_name,
            query=query_embedding,
            limit=top_k * 2,  # Get extra for filtering
            query_filter=qdrant_filter,
            with_payload=True,
        )

        search_results = []
        seen_content = set()

        # query_points returns QueryResponse with .points attribute
        points = results.points if hasattr(results, "points") else results

        for hit in points:
            score = hit.score

            # Skip low-score results
            if score < 0.5:
                continue

            payload = dict(hit.payload) if hit.payload else {}
            content = payload.pop("content", "")
            doc_id = payload.pop("doc_id", None)

            # Deduplication
            content_hash = hash(content[:500])
            if content_hash in seen_content:
                continue
            seen_content.add(content_hash)

            search_results.append(
                SearchResult(
                    document=Document(
                        content=content,
                        metadata=payload,
                        doc_id=doc_id,
                    ),
                    score=score,
                )
            )

            if len(search_results) >= top_k:
                break

        return search_results

    def search_all_namespaces(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Search across all collections and merge results.

        Args:
            query: Search query.
            top_k: Number of results to return per collection.

        Returns:
            Combined and sorted list of SearchResult objects.
        """
        all_results = []

        for collection_name in [
            self.REGULATIONS_NAMESPACE,
            self.STEWARDS_NAMESPACE,
            self.RACE_DATA_NAMESPACE,
        ]:
            try:
                results = self.search(query, collection_name, top_k)
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"Search failed for collection {collection_name}: {e}")

        # Sort by score and return top results
        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:top_k]

    def get_collection_stats(self, collection_name: str) -> dict:
        """Get statistics for a collection.

        Args:
            collection_name: Name of the collection.

        Returns:
            Dict with collection statistics.
        """
        try:
            client = self._get_client()
            info = client.get_collection(collection_name=collection_name)
            return {
                "name": collection_name,
                "count": info.points_count,
            }
        except Exception as e:
            logger.warning(f"Failed to get stats for collection {collection_name}: {e}")
            return {"name": collection_name, "count": 0, "error": str(e)}

    def clear_collection(self, collection_name: str) -> None:
        """Clear all documents from a collection.

        Args:
            collection_name: Name of the collection to clear.
        """
        from qdrant_client.models import Distance, VectorParams

        try:
            client = self._get_client()
            # Delete and recreate the collection
            client.delete_collection(collection_name=collection_name)
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.EMBEDDING_DIMENSION,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Cleared collection: %s", collection_name)
        except Exception as e:
            logger.warning(f"Failed to clear collection {collection_name}: {e}")
