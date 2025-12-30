"""Base exception classes for F1 Penalty Agent.

This module provides the foundation for structured exceptions with automatic
context capture, similar to Java's exception handling patterns. Each exception
includes:
- Error codes for quick identification
- Automatic capture of class, method, file, and line number
- Cause chaining for underlying exceptions
- JSON serialization for structured logging
"""

import inspect
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class ExceptionContext:
    """Captures location and context where exception occurred."""

    class_name: str
    method_name: str
    file_name: str
    line_number: int
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for JSON serialization."""
        return {
            "class": self.class_name,
            "method": self.method_name,
            "file": self.file_name,
            "line": self.line_number,
            "timestamp": self.timestamp,
        }


class F1AgentError(Exception):
    """Base exception for all F1 Agent errors.

    All custom exceptions should inherit from this class to ensure
    consistent error handling and JSON output format.

    Example:
        try:
            connect_to_qdrant()
        except SomeError as e:
            raise QdrantConnectionError(
                "Failed to connect to Qdrant",
                cause=e,
                context={"url": qdrant_url}
            )
    """

    error_code: str = "F1_ERR_001"

    def __init__(
        self,
        message: str,
        *,
        cause: Exception | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the exception with message and optional context.

        Args:
            message: Human-readable error message.
            cause: The underlying exception that caused this error.
            context: Additional context as key-value pairs for debugging.
        """
        super().__init__(message)
        self.message = message
        self.cause = cause
        self.extra_context = context or {}
        self.location = self._capture_location()
        self.stack_trace = traceback.format_exc() if cause else None

    def _capture_location(self) -> ExceptionContext:
        """Automatically capture class/method/file/line from call stack."""
        # Walk up the stack to find the actual caller
        frame = inspect.currentframe()
        # Skip: _capture_location -> __init__ -> raise site
        for _ in range(3):
            if frame and frame.f_back:
                frame = frame.f_back

        if frame:
            class_instance = frame.f_locals.get("self", None)
            return ExceptionContext(
                class_name=type(class_instance).__name__ if class_instance else "<module>",
                method_name=frame.f_code.co_name,
                file_name=frame.f_code.co_filename.split("\\")[-1].split("/")[-1],
                line_number=frame.f_lineno,
            )
        return ExceptionContext("<unknown>", "<unknown>", "<unknown>", 0)

    def to_dict(self, include_trace: bool = False) -> dict[str, Any]:
        """Convert exception to structured dictionary for JSON output.

        Args:
            include_trace: If True, include full stack trace (debug mode).

        Returns:
            Dictionary with error details, location, and optional trace.
        """
        result: dict[str, Any] = {
            "error": {
                "type": type(self).__name__,
                "code": self.error_code,
                "message": self.message,
            },
            "location": self.location.to_dict(),
        }

        if self.extra_context:
            result["context"] = self.extra_context

        if include_trace and self.stack_trace:
            result["stack_trace"] = [line for line in self.stack_trace.split("\n") if line.strip()]

        if self.cause:
            result["cause"] = {
                "type": type(self.cause).__name__,
                "message": str(self.cause),
            }

        return result
