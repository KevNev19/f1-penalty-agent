"""Retrieval exceptions for F1 Penalty Agent."""

from .base import F1AgentError


class RetrievalError(F1AgentError):
    """Error during document retrieval."""

    error_code = "F1_RET_001"


class NoResultsError(RetrievalError):
    """No relevant documents found for query."""

    error_code = "F1_RET_002"
