"""会话服务"""
from typing import List
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.session import Session as SessionModel, SessionStatus
from app.models.message import Message as MessageModel, MessageRole


def create_session(db: Session, user_id: int, title: str = "新会话") -> SessionModel:
    session = SessionModel(user_id=user_id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_user_sessions(db: Session, user_id: int) -> List[SessionModel]:
    return (
        db.query(SessionModel)
        .filter(SessionModel.user_id == user_id)
        .order_by(SessionModel.updated_at.desc())
        .all()
    )


def get_session_detail(db: Session, session_id: int, user_id: int) -> SessionModel | None:
    return (
        db.query(SessionModel)
        .filter(
            SessionModel.id == session_id,
            SessionModel.user_id == user_id,
        )
        .first()
    )


def create_message(
    db: Session,
    session_id: int,
    role: str,
    content: str,
    intent_tag: str | None = None,
    references: list | None = None,
) -> MessageModel:
    msg = MessageModel(
        session_id=session_id,
        role=MessageRole(role),
        content=content,
        intent_tag=intent_tag,
        references_json=references,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    # 更新会话时间
    db.query(SessionModel).filter(SessionModel.id == session_id).update(
        {"updated_at": func.now()}
    )
    db.commit()
    return msg


def get_session_messages(db: Session, session_id: int) -> List[MessageModel]:
    return (
        db.query(MessageModel)
        .filter(MessageModel.session_id == session_id)
        .order_by(MessageModel.created_at.asc())
        .all()
    )
