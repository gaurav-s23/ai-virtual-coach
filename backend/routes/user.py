from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

try:
    from .. import models
    from ..database import get_db
    from ..core.security import get_current_user
    from .schemas import DashboardResponse, StatsUpdate, UserStatsResponse
except ImportError:
    import models  # type: ignore
    from database import get_db  # type: ignore
    from core.security import get_current_user  # type: ignore
    from routes.schemas import DashboardResponse, StatsUpdate, UserStatsResponse  # type: ignore

router = APIRouter(prefix="/api", tags=["User"])


def _user_stats_payload(user: "models.User") -> dict:
    return {
        "readiness": user.readiness_score,
        "interviews": user.total_interviews,
        "mocks": user.total_mocks,
        "streak": user.streak_count,
        "email": user.email,
    }


@router.get("/user/stats/{user_id}", response_model=UserStatsResponse)
async def get_stats(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid input")
    return _user_stats_payload(user)


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    user_id: int = Query(...),
    db: Session = Depends(get_db),
    _current_user: "models.User" = Depends(get_current_user),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid input")

    base = _user_stats_payload(user)
    readiness = base["readiness"]
    return {
        "readiness": readiness,
        "attendance": base["streak"],
        "interviews": base["interviews"],
        "mocks": base["mocks"],
        "avgScore": 0,
        "lastScore": 0,
        "skills": [
            {"subject": "Technical", "A": min(100, max(0, readiness))},
            {"subject": "Logic", "A": min(100, max(0, readiness - 10))},
            {"subject": "Confidence", "A": min(100, max(0, readiness + 5))},
            {"subject": "Communication", "A": min(100, max(0, readiness - 5))},
            {"subject": "Pace", "A": min(100, max(0, readiness))},
        ],
        "email": base["email"],
    }


@router.post("/user/update-stats/{user_id}")
async def update_stats(
    user_id: int,
    data: StatsUpdate,
    db: Session = Depends(get_db),
    current_user: "models.User" = Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Invalid input")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        if data.type == "interview":
            user.total_interviews += 1
            user.readiness_score = min(100, user.readiness_score + 3)
        else:
            user.total_mocks += 1
            user.readiness_score = min(100, user.readiness_score + 1)
        db.commit()
    return {"status": "ok"}
