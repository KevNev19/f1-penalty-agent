"""Data ingestion exceptions for F1 Penalty Agent."""

from .base import F1AgentError


class DataIngestionError(F1AgentError):
    """Error during data scraping/loading."""

    error_code = "F1_DAT_001"


class ScrapingError(DataIngestionError):
    """Failed to scrape data from source."""

    error_code = "F1_DAT_002"


class PDFExtractionError(DataIngestionError):
    """Failed to extract text from PDF."""

    error_code = "F1_DAT_003"


class DataValidationError(DataIngestionError):
    """Ingested data failed validation."""

    error_code = "F1_DAT_004"
