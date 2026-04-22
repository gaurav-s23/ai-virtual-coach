from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
import json, os
from datetime import datetime
try:
    from .. import models
    from ..core.security import get_current_user
except ImportError:
    import models  # type: ignore
    from core.security import get_current_user  # type: ignore

router = APIRouter(tags=["proctor"])

class ProctorEvent(BaseModel):
    session_id: str
    event_type: str
    timestamp: Optional[str] = None
    metadata: Optional[dict] = None

@router.post("/api/proctor/log")
async def log_proctor_event(event: ProctorEvent, current_user: "models.User" = Depends(get_current_user)):
    log_dir = "backend/data/proctor_logs"
    os.makedirs(log_dir, exist_ok=True)
    path = f"{log_dir}/{event.session_id}.json"
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
    path = f"backend/data/proctor_logs/{session_id}.json"
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
