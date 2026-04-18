from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from jose import jwt
from sqlalchemy.orm import Session

try:
    from .. import models
    from ..database import get_db
    from ..core.config import get_settings
    from ..core.security import get_admin_user
    from ..auth.security import _jwt_secret
    from .schemas import AdminLoginRequest
except ImportError:
    import models  # type: ignore
    from database import get_db  # type: ignore
    from core.config import get_settings  # type: ignore
    from core.security import get_admin_user  # type: ignore
    from auth.security import _jwt_secret  # type: ignore
    from routes.schemas import AdminLoginRequest  # type: ignore

router = APIRouter(tags=["Admin"])
settings = get_settings()


@router.post("/api/admin/login")
@router.post("/admin/login")
async def admin_login(data: AdminLoginRequest):
    if not settings.admin_email or not settings.admin_password:
        raise HTTPException(status_code=500, detail="Server error, try again")
    if (data.email or "").strip().lower() != settings.admin_email or data.password != settings.admin_password:
        raise HTTPException(status_code=403, detail="Invalid input")

    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "admin",
            "type": "access",
            "role": "admin",
            "iat": int(now.timestamp()),
            "exp": now + timedelta(hours=8),
        },
        _jwt_secret(),
        algorithm="HS256",
    )
    return {"admin_token": token}




@router.get("/api/admin/stats")
async def admin_stats(db: Session = Depends(get_db), _: dict = Depends(get_admin_user)):
    return {
        "total_users": db.query(models.User).count(),
        "total_interviews": db.query(models.Interview).count(),
        "total_mocks": db.query(models.MockTest).count(),
        "total_english": db.query(models.EnglishSession).count(),
    }


@router.get("/api/admin/users")
async def admin_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=5000),
    db: Session = Depends(get_db),
    _: dict = Depends(get_admin_user),
):
    users = (
        db.query(models.User)
        .order_by(models.User.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "readiness_score": u.readiness_score,
            "total_interviews": u.total_interviews,
            "total_mocks": u.total_mocks,
            "total_english_sessions": u.total_english_sessions,
            "streak_count": u.streak_count,
            "created_at": str(u.created_at),
            "last_login": str(u.last_login),
        }
        for u in users
    ]


@router.get("/api/admin/users/{user_id}")
async def admin_user_detail(user_id: int, db: Session = Depends(get_db), _: dict = Depends(get_admin_user)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid input")
    interviews = db.query(models.Interview).filter(models.Interview.user_id == user_id).all()
    mocks = db.query(models.MockTest).filter(models.MockTest.user_id == user_id).all()
    english = db.query(models.EnglishSession).filter(models.EnglishSession.user_id == user_id).all()
    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "readiness_score": user.readiness_score,
            "streak_count": user.streak_count,
            "created_at": str(user.created_at),
        },
        "interviews": [{"id": i.id, "role": i.role, "score": i.overall_score, "created_at": str(i.created_at)} for i in interviews],
        "mocks": [{"id": m.id, "category": m.category, "score": m.score, "created_at": str(m.created_at)} for m in mocks],
        "english": [{"id": e.id, "topic": e.topic, "rating": e.rating, "created_at": str(e.created_at)} for e in english],
    }
