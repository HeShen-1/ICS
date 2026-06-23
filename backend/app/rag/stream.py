"""SSE 流式输出模块"""
import json
import asyncio
from typing import List, Dict, AsyncGenerator
from openai import APITimeoutError, RateLimitError
from app.rag.retriever import Retriever
from app.rag.prompt import build_messages
from app.rag.llm import LLMClient
from app.rag.fallback import get_fallback_response, get_fallback_sources
from app.config import get_settings

# 模块级单例缓存
_retriever: Retriever | None = None
_llm: LLMClient | None = None


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


def get_llm() -> LLMClient:
    global _llm
    if _llm is None:
        _llm = LLMClient()
    return _llm


def _sse_event(event: str, data: dict) -> str:
    """构造 SSE 事件字符串"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def generate_chat_stream(
    query: str,
    session_id: int,
    history_messages: List[Dict] = None,
) -> AsyncGenerator[str, None]:
    """RAG 问答 SSE 流式生成器

    Args:
        query: 用户问题
        session_id: 会话 ID
        history_messages: 历史消息列表

    Yields: SSE 格式字符串
    """
    settings = get_settings()
    retriever = get_retriever()
    llm = get_llm()

    try:
        # Step 1: 检索
        chunks = retriever.search(query)

        # Step 2: 检查检索结果
        if not chunks:
            fallback = get_fallback_response()
            for char in fallback:
                yield _sse_event("token", {"text": char})
                await asyncio.sleep(0.02)  # 模拟打字效果
            yield _sse_event("sources", {"references": get_fallback_sources()})
            yield _sse_event("done", {"message_id": None, "empty_retrieval": True})
            return

        # Step 3: 拼装 Prompt
        messages = build_messages(
            query=query,
            retrieved_chunks=chunks,
            history_messages=history_messages,
            max_history_rounds=settings.max_history_rounds,
        )

        # Step 4: 流式调用 LLM
        full_response = ""
        async for token in llm.chat_stream(messages):
            full_response += token
            yield _sse_event("token", {"text": token})

        # Step 5: 发送引用来源
        sources = [
            {"doc_name": c["source"], "snippet": c["text"][:100], "score": c["score"]}
            for c in chunks
        ]
        yield _sse_event("sources", {"references": sources})

        # Step 6: 结束
        yield _sse_event("done", {
            "message_id": None,
            "full_response": full_response,
            "references": sources,
        })

    except Exception as e:
        # 错误时仅发送 error 事件，不发送 done
        yield _sse_event("error", {
            "code": _error_code(e),
            "message": _error_message(e),
        })


def _error_code(error: Exception) -> str:
    if isinstance(error, APITimeoutError):
        return "LLM_TIMEOUT"
    if isinstance(error, RateLimitError):
        return "LLM_RATE_LIMITED"
    return "INTERNAL_ERROR"


def _error_message(error: Exception) -> str:
    if isinstance(error, APITimeoutError):
        return "AI 服务响应超时，请稍后重试"
    if isinstance(error, RateLimitError):
        return "AI 服务繁忙，请稍后重试"
    return "系统内部错误，请联系管理员"
