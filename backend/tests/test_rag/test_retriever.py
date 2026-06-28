"""Tests for app.rag.retriever - Retriever.search and auto_route.

Mocks Embedder and VectorStore to test filtering, routing, and validation logic.
"""
import sys
from unittest.mock import MagicMock

# Stub sentence_transformers to prevent SSL import chain failure on Windows.
sys.modules["sentence_transformers"] = MagicMock()

import pytest
from unittest.mock import patch

from app.rag.retriever import Retriever


@pytest.fixture
def mock_embedder():
    """Return a MagicMock embedder that returns a fixed embedding vector."""
    embedder = MagicMock()
    embedder.embed_query.return_value = [0.1] * 1024
    return embedder


@pytest.fixture
def mock_vector_store():
    """Return a MagicMock vector_store with a configurable search method."""
    vs = MagicMock()
    vs.search.return_value = []
    return vs


@pytest.fixture
def retriever(mock_embedder, mock_vector_store, monkeypatch):
    """Create a Retriever with mocked Embedder and VectorStore."""
    with (
        patch("app.rag.retriever.Embedder", return_value=mock_embedder),
        patch("app.rag.retriever.VectorStore", return_value=mock_vector_store),
    ):
        r = Retriever()
        # Override settings so top_k/threshold don't interfere
        monkeypatch.setattr(r, "settings", MagicMock(top_k=5, similarity_threshold=0.65))
        return r


class TestSearch:
    def test_search_with_kb_id_passes_correct_filter(self, retriever, mock_vector_store):
        """search with kb_id='123' should pass filter_expr='kb_id == "123"'."""
        retriever.search("test query", kb_id="123")

        mock_vector_store.search.assert_called_once()
        call_kwargs = mock_vector_store.search.call_args.kwargs
        assert call_kwargs["filter_expr"] == 'kb_id == "123"'

    def test_search_without_kb_id_uses_none_filter(self, retriever, mock_vector_store):
        """search without kb_id should pass filter_expr=None."""
        retriever.search("test query")

        mock_vector_store.search.assert_called_once()
        call_kwargs = mock_vector_store.search.call_args.kwargs
        assert call_kwargs["filter_expr"] is None

    def test_search_with_invalid_kb_id_raises_value_error(self, retriever):
        """search with non-digit kb_id should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid kb_id"):
            retriever.search("test query", kb_id="abc")


class TestAutoRoute:
    def test_auto_route_returns_best_kb_by_max_score(self, retriever, mock_vector_store):
        """auto_route returns KB with highest-scoring chunk (per-KB max)."""
        mock_vector_store.search.return_value = [
            {"kb_id": "kb1", "text": "a", "score": 0.9},  # best single score
            {"kb_id": "kb2", "text": "b", "score": 0.8},
            {"kb_id": "kb2", "text": "c", "score": 0.7},
            {"kb_id": "kb2", "text": "d", "score": 0.6},
        ]
        result = retriever.auto_route("query")
        assert result == "kb1"  # kb1 has max single-chunk score

    def test_auto_route_empty_results_returns_none(self, retriever, mock_vector_store):
        """Empty search results -> None."""
        mock_vector_store.search.return_value = []
        result = retriever.auto_route("query")
        assert result is None

    def test_auto_route_no_kb_id_in_chunks_returns_none(self, retriever, mock_vector_store):
        """All chunks have empty or no kb_id -> None."""
        mock_vector_store.search.return_value = [
            {"text": "a", "score": 0.9},
            {"text": "b", "score": 0.8},
            {"kb_id": "", "text": "c", "score": 0.7},
        ]
        result = retriever.auto_route("query")
        assert result is None

    def test_auto_route_with_mixed_ids_returns_highest_score_kb(self, retriever, mock_vector_store):
        """With kb_id values and varying scores, return KB with highest-score chunk."""
        mock_vector_store.search.return_value = [
            {"kb_id": "1", "text": "a", "score": 0.9},  # highest score → "1"
            {"kb_id": "2", "text": "b", "score": 0.8},
            {"kb_id": "1", "text": "c", "score": 0.7},
        ]
        result = retriever.auto_route("query")
        assert result == "1"  # kb 1 has the single highest-scoring chunk
