"""Agent-related models for query classification and responses."""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .document import SearchResult


class QueryType(Enum):
    """Type of user query for the F1 agent.

    Used to determine which prompt template to use and
    how to structure the response.

    Attributes:
        PENALTY_EXPLANATION: Questions about why a specific penalty was given.
        RULE_LOOKUP: Questions about FIA rules and regulations.
        GENERAL: General F1 questions that don't fit other categories.
    """

    PENALTY_EXPLANATION = "penalty_explanation"
    RULE_LOOKUP = "rule_lookup"
    ANALYTICS = "analytics"
    GENERAL = "general"


@dataclass
class ChatMessage:
    """A single message in the chat history."""

    role: str
    content: str


@dataclass
class RetrievalContext:
    """Context retrieved for answering a question.

    Holds the search results from different collections that will
    be used to build the LLM prompt context.

    Attributes:
        regulations: Search results from FIA regulations.
        stewards_decisions: Search results from stewards decisions.
        race_data: Search results from race control messages.
        query: The original user query.
    """

    regulations: list["SearchResult"]
    stewards_decisions: list["SearchResult"]
    race_data: list["SearchResult"]
    query: str

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Normalize text for safe use in prompts and metadata."""
        from .utils import normalize_text

        return normalize_text(text)

    def get_combined_context(self, max_chars: int = 8000) -> str:
        """Get combined context string for the LLM.

        Args:
            max_chars: Maximum characters to include.

        Returns:
            Formatted context string, or informative message if no context found.
        """
        from .utils import normalize_text

        parts = []
        char_count = 0

        # Add regulations first (most authoritative)
        if self.regulations:
            parts.append("=== FIA REGULATIONS ===")
            for result in self.regulations:
                if char_count > max_chars:
                    break
                content = normalize_text(result.document.content or "")
                source = normalize_text(result.document.metadata.get("source", "Unknown") or "")
                parts.append(f"\n[Source: {source}]\n{content}")
                char_count += len(content)

        # Add stewards decisions (specific examples)
        if self.stewards_decisions:
            parts.append("\n\n=== STEWARDS DECISIONS ===")
            for result in self.stewards_decisions:
                if char_count > max_chars:
                    break
                content = normalize_text(result.document.content or "")
                event = normalize_text(result.document.metadata.get("event", "Unknown") or "")
                parts.append(f"\n[Event: {event}]\n{content}")
                char_count += len(content)

        # Add race data (live events)
        if self.race_data:
            parts.append("\n\n=== RACE CONTROL MESSAGES ===")
            for result in self.race_data:
                if char_count > max_chars:
                    break
                content = normalize_text(result.document.content or "")
                parts.append(f"\n{content}")
                char_count += len(content)

        # Return informative message if no context found
        if not parts:
            return "No specific regulatory context found for this query. Please provide a general response based on F1 knowledge."

        return "\n".join(parts)


@dataclass
class AgentResponse:
    """Response from the F1 agent.

    Contains the generated answer along with metadata about
    the query and sources used.

    Attributes:
        answer: The generated response text.
        query_type: How the query was classified.
        sources_used: List of source citations.
        context: The retrieval context used (optional).
    """

    answer: str
    query_type: QueryType
    sources_used: list[str]
    context: "RetrievalContext | None" = None
