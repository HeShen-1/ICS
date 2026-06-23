from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.message import Message
from app.models.session import Session
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

    # 检查消息是否属于当前用户的会话
    msg = db.query(Message).join(Session).filter(
        Message.id == req.message_id,
        Session.user_id == user_id,
    ).first()
    if not msg:
        raise HTTPException(404, "消息不存在")

    fb = feedback_service.submit_feedback(db, req.message_id, req.rating, req.comment)
    return FeedbackResponse(id=fb.id)
