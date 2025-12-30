"""Validation exceptions for F1 Penalty Agent."""

from .base import F1AgentError


class ValidationError(F1AgentError):
    """Input validation failed."""

    error_code = "F1_VAL_001"


class EmptyQueryError(ValidationError):
    """Query cannot be empty or whitespace only."""

    error_code = "F1_VAL_002"


class QueryTooLongError(ValidationError):
    """Query exceeds maximum allowed length."""

    error_code = "F1_VAL_003"
