from __future__ import annotations

import os
import io
import logging

import PyPDF2
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

# Configure logger
logger = logging.getLogger(__name__)

try:
    from models import User, MockSession
    from database import get_db
    from core.security import get_current_user
    from core.rate_limit import enforce_rate_limit
    from services.mock_service import generate_new_mock, get_current_mock
    from services.llm_service import generate_english_questions, generate_final_report
    from services.llm_client import LLMClient
    from utils.sse import SSEEvent, StreamingResponse
    from routes.schemas import (
        EnglishQuestionsRequest,
        EnglishQuestionsResponse,
        EnglishReportRequest,
        FinalReportResponse,
        QuizQuestion,
        QuizRequest,
    )
except ImportError as e:
    logger.error(f"Import error in mock.py: {e}")
    # Fallback imports for development
    try:
        import models
        from database import get_db
        from core.security import get_current_user
        from core.rate_limit import enforce_rate_limit
        from services.mock_service import generate_new_mock, get_current_mock
        from services.llm_service import generate_english_questions, generate_final_report
        from services.llm_client import LLMClient
        from utils.sse import SSEEvent, StreamingResponse
        from routes.schemas import (
            EnglishQuestionsRequest,
            EnglishQuestionsResponse,
            EnglishReportRequest,
            FinalReportResponse,
            QuizQuestion,
            QuizRequest,
        )
    except ImportError as fallback_error:
        logger.error(f"Fallback import error in mock.py: {fallback_error}")
        raise SystemExit(f"Failed to import required modules in mock.py: {fallback_error}")

router = APIRouter(prefix="/api", tags=["Mock and English"])
logger = logging.getLogger("ai_virtual_coach.routes.mock")


def extract_text_from_local_pdf(file_path: str) -> str:
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(io.BytesIO(f.read()))
            return " ".join([page.extract_text() for page in reader.pages if page.extract_text()]).strip()
    except Exception:
        return ""


@router.post("/generate-quiz")
async def generate_quiz_route(data: QuizRequest, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    enforce_rate_limit(key=f"quiz:{_user.id}", max_requests=15, window_seconds=60)
    
    async def generate_quiz_stream():
        try:
            # Check if we have cached quiz
            current = get_current_mock(db)
            if current is None or data.force_new:
                pdf_path = f"./data/{data.category.lower()}.pdf"
                context = extract_text_from_local_pdf(pdf_path) if os.path.exists(pdf_path) else ""
                
                # Use unified LLM client for streaming generation
                llm_client = LLMClient()
                
                # Generate quiz using streaming
                quiz_prompt = f"""
                Generate 10 multiple choice questions for {data.category} assessment.
                
                Context: {context[:2000] if context else "No additional context provided"}
                
                Requirements:
                - Each question should have 4 options (A, B, C, D)
                - Include the correct answer
                - Questions should be progressively challenging
                - Format each question as JSON with fields: question, options (array), answer
                
                Return the questions as a JSON array.
                """
                
                questions = []
                async for chunk in llm_client.generate_stream(
                    prompt=quiz_prompt,
                    model_type="high_reasoning",  # Use high-reasoning model for mock tests
                    temperature=0.7
                ):
                    if chunk.type == "content":
                        yield SSEEvent("content", {"chunk": chunk.content})
                    elif chunk.type == "complete":
                        # Parse the generated questions
                        try:
                            import json
                            generated_questions = json.loads(chunk.content)
                            if isinstance(generated_questions, list):
                                questions = generated_questions[:10]  # Limit to 10 questions
                                
                                # Save to database
                                current = await generate_new_mock(db, category=data.category, context=context)
                                if current and hasattr(current, 'questions'):
                                    current.questions = questions
                                    db.commit()
                                
                                logger.info("mock_generated user_id=%s category=%s force_new=%s", _user.id, data.category, data.force_new)
                                
                                # Send complete event with session_id
                                yield SSEEvent("complete", {
                                    "questions": questions,
                                    "session_id": f"mock_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                                })
                        except json.JSONDecodeError:
                            logger.error("Failed to parse generated quiz questions")
                            yield SSEEvent("error", {"error": "Failed to generate valid quiz questions"})
                        break
                    elif chunk.type == "error":
                        yield SSEEvent("error", {"error": chunk.content})
                        break
            else:
                # Return cached quiz
                logger.info("mock_reused user_id=%s category=%s", _user.id, data.category)
                yield SSEEvent("complete", {
                    "questions": current.questions or [],
                    "session_id": f"mock_cached_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                })
                
        except Exception as e:
            logger.error("Error generating quiz: %s", str(e))
            yield SSEEvent("error", {"error": "Failed to generate quiz"})
    
    return StreamingResponse(generate_quiz_stream())


@router.get("/english/topic")
async def get_english_topic(_user=Depends(get_current_user)):
    return {"topic": "Modern Leadership Ethics"}


@router.post("/english/questions", response_model=EnglishQuestionsResponse)
async def get_english_questions_route(data: EnglishQuestionsRequest, _user=Depends(get_current_user)):
    # Rate limit English questions generation to prevent abuse
    enforce_rate_limit(key=f"english:{_user.id}", max_requests=10, window_seconds=60)
    
    questions = await generate_english_questions(data.topic)
    return {"questions": questions}


@router.post("/english/report", response_model=FinalReportResponse)
async def english_report(data: EnglishReportRequest, _user=Depends(get_current_user)):
    # Rate limit English report generation to prevent abuse
    enforce_rate_limit(key=f"english_report:{_user.id}", max_requests=5, window_seconds=60)
    
    result = await generate_final_report(data.history)
    if not isinstance(result, dict):
        raise HTTPException(status_code=500, detail="Server error, try again")
    return {
        "overall_score": int(result.get("overall_score") or 50),
        "technical_rating": int(result.get("technical_rating") or 50),
        "communication_rating": int(result.get("communication_rating") or 50),
        "brutal_feedback": result.get("brutal_feedback") or "Session completed. Keep practicing.",
        "ready_for_senior_role": bool(result.get("ready_for_senior_role") or False),
    }


@router.post("/mock/end-session")
async def end_mock_session(
    session_data: dict,
    db: Session = Depends(get_db),
    current_user: "models.User" = Depends(get_current_user)
):
    try:
        # Create or update mock test record
        mock_test = models.MockTest(
            user_id=current_user.id,
            session_id=session_data.get("session_id"),
            category=session_data.get("category"),
            score=session_data.get("score", 0),
            section_scores=session_data.get("section_scores", {}),
            status="completed",
            completed_at=datetime.utcnow()
        )
        db.add(mock_test)
        
        # Update user stats
        current_user.total_mocks += 1
        db.commit()
        
        logger.info("mock_session_completed user_id=%s score=%s", current_user.id, session_data.get("score", 0))
        return {"status": "success", "message": "Session completed successfully"}
        
    except Exception as e:
        logger.error("mock_end_session_error user_id=%s error=%s", current_user.id, str(e))
        raise HTTPException(status_code=500, detail="Failed to end session")


@router.post("/mock/abandon-session")
async def abandon_mock_session(
    session_data: dict,
    db: Session = Depends(get_db),
    current_user: "models.User" = Depends(get_current_user)
):
    try:
        # Create abandoned session record
        mock_test = models.MockTest(
            user_id=current_user.id,
            session_id=session_data.get("session_id"),
            category=session_data.get("category"),
            score=0,
            status="abandoned",
            abandoned_at=datetime.utcnow()
        )
        db.add(mock_test)
        db.commit()
        
        logger.info("mock_session_abandoned user_id=%s session_id=%s", current_user.id, session_data.get("session_id"))
        return {"status": "success", "message": "Session marked as abandoned"}
        
    except Exception as e:
        logger.error("mock_abandon_session_error user_id=%s error=%s", current_user.id, str(e))
        raise HTTPException(status_code=500, detail="Failed to abandon session")


@router.get("/mock/stats/{user_id}")
async def get_mock_stats(
    user_id: int,
    db: Session = Depends(get_db),
    _current_user: "models.User" = Depends(get_current_user)
):
    try:
        # Get all mock tests for the user
        mock_tests = db.query(models.MockTest).filter(models.MockTest.user_id == user_id).all()
        
        total_attempted = len(mock_tests)
        total_completed = len([m for m in mock_tests if m.status == "completed"])
        
        if total_completed == 0:
            return {
                "total_attempted": total_attempted,
                "total_completed": total_completed,
                "avg_score": 0,
                "section_scores": {"quant": 0, "verbal": 0, "reasoning": 0, "coding": 0},
                "weak_areas": []
            }
        
        # Calculate average score
        avg_score = sum(m.score for m in mock_tests if m.status == "completed") / total_completed
        
        # Calculate section scores
        section_totals = {"quant": [], "verbal": [], "reasoning": [], "coding": []}
        for test in mock_tests:
            if test.status == "completed" and test.section_scores:
                for section, score in test.section_scores.items():
                    if section.lower() in section_totals:
                        section_totals[section.lower()].append(score)
        
        section_scores = {}
        for section, scores in section_totals.items():
            section_scores[section] = sum(scores) / len(scores) if scores else 0
        
        # Identify weak areas (sections with avg score < 60)
        weak_areas = [section for section, score in section_scores.items() if score < 60]
        
        return {
            "total_attempted": total_attempted,
            "total_completed": total_completed,
            "avg_score": round(avg_score, 2),
            "section_scores": section_scores,
            "weak_areas": weak_areas
        }
        
    except Exception as e:
        logger.error("mock_stats_error user_id=%s error=%s", user_id, str(e))
        raise HTTPException(status_code=500, detail="Failed to get mock stats")
