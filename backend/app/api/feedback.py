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
