"""聊天服务"""
from datetime import date
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.daily_question import DailyQuestionCount


def check_and_increment_daily_limit(db: Session, user_id: int) -> bool:
    """原子地检查并增加每日提问计数，返回 True 表示未超限"""
    settings = get_settings()
    today = date.today()

    # 使用 SELECT ... FOR UPDATE 实现原子 upsert
    record = (
        db.query(DailyQuestionCount)
        .filter(
            DailyQuestionCount.user_id == user_id,
            DailyQuestionCount.query_date == today,
        )
        .with_for_update()
        .first()
    )

    if record:
        if record.count >= settings.daily_question_limit:
            db.rollback()  # Release FOR UPDATE lock before returning
            return False
        record.count += 1
    else:
        db.add(DailyQuestionCount(user_id=user_id, query_date=today, count=1))
    db.commit()
    return True


def validate_question(content: str) -> str | None:
    """校验问题，返回错误信息或 None"""
    settings = get_settings()
    if not content or not content.strip():
        return "问题不能为空"
    if len(content) > settings.max_question_length:
        return f"问题长度不能超过 {settings.max_question_length} 字"
    return None
