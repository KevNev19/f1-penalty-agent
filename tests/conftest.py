"""
Pytest configuration and shared fixtures.
"""
import os
import pytest
from pathlib import Path
import tempfile
import shutil


# ============================================================================
# Test Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests (no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (require API keys)")
    config.addinivalue_line("markers", "slow: Slow tests (network, large data)")


# ============================================================================
# Fixtures - Configuration
# ============================================================================

@pytest.fixture(scope="session")
def api_key():
    """Get Google API key from environment."""
    key = os.environ.get("GOOGLE_API_KEY")
    if not key:
        # Try loading from .env
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("GOOGLE_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"\'')
                    break
    
    if not key:
        pytest.skip("GOOGLE_API_KEY not set")
    
    return key


@pytest.fixture(scope="session")
def settings():
    """Get application settings."""
    from src.config import Settings
    return Settings()


# ============================================================================
# Fixtures - Temporary Directories
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test data."""
    dir_path = Path(tempfile.mkdtemp(prefix="f1agent_test_"))
    yield dir_path
    # Cleanup after test
    if dir_path.exists():
        shutil.rmtree(dir_path)


@pytest.fixture
def test_data_dir():
    """Get the test data directory (persistent fixtures)."""
    dir_path = Path(__file__).parent / "fixtures"
    dir_path.mkdir(exist_ok=True)
    return dir_path


# ============================================================================
# Fixtures - Sample Data
# ============================================================================

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
        }
    }


@pytest.fixture
def sample_documents(sample_document):
    """Multiple sample documents for testing."""
    return [
        sample_document,
        {
            "title": "Track Limits Regulation",
            "content": "Drivers must use the track at all times. For the avoidance of "
                       "doubt, the white lines defining the track edges are considered "
                       "to be part of the track but the kerbs are not.",
            "metadata": {
                "doc_type": "regulation",
                "source": "FIA Sporting Regulations",
            }
        },
        {
            "title": "Unsafe Release Penalty",
            "content": "Team XYZ was fined €5,000 for an unsafe release of Car 7 "
                       "during the pit stop. The car was released into the path of "
                       "another competitor.",
            "metadata": {
                "race": "Monaco Grand Prix",
                "season": 2025,
                "doc_type": "stewards_decision",
            }
        }
    ]


# ============================================================================
# Fixtures - Mocks
# ============================================================================

@pytest.fixture
def mock_embedding():
    """A mock 768-dimensional embedding vector."""
    return [0.01 * i for i in range(768)]


@pytest.fixture
def mock_embeddings():
    """Multiple mock embeddings for batch testing."""
    return [
        [0.01 * (i + j) for i in range(768)]
        for j in range(3)
    ]
