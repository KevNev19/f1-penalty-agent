"""Configuration management for F1 Penalty Agent."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _sanitize_secret(value: str) -> str:
    """Remove BOM characters and whitespace from secrets.

    Cloud Run secrets or environment variables may contain BOM characters
    that cause encoding errors when used in HTTP headers.
    """
    if not value:
        return value
    # Remove BOM (U+FEFF) and strip whitespace
    return value.lstrip("\ufeff").strip()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core settings
    google_api_key: str = ""
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    # LLM settings
    llm_model: str = "gemini-2.0-flash"

    # RAG settings
    chunk_size: int = 1000
    chunk_overlap: int = 400
    top_k_results: int = 5

    # Logging
    log_level: str = "INFO"

    @property
    def regulations_dir(self) -> Path:
        """Directory for FIA regulation PDFs."""
        return self.data_dir / "regulations"

    @property
    def stewards_dir(self) -> Path:
        """Directory for stewards decision PDFs."""
        return self.data_dir / "stewards"

    def get_config_hash(self) -> str:
        """Generate a hash of the current ingestion configuration."""
        import hashlib

        config_str = f"{self.chunk_size}-{self.chunk_overlap}-{self.llm_model}"
        return hashlib.md5(config_str.encode()).hexdigest()[:8]

    # Data directories
    data_dir: Path = Path("./data")
    cache_dir: Path = Path("./data/cache")

    def ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.regulations_dir.mkdir(parents=True, exist_ok=True)
        self.stewards_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
