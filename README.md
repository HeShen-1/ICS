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
│   ├── tests/                   # 后端测试 (112 用例, 84% 覆盖率)
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
│   └── vite.config.ts
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
用户提问 → 输入校验(≤500字/≤100次/天)
          → 意图识别(关键词+LLM)
          → BGE-M3 向量化
          → Milvus HNSW 检索(top_k=12, threshold=0.55)
          → 三层降级检索(kb路由→全局→低阈值兜底0.35)
          → 检索为空? → 兜底话术(不调LLM)
          → 检索有结果? → 分类去重(关键规则优先)
                        → Token 预算控制(运行计数器O(n))
                        → Prompt 拼接(System+历史+知识+日期)
                        → DeepSeek 流式生成
                        → SSE 逐字输出 + 引用来源
                        → 保存消息 + 反馈统计
```

## AI 工程特性

### 幻觉防御（四层）

| 层级 | 策略 | 说明 |
|------|------|------|
| **Prompt 约束** | 5 条硬规则，禁止编造/评价竞品 | 从源头减少幻觉 |
| **检索门槛** | 相似度阈值 0.55 过滤，0.35 兜底 | 不给 LLM 喂不相关内容 |
| **来源标注** | 每条回答 📚 参考：文档名 | 可追溯可验证 |
| **反馈闭环** | 踩的记录写入 feedback 表 | 持续迭代优化 |

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

## 运行测试

```bash
# 后端
cd backend
pytest tests/ -q                         # 112 个用例
pytest tests/ --cov=app --cov-report=term-missing

# 前端
cd frontend
npx vitest run                           # 33 个用例
```

## 许可证

本项目基于 [Apache License 2.0](LICENSE) 开源。

---

**ICS** — Intelligent Customer Service，让 AI 成为最懂业务的客服助手。
