"""LLM port abstraction."""

from __future__ import annotations

from collections.abc import Generator
from typing import Protocol


class LLMPort(Protocol):
    """Abstract interface for text generation."""

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:  # pragma: no cover - protocol
        ...

    def generate_stream(
        self, prompt: str, system_prompt: str | None = None
    ) -> Generator[str, None, None]:  # pragma: no cover - protocol
        ...
