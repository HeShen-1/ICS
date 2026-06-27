# 架构文档 (ARCHITECTURE)

> AI 智能客服系统 v1.0 | 2026-06-23

## 1. 系统架构总览

```
                                ┌──────────────────────┐
                                │   用户浏览器 (Web)     │
                                │   React + TypeScript  │
                                └──────────┬───────────┘
                                           │
                         REST (JSON)       │       SSE (text/event-stream)
                         ┌─────────────────┼─────────────────┐
                         │                 │                 │
                         ▼                 ▼                 │
                ┌──────────────────────────────────────┐     │
                │         FastAPI 应用服务器             │     │
                │                                      │     │
                │  ┌──────────────────────────────┐    │     │
                │  │      API 路由层 (Router)       │    │     │
                │  │  auth / sessions / chat /     │    │     │
                │  │  knowledge / feedback / stats  │    │     │
                │  └──────────────┬───────────────┘    │     │
                │                 │                     │     │
                │  ┌──────────────▼───────────────┐    │     │
                │  │     服务层 (Service)           │    │     │
                │  │  业务逻辑编排 / 校验 / 持久化   │    │     │
                │  └──────┬─────────────────┬──────┘    │     │
                │         │                 │           │     │
                │  ┌──────▼──────┐   ┌──────▼──────┐    │     │
                │  │  RAG 模块    │   │  SQLAlchemy │    │     │
                │  │ (核心引擎)   │   │   ORM 层    │    │     │
                │  │              │   └──────┬──────┘    │     │
                │  │ ┌──────────┐ │          │           │     │
                │  │ │ BGE-M3   │ │          │           │     │
                │  │ │(内嵌运行)│ │          │           │     │
                │  │ └──────────┘ │          │           │     │
                │  └──────┬───────┘          │           │     │
                └─────────┼──────────────────┼───────────┘     │
                          │                  │                 │
                          ▼                  ▼                 ▼
                    ┌─────────┐        ┌─────────┐    ┌─────────────┐
                    │ Milvus  │        │  MySQL  │    │  DeepSeek   │
                    │ (本地)  │        │ (本地)  │    │  (云端API)  │
                    │ 向量存储│        │结构化数据│    │   LLM 推理  │
                    └─────────┘        └─────────┘    └─────────────┘
```

## 2. 技术架构决策 (ADR)

### ADR-001: 选择 FastAPI 作为后端框架

**决策**：使用 FastAPI（Python）而非 Spring Boot（Java）。

**理由**：
- Python 是 AI/ML 生态的事实标准，LangChain、sentence-transformers、pymilvus 均为 Python 优先
- FastAPI 原生支持异步和 SSE（`StreamingResponse`），无需额外 WebSocket 中间件
- 开发效率高：Pydantic 自动校验 + OpenAPI 自动生成文档
- 笔试题 5 天周期，Python 项目搭建速度远超 Java

**代价**：Python GIL 限制高并发，但本系统并发要求低（50 用户），可接受。

---

### ADR-002: 选择 DeepSeek API 作为 LLM

**决策**：使用 DeepSeek API（`deepseek-chat`）。

**理由**：
- 兼容 OpenAI SDK，零迁移成本
- 中文效果好，价格极低
- 由用户提供 API Key

---

### ADR-003: 选择 BGE-M3 本地 Embedding

**决策**：使用 BAAI/bge-m3 本地运行，而非调用云端 Embedding API。

**理由**：
- BGE-M3 在中文检索任务上表现 SOTA（MTEB 中文榜单前列）
- 本地运行零 API 成本，无网络依赖
- 1024 维向量，精度与效率平衡
- `sentence-transformers` 一行代码加载，CPU 推理足够

**代价**：首次启动需下载约 2GB 模型文件；CPU 推理批量 embedding 较慢（对千量级文档可接受）。

---

### ADR-004: 选择 Milvus Lite（嵌入式模式）

**决策**：使用 `pymilvus` 的 MilvusClient（Lite 嵌入式模式）。

**理由**：
- 零部署：数据存本地文件，无需独立服务进程
- 功能完整：支持 COSINE 相似度、metadata 过滤、批量删除
- OpenAI 兼容的 API 风格
- 开发阶段 Lite，生产可无缝切 standalone/cloud

**代价**：Lite 模式不支持分布式索引，数据量大后性能下降。当前知识库规模（千级文档）完全可接受。

---

### ADR-005: RAG 核心链路手动实现

**决策**：Chunking、Embedding、Retrieval、Prompt 拼接、LLM 调用、SSE 流式全手动实现，仅文档解析复用 LlamaIndex Reader。

**理由**：
- 笔试题明确要求"理解每一步逻辑"
- 手动实现能精确控制分块策略、检索参数、Prompt 模板
- 避免 LangChain 黑盒抽象层带来的调试困难
- 代码量可控（RAG 模块 < 500 行）

---

### ADR-006: SSE 而非 WebSocket

**决策**：使用 SSE (Server-Sent Events) 实现流式输出。

**理由**：
- 单向数据流（服务端→客户端），天然匹配 LLM 流式输出场景
- HTTP 协议原生支持，无需额外握手和连接管理
- 浏览器 `fetch` + `ReadableStream` 即可消费
- 比 WebSocket 更简单，代理/负载均衡兼容性更好

---

## 3. 分层架构

### 3.1 后端分层

```
backend/app/
│
├── main.py              # FastAPI 应用入口 + CORS + 路由注册
├── config.py            # pydantic-settings 配置管理 (.env → Settings)
├── database.py          # SQLAlchemy engine + session + Base
├── dependencies.py      # FastAPI Depends (get_db, get_current_user_id)
│
├── api/                 # 路由层 — HTTP 请求处理
│   ├── auth.py          #   POST /api/auth/register, /api/auth/login
│   ├── sessions.py      #   GET/POST /api/sessions, GET /api/sessions/{id}
│   ├── chat.py          #   POST /api/chat/{session_id}   ← SSE 流式
│   ├── knowledge.py     #   POST upload, GET list, DELETE/{id}
│   ├── feedback.py      #   POST /api/feedback
│   └── stats.py         #   GET /api/stats/daily
│
├── services/            # 服务层 — 业务逻辑编排
│   ├── auth_service.py      #   注册/登录/密码/JWT
│   ├── session_service.py   #   会话CRUD + 消息CRUD
│   ├── chat_service.py      #   校验 + 次数 + 历史获取
│   ├── knowledge_service.py #   上传→解析→入库流水线
│   └── feedback_service.py  #   反馈持久化
│
├── models/              # 数据层 — SQLAlchemy ORM 模型
│   ├── user.py, session.py, message.py, feedback.py, document.py
│
├── schemas/             # DTO 层 — Pydantic 请求/响应模型
│   ├── auth.py, session.py, chat.py, feedback.py, knowledge.py
│
└── rag/                 # RAG 核心引擎 — 与应用层解耦
    ├── chunker.py       #   文档分块（段落感知 + 滑动窗口）
    ├── embedder.py      #   BGE-M3 本地 Embedding
    ├── vector_store.py  #   Milvus 向量 CRUD + 相似度搜索
    ├── retriever.py     #   检索服务（Embedding + Milvus 组合）
    ├── ingestion.py     #   文档入库流水线
    ├── prompt.py        #   System Prompt + 历史拼接 + 检索片段格式化
    ├── llm.py           #   DeepSeek API 流式调用 + 重试 + 超时
    ├── stream.py        #   SSE 事件生成器（编排检索→Prompt→LLM→SSE）
    └── fallback.py      #   检索为空时的兜底话术
```

**层级依赖规则**：`api → services → { models | rag }`，禁止反向依赖。`rag/` 模块独立于 FastAPI，可单独测试。

### 3.2 前端分层

```
frontend/src/
│
├── api/                 # API 调用层 — HTTP 请求封装
│   ├── client.ts        #   fetch 封装 + JWT 拦截 + 错误处理
│   ├── auth.ts          #   注册/登录
│   ├── sessions.ts      #   会话列表/详情/创建
│   ├── chat.ts          #   SSE 流式消费（fetch + ReadableStream）
│   ├── knowledge.ts     #   上传/列表/删除
│   └── feedback.ts      #   提交反馈
│
├── stores/              # 状态管理 — Zustand
│   ├── authStore.ts     #   用户认证状态
│   ├── sessionStore.ts  #   会话列表状态
│   └── chatStore.ts     #   聊天消息 + 流式内容 + 引用状态
│
├── pages/               # 页面组件 — 路由对应
│   ├── LoginPage.tsx
│   ├── RegisterPage.tsx
│   ├── ChatPage.tsx     #   主聊天页（三栏布局编排）
│   └── KnowledgePage.tsx
│
├── components/          # UI 组件 — 展示层
│   ├── ui/              #   通用组件 (Button, Input, Tag, Spinner)
│   ├── chat/            #   聊天组件
│   │   ├── ChatInput.tsx       输入框 + 字数统计
│   │   ├── ChatBubble.tsx      消息气泡 + Markdown 渲染
│   │   ├── SourceCard.tsx      知识来源引用卡片
│   │   ├── FeedbackBar.tsx     赞/踩按钮
│   │   └── StreamingText.tsx   打字机效果文本
│   ├── sidebar/         #   侧边栏
│   │   └── SessionList.tsx     会话列表 + 新建 + 退出
│   └── knowledge/       #   知识库组件
│       ├── UploadZone.tsx      拖拽上传区域
│       └── DocTable.tsx        文档表格
│
├── hooks/               # 自定义 Hook
│   ├── useSSE.ts        #   SSE 流式消费 Hook
│   └── useAuth.ts       #   认证状态 Hook
│
├── lib/                 # 工具函数
│   ├── sseParser.ts     #   text/event-stream 解析器
│   └── utils.ts
│
└── styles/              # 样式
    ├── global.css       #   Tailwind + 自定义 (markdown-body, animations)
    └── tokens.css       #   CSS 设计变量
```

## 4. 数据流

### 4.1 问答请求完整数据流

```
时间轴 →

用户浏览器                 FastAPI                    RAG 引擎                 DeepSeek API
    │                        │                          │                        │
    │  POST /api/chat/{id}   │                          │                        │
    │  {"content":"退换货?"}  │                          │                        │
    │ ──────────────────────>│                          │                        │
    │                        │                          │                        │
    │                        │  1. JWT 鉴权             │                        │
    │                        │  2. 校验问题长度          │                        │
    │                        │  3. 检查每日次数          │                        │
    │                        │  4. 保存 user message    │                        │
    │                        │     → MySQL              │                        │
    │                        │                          │                        │
    │                        │  5. 调用 Retriever ──────>│                        │
    │                        │                          │  Embedding(BGE-M3)    │
    │                        │                          │  → Milvus.search()    │
    │                        │          chunks[] <──────│                        │
    │                        │                          │                        │
    │                        │  [if empty → fallback]   │                        │
    │                        │                          │                        │
    │                        │  6. build_messages() ────>│                        │
    │                        │     System Prompt        │                        │
    │                        │     + History messages   │                        │
    │                        │     + Retrieved chunks   │                        │
    │                        │     + User query         │                        │
    │                        │                          │                        │
    │                        │                          │  7. chat_stream() ────>│
    │  SSE: event: token     │                          │     stream=True        │
    │  data: {"text":"退"}   │ <────────────────────────│ <── chunk[0] ──────────│
    │ <──────────────────────│                          │                        │
    │  SSE: event: token     │                          │                        │
    │  data: {"text":"换"}   │ <────────────────────────│ <── chunk[1] ──────────│
    │ <──────────────────────│                          │                        │
    │         ...            │         ...              │         ...            │
    │                        │                          │                        │
    │  SSE: event: sources   │                          │                        │
    │  data: {references}    │ <────────────────────────│  (LLM 完成)            │
    │ <──────────────────────│                          │                        │
    │                        │                          │                        │
    │  SSE: event: done      │                          │                        │
    │  data: {msg_id}        │  8. 保存 assistant msg   │                        │
    │ <──────────────────────│     → MySQL              │                        │
    │                        │                          │                        │
    ▼                        ▼                          ▼                        ▼
```

### 4.2 文档入库数据流

```
用户上传文件
   │
   ▼
POST /api/knowledge/upload (multipart/form-data)
   │
   ├─ 校验: 格式 (.txt/.md/.pdf) + 大小 (≤10MB)
   ├─ 保存文件 → data/uploads/{uuid}.{ext}
   ├─ 创建 Document 记录 → MySQL (status=processing)
   │
   ▼
DocumentIngestion.ingest_file()
   │
   ├─ 1. 读取文件内容
   │     .txt/.md → open().read()
   │     .pdf     → PDFReader (LlamaIndex)
   │
   ├─ 2. TextChunker.chunk()
   │     段落感知分割 → 合并短段 → 切分长段
   │     chunk_size 按文档类型自适应 (FAQ=800, Policy=1000, Tech=1200)，overlap=15%
   │
   ├─ 3. Embedder.embed()
   │     BGE-M3 批量编码 → 1024 维向量
   │
   ├─ 4. VectorStore.insert_chunks()
   │     向量 + text + metadata → Milvus
   │
   ▼
更新 Document 记录
   status=ready, chunk_count=N, milvus_ids=[...]
```

## 5. 组件交互

### 5.1 RAG 模块内部接口

```python
# ── Chunker ──
class TextChunker:
    def chunk(text: str, metadata: dict) -> list[dict]
    # 输入: 原始文本
    # 输出: [{"text": "...", "metadata": {"source": "xxx", "chunk_index": 0}}, ...]

# ── Embedder ──
class Embedder:
    def embed_query(query: str) -> list[float]      # 单条 → [0.1, 0.2, ...]
    def embed(texts: list[str]) -> list[list[float]] # 批量
    @property def dimension() -> int                 # 1024

# ── VectorStore ──
class VectorStore:
    def insert_chunks(chunks, embeddings) -> list[int]
    def search(vec, top_k, threshold, filter_expr) -> list[dict]
    def delete_by_ids(ids: list[int])
    def count() -> int

# ── Retriever ──
class Retriever:
    def search(query: str) -> list[dict]
    # 组合 Embedder + VectorStore，封装完整检索流程

# ── Prompt ──
def build_messages(query, retrieved_chunks, history, max_rounds) -> list[dict]
def format_retrieved_chunks(chunks) -> str

# ── LLM ──
class LLMClient:
    async def chat_stream(messages) -> AsyncGenerator[str, None]

# ── Stream ──
async def generate_chat_stream(query, session_id, history) -> AsyncGenerator[str, None]
# 编排完整 RAG → SSE 事件流

# ── Fallback ──
def get_fallback_response() -> str
def get_fallback_sources() -> list[dict]
```

### 5.2 前端 SSE 消费

```typescript
// api/chat.ts
async function sendMessage(sessionId, content, callbacks: SSECallback): Promise<void>
// 内部: fetch POST → ReadableStream → 按 \n\n 分帧 → parse event/data → callback

interface SSECallback {
  onToken: (text: string) => void;
  onSources: (references: Reference[]) => void;
  onDone: (data: DoneData) => void;
  onError: (code: string, message: string) => void;
}
```

## 6. 安全架构

```
┌─────────────────────────────────────────────────────────┐
│                      安全层次                            │
├─────────────────────────────────────────────────────────┤
│ 传输层    │ CORS 白名单 (localhost:5173)                 │
│           │ HTTPS (生产环境)                             │
├───────────┼─────────────────────────────────────────────┤
│ 认证层    │ JWT (HMAC-SHA256, 24h 过期)                  │
│           │ bcrypt 密码哈希                              │
├───────────┼─────────────────────────────────────────────┤
│ 授权层    │ 会话归属校验 (session.user_id == token.sub)   │
│           │ 资源隔离 (用户只能访问自己的会话和消息)        │
├───────────┼─────────────────────────────────────────────┤
│ 输入层    │ Pydantic 请求体验证                          │
│           │ 问题长度 ≤500 / 文件大小 ≤10MB / 格式白名单   │
│           │ SQLAlchemy 参数化查询（防 SQL 注入）          │
├───────────┼─────────────────────────────────────────────┤
│ 频率层    │ 每日提问次数限制（100次/天/用户）             │
│           │ LLM 重试指数退避（1s→2s→4s，最多3次）        │
├───────────┼─────────────────────────────────────────────┤
│ 数据层    │ API Key 不入库（.env 管理）                  │
│           │ 密码 bcrypt 哈希，不可逆                     │
│           │ .gitignore 排除 .env + data/                 │
└───────────┴─────────────────────────────────────────────┘
```

## 7. 错误处理策略

| 层级 | 策略 | 用户可见 |
|------|------|----------|
| API 层 | HTTPException + 统一错误码 | ✅ 错误码 + 中文消息 |
| Service 层 | Python 异常抛出 | ❌ |
| RAG 层 | try/except + 错误日志 | ✅ SSE error 事件 |
| LLM 调用 | 3 次重试 + 指数退避 | ✅ "AI 服务繁忙" |
| 前端 | try/catch + toast/error state | ✅ 内联错误提示 |

## 8. 部署架构

```
开发环境:
  ┌─────────────────────────────────────┐
  │  宿主机 (Windows / macOS / Linux)    │
  │                                     │
  │  ┌───────────┐  ┌──────────────┐   │
  │  │ Vite Dev   │  │ Uvicorn      │   │
  │  │ Server     │  │ :8000        │   │
  │  │ :5173      │  │              │   │
  │  └───────────┘  └──────┬───────┘   │
  │                        │           │
  │         ┌──────────────┼───────┐   │
  │         │              │       │   │
  │    ┌────▼────┐  ┌──────▼───┐  │   │
  │    │  MySQL  │  │ Milvus   │  │   │
  │    │  :3306  │  │  Lite    │  │   │
  │    └─────────┘  │ (文件)   │  │   │
  │                 └──────────┘  │   │
  │                               │   │
  │         模型文件:              │   │
  │         ~/.cache/huggingface/ │   │
  │         hub/models--BAAI--    │   │
  │         bge-m3/               │   │
  └─────────────────────────────────────┘

外部依赖:
  DeepSeek API (https://api.deepseek.com)
```

## 9. 技术债务 & 改进方向

| 项目 | 当前方案 | 建议改进 |
|------|----------|----------|
| 每日计数 | MySQL 查询 | Redis 计数器（原子操作，更低延迟） |
| 文件存储 | 本地磁盘 | OSS/S3 对象存储（持久化，多实例共享） |
| Embedding | CPU 推理 | GPU 推理或批量预计算缓存 |
| Milvus | Lite 嵌入式 | Standalone 分布式（数据量增长后） |
| 认证 | JWT | 增加 Refresh Token + 黑名单机制 |
| 监控 | 无 | 接入 Langfuse/Phoenix 做 LLM 可观测 |
| 测试 | 手动 | 单元测试 + 集成测试覆盖 |
