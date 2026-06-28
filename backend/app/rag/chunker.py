"""文档分块模块

策略 (方案 C — 混合分块 + Q&A 保护):
1. 解析 Markdown 标题结构 (##/###) → 构建标题路径
2. 每个 section 作为候选块:
   - Q&A 模式 (Q数字:|问：) → 强制独立成块，不与其他 section 合并
   - ≤ max_size → 直接作为一个 chunk
   - > max_size → 在段落边界 (\\n\\n > \\n > 。！？) 切分
3. header_path 存入 metadata，不拼入 chunk text（保持 embedding 精度）
4. 代码块 (```...```) 完整性保护, 不切断
5. chunk_size 按文档类型自适应:
   - FAQ / 问答: 256 (保证每个 Q&A 独立)
   - 政策 / 协议 / 条款: 1000
   - 技术 / 说明 / 介绍: 1200
   - 默认: 1000
"""
from typing import List, Dict
import re


class TextChunker:
    """文本分块器 — Markdown 语义感知 + Q&A 保护"""

    # 文档类型 → 推荐 chunk_size
    _TYPE_SIZES = {
        "faq": 256,      # Q&A 对独立成块
        "policy": 400,   # 政策/协议 — 每 1-2 个 section 一块
        "tech": 600,     # 技术文档
        "default": 600,  # 通用
    }

    # Q&A 模式: Q1:, Q2:, 问：, 答：
    _QA_PATTERN = re.compile(r"^(?:Q\d+\s*[：:]|问\s*[：:]|答\s*[：:])", re.IGNORECASE)

    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None):
        """
        Args:
            chunk_size: 分块最大字符数。None 时按文档类型自动选择
            chunk_overlap: 重叠字符数。None 时自动取 chunk_size 的 15%
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        if chunk_size is not None and chunk_overlap is not None:
            if chunk_overlap > chunk_size // 2:
                raise ValueError(
                    f"chunk_overlap ({chunk_overlap}) must be at most half "
                    f"of chunk_size ({chunk_size}), got {chunk_overlap} > {chunk_size // 2}"
                )

    # ── 公共入口 ──────────────────────────────────────

    def chunk(self, text: str, metadata: Dict[str, str] | None = None) -> List[Dict]:
        """
        将文本切分为带 metadata 的 chunk 列表。
        header_path 存入 metadata，不污染 chunk text。

        Args:
            text: 原始文本
            metadata: 附加信息（至少含 source 字段用于类型检测）

        Returns:
            [{text: "片段内容", metadata: {source, chunk_index, char_count, header_path}}, ...]
        """
        if not text or not text.strip():
            return []

        meta = metadata or {}
        source = meta.get("source", "")

        # 确定参数
        chunk_size = self.chunk_size if self.chunk_size is not None else self._detect_size(source)
        overlap = (
            self.chunk_overlap
            if self.chunk_overlap is not None
            else int(chunk_size * 0.15)
        )

        if overlap > chunk_size // 2:
            raise ValueError(
                f"chunk_overlap ({overlap}) must be at most half "
                f"of chunk_size ({chunk_size}), got {overlap} > {chunk_size // 2}"
            )

        # 1. 解析 Markdown 结构 → [(header_path, section_text), ...]
        sections = self._parse_sections(text)

        # 2. 每 section 生成 chunk candidates
        raw_chunks: List[Dict] = []  # [{header_path, text, is_qa}, ...]
        for header_path, section_text in sections:
            if not section_text.strip():
                continue
            is_qa = bool(self._QA_PATTERN.search(section_text))
            if len(section_text) <= chunk_size:
                raw_chunks.append({
                    "header_path": header_path,
                    "text": section_text.strip(),
                    "is_qa": is_qa,
                })
            else:
                for sub_text in self._split_section_text(header_path, section_text, chunk_size):
                    raw_chunks.append({
                        "header_path": header_path,
                        "text": sub_text,
                        "is_qa": is_qa,
                    })

        # 3. 轻量重叠：仅同 section 连续子块间共享 1 句上下文
        final_chunks = self._apply_overlap(raw_chunks, overlap)

        # 4. 组装输出 — header_path 进 metadata, text 保持纯净
        return [
            {
                "text": c["text"].strip(),
                "metadata": {
                    **meta,
                    "chunk_index": i,
                    "char_count": len(c["text"].strip()),
                    "header_path": c.get("header_path", ""),
                },
            }
            for i, c in enumerate(final_chunks)
            if c["text"].strip()
        ]

    # ── 文档类型检测 ─────────────────────────────────

    def _detect_size(self, filename: str) -> int:
        """根据文件名关键词推断文档类型"""
        name_lower = filename.lower()
        if any(k in name_lower for k in ("faq", "常见问题", "问答", "q&a")):
            return self._TYPE_SIZES["faq"]
        if any(k in name_lower for k in ("政策", "协议", "条款", "隐私", "法律", "policy", "agreement")):
            return self._TYPE_SIZES["policy"]
        if any(
            k in name_lower
            for k in ("技术", "说明", "介绍", "指南", "开发", "api", "tech", "guide")
        ):
            return self._TYPE_SIZES["tech"]
        return self._TYPE_SIZES["default"]

    # ── Markdown 结构解析 ─────────────────────────────

    @staticmethod
    def _parse_sections(text: str) -> List[tuple]:
        """
        按 ## / ### / #### 标题拆分为 sections。
        返回 [(header_path, content), ...]
        header_path 示例: "常见问题 > 账号相关 > 如何注册"
        """
        heading_re = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)

        headings: List[tuple] = []  # (start, end, level, title)
        for m in heading_re.finditer(text):
            level = len(m.group(1))
            title = m.group(2).strip()
            headings.append((m.start(), m.end(), level, title))

        if not headings:
            return [("", text)]

        sections = []

        # 标题前的导言
        if headings[0][0] > 0:
            pre = text[: headings[0][0]].strip()
            if pre:
                sections.append(("", pre))

        # 标题栈: [H1, H2, H3, H4]
        stack = [""] * 4

        for i, (start, end, level, title) in enumerate(headings):
            idx = level - 1
            stack[idx] = title
            for j in range(idx + 1, 4):
                stack[j] = ""

            path_parts = [h for h in stack if h]
            header_path = " > ".join(path_parts)

            content_start = end
            content_end = headings[i + 1][0] if i + 1 < len(headings) else len(text)
            content = text[content_start:content_end].strip()

            if content:
                sections.append((header_path, content))

        return sections

    # ── 长 section 段落级切分 ──────────────────────────

    def _split_section_text(
        self, header_path: str, text: str, max_size: int
    ) -> List[str]:
        """对超过 max_size 的 section 在段落边界切分, 不重叠"""
        chunks: List[str] = []
        remaining = text

        while remaining.strip():
            if len(remaining) <= max_size:
                chunks.append(remaining.strip())
                break

            split_at = self._find_split_point(remaining, max_size)

            chunk_text = remaining[:split_at].strip()
            if chunk_text:
                chunks.append(chunk_text)

            remaining = remaining[split_at:]

        return chunks

    def _find_split_point(self, text: str, max_size: int) -> int:
        """
        在 [max_size*0.5, max_size] 区间找最佳段落边界。
        优先级: \\n\\n > \\n > 。！？； > max_size 硬切
        """
        window = text[:max_size]
        min_bound = max_size // 2

        # 跳过代码块内部
        code_fence = self._find_fence_boundary(window, min_bound)
        if code_fence is not None:
            return code_fence

        # 1. 双换行（段落边界）
        pos = window.rfind("\n\n", min_bound)
        if pos > 0:
            return pos + 2

        # 2. 单换行
        pos = window.rfind("\n", min_bound)
        if pos > 0:
            return pos + 1

        # 3. 句子结束标点
        for sep in ("。", "！", "？", "；"):
            pos = window.rfind(sep, min_bound)
            if pos > 0:
                return pos + 1

        # 4. 硬切
        return max_size

    @staticmethod
    def _find_fence_boundary(window: str, min_bound: int) -> int | None:
        fences = [m.start() for m in re.finditer(r"^```", window, re.MULTILINE)]
        if len(fences) % 2 == 1:
            last_fence = fences[-1]
            if last_fence > min_bound:
                return last_fence
        return None

    # ── 重叠处理 ──────────────────────────────────────

    @staticmethod
    def _apply_overlap(raw_chunks: List[Dict], overlap: int) -> List[Dict]:
        """仅在同 section 连续子块间加 1 句上下文衔接, 不同 section 间不重叠"""
        if not raw_chunks:
            return []

        result = [dict(raw_chunks[0])]
        for i in range(1, len(raw_chunks)):
            prev = raw_chunks[i - 1]
            curr = dict(raw_chunks[i])

            same_section = prev["header_path"] == curr["header_path"]
            if not same_section or overlap <= 0 or len(prev["text"]) <= overlap:
                result.append(curr)
                continue

            # 取上一块末尾 ~overlap 字符, 找最后一个完整句子
            tail = prev["text"][-overlap:]
            best = 0
            for sep in ("\n\n", "\n", "。", "！", "？"):
                pos = tail.rfind(sep)
                if pos > best:
                    best = pos + len(sep)
            context = tail[best:].strip() if best > 0 else ""

            if context:
                curr["text"] = f"(上文续)\n{context}\n---\n{curr['text']}"

            result.append(curr)

        return result

    # ── 旧 API 兼容（供测试） ──────────────────────────

    @staticmethod
    def _split_paragraphs(text: str) -> List[str]:
        """按段落分割，保留旧接口"""
        if not text or not text.strip():
            return []
        parts = re.split(r"\n\s*\n", text)
        result = []
        for part in parts:
            lines = part.split("\n")
            result.extend(line.strip() for line in lines if line.strip())
        return result

    @staticmethod
    def _merge_and_split(paragraphs: List[str]) -> List[str]:
        """旧接口兼容 — 已不参与核心逻辑"""
        return paragraphs
