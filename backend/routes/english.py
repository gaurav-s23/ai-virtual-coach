from __future__ import annotations

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

try:
    from models import User, EnglishSession
    from database import get_db
    from core.security import get_current_user
    from core.rate_limit import enforce_rate_limit
    from services.llm_service import generate_english_questions, generate_final_report
    from services.llm_client import LLMClient
    from utils.sse import SSEEvent, StreamingResponse
except ImportError as e:
    logger.error(f"Import error in english.py: {e}")
    # Fallback imports for development
    try:
        import models
        from database import get_db
        from core.security import get_current_user
        from core.rate_limit import enforce_rate_limit
        from services.llm_service import generate_english_questions, generate_final_report
        from services.llm_client import LLMClient
        from utils.sse import SSEEvent, StreamingResponse
    except ImportError as fallback_error:
        logger.error(f"Fallback import error in english.py: {fallback_error}")
        raise SystemExit(f"Failed to import required modules in english.py: {fallback_error}")

router = APIRouter(prefix="/api", tags=["English Practice"])
logger = logging.getLogger("ai_virtual_coach.routes.english")

# English practice topics
ENGLISH_TOPICS = [
    "Modern Leadership Ethics",
    "Climate Change Solutions",
    "Artificial Intelligence Impact",
    "Global Economic Trends",
    "Remote Work Culture",
    "Mental Health Awareness",
    "Sustainable Technology",
    "Social Media Influence",
    "Digital Privacy Rights",
    "Future of Education"
]


@router.get("/english/topic")
async def get_english_topic(_user: User = Depends(get_current_user)):
    """Return a random English practice topic"""
    import random
    topic = random.choice(ENGLISH_TOPICS)
    return {"topic": topic}


@router.post("/english/questions")
async def get_english_questions(
    data: dict,
    _user: User = Depends(get_current_user)
):
    """Generate English practice questions for a topic"""
    try:
        enforce_rate_limit(key=f"english_questions:{_user.id}", max_requests=10, window_seconds=60)
        
        topic = data.get("topic", "Modern Leadership Ethics")
        phase = data.get("phase", "primary")
        
        questions = await generate_english_questions(topic)
        
        # Add session_id for tracking
        import time
        session_id = f"english_{int(time.time())}"
        
        logger.info("english_questions_generated user_id=%s topic=%s phase=%s", _user.id, topic, phase)
        
        return {
            "questions": questions,
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error("english_questions_error user_id=%s error=%s", _user.id, str(e))
        raise HTTPException(status_code=500, detail="Failed to generate questions")


@router.post("/english/chat")
async def english_practice_chat(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Streaming endpoint for English practice feedback"""
    enforce_rate_limit(key=f"english_chat:{current_user.id}", max_requests=30, window_seconds=60)
    
    session_id = data.get("session_id")
    user_answer = data.get("answer")
    
    if not session_id or not user_answer:
        raise HTTPException(status_code=400, detail="session_id and answer are required")
    
    async def english_chat_stream():
        try:
            # Use unified LLM client for streaming feedback
            llm_client = LLMClient()
            
            # Create streaming prompt for English practice feedback
            feedback_prompt = f"""
            You are an expert English language coach providing real-time feedback for a student's response.
            
            Student's Answer: "{user_answer}"
            
            Provide constructive feedback that:
            1. Evaluates grammar and vocabulary usage
            2. Suggests improvements for fluency and clarity
            3. Maintains encouraging and supportive tone
            4. Is concise (2-3 sentences max)
            5. Focuses on one or two key areas for improvement
            
            Return only the feedback text.
            """
            
            async for chunk in llm_client.generate_stream(
                prompt=feedback_prompt,
                model_type="fast",  # Use faster model for English drills
                temperature=0.4
            ):
                if chunk.type == "content":
                    yield SSEEvent("content", {"chunk": chunk.content})
                elif chunk.type == "complete":
                    # Save session interaction to database
                    try:
                        english_session = db.query(EnglishSession).filter(
                            EnglishSession.session_id == session_id,
                            EnglishSession.user_id == current_user.id
                        ).first()
                        
                        if english_session:
                            # Update session with interaction
                            if not english_session.interactions:
                                english_session.interactions = []
                            english_session.interactions.append({
                                "user_answer": user_answer,
                                "ai_feedback": chunk.content,
                                "timestamp": datetime.now().isoformat()
                            })
                            db.commit()
                    except Exception:
                        logger.warning("Failed to save English session interaction")
                    
                    # Send complete event with feedback
                    yield SSEEvent("complete", {
                        "feedback": chunk.content
                    })
                    break
                elif chunk.type == "error":
                    yield SSEEvent("error", {"error": chunk.content})
                    break
                    
        except Exception as e:
            logger.error("Error in English chat streaming: %s", str(e))
            yield SSEEvent("error", {"error": "Failed to process English practice response"})
    
    return StreamingResponse(english_chat_stream())


@router.post("/english/start-session")
async def start_english_session(
    session_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start a new English practice session"""
    try:
        session_id = session_data.get("session_id")
        topic = session_data.get("topic")
        
        # Create English session record
        english_session = EnglishSession(
            user_id=current_user.id,
            session_id=session_id,
            topic=topic,
            status="in_progress",
            started_at=datetime.utcnow()
        )
        db.add(english_session)
        
        # Update user stats
        current_user.total_english_sessions += 1
        db.commit()
        
        logger.info("english_session_started user_id=%s session_id=%s topic=%s", 
                   current_user.id, session_id, topic)
        return {"status": "success", "session_id": session_id}
        
    except Exception as e:
        logger.error("english_start_session_error user_id=%s error=%s", current_user.id, str(e))
        raise HTTPException(status_code=500, detail="Failed to start session")


@router.post("/english/end-session")
async def end_english_session(
    session_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """End an English practice session and save results"""
    try:
        session_id = session_data.get("session_id")
        messages = session_data.get("messages", [])
        
        english_session = (
            db.query(EnglishSession)
            .filter(EnglishSession.session_id == session_id)
            .filter(EnglishSession.user_id == current_user.id)
            .first()
        )
        
        if not english_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Generate final report
        if messages:
            report = await generate_final_report(messages)
            if isinstance(report, dict):
                english_session.rating = report.get("overall_score", 50)
                english_session.technical_rating = report.get("technical_rating", 50)
                english_session.communication_rating = report.get("communication_rating", 50)
                english_session.feedback = report.get("brutal_feedback", "Session completed")
        
        # Update session record
        english_session.status = "completed"
        english_session.completed_at = datetime.utcnow()
        english_session.messages = messages
        
        db.commit()
        
        logger.info("english_session_completed user_id=%s session_id=%s rating=%s", 
                   current_user.id, session_id, english_session.rating)
        return {"status": "success", "message": "Session completed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("english_end_session_error user_id=%s error=%s", current_user.id, str(e))
        raise HTTPException(status_code=500, detail="Failed to end session")


@router.post("/english/abandon-session")
async def abandon_english_session(
    session_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark an English practice session as abandoned"""
    try:
        session_id = session_data.get("session_id")
        
        english_session = (
            db.query(EnglishSession)
            .filter(EnglishSession.session_id == session_id)
            .filter(EnglishSession.user_id == current_user.id)
            .first()
        )
        
        if not english_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Update session record
        english_session.status = "abandoned"
        english_session.abandoned_at = datetime.utcnow()
        
        db.commit()
        
        logger.info("english_session_abandoned user_id=%s session_id=%s", current_user.id, session_id)
        return {"status": "success", "message": "Session marked as abandoned"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("english_abandon_session_error user_id=%s error=%s", current_user.id, str(e))
        raise HTTPException(status_code=500, detail="Failed to abandon session")


@router.get("/english/stats/{user_id}")
async def get_english_stats(
    user_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    """Get English practice statistics for a user"""
    try:
        # Get all English sessions for the user
        english_sessions = db.query(EnglishSession).filter(EnglishSession.user_id == user_id).all()
        
        total_attempted = len(english_sessions)
        total_completed = len([s for s in english_sessions if s.status == "completed"])
        
        if total_completed == 0:
            return {
                "total_attempted": total_attempted,
                "avg_fluency_score": 0,
                "weak_areas": []
            }
        
        # Calculate average fluency score (using communication_rating as proxy)
        fluency_scores = [s.communication_rating for s in english_sessions if s.status == "completed" and s.communication_rating]
        avg_fluency_score = sum(fluency_scores) / len(fluency_scores) if fluency_scores else 0
        
        # Extract weak areas from feedback
        weak_areas = []
        for session in english_sessions:
            if session.status == "completed" and session.feedback:
                feedback = session.feedback.lower()
                if "grammar" in feedback or "syntax" in feedback:
                    weak_areas.append("Grammar")
                if "vocabulary" in feedback or "word choice" in feedback:
                    weak_areas.append("Vocabulary")
                if "fluency" in feedback or "speaking" in feedback:
                    weak_areas.append("Fluency")
                if "pronunciation" in feedback:
                    weak_areas.append("Pronunciation")
                if "coherence" in feedback or "structure" in feedback:
                    weak_areas.append("Coherence")
        
        # Remove duplicates and get unique weak areas
        weak_areas = list(set(weak_areas))
        
        return {
            "total_attempted": total_attempted,
            "avg_fluency_score": round(avg_fluency_score, 2),
            "weak_areas": weak_areas
        }
        
    except Exception as e:
        logger.error("english_stats_error user_id=%s error=%s", user_id, str(e))
        raise HTTPException(status_code=500, detail="Failed to get English stats")
