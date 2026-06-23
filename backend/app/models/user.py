"""用户模型"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    phone = Column(String(20), unique=True, nullable=True, comment="手机号(与email至少一个非空)")
    email = Column(String(255), unique=True, nullable=True, comment="邮箱(与phone至少一个非空)")
    password_hash = Column(String(255), nullable=False, comment="bcrypt哈希密码")
    created_at = Column(DateTime, default=datetime.utcnow, comment="注册时间")

    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
