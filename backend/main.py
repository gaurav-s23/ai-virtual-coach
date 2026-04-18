from __future__ import annotations

import logging
import time
import uuid
import importlib
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    from .core.config import get_settings
    from .database import engine
    from .auth.security import _jwt_secret
    from .services.rag_service import start_rag_workers
    from .routes.auth import router as auth_router
    from .routes.interview import router as interview_router
    from .routes.admin import router as admin_router
    from .routes.mock import router as mock_router
    from .routes.user import router as user_router
except ImportError:
    from core.config import get_settings  # type: ignore
    from database import engine  # type: ignore
    from auth.security import _jwt_secret  # type: ignore
    from services.rag_service import start_rag_workers  # type: ignore
    from routes.auth import router as auth_router  # type: ignore
    from routes.interview import router as interview_router  # type: ignore
    from routes.admin import router as admin_router  # type: ignore
    from routes.mock import router as mock_router  # type: ignore
    from routes.user import router as user_router  # type: ignore

settings = get_settings()
logger = logging.getLogger("ai_virtual_coach.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title=settings.app_name, version=settings.app_version)

origins = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
if settings.frontend_url:
    origins.append(settings.frontend_url)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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


app.include_router(auth_router)
app.include_router(interview_router)
app.include_router(admin_router)
app.include_router(mock_router)
app.include_router(user_router)


@app.get("/")
def root():
    return {"message": "Neural Core Synced with Engine v3.0"}