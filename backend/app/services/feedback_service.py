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


def get_message_feedback(db: Session, message_id: int) -> str | None:
    """获取消息的已有点赞/踩, 不存在返回 None"""
    fb = (
        db.query(Feedback)
        .filter(Feedback.message_id == message_id)
        .first()
    )
    return fb.rating.value if fb else None
