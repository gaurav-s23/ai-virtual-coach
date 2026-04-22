from __future__ import annotations

import asyncio
import io
import logging
from dataclasses import dataclass

import PyPDF2

try:
    from .. import models
    from ..database import SessionLocal
    from ..rag.store import upsert_resume
except ImportError:
    import models  # type: ignore
    from database import SessionLocal  # type: ignore
    from rag.store import upsert_resume  # type: ignore

logger = logging.getLogger("ai_virtual_coach.services.rag")
_QUEUE: asyncio.Queue["EmbeddingTask"] | None = None
_WORKER_STARTED = False


@dataclass
class EmbeddingTask:
    user_id: int
    file_bytes: bytes
    filename: str


def extract_resume_brief(file_bytes: bytes) -> str:
    # Validate file size (max 10MB)
    if len(file_bytes) > 10 * 1024 * 1024:
        raise ValueError("File too large. Maximum size is 10MB.")
    
    # Validate file type by checking PDF header
    if len(file_bytes) < 4 or not file_bytes.startswith(b'%PDF'):
        raise ValueError("Invalid file format. Only PDF files are supported.")
    
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        # Limit number of pages to prevent processing issues
        if len(reader.pages) > 50:
            raise ValueError("File has too many pages. Maximum is 50 pages.")
        
        text = "\n".join([p.extract_text() or "" for p in reader.pages]).strip()
    except Exception as e:
        # Log the specific error for debugging
        logger.error(f"PDF processing error: {str(e)}")
        raise ValueError(f"Failed to process PDF: {str(e)}")
    
    if not text:
        raise ValueError("PDF appears to be empty or contains no extractable text.")
    
    # Validate extracted text length
    if len(text) < 50:
        raise ValueError("PDF contains too little text to be useful.")
    
    return text

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    name = lines[0][:120] if lines else "Candidate"
    skills = []
    experience = []
    project = []
    for line in lines:
        lower = line.lower()
        if any(k in lower for k in ("skill", "technology", "framework", "tool")):
            skills.append(line)
        if any(k in lower for k in ("experience", "engineer", "developer", "worked")):
            experience.append(line)
        if "project" in lower and len(project) < 3:
            project.append(line)
    exp_or_project = experience[:3] if experience else project[:3]
    return f"Name: {name}\nSkills: {' | '.join(skills[:6])}\nExperience: {' | '.join(exp_or_project)}"


def set_rag_status(user_id: int, status: str, message: str, chunks: int = 0) -> None:
    db = SessionLocal()
    try:
        row = db.query(models.RagStatus).filter(models.RagStatus.user_id == user_id).first()
        if row is None:
            row = models.RagStatus(user_id=user_id, status=status, message=message, chunks=chunks)
            db.add(row)
        else:
            row.status = status
            row.message = message
            row.chunks = chunks
            db.add(row)
        db.commit()
    finally:
        db.close()


def get_rag_status(user_id: int) -> dict:
    db = SessionLocal()
    try:
        row = db.query(models.RagStatus).filter(models.RagStatus.user_id == user_id).first()
        if not row:
            return {"status": "processing", "message": "Embedding not initialized", "chunks": 0}
        return {"status": row.status, "message": row.message, "chunks": row.chunks}
    finally:
        db.close()


async def queue_resume_embedding(user_id: int, file_bytes: bytes, filename: str) -> None:
    set_rag_status(user_id=user_id, status="processing", message="Resume embedding in progress", chunks=0)
    task = EmbeddingTask(user_id=user_id, file_bytes=file_bytes, filename=filename)
    if _QUEUE is not None:
        await _QUEUE.put(task)
        return

    asyncio.create_task(_process_embedding(task))


async def _process_embedding(task: EmbeddingTask) -> None:
    attempts = 3
    for attempt in range(attempts):
        try:
            chunks = await asyncio.to_thread(
                upsert_resume,
                user_id=task.user_id,
                file_bytes=task.file_bytes,
                filename=task.filename,
            )
            set_rag_status(
                user_id=task.user_id,
                status="ready",
                message="Resume embedding complete",
                chunks=max(0, int(chunks or 0)),
            )
            logger.info("rag_embedding_completed user_id=%s chunks=%s", task.user_id, chunks)
            return
        except Exception as exc:
            logger.exception("resume_embedding_failed user_id=%s attempt=%s error=%s", task.user_id, attempt + 1, str(exc))
            if attempt < attempts - 1:
                await asyncio.sleep(1.0 * (attempt + 1))
    set_rag_status(
        user_id=task.user_id,
        status="failed",
        message="Processing failed",
        chunks=0,
    )


async def _worker_loop(worker_id: int) -> None:
    global _QUEUE
    if _QUEUE is None:
        return
    while True:
        task = await _QUEUE.get()
        try:
            await _process_embedding(task)
        finally:
            _QUEUE.task_done()


def start_rag_workers(worker_count: int = 1) -> None:
    global _QUEUE, _WORKER_STARTED
    if _WORKER_STARTED:
        return
    _QUEUE = asyncio.Queue(maxsize=200)
    for worker_id in range(max(1, worker_count)):
        asyncio.create_task(_worker_loop(worker_id))
    _WORKER_STARTED = True
