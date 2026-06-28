# ICS — AI 智能客服系统

基于大语言模型（LLM）和 RAG（检索增强生成）架构的企业级智能客服平台。支持多知识库管理、意图识别、多轮对话、流式输出和统计分析。

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/typescript-5.x-blue.svg)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.115+-teal.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/react-19.x-61dafb.svg)](https://react.dev/)

---

## 功能特性

- **RAG 智能问答** — 上传文档自动解析向量化，用户提问时语义检索 + LLM 生成精准回答
- **流式输出** — SSE 逐字打字机效果，首字延迟 < 2s
- **意图识别** — 关键词优先 + LLM 兜底，自动区分产品咨询/售后问题/投诉/闲聊
- **多知识库路由** — 自动识别问题归属知识库，支持跨库检索
- **多轮对话** — 上下文携带最近 N 轮历史，追问自动关联上文
- **引用溯源** — 每条回答标注知识来源（文档名 + 片段摘要），可追溯可验证
- **反馈机制** — 赞/踩 + 文字反馈，统计面板实时展示满意度
- **管理后台** — 用户/会话/消息/文档统计、每日提问趋势图、反馈分析
- **Agent 任务拆解** — 读取系统文档，自动拆解复杂需求为多微服务改动方案

## 技术架构

```
用户浏览器 (React 19) ── REST/SSE ──► FastAPI ──► DeepSeek API (LLM)
                                           │
                              ┌────────────┼────────────┐
                              ▼            ▼            ▼
                           MySQL       Milvus        BGE-M3
                         (结构化数据)  (向量存储)   (本地 Embedding)
```

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | React 19 + TypeScript + Vite | SPA，Zustand 状态管理，shadcn/ui 组件库 |
| 后端 | Python FastAPI 0.115 | 异步 REST API + SSE 流式输出 |
| LLM | DeepSeek API | 兼容 OpenAI SDK，可替换为任意兼容服务 |
| Embedding | BGE-M3 (本地) | 1024 维向量，CPU 推理，零 API 成本 |
| 向量库 | Milvus Lite (嵌入式) | 零部署，本地文件存储，支持 HNSW 索引 |
| 数据库 | MySQL 8.0 | SQLAlchemy ORM，存储用户/会话/消息/文档 |
| 文档解析 | LlamaIndex Reader (.pdf) + 原生 (.txt/.md) | PDF 复用成熟方案，纯文本零依赖 |

## 快速开始

### 环境要求

- Python 3.12+ · Node.js 20+ · MySQL 8.0+

### 1. 获取 API Key

访问 [platform.deepseek.com](https://platform.deepseek.com/) 注册并创建 API Key（新用户有免费额度）。

### 2. 配置数据库

```sql
CREATE DATABASE ics_customer_service CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'ics_user'@'localhost' IDENTIFIED BY 'your-password';
GRANT ALL PRIVILEGES ON ics_customer_service.* TO 'ics_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3. 启动后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # 编辑填入 DEEPSEEK_API_KEY 和 MYSQL_PASSWORD
python init_knowledge.py     # 初始化数据库 + 示例知识库向量化
uvicorn app.main:app --reload --port 8000
```

验证：http://localhost:8000/api/health → `{"status":"ok"}`  
API 文档：http://localhost:8000/docs

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173，注册账号后即可使用。

### 5. 快速体验

1. 注册账号（手机号 + 密码，密码需含大小写字母+数字+特殊字符，至少 8 位）
2. 创建会话，尝试提问：
   - "退换货流程是什么？"
   - "如何重置密码？"
   - "今天天气怎么样？"（测试兜底话术）

## 项目结构

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口 + CORS + 安全中间件
│   │   ├── config.py            # pydantic-settings 配置管理
│   │   ├── database.py          # SQLAlchemy 引擎/会话
│   │   ├── dependencies.py      # JWT 认证依赖注入
│   │   ├── api/                 # 路由层 (auth/sessions/chat/knowledge/feedback/stats/agent)
│   │   ├── services/            # 服务层 (auth/session/chat/knowledge/stats/feedback)
│   │   ├── models/              # ORM 模型 (user/session/message/feedback/document/knowledge_base)
│   │   ├── schemas/             # Pydantic 请求/响应 Schema
│   │   ├── rag/                 # RAG 核心引擎
│   │   │   ├── chunker.py       #   自适应分块 (Scheme C: FAQ=800/Policy=1000/Tech=1200)
│   │   │   ├── embedder.py      #   BGE-M3 本地 Embedding (单例+缓存)
│   │   │   ├── vector_store.py  #   Milvus CRUD + HNSW 索引
│   │   │   ├── retriever.py     #   检索服务 (关键词重排序 + auto_route)
│   │   │   ├── ingestion.py     #   文档入库管线 (解析→分块→向量化→存储)
│   │   │   ├── prompt.py        #   System Prompt + 片段格式化 + Token 预算
│   │   │   ├── llm.py           #   DeepSeek API 封装 (重试+指数退避)
│   │   │   ├── stream.py        #   SSE 事件生成器 (三层降级检索)
│   │   │   ├── intent.py        #   意图识别 (关键词优先 + LLM 兜底)
│   │   │   └── fallback.py      #   空检索兜底话术
│   │   └── agent/               # AI Agent 任务拆解
│   │       ├── decomposer.py    #   文档加载 + LLM 拆解
│   │       └── prompt.py        #   拆解 System Prompt
│   │   └── utils/               # 工具模块
│   │       ├── security.py       #   Prompt Injection 三层防御
│   ├── tests/                   # 后端测试 (127 用例, 84% 覆盖率)
│   │   ├── test_rag/             #   RAG 模块 + 评估 (eval_dataset + test_evaluation)
│   │   ├── test_api/             #   API 端点
│   │   ├── test_services/        #   服务层
│   │   └── test_agent/           #   Agent 拆解
│   ├── example_docs/            # 示例知识库文档 (7 篇)
│   ├── init_knowledge.py        # 一键初始化脚本
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/                 # HTTP 请求 + SSE 消费
│   │   ├── stores/              # Zustand 状态管理 (auth/session/chat)
│   │   ├── pages/               # Chat/Knowledge/Stats/Agent/Login 页面
│   │   ├── components/          # chat/sidebar/knowledge/ui 组件
│   │   ├── hooks/               # useSSE, useAuth
│   │   └── lib/                 # SSE 解析、工具函数
│   ├── package.json
│   ├── vite.config.ts
│   ├── playwright.config.ts      # E2E 测试配置 (21 用例)
│   └── e2e/                      # Playwright E2E (auth/chat/knowledge/stats/agent)
├── docs/                        # 项目文档
│   ├── ARCHITECTURE.md          #   架构文档
│   ├── AI架构设计.md             #   RAG 流程 + Prompt + 检索策略
│   ├── API文档.md               #   接口规范 + SSE 格式
│   ├── 数据库设计.md             #   ER 图 + 表结构
│   ├── PRD.md                   #   产品需求文档
│   └── 业务流程说明.md           #   问答链路时序图
├── 项目说明.md                   # 项目整体说明
├── 运行指南.md                   # 详细运行说明 + 故障排查
└── README.md                    # 本文件
```

## RAG 核心链路

```
用户提问 → 注入检测(三层防御:API→服务→Prompt)
          → 输入校验(≤500字/≤100次/天)
          → 意图识别(关键词+LLM)
          → BGE-M3 向量化
          → Milvus HNSW 检索(top_k=12, threshold=0.55)
          → 三层降级检索(kb路由→全局→低阈值兜底0.35)
          → 检索为空? → 兜底话术(不调LLM)
          → 检索有结果? → 分类去重(关键规则优先)
                        → Token 预算控制(运行计数器O(n))
                        → Prompt 拼接(System+历史+知识+日期+安全裹挟)
                        → DeepSeek 流式生成
                        → SSE 逐字输出 + 引用来源
                        → 保存消息 + 反馈统计
```

## AI 工程特性

### 幻觉防御（四层）

| 层级 | 策略 | 说明 |
|------|------|------|
| **Prompt 约束** | 5 条硬规则 + 3 条安全防护规则，禁止编造/评价竞品 | 从源头减少幻觉 |
| **检索门槛** | 相似度阈值 0.55 过滤，0.35 兜底 | 不给 LLM 喂不相关内容 |
| **来源标注** | 每条回答 📚 参考：文档名 | 可追溯可验证 |
| **反馈闭环** | 踩的记录写入 feedback 表 | 持续迭代优化 |

### Prompt Injection 防护（三层）

| 层级 | 策略 | 实现位置 |
|------|------|----------|
| **API 层拦截** | Pydantic `@field_validator` 检测注入模式（分隔符/角色切换/指令覆盖/异常字符） | `schemas/chat.py` |
| **服务层校验** | `validate_question()` 注入检测 — 攻击 payload → "检测到潜在注入攻击" | `services/chat_service.py` |
| **Prompt 隔离** | query 包裹 `<user_query>` 标签 + SYSTEM_PROMPT guardrail 指令 | `rag/prompt.py` |

> 可通过 `.env` 中 `PROMPT_INJECTION_ENABLED=true/false` 开关。

### 上下文超长处理

Token 预算 8000 → 分层截断：低分片段先丢 → 远端历史先丢 → 句子边界截断。关键规则（含"必须""禁止"等）保留优先级最高。

### 大规模检索保障

检索结果 > 8 条时启用分层输出：「⚠️ 关键规则」+「📋 详细参考」，防止 LLM 注意力稀释遗漏关键规则。

## 配置说明

完整配置见 `backend/.env.example`。核心参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | 必填 | DeepSeek API 密钥 |
| `TOP_K` | 12 | 检索返回片段数 |
| `SIMILARITY_THRESHOLD` | 0.55 | 相似度阈值 |
| `FALLBACK_THRESHOLD` | 0.35 | 三层兜底阈值 |
| `MAX_CONTEXT_TOKENS` | 8000 | Token 预算 |
| `DAILY_QUESTION_LIMIT` | 100 | 每日提问上限 |
| `JWT_SECRET_KEY` | 至少 32 字符 | JWT 签名密钥 |
| `PROMPT_INJECTION_ENABLED` | true | Prompt Injection 防护开关 |
| `LLM_REWRITE_ENABLED` | true | 检索前 LLM Query Rewriting |

## 运行测试

```bash
# 后端
cd backend
pytest tests/ -q                         # 127 个用例
pytest tests/ --cov=app --cov-report=term-missing
pytest tests/test_rag/test_evaluation.py -v  # RAGAS 评估 (7 个用例)

# 前端
cd frontend
npx vitest run                           # 33 个单元测试用例
npm run e2e                              # 21 个 Playwright E2E 用例
```

## 已知不足与优化方向

> 本项目为 5 天交付的笔试项目，在 RAG 检索准确率、工程鲁棒性、评估体系等方面仍有提升空间。以下按影响程度由高到低列出关键不足、根本原因及后续优化建议。

### 📊 总览

| 模块 | 当前方案 | 核心不足 | 影响 |
|------|----------|----------|------|
| 检索排序 | Dense + 关键词启发式打分 | 无精排模型，关键词权重靠手调 | 🔴 高 |
| 语义匹配 | BGE-M3 双塔模式 | 单向量表达，长尾 query 语义丢失 | 🔴 高 |
| Query 理解 | 固定同义词表 + LLM Rewrite | 词表静态不泛化，Rewrite 依赖 LLM 可用性 | 🟡 中 |
| 分块策略 | 256–600 字符自适应 | 小 chunk 丢失上下文，大 chunk 稀释语义 | 🟡 中 |
| 意图识别 | 100+ 关键词 + LLM 兜底 | 仅 4 类，无法处理复合意图 | 🟡 中 |
| 评估体系 | RAGAS + 15组标注QA ✅ | 数据集偏小，未覆盖所有边界场景 | 🟡 中 |
| 安全防护 | 三层 Prompt Injection 防御 ✅ | 文本检测可被编码绕过，需 LLM guard 增强 | 🟡 中 |
| 增量更新 | chunk 级 hash diff ✅ | 并发更新需事务保护 | 🟢 低 |
| 反馈闭环 | 仅写入 feedback 表 | 反馈数据未回灌优化检索 | 🟢 低 |
| 向量库 | Milvus Lite 单文件 | 不支持分布式，大容量性能衰退 | 🟢 低 |
| 文档解析 | PDF + .txt/.md | 缺失 DOCX/HTML/CSV/图片 OCR | 🟢 低 |

---

### 🔴 1. RAG 检索准确率

#### 现状

当前采用 **Dense (BGE-M3) + 关键词加分 + Multi-Query RRF 融合** 的混合检索方案（`retriever.py:168-321`）。关键词评分函数 `_keyword_score()` 使用手工固定权重（2 字词 0.03、3 字词 0.05、4+ 字词 0.08、子串匹配 0.02），上限 0.30。

#### 可能原因

| 根因 | 说明 | 证据 |
|------|------|------|
| **无双塔精排** | cosine 相似度仅在全局向量空间比较，无法捕捉细微语义差异。用户问"怎么退款"和知识库中"退换货流程"语义相关但向量距离可能偏大 | `retriever.py` 仅用 `embed_query()` 做单次检索，无 Cross-Encoder 或 ColBERT 精排 |
| **关键词权重硬编码** | 不同业务场景的最优权重不同，当前权重靠手工设定，无法根据反馈数据自适应 | `retriever.py:130-165` — `_keyword_score()` 常量硬编码 |
| **同义词表静态且小** | `_SYNONYM_MAP` 仅 11 组映射，无法覆盖领域内所有同义表达（如"怎么买"↔"购买方式"、"多久到"↔"配送时效"） | `retriever.py:16-28` |
| **单向量表达瓶颈** | 双塔模型将 query 和 doc 压缩为单向量，长文本/多主题文档的语义信息在压缩中丢失 | `embedder.py:47-57` — 返回固定 1024 维单向量 |
| **无多样性控制** | 检索结果未去重/去冗余（MMR），同一文档的多个相似 chunk 可能挤占 top_k 位置 | `retriever.py:229-230` — 仅按 score 排序取 top_k |
| **chunk 语义粒度不足** | FAQ chunk=256 字符过于碎片化，单 chunk 可能只含回答不含问题，导致检索时语义不完整 | `chunker.py:26` — `_TYPE_SIZES["faq"]` = 256 |

#### 优化方案

```text
短期（1-2 周，低成本快速见效）
├── 1. 引入 Reranker 精排
│     方案：BGE-M3 粗排候选池 (top_k*5) → BGE-Reranker-v2-m3 Cross-Encoder 精排 → 取 top_k
│     预期：召回率 +10~15%，误召回率显著下降
│     成本：本地推理 ~50ms/chunk，GPU 推荐
│
├── 2. 启用 MMR (Maximal Marginal Relevance)
│     方案：取 top_k 结果后，逐条按 λ·score - (1-λ)·max_sim_to_selected 选取
│     预期：去除冗余 chunk，top_k 内覆盖更多不同来源
│     成本：O(k²) 计算，k=24 时 <1ms
│
├── 3. 扩展同义词表 + 引入 Word2Vec 近义词
│     方案：用腾讯词向量/Chinese-Word-Vectors 自动发现领域近义词
│     预期：召回率 +3~5%
│     成本：加载词向量文件 ~500MB，查询 <1ms
│
└── 4. 增大 chunk_size 用 Sentence Window 检索
      方案：FAQ 类从 256 提至 512-600，用 sentence window 在检索后取前后各 1 句扩展上下文
      预期：语义完整性提升，回答更精准
      成本：embedding 存储增大 ~1.5x

中期（1-2 月，需工程投入）
├── 5. 引入 ColBERT 晚交互检索
│     方案：ColBERT 的 MaxSim 在 token 级匹配，比单向量更细粒度
│     预期：长尾 query 准确率 +15~20%
│     成本：存储量显著增大（每 doc 存 token-level embeddings），需 GPU 索引
│
├── 6. Self-RAG / CRAG 自反思检索
│     方案：LLM 对检索结果打分（相关/部分相关/不相关），不相关则重写 query 重新检索
│     预期：复杂问题准确率 +20%+
│     成本：每次查询额外 1-2 次 LLM 调用
│
├── 7. HyDE (Hypothetical Document Embeddings)
│     方案：LLM 先生成"假设的理想回答"，用假设回答的 embedding 检索，而非原始 query
│     预期：克服 query-document 语义 gap，召回率 +10%
│     成本：每次查询多 1 次 LLM 调用，延迟 +1-3s
│
└── 8. 构建 RAG 评估框架 (RAGAS + 标注数据集)
      方案：用 RAGAS 评估 faithfulness/answer_relevancy/context_precision/context_recall
      预期：量化效果，指导调参
      成本：需构建 200+ 条标注 QA 对

长期（3 月+，需要持续打磨）
├── 9. GraphRAG — 知识图谱增强
│     方案：从文档抽取实体关系构建知识图谱，检索时融合图遍历 + 向量检索
│     预期：多跳推理问题准确率大幅提升
│     成本：实体识别模型 + 图数据库 (Neo4j)
│
├── 10. 微调 Embedding 模型
│      方案：用领域内正负样本对微调 BGE-M3，使 embedding 空间对领域语义更敏感
│      预期：领域内检索准确率 +10~20%
│      成本：需 GPU + 标注数据，训练数小时
│
└── 11. Query 路由 + 自适应检索
       方案：简单问题直接用向量检索，复杂问题走 HyDE + multi-hop + ColBERT 组合管线
       预期：平均延迟降低 30%，复杂问题准确率提升
       成本：路由模型训练/Prompt 工程
```

---

### 🟡 2. 意图识别精度

#### 现状

`intent.py` 使用关键词优先策略（闲聊 12 词 → 投诉 16 词 → 售后 32 词 → 产品 44 词），仅 4 个类别。关键词未命中时异步调用 LLM。

#### 可能原因

- 关键词匹配无法处理否定句（"我不想退款"误判为售后）
- 复合意图无法拆分（"产品很好但物流太慢" — 只判一种）
- 缺少置信度阈值，关键词匹配均为 100% 置信度

#### 优化方案

- 短期：增加语序感知（jieba 词性标注 + 否定词检测）
- 中期：训练轻量意图分类模型（BERT-tiny fine-tune），多标签支持
- 长期：引入槽位填充（SLU），结构化提取意图 + 参数

---

### 🟡 3. 多知识库路由

#### 现状

`auto_route()` 用 kb_id 频次投票 + 最高分比较。对大 KB（chunk 多）和小 KB（chunk 少但精准）的公平性问题已通过最高分策略缓解。

#### 可能原因

- 知识库元信息（描述、标签、覆盖范围）未参与路由
- 无显式 KB→query 语义匹配（当前依赖 chunk 检索反向推断）
- 多 KB 同时相关时（如"退货政策在哪个 KB？"），只能单选

#### 优化方案

- 短期：为 KB 增加 description 字段，用 KB description embedding 与 query embedding 做语义路由
- 中期：支持多 KB 联合检索（跨 KB RRF 融合）
- 长期：Agentic Router — LLM 分析问题后决定单/多 KB + 检索策略

---

### 🟡 4. 评估与可观测性

#### 现状

已集成 RAGAS 评估框架（`tests/test_rag/test_evaluation.py` — 7 个测试用例），含 15 组标注 QA 数据集（覆盖全部 7 篇 example_docs）。评估维度：recall@5 (≥0.6)、precision@5、关键词覆盖、端到端管线完整性、空检索兜底。

#### 可能原因

- 15 组 QA 规模偏小，未覆盖复合问题、长尾 query 等边界场景
- 无在线评估回路（无法自动采集用户反馈评估检索质量）
- 缺少 A/B 实验基础设施对比不同策略效果

#### 优化方案

- 短期：数据集扩充至 200+ 条 QA 对，增加复合/否定/多KB 等边界类型
- 中期：在 feedback 表中标记"检索质量评分"，建立在线评估回路；接入 LangFuse 实现全链路追踪
- 长期：Playground + A/B 对比不同检索策略（Dense vs Hybrid vs ColBERT）

---

### 🟢 5. 工程鲁棒性

| 问题 | 现状 | 优化方向 |
|------|------|----------|
| **大容量向量检索** | Milvus Lite 单文件，~100 万向量后 HNSW 性能下降 | 迁移至 Milvus Standalone / Qdrant / pgvector |
| **文档格式覆盖** | 仅 PDF + .txt/.md | 增加 DOCX、HTML、CSV、图片 OCR (tesseract) |
| **增量更新** | ✅ chunk 级 hash diff 已实现 | 并发更新需事务保护 |
| **SSE 断线恢复** | 断线后无法恢复流 | 实现 Last-Event-ID + 消息缓存重放 |
| **语义缓存** | embed_query 有简易内存缓存 | 引入 Redis 做语义缓存，相似问题直接返回缓存答案 |
| **多语言支持** | 仅中文 | BGE-M3 原生支持多语言，需补充英文 Prompt 模板 |
| **Prompt 管理** | 硬编码在代码中 | Prompt 版本化管理（LangSmith / 数据库存储），支持 A/B 测试 |
| **安全注入** | ✅ 三层 Prompt Injection 防御 | 文本检测可被编码绕过，建议叠加 LLM-as-guard |
| **大文件处理** | 10MB 上限，大文件解析阻塞 | 异步任务队列（Celery/Redis）+ 分块上传 |

---

### 📋 优化路线图建议

```
Phase 1 (1-2 周) ─ 快速提升检索质量
  ✅ Reranker 精排 (BGE-Reranker)
  ✅ MMR 去冗余
  ✅ chunk_size 调优 (FAQ 256→512)
  ✅ 构建 RAGAS 评估基准 ─ 已落地 (15组QA, 7个评估用例)
  ✅ 知识库增量更新 ─ 已落地 (chunk 级 hash diff)
  ✅ Prompt Injection 三层防御 ─ 已落地

Phase 2 (1-2 月) ─ 深层语义匹配
  ✅ HyDE / Query2Doc
  ✅ ColBERT 晚交互（试点）
  ✅ Self-RAG 自检
  ✅ 评估数据集扩充至 500+

Phase 3 (3 月+) ─ 智能体系
  ✅ GraphRAG 知识图谱
  ✅ Embedding 模型领域微调
  ✅ Agentic Router 自适应检索
  ✅ Prompt 版本化管理 + A/B 实验
```

---

## 许可证

本项目基于 [Apache License 2.0](LICENSE) 开源。


