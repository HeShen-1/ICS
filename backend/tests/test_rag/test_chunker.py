"""Tests for app.rag.chunker - TextChunker."""
import pytest
from app.rag.chunker import TextChunker


class TestSplitParagraphs:
    def test_split_paragraphs_basic(self):
        chunker = TextChunker(chunk_size=500, chunk_overlap=50)
        text = "第一段\n\n第二段\n\n第三段"
        result = chunker._split_paragraphs(text)
        assert len(result) == 3
        assert result[0] == "第一段"
        assert result[1] == "第二段"
        assert result[2] == "第三段"

    def test_split_paragraphs_empty(self):
        chunker = TextChunker()
        result = chunker._split_paragraphs("")
        assert result == []

    def test_split_paragraphs_single_line(self):
        chunker = TextChunker()
        result = chunker._split_paragraphs("只有一行")
        assert len(result) == 1
        assert result[0] == "只有一行"

    def test_split_paragraphs_single_newlines(self):
        chunker = TextChunker()
        text = "行一\n行二\n行三"
        result = chunker._split_paragraphs(text)
        assert len(result) == 3
        assert result == ["行一", "行二", "行三"]

    def test_split_paragraphs_blank_line_filtered(self):
        chunker = TextChunker()
        text = "行一\n\n\n\n行二"
        result = chunker._split_paragraphs(text)
        assert len(result) == 2
        assert result == ["行一", "行二"]


class TestChunk:
    def test_chunk_basic_text(self):
        chunker = TextChunker(chunk_size=500, chunk_overlap=50)
        text = "这是测试文本，用于验证分块功能。"
        chunks = chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0]["text"] == text
        assert chunks[0]["metadata"]["chunk_index"] == 0
        assert chunks[0]["metadata"]["char_count"] == len(text)

    def test_chunk_with_overlap(self):
        # Small chunk_size creates multiple chunks with overlap
        chunker = TextChunker(chunk_size=10, chunk_overlap=3)
        text = "ABCDEFGHIJKLMNOP"
        chunks = chunker.chunk(text)
        assert len(chunks) > 1
        # Check chunk indices are sequential
        indices = [c["metadata"]["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_chunk_empty_text(self):
        chunker = TextChunker()
        chunks = chunker.chunk("")
        assert chunks == []

    def test_chunk_whitespace_only(self):
        chunker = TextChunker()
        chunks = chunker.chunk("   \n  \n  ")
        assert chunks == []

    def test_chunk_overlap_validation(self):
        with pytest.raises(ValueError) as exc_info:
            TextChunker(chunk_size=10, chunk_overlap=6)
        assert "must be at most half" in str(exc_info.value)

    def test_chunk_overlap_equal_to_half_is_valid(self):
        # chunk_overlap exactly half of chunk_size should be valid
        chunker = TextChunker(chunk_size=10, chunk_overlap=5)
        assert chunker.chunk_overlap == 5

    def test_chunk_metadata_includes_chunk_index(self):
        chunker = TextChunker(chunk_size=20, chunk_overlap=0)
        long_text = "A" * 100
        chunks = chunker.chunk(long_text)
        for i, chunk in enumerate(chunks):
            assert chunk["metadata"]["chunk_index"] == i
            assert "char_count" in chunk["metadata"]

    def test_chunk_preserves_custom_metadata(self):
        chunker = TextChunker()
        custom_meta = {"source": "测试文档.txt", "author": "tester"}
        chunks = chunker.chunk("测试内容", metadata=custom_meta)
        assert len(chunks) == 1
        assert chunks[0]["metadata"]["source"] == "测试文档.txt"
        assert chunks[0]["metadata"]["author"] == "tester"

    def test_chunk_long_paragraph_split(self):
        """A single long paragraph exceeding chunk_size gets split."""
        chunker = TextChunker(chunk_size=10, chunk_overlap=0)
        text = "A" * 35  # single long paragraph
        chunks = chunker.chunk(text)
        assert len(chunks) >= 3  # 35 chars into size-10 chunks = 4 chunks

    def test_chunk_merge_short_paragraphs(self):
        """Short paragraphs should be merged when they fit in one chunk."""
        chunker = TextChunker(chunk_size=50, chunk_overlap=5)
        text = "短一\n短二\n短三"
        chunks = chunker.chunk(text)
        # All three short lines should fit in one chunk
        assert len(chunks) == 1
        assert "短一" in chunks[0]["text"]
        assert "短二" in chunks[0]["text"]
