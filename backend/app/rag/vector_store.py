"""Milvus 向量存储与检索"""
from typing import List, Dict, Optional
from pymilvus import MilvusClient
from app.config import get_settings


class VectorStore:
    """Milvus 向量存储封装"""

    COLLECTION_NAME = "knowledge_chunks"

    def __init__(self):
        settings = get_settings()
        self.db_path = settings.milvus_db_path
        self.dimension = settings.embedding_dimension
        self._client: MilvusClient | None = None

    @property
    def client(self) -> MilvusClient:
        """懒加载 Milvus 客户端"""
        if self._client is None:
            self._client = MilvusClient(self.db_path)
            self._ensure_collection()
        return self._client

    def _ensure_collection(self):
        """确保 collection 存在并已加载"""
        exists = self.client.has_collection(self.COLLECTION_NAME)
        if not exists:
            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                dimension=self.dimension,
                metric_type="COSINE",
                auto_id=True,
                enable_dynamic_field=True,
            )
        # pymilvus 3.0 需要显式 load 才能 search
        self.client.load_collection(self.COLLECTION_NAME)

    def insert_chunks(self, chunks: List[Dict], embeddings: List[List[float]], kb_id: str | None = None) -> List[int]:
        """批量插入 chunk + embedding, 返回 Milvus 主键 ID 列表

        Args:
            chunks: 分块列表
            embeddings: embedding 向量列表
            kb_id: 可选的知识库 ID, 写入每个 chunk 的 metadata
        """
        if not chunks or not embeddings:
            return []

        data = []
        for chunk, emb in zip(chunks, embeddings):
            entry = {
                "vector": emb,
                "text": chunk["text"],
                "source": chunk["metadata"].get("source", "unknown"),
                "chunk_index": chunk["metadata"].get("chunk_index", 0),
            }
            if kb_id:
                entry["kb_id"] = kb_id
            data.append(entry)

        result = self.client.insert(
            collection_name=self.COLLECTION_NAME,
            data=data,
        )
        ids = result.get("ids", [])
        return list(ids)  # pymilvus 3.0 返回 RepeatedScalarContainer, 需转为 list

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        threshold: float = 0.65,
        filter_expr: Optional[str] = None,
    ) -> List[Dict]:
        """向量相似度检索, 返回 [{text, source, chunk_index, score}, ...]"""
        try:
            results = self.client.search(
                collection_name=self.COLLECTION_NAME,
                data=[query_embedding],
                limit=top_k,
                output_fields=["text", "source", "chunk_index", "kb_id"],
                filter=filter_expr,
            )
        except Exception as e:
            raise RuntimeError(f"Milvus 向量检索失败: {e}") from e

        hits = []
        for hit in results[0]:
            if hit["distance"] >= threshold:
                hits.append({
                    "text": hit["entity"]["text"],
                    "source": hit["entity"]["source"],
                    "chunk_index": hit["entity"]["chunk_index"],
                    "score": round(hit["distance"], 4),
                    "kb_id": hit["entity"].get("kb_id", ""),
                })
        return hits

    def delete_by_ids(self, ids: List[int]):
        """按 ID 删除向量"""
        if ids:
            self.client.delete(
                collection_name=self.COLLECTION_NAME,
                ids=ids,
            )

    def count(self) -> int:
        """返回向量总数"""
        if not self.client.has_collection(self.COLLECTION_NAME):
            return 0
        result = self.client.query(
            collection_name=self.COLLECTION_NAME,
            filter="id >= 0",
            output_fields=["count(*)"],
        )
        return result[0].get("count(*)", 0) if result else 0

    def query_by_source(self, source: str, kb_id: str | None = None, limit: int = 1000) -> List[Dict]:
        """按文档来源查询所有分块

        Args:
            source: 文档名称 (Milvus source 字段)
            kb_id: 可选的知识库 ID, 用于隔离不同知识库的同名文档
            limit: 最大返回数量

        Returns:
            [{text, source, chunk_index, id}, ...]
        """
        filter_parts = [f'source == "{source}"']
        if kb_id:
            filter_parts.append(f'kb_id == "{kb_id}"')
        results = self.client.query(
            collection_name=self.COLLECTION_NAME,
            filter=" && ".join(filter_parts),
            output_fields=["text", "source", "chunk_index"],
            limit=limit,
        )
        return [
            {
                "text": r["text"],
                "source": r["source"],
                "chunk_index": r["chunk_index"],
                "id": r["id"],
            }
            for r in results
        ]

    def drop_collection(self):
        """删除整个 collection（重置用）"""
        if self.client.has_collection(self.COLLECTION_NAME):
            self.client.drop_collection(self.COLLECTION_NAME)
