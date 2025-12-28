"""Common utilities for the F1 Penalty Agent.

Text handling contract
----------------------
The application should treat text consistently at the boundaries:

* Incoming documents and user inputs should have BOM markers stripped so
  downstream processing does not see spurious characters.
* Normalization should be explicit. Callers can opt into Unicode
  normalization for deterministic indexing/serialization, or request
  ASCII-only output when interacting with systems that require it.
* Internal layers should assume text is already clean and avoid repeated
  sanitization; a final clean pass is allowed at the outermost API
  response boundary for defense-in-depth.
"""

import unicodedata


def clean_text(text: str, *, normalize: bool = True, ascii_only: bool = False) -> str:
    """Remove BOM markers and optionally normalize/ASCII-fold text.

    Args:
        text: Input text that may contain BOM or special characters.
        normalize: Whether to apply NFKC normalization for consistent
            downstream processing. Enabled by default.
        ascii_only: Whether to discard non-ASCII characters (useful for
            transport or logging contexts that cannot handle Unicode).

    Returns:
        Cleaned text with BOMs removed and optional normalization applied.
    """
    if not text:
        return ""

    cleaned = text.replace("\ufeff", "").replace("\ufffd", "")
    if normalize:
        cleaned = unicodedata.normalize("NFKC", cleaned)
    if ascii_only:
        cleaned = cleaned.encode("ascii", errors="ignore").decode("ascii")
    return cleaned


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
