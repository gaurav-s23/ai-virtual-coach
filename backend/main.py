import os
import io
import traceback
import time
import uuid
import logging
import re
from typing import Any, List, Optional, Literal
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, Query, Request
from fastapi import status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
import PyPDF2
from pydantic import BaseModel

# Agentic RAG imports
try:
    from .rag.store import upsert_resume
    from .agent.session import session_manager
except ImportError:
    from rag.store import upsert_resume
    from agent.session import session_manager

# --- IMPORT FROM YOUR AI_ENGINE.PY ---
try:
    # When `backend` is used as a package (e.g. `python -m backend.main`)
    from .ai_engine import (
        generate_initial_interview,
        generate_pivot_deepdives,
        generate_neural_quiz,
        generate_final_report,
        call_llm,
        clean_json_response,
    )
except ImportError:
    # When running from within the `backend/` directory (e.g. `uvicorn main:app`)
    from ai_engine import (
        generate_initial_interview,
        generate_pivot_deepdives,
        generate_neural_quiz,
        generate_final_report,
        call_llm,
        clean_json_response,
    )

# Local database imports
try:
    from . import models
    from .database import engine, get_db
except ImportError:
    import models
    from database import engine, get_db
from dotenv import load_dotenv

load_dotenv()

try:
    from .auth.security import (
        get_current_user,
        get_rate_limit_key,
        hash_password,
        validate_password_length,
        verify_password,
        issue_token_pair,
        rotate_refresh_token,
        TokenPair,
    )
except ImportError:
    from auth.security import (  # type: ignore
        get_current_user,
        get_rate_limit_key,
        hash_password,
        validate_password_length,
        verify_password,
        issue_token_pair,
        rotate_refresh_token,
        TokenPair,
    )

_ratelimit_enabled = os.getenv("RATELIMIT_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")
if _ratelimit_enabled:
    from slowapi import Limiter
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_rate_limit_key, default_limits=["60/minute"])
else:
    limiter = None  # type: ignore[assignment]

#
# Key policy:
# - The app consistently uses GOOGLE_API_KEY.
# - If GEMINI_API_KEY exists, ignore it to avoid warnings about both being set.
#
if os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
    os.environ.pop("GEMINI_API_KEY", None)

# Force default chat model (can still be overridden via env).
os.environ.setdefault("GEMINI_CHAT_MODEL", "gemini-2.5-flash")

logger = logging.getLogger("ai_virtual_coach.api")
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="AI Virtual Coach API",
    version="2.6.0",
    description="Production-grade FastAPI backend powering AI interview simulation, mock tests, and English practice.",
)

if _ratelimit_enabled:
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

origins = [
    "http://localhost:5173",    # Tera local Vite frontend
    "http://127.0.0.1:5173",    # Alternate local IP
    # "https://your-frontend.vercel.app", # Baad mein yahan Vercel ka link dalna
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # Sirf inhi origins ko allow karega
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
 )

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # Let exception handlers format response; still log timing here.
        duration_ms = (time.perf_counter() - start) * 1000
        logger.exception(
            "request_failed request_id=%s method=%s path=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
        )
        raise

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "request request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    response.headers["X-Request-ID"] = request_id
    return response

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors(),
            }
        },
    )

if _ratelimit_enabled:
    @app.exception_handler(RateLimitExceeded)  # type: ignore[misc]
    async def ratelimit_exception_handler(_request: Request, exc: "RateLimitExceeded"):
        retry_after = None
        try:
            retry_after = getattr(exc, "headers", {}).get("Retry-After")
        except Exception:
            retry_after = None

        headers = {}
        if retry_after:
            headers["Retry-After"] = retry_after

        return JSONResponse(
            status_code=429,
            headers=headers,
            content={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "Too many requests. Please retry later.",
                }
            },
        )

@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    # Avoid leaking internal stack traces to clients.
    logger.exception("Unhandled exception: %s", str(exc))
    msg = str(exc).lower()
    # Best-effort mapping for token/context overflows
    if "maximum context" in msg or "token" in msg and "limit" in msg:
        return JSONResponse(
            status_code=413,
            content={
                "error": {
                    "code": "TOKEN_LIMIT",
                    "message": "The request exceeded the model context limit. Shorten the input and try again.",
                }
            },
        )

    # Best-effort mapping for Gemini upstream failures
    if "quota" in msg or "rate" in msg and "limit" in msg or "google" in msg and "genai" in msg:
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "AI_UPSTREAM_ERROR",
                    "message": "AI provider is unavailable or rate-limited. Please retry shortly.",
                }
            },
        )

    if "chroma" in msg or "vector" in msg and "store" in msg:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "VECTORSTORE_ERROR",
                    "message": "Vector store operation failed.",
                }
            },
        )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Something went wrong. Please try again later.",
            }
        },
    )

@app.on_event("startup")
def _verify_db_on_startup() -> None:
    """
    Verify DB connectivity on startup.

    Migrations are a manual/CI step; we do NOT auto-migrate or auto-create tables here.
    """
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    except Exception as e:
        logger.exception("Database connectivity check failed: %s", str(e))
        raise SystemExit(1)

# =========================
# 🧩 SHARED RESPONSE HELPERS
# =========================
def _user_stats_payload(user: "models.User") -> dict:
    return {
        "readiness": user.readiness_score,
        "interviews": user.total_interviews,
        "mocks": user.total_mocks,
        "streak": user.streak_count,
        "email": user.email,
    }

# =========================
# 🔐 SCHEMAS
# =========================
class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = "Candidate"


class RefreshRequest(BaseModel):
    refresh_token: str

class ChatRequest(BaseModel):
    answer: str
    question: str
    context: str = ""
    user_id: Optional[int] = None
    session_id: Optional[str] = None

class PivotRequest(BaseModel):
    history: list
    context: str
    role: str

class QuizRequest(BaseModel):
    category: str 

class StatsUpdate(BaseModel):
    score: int
    type: str 

# =========================
# ✅ RESPONSE MODELS (Swagger)
# =========================
class ErrorEnvelope(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None

class RootResponse(BaseModel):
    message: str

class StartInterviewResponse(BaseModel):
    status: Literal["success"]
    intro: Optional[str] = None
    questions: Optional[List[str]] = None
    context: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    readiness_score: Optional[int] = None
    state: Optional[str] = None


class TranscriptTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: str


class TranscriptResponse(BaseModel):
    session_id: str
    transcript: List[TranscriptTurn]

class PivotResponse(BaseModel):
    analysis: str
    deep_dives: List[str]

class QuizQuestion(BaseModel):
    id: int
    question: str
    options: List[str]
    answer: str

class EnglishTopicResponse(BaseModel):
    topic: str

class EnglishQuestionsResponse(BaseModel):
    questions: Optional[List[str]] = None

class EnglishQuestionsRequest(BaseModel):
    topic: str

class EnglishReportRequest(BaseModel):
    history: list

class FinalReportResponse(BaseModel):
    overall_score: int
    technical_rating: int
    communication_rating: int
    brutal_feedback: str
    ready_for_senior_role: bool

class UserStatsResponse(BaseModel):
    readiness: int
    interviews: int
    mocks: int
    streak: int
    email: str

class DashboardResponse(BaseModel):
    readiness: int
    attendance: int
    interviews: int
    mocks: int
    avgScore: int
    lastScore: int
    skills: List[dict]
    email: str

class LoginResponse(BaseModel):
    user: dict


class LoginLegacyResponse(LoginResponse):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    expires_in: Optional[int] = None
    token: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class MeResponse(BaseModel):
    id: int
    email: str
    name: str

class StatusResponse(BaseModel):
    status: Literal["ok"]

# =========================
# 📄 PDF UTILS
# =========================
_FILENAME_SAFE_RE = re.compile(r"[^a-zA-Z0-9._-]+")

def sanitize_filename(name: str) -> str:
    base = os.path.basename(name or "resume.pdf")
    cleaned = _FILENAME_SAFE_RE.sub("_", base).strip("._")
    return cleaned[:120] or "resume.pdf"

def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = " ".join([p.extract_text() for p in pdf_reader.pages if p.extract_text()])
        return text.strip()
    except Exception:
        return ""

def extract_text_from_local_pdf(file_path):
    try:
        with open(file_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text = " ".join([p.extract_text() for p in pdf_reader.pages if p.extract_text()])
            return text.strip()
    except:
        return ""

# =========================
# 🎤 INTERVIEW MODULE (8+5 LOGIC)
# =========================

@app.post(
    "/api/start-interview",
    status_code=status.HTTP_201_CREATED,
    response_model=StartInterviewResponse,
    tags=["Interview"],
)
@((limiter.limit("5/minute") if _ratelimit_enabled else (lambda f: f)))  # type: ignore[union-attr]
async def start_interview(
    request: Request,
    resume: UploadFile = File(...),
    jd: str = Form(""),
    role: str = Form("Software Engineer"),
    user_id: int = Form(1),
    db: Session = Depends(get_db),
):
    try:
        # Used by combined rate-limit key (user_id + IP)
        request.state.user_id = str(user_id)
        resume.filename = sanitize_filename(resume.filename)
        content = await resume.read()
        if not content or len(content) < 50:
            raise HTTPException(status_code=400, detail="Empty or invalid PDF upload.")
        if len(content) > 8 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="PDF too large. Max 8MB.")

        # RAG: index resume into Chroma for this user
        chunk_count = upsert_resume(user_id=user_id, file_bytes=content, filename=resume.filename)
        if chunk_count <= 0:
            raise HTTPException(status_code=400, detail="Could not index PDF. Upload a valid text-based PDF.")

        # Keep returning a short context preview for UI compatibility
        resume_text = extract_text_from_pdf_bytes(content)
        
        # Call the refactored engine
        data = await generate_initial_interview(resume_text, jd, role)
        
        if not data:
            raise HTTPException(status_code=500, detail="AI Node failed to respond.")

        session = session_manager.create(user_id=user_id)

        # Persist interview session stub so transcript survives restarts.
        interview = models.Interview(
            user_id=user_id,
            session_id=session.session_id,
            role=role,
            transcript=[],
            had_pivot=True,
        )
        db.add(interview)
        db.commit()
        return {
            "status": "success",
            "intro": data.get("intro"),
            "questions": data.get("questions"),
            "context": (resume_text or "")[:1500],
            "session_id": session.session_id,
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("start_interview failed")
        raise HTTPException(status_code=500, detail="Interview initialization failed")

@app.post(
    "/api/interview/chat",
    summary="Short-turn interview feedback",
    description="Returns 2-line brutal feedback for the candidate's answer.",
    response_model=ChatResponse,
    tags=["Interview"],
)
@((limiter.limit("20/minute") if _ratelimit_enabled else (lambda f: f)))  # type: ignore[union-attr]
async def interview_chat(
    request: Request,
    data: ChatRequest,
    current_user: "models.User" = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user.id
    session_id = data.session_id or "default"
    interview = (
        db.query(models.Interview)
        .filter(models.Interview.session_id == session_id)
        .filter(models.Interview.user_id == user_id)
        .first()
    )
    if not interview:
        raise HTTPException(status_code=404, detail="Invalid session_id")

    # If the in-memory agent session is missing (e.g., after restart),
    # reconstruct it and seed memory from persisted transcript.
    if session_manager.get(session_id) is None:
        session_manager.create(user_id=user_id, session_id=session_id, transcript=interview.transcript or [])

    # Agentic workflow prompt: encourage tool usage
    agent_input = (
        f"UserId: {user_id}\n"
        f"Question: {data.question}\n"
        f"Answer: {data.answer}\n\n"
        "Tasks:\n"
        "1) If needed, use ResumeSearch to recall relevant resume details.\n"
        "2) Use PerformanceScorer to compute readiness score.\n"
        "3) Use FeedbackGenerator to give actionable feedback.\n"
        "4) Decide: follow-up question OR gentle correction OR move to next.\n"
        "Return a single concise reply for the candidate.\n"
    )

    result = await session_manager.invoke(session_id=session_id, user_id=user_id, text=agent_input)
    output = result.get("output") or "Weak signal. Rephrase."

    # Try extracting readiness score from tool outputs if present
    readiness_score = None
    try:
        # agent executor includes `intermediate_steps` sometimes; keep best-effort parsing
        steps = result.get("intermediate_steps") or []
        for step in steps:
            tool_output = str(step[1])
            if tool_output.isdigit():
                readiness_score = int(tool_output)
    except Exception:
        readiness_score = None

    # Persist transcript (append turns)
    now = datetime.now(timezone.utc).isoformat()
    transcript = interview.transcript or []
    transcript.append({"role": "user", "content": data.answer, "timestamp": now})
    transcript.append({"role": "assistant", "content": output, "timestamp": now})
    interview.transcript = transcript
    db.add(interview)
    db.commit()

    return {"reply": output, "readiness_score": readiness_score, "state": "INTERVIEW"}


@app.get(
    "/api/interview/{session_id}/history",
    response_model=TranscriptResponse,
    tags=["Interview"],
)
async def get_interview_history(session_id: str, current_user: "models.User" = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return full transcript for a given interview session."""
    interview = (
        db.query(models.Interview)
        .filter(models.Interview.session_id == session_id)
        .filter(models.Interview.user_id == current_user.id)
        .first()
    )
    if not interview:
        raise HTTPException(status_code=404, detail="Invalid session_id")
    transcript = interview.transcript or []
    return {"session_id": session_id, "transcript": transcript}

@app.post(
    "/api/interview/pivot",
    summary="Pivot deep-dives (8+5 logic)",
    description="Analyzes the first 8 answers and generates 5 follow-up deep-dive questions.",
    response_model=PivotResponse,
    tags=["Interview"],
)
async def interview_pivot(data: PivotRequest, _current_user: "models.User" = Depends(get_current_user)):
    # Using 8+5 Logic helper from engine
    result = await generate_pivot_deepdives(data.history, data.role, data.context)
    if not result:
        raise HTTPException(status_code=500, detail="Pivot logic failed.")
    return result

# =========================
# 📝 MOCK TEST (Zero-Upload)
# =========================

@app.post(
    "/api/generate-quiz",
    summary="Generate mock quiz (20 MCQs)",
    description="Generates 20 MCQs for a given category. Uses PDF context if available, otherwise knowledge-based generation.",
    response_model=List[QuizQuestion],
    tags=["Mock Test"],
)
async def generate_quiz(data: QuizRequest):
    category = data.category.lower()
    pdf_path = f"./data/{category}.pdf"
    
    text = ""
    if os.path.exists(pdf_path):
        text = extract_text_from_local_pdf(pdf_path)

    # Uses the fail-safe logic in generate_neural_quiz (If text empty, AI uses knowledge)
    quiz_data = await generate_neural_quiz(text, data.category)
    
    if not quiz_data:
        raise HTTPException(status_code=500, detail="Assessment synthesis failed.")
    
    return quiz_data

# =========================
# 📚 ENGLISH PRACTICE (5+5 LOGIC)
# =========================

@app.get(
    "/api/english/topic",
    summary="Get English discussion topic",
    description="Generates one advanced discussion topic for English speaking practice.",
    response_model=EnglishTopicResponse,
    tags=["English"],
)
async def get_english_topic():
    topic = await call_llm("Generate 1 advanced discussion topic for English speaking practice. 1 line.")
    return {"topic": topic.strip() if topic else "Modern Leadership Ethics"}

@app.post(
    "/api/english/questions",
    summary="Generate English practice questions",
    description="Returns 5 discussion questions for a given topic.",
    response_model=EnglishQuestionsResponse,
    tags=["English"],
)
async def get_english_questions(data: EnglishQuestionsRequest):
    topic = data.topic
    prompt = f"Topic: {topic}. Generate 5 primary discussion questions. Return JSON list of strings."
    raw = await call_llm(prompt, "Return ONLY JSON.")
    return {"questions": clean_json_response(raw)}

@app.post(
    "/api/english/report",
    summary="Generate final English session report",
    description="Produces a brutally honest performance report from a speaking transcript/history.",
    response_model=FinalReportResponse,
    tags=["English"],
)
async def english_report(data: EnglishReportRequest):
    # Using report helper from engine
    return await generate_final_report(data.history)

# =========================
# 📊 PERSISTENT DASHBOARD
# =========================

@app.get(
    "/api/user/stats/{user_id}",
    summary="Get user stats",
    description="Returns persisted counters and readiness score for a user.",
    response_model=UserStatsResponse,
    tags=["User"],
)
async def get_stats(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(status_code=404)
    return _user_stats_payload(user)

@app.get(
    "/api/dashboard",
    summary="Get dashboard payload",
    description="Returns the dashboard-friendly stats payload used by the frontend UI.",
    response_model=DashboardResponse,
    tags=["User"],
)
async def get_dashboard(
    user_id: int = Query(...),
    db: Session = Depends(get_db),
    _current_user: "models.User" = Depends(get_current_user),
):
    """
    Frontend dashboard expects a single stats object (not a path param).
    We reuse the same DB-backed counters as `/api/user/stats/{user_id}` and
    add UI-friendly fields with safe defaults.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404)

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

@app.post(
    "/api/user/update-stats/{user_id}",
    summary="Update user stats",
    description="Updates counters and readiness score after an interview/mock attempt.",
    response_model=StatusResponse,
    tags=["User"],
)
async def update_stats(user_id: int, data: StatsUpdate, db: Session = Depends(get_db)) -> StatusResponse:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        if data.type == "interview":
            user.total_interviews += 1
            user.readiness_score = min(100, user.readiness_score + 3)
        else:
            user.total_mocks += 1
            user.readiness_score = min(100, user.readiness_score + 1)
        db.commit()
    return {"status": "ok"}

# =========================
# 🔐 AUTH
# =========================

@app.post(
    "/api/login",
    summary="Login (or auto-register)",
    description="Logs in an existing user, or auto-creates a new user for first-time login.",
    response_model=LoginLegacyResponse,
    tags=["Auth"],
)
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    # Backwards-compatible alias for `/api/auth/login`.
    email = (data.email or "").strip().lower()
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        # Preserve previous behavior: auto-register on first login (now with bcrypt).
        try:
            validate_password_length(data.password)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        user = models.User(
            email=email,
            password=hash_password(data.password),
            name="Candidate",
            readiness_score=45,
            total_interviews=0,
            total_mocks=0,
            streak_count=1,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not verify_password(data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid Credentials")

    tokens = issue_token_pair(db=db, user=user)
    return {
        "user": {"id": user.id, "email": user.email},
        "token": tokens.access_token,
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": tokens.token_type,
        "expires_in": tokens.expires_in,
    }


@app.post(
    "/api/auth/signup",
    status_code=status.HTTP_201_CREATED,
    response_model=MeResponse,
    tags=["Auth"],
)
@((limiter.limit("5/minute", key_func=get_remote_address) if _ratelimit_enabled else (lambda f: f)))  # type: ignore[union-attr,name-defined]
async def auth_signup(request: Request, data: SignupRequest, db: Session = Depends(get_db)):
    """Create a new user with bcrypt-hashed password."""
    email = (data.email or "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="Invalid email")
    try:
        validate_password_length(data.password)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = models.User(
        email=email,
        password=hash_password(data.password),
        name=(data.name or "Candidate").strip()[:100],
        readiness_score=45,
        total_interviews=0,
        total_mocks=0,
        streak_count=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "name": user.name}


@app.post(
    "/api/auth/login",
    response_model=TokenResponse,
    tags=["Auth"],
)
@((limiter.limit("10/minute", key_func=get_remote_address) if _ratelimit_enabled else (lambda f: f)))  # type: ignore[union-attr,name-defined]
async def auth_login(request: Request, data: LoginRequest, db: Session = Depends(get_db)):
    """Verify credentials and issue access + refresh tokens."""
    email = (data.email or "").strip().lower()
    try:
        validate_password_length(data.password)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid Credentials")
    tokens = issue_token_pair(db=db, user=user)
    return tokens.__dict__


@app.post(
    "/api/auth/refresh",
    response_model=TokenResponse,
    tags=["Auth"],
)
async def auth_refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    """Rotate refresh token and return new access token pair."""
    # Refresh token is not JWT in this implementation; it's an opaque random string stored hashed in DB.
    token_hash = None
    try:
        from .auth.security import hash_refresh_token  # type: ignore
    except Exception:
        from auth.security import hash_refresh_token  # type: ignore

    token_hash = hash_refresh_token(data.refresh_token)
    row = db.query(models.RefreshToken).filter(models.RefreshToken.token_hash == token_hash).first()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = db.query(models.User).filter(models.User.id == row.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    tokens = rotate_refresh_token(db=db, user=user, refresh_token=data.refresh_token)
    return tokens.__dict__


@app.get(
    "/api/auth/me",
    response_model=MeResponse,
    tags=["Auth"],
)
async def auth_me(current_user: "models.User" = Depends(get_current_user)):
    """Return the current authenticated user."""
    return {"id": current_user.id, "email": current_user.email, "name": current_user.name}

@app.get(
    "/",
    summary="Health check",
    description="Basic health check route.",
    response_model=RootResponse,
    tags=["System"],
)
def root():
    return {"message": "Neural Core Synced with Engine v2.5"}