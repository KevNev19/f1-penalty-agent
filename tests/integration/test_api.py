"""Integration tests for FastAPI endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_agent():
    """Mock the F1Agent for testing."""
    mock = MagicMock()
    mock_response = MagicMock()
    mock_response.answer = "Test penalty answer"
    mock_response.sources_used = [
        {
            "source": "FIA Regulations",
            "doc_type": "regulation",
            "score": 0.85,
            "excerpt": "Track limits...",
        }
    ]
    mock_response.model_used = "gemini-2.0-flash"
    mock.ask.return_value = mock_response
    return mock


@pytest.fixture
def mock_vector_store():
    """Mock the VectorStore for testing."""
    mock = MagicMock()
    mock.get_collection_stats.return_value = {"count": 100}
    mock.REGULATIONS_COLLECTION = "regulations"
    return mock


@pytest.fixture
def client(mock_agent, mock_vector_store):
    """Create test client with mocked dependencies."""
    with (
        patch("src.api.routers.chat.get_agent") as mock_get_agent,
        patch("src.api.routers.health.get_vector_store") as mock_get_vs,
    ):
        mock_get_agent.return_value = mock_agent
        mock_get_vs.return_value = mock_vector_store

        from src.api.main import app

        yield TestClient(app)


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.mark.integration
    def test_health_check(self, client):
        """Test basic health check returns 200."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    @pytest.mark.integration
    def test_readiness_check(self, client):
        """Test readiness probe returns vector store status."""
        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "vector_store" in data


class TestChatEndpoints:
    """Tests for chat/ask endpoints."""

    @pytest.mark.integration
    def test_ask_question_success(self, client):
        """Test successful question answering."""
        response = client.post("/api/v1/ask", json={"question": "Why did Max get a penalty?"})

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["answer"] == "Test penalty answer"
        assert "sources" in data
        assert len(data["sources"]) == 1

    @pytest.mark.integration
    def test_ask_question_empty_fails(self, client):
        """Test empty question is rejected."""
        response = client.post("/api/v1/ask", json={"question": ""})

        assert response.status_code == 422  # Validation error

    @pytest.mark.integration
    def test_ask_question_too_long_fails(self, client):
        """Test too-long question is rejected."""
        long_question = "x" * 1001
        response = client.post("/api/v1/ask", json={"question": long_question})

        assert response.status_code == 422  # Validation error


class TestAPIDocumentation:
    """Tests for API documentation endpoints."""

    @pytest.mark.integration
    def test_openapi_docs(self, client):
        """Test OpenAPI docs endpoint."""
        response = client.get("/docs")
        assert response.status_code == 200

    @pytest.mark.integration
    def test_redoc_docs(self, client):
        """Test ReDoc endpoint."""
        response = client.get("/redoc")
        assert response.status_code == 200

    @pytest.mark.integration
    def test_openapi_schema(self, client):
        """Test OpenAPI schema is valid."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "F1 Penalty Agent API"
        assert "/api/v1/ask" in schema["paths"]
