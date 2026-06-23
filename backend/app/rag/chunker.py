"""文档分块模块
策略: 按段落分块 + 滑动窗口重叠，保持语义完整性
"""
from typing import List, Dict
import re


class TextChunker:
    """文本分块器"""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str, metadata: Dict[str, str] = None) -> List[Dict]:
        """
        将文本切分为带 metadata 的 chunk 列表

        Args:
            text: 原始文本
            metadata: 附加信息（如文档名）

        Returns:
            [{text: "片段内容", metadata: {source: "文档名", chunk_index: 0}}, ...]
        """
        if not text or not text.strip():
            return []

        meta = metadata or {}

        # Step 1: 按段落分割
        paragraphs = self._split_paragraphs(text)

        # Step 2: 合并短段落 + 切分长段落
        chunks = self._merge_and_split(paragraphs)

        # Step 3: 添加 metadata
        return [
            {
                "text": chunk.strip(),
                "metadata": {
                    **meta,
                    "chunk_index": i,
                    "char_count": len(chunk.strip()),
                },
            }
            for i, chunk in enumerate(chunks)
            if chunk.strip()
        ]

    def _split_paragraphs(self, text: str) -> List[str]:
        """按双换行/单换行/标题分割段落"""
        # 先按双换行分
        parts = re.split(r"\n\s*\n", text)
        # 每个部分再按单换行分（保留较短的段落）
        result = []
        for part in parts:
            lines = part.split("\n")
            result.extend(line.strip() for line in lines if line.strip())
        return result

    def _merge_and_split(self, paragraphs: List[str]) -> List[str]:
        """合并短段落，切分长段落"""
        chunks = []
        current = ""

        for para in paragraphs:
            if len(current) + len(para) + 1 <= self.chunk_size:
                current = (current + "\n" + para).strip() if current else para
            else:
                if current:
                    chunks.append(current)
                # 长段落进一步切分
                if len(para) > self.chunk_size:
                    for i in range(0, len(para), self.chunk_size - self.chunk_overlap):
                        chunks.append(para[i : i + self.chunk_size])
                else:
                    current = para

        if current:
            chunks.append(current)

        return chunks
