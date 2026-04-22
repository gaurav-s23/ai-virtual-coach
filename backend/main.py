from __future__ import annotations

import logging
import time
import uuid
import importlib
import os
import threading
import json

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import JWTError

try:
    from .core.config import get_settings
    from .database import engine
    from .auth.security import _jwt_secret
    from .auth.security import decode_access_token
    from .services.rag_service import start_rag_workers
    from .services.scoring_service import warmup_scorer
    from .routes.auth import router as auth_router
    from .routes.interview import router as interview_router
    from .routes.admin import router as admin_router
    from .routes.mock import router as mock_router
    from .routes.user import router as user_router
    from .routes.proctor import router as proctor_router
    from .routes.vision import router as vision_router
except ImportError:
    from core.config import get_settings  # type: ignore
    from database import engine  # type: ignore
    from auth.security import _jwt_secret  # type: ignore
    from auth.security import decode_access_token  # type: ignore
    from services.rag_service import start_rag_workers  # type: ignore
    from services.scoring_service import warmup_scorer  # type: ignore
    from routes.auth import router as auth_router  # type: ignore
    from routes.interview import router as interview_router  # type: ignore
    from routes.admin import router as admin_router  # type: ignore
    from routes.mock import router as mock_router  # type: ignore
    from routes.user import router as user_router  # type: ignore
    from routes.proctor import router as proctor_router  # type: ignore

settings = get_settings()
logger = logging.getLogger("ai_virtual_coach.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

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
origins = [o.strip() for o in _cors_raw.split(",") if o.strip()] or [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "http://0.0.0.0:5173",
    "http://0.0.0.0:3000",
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
    # region agent log
    _debug_log(
        run_id="pre-fix",
        hypothesis_id="H1",
        location="backend/main.py:request_logging_middleware",
        message="HTTP request received",
        data={"method": request.method, "path": request.url.path},
    )
    # endregion
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request_failed request_id=%s method=%s path=%s", request_id, request.method, request.url.path)
        raise
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - start) * 1000,
    )
    # region agent log
    _debug_log(
        run_id="pre-fix",
        hypothesis_id="H2",
        location="backend/main.py:request_logging_middleware",
        message="HTTP response emitted",
        data={"path": request.url.path, "status": response.status_code},
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
    for module_name in ("fastapi", "sqlalchemy", "jose", "passlib", "pydantic", "litellm", "PyPDF2"):
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            raise SystemExit(f"Missing required dependency '{module_name}': {exc}") from exc
    if not settings.admin_email:
        raise SystemExit("Missing required env: ADMIN_EMAIL")
    if not settings.admin_password:
        raise SystemExit("Missing required env: ADMIN_PASSWORD")
    try:
        _jwt_secret()
    except Exception:
        raise SystemExit("Missing required env: JWT_SECRET_KEY")
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    except Exception:
        logger.exception("Database connectivity check failed")
        raise SystemExit(1)
    worker_count = int(os.getenv("RAG_WORKER_COUNT", "1"))
    start_rag_workers(worker_count=worker_count)
    threading.Thread(target=warmup_scorer, daemon=True).start()


app.include_router(auth_router)
app.include_router(interview_router)
app.include_router(admin_router)
app.include_router(mock_router)
app.include_router(user_router)
app.include_router(proctor_router)
app.include_router(vision_router)

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