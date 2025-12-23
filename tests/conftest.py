"""
Pytest configuration and shared fixtures.
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests (no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (require API keys)")
    config.addinivalue_line("markers", "slow: Slow tests (network, large data)")


@pytest.fixture(scope="session")
def api_key():
    """Get Google API key from environment."""
    key = os.environ.get("GOOGLE_API_KEY")
    if not key:
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("GOOGLE_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip("\"'")
                    break

    if not key:
        pytest.skip("GOOGLE_API_KEY not set")

    return key


@pytest.fixture(scope="session")
def qdrant_url():
    """Get Qdrant URL from environment."""
    url = os.environ.get("QDRANT_URL")
    if not url:
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("QDRANT_URL="):
                    url = line.split("=", 1)[1].strip().strip("\"'")
                    break

    if not url:
        pytest.skip("QDRANT_URL not set")

    return url


@pytest.fixture(scope="session")
def qdrant_api_key():
    """Get Qdrant API key from environment."""
    key = os.environ.get("QDRANT_API_KEY")
    if not key:
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("QDRANT_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip("\"'")
                    break

    if not key:
        pytest.skip("QDRANT_API_KEY not set")

    return key


@pytest.fixture(scope="session")
def settings():
    """Get application settings."""
    from src.config import Settings

    return Settings()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test data."""
    dir_path = Path(tempfile.mkdtemp(prefix="f1agent_test_"))
    yield dir_path
    if dir_path.exists():
        shutil.rmtree(dir_path)


@pytest.fixture
def sample_document():
    """Sample FIA document for testing."""
    return {
        "title": "Test Stewards Decision",
        "content": "The stewards investigated an incident involving Car 1 and Car 44. "
        "Car 1 was found to have exceeded track limits at Turn 4, resulting "
        "in a 5-second time penalty added to the race time.",
        "metadata": {
            "race": "Abu Dhabi Grand Prix",
            "season": 2025,
            "doc_type": "stewards_decision",
        },
    }


@pytest.fixture
def mock_embedding():
    """A mock 768-dimensional embedding vector."""
    return [0.01 * i for i in range(768)]
