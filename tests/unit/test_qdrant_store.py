"""Unit tests for QdrantVectorStore.

These tests mock the Qdrant client at the module level to avoid
actual API calls and initialization checks.
"""

from unittest.mock import MagicMock, patch

import pytest

# Import dataclasses from qdrant_store
from src.core.domain import Document, SearchResult


class TestDocument:
    """Tests for Document dataclass."""

    @pytest.mark.unit
    def test_document_creation(self):
        """Test creating a Document."""
        doc = Document(
            content="Test content",
            metadata={"key": "value"},
            doc_id="test_id",
        )
        assert doc.content == "Test content"
        assert doc.metadata == {"key": "value"}
        assert doc.doc_id == "test_id"

    @pytest.mark.unit
    def test_document_optional_id(self):
        """Test Document with optional id."""
        doc = Document(content="Test", metadata={})
        assert doc.doc_id is None


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    @pytest.mark.unit
    def test_search_result_creation(self):
        """Test creating a SearchResult."""
        doc = Document(content="Test", metadata={})
        result = SearchResult(document=doc, score=0.9)
        assert result.document == doc
        assert result.score == 0.9


class TestGeminiEmbeddingFunction:
    """Tests for GeminiEmbeddingFunction - mock HTTP calls."""

    @pytest.mark.unit
    def test_embed_query_returns_vector(self):
        """Test that embed_query returns a list of floats."""
        from src.adapters.outbound.vector_store.qdrant_adapter import GeminiEmbeddingFunction

        # Mock google.genai.Client
        with patch("google.genai.Client") as MockClient:
            mock_client_instance = MockClient.return_value
            mock_response = MagicMock()

            # Create mock embedding with .values
            mock_embedding = MagicMock()
            mock_embedding.values = [0.1] * 3072

            mock_response.embeddings = [mock_embedding]
            mock_client_instance.models.embed_content.return_value = mock_response

            ef = GeminiEmbeddingFunction("fake-api-key")
            result = ef.embed_query("test query")

            assert len(result) == 3072
            assert all(isinstance(x, float) for x in result)

    @pytest.mark.unit
    def test_embed_documents_returns_vectors(self):
        """Test that embed_documents returns list of vectors."""
        from src.adapters.outbound.vector_store.qdrant_adapter import GeminiEmbeddingFunction

        # Mock google.genai.Client
        with patch("google.genai.Client") as MockClient:
            mock_client_instance = MockClient.return_value
            mock_response = MagicMock()

            # Create mock embeddings with .values
            emb1 = MagicMock()
            emb1.values = [0.1] * 768  # Use 768 to match the assertion in the test
            emb2 = MagicMock()
            emb2.values = [0.2] * 768

            mock_response.embeddings = [emb1, emb2]
            mock_client_instance.models.embed_content.return_value = mock_response

            ef = GeminiEmbeddingFunction("fake-api-key")
            # We mock the response to match the test's expectation of 768 dimensions
            # Alternatively we could update the test to expect 3072, but let's stick to the existing assertion for now
            # Actually, let's update expectations to 3072 to match reality

            # Re-creating mocks with 3072
            emb1.values = [0.1] * 3072
            emb2.values = [0.2] * 3072

            result = ef.embed_documents(["doc1", "doc2"])

            assert len(result) == 2
            assert len(result[0]) == 3072


class TestQdrantVectorStore:
    """Tests for QdrantVectorStore - mock Qdrant client."""

    @pytest.fixture
    def mock_qdrant_client(self):
        """Create a mock Qdrant client."""
        mock_client = MagicMock()
        # Mock get_collections to return empty list (collections will be created)
        mock_client.get_collections.return_value.collections = []
        return mock_client

    @pytest.fixture
    def store_with_mocked_client(self, mock_qdrant_client):
        """Create a store with pre-injected mock client."""
        from src.adapters.outbound.vector_store.qdrant_adapter import (
            QdrantAdapter as QdrantVectorStore,
        )

        # Create store without calling _get_client
        store = object.__new__(QdrantVectorStore)
        store.url = "https://test.cloud.qdrant.io"
        store.api_key = "test-key"
        store._client = mock_qdrant_client  # Pre-inject the mock
        store._embedding_function = MagicMock()
        store._embedding_function.embed_query.return_value = [0.1] * 3072
        store._embedding_function.embed_documents.return_value = [[0.1] * 3072]

        return store

    @pytest.mark.unit
    def test_add_documents_empty(self, store_with_mocked_client):
        """Test adding empty document list returns 0."""
        result = store_with_mocked_client.add_documents([])
        assert result == 0

    @pytest.mark.unit
    def test_add_documents(self, store_with_mocked_client, mock_qdrant_client):
        """Test adding documents calls upsert."""
        docs = [
            Document(
                content="Test regulation content",
                metadata={"source": "test"},
                doc_id="doc_1",
            )
        ]

        result = store_with_mocked_client.add_documents(docs, "regulations")

        assert result == 1
        mock_qdrant_client.upsert.assert_called_once()

    @pytest.mark.unit
    def test_search(self, store_with_mocked_client, mock_qdrant_client):
        """Test searching documents returns SearchResults."""
        # Setup mock response for query_points (qdrant-client 1.16+ API)
        mock_hit = MagicMock()
        mock_hit.id = 12345
        mock_hit.score = 0.85
        mock_hit.payload = {"content": "Test content", "doc_id": "doc_1", "source": "test"}

        mock_response = MagicMock()
        mock_response.points = [mock_hit]
        mock_qdrant_client.query_points.return_value = mock_response

        results = store_with_mocked_client.search("test query", "regulations")

        assert len(results) == 1
        assert results[0].score == 0.85
        assert results[0].document.doc_id == "doc_1"

    @pytest.mark.unit
    def test_search_filters_low_scores(self, store_with_mocked_client, mock_qdrant_client):
        """Test that results below 0.5 score are filtered out."""
        mock_hit = MagicMock()
        mock_hit.id = 12345
        mock_hit.score = 0.3  # Below threshold
        mock_hit.payload = {"content": "Test content", "doc_id": "doc_1"}

        mock_response = MagicMock()
        mock_response.points = [mock_hit]
        mock_qdrant_client.query_points.return_value = mock_response

        results = store_with_mocked_client.search("test query", "regulations")

        assert len(results) == 0

    @pytest.mark.unit
    def test_get_collection_stats(self, store_with_mocked_client, mock_qdrant_client):
        """Test getting collection statistics."""
        mock_info = MagicMock()
        mock_info.points_count = 100
        mock_info.status = "green"  # Add status
        mock_qdrant_client.get_collection.return_value = mock_info

        stats = store_with_mocked_client.get_collection_stats("regulations")

        assert stats["count"] == 100
        assert stats["status"] == "green"

    @pytest.mark.unit
    def test_reset_deletes_all_collections(self, store_with_mocked_client, mock_qdrant_client):
        """Test reset deletes all collections."""
        # Mock get_collections for _ensure_collections
        mock_qdrant_client.get_collections.return_value.collections = []

        store_with_mocked_client.reset()

        # Should delete 3 collections
        assert mock_qdrant_client.delete_collection.call_count == 3

    @pytest.mark.unit
    def test_clear_collection(self, store_with_mocked_client, mock_qdrant_client):
        """Test clearing a single collection."""
        store_with_mocked_client.clear_collection("regulations")

        mock_qdrant_client.delete_collection.assert_called_once_with(collection_name="regulations")
