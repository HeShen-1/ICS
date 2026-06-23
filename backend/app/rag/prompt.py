"""Prompt 拼装模块"""
from typing import List, Dict
from datetime import datetime


SYSTEM_PROMPT = """## 角色
你是智能客服助手，专门为用户解答产品相关问题。

## 核心规则（必须遵守）
1. 你只能根据下方【知识库内容】回答问题
2. 如果知识库中没有相关信息，必须回答："抱歉，我目前的知识库中暂未收录该信息"
3. 每条回答末尾必须标注引用来源：📚 参考：[文档名]

## 回答风格
- 简洁专业，先给出核心结论再展开说明
- 分点说明时使用有序列表
- 涉及流程时先概括再分步

## 知识库内容
{retrieved_chunks}

## 当前日期
{current_date}"""


def format_retrieved_chunks(chunks: List[Dict]) -> str:
    """格式化检索结果为 Prompt 可读文本"""
    if not chunks:
        return "（无相关知识库内容）"

    formatted = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source", "未知来源")
        text = chunk.get("text", "")
        score = chunk.get("score", 0)
        formatted.append(
            f"[来源 {i}: {source} (相关度: {score})]\n{text}"
        )
    return "\n\n---\n\n".join(formatted)


def build_messages(
    query: str,
    retrieved_chunks: List[Dict],
    history_messages: List[Dict] = None,
    max_history_rounds: int = 5,
) -> List[Dict]:
    """构建 LLM 消息列表"""
    chunks_text = format_retrieved_chunks(retrieved_chunks)

    system_content = SYSTEM_PROMPT.format(
        retrieved_chunks=chunks_text,
        current_date=datetime.now().strftime("%Y年%m月%d日"),
    )

    messages = [{"role": "system", "content": system_content}]

    if history_messages:
        max_messages = max_history_rounds * 2
        recent = history_messages[-max_messages:]
        messages.extend(recent)

    messages.append({"role": "user", "content": query})
    return messages
