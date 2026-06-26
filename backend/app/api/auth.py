"""认证接口"""
# TODO: Add rate limiting middleware (e.g., slowapi) for production
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, AuthResponse
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = auth_service.register_user(db, req.phone, req.password)
        token = auth_service.create_token(user.id)
        return AuthResponse(token=token, user_id=user.id, message="注册成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    try:
        user, token = auth_service.login_user(db, req.account, req.password)
        return AuthResponse(token=token, user_id=user.id, message="登录成功")
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
