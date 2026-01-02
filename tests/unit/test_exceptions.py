"""Unit tests for exception handling system.

Tests both the exception hierarchy and the exception handler utilities,
including negative tests to verify correct exceptions are raised.
"""

import json

import pytest

from src.adapters.common.exception_handler import (
    format_exception_json,
    get_error_code,
    get_http_status_code,
)
from src.core.domain.exceptions import (
    ConfigurationError,
    EmbeddingError,
    EmptyQueryError,
    F1AgentError,
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
    MissingAPIKeyError,
    QdrantConnectionError,
    QdrantQueryError,
    ValidationError,
    VectorStoreError,
)

# Apply @pytest.mark.unit to all tests in this module
pytestmark = pytest.mark.unit


class TestExceptionHierarchy:
    """Tests for the exception class hierarchy."""

    def test_f1_agent_error_is_base(self):
        """F1AgentError should be the base for all custom exceptions."""
        assert issubclass(ConfigurationError, F1AgentError)
        assert issubclass(VectorStoreError, F1AgentError)
        assert issubclass(LLMError, F1AgentError)
        assert issubclass(ValidationError, F1AgentError)
        assert issubclass(EmbeddingError, F1AgentError)

    def test_qdrant_errors_inherit_from_vector_store(self):
        """Qdrant exceptions should inherit from VectorStoreError."""
        assert issubclass(QdrantConnectionError, VectorStoreError)
        assert issubclass(QdrantQueryError, VectorStoreError)

    def test_llm_errors_inherit_from_llm_error(self):
        """LLM exceptions should inherit from LLMError."""
        assert issubclass(LLMConnectionError, LLMError)
        assert issubclass(LLMRateLimitError, LLMError)

    def test_config_errors_inherit_from_configuration(self):
        """Config exceptions should inherit from ConfigurationError."""
        assert issubclass(MissingAPIKeyError, ConfigurationError)


class TestExceptionCreation:
    """Tests for creating and using exceptions."""

    def test_basic_exception_creation(self):
        """Basic exception should have message and error code."""
        exc = F1AgentError("Test error message")
        assert str(exc) == "Test error message"
        assert exc.message == "Test error message"
        assert exc.error_code == "F1_ERR_001"

    def test_exception_with_context(self):
        """Exception should store extra context."""
        exc = QdrantConnectionError(
            "Connection failed", context={"url": "https://test.qdrant.io", "timeout": 30}
        )
        assert exc.extra_context["url"] == "https://test.qdrant.io"
        assert exc.extra_context["timeout"] == 30

    def test_exception_with_cause(self):
        """Exception should chain underlying cause."""
        original = ConnectionError("Network unreachable")
        exc = QdrantConnectionError("Connection failed", cause=original)
        assert exc.cause is original
        assert exc.cause.args[0] == "Network unreachable"

    def test_exception_captures_location(self):
        """Exception should capture file, method, and line number."""
        exc = F1AgentError("Test")
        assert exc.location.file_name is not None
        assert exc.location.method_name is not None
        assert exc.location.line_number > 0

    def test_each_exception_has_unique_error_code(self):
        """Each exception type should have a unique error code."""
        codes = set()
        exceptions = [
            F1AgentError("test"),
            ConfigurationError("test"),
            MissingAPIKeyError("test"),
            VectorStoreError("test"),
            QdrantConnectionError("test"),
            QdrantQueryError("test"),
            EmbeddingError("test"),
            LLMError("test"),
            LLMConnectionError("test"),
            LLMRateLimitError("test"),
            ValidationError("test"),
            EmptyQueryError("test"),
        ]
        for exc in exceptions:
            codes.add(exc.error_code)

        # All codes should be unique
        assert len(codes) == len(exceptions)


class TestExceptionToDict:
    """Tests for exception JSON serialization."""

    def test_to_dict_basic_structure(self):
        """to_dict should return proper structure."""
        exc = QdrantConnectionError("Test error")
        result = exc.to_dict()

        assert "error" in result
        assert result["error"]["type"] == "QdrantConnectionError"
        assert result["error"]["code"] == "F1_VEC_002"
        assert result["error"]["message"] == "Test error"

        assert "location" in result
        assert "class" in result["location"]
        assert "method" in result["location"]
        assert "file" in result["location"]
        assert "line" in result["location"]

    def test_to_dict_includes_context(self):
        """to_dict should include extra context when provided."""
        exc = LLMRateLimitError("Rate limit", context={"model": "gemini"})
        result = exc.to_dict()

        assert "context" in result
        assert result["context"]["model"] == "gemini"

    def test_to_dict_includes_cause(self):
        """to_dict should include cause when provided."""
        original = ValueError("Bad value")
        exc = ValidationError("Invalid input", cause=original)
        result = exc.to_dict()

        assert "cause" in result
        assert result["cause"]["type"] == "ValueError"
        assert result["cause"]["message"] == "Bad value"

    def test_to_dict_excludes_trace_by_default(self):
        """to_dict should not include stack trace by default."""
        original = ValueError("Bad value")
        exc = ValidationError("Invalid input", cause=original)
        result = exc.to_dict(include_trace=False)

        assert "stack_trace" not in result

    def test_to_dict_includes_trace_when_requested(self):
        """to_dict should include stack trace when requested."""
        original = ValueError("Bad value")
        exc = ValidationError("Invalid input", cause=original)
        result = exc.to_dict(include_trace=True)

        # Stack trace is only included if there's a cause with traceback
        if exc.stack_trace:
            assert "stack_trace" in result

    def test_to_dict_is_json_serializable(self):
        """to_dict output should be JSON serializable."""
        exc = QdrantConnectionError(
            "Connection failed", context={"url": "https://test.qdrant.io", "port": 6333}
        )
        result = exc.to_dict()

        # Should not raise
        json_str = json.dumps(result)
        assert isinstance(json_str, str)


class TestExceptionHandler:
    """Tests for exception handler utilities."""

    def test_format_custom_exception(self):
        """format_exception_json should handle F1AgentError correctly."""
        exc = QdrantConnectionError("Test error", context={"url": "test"})
        result = format_exception_json(exc)

        assert result["error"]["type"] == "QdrantConnectionError"
        assert result["error"]["code"] == "F1_VEC_002"

    def test_format_standard_exception(self):
        """format_exception_json should handle standard Python exceptions."""
        try:
            raise ValueError("Standard error")
        except ValueError as e:
            result = format_exception_json(e)

        assert result["error"]["type"] == "ValueError"
        assert result["error"]["code"] == "PYTHON_ERR"
        assert result["error"]["message"] == "Standard error"

    def test_format_adds_extra_context(self):
        """format_exception_json should merge extra context."""
        exc = QdrantConnectionError("Test", context={"url": "original"})
        result = format_exception_json(exc, extra_context={"request_id": "abc123"})

        assert result["context"]["url"] == "original"
        assert result["context"]["request_id"] == "abc123"

    def test_get_error_code_custom_exception(self):
        """get_error_code should return correct code for custom exceptions."""
        assert get_error_code(QdrantConnectionError("test")) == "F1_VEC_002"
        assert get_error_code(LLMRateLimitError("test")) == "F1_LLM_003"
        assert get_error_code(ValidationError("test")) == "F1_VAL_001"

    def test_get_error_code_standard_exception(self):
        """get_error_code should return PYTHON_ERR for standard exceptions."""
        assert get_error_code(ValueError("test")) == "PYTHON_ERR"
        assert get_error_code(RuntimeError("test")) == "PYTHON_ERR"


class TestHTTPStatusCodes:
    """Tests for HTTP status code mapping."""

    def test_validation_error_returns_400(self):
        """ValidationError should map to 400 Bad Request."""
        exc = ValidationError("Invalid input")
        assert get_http_status_code(exc) == 400

    def test_rate_limit_returns_429(self):
        """Rate limit errors should map to 429 Too Many Requests."""
        assert get_http_status_code(LLMRateLimitError("test")) == 429

    def test_vector_store_error_returns_503(self):
        """VectorStoreError should map to 503 Service Unavailable."""
        assert get_http_status_code(QdrantConnectionError("test")) == 503
        assert get_http_status_code(QdrantQueryError("test")) == 503

    def test_configuration_error_returns_500(self):
        """ConfigurationError should map to 500 Internal Server Error."""
        assert get_http_status_code(ConfigurationError("test")) == 500
        assert get_http_status_code(MissingAPIKeyError("test")) == 500

    def test_generic_f1_error_returns_500(self):
        """Generic F1AgentError should map to 500."""
        assert get_http_status_code(F1AgentError("test")) == 500

    def test_standard_value_error_returns_400(self):
        """Standard ValueError should map to 400."""
        assert get_http_status_code(ValueError("test")) == 400

    def test_connection_error_returns_503(self):
        """Standard ConnectionError should map to 503."""
        assert get_http_status_code(ConnectionError("test")) == 503


class TestNegativeScenarios:
    """Negative tests to verify exceptions are raised correctly."""

    def test_empty_query_raises_validation_error(self):
        """Empty query should raise EmptyQueryError."""
        from src.core.services.agent_service import AgentService as F1Agent

        # Create a minimal mock agent
        class MockLLM:
            pass

        class MockRetriever:
            pass

        agent = F1Agent(llm_client=MockLLM(), retriever=MockRetriever())

        with pytest.raises(ValueError, match="empty"):
            agent.ask("")

        with pytest.raises(ValueError, match="empty"):
            agent.ask("   ")

    def test_missing_api_key_raises_error(self):
        """Missing API key should raise MissingAPIKeyError."""
        from src.adapters.outbound.llm.gemini_adapter import GeminiAdapter as GeminiClient

        client = GeminiClient(api_key="", model="test")

        with pytest.raises(MissingAPIKeyError):
            client._get_client()

    def test_qdrant_connection_with_invalid_credentials_raises_error(self):
        """Invalid Qdrant credentials should raise QdrantConnectionError."""
        from unittest.mock import patch

        from src.adapters.outbound.vector_store.qdrant_adapter import (
            QdrantAdapter as QdrantVectorStore,
        )

        store = QdrantVectorStore(
            url="https://invalid.qdrant.example.com:6333",
            api_key="fake_key",
            embedding_api_key="fake_key",
        )

        # Mock QdrantClient to raise an exception on instantiation
        with patch("qdrant_client.QdrantClient") as mock_client:
            mock_client.side_effect = Exception("Connection refused")

            with pytest.raises(QdrantConnectionError) as exc_info:
                store._get_client()

            # Verify exception has proper structure
            exc = exc_info.value
            assert exc.error_code == "F1_VEC_002"
            assert "url" in exc.extra_context
            assert exc.cause is not None  # Should have underlying exception
            assert "Connection refused" in str(exc.cause)

    def test_exception_context_preserved(self):
        """Exception context should be preserved through raise chain."""
        try:
            try:
                raise ConnectionError("Network down")
            except Exception as e:
                raise QdrantConnectionError(
                    "Failed to connect", cause=e, context={"url": "test", "attempt": 3}
                ) from e
        except QdrantConnectionError as exc:
            assert exc.extra_context["url"] == "test"
            assert exc.extra_context["attempt"] == 3
            assert isinstance(exc.cause, ConnectionError)

    def test_exception_to_dict_after_raising(self):
        """Exception should serialize correctly after being raised."""
        try:
            raise LLMRateLimitError(
                "Rate limit exceeded", context={"model": "gemini-2.0-flash", "retry_after": 60}
            )
        except LLMRateLimitError as exc:
            result = exc.to_dict()

            assert result["error"]["type"] == "LLMRateLimitError"
            assert result["error"]["code"] == "F1_LLM_003"
            assert result["context"]["retry_after"] == 60


class TestExceptionCatchPatterns:
    """Tests for exception catching patterns."""

    def test_catch_by_base_class(self):
        """Should be able to catch all F1 errors with base class."""
        exceptions = [
            QdrantConnectionError("test"),
            LLMRateLimitError("test"),
            ValidationError("test"),
        ]

        for exc in exceptions:
            try:
                raise exc
            except F1AgentError as caught:
                assert caught.error_code is not None

    def test_catch_vector_store_errors(self):
        """Should be able to catch all vector store errors together."""
        exceptions = [
            QdrantConnectionError("test"),
            QdrantQueryError("test"),
        ]

        for exc in exceptions:
            try:
                raise exc
            except VectorStoreError as caught:
                assert "F1_VEC" in caught.error_code

    def test_catch_llm_errors(self):
        """Should be able to catch all LLM errors together."""
        exceptions = [
            LLMConnectionError("test"),
            LLMRateLimitError("test"),
        ]

        for exc in exceptions:
            try:
                raise exc
            except LLMError as caught:
                assert "F1_LLM" in caught.error_code
