import pytest
from fastapi.testclient import TestClient

try:
    import backend.main as main_module
except Exception:
    import main as main_module  # type: ignore

try:
    from backend.auth.security import create_access_token
    from backend.services.llm_service import _hash
    from backend.services.scoring_service import warmup_scorer
except Exception:
    from auth.security import create_access_token  # type: ignore
    from services.llm_service import _hash  # type: ignore
    from services.scoring_service import warmup_scorer  # type: ignore


def _auth_headers(user_id: int = 1) -> dict:
    token = create_access_token(user_id=user_id)
    return {"Authorization": f"Bearer {token}"}


def test_proctor_requires_auth():
    client = TestClient(main_module.app)
    response = client.post("/api/proctor/log", json={"session_id": "s1", "event_type": "tab_switch"})
    assert response.status_code == 401


def test_proctor_report_requires_auth():
    client = TestClient(main_module.app)
    response = client.get("/api/proctor/report/s1")
    assert response.status_code == 401


def test_audio_analysis_requires_auth():
    client = TestClient(main_module.app)
    response = client.post(
        "/api/interview/analyze-audio",
        files={"audio": ("sample.wav", b"RIFFxxxxWAVEfmt ", "audio/wav")},
    )
    assert response.status_code == 401


def test_websocket_rejects_without_token():
    client = TestClient(main_module.app)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/interview/session-123"):
            pass


def test_websocket_accepts_with_token():
    client = TestClient(main_module.app)
    token = create_access_token(user_id=1)
    with client.websocket_connect(f"/ws/interview/session-123?token={token}") as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "ping"


def test_hash_changes_for_different_content():
    a = _hash("x" * 200 + "A")
    b = _hash("x" * 200 + "B")
    assert a != b
    assert len(a) == 32


def test_warmup_scorer_callable():
    warmup_scorer()
