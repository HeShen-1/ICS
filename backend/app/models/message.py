"""消息模型"""
import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class MessageRole(enum.Enum):
    user = "user"
    assistant = "assistant"


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="消息ID")
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, comment="所属会话ID")
    role = Column(Enum(MessageRole), nullable=False, comment="发言角色")
    content = Column(Text, nullable=False, comment="消息正文")
    intent_tag = Column(String(50), nullable=True, comment="意图标签(可选)")
    references_json = Column(JSON, nullable=True, comment="引用来源JSON数组")
    created_at = Column(DateTime, default=datetime.utcnow, comment="发送时间")

    session = relationship("Session", back_populates="messages")
    feedback = relationship("Feedback", back_populates="message", cascade="all, delete-orphan")
