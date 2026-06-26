"""统计查询服务"""
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.user import User
from app.models.session import Session
from app.models.message import Message, MessageRole
from app.models.document import Document
from app.models.feedback import Feedback, FeedbackRating


def get_overview(db: Session) -> dict:
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_sessions = db.query(func.count(Session.id)).scalar() or 0
    total_messages = db.query(func.count(Message.id)).scalar() or 0
    total_documents = db.query(func.count(Document.id)).scalar() or 0
    feedback_positive_count = (
        db.query(func.count(Feedback.id))
        .filter(Feedback.rating == FeedbackRating.positive)
        .scalar()
        or 0
    )
    feedback_negative_count = (
        db.query(func.count(Feedback.id))
        .filter(Feedback.rating == FeedbackRating.negative)
        .scalar()
        or 0
    )

    return {
        "total_users": total_users,
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "total_documents": total_documents,
        "feedback_positive_count": feedback_positive_count,
        "feedback_negative_count": feedback_negative_count,
    }


def get_daily_trend(db: Session, days: int = 7) -> list[dict]:
    since = date.today() - timedelta(days=days - 1)
    results = (
        db.query(
            func.date(Message.created_at).label("date"),
            func.count(Message.id).label("count"),
        )
        .filter(Message.role == MessageRole.user)
        .filter(func.date(Message.created_at) >= since)
        .group_by(func.date(Message.created_at))
        .order_by(func.date(Message.created_at))
        .all()
    )

    result_map = {str(r.date): r.count for r in results}
    trend = []
    for i in range(days):
        d = since + timedelta(days=i)
        key = str(d)
        trend.append({"date": key, "count": result_map.get(key, 0)})

    return trend
