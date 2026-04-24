import logging
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Optional
import json, os
from datetime import datetime

logger = logging.getLogger(__name__)
try:
    import models
    from core.security import get_current_user
    from core.rate_limit import enforce_rate_limit
except ImportError as e:
    logger.error(f"Import error in proctor.py: {e}")
    # Fallback imports for development
    try:
        import models
        from core.security import get_current_user
        from core.rate_limit import enforce_rate_limit
    except ImportError as fallback_error:
        logger.error(f"Fallback import error in proctor.py: {fallback_error}")
        raise SystemExit(f"Failed to import required modules in proctor.py: {fallback_error}")

router = APIRouter(tags=["proctor"])

class ProctorEvent(BaseModel):
    session_id: str
    event_type: str
    timestamp: Optional[str] = None
    metadata: Optional[dict] = None

@router.post("/api/proctor/log")
async def log_proctor_event(
    event: ProctorEvent, 
    current_user: "models.User" = Depends(get_current_user),
    request: Request = None
):
    # Rate limiting: 50 events per minute per user
    enforce_rate_limit(
        key=f"proctor_log:{current_user.id}",
        max_requests=50,
        window_seconds=60
    )
    
    # Use secure, configurable location for proctor logs
    log_dir = os.getenv("PROCTOR_LOG_DIR", "/tmp/proctor_logs")
    os.makedirs(log_dir, exist_ok=True, mode=0o700)  # Restrictive permissions
    
    # Sanitize session_id to prevent path traversal
    safe_session_id = "".join(c for c in event.session_id if c.isalnum() or c in "-_")
    if not safe_session_id:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    
    path = os.path.join(log_dir, f"{safe_session_id}.json")
    logs = []
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                logs = json.load(f)
        except Exception:
            logs = []
    logs.append({
        "event_type": event.event_type,
        "timestamp": event.timestamp or datetime.utcnow().isoformat(),
        "metadata": event.metadata or {}
    })
    with open(path, "w") as f:
        json.dump(logs, f, indent=2)
    return {"status": "logged", "total_events": len(logs)}

@router.get("/api/proctor/report/{session_id}")
async def get_proctor_report(session_id: str, current_user: "models.User" = Depends(get_current_user)):
    # Use secure, configurable location for proctor logs
    log_dir = os.getenv("PROCTOR_LOG_DIR", "/tmp/proctor_logs")
    
    # Sanitize session_id to prevent path traversal
    safe_session_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
    if not safe_session_id:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    
    path = os.path.join(log_dir, f"{safe_session_id}.json")
    if not os.path.exists(path):
        return {"session_id": session_id, "events": [], "summary": {}}
    with open(path, "r") as f:
        logs = json.load(f)
    tab_switches = sum(1 for e in logs if e["event_type"] == "tab_switch")
    tab_hidden = sum(1 for e in logs if e["event_type"] == "tab_hidden")
    return {
        "session_id": session_id,
        "events": logs,
        "summary": {
            "total_events": len(logs),
            "tab_switches": tab_switches,
            "tab_hidden_count": tab_hidden,
            "integrity_score": max(0, 100 - (tab_switches * 10) - (tab_hidden * 5))
        }
    }
