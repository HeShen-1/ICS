"""统计接口"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user_id

router = APIRouter(prefix="/api/stats", tags=["统计"])


@router.get("/daily")
def daily_usage(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    from datetime import date
    today = date.today()
    result = db.execute(
        db.text(
            "SELECT count FROM daily_question_count "
            "WHERE user_id = :uid AND query_date = :qdate"
        ),
        {"uid": user_id, "qdate": today},
    ).fetchone()

    return {
        "date": str(today),
        "count": result[0] if result else 0,
    }
