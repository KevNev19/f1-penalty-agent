"""Prompt construction for the ask question use case."""

from __future__ import annotations

from ..models import QueryType, RetrievalContext
from ...agent.prompts import (
    F1_SYSTEM_PROMPT,
    GENERAL_F1_PROMPT,
    PENALTY_EXPLANATION_PROMPT,
    RULE_LOOKUP_PROMPT,
)


class PromptBuilder:
    """Build prompts from domain objects."""

    def build(self, query: str, query_type: QueryType, context: RetrievalContext) -> tuple[str, str]:
        if query_type == QueryType.PENALTY_EXPLANATION:
            template = PENALTY_EXPLANATION_PROMPT
        elif query_type == QueryType.RULE_LOOKUP:
            template = RULE_LOOKUP_PROMPT
        else:
            template = GENERAL_F1_PROMPT

        prompt = template.format(context=context.get_combined_context(), question=query)
        return prompt, F1_SYSTEM_PROMPT
