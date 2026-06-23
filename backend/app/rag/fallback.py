"""兜底话术管理"""
from typing import List, Dict


DEFAULT_FALLBACK_RESPONSE = (
    "抱歉，我目前的知识库中暂时没有找到与您问题相关的信息。"
    "建议您联系人工客服获取帮助，或换一种方式描述您的问题。"
)

FALLBACK_SOURCES: List[Dict] = []


def get_fallback_response() -> str:
    """返回兜底话术"""
    return DEFAULT_FALLBACK_RESPONSE


def get_fallback_sources() -> List[Dict]:
    """返回空引用列表"""
    return FALLBACK_SOURCES
