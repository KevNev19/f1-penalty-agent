"""
Comprehensive test suite for F1 Penalty Agent.
Run with: pytest tests/ -v
"""
import pytest
from pathlib import Path
import os


# ============================================================================
# Configuration Tests
# ============================================================================

class TestConfiguration:
    """Tests for application configuration."""
    
    @pytest.mark.unit
    def test_settings_loads(self):
        """Settings should load from environment/defaults."""
        from src.config import Settings
        settings = Settings()
        assert settings is not None
        assert hasattr(settings, 'data_dir')
        assert hasattr(settings, 'llm_model')
    
    @pytest.mark.unit
    def test_settings_data_dir_is_path(self):
        """data_dir should be a Path object."""
        from src.config import Settings
        settings = Settings()
        assert isinstance(settings.data_dir, Path)
    
    @pytest.mark.unit
    def test_google_api_key_configured(self, api_key):
        """Google API key should be available."""
        assert api_key is not None
        assert len(api_key) > 10


# ============================================================================
# Data Model Tests
# ============================================================================

class TestDataModels:
    """Tests for data models/dataclasses."""
    
    @pytest.mark.unit
    def test_fia_document_creation(self):
        """FIADocument should be creatable with required fields."""
        from src.data.fia_scraper import FIADocument
        doc = FIADocument(
            title="Test Decision",
            url="https://example.com/doc.pdf",
            doc_type="stewards_decision",
            event_name="Abu Dhabi Grand Prix",
            season=2025,
        )
        assert doc.title == "Test Decision"
        assert doc.season == 2025
    
    @pytest.mark.unit
    def test_document_model(self):
        """Document model for vector store."""
        from src.rag.vectorstore import Document
        doc = Document(
            content="Test content",
            metadata={"source": "test"},
            doc_id="doc_1"
        )
        assert doc.content == "Test content"
        assert doc.doc_id == "doc_1"
    
    @pytest.mark.unit
    def test_search_result_model(self):
        """SearchResult model."""
        from src.rag.vectorstore import Document, SearchResult
        doc = Document(content="Test", metadata={})
        result = SearchResult(document=doc, score=0.95)
        assert result.score == 0.95


# ============================================================================
# Embedding Tests
# ============================================================================

class TestGeminiEmbeddings:
    """Tests for Gemini embedding function."""
    
    @pytest.mark.integration
    def test_embedding_function_name(self, api_key):
        """name() should return a string."""
        from src.rag.vectorstore import GeminiEmbeddingFunction
        ef = GeminiEmbeddingFunction(api_key)
        assert isinstance(ef.name(), str)
    
    @pytest.mark.integration
    def test_embedding_single_document(self, api_key):
        """__call__ should embed a single document."""
        from src.rag.vectorstore import GeminiEmbeddingFunction
        ef = GeminiEmbeddingFunction(api_key)
        result = ef(["Test document"])
        assert len(result) == 1
        assert len(result[0]) == 768
    
    @pytest.mark.integration
    def test_embedding_batch(self, api_key):
        """__call__ should handle batch of documents."""
        from src.rag.vectorstore import GeminiEmbeddingFunction
        ef = GeminiEmbeddingFunction(api_key)
        result = ef(["Doc 1", "Doc 2", "Doc 3"])
        assert len(result) == 3
        assert all(len(emb) == 768 for emb in result)
    
    @pytest.mark.integration
    def test_embed_query(self, api_key):
        """embed_query should return single embedding."""
        from src.rag.vectorstore import GeminiEmbeddingFunction
        ef = GeminiEmbeddingFunction(api_key)
        result = ef.embed_query(input="test query")
        assert len(result) == 768


# ============================================================================
# VectorStore Tests (K8s ChromaDB)
# ============================================================================

class TestVectorStore:
    """Tests for VectorStore with K8s ChromaDB."""
    
    @pytest.mark.integration
    def test_vectorstore_http_client(self, api_key):
        """VectorStore should connect via HttpClient."""
        from src.rag.vectorstore import VectorStore
        vs = VectorStore(
            Path("data/test"),
            api_key,
            chroma_host="localhost",
            chroma_port=8000
        )
        assert vs.chroma_host == "localhost"
    
    @pytest.mark.integration
    def test_vectorstore_add_document(self, api_key):
        """VectorStore should add documents."""
        from src.rag.vectorstore import VectorStore, Document
        vs = VectorStore(
            Path("data/test"),
            api_key,
            chroma_host="localhost",
            chroma_port=8000
        )
        doc = Document(
            content="Test penalty document for integration test",
            metadata={"test": True},
            doc_id="integration_test_1"
        )
        count = vs.add_documents([doc], "integration_test")
        assert count == 1
    
    @pytest.mark.integration
    def test_vectorstore_search(self, api_key):
        """VectorStore should search and return results."""
        from src.rag.vectorstore import VectorStore, Document
        vs = VectorStore(
            Path("data/test"),
            api_key,
            chroma_host="localhost",
            chroma_port=8000
        )
        # Add document
        doc = Document(
            content="Max Verstappen 5-second penalty for track limits violation",
            metadata={"race": "Abu Dhabi"},
            doc_id="search_test_1"
        )
        vs.add_documents([doc], "search_test")
        
        # Search
        results = vs.search("track limits penalty", "search_test", top_k=1)
        assert len(results) >= 1
        assert results[0].score > 0


# ============================================================================
# Agent Tests
# ============================================================================

class TestF1Agent:
    """Tests for the F1 agent."""
    
    @pytest.mark.unit
    def test_query_type_enum(self):
        """QueryType enum should exist."""
        from src.agent.f1_agent import QueryType
        assert hasattr(QueryType, 'PENALTY')
        assert hasattr(QueryType, 'RULE')
        assert hasattr(QueryType, 'GENERAL')
    
    @pytest.mark.unit
    def test_prompts_exist(self):
        """Prompt templates should be defined."""
        from src.agent.prompts import SYSTEM_PROMPT, PENALTY_EXPLANATION_PROMPT
        assert len(SYSTEM_PROMPT) > 100
        assert PENALTY_EXPLANATION_PROMPT is not None
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_gemini_client_generate(self, api_key):
        """GeminiClient should generate responses."""
        from src.llm.gemini_client import GeminiClient
        client = GeminiClient(api_key, "gemini-2.0-flash")
        response = client.generate(
            prompt="What is 2+2? Reply with just the number.",
            system_prompt="You are a helpful assistant."
        )
        assert "4" in response
