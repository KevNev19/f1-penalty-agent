import pytest

from src.core.domain.utils import chunk_text


class TestChunkText:
    """Unit tests for the shared chunk_text helper."""

    @pytest.mark.unit
    def test_short_text_returns_single_chunk(self):
        """Texts shorter than chunk_size should not be split."""
        text = "Short text"
        assert chunk_text(text, chunk_size=50, chunk_overlap=10) == [text]

    @pytest.mark.unit
    def test_empty_text_returns_empty_list(self):
        """Empty input should return an empty list."""
        assert chunk_text("", chunk_size=50, chunk_overlap=10) == []

    @pytest.mark.unit
    def test_overlap_equal_or_exceeds_chunk_size_raises(self):
        """Invalid overlap that prevents progress should raise an error."""
        with pytest.raises(ValueError):
            chunk_text("content", chunk_size=100, chunk_overlap=100)

        with pytest.raises(ValueError):
            chunk_text("content", chunk_size=50, chunk_overlap=75)

    @pytest.mark.unit
    def test_negative_or_zero_chunk_size_raises(self):
        """chunk_size must be positive."""
        with pytest.raises(ValueError):
            chunk_text("content", chunk_size=0, chunk_overlap=10)

        with pytest.raises(ValueError):
            chunk_text("content", chunk_size=-10, chunk_overlap=1)

    @pytest.mark.unit
    def test_negative_overlap_raises(self):
        """chunk_overlap cannot be negative."""
        with pytest.raises(ValueError):
            chunk_text("content", chunk_size=10, chunk_overlap=-1)
