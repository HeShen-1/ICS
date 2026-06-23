"""认证相关 Schema"""
from pydantic import BaseModel, field_validator
import re


class RegisterRequest(BaseModel):
    phone: str | None = None
    email: str | None = None
    password: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if v and not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError("密码至少 6 位")
        return v


class LoginRequest(BaseModel):
    account: str  # 手机号或邮箱
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: int
    message: str = "登录成功"
