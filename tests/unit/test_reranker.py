"""Unit tests for CrossEncoderReranker.

Uses module-level mocking to avoid Windows PyTorch DLL loading issues.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock sentence_transformers before importing reranker
mock_cross_encoder_class = MagicMock()
mock_st_module = MagicMock()
mock_st_module.CrossEncoder = mock_cross_encoder_class

from src.rag.qdrant_store import Document, SearchResult  # noqa: E402


class TestCrossEncoderReranker:
    """Tests for CrossEncoderReranker class."""

    @pytest.fixture
    def sample_results(self):
        """Create sample search results for testing."""
        return [
            SearchResult(
                document=Document(
                    content="Track limits regulation article 33.3",
                    metadata={"source": "regulations"},
                    doc_id="doc_1",
                ),
                score=0.7,
            ),
            SearchResult(
                document=Document(
                    content="Penalty decision for exceeding track limits",
                    metadata={"source": "stewards"},
                    doc_id="doc_2",
                ),
                score=0.65,
            ),
            SearchResult(
                document=Document(
                    content="Safety car procedure article 55",
                    metadata={"source": "regulations"},
                    doc_id="doc_3",
                ),
                score=0.6,
            ),
        ]

    @pytest.fixture
    def reranker_with_mock(self):
        """Create a reranker with mocked CrossEncoder."""
        with patch.dict(sys.modules, {"sentence_transformers": mock_st_module}):
            # Reset mocks
            mock_cross_encoder_class.reset_mock()
            mock_model = MagicMock()
            mock_cross_encoder_class.return_value = mock_model
            
            # Import with mocked module
            from importlib import reload

            import src.rag.reranker as reranker_module
            reload(reranker_module)
            
            reranker = reranker_module.CrossEncoderReranker()
            return reranker, mock_model

    @pytest.mark.unit
    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Skipped on Windows due to PyTorch DLL loading issues in test env"
    )
    def test_rerank_orders_by_cross_encoder_scores(
        self, reranker_with_mock, sample_results
    ):
        """Test that rerank reorders results based on cross-encoder scores."""
        reranker, mock_model = reranker_with_mock
        
        # Cross-encoder gives doc_2 higher score than doc_1
        mock_model.predict.return_value = [0.3, 0.9, 0.1]
        
        results = reranker.rerank("track limits", sample_results, top_k=3)
        
        # doc_2 should now be first (highest cross-encoder score)
        assert results[0].document.doc_id == "doc_2"
        assert results[0].score == 0.9
        
        # doc_1 should be second
        assert results[1].document.doc_id == "doc_1"
        assert results[1].score == 0.3

    @pytest.mark.unit
    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="Skipped on Windows due to PyTorch DLL loading issues in test env"
    )
    def test_rerank_respects_top_k(self, reranker_with_mock, sample_results):
        """Test that rerank returns at most top_k results."""
        reranker, mock_model = reranker_with_mock
        mock_model.predict.return_value = [0.5, 0.6, 0.7]
        
        results = reranker.rerank("query", sample_results, top_k=2)
        
        assert len(results) == 2

    @pytest.mark.unit
    def test_rerank_empty_results(self, reranker_with_mock):
        """Test that rerank handles empty results."""
        reranker, _ = reranker_with_mock
        results = reranker.rerank("query", [], top_k=5)
        assert results == []

    @pytest.mark.unit
    def test_rerank_single_result(self, reranker_with_mock):
        """Test that rerank handles single result without calling model."""
        reranker, mock_model = reranker_with_mock
        
        single_result = [
            SearchResult(
                document=Document(content="Test", metadata={}, doc_id="doc_1"),
                score=0.8,
            )
        ]
        
        results = reranker.rerank("query", single_result, top_k=5)
        
        assert len(results) == 1
        assert results[0].document.doc_id == "doc_1"
        # Model should not be called for single result
        mock_model.predict.assert_not_called()

    @pytest.mark.unit
    def test_model_lazy_loading(self):
        """Test that model is loaded lazily on first use."""
        with patch.dict(sys.modules, {"sentence_transformers": mock_st_module}):
            mock_cross_encoder_class.reset_mock()
            
            from importlib import reload

            import src.rag.reranker as reranker_module
            reload(reranker_module)
            
            reranker = reranker_module.CrossEncoderReranker()
            
            # Model should not be loaded yet (internal _model is None)
            assert reranker._model is None

    @pytest.mark.unit
    def test_default_model_name(self):
        """Test that default model is MS MARCO MiniLM."""
        with patch.dict(sys.modules, {"sentence_transformers": mock_st_module}):
            from importlib import reload

            import src.rag.reranker as reranker_module
            reload(reranker_module)
            
            assert reranker_module.CrossEncoderReranker.MODEL_NAME == "cross-encoder/ms-marco-MiniLM-L-6-v2"

    @pytest.mark.unit
    def test_custom_model_name(self):
        """Test using custom model name."""
        with patch.dict(sys.modules, {"sentence_transformers": mock_st_module}):
            from importlib import reload

            import src.rag.reranker as reranker_module
            reload(reranker_module)
            
            reranker = reranker_module.CrossEncoderReranker(model_name="custom/model")
            assert reranker.model_name == "custom/model"

    @pytest.mark.unit
    def test_is_available_with_mocked_model(self, reranker_with_mock):
        """Test is_available returns True when model is successfully mocked."""
        reranker, mock_model = reranker_with_mock
        # Force the model to be set
        reranker._model = mock_model
        assert reranker.is_available() is True
