"""Qdrant vector store for production deployment.

This module provides a Qdrant-based vector store that implements the same interface
as the previous Pinecone store for seamless switching between backends.
"""

import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from qdrant_client import QdrantClient

from ....core.domain import Document, SearchResult
from ....core.domain.exceptions import (
    QdrantConnectionError,
)
from ....core.domain.utils import normalize_text
from ....core.ports.embedding_port import EmbeddingPort
from ....core.ports.vector_store_port import VectorStorePort

logger = logging.getLogger(__name__)

# Constants
EMBEDDING_BATCH_SIZE = 20
MAX_EMBEDDING_RETRIES = 3
EMBEDDING_DIMENSION = 3072  # gemini-embedding-001 default dimension


class GeminiEmbeddingFunction(EmbeddingPort):
    """Custom embedding function using Google Gemini API.

    Shared embedding function for consistent embeddings across the application.
    Uses the new google.genai SDK (GA May 2025).
    """

    def __init__(self, api_key: str, model_name: str = "gemini-embedding-001"):
        self.api_key = api_key
        self.model_name = model_name
        self._client = None

    def _get_client(self):
        """Get or create the genai client."""
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a single query text."""
        embeddings = self._embed_texts([text], task_type="RETRIEVAL_QUERY")
        return embeddings[0] if embeddings else [0.0] * EMBEDDING_DIMENSION

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple documents."""
        if not texts:
            return []

        # Batch processing
        all_embeddings = []
        for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
            batch = texts[i : i + EMBEDDING_BATCH_SIZE]
            try:
                embeddings = self._embed_texts(batch, "RETRIEVAL_DOCUMENT")
                all_embeddings.extend(embeddings)
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                logger.error(f"Error embedding batch {i}: {e}")
                # Add empty embeddings for failed batch to maintain index
                all_embeddings.extend([[] for _ in batch])

        return all_embeddings

    def _embed_texts(self, texts: list[str], task_type: str) -> list[list[float]]:
        """Generate embeddings using Google Gemini genai SDK."""
        client = self._get_client()

        for attempt in range(MAX_EMBEDDING_RETRIES):
            try:
                # Using the new google.genai SDK pattern
                result = client.models.embed_content(
                    model=self.model_name,
                    contents=texts,
                    config={"task_type": task_type},
                )
                # Return embeddings from result
                if result and hasattr(result, "embeddings"):
                    return [emb.values for emb in result.embeddings]
                return []
            except Exception as e:
                if attempt == MAX_EMBEDDING_RETRIES - 1:
                    logger.error(f"Failed to embed texts after retries: {e}")
                    raise
                time.sleep(2**attempt)
        return []


class QdrantAdapter(VectorStorePort):  # type: ignore[misc]
    """Qdrant-based vector store for F1 documents.

    Uses collections to separate different document types (regulations, stewards, race_data).
    Uses Gemini API for embeddings to maintain consistency.
    """

    # Collection names for different document types
    REGULATIONS_COLLECTION = "regulations"
    STEWARDS_COLLECTION = "stewards_decisions"
    RACE_DATA_COLLECTION = "race_data"

    # Embedding dimension for Gemini text-embedding-004
    EMBEDDING_DIMENSION = EMBEDDING_DIMENSION

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
        self._client: QdrantClient | None = None
        self._embedding_function = GeminiEmbeddingFunction(embedding_api_key)

    def _get_client(self) -> "QdrantClient":
        """Get or create Qdrant client connection."""
        if not self._client:
            try:
                from qdrant_client import QdrantClient

                self._client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                )
                logger.info("Connected to Qdrant at: %s", self.url)

                # Ensure collections exist
                self._ensure_collections()
            except Exception as e:
                raise QdrantConnectionError(
                    f"Failed to connect to Qdrant at {self.url}",
                    cause=e,
                    context={"url": self.url},
                ) from e

        return self._client

    def _ensure_collections(self) -> None:
        """Ensure all required collections exist."""
        try:
            client = self._get_client()
            collections = client.get_collections().collections
            existing = {c.name for c in collections}

            from qdrant_client.http import models

            for name in [
                self.REGULATIONS_COLLECTION,
                self.STEWARDS_COLLECTION,
                self.RACE_DATA_COLLECTION,
            ]:
                if name not in existing:
                    logger.info(f"Creating collection {name}")
                    client.create_collection(
                        collection_name=name,
                        vectors_config=models.VectorParams(
                            size=self.EMBEDDING_DIMENSION,
                            distance=models.Distance.COSINE,
                        ),
                    )

                # Ensure payload indexes exist for filtering
                # 'url' is used for existence checks
                client.create_payload_index(
                    collection_name=name,
                    field_name="url",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )
                # 'config_hash' is used for versioning
                client.create_payload_index(
                    collection_name=name,
                    field_name="config_hash",
                    field_schema=models.PayloadSchemaType.KEYWORD,
                )

        except Exception as e:
            logger.error(f"Failed to ensure collections: {e}")
            raise e

    def reset(self) -> None:
        """Reset the vector store by deleting all collections and recreating them."""
        client = self._get_client()

        for collection_name in [
            self.REGULATIONS_COLLECTION,
            self.STEWARDS_COLLECTION,
            self.RACE_DATA_COLLECTION,
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
        collection_name: str = REGULATIONS_COLLECTION,
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

        # Normalize content before storing to prevent BOM issues
        contents = [normalize_text(doc.content) for doc in documents]
        logger.debug("Generating embeddings for %d documents...", len(documents))
        embeddings = self._embedding_function.embed_documents(contents)

        # Prepare points for upsert
        points = []
        for i, (doc, embedding, clean_content) in enumerate(zip(documents, embeddings, contents)):
            # Generate a unique integer ID from doc_id or index
            if doc.doc_id:
                # Use hash of doc_id for consistent integer ID
                point_id = abs(hash(doc.doc_id)) % (10**18)
            else:
                point_id = abs(hash(f"{collection_name}_{i}_{time.time()}")) % (10**18)

            # Normalize metadata string values to prevent BOM issues
            clean_metadata = {}
            for key, value in doc.metadata.items():
                if isinstance(value, str):
                    clean_metadata[key] = normalize_text(value)
                else:
                    clean_metadata[key] = value

            # Store normalized content in payload along with metadata
            payload = {
                "content": clean_content,
                "doc_id": doc.doc_id,
                **clean_metadata,
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
        collection_name: str = REGULATIONS_COLLECTION,
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
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
        query_embedding = self._embedding_function.embed_query(query)

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

            # ============================================
            # FIX: Normalize content to strip BOM characters
            # This is the root cause fix for the encoding error
            # ============================================
            content = normalize_text(payload.pop("content", ""))
            doc_id = payload.pop("doc_id", None)

            # Also normalize any string metadata fields
            clean_metadata = {}
            for key, value in payload.items():
                if isinstance(value, str):
                    clean_metadata[key] = normalize_text(value)
                else:
                    clean_metadata[key] = value

            # Deduplication
            content_hash = hash(content[:500])
            if content_hash in seen_content:
                continue
            seen_content.add(content_hash)

            search_results.append(
                SearchResult(
                    document=Document(
                        content=content,
                        metadata=clean_metadata,
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
            self.REGULATIONS_COLLECTION,
            self.STEWARDS_COLLECTION,
            self.RACE_DATA_COLLECTION,
        ]:
            try:
                results = self.search(query, collection_name, top_k)
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"Search failed for collection {collection_name}: {e}")

        # Sort by score and return top results
        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:top_k]

    def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """Get statistics for a collection.

        Args:
            collection_name: Name of the collection.

        Returns:
            Dict with collection statistics.
        """
        try:
            client = self._get_client()
            stats = client.get_collection(collection_name=collection_name)
            return {
                "count": stats.points_count,
                "status": str(stats.status),
            }
        except Exception as e:
            # Collection might not exist
            logger.warning(f"Failed to get stats for {collection_name}: {e}")
            return {"count": 0, "status": "unknown"}

    def document_exists(self, collection_name: str, url: str, config_hash: str) -> bool:
        """Check if a document exists with the given URL and config hash.

        Args:
            collection_name: Collection to search in.
            url: Source URL of the document.
            config_hash: Hash of the configuration used for ingestion.

        Returns:
            True if document exists with matching config, False otherwise.
        """
        from qdrant_client.http import models

        try:
            client = self._get_client()
            # Use scroll to find at least one point matching the filter
            # We filter by URL (source identifier) AND config_hash (to ensure re-index on change)
            results, _ = client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(key="url", match=models.MatchValue(value=url)),
                        models.FieldCondition(
                            key="config_hash", match=models.MatchValue(value=config_hash)
                        ),
                    ]
                ),
                limit=1,
                with_payload=False,
                with_vectors=False,
            )
            return len(results) > 0
        except Exception as e:
            logger.warning(f"Error checking document existence: {e}")
            return False

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
