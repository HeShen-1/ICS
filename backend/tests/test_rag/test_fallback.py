"""Tests for app.rag.fallback - get_fallback_response, get_fallback_sources."""
from app.rag.fallback import get_fallback_response, get_fallback_sources, DEFAULT_FALLBACK_RESPONSE


class TestFallback:
    def test_fallback_response_not_empty(self):
        response = get_fallback_response()
        assert isinstance(response, str)
        assert len(response) > 0
        assert "抱歉" in response

    def test_fallback_sources_empty_list(self):
        sources = get_fallback_sources()
        assert sources == []
        assert isinstance(sources, list)
