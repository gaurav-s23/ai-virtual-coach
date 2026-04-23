from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

try:
    import models
except ImportError as e:
    logger.error(f"Import error in interview_service.py: {e}")
    # Fallback imports for development
    try:
        import models
    except ImportError as fallback_error:
        logger.error(f"Fallback import error in interview_service.py: {fallback_error}")
        raise SystemExit(f"Failed to import required modules in interview_service.py: {fallback_error}")


def build_welcome_message(name: str) -> str:
    clean_name = (name or "Candidate").strip() or "Candidate"
    return (
        f"Welcome {clean_name}, your interview is starting. "
        "Rules: No cheating. Answer clearly. Think before speaking."
    )


def create_interview_session(
    *,
    db: Session,
    user_id: int,
    name: str,
    role: str,
    resume_context: str,
    session_id: str,
) -> "models.Interview":
    interview = models.Interview(
        user_id=user_id,
        session_id=session_id,
        candidate_name=(name or "Candidate").strip()[:120],
        role=role,
        status="starting",
        current_question=0,
        resume_context=resume_context[:2000],
        transcript=[],
        had_pivot=True,
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return interview


def append_transcript_turn(db: Session, interview: "models.Interview", user_answer: str, assistant_reply: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    transcript = interview.transcript or []
    transcript.append({"role": "user", "content": user_answer, "timestamp": now})
    transcript.append({"role": "assistant", "content": assistant_reply, "timestamp": now})
    interview.transcript = transcript
    interview.current_question = int(interview.current_question or 0) + 1
    interview.status = "in_progress"
    db.add(interview)
    db.commit()


def interview_payload(
    *,
    intro: str,
    skill_questions: list[str],
    project_questions: list[str],
    followup_questions: list[str],
    context: str,
    session_id: str,
    rag_status: str,
    candidate_name: str,
) -> dict[str, Any]:
    return {
        "status": "success",
        "intro": intro,
        "questions": skill_questions,
        "skill_questions": skill_questions,
        "project_questions": project_questions,
        "followup_questions": followup_questions,
        "context": context[:1500],
        "session_id": session_id,
        "rag_status": rag_status,
        "candidate_name": candidate_name,
        "interview_status": "starting",
        "countdown_seconds": 8,
    }
