"""Pure query classification logic."""

from __future__ import annotations

import re

from ..models import QueryType


class QueryClassifier:
    """Classify incoming user questions into coarse types."""

    def classify(self, query: str) -> QueryType:
        query_lower = query.lower()

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
