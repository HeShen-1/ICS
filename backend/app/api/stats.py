"""统计接口"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user_id
from app.services.stats_service import get_overview, get_daily_trend, get_feedback_sessions

router = APIRouter(prefix="/api/stats", tags=["统计"])


@router.get("/daily")
def daily_usage(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    from datetime import date
    today = date.today()
    result = db.execute(
        text(
            "SELECT count FROM daily_question_count "
            "WHERE user_id = :uid AND query_date = :qdate"
        ),
        {"uid": user_id, "qdate": today},
    ).fetchone()

    return {
        "date": str(today),
        "count": result[0] if result else 0,
    }


@router.get("/overview")
def stats_overview(db: Session = Depends(get_db)):
    """管理后台 - 概览统计"""
    return get_overview(db)


@router.get("/daily_trend")
def stats_daily_trend(
    days: int = Query(default=7, ge=1, le=90, description="统计天数"),
    db: Session = Depends(get_db),
):
    """管理后台 - 每日提问趋势"""
    return get_daily_trend(db, days)


@router.get("/feedback_sessions")
def feedback_sessions(db: Session = Depends(get_db)):
    """管理后台 - 各会话评价统计"""
    return get_feedback_sessions(db)

