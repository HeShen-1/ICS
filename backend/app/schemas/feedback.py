from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    message_id: int
    rating: str  # "positive" / "negative"
    comment: str | None = None


class FeedbackResponse(BaseModel):
    id: int
    message: str = "反馈提交成功"
