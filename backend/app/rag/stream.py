"""SSE 流式输出模块"""
import json
import re
import asyncio
from typing import List, Dict, AsyncGenerator
from openai import APITimeoutError, RateLimitError
from app.rag.retriever import Retriever
from app.rag.prompt import build_messages
from app.rag.llm import LLMClient
from app.rag.fallback import get_fallback_response, get_fallback_sources
from app.rag.intent import classify_intent
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
    intent_classify: bool = True,
    intent_tag: str | None = None,
    kb_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """RAG 问答 SSE 流式生成器

    Args:
        query: 用户问题
        session_id: 会话 ID
        history_messages: 历史消息列表
        intent_classify: 是否进行意图识别
        intent_tag: 预分类的意图标签（优先级高于内置分类）
        kb_id: 可选的知识库 ID, 用于限定检索范围

    Yields: SSE 格式字符串
    """
    settings = get_settings()
    retriever = get_retriever()
    llm = get_llm()

    # Step 0: 意图识别
    if intent_tag is None and intent_classify:
        intent_tag = classify_intent(query)

    try:
        # Step 1: 检索
        if kb_id is None:
            kb_id = retriever.auto_route(query)
        if kb_id is None:
            # 自动路由失败(无KB或无匹配), 返回兜底话术而非跨库搜索
            fallback = get_fallback_response()
            for char in fallback:
                yield _sse_event("token", {"text": char})
                await asyncio.sleep(0.02)
            yield _sse_event("sources", {"references": get_fallback_sources()})
            yield _sse_event("done", {
                "message_id": None,
                "empty_retrieval": True,
                "intent_tag": intent_tag,
            })
            return

        chunks = retriever.search(query, kb_id=kb_id)

        # Step 2: 检查检索结果
        if not chunks:
            fallback = get_fallback_response()
            for char in fallback:
                yield _sse_event("token", {"text": char})
                await asyncio.sleep(0.02)  # 模拟打字效果
            yield _sse_event("sources", {"references": get_fallback_sources()})
            yield _sse_event("done", {
                "message_id": None,
                "empty_retrieval": True,
                "intent_tag": intent_tag,
            })
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

        # Step 5.5: 解析追问并发送 followup 事件
        followup_match = re.search(r"\[追问\]\s*(.+)", full_response)
        if followup_match:
            questions_raw = followup_match.group(1)
            suggestions = [q.strip() for q in questions_raw.split("|") if q.strip()]
            if suggestions:
                yield _sse_event("followup", {"suggestions": suggestions})

        # Step 6: 结束
        yield _sse_event("done", {
            "message_id": None,
            "full_response": full_response,
            "references": sources,
            "intent_tag": intent_tag,
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
