"""检索服务整合"""
from typing import List, Dict
from app.rag.embedder import Embedder
from app.rag.vector_store import VectorStore
from app.config import get_settings


class Retriever:
    """向量检索服务"""

    def __init__(self):
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.settings = get_settings()

    def search(self, query: str) -> List[Dict]:
        """
        语义检索
        Returns: [{text, source, chunk_index, score}, ...]
        """
        vec = self.embedder.embed_query(query)
        chunks = self.vector_store.search(
            query_embedding=vec,
            top_k=self.settings.top_k,
            threshold=self.settings.similarity_threshold,
        )
        return chunks
