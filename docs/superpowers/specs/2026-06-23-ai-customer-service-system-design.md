# AI 智能客服系统 - 设计文档

> 海慈科技 AI 开发工程师笔试题 | 2026-06-23

## 1. 技术选型

| 层 | 技术 | 选型原因 |
|---|------|----------|
| 前端 | React + TypeScript + Vite + shadcn/ui + Tailwind v4 | SPA 生态成熟，SSE 流式消费灵活，shadcn/ui 生产级组件 |
| 后端 | Python FastAPI | Python AI 生态不可替代，FastAPI 原生支持 SSE，异步性能好 |
| LLM | DeepSeek API (deepseek-chat) | 高性价比，兼容 OpenAI SDK，中文能力好 |
| Embedding | BGE-M3 (BAAI/bge-m3) | 中文检索 SOTA，本地运行无 API 成本，sentence-transformers 一键加载 |
| 向量库 | Milvus (Lite 嵌入式模式) | 企业级向量检索，Lite 模式零部署，支持 metadata 过滤 |
| 数据库 | MySQL | 结构化数据存储：用户、会话、消息、文档元数据 |
| RAG 框架 | 手动实现 + LlamaIndex 文档加载 | 笔试要求理解每一步，核心链路手写；文档解析复用 LlamaIndex Reader |

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                      前端 (React + TS)                    │
│  Vite + React Router + SSE 消费 + Markdown 渲染           │
└──────────────────────┬──────────────────────────────────┘
                       │ REST + SSE (流式)
┌──────────────────────▼──────────────────────────────────┐
│                  后端 (FastAPI)                           │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐     │
│  │ 用户/会话 │  │ 知识库管理│  │   RAG 核心模块     │     │
│  │ 模块     │  │ 模块      │  │   (手动实现)       │     │
│  │          │  │          │  │                    │     │
│  │ - 注册   │  │ - 上传   │  │  ┌──────────────┐ │     │
│  │ - 登录   │  │ - 列表   │  │  │ BGE-M3       │ │     │
│  │ - 会话   │  │ - 删除   │  │  │ (内嵌运行)   │ │     │
│  │          │  │          │  │  └──────────────┘ │     │
│  │          │  │          │  │ 文档解析→分块→    │     │
│  │          │  │          │  │ Embedding→Milvus  │     │
│  └──────────┘  └──────────┘  │ 检索→Prompt拼装   │     │
│                               │ → LLM→SSE流式     │     │
│                               └────────┬──────────┘     │
└──────────────────────────────────────┼──────────────────┘
                                       │
               ┌───────────────────────┼───────────────┐
               │                       │               │
               ▼                       ▼               ▼
          ┌─────────┐            ┌─────────┐    ┌──────────┐
          │  MySQL  │            │ Milvus  │    │ DeepSeek │
          │ (本地)  │            │ (本地)  │    │ (云端API)│
          │结构化数据│            │ 向量存储│    │  LLM推理 │
          └─────────┘            └─────────┘    └──────────┘
```

## 3. 数据库设计

### ER 关系
```
users 1──N sessions 1──N messages 1──N feedback
               │
documents（独立，与 messages 无 FK 关联，milvus 做桥接）
```

### 表结构

**users**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK AUTO_INCREMENT | |
| phone | VARCHAR(20) UNIQUE | 手机号登录 |
| email | VARCHAR(255) UNIQUE | 邮箱登录 |
| password_hash | VARCHAR(255) | bcrypt 哈希 |
| created_at | DATETIME | |

**sessions**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK AUTO_INCREMENT | |
| user_id | INT FK → users.id | |
| title | VARCHAR(100) | 首条消息截取前 30 字 |
| status | ENUM('active','closed') | |
| created_at | DATETIME | |
| updated_at | DATETIME | |

**messages**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK AUTO_INCREMENT | |
| session_id | INT FK → sessions.id | |
| role | ENUM('user','assistant') | 发言角色 |
| content | TEXT | 消息内容 |
| intent_tag | VARCHAR(50) NULL | 意图分类（加分项） |
| references | JSON NULL | `[{doc_name, snippet, score}]` 来源引用 |
| created_at | DATETIME | |

**feedback**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK AUTO_INCREMENT | |
| message_id | INT FK → messages.id | |
| rating | ENUM('positive','negative') | 赞/踩 |
| comment | TEXT NULL | 可选文字反馈 |
| created_at | DATETIME | |

**documents**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK AUTO_INCREMENT | |
| name | VARCHAR(255) | 文档名 |
| file_type | ENUM('txt','md','pdf') | |
| status | ENUM('processing','ready','failed') | 处理状态 |
| chunk_count | INT DEFAULT 0 | 分块数量 |
| file_size | INT | 文件大小(bytes) |
| milvus_ids | JSON | Milvus 主键 ID 数组 |
| error_msg | TEXT NULL | 失败原因 |
| created_at | DATETIME | |

## 4. RAG 核心链路

```
用户提问
  │
  ▼
1. 输入校验（长度≤500字 / 每日次数检查）
  │
  ▼
2. 意图识别（可选加分项：产品咨询/售后问题/闲聊/投诉）
  │
  ▼
3. 向量检索（问题 → BGE-M3 Embedding → Milvus 搜索）
   · Top-K = 5（可配置）
   · 相似度阈值 ≥ 0.65
   · 返回：片段内容 + 文档名 + 相似度分
  │
  ├── 检索为空? → 直接返回兜底话术，不调 LLM
  │
  ▼ 检索有结果
4. Prompt 拼装
   System Prompt + 历史消息（最近 N 轮）+ 检索片段（带来源标注）+ 用户问题
  │
  ▼
5. DeepSeek API 调用（stream=True）
   · 超时 30s
   · 重试 3 次，指数退避
  │
  ▼
6. SSE 流式输出 → 前端逐字渲染
```

### SSE 事件格式

| Event | 作用 | 数据格式 |
|-------|------|----------|
| `token` | 逐字文本 | `{"text": "字"}` |
| `sources` | 引用来源 | `{"references": [{doc_name, snippet, score}]}` |
| `error` | 异常 | `{"code": "...", "message": "..."}` |
| `done` | 流结束 | `{"message_id": 123, "intent": "产品咨询"}` |

### 可配置参数（.env）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| TOP_K | 5 | 检索返回片段数 |
| SIMILARITY_THRESHOLD | 0.65 | 相似度最低阈值 |
| MAX_HISTORY_ROUNDS | 5 | 携带最近 N 轮 |
| MAX_QUESTION_LENGTH | 500 | 单次提问上限 |
| DAILY_QUESTION_LIMIT | 100 | 每日提问上限 |
| LLM_TIMEOUT | 30 | LLM 超时秒数 |

## 5. AI 工程问题处理

### 5.1 检索为空 → 兜底话术

检索结果为空或所有片段相似度 < 阈值时，不调 LLM，直接返回预置话术（存配置文件）：
> 抱歉，我目前的知识库中暂时没有找到与您问题相关的信息。建议您联系人工客服获取帮助，或换一种方式描述您的问题。

### 5.2 上下文超长 → 分层截断

```
Token 预算分配（默认 8000 tokens）:
  System Prompt:      ~500 tokens（固定）
  历史对话:           ~1500 tokens（最近 N 轮，远端优先丢弃）
  检索片段:           ~5000 tokens（弹性，低分优先丢弃）
  用户当前问题:       ~500 tokens（不截）
  预留回答空间:       ~500 tokens

截断优先级:
  1. 检索片段按相似度倒排 → 低分片段优先丢弃
  2. 历史对话从最早开始丢弃 → 保留最近轮次
  3. 单片段过长时按句子边界截断 → 保持语义完整
```

### 5.3 LLM 幻觉 → 四层防御

| 层级 | 策略 | 机制 |
|------|------|------|
| L1 | System Prompt 约束 | 明确指令：只能根据知识库内容回答，不知道就说不知道 |
| L2 | 检索质量门槛 | 相似度 < 阈值直接丢弃，不给 LLM 喂不相关内容 |
| L3 | 来源强制标注 | 每条回答标注引用来源，前端展示，可追溯验证 |
| L4 | 用户反馈闭环 | 踩的答案记录日志，后续分析改进 Prompt |

### 5.4 System Prompt 设计

```
## 角色
你是智能客服助手，专门为用户解答产品相关问题。

## 核心规则（必须遵守）
1. 你只能根据下方【知识库内容】回答问题
2. 如果知识库中没有相关信息，必须回答："抱歉，我目前的知识库中暂未收录该信息"
3. 每条回答末尾必须标注引用来源：📚 参考：[文档名]

## 回答风格
- 简洁专业，先给出核心结论再展开说明
- 分点说明时使用有序列表
- 涉及流程时先概括再分步

## 知识库内容
{retrieved_chunks_formatted}

## 当前日期
{current_date}
```

### 5.5 加分项：大规模检索下的 LLM 执行保障

当知识库文档非常多（数十条检索结果）时：

```
策略：检索结果分层摘要 + 规则优先级排序

Step 1: 检索 Top-K=20 条片段
Step 2: 按相似度排序 → 去重（相同文档合并片段）
Step 3: Top-5 片段保持原文，其余 15 条生成摘要（用 LLM 二次摘要或规则提取）
Step 4: 以 "核心规则（原文）+ 补充规则（摘要）" 格式给 LLM
Step 5: 关键规则（如退换货时间限制、金额上限）用 ⚠️ 标记

验证方式:
  对比测试：直接给 LLM 送 20 条原文 vs 分层摘要
  评估指标：关键规则遗漏率、幻觉发生率、回答用时
```

## 6. API 设计

### 接口列表

| 方法 | 路径 | 说明 | 流式 |
|------|------|------|------|
| POST | `/api/auth/register` | 用户注册（手机号+邮箱+密码） | ❌ |
| POST | `/api/auth/login` | 登录返回 JWT | ❌ |
| GET | `/api/sessions` | 当前用户会话列表 | ❌ |
| POST | `/api/sessions` | 创建新会话 | ❌ |
| GET | `/api/sessions/{id}` | 会话详情（含消息列表） | ❌ |
| POST | `/api/chat/{session_id}` | 发送消息获取 AI 回复 | ✅ SSE |
| POST | `/api/feedback` | 提交反馈（赞/踩+可选文字） | ❌ |
| POST | `/api/knowledge/upload` | 上传文档（.txt/.md/.pdf） | ❌ |
| GET | `/api/knowledge/list` | 知识库文档列表 | ❌ |
| DELETE | `/api/knowledge/{id}` | 删除文档及向量 | ❌ |
| GET | `/api/stats/daily` | 当前用户今日提问次数 | ❌ |

### 聊天 SSE 接口详细

```
POST /api/chat/{session_id}
Authorization: Bearer <token>
Content-Type: application/json

Request:
{
  "content": "string (≤500字)",
  "intent": "string | null"
}

Response: text/event-stream
event: token
data: {"text": "单字"}

event: sources
data: {"references": [{"doc_name": "产品介绍.txt", "snippet": "...", "score": 0.92}]}

event: done
data: {"message_id": 456, "intent": "产品咨询"}

event: error
data: {"code": "DAILY_LIMIT_EXCEEDED", "message": "今日提问次数已达上限"}
```

### 错误码

| Code | 说明 |
|------|------|
| `DAILY_LIMIT_EXCEEDED` | 超每日提问上限 |
| `QUESTION_TOO_LONG` | 问题超 500 字 |
| `LLM_TIMEOUT` | LLM 调用超时 |
| `LLM_RATE_LIMITED` | API 限流 |
| `EMPTY_RETRIEVAL` | 检索无结果 |
| `DOC_PARSE_FAILED` | 文档解析失败 |

## 7. 前端设计

### 路由

| 路径 | 页面 | 组件 |
|------|------|------|
| `/login` | 登录 | LoginForm |
| `/register` | 注册 | RegisterForm |
| `/chat` | 主聊天页（新建会话） | ChatLayout |
| `/chat/:sessionId` | 历史会话 | ChatLayout |
| `/knowledge` | 知识库管理 | KnowledgeLayout |

### 组件树

```
App
├── AuthLayout
│   ├── LoginForm
│   └── RegisterForm
│
├── ChatLayout（三栏布局）
│   ├── Sidebar（会话列表 + 新建按钮）
│   ├── ChatMain（对话区）
│   │   ├── MessageList
│   │   │   ├── UserMessage（气泡右对齐）
│   │   │   └── BotMessage（气泡左对齐）
│   │   │       ├── MarkdownRenderer
│   │   │       ├── SourceCitation（📚 引用卡片）
│   │   │       ├── FeedbackButtons（👍/👎）
│   │   │       └── FollowupQuestions（追问建议）
│   │   ├── StreamingText（打字机效果）
│   │   └── ChatInput（字数统计 ≤500 + 发送按钮）
│   └── IntentTag（意图标签）
│
└── KnowledgeLayout
    ├── UploadZone（拖拽上传）
    ├── DocList（表格：名称/类型/状态/时间/操作）
    └── UploadProgress
```

### SSE 消费方案

`EventSource` API 不支持 POST 请求，使用 `fetch` + `ReadableStream` 手动解析：

```typescript
const response = await fetch(`/api/chat/${sessionId}`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
  body: JSON.stringify({ content: message }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = '';

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  // 按双换行分割 SSE events
  const events = buffer.split('\n\n');
  buffer = events.pop(); // 未完成部分留在 buffer
  for (const event of events) {
    parseSSEEvent(event); // 解析 event/data 行
  }
}
```

### 前端技术依赖

- `shadcn/ui` + `Tailwind v4` — 基础 UI 组件 + 样式
- `reactbits.dev` — 动效增强 (流式文本/消息入场动画)
- `zustand` — 全局状态（用户/sessions）
- `react-markdown` + `remark-gfm` — Markdown 渲染
- `react-router-dom` — 路由
- `lucide-react` — 图标

## 8. 后端项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置管理（.env 加载）
│   ├── dependencies.py         # 依赖注入（DB session/JWT）
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py             # 注册/登录
│   │   ├── sessions.py         # 会话 CRUD
│   │   ├── chat.py             # 聊天 SSE 接口（核心）
│   │   ├── feedback.py         # 反馈提交
│   │   ├── knowledge.py        # 知识库管理
│   │   └── stats.py            # 统计接口
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── session.py
│   │   ├── message.py
│   │   ├── feedback.py
│   │   └── document.py
│   │
│   ├── schemas/                # Pydantic 请求/响应模型
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── feedback.py
│   │   ├── knowledge.py
│   │   └── session.py
│   │
│   ├── services/               # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── session_service.py
│   │   ├── chat_service.py     # 聊天编排
│   │   ├── feedback_service.py
│   │   └── knowledge_service.py
│   │
│   └── rag/                    # RAG 核心模块（手动实现）
│       ├── __init__.py
│       ├── chunker.py          # 文档分块策略
│       ├── embedder.py         # BGE-M3 Embedding
│       ├── retriever.py        # Milvus 检索
│       ├── prompt.py           # Prompt 拼装
│       ├── llm.py              # DeepSeek API 调用
│       ├── stream.py           # SSE 生成器
│       └── fallback.py         # 兜底话术
│
├── db/
│   └── init.sql                # 建表语句 + 初始数据
│
├── data/                       # 运行时数据
│   ├── uploads/                # 上传文档存放
│   └── milvus/                 # Milvus Lite 持久化
│
├── example_docs/               # 初始测试文档
│   ├── 公司产品介绍.txt
│   ├── 常见问题FAQ.md
│   └── 退换货政策.txt
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 9. 前端项目结构

```
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── router.tsx
│   │
│   ├── api/
│   │   ├── client.ts           # axios/fetch 封装 + JWT 拦截
│   │   ├── auth.ts
│   │   ├── sessions.ts
│   │   ├── chat.ts             # SSE 流式调用
│   │   ├── feedback.ts
│   │   └── knowledge.ts
│   │
│   ├── stores/
│   │   ├── authStore.ts        # 用户状态
│   │   ├── sessionStore.ts     # 会话列表
│   │   └── chatStore.ts        # 当前聊天消息
│   │
│   ├── pages/
│   │   ├── LoginPage.tsx
│   │   ├── RegisterPage.tsx
│   │   ├── ChatPage.tsx
│   │   └── KnowledgePage.tsx
│   │
│   ├── components/
│   │   ├── ui/                 # 通用 UI 组件
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Tag.tsx
│   │   │   └── Spinner.tsx
│   │   ├── chat/
│   │   │   ├── ChatInput.tsx
│   │   │   ├── ChatBubble.tsx
│   │   │   ├── SourceCard.tsx
│   │   │   ├── FeedbackBar.tsx
│   │   │   └── StreamingText.tsx
│   │   ├── sidebar/
│   │   │   └── SessionList.tsx
│   │   └── knowledge/
│   │       ├── UploadZone.tsx
│   │       └── DocTable.tsx
│   │
│   ├── hooks/
│   │   ├── useSSE.ts           # SSE 流式消费 hook
│   │   ├── useAuth.ts
│   │   └── useCountdown.ts
│   │
│   ├── lib/
│   │   ├── sseParser.ts        # text/event-stream 解析
│   │   └── utils.ts
│   │
│   └── styles/
│       ├── global.css
│       ├── tokens.css          # CSS 变量
│       └── chat.css
│
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## 10. 文档提交清单

根据笔试题要求：

| 文档 | 内容要点 |
|------|----------|
| `docs/API文档.md` | 完整接口列表、请求/响应示例、SSE 事件格式 |
| `docs/数据库设计.md` | ER 图 + 表结构说明 |
| `docs/AI架构设计.md` | RAG 流程图（Mermaid）、Prompt 模板、向量检索策略 |
| `docs/业务流程说明.md` | 问答完整链路图 |
| `项目说明.md` | 技术选型原因、AI 架构图、业务思考（幻觉/空检索/上下文截断）、AI 工具使用体会 |
| `运行指南.md` | 模型/API 配置、环境变量说明、启动步骤 |

## 11. 开发顺序

| 天数 | 任务 |
|------|------|
| Day 1 | 环境搭建、数据库建表、后端骨架、BGE-M3 + Milvus 集成测试 |
| Day 2 | RAG 核心链路（chunking→embedding→retrieval→prompt→LLM→SSE） |
| Day 3 | 用户/会话/知识库 API + 前端聊天界面 + SSE 流式消费 |
| Day 4 | 前端完善、Prompt 调优、检索阈值测试、边界处理 |
| Day 5 | 文档编写、整体测试、提交 |

## 12. UI/UX 设计决策

> 决策日期：2026-06-23 | 基于 6 个设计站点调研

### 选型：方案 A · SaaS Light

| 设计层 | 选型 | 来源 |
|--------|------|------|
| 基础组件 | shadcn/ui (Button/Input/Card/Dialog/Sidebar/Badge/Avatar/Toast/Skeleton) | ui.shadcn.com |
| 动效增强 | reactbits.dev (流式文字入场/消息气泡 fadeInUp/打字光标闪烁) | reactbits.dev |
| 风格方向 | SaaS Light #05 — Indigo #6366f1 强调色 | designprompts.dev |
| 元素灵感 | Uiverse (赞/踩按钮/Loading 动画) | uiverse.io |
| 设计参考 | Awwwards (审美基准线) | awwwards.com |

### 设计令牌

```
主强调色: #6366f1 (Indigo)
主强调色-hover: #4f46e5
消息气泡(用户): bg-#6366f1 text-white
消息气泡(AI): bg-#f9fafb border-#f0f1f3
侧边栏: bg-#fafbfc border-#e8eaed
输入框: border-2 border-#e8eaed focus:border-#6366f1
引用卡片: bg-#eef2ff text-#5b63d3
字体: Inter / system-ui
圆角阶梯: 8px(sm) / 12px(md) / 14px(lg) / 16px(xl)
阴影: shadow-sm(消息) / shadow-md(卡片)
```

### 动效范围

- ✅ 流式文本 typing cursor 闪烁 (CSS @keyframes)
- ✅ 消息气泡 fadeInUp 入场 (CSS animation)
- ✅ 发送按钮 hover scale (transition)
- ✅ 会话列表 hover 状态 (transition)
- ❌ 背景动画 (Aurora/Beams) — 客服系统不宜太花哨
- ❌ BlobCursor — 与文字输入光标冲突

---

## 13. 待定 / 后续决策项

- [ ] 每日提问计数方案：Redis 计数器 vs MySQL 计数表（开发阶段用 MySQL，后续可切 Redis）
- [ ] 文件存储：本地上传 vs 对象存储（开发阶段本地，后续切 OSS）
- [ ] Milvus Collection Schema 设计（按文档分 Partition 或单 Collection + metadata 过滤）
- [ ] 意图识别实现方式（规则匹配 + LLM 分类 双重方案）
- [ ] 追问建议生成策略（LLM 二次调用 vs 规则模板）
- [ ] 多知识库路由（第二阶段）
