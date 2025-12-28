"""Gemini client adapter implementing the LLM port."""

from __future__ import annotations

from collections.abc import Generator

from ...llm.gemini_client import GeminiClient
from ...ports.llm import LLMPort


class GeminiLLMAdapter(LLMPort):
    """Adapter that bridges the Gemini client to the LLM port."""

    def __init__(self, client: GeminiClient) -> None:
        self.client = client

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        return self.client.generate(prompt, system_prompt=system_prompt)

    def generate_stream(
        self, prompt: str, system_prompt: str | None = None
    ) -> Generator[str, None, None]:
        return self.client.generate_stream(prompt, system_prompt=system_prompt)
