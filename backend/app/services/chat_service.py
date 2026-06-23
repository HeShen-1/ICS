"""聊天服务"""
from sqlalchemy.orm import Session
from app.config import get_settings


def check_daily_limit(db: Session, user_id: int) -> bool:
    """检查每日提问次数，返回 True 表示未超限"""
    settings = get_settings()
    from datetime import date

    today = date.today()
    result = db.execute(
        db.text(
            "SELECT count FROM daily_question_count "
            "WHERE user_id = :uid AND query_date = :qdate"
        ),
        {"uid": user_id, "qdate": today},
    ).fetchone()

    current = result[0] if result else 0
    return current < settings.daily_question_limit


def increment_question_count(db: Session, user_id: int):
    """增加当日提问计数"""
    from datetime import date
    today = date.today()

    existing = db.execute(
        db.text(
            "SELECT id FROM daily_question_count "
            "WHERE user_id = :uid AND query_date = :qdate"
        ),
        {"uid": user_id, "qdate": today},
    ).fetchone()

    if existing:
        db.execute(
            db.text(
                "UPDATE daily_question_count SET count = count + 1 "
                "WHERE id = :id"
            ),
            {"id": existing[0]},
        )
    else:
        db.execute(
            db.text(
                "INSERT INTO daily_question_count (user_id, query_date, count) "
                "VALUES (:uid, :qdate, 1)"
            ),
            {"uid": user_id, "qdate": today},
        )
    db.commit()


def validate_question(content: str) -> str | None:
    """校验问题，返回错误信息或 None"""
    settings = get_settings()
    if not content or not content.strip():
        return "问题不能为空"
    if len(content) > settings.max_question_length:
        return f"问题长度不能超过 {settings.max_question_length} 字"
    return None
