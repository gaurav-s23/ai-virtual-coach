import httpx
import pytest


try:
    # When running tests from repo root
    import backend.main as main_module
except Exception:
    # When running tests from within backend/
    import main as main_module  # type: ignore


app = main_module.app


class _DummyUpload:
    filename = "resume.pdf"

    async def read(self):
        # Minimal non-empty bytes; RAG store is mocked in tests.
        return b"%PDF-1.4\\n1 0 obj\\n<<>>\\nendobj\\ntrailer\\n<<>>\\n%%EOF"


class _FakeQuery:
    def __init__(self, user):
        self._user = user

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._user


class _FakeSession:
    def __init__(self, user):
        self._user = user

    def query(self, *_args, **_kwargs):
        return _FakeQuery(self._user)


@pytest.mark.asyncio
async def test_read_main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_dashboard_valid_user():
    class _User:
        id = 1
        readiness_score = 55
        total_interviews = 2
        total_mocks = 3
        streak_count = 7
        email = "test@example.com"

    async def _override_get_db():
        yield _FakeSession(_User())

    async def _override_get_current_user():
        return _User()

    app.dependency_overrides[main_module.get_db] = _override_get_db
    app.dependency_overrides[main_module.get_current_user] = _override_get_current_user
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/dashboard", params={"user_id": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert "readiness" in data
        assert "skills" in data
        assert "email" in data
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_dashboard_invalid_user():
    async def _override_get_db():
        yield _FakeSession(None)

    class _User:
        id = 1
        email = "test@example.com"
        name = "Test"

    async def _override_get_current_user():
        return _User()

    app.dependency_overrides[main_module.get_db] = _override_get_db
    app.dependency_overrides[main_module.get_current_user] = _override_get_current_user
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/dashboard", params={"user_id": 999999})
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_start_interview_returns_session_id(monkeypatch):
    # Avoid touching real Chroma / embeddings
    monkeypatch.setattr("backend.services.rag_service.upsert_resume", lambda **_kwargs: 3)
    monkeypatch.setattr("backend.services.rag_service.extract_resume_brief", lambda _b: "resume text")

    async def _fake_generate_initial_interview(_resume_text, _jd, _role):
        return {
            "intro": "hi",
            "skill_questions": [f"sq{i}" for i in range(1, 6)],
            "project_questions": [f"pq{i}" for i in range(1, 6)],
            "followup_questions": [],
        }

    monkeypatch.setattr("backend.services.llm_service.generate_initial_interview", _fake_generate_initial_interview)
    monkeypatch.setattr("backend.routes.interview.generate_initial_interview", _fake_generate_initial_interview)

    class _User:
        id = 1
        email = "test@example.com"
        name = "Test"

    async def _override_get_current_user():
        return _User()

    app.dependency_overrides[main_module.get_current_user] = _override_get_current_user
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            files = {"resume": ("resume.pdf", b"%PDF-1.4\\n" + (b"x" * 200), "application/pdf")}
            data = {"jd": "", "role": "Software Engineer"}
            resp = await client.post("/api/start-interview", files=files, data=data)

        assert resp.status_code == 201
        payload = resp.json()
        assert payload.get("session_id")
        assert len(payload.get("skill_questions", [])) == 5
        assert len(payload.get("project_questions", [])) == 5
    finally:
        app.dependency_overrides.clear()
