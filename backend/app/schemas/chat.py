"""聊天 Schema"""
from pydantic import BaseModel


class ChatRequest(BaseModel):
    content: str
    intent: str | None = None
    kb_id: int | None = None
