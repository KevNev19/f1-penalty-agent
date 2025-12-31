"""F1 Penalty Agent - main agent orchestration."""

import logging
import re
from collections.abc import Generator

from ..domain import AgentResponse, QueryType, RetrievalContext
from ..domain.utils import normalize_text
from ..ports.llm_port import LLMPort
from .prompts import (
    F1_SYSTEM_PROMPT,
    GENERAL_F1_PROMPT,
    PENALTY_EXPLANATION_PROMPT,
    QUERY_REWRITE_PROMPT,
    RULE_LOOKUP_PROMPT,
)
from .retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class AgentService:
    """Main F1 Penalty Agent that answers questions about F1 rules and penalties."""

    def __init__(
        self,
        llm_client: LLMPort,
        retriever: RetrievalService,
    ) -> None:
        """Initialize the agent.

        Args:
            llm_client: LLM client for generating responses.
            retriever: Retriever for fetching relevant documents.
        """
        self.llm = llm_client
        self.retriever = retriever

    def classify_query(self, query: str) -> QueryType:
        """Classify the type of user query.

        Args:
            query: User's question.

        Returns:
            QueryType indicating what kind of question this is.
        """
        query_lower = query.lower()

        # Penalty explanation patterns
        penalty_patterns = [
            r"why did .+ get a penalty",
            r"why was .+ penalized",
            r"what penalty did .+ get",
            r"explain .+ penalty",
            r"what happened .+ penalty",
            r"penalty for .+ at",
            r"\bpenalized\b",
            r"\bpunished\b",
            r"\btime penalty\b",
            r"\bgrid penalty\b",
            r"5.second|10.second|drive.through",
        ]

        for pattern in penalty_patterns:
            if re.search(pattern, query_lower):
                return QueryType.PENALTY_EXPLANATION

        # Rule lookup patterns
        rule_patterns = [
            r"what is the rule",
            r"what's the rule",
            r"what are the rules",
            r"explain the rule",
            r"what does article",
            r"according to .+ regulations",
            r"is it allowed",
            r"is it legal",
            r"what's the penalty for",
            r"how are .+ penalized",
            r"track limits",
            r"unsafe release",
            r"blue flags",
            r"safety car",
            r"pit lane",
            r"impeding",
        ]

        for pattern in rule_patterns:
            if re.search(pattern, query_lower):
                return QueryType.RULE_LOOKUP

        return QueryType.GENERAL

    def build_prompt(
        self,
        query: str,
        query_type: QueryType,
        context: RetrievalContext,
    ) -> str:
        """Build the prompt for the LLM.

        Args:
            query: User's question.
            query_type: Classification of the query.
            context: Retrieved context.

        Returns:
            Formatted prompt string.
        """
        context_str = context.get_combined_context()

        if query_type == QueryType.PENALTY_EXPLANATION:
            template = PENALTY_EXPLANATION_PROMPT
        elif query_type == QueryType.RULE_LOOKUP:
            template = RULE_LOOKUP_PROMPT
        else:
            template = GENERAL_F1_PROMPT

        return template.format(context=context_str, question=query)

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Remove BOM and other problematic Unicode characters."""
        return normalize_text(str(text) if text else "")

    def get_sources(self, context: RetrievalContext) -> list[dict]:
        """Extract source citations from context.

        Args:
            context: Retrieved context.

        Returns:
            List of source dictionaries with metadata.
        """
        sources = []
        seen_keys = set()

        for result in context.regulations[:3]:
            title = self._sanitize_text(result.document.metadata.get("source", "FIA Regulations"))
            url = result.document.metadata.get("url")
            key = f"{title}_{url}"
            if title and key not in seen_keys:
                seen_keys.add(key)
                sources.append(
                    {
                        "source": title,
                        "doc_type": "regulation",
                        "score": result.score,
                        "excerpt": result.document.metadata.get("excerpt"),  # Extract if available
                        "url": url,
                    }
                )

        for result in context.stewards_decisions[:3]:
            event = self._sanitize_text(result.document.metadata.get("event", "Unknown"))
            source = self._sanitize_text(
                result.document.metadata.get("source", "Stewards Decision")
            )
            url = result.document.metadata.get("url")
            title = f"{source} ({event})"
            key = f"{title}_{url}"

            if title and key not in seen_keys:
                seen_keys.add(key)
                sources.append(
                    {"source": title, "doc_type": "stewards", "score": result.score, "url": url}
                )

        for result in context.race_data[:3]:
            race = self._sanitize_text(result.document.metadata.get("race", "Race") or "Race")
            season = result.document.metadata.get("season", "")
            title = f"{race} {season}"
            url = result.document.metadata.get("url")
            key = f"{title}_{url}"

            if title and key not in seen_keys:
                seen_keys.add(key)
                sources.append(
                    {"source": title, "doc_type": "race_control", "score": result.score, "url": url}
                )

        return sources

    def contextualize_query(self, query: str, messages: list[object]) -> str:
        """Rewrite query to include context from history if needed.

        Args:
            query: User's follow-up question.
            messages: Chat history (list of domain.ChatMessage).

        Returns:
            Rewritten query or original if no history.
        """
        if not messages:
            return query

        # Format history for prompt
        history_str = ""
        for msg in messages[-6:]:  # Keep last 3 turns
            history_str += f"{msg.role}: {msg.content}\n"

        prompt = QUERY_REWRITE_PROMPT.format(history=history_str, question=query)
        logger.debug("Contextualizing query...")
        rewritten = self.llm.generate(prompt)
        logger.debug("Rewritten query: %s", rewritten)
        return rewritten.strip()

    def ask(
        self, query: str, messages: list[object] | None = None, stream: bool = False
    ) -> AgentResponse:
        """Ask a question and get a response.

        Args:
            query: User's question about F1 penalties/rules.
            messages: Optional chat history for context.
            stream: Whether to stream the response (not used in basic version).

        Returns:
            AgentResponse with the answer and metadata.

        Raises:
            ValueError: If query is empty or whitespace only.
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty or whitespace only")

        # Use logger instead of console.print to avoid ASCII encoding issues
        # in Cloud Run where stdout may have limited encoding support
        logger.debug("Analyzing question...")

        # Contextualize query if history exists
        search_query = query
        if messages:
            search_query = self.contextualize_query(query, messages)

        # Classify the query (use original or rewritten? search_query is safer for classification too)
        query_type = self.classify_query(search_query)
        logger.debug("Query type: %s", query_type.value)

        # Extract context hints (driver, race, etc.) from SEARCH QUERY
        query_context = self.retriever.extract_race_context(search_query)
        logger.debug("Detected context: %s", query_context)

        # Retrieve relevant documents using SEARCH QUERY
        logger.debug("Searching knowledge base...")
        context = self.retriever.retrieve(search_query, top_k=5, query_context=query_context)

        # Build prompt using ORIGINAL query content (or search query? usually original is better for LLM but search for retrieval)
        # Actually, if we rewrite "When did he..." to "When did Hamilton...", we should probably use the rewritten one for generation too
        # so the model knows who "he" is if the retrieval context didn't make it obvious (though retrieval context should have Hamilton docs).
        # Let's use search_query for prompt too to be safe.
        prompt = self.build_prompt(search_query, query_type, context)

        # Generate response
        logger.debug("Generating response...")
        answer = self.llm.generate(prompt, system_prompt=F1_SYSTEM_PROMPT)

        # Get sources
        sources = self.get_sources(context)

        return AgentResponse(
            answer=answer,
            query_type=query_type,
            sources_used=sources,
            context=context,
        )

    def ask_stream(self, query: str) -> Generator[str, None, AgentResponse]:
        """Ask a question with streaming response.

        Args:
            query: User's question.

        Yields:
            Text chunks as they're generated.

        Returns:
            Final AgentResponse.

        Raises:
            ValueError: If query is empty or whitespace only.
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty or whitespace only")

        query_type = self.classify_query(query)
        query_context = self.retriever.extract_race_context(query)
        context = self.retriever.retrieve(query, top_k=5, query_context=query_context)
        prompt = self.build_prompt(query, query_type, context)

        full_response = ""
        for chunk in self.llm.generate_stream(prompt, system_prompt=F1_SYSTEM_PROMPT):
            full_response += chunk
            yield chunk

        sources = self.get_sources(context)

        return AgentResponse(
            answer=full_response,
            query_type=query_type,
            sources_used=sources,
            context=context,
        )

    def quick_answer(self, query: str) -> str:
        """Quick answer without metadata - for simple CLI use.

        Args:
            query: User's question.

        Returns:
            Answer text only.
        """
        response = self.ask(query)
        return response.answer
