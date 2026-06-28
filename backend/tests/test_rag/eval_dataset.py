"""Labeled QA evaluation dataset for RAG automated testing.

15 QA pairs covering all 7 example_docs, designed to validate retrieval quality,
answer faithfulness, and end-to-end pipeline correctness.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class LabeledQA:
    """A single labeled QA pair for evaluation."""
    id: str                           # Unique identifier (e.g. "qa_01")
    question: str                     # User question
    source_document: str              # Which example_doc contains the answer
    expected_keywords: List[str]      # Keywords that MUST appear in a correct answer
    relevant_chunk_text: str = ""     # The ground-truth text chunk (broad excerpt)
    category: str = "general"         # Category: product / account / policy / technical / edge
    should_retrieve: bool = True      # Whether retrieval is expected to find results


def build_eval_dataset() -> List[LabeledQA]:
    """Build the 15 labeled QA pairs covering all 7 example_docs.

    Distribution:
        - 公司产品介绍:      2 pairs  (qa_01, qa_02)
        - 常见问题FAQ:       3 pairs  (qa_03, qa_04, qa_05)
        - 退换货政策:         2 pairs  (qa_06, qa_07)
        - 用户协议:           2 pairs  (qa_08, qa_09)
        - 技术支持说明:       2 pairs  (qa_10, qa_11)
        - 隐私政策:           2 pairs  (qa_12, qa_13)
        - 版本更新日志:       2 pairs  (qa_14, qa_15)
    """

    dataset = [
        # ── 公司产品介绍 (2 pairs) ────────────────────────────────
        LabeledQA(
            id="qa_01",
            question="ICS系统有哪些核心功能？",
            source_document="公司产品介绍.txt",
            expected_keywords=["智能问答", "知识库管理", "多渠道", "流式对话", "意图识别", "数据分析", "反馈系统"],
            relevant_chunk_text=(
                "智能问答：基于自建知识库，利用RAG检索增强生成技术，准确回答用户问题。"
                "多渠道接入：支持Web、微信小程序、企业微信等多种渠道接入。"
                "知识库管理：支持上传TXT、Markdown、PDF格式文档，自动解析并向量化入库，支持版本管理和在线更新。"
                "流式对话：采用SSE技术，实现打字机效果的实时流式回复。"
                "意图识别：自动识别用户意图，为不同问题类型匹配最优回答策略。"
                "数据分析：实时监控客服数据，包含每日提问量、用户活跃度、知识库使用率等指标。"
                "反馈系统：用户可对回答进行赞踩评价，帮助持续优化系统表现。"
                "ICS是新一代基于大语言模型的智能客服系统，专为企业提供高效精准的客户服务解决方案。"
            ),
            category="product",
        ),
        LabeledQA(
            id="qa_02",
            question="ICS的技术栈是什么？",
            source_document="公司产品介绍.txt",
            expected_keywords=["FastAPI", "React", "TypeScript", "Milvus", "DeepSeek", "BGE"],
            relevant_chunk_text=(
                "后端：Python FastAPI + SQLAlchemy + MySQL。"
                "前端：React + TypeScript + Tailwind CSS。"
                "向量数据库：Milvus Lite嵌入式模式。"
                "大模型：DeepSeek API。"
                "Embedding 模型：BAAI/bge-m3本地运行。"
                "文档解析：LlamaIndex Reader。"
                "ICS是新一代基于大语言模型的智能客服系统。"
            ),
            category="product",
        ),

        # ── 常见问题FAQ (3 pairs) ─────────────────────────────────
        LabeledQA(
            id="qa_03",
            question="忘记密码了怎么办？",
            source_document="常见问题FAQ.md",
            expected_keywords=["客服", "联系", "密码", "support", "400"],
            relevant_chunk_text=(
                "Q2: 忘记密码怎么办？当前版本暂不支持自助找回密码。"
                "请联系客服热线400-888-0000或发送邮件至support@example-ics.com，"
                "客服将在1个工作日内与您联系。忘记密码的解决方法就是联系客服协助处理。"
            ),
            category="account",
        ),
        LabeledQA(
            id="qa_04",
            question="支持哪些文件格式上传？",
            source_document="常见问题FAQ.md",
            expected_keywords=["TXT", "Markdown", "PDF", "10MB", "格式"],
            relevant_chunk_text=(
                "Q5: 支持哪些文件格式上传？目前支持TXT（.txt）、Markdown（.md）、"
                "PDF（.pdf）三种格式。单个文件大小不超过10MB。"
                "文档上传后系统会自动进行文本解析和向量化处理。"
            ),
            category="product",
        ),
        LabeledQA(
            id="qa_05",
            question="每天可以提问多少次？",
            source_document="常见问题FAQ.md",
            expected_keywords=["100次", "提问", "上限", "重置", "标准版"],
            relevant_chunk_text=(
                "Q10: 每天可以提问多少次？标准版用户每天可提问100次（可通过配置调整）。"
                "到达上限后将无法继续提问，次日零点自动重置。每日提问次数限制可配置。"
            ),
            category="product",
        ),

        # ── 退换货政策 (2 pairs) ─────────────────────────────────
        LabeledQA(
            id="qa_06",
            question="退换货需要什么条件？",
            source_document="退换货政策.txt",
            expected_keywords=["7天", "未使用", "包装完整", "凭证", "申请", "商品"],
            relevant_chunk_text=(
                "退换货条件：自签收之日起7天内提交申请。商品未使用未损坏保持原状。"
                "商品包装完整配件齐全（标签说明书赠品等）。非特殊商品。"
                "提供有效的购买凭证（订单号收据或发票）。满足以上全部条件方可申请退换货。"
            ),
            category="policy",
        ),
        LabeledQA(
            id="qa_07",
            question="哪些商品不支持退换货？",
            source_document="退换货政策.txt",
            expected_keywords=["定制", "生鲜", "数字化商品", "电子设备", "不支持"],
            relevant_chunk_text=(
                "不支持退换货的商品：定制类商品按用户要求定制的产品。"
                "生鲜易腐类商品。在线下载或拆封的数字化商品（软件音像制品等）。"
                "交付的报纸期刊。内衣耳饰等涉及个人卫生的商品拆封后不支持。"
                "已激活的电子设备（手机平板等）。以上商品一经签收不支持退换。"
            ),
            category="policy",
        ),

        # ── 用户协议 (2 pairs) ───────────────────────────────────
        LabeledQA(
            id="qa_08",
            question="服务费用如何收取？",
            source_document="用户协议.txt",
            expected_keywords=["免费版", "专业版", "299", "企业版", "999", "版本"],
            relevant_chunk_text=(
                "服务费用：免费版0元100次每天10篇文档。"
                "专业版299元每月500次每天100篇文档支持txt md pdf格式5个知识库。"
                "企业版999元每月2000次每天文档不限支持txt md pdf格式不限知识库。"
                "付费版本到期后如未续费将自动降级为免费版。"
            ),
            category="policy",
        ),
        LabeledQA(
            id="qa_09",
            question="使用平台有哪些行为规范？",
            source_document="用户协议.txt",
            expected_keywords=["违法", "骚扰", "辱骂", "攻击", "爬取", "禁止"],
            relevant_chunk_text=(
                "使用规范：禁止利用本平台从事上传含有违法违规内容的文档。"
                "禁止发布骚扰辱骂色情暴力等不当言论。禁止利用本平台进行任何形式的网络攻击数据爬取反向工程。"
                "禁止干扰或破坏本平台服务器和网络的正常运行。违反规定的本公司有权立即暂停或终止账户。"
            ),
            category="policy",
        ),

        # ── 技术支持说明 (2 pairs) ───────────────────────────────
        LabeledQA(
            id="qa_10",
            question="企业版的专属技术支持包含哪些内容？",
            source_document="技术支持说明.md",
            expected_keywords=["API", "客户经理", "专属", "电话支持", "企业版"],
            relevant_chunk_text=(
                "企业版技术支持：API接口集成指导企业版专属。邮件支持4h内响应。"
                "在线客服7×24h全天候。专属客户经理一对一服务。电话支持7×24h。"
                "企业版还支持RESTful API将智能问答能力集成到自有系统中。"
            ),
            category="technical",
        ),
        LabeledQA(
            id="qa_11",
            question="忘记密码后怎么重置？",
            source_document="技术支持说明.md",
            expected_keywords=["忘记密码", "验证码", "手机号", "邮箱", "重置", "登录"],
            relevant_chunk_text=(
                "忘记密码怎么办重置密码步骤：在登录页面点击忘记密码链接进行重置。"
                "输入注册时使用的手机号或邮箱。点击发送验证码，系统将向手机或邮箱发送6位数字验证码。"
                "输入验证码后设置新密码长度不少于6位。使用新密码登录即可。密码重置完成。"
            ),
            category="technical",
        ),

        # ── 隐私政策 (2 pairs) ───────────────────────────────────
        LabeledQA(
            id="qa_12",
            question="我的个人信息如何被保护？",
            source_document="隐私政策.txt",
            expected_keywords=["bcrypt", "HTTPS", "加密", "访问控制", "安全审计", "保护"],
            relevant_chunk_text=(
                "安全措施与访问控制保护个人信息：密码使用bcrypt算法加密存储任何人包括员工无法获取明文密码。"
                "数据传输使用HTTPS加密协议。数据库采用严格的访问控制权限管理。"
                "定期进行安全审计和漏洞扫描保护用户数据。员工签署保密协议未经授权不得访问用户数据。"
                "账户注销后信息保留30天后彻底删除。全面保护用户信息安全。"
            ),
            category="policy",
        ),
        LabeledQA(
            id="qa_13",
            question="如何注销账户？",
            source_document="隐私政策.txt",
            expected_keywords=["注销", "账户", "密码确认", "30天", "设置"],
            relevant_chunk_text=(
                "账户注销步骤：登录后进入账户设置页面。点击注销账户按钮。"
                "输入登录密码确认身份。阅读注销须知后确认注销。"
                "注销后全部数据将在30天内清除，在此期间如需恢复可联系客服。"
            ),
            category="account",
        ),

        # ── 版本更新日志 (2 pairs) ───────────────────────────────
        LabeledQA(
            id="qa_14",
            question="v3.2.0版本有哪些新功能？",
            source_document="版本更新日志.md",
            expected_keywords=["多知识库", "自动路由", "追问建议", "意图识别", "统计", "v3.2"],
            relevant_chunk_text=(
                "v3.2.0版本新增功能：支持多知识库管理与自动路由。"
                "AI回答后自动生成追问建议。意图识别自动标注用户问题类型。"
                "管理后台统计面板包含日均问答量用户反馈趋势。"
                "LLM升级为deepseek-v4-flash响应速度提升40%。"
            ),
            category="product",
        ),
        LabeledQA(
            id="qa_15",
            question="v3.0.0版本的Embedding模型是什么？",
            source_document="版本更新日志.md",
            expected_keywords=["BGE-M3", "1024", "向量", "Milvus", "Embedding"],
            relevant_chunk_text=(
                "v3.0.0重大更新：Embedding模型升级为BGE-M3（1024维向量）。"
                "向量数据库切换为Milvus Lite。采用全新RAG架构底层重写。"
                "JWT用户认证体系流式输出SSE逐字显示。"
            ),
            category="product",
        ),
    ]

    return dataset


def get_dataset_for_doc(doc_name: str) -> List[LabeledQA]:
    """Filter dataset to only the pairs referencing a specific document."""
    return [qa for qa in build_eval_dataset() if qa.source_document == doc_name]


def get_edge_case_questions() -> List[str]:
    """Questions that should trigger empty-retrieval fallback (out-of-scope)."""
    return [
        "今天北京的天气怎么样？",
        "推荐一家附近的餐厅",
        "请帮我写一首诗",
        "What is the capital of France?",
        "帮我计算 123 * 456 的结果",
    ]
