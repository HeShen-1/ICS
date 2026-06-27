# AI 架构设计

> AI 智能客服系统 v1.0 | RAG 流程图 + Prompt 模板 + 向量检索策略

## 1. RAG 完整流程图

```mermaid
flowchart TD
    A[用户输入问题] --> B{输入校验}
    B -->|超过500字| B1[返回错误: 问题过长]
    B -->|超过每日100次| B2[返回错误: 次数超限]
    B -->|通过| C[保存用户消息到 MySQL]

    C --> C_INTENT[意图识别: 关键词分类器]
    C_INTENT --> C_TAG[标注 intent_tag: 产品咨询/售后/闲聊/投诉]

    C_TAG --> K{知识库路由}
    K -->|请求体含 kb_id| K1[使用指定知识库]
    K -->|未指定 kb_id| K2[多知识库投票路由]
    K1 --> D
    K2 --> D

    D[向量检索阶段]
    D --> D1[BGE-M3 将问题转为 1024维向量]
    D1 --> D2[Milvus 向量相似度搜索 + kb_id 过滤]
    D2 --> D3{检索结果判断}

    D3 -->|所有片段 score < 0.55| E1[返回兜底话术]
    E1 --> E1a[保存兜底回答到 MySQL]
    E1a --> Z[结束]

    D3 -->|有score ≥ 0.55的片段| F[Prompt 拼装阶段]
    F --> F1[格式化检索片段: 来源标注 + 内容]
    F1 --> F2[获取历史对话: 最近5轮]
    F2 --> F3[拼接 System Prompt + 历史 + 知识 + 问题]
    F3 --> F4{Token 预算检查}

    F4 -->|超8000 tokens| F5[分层截断]
    F5 --> F5a[低分片段优先丢弃]
    F5a --> F5b[远端历史丢弃]
    F5b --> F5c[句子级截断]
    F5c --> F4

    F4 -->|通过| G[LLM 调用阶段]
    G --> G1[DeepSeek API chat.completions.create]
    G1 --> G1a[stream=True, temperature=0.3]
    G1a --> G2{调用成功?}

    G2 -->|超时/限流| G3[重试: 最多3次]
    G3 --> G3a[指数退避: 1s→2s→4s]
    G3a --> G1

    G2 -->|成功| H[SSE 流式输出阶段]
    H --> H1[event: token 逐字推送]
    H1 --> H2[LLM 输出完成]
    H2 --> H3[event: followup 追问建议]
    H3 --> H4[event: sources 引用来源]
    H4 --> H5[event: done 流结束]
    H5 --> I[保存 AI 回答到 MySQL]
    I --> Z[结束]
```

## 2. Prompt 模板设计

### 2.1 System Prompt（完整版）

```
## 角色
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
知识库: [公司产品介绍.txt] ICS智能客服系统...
回答:
我们的核心产品是 ICS 智能客服系统，基于大语言模型和 RAG 技术...
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
{current_date}（用于判断内容时效性）
```

### 2.2 Prompt 设计思路

| 设计点 | 具体做法 | 目的 |
|--------|----------|------|
| **角色定义** | 使用 `{company_name}` 占位符，运行时注入配置值 | 支持多租户/白标部署 |
| **规则约束** | 5 条硬规则（含禁止编造、禁止评价竞品、来源强制标注） | 从 Prompt 层面抑制幻觉和不当回答 |
| **Few-shot 示例** | 内置 3 组问答示例（退换货/产品介绍/FAQ），含 [追问] 格式 | 引导 LLM 输出结构和追问生成 |
| **否定式指令** | "禁止编造"比"尽量准确"更强硬 | 减少幻觉发生概率 |
| **来源标注** | 格式固定为 📚 参考：文档名 | 使回答可追溯、可验证 |
| **回答结构** | 三步法：核心结论→细节展开→引用来源 | 确保回答信息密度和可读性 |
| **追问引导** | LLM 生成 [追问] 标签，后端解析为 followup SSE 事件 | 引导用户深入探索，减少客服压力 |
| **当前日期** | 注入真实日期 `{current_date}` | 处理"7天内退换货"等时效性问题 |
| **temperature=0.3** | 低温度参数 | 确保回答一致性和准确性 |
| **分层输出** | >8 条检索结果时，分为「⚠️ 关键规则」+「详细参考」两层 | 防止 LLM 注意力稀释，确保关键规则不被遗漏 |

### 2.3 检索片段格式化

```python
def format_retrieved_chunks(chunks: List[Dict], max_chunk_chars: int = 800) -> str:
    """将检索结果格式化为 LLM 可读文本，支持分层输出和截断。

    当 chunks > LAYERED_THRESHOLD(8) 时，启用分层结构：
    - ## ⚠️ 关键规则（请严格遵守）← 含 必须/禁止/不得 等关键词的片段
    - ## 📋 详细参考 ← 其余普通片段
    每个 chunk 超过 max_chunk_chars 时截断并追加 "..."
    """
    for c in chunks:
        if len(c["text"]) > max_chunk_chars:
            c["text"] = c["text"][:max_chunk_chars] + "..."

    if len(chunks) <= LAYERED_THRESHOLD:
        # 少于阈值：直接按来源编号列出
        return "\n\n---\n\n".join(
            f"[来源 {i}: {c['source']} (相关度: {c['score']:.2f})]\n{c['text']}"
            for i, c in enumerate(chunks, 1)
        )

    # 分层输出
    critical = [c for c in chunks if _is_critical(c["text"])]
    normal = [c for c in chunks if not _is_critical(c["text"])]
    # 输出 "⚠️ 关键规则" + "📋 详细参考" 两层结构
```

### 2.4 多轮对话上下文与 Token 预算控制

```python
def build_messages(query, retrieved_chunks, history_messages, max_history_rounds=5):
    """构建 LLM 消息列表，含完整 token 预算控制。

    处理流程：
    1. 按 score 降序排列 + 先分类(关键/普通)再各自去重
    2. 按 token 预算（max_context_tokens - system_prompt - query）选取：
       关键规则优先，普通片段在预算不足时先丢弃
    3. 历史对话只保留最近 N 轮
    4. 动态注入 {company_name}、{current_date}、{retrieved_chunks}
    """
    settings = get_settings()

    # 分类 → 各自去重 → token 预算选取（关键优先）
    sorted_chunks = sorted(retrieved_chunks, key=lambda c: c.get("score", 0), reverse=True)
    critical = _dedup_chunks_by_source([c for c in sorted_chunks if _is_critical(c["text"])])
    normal = _dedup_chunks_by_source([c for c in sorted_chunks if not _is_critical(c["text"])])

    # 运行计数器（O(n)）选取，关键规则优先
    selected, tokens = [], 0
    for chunk in critical + normal:
        ct = _estimate_tokens(chunk["text"])
        if tokens + ct > available_budget: break
        selected.append(chunk); tokens += ct

    chunks_text = format_retrieved_chunks(selected)
    system_content = SYSTEM_PROMPT.format(
        retrieved_chunks=chunks_text,
        current_date=datetime.now().strftime("%Y年%m月%d日"),
        company_name=settings.company_name,
    )

    messages = [{"role": "system", "content": system_content}]
    if history_messages:
        messages.extend(history_messages[-(max_history_rounds * 2):])
    messages.append({"role": "user", "content": query})
    return messages
```

## 3. 向量检索策略

### 3.1 检索参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| Top-K | 12 | 返回相似度最高的 12 个片段（配合关键词重排序，实际有效 3-5 条） |
| 相似度阈值 | 0.55 | 低于此值的片段丢弃 |
| 相似度度量 | COSINE | 余弦相似度（BGE-M3 推荐） |
| Embedding 维度 | 1024 | BGE-M3 输出维度 |

### 3.2 Top-K=12 的选择理由

- **太小（如 5）**：可能遗漏跨文档的相关片段，回答覆盖面不足
- **太大（如 30）**：可能混入噪声，增加 Token 消耗，稀释 LLM 注意力
- **12 条**：配合关键词重排序（keyword boost），在召回率和精准度之间平衡。通过相似度阈值（0.55）和去重后，实际有效片段通常为 3-8 条。代码中以 top_k * 2 = 24 候选再重排序实现

### 3.3 相似度阈值 0.55 的选择理由

- BGE-M3 的 COSINE 相似度范围是 [-1, 1]（归一化后为 [0, 1]）
- 0.55：通过测试确定的经验阈值，配合三层降级检索策略：
  - 高于 0.55：通常为真实相关内容
  - 0.35-0.55：边缘相关（可能有主题词重叠但语义不匹配），三层兜底时降至 0.35 再尝试
  - 低于 0.35：基本不相关
- 阈值可配置（`.env` 中 `SIMILARITY_THRESHOLD` + `FALLBACK_THRESHOLD`），不同业务场景可调整

### 3.4 BGE-M3 Embedding 使用说明

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-m3", device="cpu")

# 对文档片段（不需要前缀）
doc_embeddings = model.encode(documents, normalize_embeddings=True)

# 对查询（BGE 官方推荐：短查询不推荐加前缀，长查询可加）
# 本项目查询 ≤500 字，视为短查询，不加前缀
query_embedding = model.encode(query, normalize_embeddings=True)
```

> **注意**：早期 BGE 模型推荐查询加 `"Represent this sentence for searching relevant passages:"` 前缀，BGE-M3 对此不敏感。本项目统一不加前缀，保持简洁。

## 4. 文档分块策略

### 4.1 自适应分块参数

| 参数 | 值 | 说明 |
|------|-----|------|
| chunk_size | 按文档类型自适应 | FAQ=800, Policy=1000, Tech=1200, Default=1000 |
| chunk_overlap | chunk_size × 15% | 相邻 chunk 重叠部分 |

### 4.2 分块流程（Scheme C — 语义感知分块）

```
1. 识别 Markdown 标题层级（# → ## → ###），按标题切分大段
2. 如需进一步分割：按双换行(\\n\\n)分段落
3. 短段落合并：do {
     合并最短的相邻段落
   } while (最短合并后长度 < chunk_size × 0.7)
4. 长段落切分：滑动窗口按 chunk_size 切分，保留 overlap
5. 代码块保护：在代码块围栏处切分，避免破坏语法
6. 每个 chunk 附带 metadata: {source, chunk_index, char_count, kb_id}
```

### 4.3 选择自适应 chunk 的理由

- **FAQ 类文档（800）**：短问答，较小窗口确保精确匹配
- **政策类文档（1000）**：规则条款需保留上下文
- **技术类文档（1200）**：长段落需要更大窗口保持语义完整
- **重叠率 15%**：在召回率和计算量之间平衡，相比固定 50 更贴合文档长度

## 5. LLM 调用配置

```python
response = await client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    stream=True,           # 流式输出
    temperature=0.3,       # 低温度：减少随机性，提高准确性
    max_tokens=2048,       # 回答长度上限
    timeout=30,            # 超时秒数
)
```

**参数说明**：
- `stream=True`：启用 SSE 流式输出
- `temperature=0.3`：客服场景需要确定性回答，低温度减少随机性
- `max_tokens=2048`：客服回答通常 100-500 tokens，2048 留足余量
- `timeout=30`：DeepSeek 通常 1-3s 出首 token，30s 充足

## 6. 关键设计决策回顾

| 决策 | 选项 A | 选项 B | 最终选择 | 理由 |
|------|--------|--------|----------|------|
| 框架 | LangChain | 手动实现 | **手动实现** | 理解原理，精细控制 |
| LLM | OpenAI | DeepSeek | **DeepSeek** | 用户提供 Key |
| Embedding | 云端 API | 本地 BGE-M3 | **本地 BGE-M3** | 中文 SOTA，零成本 |
| 向量库 | Chroma | Milvus | **Milvus** | 用户指定 |
| 流式协议 | SSE | WebSocket | **SSE** | 单向数据流，更简单 |
| PDF 解析 | 手动写 | LlamaIndex | **LlamaIndex Reader** | 复用成熟方案 |

## 7. 意图识别

### 7.1 关键词优先 + LLM 兜底

意图识别采用**关键词优先 + LLM 兜底**的异步策略。关键词匹配覆盖 >100 个高频词，仅在未命中时调用 LLM。

```python
async def classify_intent(query: str) -> str:
    """关键词优先 → LLM 兜底（异步）"""
    # 1. 闲聊强信号优先匹配（避免"你好，请问..."误判）
    for kw in CHITCHAT_KEYWORDS:        # 你好、谢谢、再见 等 12 个
        if kw in query_lower:
            # 如同时含产品关键词 → 提升为产品咨询
            ...
            return "闲聊"

    # 2. 投诉强信号                          # 投诉、举报、态度差 等 16 个
    for kw in COMPLAINT_KEYWORDS: ... return "投诉"

    # 3. 售后（优先于产品 — "产品有故障"判售后）# 退货、退款、维修 等 32 个
    for kw in AFTERSALES_KEYWORDS: ... return "售后问题"

    # 4. 产品咨询                            # 功能、价格、如何 等 44 个
    for kw in PRODUCT_KEYWORDS: ... return "产品咨询"

    # 5. 关键词未命中 → AsyncOpenAI 兜底
    response = await client.chat.completions.create(
        model=settings.deepseek_model, messages=[INTENT_SYSTEM_PROMPT, ...],
        max_tokens=10, temperature=0,
    )
    return tag if tag in valid_tags else "闲聊"
```

### 7.2 设计思路

| 设计点 | 说明 |
|--------|------|
| 关键词优先 | >100 个关键词覆盖 95% 场景，零 API 调用延迟 |
| LLM 兜底 | 未命中时异步调用 DeepSeek 分类，4 类标签严格白名单 |
| 闲聊优先 | 避免"你好，请问 X"误判为售后/产品 |
| 故障透明 | LLM 分类失败时记录日志并降级为"闲聊" |
| intent_tag 标注 | 写入 messages.intent_tag，支持统计分析和差异化回答 |

## 8. 多知识库自动路由

### 8.1 路由策略

当用户未指定 `kb_id` 时，系统使用**kb_id 频次投票**策略：

```python
def auto_route(query: str) -> str | None:
    """全库检索 → 统计 kb_id 出现频次 → 返回多数派 kb_id"""
    # top_k=10 无过滤检索所有知识库
    chunks = self.vector_store.search(query_embedding, top_k=10, threshold=threshold)

    if not chunks:
        return None  # 无结果 → 降级到全局检索

    # 统计每个 kb_id 的出现次数
    kb_counts = Counter(c.get("kb_id", "") for c in chunks)
    return kb_counts.most_common(1)[0][0]  # 返回出现最多的 kb_id
```

### 8.2 路由执行流程

```
1. auto_route(query) → 全库检索 top_k=10
2. 统计 kb_id 频次 → 返回多数派 kb_id
3. 如用户已指定 kb_id → 跳过 auto_route，直接使用
4. 路由到的 kb_id → 第二轮精确检索（kb_id 过滤）
5. route 失败（无 kb_id 或无结果）→ 三层降级检索：
   Layer 1: kb_id 过滤检索 (threshold=0.55)
   Layer 2: 全局检索无过滤 (threshold=0.55)
   Layer 3: 降阈兜底 (threshold=0.35)
```

### 8.3 路由决策表

| 条件 | 行为 |
|------|------|
| 请求指定 `kb_id` | 直接使用该知识库检索 |
| 未指定 + 单知识库 | 直接检索该知识库 |
| 未指定 + 多知识库 | 投票路由选最优知识库 |
| 路由结果为空 | 返回兜底话术 |

## 9. AI Agent 任务拆解

### 9.1 功能概述

AI Agent 模块将自然语言需求拆解为微服务层面的改动分析任务列表。输入一段用户需求描述，输出结构化的排查/改动任务清单。

### 9.2 处理流程

```
用户需求文本
  → System Prompt: "你是软件架构分析专家..."
  → LLM 分析需求，关联微服务拓扑
  → 结构化输出：任务列表 (title, description, service, priority)
  → 返回 JSON
```

### 9.3 Prompt 设计

```
## 角色
你是软件架构分析专家，擅长将用户需求拆解为微服务层面的改动分析任务。

## 输入
一段用户反馈的需求或问题。

## 输出格式
必须返回严格的 JSON 数组，每个元素包含：
- title: 任务标题（简短）
- description: 任务详细描述（1-2 句）
- service: 涉及的微服务名称
- priority: high / medium / low

## 约束
- 只返回 JSON，不包含任何解释文字
- 任务数量 2-5 个
- 优先关注 root cause 排查，其次才是修复方案
```

### 9.4 LLM 调用参数

```python
response = await client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    temperature=0.3,
    max_tokens=1024,
    response_format={"type": "json_object"},  # 强制 JSON 输出
)
```

### 9.5 示例

**输入**：用户下单后未收到确认短信，怀疑系统未发送通知

**输出**：

```json
{
  "tasks": [
    {
      "id": 1,
      "title": "排查短信发送服务",
      "description": "检查短信网关日志，确认请求是否到达、是否有错误响应",
      "service": "sms-service",
      "priority": "high"
    },
    {
      "id": 2,
      "title": "核查订单状态",
      "description": "查询订单表确认订单是否创建成功、状态是否为已支付",
      "service": "order-service",
      "priority": "high"
    },
    {
      "id": 3,
      "title": "检查通知规则",
      "description": "确认用户通知偏好设置，排查是否有规则过滤导致未发送",
      "service": "notification-service",
      "priority": "medium"
    }
  ]
}
```

### 9.6 边界与限制

| 限制 | 说明 |
|------|------|
| 单次输入 ≤ 1000 字 | 超长需求建议分段拆解 |
| 任务数 2-5 个 | 超出范围由 LLM 自行裁剪 |
| 不执行实际代码 | Agent 仅做分析规划，不修改代码或配置 |
| 微服务列表来自 LLM 推断 | 未对接实际服务注册中心 |
