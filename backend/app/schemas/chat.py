"""聊天 Schema"""
from pydantic import BaseModel, field_validator


class ChatRequest(BaseModel):
    content: str
    intent: str | None = None
    kb_id: int | None = None

    @field_validator("content")
    @classmethod
    def validate_content_no_injection(cls, v: str) -> str:
        from app.utils.security import check_injection

        error = check_injection(v)
        if error:
            raise ValueError(error)
        return v
