from __future__ import annotations

import asyncio
import io
import logging
from dataclasses import dataclass

import PyPDF2

logger = logging.getLogger("ai_virtual_coach.services.rag")

try:
    import models
    from database import SessionLocal
    from rag.store import upsert_resume
except ImportError as e:
    logger.error(f"Import error in rag_service.py: {e}")
    # Fallback imports for development
    try:
        import models
        from database import SessionLocal
        from rag.store import upsert_resume
    except ImportError as fallback_error:
        logger.error(f"Fallback import error in rag_service.py: {fallback_error}")
        raise SystemExit(f"Failed to import required modules in rag_service.py: {fallback_error}")

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
    
    # Enhanced PDF header validation
    if len(file_bytes) < 4:
        raise ValueError("File too small to be a valid PDF.")
    
    # Check for PDF signature with multiple variants
    pdf_signatures = [b'%PDF-', b'%PDF']
    is_valid_pdf = any(file_bytes.startswith(sig) for sig in pdf_signatures)
    
    if not is_valid_pdf:
        raise ValueError("Invalid file format. Only PDF files are supported.")
    
    # Additional security checks
    try:
        # Check for PDF version in header
        header_text = file_bytes[:20].decode('ascii', errors='ignore')
        if not any(version in header_text for version in ['1.0', '1.1', '1.2', '1.3', '1.4', '1.5', '1.6', '1.7', '2.0']):
            logger.warning("PDF version not recognized, proceeding with caution")
        
        # Check for potential malicious content patterns
        suspicious_patterns = [
            b'JavaScript',
            b'/JS',
            b'/JavaScript',
            b'/OpenAction',
            b'/AA',
            b'/Launch',
            b'/SubmitForm',
            b'/URI',
            b'/GoToR',
            b'/GoToE'
        ]
        
        for pattern in suspicious_patterns:
            if pattern in file_bytes[:1024]:  # Check first 1KB for suspicious patterns
                logger.warning(f"Suspicious PDF pattern detected: {pattern.decode('ascii', errors='ignore')}")
                # We'll continue but log the warning
        
        # Validate PDF structure
        if not b'obj' in file_bytes or not b'endobj' in file_bytes:
            raise ValueError("Invalid PDF structure detected.")
            
    except UnicodeDecodeError:
        logger.warning("PDF header contains non-ASCII characters, proceeding with caution")
    
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        
        # Additional PDF validation
        if not hasattr(reader, 'pages') or len(reader.pages) == 0:
            raise ValueError("PDF contains no pages.")
            
        # Limit number of pages to prevent processing issues
        if len(reader.pages) > 50:
            raise ValueError("File has too many pages. Maximum is 50 pages.")
        
        # Check for encrypted PDFs
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported.")
        
        # Extract text with error handling for each page
        text_parts = []
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text_parts.append(page_text.strip())
                elif page_num == 0:  # First page should have content
                    logger.warning(f"Page {page_num + 1} contains no extractable text")
            except Exception as page_error:
                logger.warning(f"Failed to extract text from page {page_num + 1}: {page_error}")
                continue
        
        text = "\n".join(text_parts).strip()
        
    except PyPDF2.PdfReadError as e:
        logger.error(f"PDF read error: {str(e)}")
        raise ValueError(f"Invalid or corrupted PDF file: {str(e)}")
    except Exception as e:
        # Log the specific error for debugging
        logger.error(f"PDF processing error: {str(e)}")
        raise ValueError(f"Failed to process PDF: {str(e)}")
    
    if not text:
        raise ValueError("PDF appears to be empty or contains no extractable text.")
    
    # Basic content validation
    if len(text) < 50:  # Very short text might indicate a problem
        logger.warning("Extracted text is very short, PDF might be image-only or corrupted")
    
    # Check for reasonable character content (not just special characters)
    alphanumeric_chars = sum(1 for c in text if c.isalnum())
    if alphanumeric_chars < len(text) * 0.3:  # Less than 30% alphanumeric
        logger.warning("PDF contains mostly non-alphanumeric characters, might be image-based")
    
    # Validate extracted text length
    if len(text) < 50:
        raise ValueError("PDF contains too little text to be useful.")
    
    # Resume parsing logic - now reachable
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
