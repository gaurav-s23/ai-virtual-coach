from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from jose import jwt
from sqlalchemy.orm import Session

# Configure logger
logger = logging.getLogger(__name__)

try:
    from models import User, Interview, MockTest, EnglishSession
    from database import get_db
    from core.config import get_settings
    from core.security import get_admin_user
    from auth.security import _jwt_secret
    from routes.schemas import AdminLoginRequest
except ImportError as e:
    logger.error(f"Import error in admin.py: {e}")
    # Fallback imports for development
    try:
        import models
        from database import get_db
        from core.config import get_settings
        from core.security import get_admin_user
        from auth.security import _jwt_secret
        from routes.schemas import AdminLoginRequest
    except ImportError as fallback_error:
        logger.error(f"Fallback import error in admin.py: {fallback_error}")
        raise SystemExit(f"Failed to import required modules in admin.py: {fallback_error}")

router = APIRouter(tags=["Admin"])
settings = get_settings()


@router.post("/api/admin/login")
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
    # Get today's date
    today = datetime.now(timezone.utc).date()
    
    # Count total requests today (all session types created today)
    total_requests_today = (
        db.query(Interview).filter(Interview.created_at >= today).count() +
        db.query(MockTest).filter(MockTest.created_at >= today).count() +
        db.query(EnglishSession).filter(EnglishSession.created_at >= today).count()
    )
    
    # Get all users with their details
    all_users = []
    users = db.query(User).all()
    for user in users:
        # Get resume skills (simple extraction from resume context if available)
        resume_skills = []
        if user.resume_context:
            # Simple skill extraction - in real implementation this would be more sophisticated
            skills_keywords = ["python", "javascript", "react", "node", "java", "sql", "aws", "docker", "git", "machine learning"]
            resume_text = user.resume_context.lower()
            resume_skills = [skill for skill in skills_keywords if skill in resume_text]
        
        all_users.append({
            "id": user.id,
            "name": user.name or "User",
            "email": user.email,
            "resume_skills": resume_skills,
            "joined_date": str(user.created_at.date()) if user.created_at else "Unknown"
        })
    
    return {
        "total_users": db.query(User).count(),
        "total_mock_sessions": db.query(MockTest).count(),
        "total_interview_sessions": db.query(Interview).count(),
        "total_english_sessions": db.query(EnglishSession).count(),
        "total_requests_today": total_requests_today,
        "all_users": all_users
    }


@router.get("/api/admin/users")
async def admin_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=5000),
    db: Session = Depends(get_db),
    _: dict = Depends(get_admin_user),
):
    users = (
        db.query(User)
        .order_by(User.created_at.desc())
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
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid input")
    interviews = db.query(Interview).filter(Interview.user_id == user_id).all()
    mocks = db.query(MockTest).filter(MockTest.user_id == user_id).all()
    english = db.query(EnglishSession).filter(EnglishSession.user_id == user_id).all()
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
