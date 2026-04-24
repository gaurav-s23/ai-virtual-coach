from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

# Configure logger
logger = logging.getLogger(__name__)

try:
    from models import User, MockTest
    from database import get_db
    from core.security import get_current_user
    from routes.schemas import DashboardResponse, StatsUpdate, UserStatsResponse
except ImportError as e:
    logger.error(f"Import error in user.py: {e}")
    # Fallback imports for development
    try:
        import models
        from database import get_db
        from core.security import get_current_user
        from routes.schemas import DashboardResponse, StatsUpdate, UserStatsResponse
    except ImportError as fallback_error:
        logger.error(f"Fallback import error in user.py: {fallback_error}")
        raise SystemExit(f"Failed to import required modules in user.py: {fallback_error}")

router = APIRouter(prefix="/api", tags=["User"])


def _user_stats_payload(user: User) -> dict:
    return {
        "readiness": user.readiness_score,
        "interviews": user.total_interviews,
        "mocks": user.total_mocks,
        "streak": user.streak_count,
        "email": user.email,
    }


@router.get("/user/stats/{user_id}", response_model=UserStatsResponse)
async def get_stats(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_stats_payload(user)


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    user_id: int = Query(...),
    db: Session = Depends(get_db),
    _current_user: "User" = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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
    current_user: "User" = Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Access denied: cannot access other user's data")
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        if data.type == "interview":
            user.total_interviews += 1
            user.readiness_score = min(100, user.readiness_score + 3)
        else:
            user.total_mocks += 1
            user.readiness_score = min(100, user.readiness_score + 1)
        db.commit()
    return {"status": "ok"}


@router.get("/user/dashboard-stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: "User" = Depends(get_current_user)
):
    """Get comprehensive dashboard statistics for the logged-in user"""
    try:
        user_id = current_user.id
        
        # Get Mock Test stats
        mock_tests = db.query(MockTest).filter(MockTest.user_id == user_id).all()
        mock_completed = [m for m in mock_tests if m.status == "completed"]
        mock_abandoned = [m for m in mock_tests if m.status == "abandoned"]
        
        # Calculate Mock section scores
        mock_section_scores = {"quant": 0, "verbal": 0, "reasoning": 0, "coding": 0}
        if mock_completed:
            section_totals = {"quant": [], "verbal": [], "reasoning": [], "coding": []}
            for test in mock_completed:
                if test.section_scores:
                    for section, score in test.section_scores.items():
                        if section.lower() in section_totals:
                            section_totals[section.lower()].append(score)
            
            for section, scores in section_totals.items():
                mock_section_scores[section] = sum(scores) / len(scores) if scores else 0
        
        mock_stats = {
            "total_attempted": len(mock_tests),
            "completed": len(mock_completed),
            "abandoned": len(mock_abandoned),
            "avg_score": sum(m.score for m in mock_completed) / len(mock_completed) if mock_completed else 0,
            "section_scores": mock_section_scores
        }
        
        # Get Interview stats
        interviews = db.query(models.Interview).filter(models.Interview.user_id == user_id).all()
        interview_completed = [i for i in interviews if i.status == "completed"]
        
        # Extract weak areas and fluency from interviews
        interview_weak_areas = []
        fluency_scores = []
        
        for interview in interview_completed:
            if interview.transcript:
                for entry in interview.transcript:
                    if isinstance(entry, dict) and "assistant_reply" in entry:
                        reply = entry["assistant_reply"].lower()
                        if "weak" in reply or "improve" in reply:
                            if "communication" in reply:
                                interview_weak_areas.append("Communication")
                            if "technical" in reply or "coding" in reply:
                                interview_weak_areas.append("Technical Skills")
                            if "confidence" in reply:
                                interview_weak_areas.append("Confidence")
                            if "fluency" in reply:
                                interview_weak_areas.append("Fluency")
                        
                        if "fluency" in reply or "speaking" in reply:
                            if "good" in reply or "excellent" in reply:
                                fluency_scores.append(80)
                            elif "average" in reply or "okay" in reply:
                                fluency_scores.append(60)
                            else:
                                fluency_scores.append(40)
        
        interview_stats = {
            "total_attempted": len(interviews),
            "avg_score": sum(i.overall_score for i in interview_completed if i.overall_score) / len(interview_completed) if interview_completed else 0,
            "fluency_score": sum(fluency_scores) / len(fluency_scores) if fluency_scores else 70,
            "weak_areas": list(set(interview_weak_areas))
        }
        
        # Get English stats
        english_sessions = db.query(models.EnglishSession).filter(models.EnglishSession.user_id == user_id).all()
        english_completed = [s for s in english_sessions if s.status == "completed"]
        
        english_weak_areas = []
        fluency_ratings = [s.communication_rating for s in english_completed if s.communication_rating]
        
        for session in english_completed:
            if session.feedback:
                feedback = session.feedback.lower()
                if "grammar" in feedback:
                    english_weak_areas.append("Grammar")
                if "vocabulary" in feedback:
                    english_weak_areas.append("Vocabulary")
                if "fluency" in feedback:
                    english_weak_areas.append("Fluency")
                if "pronunciation" in feedback:
                    english_weak_areas.append("Pronunciation")
        
        english_stats = {
            "total_attempted": len(english_sessions),
            "avg_fluency_score": sum(fluency_ratings) / len(fluency_ratings) if fluency_ratings else 0
        }
        
        # Get daily activity for last 7 days
        daily_activity = []
        for i in range(7):
            date = datetime.utcnow().date() - timedelta(days=i)
            
            mock_count = len([m for m in mock_tests if m.created_at.date() == date])
            interview_count = len([i for i in interviews if i.created_at.date() == date])
            english_count = len([e for e in english_sessions if e.created_at.date() == date])
            
            daily_activity.append({
                "date": str(date),
                "mock_count": mock_count,
                "interview_count": interview_count,
                "english_count": english_count
            })
        
        daily_activity.reverse()  # Show oldest to newest
        
        # Combine all weak areas
        all_weak_areas = list(set(
            mock_stats.get("weak_areas", []) + 
            interview_stats["weak_areas"] + 
            english_weak_areas
        ))
        
        return {
            "mock": mock_stats,
            "interview": interview_stats,
            "english": english_stats,
            "daily_activity": daily_activity,
            "overall_weak_areas": all_weak_areas
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {str(e)}")
