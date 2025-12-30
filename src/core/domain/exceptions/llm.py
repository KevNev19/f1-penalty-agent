"""LLM exceptions for F1 Penalty Agent."""

from .base import F1AgentError


class LLMError(F1AgentError):
    """Base error for LLM operations."""

    error_code = "F1_LLM_001"


class LLMConnectionError(LLMError):
    """Failed to connect to LLM provider.

    Common causes:
    - Invalid API key
    - Network issues
    - Service unavailable
    """

    error_code = "F1_LLM_002"


class LLMRateLimitError(LLMError):
    """Rate limit exceeded on LLM provider.

    The free tier has limited requests per minute.
    Wait a moment and try again.
    """

    error_code = "F1_LLM_003"


class LLMGenerationError(LLMError):
    """Failed to generate LLM response.

    Common causes:
    - Content filtered by safety settings
    - Token limit exceeded
    - Invalid prompt format
    """

    error_code = "F1_LLM_004"
