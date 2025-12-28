"""Common utilities for the F1 Penalty Agent.

This module contains shared helper functions used across CLI, API, and other components.
"""


def sanitize_text(text: str) -> str:
    """Remove BOM and non-ASCII characters for API-safe text.

    This function removes Unicode BOM markers and replacement characters,
    then encodes to ASCII to ensure compatibility with all consumers.

    Args:
        text: Input text that may contain BOM or special characters.

    Returns:
        Clean ASCII-safe text.
    """
    if not text:
        return ""
    text = text.replace("\ufeff", "").replace("\ufffd", "")
    return text.encode("ascii", errors="ignore").decode("ascii")


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
        chunk_size: Target size of each chunk in characters (must be positive).
        chunk_overlap: Overlap between consecutive chunks (must be less than chunk_size).

    Returns:
        List of text chunks.

    Raises:
        ValueError: If chunk_overlap >= chunk_size or parameters are invalid.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be non-negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be less than chunk_size to avoid infinite loop")

    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        # Try to break at sentence boundary
        if end < len(text):
            for punct in [". ", ".\n", "? ", "?\n", "! ", "!\n"]:
                last_punct = text.rfind(punct, start, end)
                if last_punct > start + chunk_size // 2:
                    end = last_punct + 1
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - chunk_overlap
    return chunks
