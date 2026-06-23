"""每日提问计数模型"""
from sqlalchemy import Column, Integer, Date, ForeignKey, func
from app.database import Base


class DailyQuestionCount(Base):
    __tablename__ = "daily_question_count"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    query_date = Column(Date, nullable=False)
    count = Column(Integer, default=0)
