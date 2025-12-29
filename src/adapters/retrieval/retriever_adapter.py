"""Adapter wrapping the existing retriever to the retrieval port."""

from __future__ import annotations

from ...domain.models import DocumentSnippet, RetrievalContext
from ...ports.retrieval import RetrievalPort
from ...rag.retriever import F1Retriever, SearchResult


class RetrieverAdapter(RetrievalPort):
    """Bridge from F1Retriever to the domain retrieval port."""

    def __init__(self, retriever: F1Retriever) -> None:
        self.retriever = retriever

    @staticmethod
    def _to_snippet(result: SearchResult) -> DocumentSnippet:
        return DocumentSnippet(
            content=result.document.content or "", metadata=result.document.metadata
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        query_context: dict | None = None,
    ) -> RetrievalContext:
        context = self.retriever.retrieve(query, top_k=top_k, query_context=query_context)
        return RetrievalContext(
            regulations=[self._to_snippet(r) for r in context.regulations],
            stewards_decisions=[self._to_snippet(r) for r in context.stewards_decisions],
            race_data=[self._to_snippet(r) for r in context.race_data],
            query=context.query,
        )

    def extract_race_context(self, query: str) -> dict:
        return self.retriever.extract_race_context(query)
