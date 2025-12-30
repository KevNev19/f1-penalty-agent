"""Exception handling utilities for consistent error formatting.

This module provides functions to format exceptions as structured JSON,
log them consistently, and handle them in a uniform way across the application.
"""

import json
import logging
import traceback
from typing import Any

from .exceptions import F1AgentError

logger = logging.getLogger(__name__)


def format_exception_json(
    exc: Exception,
    include_trace: bool = False,
    extra_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Format any exception as structured JSON.

    Works with both F1AgentError and standard Python exceptions.

    Args:
        exc: The exception to format.
        include_trace: If True, include full stack trace.
        extra_context: Additional context to include in output.

    Returns:
        Dictionary with structured error information.

    Example:
        >>> try:
        ...     raise ValueError("Invalid input")
        ... except Exception as e:
        ...     error_json = format_exception_json(e, include_trace=True)
        ...     print(json.dumps(error_json, indent=2))
    """
    if isinstance(exc, F1AgentError):
        result = exc.to_dict(include_trace=include_trace)
        if extra_context:
            result.setdefault("context", {}).update(extra_context)
        return result

    # Handle standard Python exceptions
    tb = traceback.extract_tb(exc.__traceback__) if exc.__traceback__ else []
    last_frame = tb[-1] if tb else None

    result: dict[str, Any] = {
        "error": {
            "type": type(exc).__name__,
            "code": "PYTHON_ERR",
            "message": str(exc),
        },
        "location": {
            "class": "<unknown>",
            "method": last_frame.name if last_frame else "<unknown>",
            "file": (
                last_frame.filename.split("\\")[-1].split("/")[-1] if last_frame else "<unknown>"
            ),
            "line": last_frame.lineno if last_frame else 0,
        },
    }

    if extra_context:
        result["context"] = extra_context

    if include_trace:
        result["stack_trace"] = [
            line.strip()
            for line in traceback.format_exception(type(exc), exc, exc.__traceback__)
            if line.strip()
        ]

    return result


def log_exception(
    exc: Exception,
    log: logging.Logger | None = None,
    level: int = logging.ERROR,
    extra_context: dict[str, Any] | None = None,
) -> None:
    """Log exception in structured JSON format.

    Args:
        exc: The exception to log.
        log: Logger instance to use (defaults to module logger).
        level: Logging level (default: ERROR).
        extra_context: Additional context to include.

    Example:
        >>> try:
        ...     do_something_risky()
        ... except Exception as e:
        ...     log_exception(e, extra_context={"operation": "data_fetch"})
    """
    log_instance = log or logger

    exc_data = format_exception_json(exc, include_trace=True, extra_context=extra_context)
    log_instance.log(level, json.dumps(exc_data, indent=2))


def handle_exception(
    exc: Exception,
    context: dict[str, Any] | None = None,
    reraise: bool = True,
    log: logging.Logger | None = None,
) -> dict[str, Any]:
    """Handle and log exception, optionally re-raising.

    Use in try/except blocks for consistent handling. This function:
    1. Logs the exception with full details
    2. Returns a client-safe error dictionary (without traces)
    3. Optionally re-raises the exception

    Args:
        exc: The exception to handle.
        context: Additional context for debugging.
        reraise: If True, re-raise the exception after logging.
        log: Logger instance to use.

    Returns:
        Dictionary with error info (safe for client response).

    Example:
        >>> try:
        ...     fetch_data()
        ... except Exception as e:
        ...     error_info = handle_exception(e, context={"operation": "fetch"}, reraise=False)
        ...     return JSONResponse(status_code=500, content=error_info)
    """
    log_exception(exc, log=log, extra_context=context)

    # Return client-safe version (no traces)
    error_info = format_exception_json(exc, include_trace=False, extra_context=context)

    if reraise:
        raise exc

    return error_info


def get_error_code(exc: Exception) -> str:
    """Get the error code from an exception.

    Args:
        exc: The exception to get code from.

    Returns:
        Error code string (e.g., "F1_VEC_002" or "PYTHON_ERR").
    """
    if isinstance(exc, F1AgentError):
        return exc.error_code
    return "PYTHON_ERR"


def get_http_status_code(exc: Exception) -> int:
    """Map exception type to appropriate HTTP status code.

    Args:
        exc: The exception to map.

    Returns:
        HTTP status code (400, 429, 500, 503, etc.).
    """
    from .exceptions import (
        ConfigurationError,
        EmbeddingRateLimitError,
        LLMRateLimitError,
        ValidationError,
        VectorStoreError,
    )

    if isinstance(exc, ValidationError):
        return 400
    if isinstance(exc, LLMRateLimitError | EmbeddingRateLimitError):
        return 429
    if isinstance(exc, VectorStoreError):
        return 503
    if isinstance(exc, ConfigurationError):
        return 500
    if isinstance(exc, F1AgentError):
        return 500

    # Standard Python exceptions
    if isinstance(exc, ValueError):
        return 400
    if isinstance(exc, ConnectionError | TimeoutError):
        return 503

    return 500
