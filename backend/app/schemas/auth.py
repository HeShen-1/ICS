"""认证相关 Schema"""
from pydantic import BaseModel, field_validator
import re


class RegisterRequest(BaseModel):
    phone: str
    password: str
    email: str | None = None  # 保留兼容，注册时忽略

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if not re.match(r"^1\d{10}$", v):
            raise ValueError("手机号格式不正确（11 位数字，以 1 开头）")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("密码至少 8 位")
        if not re.search(r"[A-Z]", v):
            raise ValueError("密码必须包含至少一个大写字母")
        if not re.search(r"[a-z]", v):
            raise ValueError("密码必须包含至少一个小写字母")
        if not re.search(r"\d", v):
            raise ValueError("密码必须包含至少一个数字")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=~`\[\];'/\\]", v):
            raise ValueError("密码必须包含至少一个特殊字符")
        return v


class LoginRequest(BaseModel):
    account: str  # 手机号或邮箱
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: int
    message: str = "登录成功"
