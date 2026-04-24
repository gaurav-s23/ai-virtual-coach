from __future__ import annotations

import os
import re
import uuid
import logging
import tempfile
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from datetime import datetime

from models import User, Interview
from database import get_db
from core.security import get_current_user
from core.rate_limit import enforce_rate_limit
from services.llm_service import generate_chat_feedback, generate_initial_interview, generate_pivot_deepdives
from services.answer_verifier import verify_answer_relevance
from services.scoring_service import score_answer_quality
from services.audio_features import extract_audio_features
from services.rag_service import extract_resume_brief, get_rag_status, queue_resume_embedding
from services.interview_service import (
    append_transcript_turn,
    build_welcome_message,
    create_interview_session,
    interview_payload,
)
from services.discussion_service import process_discussion_first_interview
from services.confidence_service import analyze_confidence
from services.llm_client import LLMClient
from utils.sse import SSEEvent, StreamingResponse
from routes.schemas import ChatRequest, ChatResponse, PivotRequest, PivotResponse, StartInterviewResponse

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
    current_user: User = Depends(get_current_user),
):
    # Rate limiting for interview creation (resource-intensive)
    enforce_rate_limit(key=f"start_interview:{current_user.id}", max_requests=3, window_seconds=300)  # 3 interviews per 5 minutes
    
    # Validate form fields with comprehensive checks
    if not name or len(name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters long")
    if len(name) > 100:
        raise HTTPException(status_code=400, detail="Name is too long (max 100 characters)")
    
    # Check for potentially malicious content in name
    if any(char in name for char in ['<', '>', '&', '"', "'", '/', '\\', '|', '?', '*']):
        raise HTTPException(status_code=400, detail="Name contains invalid characters")
    
    # Validate role field
    valid_roles = ["Software Engineer", "Data Scientist", "Product Manager", "Designer", "DevOps Engineer", "QA Engineer", "Backend Developer", "Frontend Developer", "Full Stack Developer"]
    if not role or role.strip() == "":
        raise HTTPException(status_code=400, detail="Role is required")
    if len(role) > 50:
        raise HTTPException(status_code=400, detail="Role is too long (max 50 characters)")
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    
    # Validate job description field
    if jd and len(jd) > 10000:  # 10KB limit for job description
        raise HTTPException(status_code=400, detail="Job description is too long (max 10000 characters)")
    
    # Check for potentially malicious content in job description
    if jd and any(char in jd for char in ['<script', 'javascript:', 'vbscript:', 'onload=', 'onerror=']):
        raise HTTPException(status_code=400, detail="Job description contains potentially malicious content")
    
    content = await resume.read()
    if not content or len(content) < 50:
        raise HTTPException(status_code=400, detail="Resume file is too small or empty")
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Resume file is too large (max 8MB)")
    
    # Validate file type - only accept PDF files
    if resume.filename and not resume.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Additional validation using magic bytes for file type detection
    import magic
    try:
        file_type = magic.from_buffer(content)
        if not file_type or 'pdf' not in file_type.lower():
            raise HTTPException(status_code=400, detail="Invalid file type")
    except Exception:
        # Fallback to filename check if magic detection fails
        pass

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


@router.post("/interview/chat")
async def interview_chat(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(key=f"chat:{current_user.id}", max_requests=40, window_seconds=60)
    if not data.session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")
    session_id = data.session_id
    interview = (
        db.query(Interview)
        .filter(Interview.session_id == session_id)
        .filter(Interview.user_id == current_user.id)
        .first()
    )
    if not interview:
        raise HTTPException(status_code=404, detail="Session expired")

    # Get existing discussion state from interview metadata
    discussion_state = None
    if interview.transcript and len(interview.transcript) > 0:
        try:
            # Try to get discussion state from the last transcript entry
            last_entry = interview.transcript[-1]
            if isinstance(last_entry, dict) and "discussion_state" in last_entry:
                discussion_state = last_entry["discussion_state"]
        except Exception:
            discussion_state = None

    async def interview_chat_stream():
        try:
            # Use unified LLM client for streaming feedback
            llm_client = LLMClient()
            
            # Build context for the interview feedback
            context = data.context or ""
            resume_brief = ""
            try:
                resume_brief = extract_resume_brief(current_user.id) or ""
            except Exception:
                resume_brief = ""
            
            # Create streaming prompt for interview feedback
            feedback_prompt = f"""
            You are an expert interviewer providing real-time feedback for a candidate's response.
            
            Question: {data.question}
            Candidate's Answer: {data.answer}
            Time Taken: {data.time_taken_seconds or 0} seconds
            
            Context: {context}
            Resume Brief: {resume_brief}
            
            Discussion State: {discussion_state}
            
            Provide constructive, professional feedback that:
            1. Evaluates the answer quality
            2. Suggests improvements
            3. Maintains encouraging tone
            4. Is concise (2-3 sentences max)
            
            Return only the feedback text.
            """
            
            # Calculate dynamic confidence score based on answer quality
            answer_length = len(data.answer or "")
            keyword_quality = 0
            quality_keywords = ["excellent", "good", "clear", "detailed", "specific"]
            for keyword in quality_keywords:
                if keyword in (data.answer or "").lower():
                    keyword_quality += 10
            confidence_score = min(95, max(50, 50 + (answer_length // 20) + keyword_quality))
            
            async for chunk in llm_client.generate_stream(
                prompt=feedback_prompt,
                model_type="high_reasoning",  # Use high-reasoning model for interviews
                temperature=0.3
            ):
                if chunk.type == "content":
                    yield SSEEvent("content", {"chunk": chunk.content})
                elif chunk.type == "complete":
                    # Calculate confidence score based on answer quality
                    try:
                        confidence_score = await score_answer_quality(data.answer, data.question)
                    except Exception:
                        confidence_score = 75  # Default if scoring fails
                    
                    # Update transcript with streaming feedback
                    try:
                        await append_transcript_turn(
                            db, session_id, current_user.id, data.question, data.answer, chunk.content
                        )
                    except (KeyError, IndexError, ValueError) as e:
                        logger.warning(f"Failed to append transcript turn: {e}")
                    except Exception as e:
                        logger.error(f"Unexpected error in transcript update: {e}")
                        raise HTTPException(status_code=500, detail="Failed to update transcript")
                    
                    # Send complete event with feedback and confidence
                    yield SSEEvent("complete", {
                        "feedback": chunk.content,
                        "confidence_score": confidence_score
                    })
                    break
                elif chunk.type == "error":
                    yield SSEEvent("error", {"error": chunk.content})
                    break
                    
        except Exception as e:
            logger.error("Error in interview chat streaming: %s", str(e))
            yield SSEEvent("error", {"error": "Failed to process interview response"})
    
    return StreamingResponse(interview_chat_stream())
    
     
                        

@router.get("/interview/{session_id}/history")
async def interview_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    interview = (
        db.query(Interview)
        .filter(Interview.session_id == session_id)
        .filter(Interview.user_id == current_user.id)
        .first()
    )
    if not interview:
        raise HTTPException(status_code=404, detail="Session expired")
    return {"session_id": session_id, "transcript": interview.transcript or []}


@router.get("/interview/rag-status")
async def interview_rag_status(current_user: User = Depends(get_current_user)):
    return get_rag_status(current_user.id)


@router.post("/interview/pivot", response_model=PivotResponse)
async def interview_pivot(data: PivotRequest, _current_user: User = Depends(get_current_user)):
    enforce_rate_limit(key=f"pivot:{_current_user.id}", max_requests=10, window_seconds=60)
    result = await generate_pivot_deepdives(data.history, data.role, data.context)
    logger.info("interview_pivot user_id=%s role=%s", _current_user.id, data.role)
    if not result:
        raise HTTPException(status_code=500, detail="Processing failed")
    return result


@router.post("/interview/analyze-audio")
async def analyze_audio(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    suffix = os.path.splitext(audio.filename or "")[-1] or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        file_path = tmp.name
        tmp.write(await audio.read())
    try:
        return extract_audio_features(file_path)
    finally:
        os.unlink(file_path)


@router.post("/interview/end-session")
async def end_interview_session(
    session_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        session_id = session_data.get("session_id")
        interview = (
            db.query(Interview)
            .filter(Interview.session_id == session_id)
            .filter(Interview.user_id == current_user.id)
            .first()
        )
        
        if not interview:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Update interview record
        interview.status = "completed"
        interview.overall_score = session_data.get("performance_log", {}).get("overall_score", 0)
        interview.completed_at = datetime.utcnow()
        
        # Update user stats
        current_user.total_interviews += 1
        db.commit()
        
        logger.info("interview_session_completed user_id=%s session_id=%s score=%s", 
                   current_user.id, session_id, interview.overall_score)
        return {"status": "success", "message": "Interview session completed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("interview_end_session_error user_id=%s error=%s", current_user.id, str(e))
        raise HTTPException(status_code=500, detail="Failed to end interview session")


@router.post("/interview/abandon-session")
async def abandon_interview_session(
    session_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        session_id = session_data.get("session_id")
        interview = (
            db.query(Interview)
            .filter(Interview.session_id == session_id)
            .filter(Interview.user_id == current_user.id)
            .first()
        )
        
        if not interview:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Update interview record
        interview.status = "abandoned"
        interview.abandoned_at = datetime.utcnow()
        db.commit()
        
        logger.info("interview_session_abandoned user_id=%s session_id=%s", current_user.id, session_id)
        return {"status": "success", "message": "Interview session marked as abandoned"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("interview_abandon_session_error user_id=%s error=%s", current_user.id, str(e))
        raise HTTPException(status_code=500, detail="Failed to abandon interview session")


@router.get("/interview/stats/{user_id}")
async def get_interview_stats(
    user_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    try:
        # Get all interviews for the user
        interviews = db.query(Interview).filter(Interview.user_id == user_id).all()
        
        total_attempted = len(interviews)
        total_completed = len([i for i in interviews if i.status == "completed"])
        
        if total_completed == 0:
            return {
                "total_attempted": total_attempted,
                "avg_score": 0,
                "weak_areas": [],
                "fluency_score": 0
            }
        
        # Calculate average score
        avg_score = sum(i.overall_score for i in interviews if i.status == "completed" and i.overall_score) / total_completed
        
        # Extract weak areas from interview transcripts
        weak_areas = []
        fluency_scores = []
        
        for interview in interviews:
            if interview.status == "completed" and interview.transcript:
                # Analyze transcript for weak areas and fluency
                for entry in interview.transcript:
                    if isinstance(entry, dict) and "assistant_reply" in entry:
                        reply = entry["assistant_reply"].lower()
                        if "weak" in reply or "improve" in reply or "work on" in reply:
                            # Extract weak areas from feedback
                            if "communication" in reply:
                                weak_areas.append("Communication")
                            if "technical" in reply or "coding" in reply:
                                weak_areas.append("Technical Skills")
                            if "confidence" in reply:
                                weak_areas.append("Confidence")
                            if "fluency" in reply:
                                weak_areas.append("Fluency")
                        
                        # Extract fluency scores if available
                        if "fluency" in reply or "speaking" in reply:
                            # Simple fluency estimation based on feedback
                            if "good" in reply or "excellent" in reply:
                                fluency_scores.append(80)
                            elif "average" in reply or "okay" in reply:
                                fluency_scores.append(60)
                            else:
                                fluency_scores.append(40)
        
        # Remove duplicates and get unique weak areas
        weak_areas = list(set(weak_areas))
        
        # Calculate average fluency score
        fluency_score = sum(fluency_scores) / len(fluency_scores) if fluency_scores else 70
        
        return {
            "total_attempted": total_attempted,
            "avg_score": round(avg_score, 2),
            "weak_areas": weak_areas,
            "fluency_score": round(fluency_score, 2)
        }
        
    except Exception as e:
        logger.error("interview_stats_error user_id=%s error=%s", user_id, str(e))
        raise HTTPException(status_code=500, detail="Failed to get interview stats")


@router.post("/interview/abandon-session")
async def abandon_session(
    session_id: str,
    abandoned_at: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark an interview session as abandoned."""
    # Rate limiting for session abandonment
    enforce_rate_limit(key=f"abandon_session:{current_user.id}", max_requests=10, window_seconds=60)  # 10 abandons per minute
    try:
        # Parse the abandoned_at timestamp
        from datetime import datetime
        abandoned_timestamp = datetime.fromisoformat(abandoned_at.replace('Z', '+00:00'))
        
        # Find the interview session
        interview = (
            db.query(Interview)
            .filter(Interview.session_id == session_id)
            .filter(Interview.user_id == current_user.id)
            .first()
        )
        
        if not interview:
            logger.warning("interview_abandon_not_found user_id=%s session_id=%s", current_user.id, session_id)
            raise HTTPException(status_code=404, detail="Interview session not found")
        
        # Update the interview status to abandoned
        interview.status = "abandoned"
        # Note: We don't have abandoned_at field in Interview model, but we could add it in the future
        # For now, we'll update the status and log the abandonment
        
        db.commit()
        
        logger.info("interview_abandoned user_id=%s session_id=%s abandoned_at=%s", 
                   current_user.id, session_id, abandoned_timestamp)
        
        return {"message": "Session marked as abandoned", "session_id": session_id}
        
    except ValueError as e:
        logger.error("interview_abandon_invalid_timestamp user_id=%s session_id=%s error=%s", 
                    current_user.id, session_id, str(e))
        raise HTTPException(status_code=400, detail="Invalid timestamp format")
    except Exception as e:
        logger.error("interview_abandon_error user_id=%s session_id=%s error=%s", 
                    current_user.id, session_id, str(e))
        raise HTTPException(status_code=500, detail="Failed to abandon session")
