# API 文档

> AI 智能客服系统 v1.0 | 接口规范

## 概述

- **Base URL**: `http://localhost:8000/api`
- **认证方式**: JWT Bearer Token（登录后获取，Header: `Authorization: Bearer <token>`）
- **内容类型**: `application/json`（文件上传除外）
- **流式接口**: `text/event-stream` (SSE)

## 通用错误格式

所有非流式接口错误统一返回：

```json
{
  "detail": "错误描述信息"
}
```

HTTP 状态码遵循 REST 语义：
- `200` — 成功
- `400` — 请求参数错误
- `401` — 未认证 / Token 失效
- `404` — 资源不存在
- `429` — 请求频率超限
- `500` — 服务器内部错误

---

## 1. 认证模块

### 1.1 用户注册

```
POST /api/auth/register
```

**请求体**：

```json
{
  "phone": "13800138000",
  "email": "user@example.com",
  "password": "123456"
}
```

> 说明：`phone` 和 `email` 至少填一个。两个都填也可以。

**校验规则**：
- phone: 可选，11 位中国大陆手机号（正则 `/^1[3-9]\d{9}$/`）
- email: 可选，合法邮箱格式
- password: 必填，最少 6 位

**成功响应** (200)：

```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user_id": 1,
  "message": "注册成功"
}
```

**错误响应** (400)：

```json
{
  "detail": "该手机号已注册"
}
```

### 1.2 用户登录

```
POST /api/auth/login
```

**请求体**：

```json
{
  "account": "13800138000",
  "password": "123456"
}
```

> `account` 可以是手机号或邮箱。

**成功响应** (200)：

```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user_id": 1,
  "message": "登录成功"
}
```

**错误响应** (401)：

```json
{
  "detail": "账号或密码错误"
}
```

---

## 2. 会话模块

> 以下接口均需 Header: `Authorization: Bearer <token>`

### 2.1 获取会话列表

```
GET /api/sessions
```

**成功响应** (200)：

```json
{
  "sessions": [
    {
      "id": 1,
      "title": "退换货问题咨询",
      "status": "active",
      "message_count": 6,
      "created_at": "2026-06-23T10:00:00",
      "updated_at": "2026-06-23T14:30:00"
    }
  ],
  "total": 1
}
```

### 2.2 创建会话

```
POST /api/sessions
```

**请求体**：

```json
{
  "title": "新会话"
}
```

> `title` 可选，默认 "新会话"。

**成功响应** (200)：

```json
{
  "id": 2,
  "title": "新会话",
  "status": "active",
  "message_count": 0,
  "created_at": "2026-06-23T15:00:00",
  "updated_at": "2026-06-23T15:00:00"
}
```

### 2.3 获取会话详情

```
GET /api/sessions/{session_id}
```

**成功响应** (200)：

```json
{
  "id": 1,
  "title": "退换货问题咨询",
  "status": "active",
  "message_count": 2,
  "created_at": "2026-06-23T10:00:00",
  "updated_at": "2026-06-23T14:30:00",
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "退换货怎么操作？",
      "intent_tag": null,
      "references": null,
      "created_at": "2026-06-23T10:00:00"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "退换货流程如下：\n\n1. 登录账户...",
      "intent_tag": "售后问题",
      "references": [
        {
          "doc_name": "退换货政策.txt",
          "snippet": "退换货流程：1. 登录账户...",
          "score": 0.92
        }
      ],
      "created_at": "2026-06-23T10:00:05"
    }
  ]
}
```

---

## 3. 聊天模块（核心）

### 3.1 发送消息（SSE 流式）

```
POST /api/chat/{session_id}
Content-Type: application/json
Authorization: Bearer <token>
```

**请求体**：

```json
{
  "content": "退换货流程是什么？"
}
```

> `content` 长度限制：≤ 500 字（通过 `.env` 可配置 `MAX_QUESTION_LENGTH`）

**响应格式**: `text/event-stream` (SSE)

#### SSE 事件类型

##### `event: token` — 逐字文本

```
event: token
data: {"text": "退"}

event: token
data: {"text": "换"}

event: token
data: {"text": "货"}
```

> LLM 每生成一个 token 推送一个 event。前端应逐字追加渲染，实现打字机效果。

##### `event: sources` — 引用来源

```
event: sources
data: {"references": [{"doc_name": "退换货政策.txt", "snippet": "退换货流程：1. 登录账户，进入\"我的订单\"...", "score": 0.92}]}
```

> 在所有 token 推送完毕后发送。包含本次回答引用的知识库文档名称、片段摘要和相似度得分。

##### `event: done` — 流结束

```
event: done
data: {"message_id": 456, "references": [{"doc_name": "退换货政策.txt", "snippet": "...", "score": 0.92}]}
```

> 正常完成标记。`message_id` 为数据库中的消息 ID。前端收到此事件后可停止流式渲染。

##### `event: error` — 异常

```
event: error
data: {"code": "DAILY_LIMIT_EXCEEDED", "message": "今日提问次数已达上限（100次），请明日再试"}
```

**流式错误码**：

| Code | 说明 | 触发条件 |
|------|------|----------|
| `DAILY_LIMIT_EXCEEDED` | 超每日上限 | 当日提问 ≥ 100 次 |
| `QUESTION_TOO_LONG` | 问题过长 | 问题 > 500 字 |
| `LLM_TIMEOUT` | LLM 超时 | DeepSeek 响应 > 30s |
| `LLM_RATE_LIMITED` | API 限流 | DeepSeek 限流 |
| `EMPTY_RETRIEVAL` | 检索无结果 | Milvus 检索为空/低于阈值 |
| `INTERNAL_ERROR` | 内部错误 | 其他未预期异常 |

#### 前端 SSE 消费示例

```typescript
// 注意：不能用 EventSource（不支持 POST），用 fetch + ReadableStream
const response = await fetch(`/api/chat/${sessionId}`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  },
  body: JSON.stringify({ content: message }),
});

const reader = response.body!.getReader();
const decoder = new TextDecoder();
let buffer = '';

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  buffer += decoder.decode(value, { stream: true });
  const events = buffer.split('\n\n');
  buffer = events.pop() || '';  // 未完整的事件留在 buffer

  for (const event of events) {
    const eventMatch = event.match(/^event: (\w+)$/m);
    const dataMatch = event.match(/^data: (.+)$/m);
    if (!eventMatch || !dataMatch) continue;

    const type = eventMatch[1];
    const data = JSON.parse(dataMatch[1]);

    switch (type) {
      case 'token':    onTokenReceived(data.text); break;
      case 'sources':  onSourcesReceived(data.references); break;
      case 'done':     onStreamDone(data); break;
      case 'error':    onStreamError(data.code, data.message); break;
    }
  }
}
```

#### curl 测试

```bash
# 流式调用（-N 禁用缓冲，逐行输出）
curl -N -X POST "http://localhost:8000/api/chat/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"退换货流程是什么？"}'
```

**期望输出**：

```
event: token
data: {"text":"退"}

event: token
data: {"text":"换"}

event: token
data: {"text":"货"}

...

event: sources
data: {"references":[{"doc_name":"退换货政策.txt","snippet":"退换货流程...","score":0.92}]}

event: done
data: {"message_id":123}
```

**非流式错误响应**（请求校验失败时，非 SSE）：

```json
{
  "detail": "问题长度不能超过 500 字"
}
```

---

## 4. 反馈模块

### 4.1 提交反馈

```
POST /api/feedback
Authorization: Bearer <token>
```

**请求体**：

```json
{
  "message_id": 456,
  "rating": "positive",
  "comment": null
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message_id | int | ✅ | AI 消息的 ID |
| rating | string | ✅ | `"positive"` (赞) 或 `"negative"` (踩) |
| comment | string ❌ | 踩时的文字说明（可选） |

**成功响应** (200)：

```json
{
  "id": 1,
  "message": "反馈提交成功"
}
```

---

## 5. 知识库模块

### 5.1 上传文档

```
POST /api/knowledge/upload
Content-Type: multipart/form-data
Authorization: Bearer <token>
```

**表单字段**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | ✅ | 文档文件 |

**支持格式**：`.txt` / `.md` / `.pdf`
**大小限制**：≤ 10MB

**成功响应** (200)：

```json
{
  "id": 1,
  "name": "产品介绍.txt",
  "file_type": "txt",
  "status": "ready",
  "chunk_count": 8,
  "file_size": 2048,
  "created_at": "2026-06-23T10:00:00"
}
```

> 上传后自动触发向量入库。`status` 初始为 `"processing"`，完成后变为 `"ready"` 或 `"failed"`。

**错误响应**：

```json
{
  "detail": "不支持的文件格式: docx，仅支持 {'txt', 'md', 'pdf'}"
}
```

或

```json
{
  "detail": "文件大小不能超过 10MB"
}
```

### 5.2 文档列表

```
GET /api/knowledge/list
Authorization: Bearer <token>
```

**成功响应** (200)：

```json
{
  "documents": [
    {
      "id": 1,
      "name": "产品介绍.txt",
      "file_type": "txt",
      "status": "ready",
      "chunk_count": 8,
      "file_size": 2048,
      "created_at": "2026-06-23T10:00:00"
    },
    {
      "id": 2,
      "name": "常见问题FAQ.md",
      "file_type": "md",
      "status": "processing",
      "chunk_count": 0,
      "file_size": 3500,
      "created_at": "2026-06-23T10:05:00"
    }
  ],
  "total": 2
}
```

**status 说明**：

| 值 | 含义 |
|----|------|
| `processing` | 正在解析和向量化 |
| `ready` | 向量化完毕，可用于检索 |
| `failed` | 处理失败（检查 `error_msg`） |

### 5.3 删除文档

```
DELETE /api/knowledge/{doc_id}
Authorization: Bearer <token>
```

**成功响应** (200)：

```json
{
  "message": "删除成功"
}
```

> 删除文档同时清除 Milvus 中对应的所有向量数据。

**错误响应** (404)：

```json
{
  "detail": "文档不存在"
}
```

---

## 6. 统计模块

### 6.1 今日提问次数

```
GET /api/stats/daily
Authorization: Bearer <token>
```

**成功响应** (200)：

```json
{
  "date": "2026-06-23",
  "count": 5
}
```

---

## 7. 健康检查

```
GET /api/health
```

**响应** (200)：

```json
{
  "status": "ok",
  "service": "ICS Customer Service"
}
```

---

## 附录：接口速查表

| 方法 | 路径 | 认证 | 流式 | 说明 |
|------|------|------|------|------|
| POST | `/api/auth/register` | ❌ | ❌ | 用户注册 |
| POST | `/api/auth/login` | ❌ | ❌ | 用户登录 |
| GET | `/api/sessions` | ✅ | ❌ | 会话列表 |
| POST | `/api/sessions` | ✅ | ❌ | 创建会话 |
| GET | `/api/sessions/{id}` | ✅ | ❌ | 会话详情 |
| **POST** | **`/api/chat/{session_id}`** | ✅ | ✅ **SSE** | **发送消息** |
| POST | `/api/feedback` | ✅ | ❌ | 提交反馈 |
| POST | `/api/knowledge/upload` | ✅ | ❌ | 上传文档 |
| GET | `/api/knowledge/list` | ✅ | ❌ | 文档列表 |
| DELETE | `/api/knowledge/{id}` | ✅ | ❌ | 删除文档 |
| GET | `/api/stats/daily` | ✅ | ❌ | 今日次数 |
| GET | `/api/health` | ❌ | ❌ | 健康检查 |
