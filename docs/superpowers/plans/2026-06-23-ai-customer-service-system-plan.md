# AI 智能客服系统 - 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建基于 DeepSeek API + BGE-M3 + Milvus 的 RAG 智能客服系统，支持文档上传/向量化/语义检索/流式 AI 回答/多轮对话/反馈。

**Architecture:** React + TypeScript 前端直连 Python FastAPI 后端。后端分 Web 层（auth/sessions/chat/knowledge API）+ RAG 层（chunker/embedder/retriever/prompt/llm/stream）。MySQL 存结构化数据，Milvus Lite 存向量，BGE-M3 本地生成 embedding，DeepSeek API 提供 LLM。

**Tech Stack:** React 19 + TypeScript + Vite + Tailwind v4 + shadcn/ui + reactbits.dev + Zustand + react-markdown + lucide-react | Python 3.12 + FastAPI + SQLAlchemy + PyMySQL + sentence-transformers + pymilvus + openai (DeepSeek 兼容) | MySQL 8.0 | Milvus Lite

---

## Phase 1: 项目脚手架 & 基础设施 (Day 1 上午)

### Task 1: 项目目录初始化

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/.gitignore`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/db/init.sql`

- [ ] **Step 1: 创建后端目录结构**

```bash
cd D:/vsCode/ICS
mkdir -p backend/app/{api,models,schemas,services,rag}
mkdir -p backend/db backend/data/uploads backend/data/milvus backend/example_docs
```

- [ ] **Step 2: 编写 `backend/requirements.txt`**

```text
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.35
pymysql==1.1.1
cryptography==43.0.0
pydantic==2.9.0
pydantic-settings==2.5.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.12
sentence-transformers==3.1.1
pymilvus==2.4.5
openai==1.51.0
llama-index-core==0.11.0
llama-index-readers-file==0.2.0
aiofiles==24.1.0
httpx==0.27.2
```

- [ ] **Step 3: 编写 `backend/.env.example`**

```ini
# Database
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=ics_customer_service

# DeepSeek API
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# Embedding (BGE-M3 本地模型)
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_DEVICE=cpu

# Milvus
MILVUS_DB_PATH=./data/milvus/ics_knowledge.db

# JWT
JWT_SECRET_KEY=change-me-to-a-random-secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# App
UPLOAD_DIR=./data/uploads
MAX_QUESTION_LENGTH=500
DAILY_QUESTION_LIMIT=100
TOP_K=5
SIMILARITY_THRESHOLD=0.65
MAX_HISTORY_ROUNDS=5
LLM_TIMEOUT=30
MAX_CONTEXT_TOKENS=8000
```

- [ ] **Step 4: 编写 `backend/.gitignore`**

```gitignore
__pycache__/
*.pyc
.env
data/
.venv/
*.egg-info/
dist/
```

- [ ] **Step 5: 编写 `backend/app/__init__.py`** (空文件)

```bash
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/models/__init__.py
touch backend/app/schemas/__init__.py
touch backend/app/services/__init__.py
touch backend/app/rag/__init__.py
```

- [ ] **Step 6: 编写 `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "ics_customer_service"

    # DeepSeek API
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # Embedding
    embedding_model: str = "BAAI/bge-m3"
    embedding_device: str = "cpu"

    # Milvus
    milvus_db_path: str = "./data/milvus/ics_knowledge.db"

    # JWT
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # App
    upload_dir: str = "./data/uploads"
    max_question_length: int = 500
    daily_question_limit: int = 100
    top_k: int = 5
    similarity_threshold: float = 0.65
    max_history_rounds: int = 5
    llm_timeout: int = 30
    max_context_tokens: int = 8000

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 7: 编写 `backend/db/init.sql`**

```sql
CREATE DATABASE IF NOT EXISTS ics_customer_service
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE ics_customer_service;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  phone VARCHAR(20) UNIQUE,
  email VARCHAR(255) UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS sessions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  title VARCHAR(100) DEFAULT '新会话',
  status ENUM('active','closed') DEFAULT 'active',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS messages (
  id INT AUTO_INCREMENT PRIMARY KEY,
  session_id INT NOT NULL,
  role ENUM('user','assistant') NOT NULL,
  content TEXT NOT NULL,
  intent_tag VARCHAR(50) DEFAULT NULL,
  references_json JSON DEFAULT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS feedback (
  id INT AUTO_INCREMENT PRIMARY KEY,
  message_id INT NOT NULL,
  rating ENUM('positive','negative') NOT NULL,
  comment TEXT DEFAULT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS documents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  file_type ENUM('txt','md','pdf') NOT NULL,
  status ENUM('processing','ready','failed') DEFAULT 'processing',
  chunk_count INT DEFAULT 0,
  file_size INT DEFAULT 0,
  milvus_ids JSON DEFAULT NULL,
  error_msg TEXT DEFAULT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS daily_question_count (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  query_date DATE NOT NULL,
  count INT DEFAULT 0,
  UNIQUE KEY uk_user_date (user_id, query_date),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;
```

- [ ] **Step 8: 编写 `backend/app/main.py`**

```python
"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ICS Customer Service API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "ICS Customer Service"}
```

- [ ] **Step 9: 验证后端启动**

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate  # Windows
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 MySQL 密码
uvicorn app.main:app --reload --port 8000
```

Expected: 访问 `http://localhost:8000/api/health` 返回 `{"status": "ok"}`

- [ ] **Step 10: 初始化前端项目**

```bash
cd D:/vsCode/ICS
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-router-dom zustand react-markdown remark-gfm lucide-react
npm install -D @types/node tailwindcss @tailwindcss/vite
```

- [ ] **Step 10b: 配置 Tailwind CSS v4**

Create `frontend/src/styles/global.css` (will be extended later):
```css
@import "tailwindcss";
```

Modify `frontend/src/main.tsx` to import:
```typescript
import './styles/global.css';
```

- [ ] **Step 11: 配置 Vite 代理 + Tailwind 插件**

Modify `frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 12: 验证前端启动**

```bash
cd frontend
npm run dev
```

Expected: 访问 `http://localhost:5173` 看到 Vite + React 默认页面

- [ ] **Step 13: Commit**

```bash
git add -A
git commit -m "chore: project scaffolding - FastAPI backend + React frontend"
```

---

### Task 2: 后端基础层 - 数据库连接 & 模型

**Files:**
- Create: `backend/app/database.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/session.py`
- Create: `backend/app/models/message.py`
- Create: `backend/app/models/feedback.py`
- Create: `backend/app/models/document.py`

- [ ] **Step 1: 编写数据库连接 `backend/app/database.py`**

```python
"""数据库连接管理"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: 编写 User 模型 `backend/app/models/user.py`**

```python
"""用户模型"""
from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), unique=True, nullable=True)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 3: 编写 Session 模型 `backend/app/models/session.py`**

```python
"""会话模型"""
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class SessionStatus(str, enum.Enum):
    active = "active"
    closed = "closed"


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(100), default="新会话")
    status = Column(Enum(SessionStatus), default=SessionStatus.active)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    messages = relationship("Message", back_populates="session", order_by="Message.created_at")
```

- [ ] **Step 4: 编写 Message 模型 `backend/app/models/message.py`**

```python
"""消息模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    intent_tag = Column(String(50), nullable=True)
    references_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    session = relationship("Session", back_populates="messages")
```

- [ ] **Step 5: 编写 Feedback 模型 `backend/app/models/feedback.py`**

```python
"""反馈模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, func
from app.database import Base
import enum


class FeedbackRating(str, enum.Enum):
    positive = "positive"
    negative = "negative"


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Enum(FeedbackRating), nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 6: 编写 Document 模型 `backend/app/models/document.py`**

```python
"""知识库文档模型"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, func
from sqlalchemy.dialects.mysql import JSON
from app.database import Base
import enum


class DocumentStatus(str, enum.Enum):
    processing = "processing"
    ready = "ready"
    failed = "failed"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    file_type = Column(Enum("txt", "md", "pdf"), nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.processing)
    chunk_count = Column(Integer, default=0)
    file_size = Column(Integer, default=0)
    milvus_ids = Column(JSON, nullable=True)
    error_msg = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

- [ ] **Step 7: 验证模型导入**

```bash
cd backend
python -c "from app.models.user import User; from app.models.session import Session; from app.models.message import Message; from app.models.feedback import Feedback; from app.models.document import Document; print('All models imported OK')"
```

Expected: `All models imported OK`

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: add database connection and ORM models"
```

---

## Phase 2: RAG 核心模块 (Day 1 下午 - Day 2)

### Task 3: RAG - 文档分块器 (Chunker)

**Files:**
- Create: `backend/app/rag/chunker.py`

- [ ] **Step 1: 编写 Chunker `backend/app/rag/chunker.py`**

```python
"""文档分块模块
策略: 按段落分块 + 滑动窗口重叠，保持语义完整性
"""
from typing import List, Dict
import re


class TextChunker:
    """文本分块器"""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str, metadata: Dict[str, str] = None) -> List[Dict]:
        """
        将文本切分为带 metadata 的 chunk 列表

        Args:
            text: 原始文本
            metadata: 附加信息（如文档名）

        Returns:
            [{text: "片段内容", metadata: {source: "文档名", chunk_index: 0}}, ...]
        """
        if not text or not text.strip():
            return []

        meta = metadata or {}

        # Step 1: 按段落分割
        paragraphs = self._split_paragraphs(text)

        # Step 2: 合并短段落 + 切分长段落
        chunks = self._merge_and_split(paragraphs)

        # Step 3: 添加 metadata
        return [
            {
                "text": chunk.strip(),
                "metadata": {
                    **meta,
                    "chunk_index": i,
                    "char_count": len(chunk.strip()),
                },
            }
            for i, chunk in enumerate(chunks)
            if chunk.strip()
        ]

    def _split_paragraphs(self, text: str) -> List[str]:
        """按双换行/单换行/标题分割段落"""
        # 先按双换行分
        parts = re.split(r"\n\s*\n", text)
        # 每个部分再按单换行分（保留较短的段落）
        result = []
        for part in parts:
            lines = part.split("\n")
            result.extend(line.strip() for line in lines if line.strip())
        return result

    def _merge_and_split(self, paragraphs: List[str]) -> List[str]:
        """合并短段落，切分长段落"""
        chunks = []
        current = ""

        for para in paragraphs:
            if len(current) + len(para) + 1 <= self.chunk_size:
                current = (current + "\n" + para).strip() if current else para
            else:
                if current:
                    chunks.append(current)
                # 长段落进一步切分
                if len(para) > self.chunk_size:
                    for i in range(0, len(para), self.chunk_size - self.chunk_overlap):
                        chunks.append(para[i : i + self.chunk_size])
                else:
                    current = para

        if current:
            chunks.append(current)

        return chunks
```

- [ ] **Step 2: 验证 Chunker**

```bash
cd backend
python -c "
from app.rag.chunker import TextChunker
c = TextChunker(chunk_size=100, chunk_overlap=20)
text = '第一段内容。' * 20 + '\n\n第二段内容。' * 20
chunks = c.chunk(text, {'source': 'test.txt'})
print(f'Total chunks: {len(chunks)}')
for i, ch in enumerate(chunks[:3]):
    print(f'Chunk {i}: {len(ch[\"text\"])} chars, meta={ch[\"metadata\"]}')
"
```

Expected: 合理分块数，每块携带 metadata

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: add document chunker with paragraph-aware splitting"
```

---

### Task 4: RAG - Embedding 模块 (Embedder)

**Files:**
- Create: `backend/app/rag/embedder.py`

- [ ] **Step 1: 编写 Embedder `backend/app/rag/embedder.py`**

```python
"""Embedding 模块 - BGE-M3 本地模型"""
from typing import List
from sentence_transformers import SentenceTransformer
from app.config import get_settings


class Embedder:
    """BGE-M3 Embedding 封装"""

    def __init__(self):
        settings = get_settings()
        self.model_name = settings.embedding_model
        self.device = settings.embedding_device
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        """懒加载模型"""
        if self._model is None:
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
            )
        return self._model

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成 embedding 向量

        Args:
            texts: 文本列表

        Returns:
            embedding 向量列表，每个向量维度 1024
        """
        if not texts:
            return []

        # BGE-M3 对查询需要添加前缀以提升检索效果
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """单条查询 embedding（自动添加 BGE 查询前缀）"""
        # BGE 模型官方推荐查询加前缀
        return self.embed([query])[0]

    @property
    def dimension(self) -> int:
        """返回 embedding 维度"""
        return self.model.get_sentence_embedding_dimension()
```

- [ ] **Step 2: 验证 Embedder（首次运行会下载模型 ~2GB）**

```bash
cd backend
python -c "
from app.rag.embedder import Embedder
e = Embedder()
vec = e.embed_query('你好，这是一个测试句子')
print(f'Embedding dimension: {len(vec)}')
print(f'First 5 values: {vec[:5]}')
"
```

Expected: `Embedding dimension: 1024` （BGE-M3 维度）

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: add BGE-M3 embedding module"
```

---

### Task 5: RAG - Milvus 向量存储 & 检索

**Files:**
- Create: `backend/app/rag/vector_store.py`

- [ ] **Step 1: 编写 VectorStore `backend/app/rag/vector_store.py`**

```python
"""Milvus 向量存储与检索"""
from typing import List, Dict, Optional
from pymilvus import (
    MilvusClient,
    DataType,
    connections,
)
from app.config import get_settings


class VectorStore:
    """Milvus 向量存储封装"""

    COLLECTION_NAME = "knowledge_chunks"
    _instance: Optional["VectorStore"] = None

    def __init__(self):
        settings = get_settings()
        self.db_path = settings.milvus_db_path
        self.dimension = 1024  # BGE-M3 维度
        self._client: MilvusClient | None = None

    @property
    def client(self) -> MilvusClient:
        """懒加载 Milvus 客户端"""
        if self._client is None:
            self._client = MilvusClient(self.db_path)
            self._ensure_collection()
        return self._client

    def _ensure_collection(self):
        """确保 collection 存在"""
        if self.client.has_collection(self.COLLECTION_NAME):
            return

        self.client.create_collection(
            collection_name=self.COLLECTION_NAME,
            dimension=self.dimension,
            metric_type="COSINE",
            auto_id=True,
            enable_dynamic_field=True,
        )

    def insert_chunks(self, chunks: List[Dict], embeddings: List[List[float]]) -> List[int]:
        """
        批量插入 chunk + embedding

        Args:
            chunks: [{text: str, metadata: {source: str, ...}}, ...]
            embeddings: [vec1, vec2, ...]

        Returns:
            插入的 Milvus 主键 ID 列表
        """
        if not chunks or not embeddings:
            return []

        data = []
        for chunk, emb in zip(chunks, embeddings):
            data.append({
                "vector": emb,
                "text": chunk["text"],
                "source": chunk["metadata"].get("source", "unknown"),
                "chunk_index": chunk["metadata"].get("chunk_index", 0),
            })

        result = self.client.insert(
            collection_name=self.COLLECTION_NAME,
            data=data,
        )
        return result.get("ids", [])

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        threshold: float = 0.65,
        filter_expr: Optional[str] = None,
    ) -> List[Dict]:
        """
        向量相似度检索

        Args:
            query_embedding: 查询 embedding
            top_k: 返回 Top-K
            threshold: 相似度阈值
            filter_expr: Milvus 过滤表达式, 如 'source == "产品介绍.txt"'

        Returns:
            [{text, source, chunk_index, score}, ...]
        """
        results = self.client.search(
            collection_name=self.COLLECTION_NAME,
            data=[query_embedding],
            limit=top_k,
            output_fields=["text", "source", "chunk_index"],
            filter=filter_expr,
        )

        hits = []
        for hit in results[0]:
            if hit["distance"] >= threshold:
                hits.append({
                    "text": hit["entity"]["text"],
                    "source": hit["entity"]["source"],
                    "chunk_index": hit["entity"]["chunk_index"],
                    "score": round(hit["distance"], 4),
                })
        return hits

    def delete_by_ids(self, ids: List[int]):
        """按 ID 删除向量"""
        if ids:
            self.client.delete(
                collection_name=self.COLLECTION_NAME,
                ids=ids,
            )

    def count(self) -> int:
        """返回向量总数"""
        return self.client.query(
            collection_name=self.COLLECTION_NAME,
            filter="id >= 0",
            output_fields=["count(*)"],
        )[0].get("count(*)", 0) if self.client.has_collection(self.COLLECTION_NAME) else 0

    def drop_collection(self):
        """删除整个 collection（重置用）"""
        if self.client.has_collection(self.COLLECTION_NAME):
            self.client.drop_collection(self.COLLECTION_NAME)
```

- [ ] **Step 2: 验证 Milvus 读写**

```bash
cd backend
python -c "
from app.rag.vector_store import VectorStore
vs = VectorStore()
print(f'Vector count before: {vs.count()}')
# 插入测试向量
ids = vs.insert_chunks(
    [{'text': '测试内容', 'metadata': {'source': 'test.txt', 'chunk_index': 0}}],
    [[0.1] * 1024]
)
print(f'Inserted IDs: {ids}')
print(f'Vector count after: {vs.count()}')
vs.delete_by_ids(ids)
print(f'Vector count after delete: {vs.count()}')
"
```

Expected: 插入后 count=1, 删除后 count=0

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: add Milvus vector store with CRUD operations"
```

---

### Task 6: RAG - 文档解析与入库服务

**Files:**
- Create: `backend/app/rag/ingestion.py`

- [ ] **Step 1: 编写文档入库服务 `backend/app/rag/ingestion.py`**

```python
"""文档解析与入库服务"""
import os
from typing import Dict
from pathlib import Path
from app.rag.chunker import TextChunker
from app.rag.embedder import Embedder
from app.rag.vector_store import VectorStore


class DocumentIngestion:
    """文档入库：解析 → 分块 → Embedding → 存入 Milvus"""

    def __init__(self):
        self.chunker = TextChunker()
        self.embedder = Embedder()
        self.vector_store = VectorStore()

    def ingest_file(self, file_path: str) -> Dict:
        """
        处理单个文件并入库

        Args:
            file_path: 文件路径

        Returns:
            {
                "success": True/False,
                "chunk_count": int,
                "milvus_ids": [id1, id2, ...],
                "error": str | None,
            }
        """
        try:
            # 1. 读取文件内容
            text = self._read_file(file_path)
            if not text:
                return {"success": False, "chunk_count": 0, "milvus_ids": [], "error": "文件内容为空"}

            # 2. 分块
            doc_name = os.path.basename(file_path)
            chunks = self.chunker.chunk(text, metadata={"source": doc_name})
            if not chunks:
                return {"success": False, "chunk_count": 0, "milvus_ids": [], "error": "分块结果为空"}

            # 3. 批量生成 Embedding
            chunk_texts = [c["text"] for c in chunks]
            embeddings = self.embedder.embed(chunk_texts)

            # 4. 批量写入 Milvus
            milvus_ids = self.vector_store.insert_chunks(chunks, embeddings)

            return {
                "success": True,
                "chunk_count": len(chunks),
                "milvus_ids": milvus_ids,
                "error": None,
            }
        except Exception as e:
            return {"success": False, "chunk_count": 0, "milvus_ids": [], "error": str(e)}

    def _read_file(self, file_path: str) -> str:
        """读取文件内容，支持 .txt / .md / .pdf"""
        ext = Path(file_path).suffix.lower()

        if ext in (".txt", ".md"):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

        if ext == ".pdf":
            # 使用 llama-index 读取 PDF
            from llama_index.readers.file import PDFReader
            reader = PDFReader()
            documents = reader.load_data(file=Path(file_path))
            return "\n\n".join(doc.text for doc in documents)

        raise ValueError(f"不支持的文件格式: {ext}")
```

- [ ] **Step 2: 创建示例文档用于测试**

`backend/example_docs/公司产品介绍.txt`：

```text
# 海慈科技智能客服系统产品介绍

## 产品概述
海慈智能客服系统是一套基于人工智能技术的企业级客服解决方案。系统支持多渠道接入（网页、APP、微信公众号），能够自动回答用户常见问题，大幅降低企业客服人力成本。

## 核心功能

### 1. 智能问答
系统支持基于知识库的智能问答，用户输入问题后，AI 自动检索相关知识并生成准确回答。回答准确率可达 95% 以上。

### 2. 多轮对话
支持上下文感知的多轮对话，AI 能够理解对话历史，提供连贯的交互体验。

### 3. 知识库管理
企业可自行上传产品文档、FAQ、政策文件等，系统自动解析并索引，无需人工标注。

### 4. 数据分析
提供问答统计、用户满意度分析、热点问题识别等数据分析功能，帮助企业持续优化服务质量。

## 产品版本

| 版本 | 价格 | 功能 |
|------|------|------|
| 基础版 | ¥999/月 | 1000次/天问答，1个知识库，基础数据分析 |
| 专业版 | ¥2999/月 | 5000次/天问答，5个知识库，高级数据分析 |
| 企业版 | ¥9999/月 | 无限制问答，无限知识库，定制化开发 |

## 技术支持
- 工作时间：周一至周五 9:00-18:00
- 响应时间：2 小时内
- 支持方式：在线客服、电话、邮件
```

`backend/example_docs/常见问题FAQ.md`：

```markdown
# 海慈智能客服 - 常见问题 FAQ

## 账号相关

### Q: 如何注册账号？
访问官网 https://www.haici.com，点击右上角"注册"按钮，填写手机号或邮箱，设置密码即可完成注册。

### Q: 忘记密码怎么办？
在登录页面点击"忘记密码"，输入注册手机号或邮箱，系统会发送验证码，验证后即可设置新密码。

### Q: 可以修改绑定的手机号吗？
可以。登录后在"个人中心"→"安全设置"中修改绑定手机号。修改时需要验证当前手机号。

## 使用相关

### Q: 支持哪些渠道接入？
支持网页嵌入、微信小程序、APP SDK 三种接入方式。网页嵌入只需添加一行 JS 代码即可。

### Q: 如何上传知识库文档？
在管理后台的"知识库"页面，点击"上传文档"，支持 .txt、.md、.pdf 格式，单文件不超过 10MB。

### Q: AI 回答不准确怎么办？
可以在对话记录中对不准确的回答点"踩"，系统会记录并用于优化。同时建议检查知识库文档内容是否完整准确。

## 计费相关

### Q: 免费试用期多久？
新用户享受 14 天免费试用，试用期间可使用专业版全部功能。

### Q: 如何升级套餐？
登录后在"账户中心"→"套餐管理"中点击"升级"，选择目标套餐并支付差额即可。

### Q: 支持退款吗？
购买后 7 天内如未使用可全额退款。已使用的天数按比例扣除后退还剩余金额。
```

`backend/example_docs/退换货政策.txt`：

```text
# 退换货政策

## 一、退换货条件

1. 自签收之日起 7 天内，商品未使用且包装完好，可申请无理由退货。
2. 商品存在质量问题（非人为损坏），可申请退货或换货。
3. 以下情况不支持退换货：
   - 超过 7 天无理由退货期
   - 商品已被使用或包装破损
   - 定制类商品
   - 数字商品/软件授权

## 二、退换货流程

1. 登录账户，进入"我的订单"页面
2. 选择需要退换货的订单，点击"申请售后"
3. 填写退换货原因，上传商品照片（质量问题需提供）  4. 提交申请后，客服会在 24 小时内审核
5. 审核通过后：
   - 退货：将商品寄回指定地址，仓库签收后 3 个工作日内退款
   - 换货：仓库收到退回商品后，2 个工作日内发出新品

## 三、退货运费

1. 质量问题退货：运费由商家承担（请选择到付）
2. 无理由退货：运费由用户承担
3. 换货运费：商家承担发货运费，用户承担退回运费

## 四、退款说明

1. 退款金额 = 商品实付金额（不含优惠券和运费）
2. 退款路径：原路退回（银行卡/支付宝/微信支付）
3. 退款到账时间：
   - 银行卡：3-7 个工作日
   - 支付宝/微信：1-3 个工作日

## 五、客服联系

如有退换货问题，请联系客服：
- 在线客服：官网右下角
- 客服电话：400-888-9999
- 工作时间：周一至周日 9:00-21:00
```

- [ ] **Step 3: 测试文档入库完整流程**

```bash
cd backend
cp .env.example .env
# 编辑 .env 填入配置
python -c "
from app.rag.ingestion import DocumentIngestion
di = DocumentIngestion()
result = di.ingest_file('example_docs/公司产品介绍.txt')
print(f'Product doc: {result}')
result2 = di.ingest_file('example_docs/常见问题FAQ.md')
print(f'FAQ doc: {result2}')
result3 = di.ingest_file('example_docs/退换货政策.txt')
print(f'Return policy: {result3}')
print(f'Total vectors: {di.vector_store.count()}')
"
```

Expected: 三个文档均 `success: True`，total vectors > 0

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: add document ingestion pipeline + example docs"
```

---

### Task 7: RAG - Prompt 拼装 & LLM 调用 & Fallback

**Files:**
- Create: `backend/app/rag/prompt.py`
- Create: `backend/app/rag/fallback.py`
- Create: `backend/app/rag/llm.py`

- [ ] **Step 1: 编写 Prompt 模块 `backend/app/rag/prompt.py`**

```python
"""Prompt 拼装模块"""
from typing import List, Dict
from datetime import datetime


SYSTEM_PROMPT = """## 角色
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
{retrieved_chunks}

## 当前日期
{current_date}"""


def format_retrieved_chunks(chunks: List[Dict]) -> str:
    """格式化检索结果为 Prompt 可读文本"""
    if not chunks:
        return "（无相关知识库内容）"

    formatted = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk.get("source", "未知来源")
        text = chunk.get("text", "")
        score = chunk.get("score", 0)
        formatted.append(
            f"[来源 {i}: {source} (相关度: {score})]\n{text}"
        )
    return "\n\n---\n\n".join(formatted)


def build_messages(
    query: str,
    retrieved_chunks: List[Dict],
    history_messages: List[Dict] = None,
    max_history_rounds: int = 5,
) -> List[Dict]:
    """
    构建 LLM 消息列表

    Args:
        query: 用户当前问题
        retrieved_chunks: Milvus 检索结果
        history_messages: 历史消息 [{"role": "user","content":"..."}, ...]
        max_history_rounds: 最多携带 N 轮历史

    Returns:
        OpenAI 格式 messages 列表
    """
    # 格式化检索片段
    chunks_text = format_retrieved_chunks(retrieved_chunks)

    # System Prompt
    system_content = SYSTEM_PROMPT.format(
        retrieved_chunks=chunks_text,
        current_date=datetime.now().strftime("%Y年%m月%d日"),
    )

    messages = [{"role": "system", "content": system_content}]

    # 拼装历史消息（最近 N 轮）
    if history_messages:
        # 保留最近 max_history_rounds 轮（一轮 = user + assistant）
        max_messages = max_history_rounds * 2
        recent = history_messages[-max_messages:]
        messages.extend(recent)

    # 当前问题
    messages.append({"role": "user", "content": query})

    return messages
```

- [ ] **Step 2: 编写 Fallback 模块 `backend/app/rag/fallback.py`**

```python
"""兜底话术管理"""
from typing import List, Dict


DEFAULT_FALLBACK_RESPONSE = (
    "抱歉，我目前的知识库中暂时没有找到与您问题相关的信息。"
    "建议您联系人工客服获取帮助，或换一种方式描述您的问题。"
)

FALLBACK_SOURCES: List[Dict] = []  # 空引用


def get_fallback_response() -> str:
    """返回兜底话术"""
    return DEFAULT_FALLBACK_RESPONSE


def get_fallback_sources() -> List[Dict]:
    """返回空引用列表"""
    return FALLBACK_SOURCES
```

- [ ] **Step 3: 编写 LLM 模块 `backend/app/rag/llm.py`**

```python
"""DeepSeek LLM 调用模块"""
import asyncio
from typing import List, Dict, AsyncGenerator
from openai import AsyncOpenAI
from app.config import get_settings


class LLMClient:
    """DeepSeek API 封装（兼容 OpenAI SDK）"""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
        self.model = settings.deepseek_model
        self.timeout = settings.llm_timeout
        self.max_retries = 3

    async def chat_stream(
        self,
        messages: List[Dict],
    ) -> AsyncGenerator[str, None]:
        """
        流式调用 LLM

        Yields:
            每次 yield 一个 token 文本
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=True,
                    temperature=0.3,
                    max_tokens=2048,
                    timeout=self.timeout,
                )

                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

                return  # 成功，退出

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait = 2 ** attempt  # 指数退避: 1s, 2s, 4s
                    await asyncio.sleep(wait)
                continue

        # 所有重试失败
        raise RuntimeError(f"LLM 调用失败（已重试 {self.max_retries} 次）: {last_error}")
```

- [ ] **Step 4: 验证 Prompt + LLM 联调**

```bash
cd backend
python -c "
import asyncio
from app.rag.prompt import build_messages
from app.rag.llm import LLMClient
from app.rag.vector_store import VectorStore
from app.rag.embedder import Embedder

async def test():
    query = '退换货流程是什么？'
    vs = VectorStore()
    emb = Embedder()
    vec = emb.embed_query(query)
    chunks = vs.search(vec, top_k=3, threshold=0.3)
    print(f'Retrieved {len(chunks)} chunks')
    msgs = build_messages(query, chunks)
    llm = LLMClient()
    print('--- LLM Response ---')
    async for token in llm.chat_stream(msgs):
        print(token, end='', flush=True)
    print()

asyncio.run(test())
"
```

Expected: 流式输出退换货相关内容，末尾带📚引用

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add prompt builder, LLM client (DeepSeek), and fallback handler"
```

---

### Task 8: RAG - SSE 流式输出 & 检索服务整合

**Files:**
- Create: `backend/app/rag/stream.py`
- Create: `backend/app/rag/retriever.py`

- [ ] **Step 1: 编写 Retriever `backend/app/rag/retriever.py`**

```python
"""检索服务整合"""
from typing import List, Dict
from app.rag.embedder import Embedder
from app.rag.vector_store import VectorStore
from app.config import get_settings


class Retriever:
    """向量检索服务"""

    def __init__(self):
        self.embedder = Embedder()
        self.vector_store = VectorStore()
        self.settings = get_settings()

    def search(self, query: str) -> List[Dict]:
        """
        语义检索

        Args:
            query: 用户问题

        Returns:
            [{text, source, chunk_index, score}, ...]
        """
        vec = self.embedder.embed_query(query)
        chunks = self.vector_store.search(
            query_embedding=vec,
            top_k=self.settings.top_k,
            threshold=self.settings.similarity_threshold,
        )
        return chunks
```

- [ ] **Step 2: 编写 SSE Stream 生成器 `backend/app/rag/stream.py`**

```python
"""SSE 流式输出模块"""
import json
import asyncio
from typing import List, Dict, AsyncGenerator
from app.rag.retriever import Retriever
from app.rag.prompt import build_messages
from app.rag.llm import LLMClient
from app.rag.fallback import get_fallback_response, get_fallback_sources
from app.config import get_settings


def _sse_event(event: str, data: dict) -> str:
    """构造 SSE 事件字符串"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def generate_chat_stream(
    query: str,
    session_id: int,
    history_messages: List[Dict] = None,
) -> AsyncGenerator[str, None]:
    """
    RAG 问答 SSE 流式生成器

    Args:
        query: 用户问题
        session_id: 会话 ID
        history_messages: 历史消息列表

    Yields:
        SSE 格式字符串
    """
    settings = get_settings()
    retriever = Retriever()
    llm = LLMClient()

    try:
        # Step 1: 检索
        chunks = retriever.search(query)

        # Step 2: 检查检索结果
        if not chunks:
            fallback = get_fallback_response()
            for char in fallback:
                yield _sse_event("token", {"text": char})
                await asyncio.sleep(0.02)  # 模拟打字效果
            yield _sse_event("sources", {"references": get_fallback_sources()})
            yield _sse_event("done", {"message_id": None, "empty_retrieval": True})
            return

        # Step 3: 拼装 Prompt
        messages = build_messages(
            query=query,
            retrieved_chunks=chunks,
            history_messages=history_messages,
            max_history_rounds=settings.max_history_rounds,
        )

        # Step 4: 流式调用 LLM
        full_response = ""
        async for token in llm.chat_stream(messages):
            full_response += token
            yield _sse_event("token", {"text": token})

        # Step 5: 发送引用来源
        sources = [
            {"doc_name": c["source"], "snippet": c["text"][:100], "score": c["score"]}
            for c in chunks
        ]
        yield _sse_event("sources", {"references": sources})

        # Step 6: 结束
        yield _sse_event("done", {
            "message_id": None,
            "full_response": full_response,
            "references": sources,
        })

    except Exception as e:
        yield _sse_event("error", {
            "code": _error_code(e),
            "message": _error_message(e),
        })
        yield _sse_event("done", {"message_id": None, "error": str(e)})


def _error_code(error: Exception) -> str:
    msg = str(error).lower()
    if "timeout" in msg:
        return "LLM_TIMEOUT"
    if "rate" in msg or "limit" in msg:
        return "LLM_RATE_LIMITED"
    return "INTERNAL_ERROR"


def _error_message(error: Exception) -> str:
    msg = str(error)
    if "timeout" in msg:
        return "AI 服务响应超时，请稍后重试"
    if "rate" in msg or "limit" in msg:
        return "AI 服务繁忙，请稍后重试"
    return "系统内部错误，请联系管理员"
```

- [ ] **Step 3: 验证完整 RAG 链路（检索 → Prompt → LLM → SSE）**

```bash
cd backend
python -c "
import asyncio
from app.rag.stream import generate_chat_stream

async def test():
    print('=== RAG Pipeline Test ===')
    async for event in generate_chat_stream('我想退货，怎么办？', session_id=1):
        print(event, end='')
    print('=== Done ===')

asyncio.run(test())
"
```

Expected: 流式输出退换货回答 + sources 事件 + done 事件

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: add retriever service and SSE stream generator"
```

---

## Phase 3: 后端 API 层 (Day 2-3)

### Task 9: 认证模块 (JWT + bcrypt)

**Files:**
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/dependencies.py`
- Create: `backend/app/api/auth.py`

- [ ] **Step 1: 编写 Auth Schema `backend/app/schemas/auth.py`**

```python
"""认证相关 Schema"""
from pydantic import BaseModel, EmailStr, field_validator
import re


class RegisterRequest(BaseModel):
    phone: str | None = None
    email: str | None = None
    password: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if v and not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("密码至少 6 位")
        return v


class LoginRequest(BaseModel):
    account: str  # 手机号或邮箱
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: int
    message: str = "登录成功"
```

- [ ] **Step 2: 编写 Auth Service `backend/app/services/auth_service.py`**

```python
"""认证服务"""
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from app.models.user import User
from app.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return int(payload["sub"])
    except Exception:
        return None


def register_user(db: Session, phone: str | None, email: str | None, password: str) -> User:
    if not phone and not email:
        raise ValueError("手机号和邮箱至少填一个")

    # 检查是否已存在
    if phone:
        existing = db.query(User).filter(User.phone == phone).first()
        if existing:
            raise ValueError("该手机号已注册")
    if email:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise ValueError("该邮箱已注册")

    user = User(
        phone=phone,
        email=email,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, account: str, password: str) -> tuple[User, str]:
    # 按手机号或邮箱查找
    user = db.query(User).filter(
        (User.phone == account) | (User.email == account)
    ).first()

    if not user:
        raise ValueError("账号或密码错误")

    if not verify_password(password, user.password_hash):
        raise ValueError("账号或密码错误")

    token = create_token(user.id)
    return user, token
```

- [ ] **Step 3: 编写依赖注入 `backend/app/dependencies.py`**

```python
"""FastAPI 依赖注入"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.auth_service import verify_token

security = HTTPBearer()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """从 JWT Token 解析当前用户 ID"""
    user_id = verify_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证 Token",
        )
    return user_id
```

- [ ] **Step 4: 编写 Auth API `backend/app/api/auth.py`**

```python
"""认证接口"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, AuthResponse
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = auth_service.register_user(db, req.phone, req.email, req.password)
        token = auth_service.create_token(user.id)
        return AuthResponse(token=token, user_id=user.id, message="注册成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    try:
        user, token = auth_service.login_user(db, req.account, req.password)
        return AuthResponse(token=token, user_id=user.id, message="登录成功")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
```

- [ ] **Step 5: 注册路由到 main.py**

Modify `backend/app/main.py`:

```python
"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth

app = FastAPI(title="ICS Customer Service API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "ICS Customer Service"}
```

- [ ] **Step 6: 测试认证接口**

```bash
cd backend
# 启动服务
uvicorn app.main:app --reload --port 8000 &
sleep 2

# 测试注册
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800138000","email":"test@test.com","password":"123456"}'

# 测试登录
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"account":"13800138000","password":"123456"}'
```

Expected: 注册返回 token，登录返回 token

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: add JWT authentication with register/login endpoints"
```

---

### Task 10: 会话管理 API

**Files:**
- Create: `backend/app/schemas/session.py`
- Create: `backend/app/services/session_service.py`
- Create: `backend/app/api/sessions.py`

- [ ] **Step 1: 编写 Session Schema `backend/app/schemas/session.py`**

```python
"""会话 Schema"""
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    intent_tag: str | None = None
    references: list | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class SessionOut(BaseModel):
    id: int
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


class SessionDetailOut(SessionOut):
    messages: List[MessageOut] = []


class SessionCreate(BaseModel):
    title: str = "新会话"


class SessionListResponse(BaseModel):
    sessions: List[SessionOut]
    total: int


class MessageCreate(BaseModel):
    content: str
```

- [ ] **Step 2: 编写 Session Service `backend/app/services/session_service.py`**

```python
"""会话服务"""
from typing import List
from sqlalchemy.orm import Session
from app.models.session import Session as SessionModel, SessionStatus
from app.models.message import Message as MessageModel, MessageRole


def create_session(db: Session, user_id: int, title: str = "新会话") -> SessionModel:
    session = SessionModel(user_id=user_id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_user_sessions(db: Session, user_id: int) -> List[SessionModel]:
    return (
        db.query(SessionModel)
        .filter(SessionModel.user_id == user_id)
        .order_by(SessionModel.updated_at.desc())
        .all()
    )


def get_session_detail(db: Session, session_id: int, user_id: int) -> SessionModel | None:
    return (
        db.query(SessionModel)
        .filter(
            SessionModel.id == session_id,
            SessionModel.user_id == user_id,
        )
        .first()
    )


def create_message(
    db: Session,
    session_id: int,
    role: str,
    content: str,
    intent_tag: str | None = None,
    references: list | None = None,
) -> MessageModel:
    msg = MessageModel(
        session_id=session_id,
        role=MessageRole(role),
        content=content,
        intent_tag=intent_tag,
        references_json=references,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    # 更新会话时间
    db.query(SessionModel).filter(SessionModel.id == session_id).update(
        {"updated_at": db.func.now()}
    )
    db.commit()
    return msg


def get_session_messages(db: Session, session_id: int) -> List[MessageModel]:
    return (
        db.query(MessageModel)
        .filter(MessageModel.session_id == session_id)
        .order_by(MessageModel.created_at.asc())
        .all()
    )
```

- [ ] **Step 3: 编写 Sessions API `backend/app/api/sessions.py`**

```python
"""会话接口"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user_id
from app.schemas.session import (
    SessionCreate,
    SessionOut,
    SessionDetailOut,
    SessionListResponse,
)
from app.services import session_service

router = APIRouter(prefix="/api/sessions", tags=["会话"])


@router.get("", response_model=SessionListResponse)
def list_sessions(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    sessions = session_service.get_user_sessions(db, user_id)
    return SessionListResponse(
        sessions=[
            SessionOut(
                id=s.id,
                title=s.title,
                status=s.status.value,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=len(s.messages),
            )
            for s in sessions
        ],
        total=len(sessions),
    )


@router.post("", response_model=SessionOut)
def create_new_session(
    req: SessionCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    session = session_service.create_session(db, user_id, req.title)
    return SessionOut(
        id=session.id,
        title=session.title,
        status=session.status.value,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0,
    )


@router.get("/{session_id}", response_model=SessionDetailOut)
def get_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    session = session_service.get_session_detail(db, session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    return SessionDetailOut(
        id=session.id,
        title=session.title,
        status=session.status.value,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(session.messages),
        messages=[
            {
                "id": m.id,
                "role": m.role.value,
                "content": m.content,
                "intent_tag": m.intent_tag,
                "references": m.references_json,
                "created_at": m.created_at,
            }
            for m in session.messages
        ],
    )
```

- [ ] **Step 4: 注册路由 & 测试**

Register in `backend/app/main.py`:
```python
from app.api import sessions
app.include_router(sessions.router)
```

```bash
# 测试（先登录获取 token）
TOKEN="your-jwt-token"

curl http://localhost:8000/api/sessions \
  -H "Authorization: Bearer $TOKEN"

curl -X POST http://localhost:8000/api/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"测试会话"}'
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add session CRUD API with list/create/detail endpoints"
```

---

### Task 11: 聊天 SSE 接口（核心）

**Files:**
- Create: `backend/app/api/chat.py`
- Create: `backend/app/services/chat_service.py`

- [ ] **Step 1: 编写 Chat Service `backend/app/services/chat_service.py`**

```python
"""聊天服务"""
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.message import MessageRole


def check_daily_limit(db: Session, user_id: int) -> bool:
    """检查每日提问次数，返回 True 表示未超限"""
    settings = get_settings()
    from datetime import date
    from app.models.document import Document  # 复用 models

    # 使用 raw SQL 查询 daily_question_count
    today = date.today()
    result = db.execute(
        db.text(
            "SELECT count FROM daily_question_count "
            "WHERE user_id = :uid AND query_date = :qdate"
        ),
        {"uid": user_id, "qdate": today},
    ).fetchone()

    current = result[0] if result else 0
    return current < settings.daily_question_limit


def increment_question_count(db: Session, user_id: int):
    """增加当日提问计数"""
    from datetime import date
    today = date.today()

    existing = db.execute(
        db.text(
            "SELECT id FROM daily_question_count "
            "WHERE user_id = :uid AND query_date = :qdate"
        ),
        {"uid": user_id, "qdate": today},
    ).fetchone()

    if existing:
        db.execute(
            db.text(
                "UPDATE daily_question_count SET count = count + 1 "
                "WHERE id = :id"
            ),
            {"id": existing[0]},
        )
    else:
        db.execute(
            db.text(
                "INSERT INTO daily_question_count (user_id, query_date, count) "
                "VALUES (:uid, :qdate, 1)"
            ),
            {"uid": user_id, "qdate": today},
        )
    db.commit()


def validate_question(content: str) -> str | None:
    """校验问题，返回错误信息或 None"""
    settings = get_settings()
    if not content or not content.strip():
        return "问题不能为空"
    if len(content) > settings.max_question_length:
        return f"问题长度不能超过 {settings.max_question_length} 字"
    return None
```

- [ ] **Step 2: 编写 Chat API `backend/app/api/chat.py`**

```python
"""聊天 SSE 接口"""
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user_id
from app.schemas.chat import ChatRequest
from app.services import session_service, chat_service
from app.rag.stream import generate_chat_stream

router = APIRouter(prefix="/api/chat", tags=["聊天"])


@router.post("/{session_id}")
async def chat(
    session_id: int,
    req: ChatRequest,
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    # 1. 校验会话归属
    session = session_service.get_session_detail(db, session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 2. 校验问题
    error = chat_service.validate_question(req.content)
    if error:
        raise HTTPException(status_code=400, detail=error)

    # 3. 检查每日次数
    if not chat_service.check_daily_limit(db, user_id):
        raise HTTPException(status_code=429, detail="今日提问次数已达上限")

    # 4. 保存用户消息
    session_service.create_message(db, session_id, "user", req.content)

    # 5. 获取历史消息
    messages = session_service.get_session_messages(db, session_id)
    history = [
        {"role": m.role.value, "content": m.content}
        for m in messages[:-1]  # 不包含刚保存的用户消息（会在 stream 中处理）
    ]

    # 6. 次数+1
    chat_service.increment_question_count(db, user_id)

    # 7. 返回 SSE 流
    async def event_stream():
        full_response = ""
        references = []

        async for sse_str in generate_chat_stream(
            query=req.content,
            session_id=session_id,
            history_messages=history,
        ):
            # 解析 done 事件获取完整回答和引用
            if 'event: done' in sse_str:
                try:
                    data_str = sse_str.split('data: ')[1]
                    done_data = json.loads(data_str)
                    full_response = done_data.get("full_response", "")
                    references = done_data.get("references", [])
                except Exception:
                    pass

            yield sse_str

        # 8. 保存 AI 回答到数据库
        if full_response:
            session_service.create_message(
                db,
                session_id,
                "assistant",
                full_response,
                references=references,
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
```

- [ ] **Step 3: 创建 Chat Schema `backend/app/schemas/chat.py`**

```python
"""聊天 Schema"""
from pydantic import BaseModel


class ChatRequest(BaseModel):
    content: str
    intent: str | None = None
```

- [ ] **Step 4: 测试聊天 SSE 接口**

```bash
curl -N -X POST http://localhost:8000/api/chat/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"退换货怎么操作？"}'
```

Expected: 流式输出 SSE events（token → sources → done）

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add chat SSE endpoint with full RAG pipeline integration"
```

---

### Task 12: 知识库管理 & 反馈 API

**Files:**
- Create: `backend/app/schemas/knowledge.py`
- Create: `backend/app/schemas/feedback.py`
- Create: `backend/app/services/knowledge_service.py`
- Create: `backend/app/services/feedback_service.py`
- Create: `backend/app/api/knowledge.py`
- Create: `backend/app/api/feedback.py`
- Create: `backend/app/api/stats.py`

- [ ] **Step 1: 编写 Knowledge Schema `backend/app/schemas/knowledge.py`**

```python
"""知识库 Schema"""
from pydantic import BaseModel
from datetime import datetime


class DocumentOut(BaseModel):
    id: int
    name: str
    file_type: str
    status: str
    chunk_count: int
    file_size: int
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: list[DocumentOut]
    total: int
```

- [ ] **Step 2: 编写 Knowledge Service `backend/app/services/knowledge_service.py`**

```python
"""知识库服务"""
import os
import uuid
from typing import List
from sqlalchemy.orm import Session
from app.models.document import Document, DocumentStatus
from app.rag.ingestion import DocumentIngestion


def upload_document(db: Session, file_content: bytes, filename: str) -> Document:
    """上传并处理文档"""
    # 保存文件
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = "data/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, safe_name)

    with open(file_path, "wb") as f:
        f.write(file_content)

    file_size = len(file_content)

    # 创建数据库记录（状态：处理中）
    doc = Document(
        name=filename,
        file_type=ext if ext in ("txt", "md", "pdf") else "txt",
        status=DocumentStatus.processing,
        file_size=file_size,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    try:
        # 入库到 Milvus
        ingestion = DocumentIngestion()
        result = ingestion.ingest_file(file_path)

        if result["success"]:
            doc.status = DocumentStatus.ready
            doc.chunk_count = result["chunk_count"]
            doc.milvus_ids = result["milvus_ids"]
        else:
            doc.status = DocumentStatus.failed
            doc.error_msg = result["error"]
    except Exception as e:
        doc.status = DocumentStatus.failed
        doc.error_msg = str(e)

    db.commit()
    db.refresh(doc)
    return doc


def list_documents(db: Session) -> List[Document]:
    return (
        db.query(Document)
        .order_by(Document.created_at.desc())
        .all()
    )


def delete_document(db: Session, doc_id: int):
    """删除文档及向量"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise ValueError("文档不存在")

    # 删除 Milvus 向量
    if doc.milvus_ids:
        from app.rag.vector_store import VectorStore
        vs = VectorStore()
        vs.delete_by_ids(doc.milvus_ids)

    # 删除上传文件
    # (files tracked by filename pattern in upload dir, skip for now)

    db.delete(doc)
    db.commit()
```

- [ ] **Step 3: 编写 Knowledge API `backend/app/api/knowledge.py`**

```python
"""知识库接口"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user_id
from app.schemas.knowledge import DocumentOut, DocumentListResponse
from app.services import knowledge_service

router = APIRouter(prefix="/api/knowledge", tags=["知识库"])

ALLOWED_EXTENSIONS = {"txt", "md", "pdf"}


@router.post("/upload", response_model=DocumentOut)
async def upload(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件格式: {ext}，仅支持 {ALLOWED_EXTENSIONS}")

    content = await file.read()
    max_size = 10 * 1024 * 1024  # 10MB
    if len(content) > max_size:
        raise HTTPException(400, "文件大小不能超过 10MB")

    doc = knowledge_service.upload_document(db, content, file.filename)
    return DocumentOut(
        id=doc.id,
        name=doc.name,
        file_type=doc.file_type.value if hasattr(doc.file_type, 'value') else doc.file_type,
        status=doc.status.value if hasattr(doc.status, 'value') else doc.status,
        chunk_count=doc.chunk_count,
        file_size=doc.file_size,
        created_at=doc.created_at,
    )


@router.get("/list", response_model=DocumentListResponse)
def list_docs(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    docs = knowledge_service.list_documents(db)
    return DocumentListResponse(
        documents=[
            DocumentOut(
                id=d.id,
                name=d.name,
                file_type=d.file_type.value if hasattr(d.file_type, 'value') else d.file_type,
                status=d.status.value if hasattr(d.status, 'value') else d.status,
                chunk_count=d.chunk_count,
                file_size=d.file_size,
                created_at=d.created_at,
            )
            for d in docs
        ],
        total=len(docs),
    )


@router.delete("/{doc_id}")
def delete_doc(
    doc_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    try:
        knowledge_service.delete_document(db, doc_id)
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(404, detail=str(e))
```

- [ ] **Step 4: 编写 Feedback Schema + Service + API**

`backend/app/schemas/feedback.py`:
```python
from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    message_id: int
    rating: str  # "positive" / "negative"
    comment: str | None = None


class FeedbackResponse(BaseModel):
    id: int
    message: str = "反馈提交成功"
```

`backend/app/services/feedback_service.py`:
```python
from sqlalchemy.orm import Session
from app.models.feedback import Feedback, FeedbackRating


def submit_feedback(
    db: Session,
    message_id: int,
    rating: str,
    comment: str | None = None,
) -> Feedback:
    fb = Feedback(
        message_id=message_id,
        rating=FeedbackRating(rating),
        comment=comment,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb
```

`backend/app/api/feedback.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user_id
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.services import feedback_service

router = APIRouter(prefix="/api/feedback", tags=["反馈"])


@router.post("", response_model=FeedbackResponse)
def submit(
    req: FeedbackRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if req.rating not in ("positive", "negative"):
        raise HTTPException(400, "rating 必须是 positive 或 negative")

    fb = feedback_service.submit_feedback(db, req.message_id, req.rating, req.comment)
    return FeedbackResponse(id=fb.id)
```

`backend/app/api/stats.py`:
```python
"""统计接口"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user_id
from app.services import chat_service

router = APIRouter(prefix="/api/stats", tags=["统计"])


@router.get("/daily")
def daily_usage(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    from datetime import date
    today = date.today()
    result = db.execute(
        db.text(
            "SELECT count FROM daily_question_count "
            "WHERE user_id = :uid AND query_date = :qdate"
        ),
        {"uid": user_id, "qdate": today},
    ).fetchone()

    return {
        "date": str(today),
        "count": result[0] if result else 0,
    }
```

- [ ] **Step 5: 注册所有新路由到 main.py**

```python
from app.api import auth, sessions, chat, knowledge, feedback, stats

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(knowledge.router)
app.include_router(feedback.router)
app.include_router(stats.router)
```

- [ ] **Step 6: 测试知识库上传**

```bash
# 上传文档
curl -X POST http://localhost:8000/api/knowledge/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@backend/example_docs/公司产品介绍.txt"

# 查看列表
curl http://localhost:8000/api/knowledge/list \
  -H "Authorization: Bearer $TOKEN"
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: add knowledge upload/list/delete, feedback, and stats APIs"
```

---

## Phase 4: 前端开发 (Day 3-4)

### Task 13: 前端基础架构 - API 客户端 & 路由 & Store

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/auth.ts`
- Create: `frontend/src/api/sessions.ts`
- Create: `frontend/src/api/chat.ts`
- Create: `frontend/src/api/knowledge.ts`
- Create: `frontend/src/api/feedback.ts`
- Create: `frontend/src/stores/authStore.ts`
- Create: `frontend/src/stores/sessionStore.ts`
- Create: `frontend/src/stores/chatStore.ts`
- Create: `frontend/src/router.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: 编写 API 客户端 `frontend/src/api/client.ts`**

```typescript
const BASE_URL = '/api';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

function getToken(): string | null {
  return localStorage.getItem('token');
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Don't set Content-Type for FormData (browser sets it with boundary)
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || res.statusText);
  }

  return res.json();
}

export { request, ApiError, BASE_URL };
export type { ApiError };
```

- [ ] **Step 2: 编写 Auth API `frontend/src/api/auth.ts`**

```typescript
import { request } from './client';

interface RegisterParams {
  phone?: string;
  email?: string;
  password: string;
}

interface LoginParams {
  account: string;
  password: string;
}

interface AuthResponse {
  token: string;
  user_id: number;
  message: string;
}

export async function register(params: RegisterParams): Promise<AuthResponse> {
  return request('/auth/register', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function login(params: LoginParams): Promise<AuthResponse> {
  return request('/auth/login', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}
```

- [ ] **Step 3: 编写 Sessions API + Chat API**

`frontend/src/api/sessions.ts`:
```typescript
import { request } from './client';

export interface Session {
  id: number;
  title: string;
  status: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface SessionDetail extends Session {
  messages: Message[];
}

export interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  intent_tag: string | null;
  references: Reference[] | null;
  created_at: string;
}

export interface Reference {
  doc_name: string;
  snippet: string;
  score: number;
}

export async function listSessions(): Promise<{ sessions: Session[]; total: number }> {
  return request('/sessions');
}

export async function createSession(title?: string): Promise<Session> {
  return request('/sessions', {
    method: 'POST',
    body: JSON.stringify({ title: title || '新会话' }),
  });
}

export async function getSession(id: number): Promise<SessionDetail> {
  return request(`/sessions/${id}`);
}
```

`frontend/src/api/chat.ts`:
```typescript
import { BASE_URL } from './client';

export type SSECallback = {
  onToken: (text: string) => void;
  onSources: (references: Reference[]) => void;
  onDone: (data: { message_id: number | null; references?: Reference[] }) => void;
  onError: (code: string, message: string) => void;
};

interface Reference {
  doc_name: string;
  snippet: string;
  score: number;
}

export async function sendMessage(
  sessionId: number,
  content: string,
  callbacks: SSECallback,
): Promise<void> {
  const token = localStorage.getItem('token');

  const response = await fetch(`${BASE_URL}/chat/${sessionId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ content }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '请求失败' }));
    callbacks.onError('HTTP_ERROR', error.detail || '请求失败');
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    callbacks.onError('STREAM_ERROR', '无法读取流');
    return;
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() || '';

    for (const part of parts) {
      if (!part.trim()) continue;

      const eventMatch = part.match(/^event: (\w+)$/m);
      const dataMatch = part.match(/^data: (.+)$/m);

      if (!eventMatch || !dataMatch) continue;

      const event = eventMatch[1];
      try {
        const data = JSON.parse(dataMatch[1]);

        switch (event) {
          case 'token':
            callbacks.onToken(data.text);
            break;
          case 'sources':
            callbacks.onSources(data.references || []);
            break;
          case 'done':
            callbacks.onDone(data);
            break;
          case 'error':
            callbacks.onError(data.code, data.message);
            break;
        }
      } catch {
        // Skip malformed events
      }
    }
  }
}
```

- [ ] **Step 4: 编写 Zustand Stores**

`frontend/src/stores/authStore.ts`:
```typescript
import { create } from 'zustand';
import { login as apiLogin, register as apiRegister } from '../api/auth';

interface AuthState {
  token: string | null;
  userId: number | null;
  isAuthenticated: boolean;
  login: (account: string, password: string) => Promise<void>;
  register: (phone: string | undefined, email: string | undefined, password: string) => Promise<void>;
  logout: () => void;
  init: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  userId: null,
  isAuthenticated: false,

  login: async (account, password) => {
    const res = await apiLogin({ account, password });
    localStorage.setItem('token', res.token);
    set({ token: res.token, userId: res.user_id, isAuthenticated: true });
  },

  register: async (phone, email, password) => {
    const res = await apiRegister({ phone, email, password });
    localStorage.setItem('token', res.token);
    set({ token: res.token, userId: res.user_id, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem('token');
    set({ token: null, userId: null, isAuthenticated: false });
  },

  init: () => {
    const token = localStorage.getItem('token');
    if (token) {
      set({ token, isAuthenticated: true });
    }
  },
}));
```

`frontend/src/stores/chatStore.ts`:
```typescript
import { create } from 'zustand';
import { sendMessage } from '../api/chat';
import type { Message, Reference } from '../api/sessions';

interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  streamContent: string;
  references: Reference[];
  error: string | null;

  addUserMessage: (content: string) => void;
  sendChat: (sessionId: number, content: string) => Promise<void>;
  clearStream: () => void;
  setMessages: (messages: Message[]) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isStreaming: false,
  streamContent: '',
  references: [],
  error: null,

  addUserMessage: (content) => {
    set((s) => ({
      messages: [
        ...s.messages,
        { id: Date.now(), role: 'user', content, intent_tag: null, references: null, created_at: new Date().toISOString() },
      ],
    }));
  },

  sendChat: async (sessionId, content) => {
    set({ isStreaming: true, streamContent: '', references: [], error: null });

    let fullText = '';
    await sendMessage(sessionId, content, {
      onToken: (text) => {
        fullText += text;
        set({ streamContent: fullText });
      },
      onSources: (refs) => {
        set({ references: refs });
      },
      onDone: (data) => {
        const state = get();
        const botMsg: Message = {
          id: data.message_id || Date.now(),
          role: 'assistant',
          content: fullText,
          intent_tag: null,
          references: data.references || state.references,
          created_at: new Date().toISOString(),
        };
        set((s) => ({
          messages: [...s.messages, botMsg],
          isStreaming: false,
          streamContent: '',
        }));
      },
      onError: (code, message) => {
        set({ error: message, isStreaming: false });
      },
    });
  },

  clearStream: () => set({ streamContent: '', isStreaming: false, error: null }),
  setMessages: (messages) => set({ messages }),
}));
```

- [ ] **Step 5: 编写路由 + App + main**

`frontend/src/router.tsx`:
```typescript
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { ChatPage } from './pages/ChatPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { KnowledgePage } from './pages/KnowledgePage';

function Protected({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token');
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/register', element: <RegisterPage /> },
  {
    path: '/chat',
    element: <Protected><ChatPage /></Protected>,
  },
  {
    path: '/chat/:sessionId',
    element: <Protected><ChatPage /></Protected>,
  },
  {
    path: '/knowledge',
    element: <Protected><KnowledgePage /></Protected>,
  },
  { path: '*', element: <Navigate to="/chat" replace /> },
]);
```

`frontend/src/main.tsx`:
```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { router } from './router';
import { useAuthStore } from './stores/authStore';
import './styles/global.css';

useAuthStore.getState().init();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
);
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: add frontend API client, Zustand stores, and routing"
```

---

### Task 14: 前端 - 登录/注册页

**Files:**
- Create: `frontend/src/pages/LoginPage.tsx`
- Create: `frontend/src/pages/RegisterPage.tsx`

- [ ] **Step 1: 编写登录页 `frontend/src/pages/LoginPage.tsx`**

```tsx
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

export function LoginPage() {
  const [account, setAccount] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(account, password);
      navigate('/chat');
    } catch (err: any) {
      setError(err.message || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-2xl shadow-sm border border-gray-100">
        <h1 className="text-2xl font-bold text-center mb-8">智能客服系统</h1>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">手机号 / 邮箱</label>
            <input
              type="text"
              value={account}
              onChange={(e) => setAccount(e.target.value)}
              placeholder="请输入手机号或邮箱"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
              required
            />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition"
          >
            {loading ? '登录中...' : '登录'}
          </button>
        </form>
        <p className="text-center text-sm text-gray-500 mt-6">
          还没有账号？
          <Link to="/register" className="text-blue-600 hover:underline ml-1">立即注册</Link>
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 编写注册页 `frontend/src/pages/RegisterPage.tsx`**

```tsx
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

export function RegisterPage() {
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const register = useAuthStore((s) => s.register);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!phone && !email) {
      setError('手机号和邮箱至少填写一个');
      return;
    }
    if (password !== confirmPassword) {
      setError('两次密码输入不一致');
      return;
    }
    if (password.length < 6) {
      setError('密码至少 6 位');
      return;
    }

    setLoading(true);
    try {
      await register(phone || undefined, email || undefined, password);
      navigate('/chat');
    } catch (err: any) {
      setError(err.message || '注册失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="w-full max-w-md p-8 bg-white rounded-2xl shadow-sm border border-gray-100">
        <h1 className="text-2xl font-bold text-center mb-8">注册账号</h1>
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">手机号</label>
            <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="选填" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="选填" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">密码</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="至少 6 位" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">确认密码</label>
            <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="再次输入密码" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition" required />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button type="submit" disabled={loading} className="w-full py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition">
            {loading ? '注册中...' : '注册'}
          </button>
        </form>
        <p className="text-center text-sm text-gray-500 mt-6">
          已有账号？
          <Link to="/login" className="text-blue-600 hover:underline ml-1">去登录</Link>
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: add login and register pages with form validation"
```

---

### Task 15: 前端 - 聊天页面（核心）

**Files:**
- Create: `frontend/src/pages/ChatPage.tsx`
- Create: `frontend/src/components/sidebar/SessionList.tsx`
- Create: `frontend/src/components/chat/ChatBubble.tsx`
- Create: `frontend/src/components/chat/ChatInput.tsx`
- Create: `frontend/src/components/chat/SourceCard.tsx`
- Create: `frontend/src/components/chat/FeedbackBar.tsx`
- Create: `frontend/src/components/chat/StreamingText.tsx`
- Create: `frontend/src/styles/global.css` (tailwind directives + custom)

- [ ] **Step 1: 编写 CSS 入口 `frontend/src/styles/global.css`**

```css
@import "tailwindcss";

/* === Design Tokens (SaaS Light — Indigo #6366f1) === */
:root {
  --color-primary: #6366f1;
  --color-primary-hover: #4f46e5;
  --color-primary-light: #eef2ff;
  --color-bg-sidebar: #fafbfc;
  --color-border: #e8eaed;
  --color-bg-bot: #f9fafb;
  --color-text-primary: #374151;
  --color-text-secondary: #6b7280;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 14px;
  --radius-xl: 16px;
}

/* Custom scrollbar */
.sidebar-scroll::-webkit-scrollbar { width: 4px; }
.sidebar-scroll::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 2px; }

/* Streaming cursor blink */
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
.streaming-cursor::after { content: '|'; animation: blink 0.8s infinite; color: var(--color-primary); }

/* Message bubble animations */
@keyframes fadeInUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.msg-enter { animation: fadeInUp 0.3s ease-out; }

/* Markdown content styling */
.markdown-body h1 { font-size: 1.25rem; font-weight: 700; margin: 0.75rem 0 0.5rem; }
.markdown-body h2 { font-size: 1.125rem; font-weight: 600; margin: 0.5rem 0 0.25rem; }
.markdown-body ul, .markdown-body ol { padding-left: 1.25rem; margin: 0.25rem 0; }
.markdown-body li { margin: 0.125rem 0; }
.markdown-body p { margin: 0.25rem 0; }
.markdown-body code { background: #f3f4f6; padding: 0.125rem 0.375rem; border-radius: 0.25rem; font-size: 0.875rem; }
.markdown-body pre { background: #1f2937; color: #f9fafb; padding: 0.75rem; border-radius: 0.5rem; overflow-x: auto; margin: 0.5rem 0; }
.markdown-body table { width: 100%; border-collapse: collapse; margin: 0.5rem 0; }
.markdown-body th, .markdown-body td { border: 1px solid #e5e7eb; padding: 0.375rem 0.75rem; text-align: left; }
.markdown-body th { background: #f9fafb; font-weight: 600; }
.markdown-body strong { font-weight: 600; color: #1f2937; }
```

- [ ] **Step 2: 编写组件**

`frontend/src/components/sidebar/SessionList.tsx`:
```tsx
import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { listSessions, createSession, type Session } from '../../api/sessions';
import { useSessionStore } from '../../stores/sessionStore';
import { MessageSquare, Plus, LogOut, Database } from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';

export function SessionList() {
  const { sessions, setSessions } = useSessionStore();
  const navigate = useNavigate();
  const { sessionId } = useParams();
  const logout = useAuthStore((s) => s.logout);

  useEffect(() => {
    listSessions()
      .then((res) => setSessions(res.sessions))
      .catch(() => {});
  }, [setSessions]);

  const handleNew = async () => {
    try {
      const s = await createSession();
      setSessions([s, ...sessions]);
      navigate(`/chat/${s.id}`);
    } catch {}
  };

  return (
    <div className="w-64 h-screen bg-gray-900 text-gray-100 flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <button
          onClick={handleNew}
          className="w-full flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition text-sm font-medium"
        >
          <Plus size={16} /> 新建会话
        </button>
      </div>

      <div className="flex-1 overflow-y-auto sidebar-scroll p-2 space-y-1">
        {sessions.map((s) => (
          <button
            key={s.id}
            onClick={() => navigate(`/chat/${s.id}`)}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm transition flex items-center gap-2 ${
              String(s.id) === sessionId ? 'bg-gray-700 text-white' : 'hover:bg-gray-800 text-gray-300'
            }`}
          >
            <MessageSquare size={14} />
            <span className="truncate">{s.title}</span>
          </button>
        ))}
        {sessions.length === 0 && (
          <p className="text-gray-500 text-xs text-center py-8">暂无会话</p>
        )}
      </div>

      <div className="p-3 border-t border-gray-700 space-y-1">
        <button
          onClick={() => navigate('/knowledge')}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 rounded-lg transition"
        >
          <Database size={14} /> 知识库管理
        </button>
        <button
          onClick={() => { logout(); navigate('/login'); }}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 rounded-lg transition"
        >
          <LogOut size={14} /> 退出登录
        </button>
      </div>
    </div>
  );
}
```

`frontend/src/components/chat/ChatBubble.tsx`:
```tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '../../api/sessions';
import { SourceCard } from './SourceCard';
import { FeedbackBar } from './FeedbackBar';

interface Props {
  message: Message;
}

export function ChatBubble({ message }: Props) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} msg-enter mb-4`}>
      <div className={`max-w-[80%] ${isUser ? 'order-1' : ''}`}>
        <div className={`px-4 py-3 rounded-2xl ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-md'
            : 'bg-white border border-gray-100 shadow-sm rounded-bl-md'
        }`}>
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="markdown-body text-sm text-gray-800 prose-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* 引用来源 + 反馈按钮（仅 AI 消息） */}
        {!isUser && message.references && message.references.length > 0 && (
          <div className="mt-2 space-y-1">
            {message.references.map((ref, i) => (
              <SourceCard key={i} docName={ref.doc_name} snippet={ref.snippet} score={ref.score} />
            ))}
          </div>
        )}

        {!isUser && <FeedbackBar messageId={message.id} />}

        {message.intent_tag && (
          <span className="inline-block mt-1 text-xs px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full">
            {message.intent_tag}
          </span>
        )}
      </div>
    </div>
  );
}
```

`frontend/src/components/chat/StreamingText.tsx`:
```tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
  content: string;
}

export function StreamingText({ content }: Props) {
  return (
    <div className="flex justify-start msg-enter mb-4">
      <div className="max-w-[80%]">
        <div className="px-4 py-3 rounded-2xl bg-white border border-gray-100 shadow-sm rounded-bl-md streaming-cursor">
          <div className="markdown-body text-sm text-gray-800 prose-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content || ' '}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}
```

`frontend/src/components/chat/ChatInput.tsx`:
```tsx
import { useState } from 'react';
import { Send } from 'lucide-react';

interface Props {
  onSend: (content: string) => void;
  disabled?: boolean;
  maxLength?: number;
}

export function ChatInput({ onSend, disabled, maxLength = 500 }: Props) {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    if (input.length > maxLength) return;
    onSend(input.trim());
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 border-t border-gray-100 bg-white">
      <div className="flex items-end gap-2 max-w-3xl mx-auto">
        <div className="flex-1 relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入您的问题... (Enter 发送, Shift+Enter 换行)"
            className="w-full px-4 py-2.5 border border-gray-200 rounded-xl resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition text-sm"
            rows={2}
            disabled={disabled}
          />
          <span className={`absolute bottom-2 right-3 text-xs ${input.length > maxLength ? 'text-red-500' : 'text-gray-400'}`}>
            {input.length}/{maxLength}
          </span>
        </div>
        <button
          type="submit"
          disabled={disabled || !input.trim() || input.length > maxLength}
          className="p-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-40 transition shrink-0"
        >
          <Send size={18} />
        </button>
      </div>
    </form>
  );
}
```

`frontend/src/components/chat/SourceCard.tsx`:
```tsx
import { BookOpen } from 'lucide-react';

interface Props {
  docName: string;
  snippet: string;
  score: number;
}

export function SourceCard({ docName, snippet, score }: Props) {
  return (
    <div className="flex items-start gap-2 px-2.5 py-1.5 bg-gray-50 rounded-lg text-xs text-gray-500">
      <BookOpen size={12} className="mt-0.5 shrink-0" />
      <div>
        <span className="font-medium text-gray-700">📚 参考：{docName}</span>
        <span className="ml-2 text-gray-400">(相关度: {score})</span>
        {snippet && <p className="text-gray-400 mt-0.5 line-clamp-2">{snippet}</p>}
      </div>
    </div>
  );
}
```

`frontend/src/components/chat/FeedbackBar.tsx`:
```tsx
import { useState } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { submitFeedback } from '../../api/feedback';

interface Props {
  messageId: number;
}

export function FeedbackBar({ messageId }: Props) {
  const [feedback, setFeedback] = useState<string | null>(null);

  const handle = async (rating: 'positive' | 'negative') => {
    if (feedback) return;
    setFeedback(rating);
    try {
      await submitFeedback(messageId, rating);
    } catch {}
  };

  return (
    <div className="flex items-center gap-1 mt-1 ml-1">
      <button
        onClick={() => handle('positive')}
        disabled={!!feedback}
        className={`p-1 rounded transition ${feedback === 'positive' ? 'text-green-600' : 'text-gray-300 hover:text-green-500'}`}
      >
        <ThumbsUp size={14} />
      </button>
      <button
        onClick={() => handle('negative')}
        disabled={!!feedback}
        className={`p-1 rounded transition ${feedback === 'negative' ? 'text-red-600' : 'text-gray-300 hover:text-red-500'}`}
      >
        <ThumbsDown size={14} />
      </button>
      {feedback && <span className="text-xs text-gray-400 ml-1">感谢反馈</span>}
    </div>
  );
}
```

- [ ] **Step 3: 编写聊天主页 `frontend/src/pages/ChatPage.tsx`**

```tsx
import { useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { SessionList } from '../components/sidebar/SessionList';
import { ChatBubble } from '../components/chat/ChatBubble';
import { ChatInput } from '../components/chat/ChatInput';
import { StreamingText } from '../components/chat/StreamingText';
import { useChatStore } from '../stores/chatStore';
import { getSession } from '../api/sessions';

export function ChatPage() {
  const { sessionId } = useParams();
  const { messages, isStreaming, streamContent, error, setMessages, addUserMessage, sendChat } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (sessionId) {
      getSession(Number(sessionId))
        .then((s) => setMessages(s.messages || []))
        .catch(() => setMessages([]));
    } else {
      setMessages([]);
    }
  }, [sessionId, setMessages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamContent]);

  const handleSend = async (content: string) => {
    if (!sessionId) return;
    addUserMessage(content);
    await sendChat(Number(sessionId), content);
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <SessionList />
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="h-14 border-b border-gray-200 bg-white flex items-center px-6">
          <h2 className="text-sm font-medium text-gray-700">
            {sessionId ? `会话 #${sessionId}` : '新会话'}
          </h2>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {messages.length === 0 && !isStreaming && (
            <div className="flex items-center justify-center h-full text-gray-400 text-sm">
              输入问题开始对话
            </div>
          )}

          {messages.map((msg) => (
            <ChatBubble key={msg.id} message={msg} />
          ))}

          {isStreaming && <StreamingText content={streamContent} />}

          {error && (
            <div className="flex justify-center mb-4">
              <p className="text-red-500 text-sm bg-red-50 px-4 py-2 rounded-lg">{error}</p>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <ChatInput onSend={handleSend} disabled={isStreaming || !sessionId} />
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: add chat page with SSE streaming, session sidebar, and feedback"
```

---

### Task 16: 前端 - 知识库页面

**Files:**
- Create: `frontend/src/stores/sessionStore.ts` (补充)
- Create: `frontend/src/pages/KnowledgePage.tsx`
- Create: `frontend/src/api/feedback.ts`

- [ ] **Step 1: 补充 sessionStore `frontend/src/stores/sessionStore.ts`**

```typescript
import { create } from 'zustand';
import type { Session } from '../api/sessions';

interface SessionState {
  sessions: Session[];
  setSessions: (sessions: Session[]) => void;
  addSession: (session: Session) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  sessions: [],
  setSessions: (sessions) => set({ sessions }),
  addSession: (session) => set((s) => ({ sessions: [session, ...s.sessions] })),
}));
```

- [ ] **Step 2: 编写 Feedback API `frontend/src/api/feedback.ts`**

```typescript
import { request } from './client';

export async function submitFeedback(
  messageId: number,
  rating: string,
  comment?: string,
): Promise<{ id: number; message: string }> {
  return request('/feedback', {
    method: 'POST',
    body: JSON.stringify({ message_id: messageId, rating, comment }),
  });
}
```

- [ ] **Step 3: 编写 Knowledge API `frontend/src/api/knowledge.ts`**

```typescript
import { request } from './client';

export interface Document {
  id: number;
  name: string;
  file_type: string;
  status: string;
  chunk_count: number;
  file_size: number;
  created_at: string;
}

export async function listDocuments(): Promise<{ documents: Document[]; total: number }> {
  return request('/knowledge/list');
}

export async function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append('file', file);
  const token = localStorage.getItem('token');
  const res = await fetch('/api/knowledge/upload', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '上传失败' }));
    throw new Error(err.detail);
  }
  return res.json();
}

export async function deleteDocument(id: number): Promise<void> {
  return request(`/knowledge/${id}`, { method: 'DELETE' });
}
```

- [ ] **Step 4: 编写 KnowledgePage `frontend/src/pages/KnowledgePage.tsx`**

```tsx
import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { listDocuments, uploadDocument, deleteDocument, type Document } from '../api/knowledge';
import { ArrowLeft, Upload, Trash2, FileText, Loader2, CheckCircle, XCircle, Clock } from 'lucide-react';

const statusConfig: Record<string, { icon: typeof CheckCircle; color: string; label: string }> = {
  ready: { icon: CheckCircle, color: 'text-green-500', label: '就绪' },
  processing: { icon: Loader2, color: 'text-blue-500 animate-spin', label: '处理中' },
  failed: { icon: XCircle, color: 'text-red-500', label: '失败' },
};

const typeIcons: Record<string, string> = { txt: '📄', md: '📝', pdf: '📕' };

export function KnowledgePage() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const fetchDocs = async () => {
    try {
      const res = await listDocuments();
      setDocs(res.documents);
    } catch {}
  };

  useEffect(() => { fetchDocs(); }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadDocument(file);
      await fetchDocs();
    } catch {}
    setUploading(false);
    if (fileRef.current) fileRef.current.value = '';
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确认删除此文档？向量数据将同步清除。')) return;
    try {
      await deleteDocument(id);
      await fetchDocs();
    } catch {}
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto p-6">
        <div className="flex items-center gap-4 mb-8">
          <button onClick={() => navigate('/chat')} className="p-2 hover:bg-gray-200 rounded-lg transition">
            <ArrowLeft size={20} />
          </button>
          <h1 className="text-xl font-bold">知识库管理</h1>
        </div>

        {/* Upload */}
        <div className="mb-6">
          <label className="flex items-center justify-center gap-2 px-6 py-10 border-2 border-dashed border-gray-300 rounded-xl cursor-pointer hover:border-blue-400 hover:bg-blue-50/50 transition">
            <Upload size={20} className="text-gray-400" />
            <span className="text-sm text-gray-500">{uploading ? '上传中...' : '点击或拖拽上传文档 (.txt / .md / .pdf，最大 10MB)'}</span>
            <input ref={fileRef} type="file" accept=".txt,.md,.pdf" onChange={handleUpload} className="hidden" disabled={uploading} />
          </label>
        </div>

        {/* Doc List */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50">
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">文档名称</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">类型</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">状态</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">分块</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">上传时间</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-gray-500">操作</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((doc) => {
                const status = statusConfig[doc.status] || statusConfig.failed;
                const StatusIcon = status.icon;
                return (
                  <tr key={doc.id} className="border-b border-gray-50 hover:bg-gray-50/50 transition">
                    <td className="px-4 py-3 text-sm font-medium">{typeIcons[doc.file_type] || '📄'} {doc.name}</td>
                    <td className="px-4 py-3 text-xs text-gray-500 uppercase">{doc.file_type}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 text-xs ${status.color}`}>
                        <StatusIcon size={12} /> {status.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">{doc.chunk_count} 块</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{new Date(doc.created_at).toLocaleDateString('zh-CN')}</td>
                    <td className="px-4 py-3 text-right">
                      <button onClick={() => handleDelete(doc.id)} className="p-1.5 text-gray-400 hover:text-red-500 transition">
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                );
              })}
              {docs.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-gray-400 text-sm">暂无知识库文档</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add knowledge management page with upload and delete"
```

---

## Phase 5: 初始化脚本 & 端到端验证 (Day 4)

### Task 17: 系统初始化脚本

**Files:**
- Create: `backend/init_knowledge.py`

- [ ] **Step 1: 编写初始化脚本 `backend/init_knowledge.py`**

```python
"""系统初始化：将 example_docs 批量入库"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.rag.ingestion import DocumentIngestion
from app.rag.vector_store import VectorStore
from app.database import engine, SessionLocal, Base
from app.models import *  # noqa - 注册所有模型


def init_database():
    """创建所有表"""
    Base.metadata.create_all(bind=engine)
    print("✅ 数据库表创建完成")


def init_knowledge():
    """批量入库示例文档"""
    example_dir = os.path.join(os.path.dirname(__file__), "example_docs")
    if not os.path.isdir(example_dir):
        print("⚠️  example_docs 目录不存在")
        return

    ingestion = DocumentIngestion()
    db = SessionLocal()

    from app.models.document import Document, DocumentStatus

    for filename in os.listdir(example_dir):
        file_path = os.path.join(example_dir, filename)
        if not os.path.isfile(file_path):
            continue

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ("txt", "md", "pdf"):
            continue

        print(f"📄 处理: {filename} ...")
        result = ingestion.ingest_file(file_path)

        # 保存文档记录到 MySQL
        doc = Document(
            name=filename,
            file_type=ext,
            status=DocumentStatus.ready if result["success"] else DocumentStatus.failed,
            chunk_count=result["chunk_count"],
            file_size=os.path.getsize(file_path),
            milvus_ids=result["milvus_ids"],
            error_msg=result["error"],
        )
        db.add(doc)
        db.commit()

        if result["success"]:
            print(f"   ✅ {result['chunk_count']} 个分块入库成功")
        else:
            print(f"   ❌ 失败: {result['error']}")

    db.close()

    vs = VectorStore()
    print(f"\n📊 Milvus 向量总数: {vs.count()}")


if __name__ == "__main__":
    init_database()
    init_knowledge()
    print("\n🎉 初始化完成！")
```

- [ ] **Step 2: 运行初始化**

```bash
cd backend
cp .env.example .env
# 编辑 .env 填入 MySQL 密码 + DeepSeek API Key
python init_knowledge.py
```

Expected:
```
✅ 数据库表创建完成
📄 处理: 常见问题FAQ.md ...
   ✅ 15 个分块入库成功
📄 处理: 公司产品介绍.txt ...
   ✅ 8 个分块入库成功
📄 处理: 退换货政策.txt ...
   ✅ 10 个分块入库成功
📊 Milvus 向量总数: 33
🎉 初始化完成！
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: add system initialization script for DB + knowledge base"
```

---

### Task 18: 端到端验证

- [ ] **Step 1: 启动后端**

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

- [ ] **Step 2: 测试注册**

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800000001","password":"123456"}'
```

- [ ] **Step 3: 测试登录（保存 token）**

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"account":"13800000001","password":"123456"}' | python -c "import sys,json; print(json.load(sys.stdin)['token'])")
echo "Token: $TOKEN"
```

- [ ] **Step 4: 测试创建会话**

```bash
SESSION_ID=$(curl -s -X POST http://localhost:8000/api/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"测试会话"}' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Session: $SESSION_ID"
```

- [ ] **Step 5: 测试 RAG 问答**

```bash
curl -N -X POST "http://localhost:8000/api/chat/$SESSION_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"退换货流程是什么？"}'
```

Expected: 流式 SSE 输出，包含 token → sources → done 事件，回答引用退换货政策文档

- [ ] **Step 6: 测试空检索兜底**

```bash
curl -N -X POST "http://localhost:8000/api/chat/$SESSION_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"今天天气怎么样？"}'
```

Expected: 返回兜底话术，不编造答案

- [ ] **Step 7: 测试前端**

```bash
cd frontend
npm run dev
```

验证:
- 访问 `http://localhost:5173/login` → 登录
- 新建会话 → 提问"退换货流程"
- 确认: 流式逐字输出 + 引用来源卡片 + 反馈按钮
- 知识库页: 查看文档列表

- [ ] **Step 8: Commit final fixes**

```bash
git add -A
git commit -m "test: end-to-end verification of RAG pipeline and frontend"
```

---

## Phase 6: 文档编写 (Day 5)

### Task 19: 编写所有提交文档

- [ ] **Step 1: `docs/API文档.md`**

包含：
- 所有接口的 Method/Path/说明/请求体/响应体
- SSE 事件格式说明
- 错误码对照表
- curl 示例

- [ ] **Step 2: `docs/数据库设计.md`**

包含：
- Mermaid ER 图
- 每张表的字段说明、类型、约束
- 设计思路（为什么 messages.references 用 JSON，为什么 daily_question_count 独立表）

- [ ] **Step 3: `docs/AI架构设计.md`**

包含：
- Mermaid RAG 流程图
- System Prompt 完整模板
- 向量检索策略（Top-K=5, 阈值 0.65 的理由）
- 分层截断策略
- 幻觉防御四层体系

- [ ] **Step 4: `docs/业务流程说明.md`**

包含：
- 用户提问到拿到答案的完整时序图
- 文档入库流程

- [ ] **Step 5: `项目说明.md`**

包含：
- 技术选型及原因
- 整体 AI 架构图
- **重点**：AI 工程问题处理（检索为空/上下文超长/LLM 幻觉）
- AI 编程工具使用体会

- [ ] **Step 6: `运行指南.md`**

包含：
- 环境要求（Python 3.12+, Node 20+, MySQL 8.0+）
- .env 配置说明（每项含义）
- DeepSeek API Key 获取方式
- 完整启动步骤
- 常见问题排查

- [ ] **Step 7: 最终检查清单**

- [ ] `.env.example` 已存在，无真实 API Key
- [ ] `.gitignore` 包含 `.env`, `data/`, `__pycache__/`
- [ ] 所有 README.md 启动说明清晰
- [ ] 代码无硬编码密钥
- [ ] 核心 RAG 链路可独立运行验证

- [ ] **Step 8: 最终 commit**

```bash
git add -A
git commit -m "docs: add all required documentation"
```

---

## 总结

| Phase | 任务数 | 说明 |
|-------|--------|------|
| Phase 1 | 2 | 项目脚手架、DB 模型 |
| Phase 2 | 6 | RAG 核心模块（chunker → embedder → vector_store → ingestion → prompt → llm → stream） |
| Phase 3 | 4 | 后端 API（auth → sessions → chat SSE → knowledge + feedback + stats） |
| Phase 4 | 4 | 前端（auth pages → chat page + SSE → knowledge page） |
| Phase 5 | 2 | 初始化脚本 + E2E 验证 |
| Phase 6 | 1 | 全部文档 |

**总计 19 个 Task，约 100 个上下的 step。**
