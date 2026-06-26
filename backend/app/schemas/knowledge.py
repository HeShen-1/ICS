"""知识库 Schema"""
from pydantic import BaseModel, Field
from datetime import datetime


class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求"""
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None


class KnowledgeBaseOut(BaseModel):
    """知识库响应"""
    id: int
    user_id: int
    name: str
    description: str | None
    document_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应"""
    knowledge_bases: list[KnowledgeBaseOut]
    total: int


class DocumentOut(BaseModel):
    """文档响应"""
    id: int
    name: str
    file_type: str
    status: str
    chunk_count: int
    file_size: int
    kb_id: int | None = None
    kb_name: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    documents: list[DocumentOut]
    total: int


class DocumentContentOut(BaseModel):
    """文档原始内容响应"""
    id: int
    name: str
    content: str


class ChunkOut(BaseModel):
    """分块信息"""
    chunk_index: int
    text: str
    source: str


class DocumentChunksOut(BaseModel):
    """文档分块列表响应"""
    id: int
    name: str
    chunks: list[ChunkOut]
