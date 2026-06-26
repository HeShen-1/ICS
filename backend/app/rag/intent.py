"""意图识别模块 - 基于关键词的轻量分类器"""
from typing import Optional


INTENT_KEYWORDS = {
    "产品咨询": [
        "功能", "版本", "价格", "费用", "如何使用", "怎么用",
        "是什么", "有什么", "支持", "能不能", "可以", "介绍",
    ],
    "售后问题": [
        "退换", "退货", "退款", "维修", "保修", "故障", "坏了",
        "有问题", "不好使", "不能用", "错误", "报错", "换货",
    ],
    "投诉": [
        "投诉", "差评", "不满意", "太差", "态度", "客服", "举报", "垃圾",
    ],
}


def classify_intent(query: str) -> str:
    """根据关键词分类用户意图

    Args:
        query: 用户输入的问题文本

    Returns:
        意图标签: "产品咨询" | "售后问题" | "投诉" | "闲聊"
    """
    query_lower = query.lower().strip()
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in query_lower:
                return intent
    return "闲聊"


def classify_intent_with_llm(query: str, llm_client: Optional[object] = None) -> str:
    """使用 LLM 进行更精确的意图分类（可选，备用）

    Args:
        query: 用户输入的问题文本
        llm_client: LLM 客户端实例（暂未使用，保留扩展点）

    Returns:
        意图标签: 同 classify_intent
    """
    return classify_intent(query)  # fallback to keyword
