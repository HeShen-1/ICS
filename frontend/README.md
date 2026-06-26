# 前端 — AI 智能客服系统

> React 19 + TypeScript + Vite + Tailwind v4 + shadcn/ui

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 框架 | React 19 + TypeScript | SPA |
| 构建 | Vite | HMR 开发服务器 |
| CSS | Tailwind CSS v4 | utility-first |
| UI 组件 | shadcn/ui | Button/Input/Card/Sidebar |
| 图标 | lucide-react | 轻量开源图标 |
| 状态管理 | Zustand | 全局状态 |
| 路由 | React Router v6 | SPA 路由 |

## 目录结构

```
frontend/src/
├── api/                 # HTTP 请求 + SSE 消费
│   ├── client.ts        #   fetch 封装 + JWT 拦截
│   ├── auth.ts          #   注册/登录
│   ├── sessions.ts      #   会话 CRUD
│   ├── chat.ts          #   SSE 流式消费
│   ├── knowledge.ts     #   文档上传/管理
│   └── feedback.ts      #   赞/踩反馈
├── stores/              # Zustand 状态
│   ├── authStore.ts     #   认证状态
│   ├── sessionStore.ts  #   会话列表
│   └── chatStore.ts     #   聊天消息+流式
├── pages/               # 页面
│   ├── LoginPage.tsx    #   登录
│   ├── RegisterPage.tsx #   注册
│   ├── ChatPage.tsx     #   聊天主页
│   └── KnowledgePage.tsx #  知识库管理
├── components/          # 组件
│   ├── chat/            #   聊天组件 (Input/Bubble/SourceCard/FeedbackBar)
│   ├── sidebar/         #   侧边栏 (SessionList)
│   ├── knowledge/       #   知识库组件 (UploadZone/DocTable)
│   └── ui/              #   通用组件 (Button/Input/Card)
├── hooks/               # 自定义 Hook
│   ├── useSSE.ts        #   SSE 流式消费
│   └── useAuth.ts       #   认证状态
├── lib/                 # 工具
│   ├── sseParser.ts     #   SSE 事件解析
│   └── utils.ts
└── styles/              # 样式
    └── global.css       #   Tailwind + 自定义动画
```

## 快速启动

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173
```

## 代理配置

Vite 开发代理 (`vite.config.ts`): `/api` 请求自动转发到后端 `http://localhost:8000`。

## SSE 流式消费

前端使用 `fetch` + `ReadableStream` + `TextDecoder` 消费 SSE 流（不支持 `EventSource`，因为需要 POST 请求）。

SSE 事件类型:
- `event: token` — 逐字文本（打字机效果）
- `event: sources` — 引用来源列表
- `event: done` — 流结束
- `event: error` — 异常（超时/限流/空检索等）

## 设计令牌

| 令牌 | 值 |
|------|-----|
| 主强调色 | #6366f1 (Indigo-500) |
| 字体 | Inter, -apple-system, sans-serif |
| 用户气泡 | bg-indigo-500 text-white rounded-(16px 16px 4px 16px) |
| AI 气泡 | bg-gray-50 border rounded-(16px 16px 16px 4px) |
