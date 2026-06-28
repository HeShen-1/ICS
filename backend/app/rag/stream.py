"""SSE 流式输出模块"""
import json
import re
import asyncio
import logging
from typing import List, Dict, AsyncGenerator
from openai import APITimeoutError, RateLimitError
from app.rag.retriever import Retriever
from app.rag.prompt import build_messages
from app.rag.llm import LLMClient
from app.rag.fallback import get_fallback_response, get_fallback_sources
from app.rag.intent import classify_intent
from app.config import get_settings

logger = logging.getLogger(__name__)

# 模块级单例缓存
_retriever: Retriever | None = None
_llm: LLMClient | None = None
_kb_name_cache: dict[str, str] = {}

# LLM Query Rewrite Prompt — 极简，<30 tokens 输出
_QUERY_REWRITE_PROMPT = (
    "将用户问题改写为搜索关键词（空格分隔），提取核心概念，去除语气词。"
    "只输出关键词，不要解释。\n"
    "用户问题：{query}\n"
    "关键词："
)


def _lookup_kb_name(kb_id: str | None) -> str | None:
    """查询知识库名称，带缓存"""
    if not kb_id:
        return None
    if kb_id in _kb_name_cache:
        return _kb_name_cache[kb_id]
    try:
        kb_id_int = int(kb_id)
    except (ValueError, TypeError):
        return None
    try:
        from app.database import SessionLocal
        from app.models.knowledge_base import KnowledgeBase

        db = SessionLocal()
        try:
            kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id_int).first()
            name = kb.name if kb else None
            _kb_name_cache[kb_id] = name
            return name
        finally:
            db.close()
    except Exception:
        logger = __import__("logging").getLogger(__name__)
        logger.warning("KB name lookup failed for kb_id=%s", kb_id, exc_info=True)
        return None


async def _rewrite_query(llm: LLMClient, query: str) -> str | None:
    """LLM Query Rewriting: 口语化问题 → 搜索关键词

    将用户的口语化问题改写为搜索优化的关键词串，
    桥接用户措辞和知识库措辞之间的语义 gap。

    Returns:
        改写后的关键词串，或 None（LLM 不可用/超时时）
    """
    try:
        prompt = _QUERY_REWRITE_PROMPT.format(query=query)
        response = await llm.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,  # 确定性输出
            max_tokens=30,
        )
        keywords = response.choices[0].message.content.strip()
        if keywords and len(keywords) >= 2:
            logger.info("LLM Rewrite: '%s' → '%s'", query, keywords)
            return keywords
    except Exception:
        logger.warning("Query rewrite failed for: %s", query, exc_info=True)
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
        intent_tag = await classify_intent(query)

    # Step 0.5: LLM Query Rewriting — 口语化问题 → 搜索关键词
    search_query = query
    if settings.llm_rewrite_enabled:
        rewritten = await _rewrite_query(llm, query)
        if rewritten:
            # 原始 query + 改写关键词拼接，兼顾语义和关键词覆盖
            search_query = f"{query} {rewritten}"

    try:
        # Step 1: 自动路由到最匹配的知识库（仅在调用方未指定 kb_id 时）
        if kb_id is None:
            kb_id = retriever.auto_route(search_query)
        kb_name = _lookup_kb_name(kb_id)

        # Step 2: 检索 — Multi-Query RRF + 三层降级
        chunks = []
        if kb_id is not None:
            # 第一层: 路由到特定知识库, Multi-Query RRF 检索
            chunks = retriever.multi_search(search_query, kb_id=kb_id)

        if not chunks and kb_id is None:
            # 第二层: auto_route 失败, 全局 Multi-Query RRF 检索
            chunks = retriever.multi_search(search_query, kb_id=None)

        if not chunks:
            # 第三层: 降低阈值仅用于路由探测，不以低质量 chunk 直接生成
            fallback_chunks = retriever.vector_store.search(
                query_embedding=retriever.embedder.embed_query(search_query),
                top_k=settings.top_k,
                threshold=settings.fallback_threshold,
            )
            if fallback_chunks:
                # 取多数派 kb_id 作为路由
                from collections import Counter
                kb_counts = Counter(c.get("kb_id", "") for c in fallback_chunks)
                best_kb = kb_counts.most_common(1)[0][0] if kb_counts else None
                if best_kb:
                    # 用路由结果重新 Multi-Query RRF 检索
                    chunks = retriever.multi_search(search_query, kb_id=best_kb)
                    if chunks:
                        kb_id = best_kb
                        kb_name = _lookup_kb_name(kb_id)
                # 第二机会: 如果路由后正常阈值仍无结果，检查兜底 chunk 质量
                if not chunks:
                    best_score = max((c.get("score", 0) for c in fallback_chunks), default=0)
                    if best_score >= settings.similarity_threshold:
                        # 兜底 chunk 中有达到正常阈值的 → 通过质量门，可以使用
                        chunks = fallback_chunks
                        kb_counts = Counter(c.get("kb_id", "") for c in chunks)
                        kb_id = kb_counts.most_common(1)[0][0] if kb_counts else None
                        kb_name = _lookup_kb_name(kb_id)
                    # else: 所有兜底 chunk 仍低于 quality bar → 走硬兜底

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

        # 如果 kb_name 为空（auto_route 失败），从检索到的 chunk 推断
        if not kb_name and chunks:
            inferred_kb = chunks[0].get("kb_id", "")
            if inferred_kb:
                kb_name = _lookup_kb_name(inferred_kb)

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
