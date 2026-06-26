"""Tests for app.agent.decomposer - TaskDecomposer.

Covers: valid JSON, invalid JSON, missing fields, LLM exception, _load_docs.
"""
import sys
from unittest.mock import MagicMock

# Stub sentence_transformers to prevent SSL import chain failure on Windows.
# The import chain via app.rag.llm -> app/rag/__init__.py -> app.rag.embedder
# pulls in sentence_transformers, which on some Windows environments fails with
# an SSL certificate store error during aiohttp init.
sys.modules["sentence_transformers"] = MagicMock()

import json
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, patch

from app.agent.decomposer import TaskDecomposer


VALID_RESPONSE = {
    "services": ["auth-service", "chat-service"],
    "tasks": [
        {"title": "Implement login", "description": "Add login page"},
        {"title": "Implement logout", "description": "Add logout button"},
    ],
    "parallel_groups": [["Implement login", "Implement logout"]],
    "explanation": "These tasks are independent of each other",
}


@pytest.fixture
def mock_llm_client():
    """Create a mock LLMClient whose async chat() method is an AsyncMock."""
    client = MagicMock()
    # decompose() calls self.llm.chat(), which must be awaitable
    client.chat = AsyncMock()
    client.model = "test-model"
    client.timeout = 30
    return client


@pytest.fixture
def decomposer(mock_llm_client):
    """Return a TaskDecomposer wired with the mock LLMClient."""
    return TaskDecomposer(llm_client=mock_llm_client)


def _make_response(content: str):
    """Create a mock ChatCompletion response object."""
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.mark.asyncio
async def test_valid_json(decomposer, mock_llm_client):
    """Mock LLM returns valid JSON -> returns structured dict."""
    mock_llm_client.chat.return_value = _make_response(json.dumps(VALID_RESPONSE))

    result = await decomposer.decompose("test requirement")

    assert result == VALID_RESPONSE
    assert set(result.keys()) == {"services", "tasks", "parallel_groups", "explanation"}
    assert len(result["tasks"]) == 2
    mock_llm_client.chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_json(decomposer, mock_llm_client):
    """Mock LLM returns malformed text -> ValueError."""
    mock_llm_client.chat.return_value = _make_response(
        "this is not valid json{{{broken"
    )

    with pytest.raises(ValueError, match="LLM 返回格式异常"):
        await decomposer.decompose("test requirement")


@pytest.mark.asyncio
async def test_missing_fields(decomposer, mock_llm_client):
    """Mock LLM returns JSON missing required field 'tasks' -> ValueError."""
    bad_json = {"services": [], "parallel_groups": [], "explanation": "missing tasks"}
    mock_llm_client.chat.return_value = _make_response(json.dumps(bad_json))

    with pytest.raises(ValueError, match="缺少必要字段"):
        await decomposer.decompose("test requirement")


@pytest.mark.asyncio
async def test_llm_exception(decomposer, mock_llm_client):
    """Mock LLM raises exception during API call -> RuntimeError."""
    mock_llm_client.chat.side_effect = ConnectionError("API unreachable")

    with pytest.raises(RuntimeError, match="LLM 调用失败"):
        await decomposer.decompose("test requirement")


def test_load_docs(mock_llm_client):
    """_load_docs reads the real docs/ directory and returns substantive markdown.

    The module-level DOCS_DIR is relative to the decomposer file path, which
    resolves to backend/docs/. We patch it to the project's real docs/ directory.
    """
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    real_docs = project_root / "docs"

    decomposer = TaskDecomposer(llm_client=mock_llm_client)
    with patch("app.agent.decomposer.DOCS_DIR", real_docs):
        docs_text = decomposer._load_docs()

    assert docs_text, "docs_text should not be empty"
    assert len(docs_text) > 100, "Should contain substantial content from multiple docs"
    # Verify key documents are included
    assert "PRD" in docs_text or "产品需求" in docs_text or "数据库设计" in docs_text
