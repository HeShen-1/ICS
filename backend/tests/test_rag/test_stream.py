"""Tests for app.rag.stream - generate_chat_stream error paths and fallback.

Mocks Retriever.search, Retriever.auto_route, and LLMClient.chat_stream to
verify SSE event generation for edge cases.
"""
import sys
from unittest.mock import MagicMock

# Stub sentence_transformers to prevent SSL import chain failure on Windows.
sys.modules["sentence_transformers"] = MagicMock()

import json
import asyncio
import pytest
from unittest.mock import patch
from openai import APITimeoutError, RateLimitError

from app.rag.stream import generate_chat_stream, _sse_event


async def _dummy_agen(items):
    """Simple async generator helper."""
    for item in items:
        yield item


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_test_settings(monkeypatch):
    """Install a minimal Settings mock in all modules that import get_settings."""
    import importlib
    import app.config
    from app.config import Settings

    ts = Settings(
        mysql_host="localhost",
        mysql_user="test",
        mysql_password="test",
        mysql_database="test",
        deepseek_api_key="test-key",
        jwt_secret_key="test-secret-key-not-change-me",
        jwt_algorithm="HS256",
        jwt_expire_minutes=1440,
        upload_dir="/tmp/test_uploads",
        max_question_length=500,
        daily_question_limit=100,
        max_context_tokens=8000,
        max_history_rounds=5,
        top_k=5,
        similarity_threshold=0.65,
        llm_timeout=30,
        llm_temperature=0.3,
        llm_max_tokens=2048,
    )

    for mod_name in ("app.config", "app.rag.stream", "app.rag.prompt", "app.rag.llm"):
        mod = importlib.import_module(mod_name)
        monkeypatch.setattr(mod, "get_settings", lambda: ts)
    return ts


async def _collect_events(generator):
    """Drain an SSE generator into a list of (event_type, data_dict) tuples."""
    events = []
    async for raw in generator:
        raw = raw.strip()
        if not raw:
            continue
        lines = raw.split("\n")
        event_type = None
        data_str = None
        for line in lines:
            if line.startswith("event: "):
                event_type = line[len("event: "):]
            elif line.startswith("data: "):
                data_str = line[len("data: "):]
        if event_type and data_str is not None:
            events.append((event_type, json.loads(data_str)))
    return events


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEmptyRetrievalFallback:
    def test_empty_retrieval_yields_fallback(self, monkeypatch):
        """三层降级全空时触发兜底话术."""
        _make_test_settings(monkeypatch)

        mock_retriever = MagicMock()
        mock_retriever.auto_route.return_value = "kb1"
        mock_retriever.search.return_value = []  # layer 1 & 2 empty
        # layer 3: vector_store.search also returns empty
        mock_retriever.vector_store.search.return_value = []

        mock_llm = MagicMock()

        with (
            patch("app.rag.stream.get_retriever", return_value=mock_retriever),
            patch("app.rag.stream.get_llm", return_value=mock_llm),
        ):
            events = asyncio.run(
                _collect_events(
                    generate_chat_stream("test", session_id=1, intent_classify=False, intent_tag="test")
                )
            )

        token_text = "".join(d["text"] for t, d in events if t == "token")
        assert len(token_text) > 0, "Should emit fallback token text"
        done = [d for t, d in events if t == "done"]
        assert len(done) == 1
        assert done[0]["empty_retrieval"] is True

    def test_layer2_unfiltered_search_when_route_fails(self, monkeypatch):
        """auto_route 返回 None 时触发第二层无过滤全局检索."""
        _make_test_settings(monkeypatch)

        mock_retriever = MagicMock()
        mock_retriever.auto_route.return_value = None
        # Layer 2 (unfiltered search) returns chunks → should NOT hit fallback
        mock_retriever.search.return_value = [
            {"source": "test.md", "text": "content", "score": 0.72, "kb_id": "1"}
        ]

        mock_llm = MagicMock()
        mock_llm.chat_stream.return_value = _dummy_agen(["ok"])

        with (
            patch("app.rag.stream.get_retriever", return_value=mock_retriever),
            patch("app.rag.stream.get_llm", return_value=mock_llm),
        ):
            events = asyncio.run(
                _collect_events(
                    generate_chat_stream("test", session_id=1, intent_classify=False, intent_tag="test")
                )
            )

        # Layer 2 unfiltered search should have been called
        mock_retriever.search.assert_called()
        done = [d for t, d in events if t == "done"]
        assert len(done) == 1
        assert done[0].get("empty_retrieval") is not True


class TestStreamErrors:
    def test_apitimeout_yields_timeout_error(self, monkeypatch):
        """When chat_stream raises APITimeoutError, error event has LLM_TIMEOUT."""
        _make_test_settings(monkeypatch)

        mock_retriever = MagicMock()
        mock_retriever.auto_route.return_value = "kb1"
        mock_retriever.search.return_value = [
            {"source": "test.md", "text": "some content", "score": 0.95}
        ]

        async def _failing_stream(self, messages):
            raise APITimeoutError("Request timed out")
            yield  # type: AsyncGenerator — unreachable

        with (
            patch("app.rag.stream.get_retriever", return_value=mock_retriever),
            patch("app.rag.llm.LLMClient.chat_stream", _failing_stream),
        ):
            events = asyncio.run(
                _collect_events(
                    generate_chat_stream("test", session_id=1, intent_classify=False, intent_tag="test")
                )
            )

        errors = [d for t, d in events if t == "error"]
        assert len(errors) == 1
        assert errors[0]["code"] == "LLM_TIMEOUT"
        assert errors[0]["message"] == "AI 服务响应超时，请稍后重试"

    def test_ratelimit_yields_rate_limit_error(self, monkeypatch):
        """When chat_stream raises RateLimitError, error event has LLM_RATE_LIMITED."""
        _make_test_settings(monkeypatch)

        mock_retriever = MagicMock()
        mock_retriever.auto_route.return_value = "kb1"
        mock_retriever.search.return_value = [
            {"source": "test.md", "text": "content", "score": 0.95}
        ]

        async def _failing_stream(self, messages):
            # RateLimitError requires response= and body= keyword-only args
            raise RateLimitError(
                "Rate limit exceeded",
                response=MagicMock(),
                body={"error": {"message": "Rate limit exceeded"}},
            )
            yield

        with (
            patch("app.rag.stream.get_retriever", return_value=mock_retriever),
            patch("app.rag.llm.LLMClient.chat_stream", _failing_stream),
        ):
            events = asyncio.run(
                _collect_events(
                    generate_chat_stream("test", session_id=1, intent_classify=False, intent_tag="test")
                )
            )

        errors = [d for t, d in events if t == "error"]
        assert len(errors) == 1
        assert errors[0]["code"] == "LLM_RATE_LIMITED"
        assert errors[0]["message"] == "AI 服务繁忙，请稍后重试"

    def test_generic_exception_yields_internal_error(self, monkeypatch):
        """When chat_stream raises a generic ValueError, error event has INTERNAL_ERROR."""
        _make_test_settings(monkeypatch)

        mock_retriever = MagicMock()
        mock_retriever.auto_route.return_value = "kb1"
        mock_retriever.search.return_value = [
            {"source": "test.md", "text": "content", "score": 0.95}
        ]

        async def _failing_stream(self, messages):
            raise ValueError("Unexpected internal failure")
            yield

        with (
            patch("app.rag.stream.get_retriever", return_value=mock_retriever),
            patch("app.rag.llm.LLMClient.chat_stream", _failing_stream),
        ):
            events = asyncio.run(
                _collect_events(
                    generate_chat_stream("test", session_id=1, intent_classify=False, intent_tag="test")
                )
            )

        errors = [d for t, d in events if t == "error"]
        assert len(errors) == 1
        assert errors[0]["code"] == "INTERNAL_ERROR"
        assert errors[0]["message"] == "系统内部错误，请联系管理员"
