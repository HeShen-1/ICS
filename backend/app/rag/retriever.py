"""检索服务整合"""
from typing import List, Dict
from collections import Counter
from app.rag.embedder import Embedder
from app.rag.vector_store import VectorStore
from app.config import get_settings


class Retriever:
    """向量检索服务"""

    def __init__(self):
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.settings = get_settings()

    def search(self, query: str, kb_id: str | None = None) -> List[Dict]:
        """
        语义检索

        Args:
            query: 用户问题
            kb_id: 可选的知识库 ID, 用于限定检索范围

        Returns: [{text, source, chunk_index, score}, ...]
        """
        vec = self.embedder.embed_query(query)
        # 安全: kb_id 来自 MySQL 自增整数, 校验后安全拼接为 Milvus filter
        if kb_id is not None:
            if not kb_id.isdigit():
                raise ValueError(f"Invalid kb_id: {kb_id}")
            filter_expr = f'kb_id == "{kb_id}"'
        else:
            filter_expr = None
        chunks = self.vector_store.search(
            query_embedding=vec,
            top_k=self.settings.top_k,
            threshold=self.settings.similarity_threshold,
            filter_expr=filter_expr,
        )
        return chunks

    def auto_route(self, query: str) -> str | None:
        """
        自动路由: 无过滤检索 top_k=10, 按 kb_id 统计, 返回多数派 kb_id

        Args:
            query: 用户问题

        Returns:
            多数派知识库 ID, 或 None (无法确定时)
        """
        vec = self.embedder.embed_query(query)
        chunks = self.vector_store.search(
            query_embedding=vec,
            top_k=10,
            threshold=self.settings.similarity_threshold,
        )
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
