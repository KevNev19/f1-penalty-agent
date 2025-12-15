"""Configuration management for F1 Penalty Agent."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Google AI API
    google_api_key: str = ""

    # Data directories
    data_dir: Path = Path("./data")
    cache_dir: Path = Path("./data/cache")

    # ChromaDB settings
    chroma_persist_dir: Path = Path("./data/chroma")
    chroma_host: str | None = None  # Set to "localhost" for K8s mode
    chroma_port: int = 8000

    # Model settings
    embedding_model: str = "all-MiniLM-L6-v2"
    llm_model: str = "gemini-2.0-flash"  # Free tier compatible

    # RAG settings
    chunk_size: int = 1000
    chunk_overlap: int = 200
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

    def ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.regulations_dir.mkdir(parents=True, exist_ok=True)
        self.stewards_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_persist_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
