"""意图识别模块 — 关键词优先 + LLM 兜底"""
import logging
from openai import AsyncOpenAI
from app.config import get_settings
from app.utils.security import sanitize_for_prompt

logger = logging.getLogger(__name__)

# 产品咨询关键词
PRODUCT_KEYWORDS = [
    "功能", "版本", "价格", "费用", "多少钱", "怎么收费",
    "如何使用", "怎么用", "用法", "教程", "指南",
    "是什么", "有什么", "有哪些", "介绍", "说明",
    "支持", "能不能", "可以", "是否", "有没有",
    "产品", "服务", "平台", "系统", "软件",
    "最新", "新功能", "更新", "升级", "新版",
    "特性", "特点", "优势", "区别", "对比",
    "推荐", "建议", "哪个好", "怎么选",
    "配置", "部署", "安装", "接入", "集成",
    "试用", "演示", "案例", "客户", "合作",
    "上线", "发布", "规划", "路线图", "roadmap",
    "提供", "包含", "包括", "覆盖",
    "联系", "电话", "客服", "咨询", "帮助",
    "范围", "领域", "行业", "适用",
]

# 售后关键词
AFTERSALES_KEYWORDS = [
    "退换", "退货", "退款", "退钱", "退订",
    "维修", "保修", "故障", "坏了", "不工作",
    "有问题", "不好使", "不能用", "失效", "异常",
    "错误", "报错", "出错", "bug", "卡住",
    "换货", "更换", "换一个",
    "赔偿", "赔付", "补偿", "索赔",
    "质量", "缺陷", "瑕疵",
    "多久", "什么时候", "还没", "还没有",
    "发货", "物流", "快递", "收到",
    "订单", "取消", "修改", "变更",
    "恢复", "找回", "重置", "清除",
    "账号", "密码", "登录", "注册", "验证",
    "安全", "泄露", "被盗", "异常登录",
    "发票", "合同", "凭证", "记录",
    "投诉", "不满", "太差", "态度", "差评",
]

# 投诉关键词（更强负面信号）
COMPLAINT_KEYWORDS = [
    "投诉", "举报", "垃圾", "骗子", "骗人",
    "态度差", "态度恶劣", "服务差", "太烂",
    "要投诉", "维权", "消协", "12315",
    "赔偿", "欺诈", "虚假", "误导",
    "泄露隐私", "侵犯", "违法", "违规",
    "不满意", "太差", "差评",
]

# 闲聊关键词（强信号，优先匹配）
CHITCHAT_KEYWORDS = [
    "你好", "您好", "嗨", "哈喽", "hello", "hi ",
    "谢谢", "感谢", "不客气", "再见", "拜拜",
    "天气", "吃饭", "今天", "怎么样", "心情",
    "你是谁", "你叫什么", "你是机器人", "你有感情",
    "讲笑话", "唱歌", "聊天", "无聊", "好玩",
]

INTENT_SYSTEM_PROMPT = """你是客服意图分类器。严格判断用户意图属于以下哪个类别。只输出类别名,其他什么都不输出。

类别定义（含典型问法）:
- 产品咨询: 任何与产品/服务/平台/功能/版本/价格/使用方法/技术说明相关的问题。例如:"你们有什么产品"、"最新版本支持什么"、"怎么收费"、"能不能对接我们系统"
- 售后问题: 退换货/退款/维修/故障/报错/质量/物流/账号等使用中遇到的问题。例如:"退款申请"、"系统报错了"、"物流到哪了"、"密码忘记了"
- 投诉: 明确表达不满/愤怒/要投诉/要赔偿的负面情绪。例如:"我要投诉你们"、"太垃圾了"、"服务态度太差"
- 闲聊: 完全与产品/服务/业务无关的寒暄或闲聊。例如:"你好"、"今天天气不错"

注意:只要用户问题涉及产品、服务、功能、业务相关话题,就归为"产品咨询"或"售后问题",不要归为"闲聊"。"""


async def classify_intent(query: str) -> str:
    """关键词优先 → LLM 兜底（异步）

    Args:
        query: 用户输入的问题文本

    Returns:
        意图标签: "产品咨询" | "售后问题" | "投诉" | "闲聊"
    """
    # Sanitize for prompt safety
    query = sanitize_for_prompt(query)
    query_lower = query.lower().strip()

    # 1. 先匹配闲聊强信号（避免把"你好,请问..."判为售后）
    for kw in CHITCHAT_KEYWORDS:
        if kw in query_lower:
            # 纯闲聊 vs 闲聊+产品问题: 如果同时含产品/售后关键词,按后者判
            for pk in PRODUCT_KEYWORDS:
                if pk in query_lower:
                    return "产品咨询"
            for ak in AFTERSALES_KEYWORDS:
                if ak in query_lower:
                    return "售后问题"
            return "闲聊"

    # 2. 匹配投诉强信号
    for kw in COMPLAINT_KEYWORDS:
        if kw in query_lower:
            return "投诉"

    # 3. 匹配售后（优先于产品 — "产品有故障" 应该判售后）
    for kw in AFTERSALES_KEYWORDS:
        if kw in query_lower:
            return "售后问题"

    # 4. 匹配产品咨询
    for kw in PRODUCT_KEYWORDS:
        if kw in query_lower:
            return "产品咨询"

    # 5. 关键词未命中 → LLM
    settings = get_settings()
    if not settings.deepseek_api_key or settings.deepseek_api_key.startswith("your-"):
        return "闲聊"

    try:
        client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=settings.llm_timeout,
        )
        response = await client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            max_tokens=10,
            temperature=0,
        )
        tag = response.choices[0].message.content.strip()
        valid_tags = {"产品咨询", "售后问题", "投诉", "闲聊"}
        return tag if tag in valid_tags else "闲聊"
    except Exception:
        logger.warning("Intent LLM classification failed, falling back to 闲聊", exc_info=True)
        return "闲聊"


async def classify_intent_with_llm(query: str, llm_client: object | None = None) -> str:
    return await classify_intent(query)


def _keyword_classify(query: str) -> str:
    """关键词分类（投诉优先, 闲聊兜底）"""
    query_lower = query.lower().strip()
    # 投诉优先（强信号）
    for kw in COMPLAINT_KEYWORDS:
        if kw in query_lower:
            return "投诉"
    # 售后 > 产品（"产品有故障" 判售后）
    for kw in AFTERSALES_KEYWORDS:
        if kw in query_lower:
            return "售后问题"
    for kw in PRODUCT_KEYWORDS:
        if kw in query_lower:
            return "产品咨询"
    return "闲聊"
