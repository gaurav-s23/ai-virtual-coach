from __future__ import annotations

import os
import re
import uuid
import logging
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

try:
    from .. import models
    from ..database import get_db
    from ..core.security import get_current_user
    from ..core.rate_limit import enforce_rate_limit
    from ..services.llm_service import generate_chat_feedback, generate_initial_interview, generate_pivot_deepdives
    from ..services.rag_service import extract_resume_brief, get_rag_status, queue_resume_embedding
    from ..services.interview_service import (
        append_transcript_turn,
        build_welcome_message,
        create_interview_session,
        interview_payload,
    )
    from .schemas import ChatRequest, ChatResponse, PivotRequest, PivotResponse, StartInterviewResponse
except ImportError:
    import models  # type: ignore
    from database import get_db  # type: ignore
    from core.security import get_current_user  # type: ignore
    from core.rate_limit import enforce_rate_limit  # type: ignore
    from services.llm_service import generate_chat_feedback, generate_initial_interview, generate_pivot_deepdives  # type: ignore
    from services.rag_service import extract_resume_brief, get_rag_status, queue_resume_embedding  # type: ignore
    from services.interview_service import (  # type: ignore
        append_transcript_turn,
        build_welcome_message,
        create_interview_session,
        interview_payload,
    )
    from routes.schemas import ChatRequest, ChatResponse, PivotRequest, PivotResponse, StartInterviewResponse  # type: ignore

router = APIRouter(prefix="/api", tags=["Interview"])
_FILENAME_SAFE_RE = re.compile(r"[^a-zA-Z0-9._-]+")
logger = logging.getLogger("ai_virtual_coach.routes.interview")


def sanitize_filename(name: str) -> str:
    base = os.path.basename(name or "resume.pdf")
    cleaned = _FILENAME_SAFE_RE.sub("_", base).strip("._")
    return cleaned[:120] or "resume.pdf"


@router.post("/start-interview", response_model=StartInterviewResponse, status_code=201)
async def start_interview(
    resume: UploadFile = File(...),
    name: str = Form("Candidate"),
    jd: str = Form(""),
    role: str = Form("Software Engineer"),
    db: Session = Depends(get_db),
    current_user: "models.User" = Depends(get_current_user),
):
    content = await resume.read()
    if not content or len(content) < 50:
        raise HTTPException(status_code=400, detail="Invalid input")
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Invalid input")

    safe_filename = sanitize_filename(resume.filename or "resume.pdf")
    logger.info("interview_start user_id=%s role=%s filename=%s", current_user.id, role, safe_filename)
    await queue_resume_embedding(user_id=current_user.id, file_bytes=content, filename=safe_filename)
    resume_text = extract_resume_brief(content)
    plan = await generate_initial_interview(resume_text, jd, role)
    session_id = str(uuid.uuid4())
    welcome = build_welcome_message(name)
    intro = f"{welcome}\n\n{plan.get('intro') or ''}".strip()
    create_interview_session(
        db=db,
        user_id=current_user.id,
        name=name,
        role=role,
        resume_context=resume_text,
        session_id=session_id,
    )

    return interview_payload(
        intro=intro,
        skill_questions=plan.get("skill_questions") or [],
        project_questions=plan.get("project_questions") or [],
        followup_questions=plan.get("followup_questions") or [],
        context=resume_text,
        session_id=session_id,
        rag_status="processing",
        candidate_name=(name or "Candidate").strip()[:120],
    )


@router.post("/interview/chat", response_model=ChatResponse)
async def interview_chat(
    data: ChatRequest,
    current_user: "models.User" = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(key=f"chat:{current_user.id}", max_requests=40, window_seconds=60)
    session_id = data.session_id or "default"
    interview = (
        db.query(models.Interview)
        .filter(models.Interview.session_id == session_id)
        .filter(models.Interview.user_id == current_user.id)
        .first()
    )
    if not interview:
        raise HTTPException(status_code=404, detail="Session expired")

    output, readiness_score = await generate_chat_feedback(
        question=data.question,
        answer=data.answer,
        context=data.context or interview.resume_context or "",
    )

    append_transcript_turn(db=db, interview=interview, user_answer=data.answer, assistant_reply=output)
    logger.info("interview_chat user_id=%s session_id=%s question_idx=%s", current_user.id, session_id, interview.current_question)
    return {"reply": output, "readiness_score": readiness_score, "state": interview.status}


@router.get("/interview/{session_id}/history")
async def interview_history(
    session_id: str,
    current_user: "models.User" = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    interview = (
        db.query(models.Interview)
        .filter(models.Interview.session_id == session_id)
        .filter(models.Interview.user_id == current_user.id)
        .first()
    )
    if not interview:
        raise HTTPException(status_code=404, detail="Session expired")
    return {"session_id": session_id, "transcript": interview.transcript or []}


@router.get("/interview/rag-status")
async def interview_rag_status(current_user: "models.User" = Depends(get_current_user)):
    return get_rag_status(current_user.id)


@router.post("/interview/pivot", response_model=PivotResponse)
async def interview_pivot(data: PivotRequest, _current_user: "models.User" = Depends(get_current_user)):
    enforce_rate_limit(key=f"pivot:{_current_user.id}", max_requests=10, window_seconds=60)
    result = await generate_pivot_deepdives(data.history, data.role, data.context)
    logger.info("interview_pivot user_id=%s role=%s", _current_user.id, data.role)
    if not result:
        raise HTTPException(status_code=500, detail="Processing failed")
    return result
