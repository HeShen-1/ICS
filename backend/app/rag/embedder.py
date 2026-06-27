"""Embedding 模块 - BGE-M3 本地模型（单例）"""
from typing import List
from sentence_transformers import SentenceTransformer
from app.config import get_settings

# 模块级模型缓存：所有 Embedder 实例共享同一个模型
_model: SentenceTransformer | None = None


class Embedder:
    """BGE-M3 Embedding 封装（单例模型）"""

    def __init__(self):
        settings = get_settings()
        self.model_name = settings.embedding_model
        self.device = settings.embedding_device

    @property
    def model(self) -> SentenceTransformer:
        """模块级模型懒加载，所有实例共享"""
        global _model
        if _model is None:
            settings = get_settings()
            _model = SentenceTransformer(
                settings.embedding_model,
                device=settings.embedding_device,
            )
        return _model

    def embed(self, texts: List[str]) -> List[List[float]]:
        """批量生成 embedding 向量"""
        if not texts:
            return []

        try:
            embeddings = self.model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return embeddings.tolist()
        except Exception as e:
            raise RuntimeError(f"Embedding 模型编码失败: {e}") from e

    def embed_query(self, query: str) -> List[float]:
        """单条查询 embedding"""
        return self.embed([query])[0]

    @property
    def dimension(self) -> int:
        """返回 embedding 维度"""
        return self.model.get_sentence_embedding_dimension()
