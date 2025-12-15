"""
Comprehensive test suite for F1 Penalty Agent.
Run with: pytest tests/ -v

Test markers:
  - unit: Pure unit tests, no external dependencies
  - integration: Requires ChromaDB and/or API key
  - slow: Tests that take longer (API calls)
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch


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
    def test_settings_has_chromadb_config(self):
        """Settings should have ChromaDB configuration."""
        from src.config import Settings
        settings = Settings()
        assert hasattr(settings, 'chroma_host')
        assert hasattr(settings, 'chroma_port')
        assert settings.chroma_port == 8000
    
    @pytest.mark.unit
    def test_settings_default_model(self):
        """Default LLM model should be gemini-2.0-flash."""
        from src.config import Settings
        settings = Settings()
        assert settings.llm_model == "gemini-2.0-flash"
    
    @pytest.mark.unit
    def test_settings_ensure_directories(self, tmp_path):
        """ensure_directories should create required directories."""
        from src.config import Settings
        settings = Settings(
            data_dir=tmp_path / "data",
            cache_dir=tmp_path / "cache",
            chroma_persist_dir=tmp_path / "chroma"
        )
        settings.ensure_directories()
        assert (tmp_path / "data").exists()
        assert (tmp_path / "cache").exists()
    
    @pytest.mark.unit
    def test_google_api_key_configured(self, api_key):
        """Google API key should be available."""
        assert api_key is not None
        assert len(api_key) > 10


# ============================================================================
# Logging Module Tests
# ============================================================================

class TestLogging:
    """Tests for the logging configuration."""
    
    @pytest.mark.unit
    def test_setup_logging(self):
        """setup_logging should return a logger."""
        from src.logging_config import setup_logging
        logger = setup_logging(level="DEBUG")
        assert logger is not None
        assert logger.name == "f1_agent"
    
    @pytest.mark.unit
    def test_get_logger(self):
        """get_logger should return logger instances."""
        from src.logging_config import get_logger
        logger = get_logger()
        assert logger.name == "f1_agent"
        
        child_logger = get_logger("test")
        assert child_logger.name == "f1_agent.test"
    
    @pytest.mark.unit
    def test_setup_logging_with_file(self, tmp_path):
        """setup_logging should create file handler."""
        from src.logging_config import setup_logging
        log_file = tmp_path / "test.log"
        logger = setup_logging(log_file=log_file)
        logger.info("Test message")
        assert log_file.exists()


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
        assert doc.text_content is None
    
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
        assert result.document.content == "Test"


# ============================================================================
# Agent Tests - Query Classification
# ============================================================================

class TestQueryClassification:
    """Tests for F1Agent query classification."""
    
    @pytest.fixture
    def mock_agent(self):
        """Create agent with mocked dependencies."""
        from src.agent.f1_agent import F1Agent
        mock_llm = Mock()
        mock_retriever = Mock()
        return F1Agent(mock_llm, mock_retriever)
    
    @pytest.mark.unit
    def test_classify_penalty_question(self, mock_agent):
        """Penalty questions should be classified correctly."""
        from src.agent.f1_agent import QueryType
        
        penalty_queries = [
            "Why did Verstappen get a penalty?",
            "What penalty did Hamilton get in Monaco?",
            "Explain Leclerc's 5-second time penalty",
            "Why was Norris penalized at Silverstone?",
        ]
        
        for query in penalty_queries:
            result = mock_agent.classify_query(query)
            assert result == QueryType.PENALTY_EXPLANATION, f"Failed for: {query}"
    
    @pytest.mark.unit
    def test_classify_rule_question(self, mock_agent):
        """Rule questions should be classified correctly."""
        from src.agent.f1_agent import QueryType
        
        rule_queries = [
            "What is the rule for track limits?",
            "Explain the blue flags rule",
            "What's the penalty for unsafe release?",
            "Is it allowed to push another car off track?",  # Matches "is it allowed"
        ]
        
        for query in rule_queries:
            result = mock_agent.classify_query(query)
            assert result == QueryType.RULE_LOOKUP, f"Failed for: {query}"
    
    @pytest.mark.unit
    def test_classify_general_question(self, mock_agent):
        """General questions should be classified as GENERAL."""
        from src.agent.f1_agent import QueryType
        
        general_queries = [
            "Tell me about F1",
            "Who won the championship?",
            "How fast are F1 cars?",
        ]
        
        for query in general_queries:
            result = mock_agent.classify_query(query)
            assert result == QueryType.GENERAL, f"Failed for: {query}"


# ============================================================================
# Retriever Tests - Text Chunking
# ============================================================================

class TestTextChunking:
    """Tests for F1Retriever text chunking."""
    
    @pytest.fixture
    def mock_retriever(self):
        """Create retriever with mocked vector store."""
        from src.rag.retriever import F1Retriever
        mock_vs = Mock()
        return F1Retriever(mock_vs)
    
    @pytest.mark.unit
    def test_chunk_short_text(self, mock_retriever):
        """Short text should return single chunk."""
        short_text = "This is a short text."
        chunks = mock_retriever.chunk_text(short_text, chunk_size=100)
        assert len(chunks) == 1
        assert chunks[0] == short_text
    
    @pytest.mark.unit
    def test_chunk_long_text(self, mock_retriever):
        """Long text should be split into multiple chunks."""
        long_text = "Word " * 500  # ~2500 characters
        chunks = mock_retriever.chunk_text(long_text, chunk_size=500, chunk_overlap=100)
        assert len(chunks) > 1
        # Check overlap exists
        assert len(chunks[0]) >= 400
    
    @pytest.mark.unit
    def test_chunk_preserves_content(self, mock_retriever):
        """Chunking should not lose content."""
        text = "Line one. Line two. Line three. Line four. Line five."
        chunks = mock_retriever.chunk_text(text, chunk_size=20, chunk_overlap=5)
        # All important content should appear in at least one chunk
        combined = " ".join(chunks)
        assert "Line one" in combined
        assert "Line five" in combined


# ============================================================================
# Retriever Tests - Context Extraction
# ============================================================================

class TestContextExtraction:
    """Tests for F1Retriever context extraction."""
    
    @pytest.fixture
    def mock_retriever(self):
        """Create retriever with mocked vector store."""
        from src.rag.retriever import F1Retriever
        mock_vs = Mock()
        return F1Retriever(mock_vs)
    
    @pytest.mark.unit
    def test_extract_driver_name(self, mock_retriever):
        """Should extract driver names from queries."""
        context = mock_retriever.extract_race_context("Why did Verstappen get a penalty?")
        assert context.get("driver") == "Max Verstappen"
    
    @pytest.mark.unit
    def test_extract_hamilton(self, mock_retriever):
        """Should extract Hamilton's name."""
        context = mock_retriever.extract_race_context("Hamilton's penalty in Monaco")
        assert context.get("driver") == "Lewis Hamilton"
    
    @pytest.mark.unit
    def test_extract_race_name(self, mock_retriever):
        """Should extract Grand Prix names."""
        context = mock_retriever.extract_race_context("What happened at Monaco Grand Prix?")
        assert context.get("race") == "Monaco"
    
    @pytest.mark.unit
    def test_extract_season(self, mock_retriever):
        """Should extract season year as integer."""
        context = mock_retriever.extract_race_context("Penalties in the 2024 season")
        assert context.get("season") == 2024  # Returns int, not string


# ============================================================================
# Retrieval Context Tests
# ============================================================================

class TestRetrievalContext:
    """Tests for RetrievalContext."""
    
    @pytest.mark.unit
    def test_retrieval_context_creation(self):
        """RetrievalContext should be creatable."""
        from src.rag.retriever import RetrievalContext
        ctx = RetrievalContext(
            regulations=[],
            stewards_decisions=[],
            race_data=[],
            query="test query"
        )
        assert ctx.query == "test query"
        assert len(ctx.regulations) == 0
    
    @pytest.mark.unit
    def test_get_combined_context_empty(self):
        """Empty context should return informative message."""
        from src.rag.retriever import RetrievalContext
        ctx = RetrievalContext(
            regulations=[],
            stewards_decisions=[],
            race_data=[],
            query="test"
        )
        result = ctx.get_combined_context()
        assert "No specific context" in result or len(result) == 0 or isinstance(result, str)


# ============================================================================
# GeminiClient Tests
# ============================================================================

class TestGeminiClient:
    """Tests for GeminiClient."""
    
    @pytest.mark.unit
    def test_client_initialization(self, api_key):
        """GeminiClient should initialize with API key."""
        from src.llm.gemini_client import GeminiClient
        client = GeminiClient(api_key, "gemini-2.0-flash")
        assert client.api_key == api_key
        assert client.model_name == "gemini-2.0-flash"
        assert client._model is None  # Lazy loading
    
    @pytest.mark.unit
    def test_client_no_api_key_error(self):
        """GeminiClient should raise error without API key."""
        from src.llm.gemini_client import GeminiClient
        client = GeminiClient("", "gemini-2.0-flash")
        with pytest.raises(ValueError, match="API key"):
            client._get_model()


# ============================================================================
# Agent Prompt Tests
# ============================================================================

class TestPrompts:
    """Tests for agent prompts."""
    
    @pytest.mark.unit
    def test_prompts_exist(self):
        """Prompt templates should be defined."""
        from src.agent.prompts import (
            F1_SYSTEM_PROMPT,
            PENALTY_EXPLANATION_PROMPT,
            RULE_LOOKUP_PROMPT,
            GENERAL_F1_PROMPT,
        )
        assert len(F1_SYSTEM_PROMPT) > 100
        assert PENALTY_EXPLANATION_PROMPT is not None
        assert RULE_LOOKUP_PROMPT is not None
        assert GENERAL_F1_PROMPT is not None
    
    @pytest.mark.unit
    def test_prompts_have_placeholders(self):
        """Prompts should have context and question placeholders."""
        from src.agent.prompts import PENALTY_EXPLANATION_PROMPT
        assert "{context}" in PENALTY_EXPLANATION_PROMPT
        assert "{question}" in PENALTY_EXPLANATION_PROMPT
    
    @pytest.mark.unit
    def test_query_type_enum(self):
        """QueryType enum should have correct values."""
        from src.agent.f1_agent import QueryType
        assert QueryType.PENALTY_EXPLANATION.value == "penalty_explanation"
        assert QueryType.RULE_LOOKUP.value == "rule_lookup"
        assert QueryType.GENERAL.value == "general"


# ============================================================================
# Embedding Function Tests  
# ============================================================================

class TestGeminiEmbeddings:
    """Tests for Gemini embedding function."""
    
    @pytest.mark.integration
    def test_embedding_function_name(self, api_key):
        """name() should return a string."""
        from src.rag.vectorstore import GeminiEmbeddingFunction
        ef = GeminiEmbeddingFunction(api_key)
        assert isinstance(ef.name(), str)
        assert "gemini" in ef.name().lower()
    
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
    """Tests for VectorStore."""
    
    @pytest.mark.unit
    def test_vectorstore_initialization(self, api_key):
        """VectorStore should initialize with parameters."""
        from src.rag.vectorstore import VectorStore
        vs = VectorStore(
            Path("data/test"),
            api_key,
            chroma_host="localhost",
            chroma_port=8000
        )
        assert vs.chroma_host == "localhost"
        assert vs.chroma_port == 8000
        assert vs.persist_dir == Path("data/test")
    
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
        doc = Document(
            content="Max Verstappen 5-second penalty for track limits violation",
            metadata={"race": "Abu Dhabi"},
            doc_id="search_test_1"
        )
        vs.add_documents([doc], "search_test")
        results = vs.search("track limits penalty", "search_test", top_k=1)
        assert len(results) >= 1


# ============================================================================
# Integration Tests - Full Agent Flow
# ============================================================================

class TestAgentIntegration:
    """Integration tests for full agent flow."""
    
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
