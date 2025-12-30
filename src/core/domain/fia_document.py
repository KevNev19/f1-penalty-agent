"""FIA document model for regulations and stewards decisions."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class FIADocument:
    """Represents a scraped FIA document.

    Used for both regulations and stewards decisions scraped from
    the FIA website.

    Attributes:
        title: Document title.
        url: URL where the document was found.
        doc_type: Type of document ("regulation", "stewards_decision", "guidelines").
        event_name: For stewards decisions, the race/event name.
        season: F1 season year.
        local_path: Path to downloaded PDF file.
        text_content: Extracted text from the PDF.
    """

    title: str
    url: str
    doc_type: str  # "regulation", "stewards_decision", "guidelines"
    event_name: str | None = None  # For stewards decisions
    season: int = 2025
    local_path: Path | None = None
    text_content: str | None = None
