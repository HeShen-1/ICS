"""文档解析与入库服务"""
import os
from typing import Dict
from pathlib import Path
from app.rag.chunker import TextChunker
from app.rag.embedder import Embedder
from app.rag.vector_store import VectorStore


class DocumentIngestion:
    """文档入库：解析 → 分块 → Embedding → 存入 Milvus"""

    def __init__(self):
        self.chunker = TextChunker()
        self.embedder = Embedder()
        self.vector_store = VectorStore()

    def ingest_file(self, file_path: str, kb_id: str | None = None, source_name: str | None = None) -> Dict:
        """
        处理单个文件并入库

        Args:
            file_path: 文件路径
            kb_id: 可选的知识库 ID
            source_name: 可选的自定义 source 名称, 不传则用 file_path 的 basename

        Returns:
            {"success": True/False, "chunk_count": int, "milvus_ids": [...], "error": str|None}
        """
        try:
            # 1. 读取文件内容
            text = self._read_file(file_path)
            if not text:
                return {"success": False, "chunk_count": 0, "milvus_ids": [], "error": "文件内容为空"}

            # 2. 分块
            doc_name = source_name or os.path.basename(file_path)
            chunks = self.chunker.chunk(text, metadata={"source": doc_name})
            if not chunks:
                return {"success": False, "chunk_count": 0, "milvus_ids": [], "error": "分块结果为空"}

            # 3. 批量生成 Embedding
            chunk_texts = [c["text"] for c in chunks]
            embeddings = self.embedder.embed(chunk_texts)

            # 4. 批量写入 Milvus
            milvus_ids = self.vector_store.insert_chunks(chunks, embeddings, kb_id=kb_id)

            return {
                "success": True,
                "chunk_count": len(chunks),
                "milvus_ids": milvus_ids,
                "error": None,
            }
        except Exception as e:
            return {"success": False, "chunk_count": 0, "milvus_ids": [], "error": str(e)}

    def _read_file(self, file_path: str) -> str:
        """读取文件内容，支持 .txt / .md / .pdf"""
        ext = Path(file_path).suffix.lower()

        if ext in (".txt", ".md"):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

        if ext == ".pdf":
            try:
                from llama_index.readers.file import PDFReader
            except ImportError:
                raise ImportError("PDF 处理需要安装 llama-index: pip install llama-index-readers-file")
            reader = PDFReader()
            documents = reader.load_data(file=Path(file_path))
            return "\n\n".join(doc.text for doc in documents)

        raise ValueError(f"不支持的文件格式: {ext}")
