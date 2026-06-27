"""检索服务整合"""
import re
from typing import List, Dict
from collections import Counter
from app.rag.embedder import Embedder
from app.rag.vector_store import VectorStore
from app.config import get_settings


def _tokenize_query(query: str) -> List[str]:
    """简单中文分词: 2-4 字滑动窗口提取关键词"""
    cleaned = re.sub(r"[^一-鿿\w]", "", query)
    tokens = set()
    for n in (2, 3, 4):
        for i in range(len(cleaned) - n + 1):
            tokens.add(cleaned[i : i + n])
    # 保留完整的英文/数字词
    for w in re.findall(r"[a-zA-Z0-9]+", query):
        tokens.add(w.lower())
    return list(tokens)


class Retriever:
    """向量检索服务"""

    def __init__(self):
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.settings = get_settings()

    def search(self, query: str, kb_id: str | None = None) -> List[Dict]:
        """
        语义检索 + 关键词加分重排序

        Args:
            query: 用户问题
            kb_id: 可选的知识库 ID, 用于限定检索范围

        Returns: [{text, source, chunk_index, score}, ...]

        Raises:
            RuntimeError: embedding 或向量检索失败时
        """
        try:
            vec = self.embedder.embed_query(query)
        except Exception as e:
            raise RuntimeError(f"Embedding 生成失败: {e}") from e

        if kb_id is not None:
            if not kb_id.isdigit():
                raise ValueError(f"Invalid kb_id: {kb_id}")
            filter_expr = f'kb_id == "{kb_id}"'
        else:
            filter_expr = None

        # 先取 top_k*2 做候选池, 给关键词重排留空间
        try:
            candidates = self.vector_store.search(
                query_embedding=vec,
                top_k=self.settings.top_k * 2,
                threshold=self.settings.similarity_threshold,
                filter_expr=filter_expr,
            )
        except Exception as e:
            raise RuntimeError(f"向量检索失败: {e}") from e

        if not candidates:
            return []

        # 关键词加分: query 中的词在 chunk 文本中出现 → 加权
        query_words = _tokenize_query(query)
        for c in candidates:
            if query_words:
                hits = sum(1 for w in query_words if w in c["text"])
                c["score"] = c["score"] + hits * 0.03  # 每个命中词 +0.03

        # 按加分后 score 重排, 取 top_k
        candidates.sort(key=lambda c: c["score"], reverse=True)
        return candidates[: self.settings.top_k]

    def auto_route(self, query: str) -> str | None:
        """
        自动路由: 无过滤检索 top_k=10, 按 kb_id 统计, 返回多数派 kb_id

        Args:
            query: 用户问题

        Returns:
            多数派知识库 ID, 或 None (无法确定时)
        """
        try:
            vec = self.embedder.embed_query(query)
            chunks = self.vector_store.search(
                query_embedding=vec,
                top_k=10,
                threshold=self.settings.similarity_threshold,
            )
        except Exception:
            return None  # embedding/检索失败 → 由上层降级

        if not chunks:
            return None

        # 统计每个 kb_id 出现次数
        kb_counts = Counter()
        for c in chunks:
            kid = c.get("kb_id", "")
            if kid:
                kb_counts[kid] += 1

        if not kb_counts:
            return None

        # 返回出现次数最多的 kb_id
        return kb_counts.most_common(1)[0][0]
