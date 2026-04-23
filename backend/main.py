from __future__ import annotations

import logging
import time
import uuid
import importlib
import os
import threading
import json
from pathlib import Path

# Load environment variables early - this must be done before any imports that depend on env vars
from dotenv import load_dotenv

# Try to load .env from multiple possible locations
env_paths = [
    Path.cwd() / ".env",  # Current working directory
    Path(__file__).parent.parent / ".env",  # Project root (backend/../.env)
    Path(__file__).parent / ".env",  # Backend directory
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break
else:
    # If no .env file found, still try to load from default location
    load_dotenv()

# Setup logging early
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("ai_virtual_coach.api")

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import JWTError

try:
    from core.config import get_settings
    from database import engine
    from auth.security import _jwt_secret
    from auth.security import decode_access_token
    from services.rag_service import start_rag_workers
    from services.scoring_service import warmup_scorer
    from routes.auth import router as auth_router
    from routes.interview import router as interview_router
    from routes.admin import router as admin_router
    from routes.mock import router as mock_router
    from routes.user import router as user_router
    from routes.proctor import router as proctor_router
    from routes.vision import router as vision_router
    from routes.english import router as english_router
except ImportError as e:
    logger.error(f"Import error in main.py: {e}")
    # Fallback imports for development
    try:
        from core.config import get_settings
        from database import engine
        from auth.security import _jwt_secret, decode_access_token
        from services.rag_service import start_rag_workers
        from services.scoring_service import warmup_scorer
        from routes.auth import router as auth_router
        from routes.interview import router as interview_router
        from routes.admin import router as admin_router
        from routes.mock import router as mock_router
        from routes.user import router as user_router
        from routes.proctor import router as proctor_router
        from routes.vision import router as vision_router
        from routes.english import router as english_router
    except ImportError as fallback_error:
        logger.error(f"Fallback import error: {fallback_error}")
        raise SystemExit(f"Failed to import required modules: {fallback_error}")

settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.app_version)
_DEBUG_LOG_PATH = "debug-196b20.log"


def _debug_log(*, run_id: str, hypothesis_id: str, location: str, message: str, data: dict) -> None:
    payload = {
        "sessionId": "196b20",
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")

_cors_raw = os.getenv("CORS_ORIGINS", "")
# Enhanced CORS origins for local development
origins = [o.strip() for o in _cors_raw.split(",") if o.strip()] or [
    "http://localhost:5173",    # Vite default
    "http://localhost:3000",    # Create React App default
    "http://127.0.0.1:5173",   # Alternative localhost
    "http://127.0.0.1:3000",   # Alternative localhost
    "http://0.0.0.0:5173",     # Network access
    "http://0.0.0.0:3000",     # Network access
    "http://localhost:8080",   # Alternative dev port
    "http://127.0.0.1:8080",   # Alternative dev port
]
if settings.frontend_url:
    origins.append(settings.frontend_url)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    start = time.perf_counter()
    
    # Enhanced logging for streaming endpoints
    is_streaming_endpoint = request.url.path in [
        "/api/generate-quiz",
        "/api/interview/chat", 
        "/api/english/chat"
    ]
    
    # region agent log
    _debug_log(
        run_id="pre-fix",
        hypothesis_id="H1",
        location="backend/main.py:request_logging_middleware",
        message="HTTP request received",
        data={"method": request.method, "path": request.url.path, "streaming": is_streaming_endpoint},
    )
    # endregion
    
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request_failed request_id=%s method=%s path=%s", request_id, request.method, request.url.path)
        raise
    
    response.headers["X-Request-ID"] = request_id
    
    # Add streaming headers for SSE endpoints
    if is_streaming_endpoint and hasattr(response, 'headers'):
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Connection"] = "keep-alive"
        response.headers["X-Accel-Buffering"] = "no"  # Disable nginx buffering
    
    logger.info(
        "request request_id=%s method=%s path=%s status=%s duration_ms=%.2f streaming=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - start) * 1000,
        is_streaming_endpoint,
    )
    
    # region agent log
    _debug_log(
        run_id="pre-fix",
        hypothesis_id="H2",
        location="backend/main.py:request_logging_middleware",
        message="HTTP response emitted",
        data={"path": request.url.path, "status": response.status_code, "streaming": is_streaming_endpoint},
    )
    # endregion
    
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {"code": "VALIDATION_ERROR", "message": "Invalid input", "details": exc.errors()}})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", str(exc))
    return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_SERVER_ERROR", "message": "Server error, try again"}})


@app.on_event("startup")
def _verify_db_on_startup() -> None:
    """Verify all required dependencies and environment variables on startup."""
    logger.info("Starting application startup verification...")
    
    # Check required dependencies
    missing_deps = []
    for module_name in ("fastapi", "sqlalchemy", "jose", "passlib", "pydantic", "litellm", "PyPDF2"):
        try:
            importlib.import_module(module_name)
            logger.debug(f"✓ Dependency '{module_name}' is available")
        except Exception as exc:
            missing_deps.append(module_name)
            logger.error(f"✗ Missing required dependency '{module_name}': {exc}")
    
    if missing_deps:
        logger.error(f"Application cannot start: Missing dependencies: {', '.join(missing_deps)}")
        logger.error("Please install missing dependencies with: pip install -r requirements.txt")
        raise SystemExit(f"Missing required dependencies: {', '.join(missing_deps)}")
    
    # Check required environment variables
    missing_vars = []
    if not settings.admin_email:
        missing_vars.append("ADMIN_EMAIL")
        logger.error("✗ ADMIN_EMAIL is not set or is empty")
    else:
        logger.debug(f"✓ ADMIN_EMAIL is configured: {settings.admin_email}")
    
    if not settings.admin_password:
        missing_vars.append("ADMIN_PASSWORD")
        logger.error("✗ ADMIN_PASSWORD is not set or is empty")
    else:
        logger.debug("✓ ADMIN_PASSWORD is configured")
    
    try:
        _jwt_secret()
        logger.debug("✓ JWT_SECRET_KEY is configured")
    except Exception:
        missing_vars.append("JWT_SECRET_KEY")
        logger.error("✗ JWT_SECRET_KEY is not set or is invalid")
    
    if missing_vars:
        logger.error(f"Application cannot start: Missing environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in your .env file or environment")
        logger.info("Refer to .env.example for required variables")
        raise SystemExit(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Check database connectivity
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        logger.info("✓ Database connectivity check passed")
    except Exception as exc:
        logger.error(f"✗ Database connectivity check failed: {exc}")
        logger.error("Please ensure your database is running and DATABASE_URL is correct")
        raise SystemExit("Database connectivity failed")
    
    # Start background services
    try:
        worker_count = int(os.getenv("RAG_WORKER_COUNT", "1"))
        logger.info(f"Starting {worker_count} RAG worker(s)...")
        start_rag_workers(worker_count=worker_count)
        logger.info("✓ RAG workers started")
        
        logger.info("Starting scoring service warmup...")
        threading.Thread(target=warmup_scorer, daemon=True).start()
        logger.info("✓ Scoring service warmup initiated")
    except Exception as exc:
        logger.error(f"✗ Failed to start background services: {exc}")
        raise SystemExit(f"Background services failed to start: {exc}")
    
    logger.info("✓ All startup checks passed successfully")
    logger.info(f"Application '{settings.app_name}' v{settings.app_version} is ready")


app.include_router(auth_router)
app.include_router(interview_router)
app.include_router(admin_router)
app.include_router(mock_router)
app.include_router(user_router)
app.include_router(proctor_router)
app.include_router(vision_router)
app.include_router(english_router)

_ws_connections: dict = {}


@app.websocket("/ws/interview/{session_id}")
async def interview_ws(websocket: WebSocket, session_id: str):
    token = websocket.query_params.get("token")
    # region agent log
    _debug_log(
        run_id="pre-fix",
        hypothesis_id="H3",
        location="backend/main.py:interview_ws",
        message="WebSocket connect attempt",
        data={"session_id": session_id, "has_token": bool(token)},
    )
    # endregion
    if not token:
        # region agent log
        _debug_log(
            run_id="pre-fix",
            hypothesis_id="H3",
            location="backend/main.py:interview_ws",
            message="WebSocket rejected missing token",
            data={"session_id": session_id},
        )
        # endregion
        await websocket.close(code=1008)
        return
    try:
        decode_access_token(token)
    except (JWTError, ValueError):
        # region agent log
        _debug_log(
            run_id="pre-fix",
            hypothesis_id="H4",
            location="backend/main.py:interview_ws",
            message="WebSocket rejected invalid token",
            data={"session_id": session_id},
        )
        # endregion
        await websocket.close(code=1008)
        return
    # region agent log
    _debug_log(
        run_id="pre-fix",
        hypothesis_id="H5",
        location="backend/main.py:interview_ws",
        message="WebSocket token accepted",
        data={"session_id": session_id},
    )
    # endregion
    await websocket.accept()
    _ws_connections[session_id] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(data)
    except WebSocketDisconnect:
        _ws_connections.pop(session_id, None)
    except Exception:
        _ws_connections.pop(session_id, None)


@app.get("/")
def root():
    return {"message": "Neural Core Synced with Engine v3.0"}