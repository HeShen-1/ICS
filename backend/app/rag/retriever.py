"""检索服务整合 — Dense + Keyword + Multi-Query RRF"""
import re
from typing import List, Dict
from collections import Counter
from app.rag.embedder import Embedder
from app.rag.vector_store import VectorStore
from app.config import get_settings


# ── Query 扩展 ──────────────────────────────────────

# 中文停用词 / 语气词
_FILLER_WORDS = {"了", "的", "吧", "把", "吗", "呢", "啊", "呀", "嘛", "哦", "哈", "啦", "喔"}

# 同义词映射: query 中的词 → 文档中可能出现的词
_SYNONYM_MAP = {
    "忘记": ["找回", "重置", "恢复"],
    "登录": ["账号", "账户", "注册"],
    "怎么办": ["如何", "怎么处理", "解决", "方法"],
    "找回": ["忘记", "重置", "恢复", "取回"],
    "密码": ["口令", "凭证", "密钥"],
    "重置": ["找回", "修改", "更换", "变更"],
    "修改": ["更改", "变更", "更新", "重置"],
    "退款": ["退换", "退货", "退还"],
    "退货": ["退换", "退款", "退还"],
    "退换货": ["退货", "退款", "售后"],
    "无法": ["不能", "不可", "失败"],
}


def _expand_query_variants(query: str) -> list[str]:
    """生成 3-5 个 query 变体用于多路召回"""
    variants = [query]

    # 1. 去掉语气词
    cleaned = query
    for f in _FILLER_WORDS:
        cleaned = cleaned.replace(f, "")
    if cleaned != query and len(cleaned) >= 2:
        variants.append(cleaned)

    # 2. jieba 关键词拼接
    try:
        import jieba
        tokens = [w for w in jieba.cut(query) if len(w) >= 2 and w not in _FILLER_WORDS]
        if tokens:
            variants.append(" ".join(tokens))
            # 纯内容词 (去疑问词)
            question_words = {"怎么", "什么", "如何", "为什么", "哪里", "哪", "谁", "多少"}
            core = [t for t in tokens if t not in question_words]
            if core and len(core) < len(tokens):
                variants.append(" ".join(core))
    except ImportError:
        pass

    # 3. 同义词替换: 每个可替换位置生成一个变体
    for word, syns in _SYNONYM_MAP.items():
        if word in query:
            for syn in syns[:2]:  # 最多 2 个同义词变体
                variants.append(query.replace(word, syn))

    # 去重 + 截断
    seen = set()
    result = []
    for v in variants:
        if v not in seen and len(v.strip()) >= 2:
            seen.add(v)
            result.append(v)
    return result[:5]


# ── RRF 融合 ────────────────────────────────────────

def _rrf_fuse(results_list: list[list[Dict]], k: int = 60) -> list[Dict]:
    """Reciprocal Rank Fusion: 多路召回结果合并

    Args:
        results_list: 每组是一个排好序的 chunk 列表 (best first)
        k: RRF 平滑参数

    Returns:
        融合后排好序的 chunk 列表
    """
    rrf_scores: dict[tuple, float] = {}
    chunk_map: dict[tuple, Dict] = {}

    for results in results_list:
        for rank, chunk in enumerate(results):
            key = (chunk.get("source", ""), chunk.get("chunk_index", -1))
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            if key not in chunk_map:
                chunk_map[key] = chunk

    sorted_keys = sorted(rrf_scores, key=rrf_scores.get, reverse=True)
    return [chunk_map[key] for key in sorted_keys]


# ── Tokenizer + Keyword ─────────────────────────────

def _tokenize_query(query: str) -> List[str]:
    """中文分词: 优先用 jieba，不可用时回退 n-gram 滑动窗口"""
    try:
        import jieba
        tokens = set()
        for word in jieba.cut(query):
            word = word.strip()
            # 过滤单字和标点
            if len(word) >= 2 and re.search(r"[一-鿿\w]", word):
                tokens.add(word)
        # 补充 n-gram 兜底 (jieba 可能漏切)
        cleaned = re.sub(r"[^一-鿿\w]", "", query)
        for n in (2, 3, 4):
            for i in range(len(cleaned) - n + 1):
                tokens.add(cleaned[i : i + n])
        for w in re.findall(r"[a-zA-Z0-9]+", query):
            tokens.add(w.lower())
        return list(tokens)
    except ImportError:
        # jieba 不可用 → 纯 n-gram
        cleaned = re.sub(r"[^一-鿿\w]", "", query)
        tokens = set()
        for n in (2, 3, 4):
            for i in range(len(cleaned) - n + 1):
                tokens.add(cleaned[i : i + n])
        for w in re.findall(r"[a-zA-Z0-9]+", query):
            tokens.add(w.lower())
        return list(tokens)


def _keyword_score(query: str, text: str) -> float:
    """加权关键词匹配分: 精确 + 子串模糊匹配

    精确匹配 (ngram in text): 全权重
    子串匹配 (ngram 是 text 中某词的子串): 半权重
      解决中文复合词不匹配问题, 如 "退货" 是 "退换货" 的子串
    """
    query_ngrams = _tokenize_query(query)
    if not query_ngrams:
        return 0.0

    # 构建 text 中所有 2-6 字子串的集合，用于子串匹配
    text_clean = re.sub(r"[^一-鿿\w]", "", text)
    text_substrings: set[str] = set()
    for n in (2, 3, 4, 5, 6):
        for i in range(len(text_clean) - n + 1):
            text_substrings.add(text_clean[i : i + n])

    score = 0.0
    for ngram in query_ngrams:
        n = len(ngram)
        if ngram in text:
            # 精确匹配: 完整 token 出现在文本中
            if n >= 4:
                score += 0.08
            elif n == 3:
                score += 0.05
            elif n == 2:
                score += 0.03
        elif ngram in text_substrings:
            # 子串匹配: token 是文本中某词的子串 (如 "退货" ⊂ "退换货")
            if n >= 3:
                score += 0.02  # 3+ char 子串 → 小加分
            # 2-char 子串不加分 (噪声太多)

    return min(score, 0.30)


class Retriever:
    """向量检索服务"""

    def __init__(self):
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.settings = get_settings()

    def search(self, query: str, kb_id: str | None = None) -> List[Dict]:
        """
        语义检索 + 关键词加分重排序

        Args:
            query: 用户问题
            kb_id: 可选的知识库 ID, 用于限定检索范围

        Returns: [{text, source, chunk_index, score}, ...]

        Raises:
            RuntimeError: embedding 或向量检索失败时
        """
        try:
            vec = self.embedder.embed_query(query)
        except Exception as e:
            raise RuntimeError(f"Embedding 生成失败: {e}") from e

        if kb_id is not None:
            if not kb_id.isdigit():
                raise ValueError(f"Invalid kb_id: {kb_id}")
            filter_expr = f'kb_id == "{kb_id}"'
        else:
            filter_expr = None

        # 先以较低阈值取候选池 (top_k*5)，给关键词加分 + RRF 留空间
        # 基 embedding 可能略低于阈值 (如 0.40-0.52)，关键词命中能推过门槛
        try:
            candidates = self.vector_store.search(
                query_embedding=vec,
                top_k=self.settings.top_k * 5,
                threshold=self.settings.fallback_threshold,
                filter_expr=filter_expr,
            )
        except Exception as e:
            raise RuntimeError(f"向量检索失败: {e}") from e

        if not candidates:
            return []

        # 加权关键词加分: header_path + text 作为匹配目标
        # header_path 含标题/问题文本 (如 "Q2: 忘记密码怎么办？") → 提升 FAQ 类型匹配
        for c in candidates:
            match_target = c.get("header_path", "") + " " + c["text"]
            c["score"] = c["score"] + _keyword_score(query, match_target)

        # 加分后按正常阈值过滤 (关键词加分可能推过门槛)
        candidates = [c for c in candidates if c["score"] >= self.settings.similarity_threshold]

        if not candidates:
            return []

        # 按加分后 score 重排, 取 top_k
        candidates.sort(key=lambda c: c["score"], reverse=True)
        return candidates[: self.settings.top_k]

    def auto_route(self, query: str) -> str | None:
        """
        自动路由: 大候选池 → 关键词加分 → 阈值过滤 → 每 KB 最高分比较

        用每 KB 的最高分 chunk 代表该 KB 的匹配质量。
        避免大 KB (chunk 多) 靠数量优势淹没小 KB 的精准匹配。

        Args:
            query: 用户问题

        Returns:
            最佳知识库 ID, 或 None (无法确定时)
        """
        try:
            vec = self.embedder.embed_query(query)
            # 大候选池确保小 KB 的 chunk 不被挤出
            chunks = self.vector_store.search(
                query_embedding=vec,
                top_k=50,
                threshold=self.settings.fallback_threshold,
            )
        except Exception:
            return None

        if not chunks:
            return None

        # 加权关键词加分 (含 header_path)
        for c in chunks:
            match_target = c.get("header_path", "") + " " + c["text"]
            c["score"] = c["score"] + _keyword_score(query, match_target)

        # 按正常阈值过滤
        chunks = [c for c in chunks if c["score"] >= self.settings.similarity_threshold]
        if not chunks:
            return None

        # 每 KB 取最高分 → 返回最高分 KB
        # 即使 KB 只有 5 个 chunk，只要其中一个精准匹配就能胜出
        kb_best: dict[str, float] = {}
        for c in chunks:
            kid = c.get("kb_id", "")
            if kid:
                kb_best[kid] = max(kb_best.get(kid, 0), c["score"])

        if not kb_best:
            return None

        return max(kb_best, key=kb_best.get)

    def multi_search(self, query: str, kb_id: str | None = None) -> List[Dict]:
        """Multi-Query RRF 检索: 生成多个 query 变体 → 各自检索 → RRF 融合

        解决单 query 与文档措辞不匹配的语义 gap 问题。
        例如 "忘记登录密码了怎么办" 的变体 "忘记密码怎么办" 可精确匹配 FAQ Q2 header。

        Args:
            query: 用户问题
            kb_id: 可选的知识库 ID

        Returns:
            融合后按 RRF score 排序的 chunk 列表
        """
        variants = _expand_query_variants(query)
        if len(variants) <= 1:
            return self.search(query, kb_id=kb_id)

        # 每路独立检索
        all_results: list[list[Dict]] = []
        for v in variants:
            try:
                results = self.search(v, kb_id=kb_id)
                if results:
                    all_results.append(results)
            except Exception:
                continue

        if not all_results:
            return []

        if len(all_results) == 1:
            return all_results[0]

        # RRF 融合
        fused = _rrf_fuse(all_results)

        # 按 RRF score 排序 (已在 _rrf_fuse 中排好)，按正常阈值过滤
        fused = [c for c in fused if c.get("score", 0) >= self.settings.similarity_threshold]

        return fused[: self.settings.top_k]
