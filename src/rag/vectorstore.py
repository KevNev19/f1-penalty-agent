"""Vector store for document storage and retrieval using ChromaDB."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.console import Console

if TYPE_CHECKING:
    from chromadb.api.models.Collection import Collection

console = Console()
logger = logging.getLogger(__name__)


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


from chromadb import Documents, Embeddings

class GeminiEmbeddingFunction:
    """Custom embedding function using Google Gemini API."""

    def __init__(self, api_key: str, model_name: str = "models/text-embedding-004"):
        self.api_key = api_key
        self.model_name = model_name
        try:
            from google import genai
            self.client = genai.Client(api_key=api_key)
        except ImportError:
            raise ImportError("Please install google-genai to use Gemini embeddings")

    def __call__(self, input) -> Embeddings:
        """Generate embeddings for the input texts (for documents).

        Args:
            input: List of document texts to embed.
        """
        console.print(f"[dim]Generating embeddings for {len(input)} documents...[/]")
        try:
            return self._embed_texts(input, task_type="RETRIEVAL_DOCUMENT")
        except Exception as e:
            console.print(f"[red]Embedding error: {e}[/]")
            import traceback
            traceback.print_exc()
            raise e

    def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a single query text.

        This is called by ChromaDB when performing searches.

        Args:
            text: The query text to embed.
        """
        embeddings = self._embed_texts([text], task_type="RETRIEVAL_QUERY")
        return embeddings[0] if embeddings else [0.0] * 768

    def _embed_texts(self, texts: list[str], task_type: str) -> list[list[float]]:
        """Generate embeddings using Google Gemini REST API (batchEmbedContents)."""
        import requests
        import time

        api_url = f"https://generativelanguage.googleapis.com/v1beta/{self.model_name}:batchEmbedContents?key={self.api_key}"
        embeddings = []

        # Process in batches (API limit is usually 100 requests per batch call, likely less for payload size)
        # Using 20 as a safe batch size to avoid payload limits
        batch_size = 20
        max_retries = 3

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            
            # Construct request body for batchEmbedContents
            requests_payload = []
            for text in batch_texts:
                requests_payload.append({
                    "model": self.model_name,
                    "content": {"parts": [{"text": text}]},
                    "taskType": task_type,
                    "title": "Document" if task_type == "RETRIEVAL_DOCUMENT" else None
                })
            
            payload = {"requests": requests_payload}
            
            for attempt in range(max_retries):
                try:
                    response = requests.post(api_url, json=payload, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        # Extract embeddings from response
                        if "embeddings" in data:
                            for emb in data["embeddings"]:
                                # Gemini API returns 'values'
                                embeddings.append(emb.get("values", [0.0] * 768))
                        else:
                             # Handle empty/partial response by adding zeros
                             console.print(f"[yellow]Warning: No embeddings in response: {data}[/]")
                             embeddings.extend([[0.0] * 768] * len(batch_texts))
                        break
                    elif response.status_code == 429:
                        wait_time = 2 ** attempt
                        console.print(f"[yellow]Rate limit hit (429), retrying in {wait_time}s...[/]")
                        time.sleep(wait_time)
                    else:
                        console.print(f"[red]API Error {response.status_code}: {response.text}[/]")
                        if attempt == max_retries - 1:
                            embeddings.extend([[0.0] * 768] * len(batch_texts))
                        time.sleep(1)
                except Exception as e:
                    console.print(f"[red]Request failed: {e}[/]")
                    if attempt == max_retries - 1:
                        embeddings.extend([[0.0] * 768] * len(batch_texts))
                    time.sleep(1)

        return embeddings


class VectorStore:
    """ChromaDB-based vector store for F1 documents.

    Uses Gemini API for embeddings to avoid Windows DLL issues with PyTorch/ONNX.
    """

    # Collection names for different document types
    REGULATIONS_COLLECTION = "f1_regulations"
    STEWARDS_COLLECTION = "stewards_decisions"
    RACE_DATA_COLLECTION = "race_data"

    def __init__(
        self,
        persist_dir: Path,
        api_key: str | None = None,
        chroma_host: str | None = None,
        chroma_port: int = 8000,
    ) -> None:
        """Initialize the vector store.

        Args:
            persist_dir: Directory for ChromaDB persistence (local mode).
            api_key: Google API key for embeddings.
            chroma_host: ChromaDB server host (if using HttpClient for k3d/Docker).
            chroma_port: ChromaDB server port (default 8000).
        """
        self.persist_dir = persist_dir
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = api_key
        self.chroma_host = chroma_host
        self.chroma_port = chroma_port
        self._client = None
        self._collections: dict[str, Collection] = {}
        self._embedding_function = None

    def reset(self) -> None:
        """Reset the vector store by deleting all collections.
        
        This is useful for full re-indexing.
        """
        # Ensure client is initialized
        client = self._get_client()
        for name in [
            self.REGULATIONS_COLLECTION,
            self.STEWARDS_COLLECTION,
            self.RACE_DATA_COLLECTION,
        ]:
            try:
                client.delete_collection(name)
                # Remove from cache
                if name in self._collections:
                    del self._collections[name]
                console.print(f"  [dim]Deleted collection {name}[/]")
            except Exception:
                # Collection might not exist
                pass
        console.print("[yellow]Vector store reset complete[/]")

    def _get_client(self) -> Any:
        """Get or create ChromaDB client.

        Uses HttpClient if chroma_host is set (k3d/Docker mode),
        otherwise uses PersistentClient (local mode).
        """
        if self._client is None:
            import chromadb
            from chromadb.config import Settings

            if self.chroma_host:
                # Use HttpClient for k3d/Docker ChromaDB server
                self._client = chromadb.HttpClient(
                    host=self.chroma_host,
                    port=self.chroma_port,
                )
                console.print(
                    f"[green]ChromaDB connected to {self.chroma_host}:{self.chroma_port}[/]"
                )
            else:
                # Use PersistentClient for local development
                # Simple initialization - ChromaDB handles internal API selection
                self._client = chromadb.PersistentClient(
                    path=str(self.persist_dir),
                    settings=Settings(anonymized_telemetry=False),
                )
                console.print(f"[green]ChromaDB initialized at {self.persist_dir}[/]")

        return self._client

    def _get_embedding_function(self) -> Any:
        """Get the Gemini embedding function."""
        if self._embedding_function is None:
            if self.api_key:
                self._embedding_function = GeminiEmbeddingFunction(self.api_key)
                console.print("[green]Using Gemini API for embeddings[/]")
            else:
                # Try to get from environment
                from ..config import settings

                if settings.google_api_key:
                    self._embedding_function = GeminiEmbeddingFunction(settings.google_api_key)
                    console.print("[green]Using Gemini API for embeddings[/]")
                else:
                    console.print("[red]No API key available for embeddings[/]")
                    return None

        return self._embedding_function

    def _get_collection(self, name: str) -> Any:
        """Get or create a collection.

        Args:
            name: Collection name.

        Returns:
            ChromaDB collection.
        """
        if name not in self._collections:
            client = self._get_client()

            # We generate embeddings client-side for both modes to avoid
            # ChromaDB 1.3+ EmbeddingFunction interface issues and inconsistencies.
            self._collections[name] = client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
                # No embedding_function passed - we handle it explicitly
            )
        return self._collections[name]

    def add_documents(
        self,
        documents: list[Document],
        collection_name: str = REGULATIONS_COLLECTION,
    ) -> int:
        """Add documents to the vector store.

        Args:
            documents: List of documents to add.
            collection_name: Name of the collection to add to.

        Returns:
            Number of documents added.
        """
        if not documents:
            return 0

        collection = self._get_collection(collection_name)

        # Prepare data for insertion
        contents = [doc.content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        ids = [doc.doc_id or f"{collection_name}_{i}" for i, doc in enumerate(documents)]

        console.print(f"[blue]Indexing {len(documents)} documents...[/]")

        # Generate embeddings explicitly
        ef = self._get_embedding_function()
        embeddings = ef(contents)
        
        collection.add(
            documents=contents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings,
        )

        console.print(f"[green]Added {len(documents)} documents to {collection_name}[/]")
        return len(documents)

    def search(
        self,
        query: str,
        collection_name: str = REGULATIONS_COLLECTION,
        top_k: int = 5,
        filter_metadata: dict | None = None,
    ) -> list[SearchResult]:
        """Search for relevant documents.

        Args:
            query: Search query.
            collection_name: Collection to search in.
            top_k: Number of results to return.
            filter_metadata: Optional metadata filter (ChromaDB where clause).

        Returns:
            List of SearchResult objects.
        """
        collection = self._get_collection(collection_name)

        # Generate query embedding explicitly
        ef = self._get_embedding_function()
        query_embedding = ef.embed_query(text=query)
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k * 2,  # Get extra for deduplication
            where=filter_metadata,
            # Note: ids are automatically included in ChromaDB 1.3+
            include=["documents", "metadatas", "distances"],
        )

        # Convert to SearchResult objects with deduplication
        search_results = []
        seen_content = set()  # Track content hashes for deduplication

        if results["documents"] and results["documents"][0]:
            for i, doc_content in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                # ChromaDB returns distances, convert to similarity score
                distance = results["distances"][0][i] if results["distances"] else 0
                score = 1 - distance  # Cosine distance to similarity

                # Skip low-score results (threshold at 0.5)
                if score < 0.5:
                    continue

                # Deduplication: skip if we've seen very similar content
                content_hash = hash(doc_content[:500])  # Hash first 500 chars
                if content_hash in seen_content:
                    continue
                seen_content.add(content_hash)

                search_results.append(
                    SearchResult(
                        document=Document(
                            content=doc_content,
                            metadata=metadata,
                            doc_id=results["ids"][0][i] if results["ids"] else None,
                        ),
                        score=score,
                    )
                )

                # Stop once we have enough unique results
                if len(search_results) >= top_k:
                    break

        return search_results

    def search_all_collections(
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
            except ValueError:
                # Collection doesn't exist yet - this is expected during initial setup
                logger.debug(f"Collection {collection_name} not found, skipping")
            except Exception as e:
                # Log unexpected errors but continue with other collections
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
            # Use client.get_collection directly to avoid _get_collection
            # which may trigger hnswlib issues with get_or_create_collection
            client = self._get_client()
            try:
                collection = client.get_collection(name=collection_name)
                return {
                    "name": collection_name,
                    "count": collection.count(),
                }
            except Exception:
                # Collection doesn't exist
                return {"name": collection_name, "count": 0}
        except Exception as e:
            logger.warning(f"Failed to get stats for collection {collection_name}: {e}")
            return {"name": collection_name, "count": 0, "error": str(e)}

    def clear_collection(self, collection_name: str) -> None:
        """Clear all documents from a collection.

        Args:
            collection_name: Name of the collection to clear.
        """
        client = self._get_client()
        try:
            client.delete_collection(collection_name)
            if collection_name in self._collections:
                del self._collections[collection_name]
            console.print(f"[yellow]Cleared collection: {collection_name}[/]")
        except ValueError:
            # Collection doesn't exist - nothing to clear
            logger.debug(f"Collection {collection_name} does not exist, nothing to clear")
        except Exception as e:
            logger.warning(f"Failed to clear collection {collection_name}: {e}")
