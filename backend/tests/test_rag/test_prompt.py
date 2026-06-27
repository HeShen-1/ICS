"""Tests for app.rag.prompt - format_retrieved_chunks, build_messages."""
import pytest
from unittest.mock import patch
from app.rag.prompt import (
    format_retrieved_chunks,
    build_messages,
    _is_critical,
    _estimate_tokens,
    _dedup_chunks_by_source,
    SYSTEM_PROMPT,
    LAYERED_THRESHOLD,
)

# Reusable chunk builders


def _make_chunk(text, source="doc1.md", score=0.9):
    return {"text": text, "source": source, "score": score}


class TestFormatRetrievedChunks:
    def test_format_retrieved_chunks_basic(self):
        chunks = [_make_chunk("普通内容 A"), _make_chunk("普通内容 B")]
        result = format_retrieved_chunks(chunks)
        assert "普通内容 A" in result
        assert "普通内容 B" in result
        assert "来源 1:" in result
        assert "来源 2:" in result

    def test_format_retrieved_chunks_empty(self):
        result = format_retrieved_chunks([])
        assert "无相关知识库内容" in result

    def test_format_retrieved_chunks_critical_keyword_detection(self):
        chunks = [
            _make_chunk("普通内容"),
            _make_chunk("用户必须遵守规则"),
        ]
        result = format_retrieved_chunks(chunks)
        assert "关键规则" in result

    def test_format_retrieved_chunks_layered_output(self):
        """When more than LAYERED_THRESHOLD chunks, output should be layered."""
        chunks = [
            _make_chunk(f"内容 {i}") for i in range(LAYERED_THRESHOLD + 2)
        ]
        # Make some critical
        chunks[0] = _make_chunk("用户必须遵守此规则")
        chunks[1] = _make_chunk("严禁违规操作")
        result = format_retrieved_chunks(chunks)
        assert "关键规则（请严格遵守）" in result
        assert "详细参考" in result

    def test_format_retrieved_chunks_truncation(self):
        long_text = "X" * 1000
        chunks = [_make_chunk(long_text)]
        result = format_retrieved_chunks(chunks, max_chunk_chars=200)
        # Should contain truncated text with "..."
        assert "..." in result
        assert len(result) < 1000  # much shorter than original

    def test_format_retrieved_chunks_score_displayed(self):
        chunks = [_make_chunk("内容", score=0.85)]
        result = format_retrieved_chunks(chunks)
        assert "0.85" in result


class TestBuildMessages:
    def _patch_prompt_settings(self, monkeypatch):
        from app.config import Settings
        test_settings = Settings(
            mysql_host="localhost",
            mysql_user="test",
            mysql_password="test",
            mysql_database="test",
            deepseek_api_key="test-key",
            jwt_secret_key="jwt-ci-dev-key-32chars-abcdefghX",
            jwt_algorithm="HS256",
            jwt_expire_minutes=1440,
            upload_dir="/tmp/test_uploads",
            max_question_length=500,
            daily_question_limit=100,
            max_context_tokens=8000,
            max_history_rounds=5,
            top_k=5,
            similarity_threshold=0.65,
        )
        import app.rag.prompt as prompt_mod
        monkeypatch.setattr(prompt_mod, "get_settings", lambda: test_settings)
        return test_settings

    def test_build_messages_basic(self, monkeypatch):
        """build_messages creates system + user messages."""
        self._patch_prompt_settings(monkeypatch)

        chunks = [_make_chunk("知识片段 1"), _make_chunk("知识片段 2")]
        messages = build_messages("测试问题", chunks)
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "测试问题"
        assert "知识片段" in messages[0]["content"]

    def test_build_messages_with_history(self, monkeypatch):
        self._patch_prompt_settings(monkeypatch)

        history = [
            {"role": "user", "content": "之前的问题"},
            {"role": "assistant", "content": "之前的回答"},
        ]
        chunks = [_make_chunk("知识内容")]
        messages = build_messages("新问题", chunks, history_messages=history)
        # Should include history between system and last user message
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "之前的问题"
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "新问题"

    def test_build_messages_token_budget_critical_first(self, monkeypatch):
        """Critical chunks should be prioritized when token budget is tight."""
        self._patch_prompt_settings(monkeypatch)

        # Many large normal chunks + one critical chunk
        chunks = [_make_chunk("X" * 500, f"src{i}") for i in range(10)]
        chunks.append(_make_chunk("用户必须遵守此规则", "critical_src"))
        messages = build_messages("测试", chunks)
        # Critical chunk should be in the system prompt content
        assert "必须" in messages[0]["content"]


class TestIsCritical:
    def test_is_critical_positive(self):
        assert _is_critical("用户必须遵守规则") is True

    def test_is_critical_negative(self):
        assert _is_critical("这是普通内容描述") is False

    def test_is_critical_important_keyword(self):
        assert _is_critical("注意事项：安全第一") is True


class TestEstimateTokens:
    def test_estimate_chinese(self):
        tokens = _estimate_tokens("你好世界")
        assert tokens > 0
        # Function returns int, so 4 chars * 1.3 = 5.2 -> int 5
        assert 4 <= tokens <= 6

    def test_estimate_english(self):
        tokens = _estimate_tokens("hello world")
        assert 0 < tokens < 20


class TestDedupChunksBySource:
    def test_dedup_keeps_highest_score(self):
        chunks = [
            {"source": "doc1", "text": "A", "score": 0.8},
            {"source": "doc1", "text": "B", "score": 0.9},
            {"source": "doc2", "text": "C", "score": 0.7},
        ]
        result = _dedup_chunks_by_source(chunks)
        sources = [c["source"] for c in result]
        assert sources.count("doc1") == 1
        doc1 = [c for c in result if c["source"] == "doc1"][0]
        assert doc1["score"] == 0.9
        assert doc1["text"] == "B"

    def test_dedup_empty(self):
        assert _dedup_chunks_by_source([]) == []
