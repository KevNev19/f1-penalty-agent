"""Domain models for the F1 penalty assistant."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ...common.utils import normalize_text


class QueryType(Enum):
    """Type of user query."""

    PENALTY_EXPLANATION = "penalty_explanation"
    RULE_LOOKUP = "rule_lookup"
    GENERAL = "general"


@dataclass
class SourceCitation:
    """Metadata describing where an answer came from."""

    title: str
    doc_type: str
    relevance_score: float | None = None
    excerpt: str | None = None


@dataclass
class DocumentSnippet:
    """Small slice of text and metadata returned by retrieval."""

    content: str
    metadata: dict[str, Any]


@dataclass
class RetrievalContext:
    """Aggregated retrieval context grouped by source type."""

    regulations: list[DocumentSnippet]
    stewards_decisions: list[DocumentSnippet]
    race_data: list[DocumentSnippet]
    query: str

    def get_combined_context(self, max_chars: int = 8000) -> str:
        """Combine retrieved snippets into a prompt-friendly block."""

        parts: list[str] = []
        char_count = 0

        if self.regulations:
            parts.append("=== FIA REGULATIONS ===")
            for snippet in self.regulations:
                if char_count > max_chars:
                    break
                source = normalize_text(snippet.metadata.get("source") or "Unknown")
                content = normalize_text(snippet.content or "")
                parts.append(f"\n[Source: {source}]\n{content}")
                char_count += len(content)

        if self.stewards_decisions:
            parts.append("\n\n=== STEWARDS DECISIONS ===")
            for snippet in self.stewards_decisions:
                if char_count > max_chars:
                    break
                event = normalize_text(snippet.metadata.get("event") or "Unknown")
                content = normalize_text(snippet.content or "")
                parts.append(f"\n[Event: {event}]\n{content}")
                char_count += len(content)

        if self.race_data:
            parts.append("\n\n=== RACE CONTROL MESSAGES ===")
            for snippet in self.race_data:
                if char_count > max_chars:
                    break
                content = normalize_text(snippet.content or "")
                parts.append(f"\n{content}")
                char_count += len(content)

        if not parts:
            return (
                "No specific regulatory context found for this query. "
                "Please provide a general response based on F1 knowledge."
            )

        return "\n".join(parts)


@dataclass
class Answer:
    """Answer produced by the application service."""

    text: str
    query_type: QueryType
    sources: list[SourceCitation]
    context: RetrievalContext | None = None
    model_used: str | None = None
