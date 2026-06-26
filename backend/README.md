# 后端 — AI 智能客服系统

> Python FastAPI 后端，提供 REST API、RAG 核心引擎、数据库管理。

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 框架 | FastAPI 0.115 | 异步 Web 框架 |
| 数据库 | MySQL 8.0 + SQLAlchemy 2.0 | 结构化数据存储 |
| 向量库 | Milvus Lite (pymilvus 2.4) | 嵌入式向量存储 |
| LLM | DeepSeek API (deepseek-chat) | 云端大模型 |
| Embedding | BGE-M3 (sentence-transformers) | 本地 1024 维向量化 |
| 认证 | JWT (python-jose) | HS256 签名 |

## 目录结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口 + CORS + 路由注册
│   ├── config.py            # pydantic-settings 配置管理
│   ├── database.py          # SQLAlchemy engine/session/Base
│   ├── dependencies.py      # Depends 依赖注入
│   ├── api/                 # 路由层
│   │   ├── auth.py          #   注册 / 登录 / Token 刷新
│   │   ├── chat.py          #   SSE 流式聊天
│   │   ├── sessions.py      #   会话 CRUD
│   │   ├── knowledge.py     #   文档上传 / 管理
│   │   ├── feedback.py      #   用户反馈
│   │   └── stats.py         #   统计数据
│   ├── services/            # 服务层（业务编排）
│   │   ├── auth_service.py
│   │   ├── chat_service.py
│   │   ├── session_service.py
│   │   ├── knowledge_service.py
│   │   └── feedback_service.py
│   ├── models/              # ORM 模型（SQLAlchemy）
│   │   ├── user.py
│   │   ├── session.py
│   │   ├── message.py
│   │   ├── document.py
│   │   └── feedback.py
│   ├── schemas/             # Pydantic DTO（请求/响应模型）
│   └── rag/                 # RAG 核心引擎（零 FastAPI 依赖）
│       ├── chunker.py       #   文档分块（段落感知 + 滑动窗口）
│       ├── embedder.py      #   BGE-M3 Embedding（懒加载单例）
│       ├── vector_store.py  #   Milvus CRUD
│       ├── retriever.py     #   语义检索
│       ├── ingestion.py     #   文档入库管线
│       ├── prompt.py        #   System Prompt + Token 截断
│       ├── llm.py           #   DeepSeek API + 重试
│       ├── stream.py        #   SSE 事件生成器
│       └── fallback.py      #   空检索兜底话术
├── db/init.sql              # 建表语句
├── example_docs/            # 测试知识库文档
├── data/                    # 运行时数据（uploads/, milvus/）
├── init_knowledge.py        # 一键初始化脚本
├── requirements.txt
└── .env.example             # 环境变量模板（实际 .env 在项目根目录）
```

## 架构分层

```
api → services → { models, rag }
  ↓        ↓
schemas  database
```

**依赖规则：**
- API 层只做路由和参数校验，调用 services
- Services 编排业务逻辑，调用 models 和 rag
- RAG 模块零 FastAPI 依赖，可独立测试
- 禁止反向依赖

## 环境变量

配置统一放在**项目根目录**的 `.env` 文件。`.env.example` 为模板。

| 变量 | 必填 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | ✅ | DeepSeek API 密钥 |
| `MYSQL_PASSWORD` | ✅ | MySQL 密码 |
| `MYSQL_HOST` | ❌ | 默认 localhost |
| `MYSQL_PORT` | ❌ | 默认 3306 |
| `MYSQL_USER` | ❌ | 默认 ics_user |
| `MYSQL_DATABASE` | ❌ | 默认 ics_customer_service |
| `EMBEDDING_MODEL` | ❌ | 默认 BAAI/bge-m3 |
| `EMBEDDING_DEVICE` | ❌ | cpu / cuda |
| `HF_HOME` | ❌ | HuggingFace 模型缓存路径 |
| `TOP_K` | ❌ | 检索返回片段数（默认 5） |
| `SIMILARITY_THRESHOLD` | ❌ | 相似度阈值（默认 0.65） |
| `LLM_TIMEOUT` | ❌ | LLM 超时秒数（默认 30） |

## RAG 核心链路

```
用户问题 → 输入校验(≤500字/≤100次/天) → BGE-M3 Embedding(本地)
  → Milvus 检索(top_k=5, threshold=0.65)
  → 结果为空? → 兜底话术(不调LLM)
  → 有结果? → Prompt拼接(System+历史+知识片段) → DeepSeek stream → SSE逐字输出
  → 保存消息+引用来源 → MySQL
```

## 快速启动

```bash
# 1. 激活 conda 环境
conda activate ics

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量（在项目根目录）
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY 和 MYSQL_PASSWORD

# 4. 初始化数据库 + 知识库
python init_knowledge.py

# 5. 启动服务
uvicorn app.main:app --reload --port 8000
```

验证：http://localhost:8000/api/health → `{"status":"ok"}`

API 文档：http://localhost:8000/docs (Swagger UI)

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 |
| GET | `/api/sessions` | 会话列表 |
| POST | `/api/sessions` | 新建会话 |
| DELETE | `/api/sessions/{id}` | 删除会话 |
| POST | `/api/chat/stream` | SSE 流式聊天 |
| GET | `/api/chat/history/{session_id}` | 聊天历史 |
| POST | `/api/knowledge/upload` | 上传文档 |
| GET | `/api/knowledge/documents` | 文档列表 |
| DELETE | `/api/knowledge/documents/{id}` | 删除文档 |
| POST | `/api/feedback` | 提交反馈 |
| GET | `/api/stats/overview` | 统计概览 |

## 开发约定

- **类型注解**：所有函数签名必须含类型注解
- **异步优先**：LLM 调用用 `async/await`，SSE 用 `AsyncGenerator`
- **无硬编码**：所有配置值来自 `config.Settings`
- **文件上限**：单文件 ≤ 400 行，单函数 ≤ 50 行
