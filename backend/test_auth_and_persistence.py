import importlib
import os

import httpx
import pytest


@pytest.mark.asyncio
async def test_auth_signup_and_login_success():
    import backend.main as main_module

    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/auth/signup", json={"email": "u1@example.com", "password": "pw", "name": "U1"})
        assert resp.status_code == 201

        resp = await client.post("/api/auth/login", json={"email": "u1@example.com", "password": "pw"})
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("access_token")
        assert data.get("refresh_token")


@pytest.mark.asyncio
async def test_auth_duplicate_signup_conflict():
    import backend.main as main_module

    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/auth/signup", json={"email": "dup@example.com", "password": "pw"})
        resp = await client.post("/api/auth/signup", json={"email": "dup@example.com", "password": "pw"})
        assert resp.status_code == 409


@pytest.mark.asyncio
async def test_auth_wrong_password():
    import backend.main as main_module

    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/auth/signup", json={"email": "u2@example.com", "password": "pw"})
        resp = await client.post("/api/auth/login", json={"email": "u2@example.com", "password": "wrong"})
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_protected_endpoint_without_token():
    import backend.main as main_module

    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_expired_token_rejected():
    from datetime import datetime, timedelta, timezone
    from jose import jwt

    import backend.main as main_module

    now = datetime.now(timezone.utc)
    payload = {"sub": "1", "type": "access", "iat": int(now.timestamp()), "exp": now - timedelta(minutes=1)}
    token = jwt.encode(payload, os.environ["JWT_SECRET_KEY"], algorithm=os.getenv("JWT_ALGORITHM", "HS256"))

    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_transcript_persisted_after_chat(monkeypatch):
    import backend.main as main_module
    from backend.database import SessionLocal
    from backend import models

    # Avoid touching real Chroma / embeddings and external LLM calls.
    monkeypatch.setattr(main_module, "upsert_resume", lambda **_kwargs: 3)
    monkeypatch.setattr(main_module, "extract_text_from_pdf_bytes", lambda _b: "resume text")

    async def _fake_generate_initial_interview(_resume_text, _jd, _role):
        return {"intro": "hi", "questions": ["q1", "q2"]}

    monkeypatch.setattr(main_module, "generate_initial_interview", _fake_generate_initial_interview)

    # Make agent invocation deterministic.
    async def _fake_invoke(*_args, **_kwargs):
        return {"output": "assistant reply", "intermediate_steps": []}

    monkeypatch.setattr(main_module.session_manager, "invoke", _fake_invoke)

    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Create user + login to get token.
        resp = await client.post("/api/auth/signup", json={"email": "chat@example.com", "password": "pw"})
        user_id = resp.json()["id"]
        token_resp = await client.post("/api/auth/login", json={"email": "chat@example.com", "password": "pw"})
        access = token_resp.json()["access_token"]

        files = {"resume": ("resume.pdf", b"%PDF-1.4\n" + (b"x" * 200), "application/pdf")}
        data = {"jd": "", "role": "Software Engineer", "user_id": str(user_id)}
        si = await client.post("/api/start-interview", files=files, data=data)
        assert si.status_code == 201
        session_id = si.json()["session_id"]

        chat = await client.post(
            "/api/interview/chat",
            json={"question": "q", "answer": "a", "session_id": session_id},
            headers={"Authorization": f"Bearer {access}"},
        )
        assert chat.status_code == 200

    db = SessionLocal()
    try:
        row = db.query(models.Interview).filter(models.Interview.session_id == session_id).first()
        assert row is not None
        assert isinstance(row.transcript, list)
        assert len(row.transcript) == 2
        assert row.transcript[0]["role"] == "user"
        assert row.transcript[1]["role"] == "assistant"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_rate_limit_returns_429_after_exceeded(monkeypatch):
    """
    Enable rate limiting and hammer /api/auth/login (IP-only) until we get 429.
    """
    import backend.models as models
    from backend.database import SessionLocal
    from backend.auth.security import hash_password

    os.environ["RATELIMIT_ENABLED"] = "true"
    import backend.main as main_module
    main_module = importlib.reload(main_module)

    # Create a user directly in DB to login repeatedly.
    db = SessionLocal()
    try:
        u = models.User(email="rl@example.com", password=hash_password("pw"), name="RL")
        db.add(u)
        db.commit()
    finally:
        db.close()

    transport = httpx.ASGITransport(app=main_module.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        last = None
        for _ in range(12):
            last = await client.post("/api/auth/login", json={"email": "rl@example.com", "password": "pw"})
        assert last is not None
        assert last.status_code in (200, 429)
        # We should eventually hit the limiter.
        assert last.status_code == 429
        assert "Retry-After" in last.headers or last.json().get("error", {}).get("code") == "RATE_LIMITED"

