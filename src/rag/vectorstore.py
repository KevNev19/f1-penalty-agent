"""Vector store for document storage and retrieval using ChromaDB."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from rich.console import Console

console = Console()


@dataclass
class Document:
    """A document chunk with content and metadata."""

    content: str
    metadata: dict[str, Any]
    doc_id: Optional[str] = None


@dataclass
class SearchResult:
    """A search result with document and relevance score."""

    document: Document
    score: float


class GeminiEmbeddingFunction:
    """Embedding function using Google Gemini API."""
    
    def __init__(self, api_key: str):
        """Initialize with API key."""
        self.api_key = api_key
        self._model = None
    
    def name(self) -> str:
        """Return the embedding function name (required by ChromaDB)."""
        return "gemini-text-embedding-004"
    
    def _get_model(self):
        """Lazy load the embedding model."""
        if self._model is None:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._model = genai
        return self._model
    
    def __call__(self, input: list[str]) -> list[list[float]]:
        """Generate embeddings for the input texts (for documents).
        
        This is called by ChromaDB to generate embeddings for indexing.
        """
        return self._embed_texts(input, task_type="retrieval_document")
    
    def embed_query(self, input: str) -> list[float]:
        """Generate embedding for a single query text.
        
        This is called by ChromaDB when performing searches.
        Args:
            input: The query text to embed.
        """
        embeddings = self._embed_texts([input], task_type="retrieval_query")
        return embeddings[0] if embeddings else [0.0] * 768
    
    def _embed_texts(self, texts: list[str], task_type: str) -> list[list[float]]:
        """Generate embeddings for texts with specified task type."""
        model = self._get_model()
        embeddings = []
        
        # Process in batches to avoid rate limits
        batch_size = 10
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            for text in batch:
                try:
                    result = model.embed_content(
                        model="models/text-embedding-004",
                        content=text,
                        task_type=task_type,
                    )
                    embeddings.append(result["embedding"])
                except Exception as e:
                    console.print(f"[yellow]Embedding error: {e}[/]")
                    # Return a zero vector as fallback
                    embeddings.append([0.0] * 768)
        
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
        api_key: Optional[str] = None,
        chroma_host: Optional[str] = None,
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
        self._collections: dict[str, Any] = {}
        self._embedding_function = None

    def _get_client(self) -> Any:
        """Get or create ChromaDB client.
        
        Uses HttpClient if chroma_host is set (k3d/Docker mode),
        otherwise uses PersistentClient (local mode with SegmentAPI workaround).
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
                console.print(f"[green]ChromaDB connected to {self.chroma_host}:{self.chroma_port}[/]")
            else:
                # Use PersistentClient for local development
                # IMPORTANT: Use SegmentAPI to avoid Rust bindings hanging on Windows/Python 3.12
                # See: https://github.com/chroma-core/chroma/issues/189
                self._client = chromadb.PersistentClient(
                    path=str(self.persist_dir),
                    settings=Settings(
                        anonymized_telemetry=False,
                        chroma_api_impl="chromadb.api.segment.SegmentAPI",
                    ),
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
            
            # For HttpClient, we don't pass embedding_function (generate embeddings client-side)
            # For PersistentClient, we can use the embedding function
            if self.chroma_host:
                # HttpClient mode - no embedding_function
                self._collections[name] = client.get_or_create_collection(
                    name=name,
                    metadata={"hnsw:space": "cosine"},
                )
            else:
                # PersistentClient mode - use embedding function
                ef = self._get_embedding_function()
                self._collections[name] = client.get_or_create_collection(
                    name=name,
                    metadata={"hnsw:space": "cosine"},
                    embedding_function=ef,
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
        ids = [
            doc.doc_id or f"{collection_name}_{i}"
            for i, doc in enumerate(documents)
        ]

        console.print(f"[blue]Indexing {len(documents)} documents...[/]")
        
        # For HttpClient, generate embeddings client-side
        if self.chroma_host:
            ef = self._get_embedding_function()
            embeddings = ef(contents)
            collection.add(
                documents=contents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings,
            )
        else:
            # PersistentClient - ChromaDB handles embeddings via collection's embedding_function
            collection.add(
                documents=contents,
                metadatas=metadatas,
                ids=ids,
            )

        console.print(f"[green]Added {len(documents)} documents to {collection_name}[/]")
        return len(documents)

    def search(
        self,
        query: str,
        collection_name: str = REGULATIONS_COLLECTION,
        top_k: int = 5,
        filter_metadata: Optional[dict] = None,
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

        # For HttpClient, generate query embedding client-side
        if self.chroma_host:
            ef = self._get_embedding_function()
            query_embedding = ef.embed_query(input=query)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"],
            )
        else:
            # PersistentClient - ChromaDB handles query embedding
            results = collection.query(
                query_texts=[query],
                n_results=top_k,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"],
            )

        # Convert to SearchResult objects
        search_results = []
        if results["documents"] and results["documents"][0]:
            for i, doc_content in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                # ChromaDB returns distances, convert to similarity score
                distance = results["distances"][0][i] if results["distances"] else 0
                score = 1 - distance  # Cosine distance to similarity

                search_results.append(SearchResult(
                    document=Document(
                        content=doc_content,
                        metadata=metadata,
                        doc_id=results["ids"][0][i] if results["ids"] else None,
                    ),
                    score=score,
                ))

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
            except Exception:
                # Collection might not exist yet
                pass

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
            collection = self._get_collection(collection_name)
            return {
                "name": collection_name,
                "count": collection.count(),
            }
        except Exception:
            return {"name": collection_name, "count": 0}

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
        except Exception:
            pass
