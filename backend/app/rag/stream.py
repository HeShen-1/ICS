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
_kb_name_cache: dict[str, str] = {}


def _lookup_kb_name(kb_id: str | None) -> str | None:
    """查询知识库名称，带缓存"""
    if not kb_id:
        return None
    if kb_id in _kb_name_cache:
        return _kb_name_cache[kb_id]
    try:
        from app.database import SessionLocal
        from app.models.knowledge_base import KnowledgeBase

        db = SessionLocal()
        kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == int(kb_id)).first()
        db.close()
        name = kb.name if kb else None
        _kb_name_cache[kb_id] = name
        return name
    except Exception:
        return None


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
        # Step 1: 自动路由到最匹配的知识库
        kb_id = retriever.auto_route(query)
        kb_name = _lookup_kb_name(kb_id)

        # Step 2: 检索 — 三层降级
        chunks = []
        if kb_id is not None:
            # 第一层: 路由到特定知识库检索
            chunks = retriever.search(query, kb_id=kb_id)

        if not chunks and kb_id is None:
            # 第二层: auto_route 失败, 尝试无过滤全局检索
            chunks = retriever.search(query, kb_id=None)

        if not chunks:
            # 第三层: 降低阈值再试
            chunks = retriever.vector_store.search(
                query_embedding=retriever.embedder.embed_query(query),
                top_k=settings.top_k,
                threshold=0.35,  # 大幅降低, 兜底
            )
            if chunks:
                # 取多数派 kb_id 作为路由
                from collections import Counter
                kb_counts = Counter(c.get("kb_id", "") for c in chunks)
                kb_id = kb_counts.most_common(1)[0][0] if kb_counts else None
                kb_name = _lookup_kb_name(kb_id)

        # 最终仍无结果 → 兜底
        if not chunks:
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

        # Step 5: 发送引用来源（含知识库名称，按文档去重）
        seen_sources = {}
        for c in chunks:
            doc = c["source"]
            if doc not in seen_sources or c["score"] > seen_sources[doc]["score"]:
                seen_sources[doc] = {
                    "doc_name": doc,
                    "snippet": c["text"][:100],
                    "score": c["score"],
                    "kb_name": kb_name or "",
                }
        sources = list(seen_sources.values())
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
