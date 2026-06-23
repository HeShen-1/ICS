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
