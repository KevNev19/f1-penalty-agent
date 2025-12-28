"""Common utilities for the F1 Penalty Agent.

This module contains shared helper functions used across CLI, API, and other components.
"""

import re


def normalize_text(text: str | None) -> str:
    """Normalize text while preserving UTF-8 characters.

    The helper removes UTF-8 byte order marks (``utf-8-sig``), standardizes
    whitespace, and trims surrounding space without re-encoding to ASCII. This
    keeps non-ASCII characters (e.g., café, Nürburgring) intact while removing
    problematic markers that can appear in scraped documents or API responses.

    Args:
        text: Input text that may contain BOM or irregular whitespace.

    Returns:
        Clean, UTF-8-preserving text with normalized whitespace.
    """

    if text is None:
        return ""

    if not isinstance(text, str):
        text = str(text)

    # Remove BOM markers that can appear at the start of documents
    cleaned = text.replace("\ufeff", "").replace("\ufffe", "")

    # Normalize newlines and collapse repeated spaces/tabs while keeping paragraph breaks
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


def sanitize_text(text: str | None) -> str:
    """Backward-compatible alias for :func:`normalize_text`."""

    return normalize_text(text)


def chunk_text(
    text: str,
    chunk_size: int = 1500,
    chunk_overlap: int = 200,
) -> list[str]:
    """Split text into overlapping chunks for better vector search.

    Creates chunks of approximately chunk_size characters with overlap
    between consecutive chunks. Attempts to break at sentence boundaries
    for more coherent chunks.

    Args:
        text: Text to chunk.
        chunk_size: Target size of each chunk in characters.
        chunk_overlap: Overlap between consecutive chunks.

    Returns:
        List of text chunks.
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        # Try to break at sentence boundary
        if end < len(text):
            for punct in [". ", ".\n", "? ", "! "]:
                last_punct = text.rfind(punct, start, end)
                if last_punct > start + chunk_size // 2:
                    end = last_punct + 1
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - chunk_overlap
    return chunks
