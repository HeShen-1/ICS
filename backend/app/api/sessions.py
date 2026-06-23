"""会话接口"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.message import Message
from app.models.session import Session as SessionModel
from app.schemas.session import (
    SessionCreate,
    SessionOut,
    SessionDetailOut,
    SessionListResponse,
)
from app.services import session_service

router = APIRouter(prefix="/api/sessions", tags=["会话"])


@router.get("", response_model=SessionListResponse)
def list_sessions(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    sessions = session_service.get_user_sessions(db, user_id)

    # 批量查询消息计数，避免 N+1 查询
    session_ids = [s.id for s in sessions]
    message_counts = {}
    if session_ids:
        rows = (
            db.query(SessionModel.id, func.count(Message.id))
            .outerjoin(Message, Message.session_id == SessionModel.id)
            .filter(SessionModel.id.in_(session_ids))
            .group_by(SessionModel.id)
            .all()
        )
        message_counts = {row[0]: row[1] for row in rows}

    return SessionListResponse(
        sessions=[
            SessionOut(
                id=s.id,
                title=s.title,
                status=s.status.value,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=message_counts.get(s.id, 0),
            )
            for s in sessions
        ],
        total=len(sessions),
    )


@router.post("", response_model=SessionOut)
def create_new_session(
    req: SessionCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    session = session_service.create_session(db, user_id, req.title)
    return SessionOut(
        id=session.id,
        title=session.title,
        status=session.status.value,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0,
    )


@router.get("/{session_id}", response_model=SessionDetailOut)
def get_session(
    session_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    session = session_service.get_session_detail(db, session_id, user_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    return SessionDetailOut(
        id=session.id,
        title=session.title,
        status=session.status.value,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(session.messages),
        messages=[
            {
                "id": m.id,
                "role": m.role.value,
                "content": m.content,
                "intent_tag": m.intent_tag,
                "references": m.references_json,
                "created_at": m.created_at,
            }
            for m in session.messages
        ],
    )
