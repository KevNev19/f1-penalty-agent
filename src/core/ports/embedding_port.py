"""Embedding Port Interface."""

from abc import ABC, abstractmethod


class EmbeddingPort(ABC):
    """Abstract interface for embedding functions."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]: ...

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
