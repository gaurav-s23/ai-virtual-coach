from __future__ import annotations

import os
import io
import logging

import PyPDF2
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

try:
    from ..database import get_db
    from ..core.security import get_current_user
    from ..core.rate_limit import enforce_rate_limit
    from ..services.mock_service import generate_new_mock, get_current_mock
    from ..services.llm_service import generate_english_questions, generate_final_report
    from .schemas import (
        EnglishQuestionsRequest,
        EnglishQuestionsResponse,
        EnglishReportRequest,
        FinalReportResponse,
        QuizQuestion,
        QuizRequest,
    )
except ImportError:
    from database import get_db  # type: ignore
    from core.security import get_current_user  # type: ignore
    from core.rate_limit import enforce_rate_limit  # type: ignore
    from services.mock_service import generate_new_mock, get_current_mock  # type: ignore
    from services.llm_service import generate_english_questions, generate_final_report  # type: ignore
    from routes.schemas import (  # type: ignore
        EnglishQuestionsRequest,
        EnglishQuestionsResponse,
        EnglishReportRequest,
        FinalReportResponse,
        QuizQuestion,
        QuizRequest,
    )

router = APIRouter(prefix="/api", tags=["Mock and English"])
logger = logging.getLogger("ai_virtual_coach.routes.mock")


def extract_text_from_local_pdf(file_path: str) -> str:
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(io.BytesIO(f.read()))
            return " ".join([page.extract_text() for page in reader.pages if page.extract_text()]).strip()
    except Exception:
        return ""


@router.post("/generate-quiz", response_model=list[QuizQuestion])
async def generate_quiz_route(data: QuizRequest, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    enforce_rate_limit(key=f"quiz:{_user.id}", max_requests=15, window_seconds=60)
    current = get_current_mock(db)
    if current is None or data.force_new:
        pdf_path = f"./data/{data.category.lower()}.pdf"
        context = extract_text_from_local_pdf(pdf_path) if os.path.exists(pdf_path) else ""
        current = await generate_new_mock(db, category=data.category, context=context)
        logger.info("mock_generated user_id=%s category=%s force_new=%s", _user.id, data.category, data.force_new)
    else:
        logger.info("mock_reused user_id=%s category=%s", _user.id, data.category)
    return current.questions or []


@router.get("/english/topic")
async def get_english_topic(_user=Depends(get_current_user)):
    return {"topic": "Modern Leadership Ethics"}


@router.post("/english/questions", response_model=EnglishQuestionsResponse)
async def get_english_questions_route(data: EnglishQuestionsRequest, _user=Depends(get_current_user)):
    questions = await generate_english_questions(data.topic)
    return {"questions": questions}


@router.post("/english/report", response_model=FinalReportResponse)
async def english_report(data: EnglishReportRequest, _user=Depends(get_current_user)):
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
