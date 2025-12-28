"""Use-case service for answering a question."""

from __future__ import annotations

from collections.abc import Generator

from ...common.utils import normalize_text
from ...domain.models import Answer, QueryType, RetrievalContext, SourceCitation
from ...domain.services.prompt_builder import PromptBuilder
from ...domain.services.query_classifier import QueryClassifier
from ...ports.llm import LLMPort
from ...ports.retrieval import RetrievalPort


class AskQuestionService:
    """Application service orchestrating classification, retrieval, and generation."""

    def __init__(
        self,
        classifier: QueryClassifier,
        prompt_builder: PromptBuilder,
        llm: LLMPort,
        retriever: RetrievalPort,
    ) -> None:
        self.classifier = classifier
        self.prompt_builder = prompt_builder
        self.llm = llm
        self.retriever = retriever

    def _build_sources(self, context: RetrievalContext) -> list[SourceCitation]:
        sources: list[SourceCitation] = []

        for snippet in context.regulations[:3]:
            source_title = normalize_text(str(snippet.metadata.get("source", "FIA Regulations")))
            if source_title and all(src.title != source_title for src in sources):
                sources.append(SourceCitation(title=source_title, doc_type="regulation"))

        for snippet in context.stewards_decisions[:3]:
            event = normalize_text(str(snippet.metadata.get("event", "Unknown")))
            source = normalize_text(str(snippet.metadata.get("source", "Stewards Decision")))
            title = f"{source} ({event})"
            if all(src.title != title for src in sources):
                sources.append(SourceCitation(title=title, doc_type="stewards_decision"))

        for snippet in context.race_data[:3]:
            race = normalize_text(str(snippet.metadata.get("race", "Race") or "Race"))
            season = snippet.metadata.get("season", "")
            title = f"{race} {season}".strip()
            if all(src.title != title for src in sources):
                sources.append(SourceCitation(title=title, doc_type="race_control"))

        return sources

    def ask(self, query: str, top_k: int = 5) -> Answer:
        clean_query = normalize_text(query)
        if not clean_query or not clean_query.strip():
            raise ValueError("Query cannot be empty or whitespace only")

        query_type: QueryType = self.classifier.classify(clean_query)
        query_context = self.retriever.extract_race_context(clean_query)
        context = self.retriever.retrieve(clean_query, top_k=top_k, query_context=query_context)

        prompt, system_prompt = self.prompt_builder.build(clean_query, query_type, context)
        response_text = self.llm.generate(prompt, system_prompt=system_prompt)
        sources = self._build_sources(context)

        return Answer(
            text=response_text,
            query_type=query_type,
            sources=sources,
            context=context,
            model_used=None,
        )

    def ask_stream(self, query: str, top_k: int = 5) -> Generator[str, None, Answer]:
        clean_query = normalize_text(query)
        if not clean_query or not clean_query.strip():
            raise ValueError("Query cannot be empty or whitespace only")

        query_type: QueryType = self.classifier.classify(clean_query)
        query_context = self.retriever.extract_race_context(clean_query)
        context = self.retriever.retrieve(clean_query, top_k=top_k, query_context=query_context)

        prompt, system_prompt = self.prompt_builder.build(clean_query, query_type, context)

        full_response = ""
        for chunk in self.llm.generate_stream(prompt, system_prompt=system_prompt):
            full_response += chunk
            yield chunk

        sources = self._build_sources(context)
        return Answer(
            text=full_response,
            query_type=query_type,
            sources=sources,
            context=context,
            model_used=None,
        )
