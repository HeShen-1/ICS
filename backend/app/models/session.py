"""会话模型"""
import enum

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database import Base


class SessionStatus(enum.Enum):
    active = "active"
    closed = "closed"


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="会话ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户ID")
    title = Column(String(100), default="新会话", comment="会话标题")
    status = Column(Enum(SessionStatus), default=SessionStatus.active, comment="会话状态")
    pinned = Column(Boolean, default=False, comment="是否置顶")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="最后更新时间",
    )

    user = relationship("User", back_populates="sessions")
    messages = relationship(
        "Message",
        back_populates="session",
        order_by="Message.created_at",
        cascade="all, delete-orphan",
    )
