"""Embedding model for converting text to vectors."""

from typing import Optional

import numpy as np
from rich.console import Console

console = Console()


class EmbeddingModel:
    """Wrapper for sentence-transformers embedding model."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        """Initialize the embedding model.

        Args:
            model_name: Name of the sentence-transformers model to use.
                        Default is all-MiniLM-L6-v2 (fast, good quality, 384 dims).
        """
        self.model_name = model_name
        self._model = None

    def _load_model(self) -> None:
        """Lazy load the model on first use."""
        if self._model is None:
            console.print(f"[blue]Loading embedding model: {self.model_name}...[/]")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            console.print("[green]Embedding model loaded[/]")

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text string.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector as list of floats.
        """
        self._load_model()
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Embed multiple texts efficiently.

        Args:
            texts: List of texts to embed.
            batch_size: Batch size for encoding.

        Returns:
            List of embedding vectors.
        """
        self._load_model()
        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 10,
        )
        return embeddings.tolist()

    def get_dimension(self) -> int:
        """Get the embedding dimension.

        Returns:
            Dimension of embedding vectors.
        """
        self._load_model()
        return self._model.get_sentence_embedding_dimension()
