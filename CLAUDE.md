# CLAUDE.md

> AI 智能客服系统 — RAG 企业级智能问答平台

## 项目概述

基于大语言模型 (LLM) 的企业级智能客服系统。核心是通过 RAG (Retrieval-Augmented Generation) 架构实现：用户上传知识库文档 → 自动解析向量化 → 用户提问 → 语义检索 → LLM 生成回答 → 流式逐字输出。

**笔试项目**：海慈科技 AI 开发工程师笔试题，5 天交付周期。

## 技术栈

| 层 | 技术 | 版本 |
|---|------|------|
| 前端 | React + TypeScript + Vite | React 19 / TS 5.x |
| 后端 | Python FastAPI | 0.115+ |
| LLM | DeepSeek API (deepseek-v4-flash) | 兼容 OpenAI SDK |
| Embedding | BGE-M3 (BAAI/bge-m3) | sentence-transformers 3.x |
| 向量库 | Milvus Lite (嵌入式) | pymilvus 2.4 |
| 数据库 | MySQL | 8.0+ |
| RAG 框架 | 手动实现 + LlamaIndex Reader | - |
| UI 组件 | shadcn/ui + reactbits.dev | Tailwind v4 |
| 设计风格 | SaaS Light — Indigo #6366f1 | designprompts.dev #05 |
| 图标 | lucide-react | - |

## 项目结构

```
ICS/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口 + CORS + 路由注册
│   │   ├── config.py            # pydantic-settings (.env → Settings)
│   │   ├── database.py          # SQLAlchemy engine/session/Base
│   │   ├── dependencies.py      # Depends(get_db, get_current_user_id)
│   │   ├── api/                 # 路由层 (auth, sessions, chat, knowledge, feedback, stats)
│   │   ├── services/            # 服务层 (auth_service, session_service, chat_service, knowledge_service, stats_service)
│   │   ├── models/              # ORM 模型 (user, session, message, feedback, document)
│   │   ├── schemas/             # Pydantic DTO
│   │   └── rag/                 # RAG 核心引擎 (独立于 Web 层)
│   │       ├── chunker.py       #   文档分块
│   │       ├── embedder.py      #   BGE-M3 Embedding
│   │       ├── vector_store.py  #   Milvus CRUD
│   │       ├── retriever.py     #   检索服务
│   │       ├── ingestion.py     #   文档入库管线
│   │       ├── prompt.py        #   System Prompt + 拼接
│   │       ├── llm.py           #   DeepSeek API + 重试
│   │       ├── stream.py        #   SSE 事件生成器
│   │       ├── intent.py          #   意图识别与追问
│   │       └── fallback.py      #   空检索兜底
│   ├── db/init.sql              # 建表语句
│   ├── example_docs/            # 测试知识库文档 (3 篇)
│   ├── data/                    # 运行时数据 (uploads/, milvus/) — gitignore
│   ├── init_knowledge.py        # 一键初始化脚本
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── api/                 # HTTP 请求 + SSE 消费
│   │   ├── stores/              # Zustand (auth, session, chat)
│   │   ├── pages/               # Login, Register, Chat, Knowledge, Stats
│   │   ├── components/          # chat/, sidebar/, knowledge/, ui/
│   │   ├── hooks/               # useSSE, useAuth
│   │   ├── lib/                 # sseParser, utils
│   │   └── styles/              # global.css (Tailwind)
│   └── vite.config.ts           # proxy /api → localhost:8000
├── docs/
│   ├── PRD.md                   # 产品需求文档
│   ├── ARCHITECTURE.md          # 架构文档
│   ├── API文档.md
│   ├── 数据库设计.md
│   ├── AI架构设计.md
│   ├── 业务流程说明.md
│   └── superpowers/             # 设计 spec + 实现 plan
├── 项目说明.md                 # 项目整体说明（技术选型、AI架构、业务思考）
├── 运行指南.md                 # 环境要求 + 启动步骤 + 故障排查
├── .gitignore                  # 排除 .env / data/ / __pycache__ / node_modules
└── CLAUDE.md                   # ← 本文件（AI 助手开发指南）
```

## 架构原则

### 分层依赖规则

```
api → services → { models, rag }
  ↓        ↓
schemas  database

禁止反向依赖。rag/ 模块零依赖 FastAPI，可独立测试。
```

### RAG 核心链路

```
用户问题 → 校验(≤500字/≤100次/天) → BGE-M3 Embedding → Milvus 检索(top_k=5, threshold=0.65)
  → 检索为空? → 兜底话术(不调LLM)
  → 检索有结果? → Prompt拼接(System+历史+知识片段) → DeepSeek stream → SSE逐字输出
  → 保存消息 + 引用来源 → MySQL
```

### 关键配置 (.env)

```ini
# === 必填 ===
DEEPSEEK_API_KEY=          # DeepSeek API Key (用户提供)

# === LLM ===
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
LLM_TIMEOUT=30             # LLM 超时秒数

# === Embedding ===
EMBEDDING_MODEL=BAAI/bge-m3    # 或本地路径 (如 ./models/bge-m3)
EMBEDDING_DEVICE=cpu           # CPU 推理, GPU 可用 cuda
HF_HOME=./models               # HuggingFace 模型缓存路径

# === 向量库 ===
MILVUS_DB_PATH=./data/milvus/ics_knowledge.db

# === MySQL ===
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=ics_user
MYSQL_PASSWORD=
MYSQL_DATABASE=ics_customer_service

# === JWT ===
JWT_SECRET_KEY=change-me-to-random
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# === 业务参数 ===
TOP_K=5                    # Milvus 检索片段数
SIMILARITY_THRESHOLD=0.65  # 相似度阈值
MAX_QUESTION_LENGTH=500    # 问题长度上限
DAILY_QUESTION_LIMIT=100   # 每日提问上限
MAX_HISTORY_ROUNDS=5       # 多轮对话轮数
MAX_CONTEXT_TOKENS=8000    # Token 预算

# === 文件 ===
UPLOAD_DIR=./data/uploads
```

## 开发约定

### 后端规范

- **类型注解**：所有函数签名必须含类型注解（mypy strict 目标）
- **异步优先**：LLM 调用用 `async/await`，SSE 用 `AsyncGenerator`
- **错误处理**：RAG 模块异常用 try/except → SSE error 事件；API 层用 HTTPException
- **模型加载**：BGE-M3 懒加载（`@property`），避免启动时阻塞
- **无硬编码**：所有配置值来自 `Settings` (pydantic-settings)

### 前端规范

- **组件**：`PascalCase` 文件名，`function Component() {}` 声明
- **状态管理**：服务端数据通过 `api/` 直接调，全局状态用 Zustand store
- **SSE 消费**：`fetch` + `ReadableStream` + `TextDecoder`（不用 EventSource，不支持 POST）
- **CSS**：Tailwind utility-first + 自定义 `markdown-body` 类处理 AI 回答中 Markdown 样式
- **无 any**：TypeScript strict，接口定义在 `api/` 模块中

### 通用规范

- **文件大小**：单文件 ≤ 400 行
- **函数大小**：单函数 ≤ 50 行
- **无硬编码密钥**：API Key 一律从环境变量读取
- **提交格式**：`type: description` (feat/fix/refactor/docs/test/chore)

## 常用命令

```bash
# 后端
cd backend
source .venv/Scripts/activate        # Windows
pip install -r requirements.txt
cp .env.example .env                 # 编辑填入 API Key
python init_knowledge.py             # 初始化 DB + 向量库
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev                          # http://localhost:5173

# 测试 API
curl http://localhost:8000/api/health
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800000001","password":"123456"}'
```

## RAG 模块接口约定

```python
# chunker
TextChunker(chunk_size=500, chunk_overlap=50).chunk(text, metadata) -> list[dict]

# embedder
Embedder().embed_query(query: str) -> list[float]     # 1024维
Embedder().embed(texts: list[str]) -> list[list[float]]

# vector_store
VectorStore().insert_chunks(chunks, embeddings) -> list[int]
VectorStore().search(vec, top_k, threshold, filter) -> list[dict]  # [{text, source, score}]
VectorStore().delete_by_ids(ids)

# retriever
Retriever().search(query: str) -> list[dict]

# prompt
build_messages(query, retrieved_chunks, history, max_rounds) -> list[dict]

# llm
LLMClient().chat_stream(messages) -> AsyncGenerator[str, None]

# stream
generate_chat_stream(query, session_id, history) -> AsyncGenerator[str, None]
```

## AI 工程要点

本文档仅供开发参考。AI 工程问题的详细处理策略见 `docs/AI架构设计.md`，核心要点：

1. **检索为空** → 不调 LLM，直接返回预置兜底话术
2. **上下文超长** → 分层截断（低分片段先丢 → 远端历史先丢 → 句子边界截断）
3. **LLM 幻觉** → 四层防御（Prompt 约束 + 检索门槛 + 来源标注 + 反馈闭环）
4. **System Prompt** → 角色："你是智能客服助手" — 不含公司名

## UI 设计令牌

```
主强调色:          #6366f1 (Indigo-500)
主强调色-hover:     #4f46e5 (Indigo-600)
主强调色-light:     #eef2ff (Indigo-50)
消息气泡-用户:      bg-#6366f1 text-white rounded-(16px 16px 4px 16px)
消息气泡-AI:        bg-#f9fafb border-#f0f1f3 rounded-(16px 16px 16px 4px)
侧边栏:            bg-#fafbfc border-r-#e8eaed w-60
输入框:            border-2 border-#e8eaed focus:border-#6366f1 rounded-2xl
引用卡片:           bg-#eef2ff text-#5b63d3 rounded-lg
发送按钮:          bg-#6366f1 text-white rounded-xl w-10 h-10
字体:              Inter, -apple-system, sans-serif
圆角阶梯:          8px(btn) / 10px(avatar) / 12px(card) / 14px(input) / 16px(bubble)
阴影层级:          shadow-sm(气泡) / shadow-md(卡片) / 0 2px 8px rgba(99,102,241,0.2)(用户气泡)
```

### 动效

- 流式文本: CSS `@keyframes blink` typing cursor
- 消息入场: CSS `@keyframes fadeInUp` 0.3s ease-out
- 交互反馈: Tailwind `transition-all duration-150`
- 无背景大动效 (Aurora/Beams)，保持客服场景克制

## 约束

- ✅ DeepSeek API Key 由用户提供，`.env` 不入库
- ✅ 初始知识库使用 `example_docs/` 下 3 篇测试文档
- ✅ RAG 核心链路手动实现（chunking/embedding/search/prompt/stream），文档解析可复用 LlamaIndex
- ✅ 流式输出使用 SSE (text/event-stream)
- ✅ 前端不得直接调用 LLM API，所有 AI 调用走后端
- ❌ 不提交真实 API Key
- ❌ 不用 WebSocket（除非有明确理由）
