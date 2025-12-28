"""Google Gemini API client for LLM inference using the google-genai SDK."""

from collections.abc import Generator
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from google import genai

from ..common.utils import normalize_text

console = Console()


class GeminiClient:
    """Client for Google Gemini API using the new google-genai SDK."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        """Initialize the Gemini client.

        Args:
            api_key: Google AI API key.
            model: Model to use (default: gemini-2.0-flash for free tier).
        """
        self.api_key = api_key
        self.model_name = model
        self._client = None

    def _get_client(self) -> "genai.Client":
        """Lazy load the Gemini client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError(
                    "Google API key not set. Get one at https://aistudio.google.com/ "
                    "and set GOOGLE_API_KEY in your .env file."
                )

            from google import genai

            self._client = genai.Client(api_key=self.api_key)
            console.print(f"[green]Gemini client initialized for model: {self.model_name}[/]")

        return self._client

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        max_retries: int = 3,
    ) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: User prompt/question.
            system_prompt: Optional system instructions.
            temperature: Sampling temperature (0.0-1.0).
            max_tokens: Maximum tokens to generate.
            max_retries: Maximum retry attempts for rate limits.

        Returns:
            Generated text response.
        """
        import time

        from google.genai.types import GenerateContentConfig

        client = self._get_client()

        if system_prompt:
            full_prompt = f"{system_prompt}\n\n---\n\nUser Question: {prompt}"
        else:
            full_prompt = prompt

        # Normalize prompt to prevent BOM/whitespace issues while preserving UTF-8
        full_prompt = normalize_text(full_prompt)

        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt,
                    config=GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                    ),
                )

                # Handle safety filters (check candidates)
                if not response.candidates:
                    return "I apologize, but I cannot provide a response to that query."

                return normalize_text(response.text)

            except Exception as e:
                error_msg = str(e).lower()
                if "quota" in error_msg or "rate" in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = 2**attempt  # Exponential backoff
                        console.print(f"[yellow]Rate limit hit, retrying in {wait_time}s...[/]")
                        time.sleep(wait_time)
                    else:
                        return (
                            "Rate limit reached. Please wait a moment and try again.\n"
                            "Tip: The free tier has limited requests per minute."
                        )
                else:
                    console.print(f"[red]Gemini error: {e}[/]")
                    raise

        return "Failed to generate response after retries."

    def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> Generator[str, None, None]:
        """Generate a streaming response from the LLM.

        Args:
            prompt: User prompt/question.
            system_prompt: Optional system instructions.
            temperature: Sampling temperature (0.0-1.0).

        Yields:
            Text chunks as they're generated.
        """
        from google.genai.types import GenerateContentConfig

        client = self._get_client()

        if system_prompt:
            full_prompt = f"{system_prompt}\n\n---\n\nUser Question: {prompt}"
        else:
            full_prompt = prompt

        # Normalize prompt to prevent encoding errors
        full_prompt = normalize_text(full_prompt)

        try:
            # Use generate_content_stream for streaming
            for chunk in client.models.generate_content_stream(
                model=self.model_name,
                contents=full_prompt,
                config=GenerateContentConfig(temperature=temperature),
            ):
                if chunk.text:
                    yield normalize_text(chunk.text)

        except Exception as e:
            error_msg = str(e)
            if "quota" in error_msg.lower() or "rate" in error_msg.lower():
                yield "Rate limit reached. Please wait and try again."
            else:
                yield f"Error: {e}"

    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string.

        Args:
            text: Text to count tokens for.

        Returns:
            Approximate token count.
        """
        client = self._get_client()
        try:
            response = client.models.count_tokens(
                model=self.model_name,
                contents=text,
            )
            return response.total_tokens
        except Exception:
            # Fallback: rough estimate
            return len(text) // 4
