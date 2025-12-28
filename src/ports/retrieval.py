"""Retrieval port abstraction."""

from __future__ import annotations

from typing import Protocol

from ..domain.models import RetrievalContext


class RetrievalPort(Protocol):
    """Abstract interface for fetching contextual documents."""

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        query_context: dict | None = None,
    ) -> RetrievalContext:  # pragma: no cover - protocol
        ...

    def extract_race_context(self, query: str) -> dict:  # pragma: no cover - protocol
        ...
