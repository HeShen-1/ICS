"""Prompt 拼装模块"""
from typing import List, Dict
from datetime import datetime
import re
from app.config import get_settings


SYSTEM_PROMPT = """## 角色
你是「{company_name}」智能助手，基于企业知识库为用户提供产品咨询、
售后支持、政策解答。仅依据【知识库内容】作答。

## 核心规则（必须遵守）
1. 根据【知识库内容】作答。即使信息不完整，也先提供已知内容，再说明局限
2. 仅当知识库完全没有相关内容时，回答"抱歉，暂未收录该信息，建议联系人工客服"
3. 禁止编造、推测、补充知识库外的任何信息
4. 禁止评价竞品、对比其他公司产品
5. 每条回答末尾必须标注引用：📚 参考：文档名1、文档名2

## 回答示例

用户: 退换货需要什么条件？
知识库: [退换货政策.txt] 客户在收到商品7天内可申请无理由退换...
回答:
商品支持7天无理由退换，需保持原包装完好。
流程：1. 联系客服申请 2. 寄回商品 3. 仓库验收后3个工作日内退款
📚 参考：退换货政策.txt
[追问] 超过7天还能退换吗？ | 退款多久到账？ | 换货流程有什么不同？

用户: 你们公司有什么产品？
知识库: [公司产品介绍.txt] ICS智能客服系统，新一代基于大语言模型的企业客服平台...
回答:
我们的核心产品是 ICS 智能客服系统，基于大语言模型和 RAG 技术，
为企业提供知识库问答、意图识别、多轮对话等能力。
主要功能：智能问答、知识库管理、数据分析看板、Agent 问题拆解。
📚 参考：公司产品介绍.txt
[追问] 系统如何部署？ | 支持哪些文件格式？ | 收费标准是什么？

## 回答结构
1. 先给 1-2 句核心结论
2. 展开细节（分点/步骤，每条 ≤3 行）
3. 末尾标注引用：📚 参考：文档名

## 追问引导
追问必须与当前回答紧密相关。格式: [追问] 问题1 | 问题2 | 问题3

## 知识库内容
{retrieved_chunks}

## 当前日期
{current_date}（用于判断内容时效性）"""

# 关键规则关键词（命中任一即标为关键规则 chunk）
CRITICAL_RULE_KEYWORDS = [
    "必须", "禁止", "不得", "有效期", "截止", "不超过",
    "最多", "最少", "起", "止", "严禁", "务必", "注意", "重要"
]
CRITICAL_RULE_PREFIX = "⚠️ 关键规则"
# 超过此数量时启用分层结构（关键规则 / 详细参考）
LAYERED_THRESHOLD = 8


def _estimate_tokens(text: str) -> int:
    """粗略估算 token 数：中文字符 ~1.3 tokens，英文单词 ~1 token"""
    chinese_chars = len(re.findall(r"[一-鿿]", text))
    other = len(text) - chinese_chars
    return int(chinese_chars * 1.3 + other * 0.3)


def _is_critical(text: str) -> bool:
    """检测 chunk 文本是否包含关键规则关键词"""
    for keyword in CRITICAL_RULE_KEYWORDS:
        if keyword in text:
            return True
    return False


def _dedup_chunks_by_source(chunks: List[Dict]) -> List[Dict]:
    """按文档来源去重：同一文档的多个 chunk 仅保留得分最高者。

    输入应按 score 降序排列，保证去重后保留的是最高分片段。
    输出保持首次出现顺序（即高分优先）。
    """
    if not chunks:
        return []
    seen: Dict[str, Dict] = {}
    for chunk in chunks:
        source = chunk.get("source", "未知来源")
        if source not in seen or chunk.get("score", 0) > seen[source].get("score", 0):
            seen[source] = chunk
    return list(seen.values())


def _format_single_chunk(
    chunk: Dict, index: int, max_chunk_chars: int, *, critical: bool = False
) -> str:
    """格式化单个 chunk，关键规则 chunk 附加前缀"""
    source = chunk.get("source", "未知来源")
    text = chunk.get("text", "")
    score = chunk.get("score", 0)
    truncated = text[:max_chunk_chars]
    if len(text) > max_chunk_chars:
        truncated += "..."
    prefix = f"{CRITICAL_RULE_PREFIX} " if critical else ""
    return f"{prefix}[来源 {index}: {source} (相关度: {score})]\n{truncated}"


def format_retrieved_chunks(chunks: List[Dict], max_chunk_chars: int = 800) -> str:
    """格式化检索结果为 Prompt 可读文本，对过长 chunk 进行截断。

    当 chunks 总数超过 LAYERED_THRESHOLD 时，采用分层结构：
    - 关键规则 chunk 聚拢为「⚠️ 关键规则（请严格遵守）」区块
    - 其余 chunk 归入「📋 详细参考」区块
    不论是否分层，关键规则 chunk 都会附加 CRITICAL_RULE_PREFIX 前缀。
    """
    if not chunks:
        return "（无相关知识库内容）"

    # 分类：关键规则 vs 普通
    critical_chunks = [c for c in chunks if _is_critical(c.get("text", ""))]
    normal_chunks = [c for c in chunks if not _is_critical(c.get("text", ""))]

    if len(chunks) > LAYERED_THRESHOLD:
        # 分层输出
        parts: List[str] = []
        if critical_chunks:
            parts.append("## ⚠️ 关键规则（请严格遵守）")
            for i, chunk in enumerate(critical_chunks, 1):
                parts.append(
                    _format_single_chunk(chunk, i, max_chunk_chars, critical=True)
                )
        if normal_chunks:
            parts.append("## 📋 详细参考")
            for i, chunk in enumerate(normal_chunks, 1):
                parts.append(
                    _format_single_chunk(chunk, i, max_chunk_chars, critical=False)
                )
        return "\n\n".join(parts)
    else:
        # 普通输出（关键 chunk 带前缀，保持原有顺序）
        formatted = []
        for i, chunk in enumerate(chunks, 1):
            is_crit = chunk in critical_chunks
            formatted.append(
                _format_single_chunk(chunk, i, max_chunk_chars, critical=is_crit)
            )
        return "\n\n---\n\n".join(formatted)


def build_messages(
    query: str,
    retrieved_chunks: List[Dict],
    history_messages: List[Dict] = None,
    max_history_rounds: int = 5,
) -> List[Dict]:
    """构建 LLM 消息列表，含上下文窗口截断与大检索量保障。

    处理流程：
    1. 按文档来源去重（同一文档仅保留最高分 chunk）
    2. 识别关键规则 chunk（含 必须/禁止/不得 等关键词）
    3. 按 token 预算选取：关键规则优先，非关键 chunk 在预算不足时先丢弃
    4. 超过 LAYERED_THRESHOLD 条时采用分层结构输出
    """
    settings = get_settings()

    # 1. 按 score 降序排列
    sorted_chunks = sorted(
        retrieved_chunks, key=lambda c: c.get("score", 0), reverse=True
    )

    # 2. 先分类（关键规则 vs 普通），再各自去重，避免关键片段被高分普通片段覆盖
    critical_candidates = [c for c in sorted_chunks if _is_critical(c.get("text", ""))]
    normal_candidates = [c for c in sorted_chunks if not _is_critical(c.get("text", ""))]
    critical_chunks = _dedup_chunks_by_source(critical_candidates)
    normal_chunks = _dedup_chunks_by_source(normal_candidates)

    # 3. 预估算 token 基数
    system_content = SYSTEM_PROMPT.format(
        retrieved_chunks="{retrieved_chunks}",
        current_date=datetime.now().strftime("%Y年%m月%d日"),
        company_name=settings.company_name,
    )
    base_tokens = _estimate_tokens(system_content) + _estimate_tokens(query)
    available_budget = settings.max_context_tokens - base_tokens

    # 4. 按 token 预算选取：关键规则优先，非关键在预算不足时先丢弃
    #    使用运行计数器代替每轮 sum() — O(n) 代替 O(n²)
    selected_chunks: List[Dict] = []
    current_tokens = 0

    for chunk in critical_chunks:
        chunk_tokens = _estimate_tokens(chunk.get("text", ""))
        if current_tokens + chunk_tokens > available_budget:
            break
        selected_chunks.append(chunk)
        current_tokens += chunk_tokens

    for chunk in normal_chunks:
        chunk_tokens = _estimate_tokens(chunk.get("text", ""))
        if current_tokens + chunk_tokens > available_budget:
            break
        selected_chunks.append(chunk)
        current_tokens += chunk_tokens

    # 6. 格式化（内部处理分层结构）
    chunks_text = format_retrieved_chunks(selected_chunks)

    system_content = SYSTEM_PROMPT.format(
        retrieved_chunks=chunks_text,
        current_date=datetime.now().strftime("%Y年%m月%d日"),
        company_name=settings.company_name,
    )

    messages: List[Dict] = [{"role": "system", "content": system_content}]

    if history_messages:
        max_messages = max_history_rounds * 2
        recent = history_messages[-max_messages:]
        messages.extend(recent)

    messages.append({"role": "user", "content": query})
    return messages
