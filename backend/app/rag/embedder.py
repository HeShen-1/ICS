"""Embedding 模块 - BGE-M3 本地模型"""
from typing import List
from sentence_transformers import SentenceTransformer
from app.config import get_settings


class Embedder:
    """BGE-M3 Embedding 封装"""

    def __init__(self):
        settings = get_settings()
        self.model_name = settings.embedding_model
        self.device = settings.embedding_device
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        """懒加载模型"""
        if self._model is None:
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
            )
        return self._model

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成 embedding 向量

        Args:
            texts: 文本列表

        Returns:
            embedding 向量列表，每个向量维度 1024
        """
        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """单条查询 embedding"""
        return self.embed([query])[0]

    @property
    def dimension(self) -> int:
        """返回 embedding 维度"""
        return self.model.get_sentence_embedding_dimension()
