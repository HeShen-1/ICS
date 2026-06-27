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
    feedback_rating: str | None = None  # "positive" / "negative" / None

    class Config:
        from_attributes = True


class SessionOut(BaseModel):
    id: int
    title: str
    status: str
    pinned: bool = False
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


class SessionDetailOut(SessionOut):
    messages: List[MessageOut] = []


class SessionCreate(BaseModel):
    title: str = "新会话"


class SessionUpdate(BaseModel):
    title: str


class SessionPin(BaseModel):
    pinned: bool


class SessionListResponse(BaseModel):
    sessions: List[SessionOut]
    total: int
