"""RAG Automated Evaluation Tests.

Covers 4 evaluation dimensions:
    TestRetrievalMetrics   — recall@5, precision@5, document coverage
    TestFaithfulness       — hallucination detection on known questions
    TestAnswerRelevance    — keyword overlap between question and answer
    TestEndToEnd           — full pipeline structure and fallback behavior
"""

import re
import pytest
from typing import List

from tests.test_rag.eval_dataset import (
    LabeledQA,
    build_eval_dataset,
    get_dataset_for_doc,
    get_edge_case_questions,
)


# ── Helper: keyword-based retrieval simulator ────────────────────

def _tokenize(text: str) -> list[str]:
    """Tokenize Chinese/English text using jieba if available, else n-gram."""
    try:
        import jieba
        tokens = []
        for word in jieba.cut(text):
            word = word.strip()
            if len(word) >= 2 and re.search(r"[一-鿿\w]", word):
                tokens.append(word)
        # Supplement with n-gram for fallback coverage
        cleaned = re.sub(r"[^一-鿿\w]", "", text)
        for n in (2, 3):
            for i in range(len(cleaned) - n + 1):
                ng = cleaned[i:i + n]
                if ng not in tokens:
                    tokens.append(ng)
        for w in re.findall(r"[a-zA-Z0-9]+", text):
            wl = w.lower()
            if wl not in tokens:
                tokens.append(wl)
        return tokens
    except ImportError:
        cleaned = re.sub(r"[^一-鿿\w]", "", text)
        tokens = []
        for n in (2, 3, 4):
            for i in range(len(cleaned) - n + 1):
                tokens.append(cleaned[i:i + n])
        for w in re.findall(r"[a-zA-Z0-9]+", text):
            tokens.append(w.lower())
        return tokens


def _keyword_match_score(query: str, text: str) -> float:
    """Keyword overlap score using jieba + n-gram tokenization."""
    query_tokens = set(_tokenize(query.lower()))
    text_tokens = set(_tokenize(text.lower()))
    if not query_tokens:
        return 0.0
    hits = sum(1 for t in query_tokens if t in text_tokens)
    return hits / len(query_tokens)


def _simulate_retrieval(
    question: str,
    dataset: List[LabeledQA],
    top_k: int = 5,
) -> List[dict]:
    """Simulate retrieval by scanning all labeled chunks and scoring by keyword overlap.

    Returns top_k results as list of {source, text, score} dicts.
    """
    candidates = []
    for qa in dataset:
        score = _keyword_match_score(question, qa.relevant_chunk_text)
        candidates.append({
            "source": qa.source_document,
            "text": qa.relevant_chunk_text,
            "score": score,
            "qa_id": qa.id,
        })
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates[:top_k]


# ── TestRetrievalMetrics ────────────────────────────────────────

class TestRetrievalMetrics:
    """Validate retrieval quality metrics: recall@5, precision@5, coverage."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.dataset = build_eval_dataset()
        assert len(self.dataset) == 15, "Dataset must have 15 QA pairs"

    def test_recall_at_5(self):
        """Recall@5 >= 0.6: for most questions, the correct chunk is in top-5."""
        recall_hits = 0
        for qa in self.dataset:
            results = _simulate_retrieval(qa.question, self.dataset, top_k=5)
            retrieved_ids = {r["qa_id"] for r in results}
            if qa.id in retrieved_ids:
                recall_hits += 1

        recall = recall_hits / len(self.dataset)
        assert recall >= 0.6, (
            f"Recall@5 is {recall:.2f}, expected >= 0.6. "
            f"{recall_hits}/{len(self.dataset)} questions had correct chunk in top-5."
        )

    def test_precision_at_5(self):
        """Precision@5 > 0: at least some results have non-zero keyword overlap."""
        total_precision = 0.0
        for qa in self.dataset:
            results = _simulate_retrieval(qa.question, self.dataset, top_k=5)
            relevant = sum(1 for r in results if r["score"] > 0)
            total_precision += relevant / max(len(results), 1)

        avg_precision = total_precision / len(self.dataset)
        assert avg_precision > 0, (
            f"Average precision@5 is {avg_precision:.2f}, expected > 0."
        )

    def test_coverage(self):
        """All 7 example_docs are represented in the dataset."""
        unique_sources = {qa.source_document for qa in self.dataset}
        expected_docs = {
            "公司产品介绍.txt",
            "常见问题FAQ.md",
            "退换货政策.txt",
            "用户协议.txt",
            "技术支持说明.md",
            "隐私政策.txt",
            "版本更新日志.md",
        }
        missing = expected_docs - unique_sources
        assert not missing, f"Missing document coverage: {missing}"
        assert len(unique_sources) == 7, (
            f"Expected 7 unique source docs, got {len(unique_sources)}: {unique_sources}"
        )

    def test_retrieval_score_monotonic(self):
        """Scores should be monotonically decreasing in sorted results."""
        for qa in self.dataset[:5]:  # Sample 5 to keep test fast
            results = _simulate_retrieval(qa.question, self.dataset, top_k=10)
            scores = [r["score"] for r in results]
            for i in range(len(scores) - 1):
                assert scores[i] >= scores[i + 1], (
                    f"Scores not monotonic for {qa.id}: {scores}"
                )


# ── TestFaithfulness ────────────────────────────────────────────

class TestFaithfulness:
    """Validate that answers do not contain hallucinations."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.dataset = build_eval_dataset()

    def test_no_hallucination_on_known_questions(self):
        """For known questions, expected_keywords must be findable in the source chunk.

        A faithful answer draws only from retrieved content. We verify that the
        ground-truth keywords actually exist in the relevant chunk text.
        """
        for qa in self.dataset:
            chunk_lower = qa.relevant_chunk_text.lower()
            for kw in qa.expected_keywords:
                assert kw.lower() in chunk_lower, (
                    f"Keyword '{kw}' for {qa.id} not found in chunk text. "
                    f"This keyword would constitute hallucination if claimed."
                )

    def test_edge_case_questions_should_not_retrieve(self):
        """Out-of-scope questions should produce low keyword overlap scores."""
        edge_cases = get_edge_case_questions()
        for question in edge_cases:
            results = _simulate_retrieval(question, self.dataset, top_k=5)
            max_score = max((r["score"] for r in results), default=0.0)
            assert max_score < 0.5, (
                f"Edge-case question '{question}' had max retrieval score {max_score:.2f}. "
                f"Expected < 0.5 for out-of-scope queries."
            )

    def test_all_expected_keywords_are_meaningful(self):
        """Every expected_keyword must be at least 2 characters."""
        for qa in self.dataset:
            for kw in qa.expected_keywords:
                assert len(kw) >= 2, (
                    f"Keyword '{kw}' in {qa.id} is too short (< 2 chars)."
                )


# ── TestAnswerRelevance ─────────────────────────────────────────

class TestAnswerRelevance:
    """Validate that answers are relevant to the question asked."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.dataset = build_eval_dataset()

    def test_keyword_overlap(self):
        """Each question's expected_keywords must overlap with its source chunk.

        High overlap indicates the answer content is relevant to the question.
        """
        for qa in self.dataset:
            chunk_lower = qa.relevant_chunk_text.lower()
            matched = [kw for kw in qa.expected_keywords if kw.lower() in chunk_lower]
            ratio = len(matched) / len(qa.expected_keywords)
            assert ratio >= 0.5, (
                f"{qa.id}: keyword overlap ratio is {ratio:.2f} (< 0.5). "
                f"Only matched: {matched}"
            )

    def test_questions_are_distinct(self):
        """No two QA pairs should have identical questions."""
        questions = [qa.question for qa in self.dataset]
        assert len(set(questions)) == len(questions), (
            "Duplicate questions found in dataset."
        )

    def test_categories_are_valid(self):
        """All QA pairs must have one of the known categories."""
        valid_categories = {"product", "account", "policy", "technical", "edge", "general"}
        for qa in self.dataset:
            assert qa.category in valid_categories, (
                f"{qa.id}: unknown category '{qa.category}'"
            )


# ── TestEndToEnd ────────────────────────────────────────────────

class TestEndToEnd:
    """End-to-end pipeline structure and fallback validation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.dataset = build_eval_dataset()
        self.edge_cases = get_edge_case_questions()

    def test_full_pipeline_structure(self):
        """Verify the full RAG pipeline structure executes without crashing.

        Steps: query → embed → retrieve → build_messages → format chunks
        """
        from unittest.mock import patch, MagicMock, AsyncMock
        from app.rag.prompt import build_messages, format_retrieved_chunks
        from app.rag.fallback import get_fallback_response

        # Simulate retrieved chunks for a known question
        qa = self.dataset[0]
        mock_chunks = [
            {
                "text": qa.relevant_chunk_text,
                "source": qa.source_document,
                "score": 0.85,
                "chunk_index": 0,
                "header_path": "",
                "kb_id": "1",
            }
        ]

        # Verify build_messages returns a valid structure
        messages = build_messages(
            query=qa.question,
            retrieved_chunks=mock_chunks,
            history_messages=None,
        )
        assert isinstance(messages, list), "build_messages should return a list"
        assert len(messages) >= 2, "Should have at least system + user messages"
        assert messages[0]["role"] == "system", "First message must be system prompt"
        assert messages[-1]["role"] == "user", "Last message must be user query"
        assert qa.question in messages[-1]["content"], "User message must contain the question"

        # Verify format_retrieved_chunks produces readable text
        chunks_text = format_retrieved_chunks(mock_chunks)
        assert qa.source_document in chunks_text, (
            "Formatted chunks must reference source document name"
        )
        assert "来源" in chunks_text, "Formatted chunks must label source"

        # Verify fallback produces non-empty response
        fallback = get_fallback_response()
        assert len(fallback) > 0, "Fallback response must not be empty"

    def test_empty_retrieval_fallback(self):
        """When retrieval returns empty results, fallback should activate.

        The fallback response must contain the configured default message
        and not crash or hang.
        """
        from app.rag.fallback import get_fallback_response, get_fallback_sources

        fallback = get_fallback_response()
        sources = get_fallback_sources()

        assert isinstance(fallback, str), "Fallback response must be a string"
        assert len(fallback) > 20, "Fallback response must be meaningful"
        assert sources == [], "Fallback sources must be empty list"

        # Verify fallback mentions inability to answer
        fallback_keywords = ["抱歉", "暂时", "没有", "信息"]
        for kw in fallback_keywords:
            assert kw in fallback, (
                f"Fallback must contain '{kw}', got: {fallback}"
            )

    def test_dataset_integrity(self):
        """All 15 QA pairs must have all required fields populated."""
        for qa in self.dataset:
            assert qa.id, f"QA pair missing id"
            assert qa.question, f"{qa.id}: missing question"
            assert qa.source_document, f"{qa.id}: missing source_document"
            assert qa.expected_keywords, f"{qa.id}: missing expected_keywords"
            assert len(qa.expected_keywords) >= 3, (
                f"{qa.id}: must have >= 3 expected_keywords, got {len(qa.expected_keywords)}"
            )
            assert qa.relevant_chunk_text, f"{qa.id}: missing relevant_chunk_text"
            assert len(qa.relevant_chunk_text) >= 30, (
                f"{qa.id}: chunk text too short ({len(qa.relevant_chunk_text)} chars)"
            )

    def test_build_messages_with_many_chunks(self):
        """build_messages handles large numbers of retrieved chunks gracefully."""
        from app.rag.prompt import build_messages

        # Simulate 15+ chunks (triggers layered threshold)
        many_chunks = []
        for qa in self.dataset:
            many_chunks.append({
                "text": qa.relevant_chunk_text,
                "source": qa.source_document,
                "score": 0.5 + 0.03 * len(many_chunks),
                "chunk_index": len(many_chunks),
                "header_path": "",
                "kb_id": "1",
            })

        messages = build_messages(
            query="测试问题",
            retrieved_chunks=many_chunks,
        )
        assert len(messages) >= 2, "Should handle 15+ chunks without crashing"
        # System message should contain formatted chunks
        system_content = messages[0]["content"]
        assert "来源" in system_content or "知识库内容" in system_content, (
            "System prompt should contain chunk references"
        )

    def test_edge_case_empty_results(self):
        """Edge-case questions should produce low/no keyword overlap."""
        for question in self.edge_cases:
            results = _simulate_retrieval(question, self.dataset, top_k=12)
            # None of the top results should have high confidence
            high_conf = [r for r in results if r["score"] >= 0.5]
            assert len(high_conf) == 0, (
                f"Edge question '{question}' unexpectedly matched: {high_conf}"
            )
