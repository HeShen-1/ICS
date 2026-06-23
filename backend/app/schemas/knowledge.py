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
