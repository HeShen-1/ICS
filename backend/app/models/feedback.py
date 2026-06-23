"""反馈模型"""
import enum
from datetime import datetime

from sqlalchemy import Column, Integer, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class FeedbackRating(enum.Enum):
    positive = "positive"
    negative = "negative"


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="反馈ID")
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False, comment="被评价的消息ID")
    rating = Column(Enum(FeedbackRating), nullable=False, comment="赞/踩")
    comment = Column(Text, nullable=True, comment="反馈文字(可选)")
    created_at = Column(DateTime, default=datetime.utcnow, comment="反馈时间")

    message = relationship("Message", back_populates="feedback")
