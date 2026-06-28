"""文档解析与入库服务"""
import hashlib
import os
from typing import Dict, List
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

    @staticmethod
    def _compute_file_hash(file_path: str) -> str:
        """计算文件的 SHA256 哈希值"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def ingest_file_incremental(
        self, file_path: str, kb_id: str | None = None, source_name: str | None = None
    ) -> Dict:
        """增量更新文件：对比新旧分块，仅更新变化的 chunk

        流程：query_by_source 获取旧分块 → 新分块 → 按 chunk_index diff →
              删除旧的不匹配 chunk → 插入新的 chunk → 返回全部 milvus_ids

        Args:
            file_path: 文件路径
            kb_id: 可选的知识库 ID
            source_name: 可选的自定义 source 名称

        Returns:
            {"success": True/False, "chunk_count": int, "milvus_ids": [...], "error": str|None}
        """
        try:
            doc_name = source_name or os.path.basename(file_path)

            # 1. 查询旧分块
            kb_id_str = str(kb_id) if kb_id else None
            old_chunks = self.vector_store.query_by_source(doc_name, kb_id=kb_id_str)
            old_by_index: Dict[int, dict] = {c["chunk_index"]: c for c in old_chunks}

            # 2. 读取并分块新文件
            text = self._read_file(file_path)
            if not text:
                return {"success": False, "chunk_count": 0, "milvus_ids": [], "error": "文件内容为空"}

            new_chunks = self.chunker.chunk(text, metadata={"source": doc_name})
            if not new_chunks:
                return {"success": False, "chunk_count": 0, "milvus_ids": [], "error": "分块结果为空"}

            # 3. 按 chunk_index 对比 diff
            kept_ids: List[int] = []
            to_delete: List[int] = []
            to_insert_chunks: List[dict] = []

            new_indices: set[int] = set()
            for c in new_chunks:
                idx = c["metadata"]["chunk_index"]
                new_indices.add(idx)
                if idx in old_by_index:
                    old = old_by_index[idx]
                    if c["text"] == old["text"]:
                        kept_ids.append(old["id"])
                        continue
                    else:
                        to_delete.append(old["id"])
                to_insert_chunks.append(c)

            # 旧分块中有但新分块中没有的 → 删除
            for idx, old in old_by_index.items():
                if idx not in new_indices:
                    to_delete.append(old["id"])

            # 4. 执行删除与插入
            if to_delete:
                self.vector_store.delete_by_ids(to_delete)

            new_ids: List[int] = []
            if to_insert_chunks:
                chunk_texts = [c["text"] for c in to_insert_chunks]
                embeddings = self.embedder.embed(chunk_texts)
                new_ids = self.vector_store.insert_chunks(
                    to_insert_chunks, embeddings, kb_id=kb_id_str
                )

            return {
                "success": True,
                "chunk_count": len(new_chunks),
                "milvus_ids": kept_ids + list(new_ids),
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
