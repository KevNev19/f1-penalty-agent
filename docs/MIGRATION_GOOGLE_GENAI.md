# Migration Plan: google-generativeai → google-genai

> **Status: ✅ COMPLETED** (December 17, 2025)
>
> This migration has been implemented. See commits on branch `claude/migrate-google-genai-EYpex`.

## Overview

The `google-generativeai` package reached End-of-Life on **November 30, 2025**. This document outlines the migration plan to the new `google-genai` SDK.

**References:**
- [Migration Guide](https://ai.google.dev/gemini-api/docs/migrate)
- [google-genai PyPI](https://pypi.org/project/google-genai/)
- [Google Gen AI SDK GitHub](https://github.com/googleapis/python-genai)

## Impact Assessment

### Files Requiring Changes

| File | Changes Required | Complexity |
|------|------------------|------------|
| `pyproject.toml` | Replace dependency | Low |
| `src/llm/gemini_client.py` | Full rewrite of client | Medium |
| `src/rag/vectorstore.py` | Update embedding function | Medium |
| `src/config.py` | Update env var name (optional) | Low |
| `tests/test_suite.py` | Update mocks | Low |

### Breaking Changes Summary

1. **Package name**: `google-generativeai` → `google-genai`
2. **Import**: `import google.generativeai as genai` → `from google import genai`
3. **Configuration**: `genai.configure(api_key=...)` → `genai.Client(api_key=...)`
4. **Model access**: `genai.GenerativeModel(name)` → `client.models.generate_content(model=name, ...)`
5. **Embeddings**: `genai.embed_content(...)` → `client.models.embed_content(...)`
6. **Streaming**: `model.generate_content(..., stream=True)` → `client.models.generate_content_stream(...)`
7. **Env var**: `GOOGLE_API_KEY` → `GEMINI_API_KEY` (recommended, but old still works)

---

## Detailed Code Changes

### 1. pyproject.toml

```diff
- # NOTE: google-generativeai reached EOL on Nov 30, 2025
- # TODO: Migrate to google-genai package (requires code changes)
- # See: https://ai.google.dev/gemini-api/docs/libraries
- "google-generativeai>=0.8.5",
+ "google-genai>=1.0.0",
```

### 2. src/llm/gemini_client.py

#### Current Code (OLD)
```python
import google.generativeai as genai

genai.configure(api_key=self.api_key)
self._model = genai.GenerativeModel(self.model_name)

response = model.generate_content(
    full_prompt,
    generation_config={
        "temperature": temperature,
        "max_output_tokens": max_tokens,
    },
)
```

#### New Code (NEW)
```python
from google import genai
from google.genai.types import GenerateContentConfig

self._client = genai.Client(api_key=self.api_key)

response = self._client.models.generate_content(
    model=self.model_name,
    contents=full_prompt,
    config=GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
    ),
)
```

#### Full Rewritten gemini_client.py

```python
"""Google Gemini API client for LLM inference."""

from collections.abc import Generator

from rich.console import Console

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

    def _get_client(self):
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

        # Combine system and user prompts
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n---\n\nUser Question: {prompt}"
        else:
            full_prompt = prompt

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

                return response.text

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

        try:
            # Use generate_content_stream for streaming
            for chunk in client.models.generate_content_stream(
                model=self.model_name,
                contents=full_prompt,
                config=GenerateContentConfig(temperature=temperature),
            ):
                if chunk.text:
                    yield chunk.text

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
```

### 3. src/rag/vectorstore.py - GeminiEmbeddingFunction

#### Current Code (OLD)
```python
class GeminiEmbeddingFunction:
    def _get_model(self):
        if self._model is None:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._model = genai
        return self._model

    def _embed_texts(self, texts: list[str], task_type: str) -> list[list[float]]:
        model = self._get_model()
        result = model.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type=task_type,
        )
        embeddings.append(result["embedding"])
```

#### New Code (NEW)
```python
class GeminiEmbeddingFunction:
    """Embedding function using Google Gemini API (google-genai SDK)."""

    def __init__(self, api_key: str):
        """Initialize with API key."""
        self.api_key = api_key
        self._client = None

    def name(self) -> str:
        """Return the embedding function name (required by ChromaDB)."""
        return "gemini-text-embedding-004"

    def _get_client(self):
        """Lazy load the Gemini client."""
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def __call__(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for the input texts (for documents)."""
        return self._embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        """Generate embedding for a single query text."""
        embeddings = self._embed_texts([text], task_type="RETRIEVAL_QUERY")
        return embeddings[0] if embeddings else [0.0] * 768

    def _embed_texts(self, texts: list[str], task_type: str) -> list[list[float]]:
        """Generate embeddings for texts with specified task type."""
        import time
        from google.genai.types import EmbedContentConfig

        client = self._get_client()
        embeddings = []

        batch_size = 10
        max_retries = 3

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            for text in batch:
                for attempt in range(max_retries):
                    try:
                        result = client.models.embed_content(
                            model="text-embedding-004",
                            contents=text,
                            config=EmbedContentConfig(task_type=task_type),
                        )
                        # New SDK returns embedding directly
                        embeddings.append(result.embeddings[0].values)
                        break
                    except Exception as e:
                        error_msg = str(e).lower()
                        if "rate" in error_msg or "quota" in error_msg:
                            wait_time = 2**attempt
                            console.print(f"[yellow]Rate limit hit, retrying in {wait_time}s...[/]")
                            time.sleep(wait_time)
                        elif attempt == max_retries - 1:
                            console.print(f"[red]Embedding error after {max_retries} attempts: {e}[/]")
                            embeddings.append([0.0] * 768)
                        else:
                            time.sleep(0.5)

        return embeddings
```

---

## Migration Steps

### Phase 1: Preparation
1. [ ] Create feature branch `feature/migrate-google-genai`
2. [ ] Add `google-genai>=1.0.0` to pyproject.toml alongside existing package
3. [ ] Run `poetry lock` to verify no dependency conflicts

### Phase 2: Code Changes
4. [ ] Update `src/llm/gemini_client.py` with new SDK
5. [ ] Update `GeminiEmbeddingFunction` in `src/rag/vectorstore.py`
6. [ ] Update any test mocks that reference the old SDK

### Phase 3: Testing
7. [ ] Run unit tests: `poetry run pytest tests/ -m unit -v`
8. [ ] Test embedding generation manually
9. [ ] Test LLM generation manually
10. [ ] Test streaming responses

### Phase 4: Cleanup
11. [ ] Remove `google-generativeai` from pyproject.toml
12. [ ] Remove migration TODO comments
13. [ ] Update README if needed

### Phase 5: Deploy
14. [ ] Run full CI pipeline
15. [ ] Create PR for review
16. [ ] Merge and deploy

---

## Key API Differences

| Feature | Old SDK | New SDK |
|---------|---------|---------|
| Package | `google-generativeai` | `google-genai` |
| Import | `import google.generativeai as genai` | `from google import genai` |
| Init | `genai.configure(api_key=...)` | `client = genai.Client(api_key=...)` |
| Generate | `model.generate_content(prompt)` | `client.models.generate_content(model=..., contents=...)` |
| Stream | `model.generate_content(..., stream=True)` | `client.models.generate_content_stream(...)` |
| Embed | `genai.embed_content(model=..., content=...)` | `client.models.embed_content(model=..., contents=...)` |
| Token count | `model.count_tokens(text)` | `client.models.count_tokens(model=..., contents=...)` |
| Config | Dict `{"temperature": 0.7}` | `GenerateContentConfig(temperature=0.7)` |
| Embedding result | `result["embedding"]` | `result.embeddings[0].values` |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| API behavior differences | Medium | Extensive testing before merge |
| Rate limit handling changes | Low | Keep same retry logic |
| Embedding dimension changes | High | Verify 768 dimensions maintained |
| Breaking existing indexes | High | Test with fresh ChromaDB instance first |

---

## Rollback Plan

If issues arise:
1. Revert pyproject.toml to use `google-generativeai>=0.8.5`
2. Revert code changes in `gemini_client.py` and `vectorstore.py`
3. Run `poetry lock && poetry install`

The old package will continue to work (just without new features/support).
