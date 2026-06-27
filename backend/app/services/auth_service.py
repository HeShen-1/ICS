"""认证服务"""
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone
from app.models.user import User
from app.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "iss": "ics-api",
        "aud": "ics-frontend",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> int | None:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience="ics-frontend",
        )
        return int(payload["sub"])
    except (jwt.ExpiredSignatureError, jwt.JWTError, KeyError, ValueError):
        return None


def register_user(db: Session, phone: str, password: str) -> User:
    existing = db.query(User).filter(User.phone == phone).first()
    if existing:
        raise ValueError("该手机号已注册")

    user = User(
        phone=phone,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_user(db: Session, account: str, password: str) -> tuple[User, str]:
    user = db.query(User).filter(
        (User.phone == account) | (User.email == account)
    ).first()

    if not user:
        raise ValueError("账号或密码错误")

    if not verify_password(password, user.password_hash):
        raise ValueError("账号或密码错误")

    token = create_token(user.id)
    return user, token
