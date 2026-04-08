import httpx
import pytest


def test_resume_search_tool_returns_chunks(monkeypatch):
    from backend.agent.tools import ResumeSearchTool

    monkeypatch.setattr("backend.agent.tools.retrieve", lambda user_id, query, k=4: ["chunk1", "chunk2"])
    out = ResumeSearchTool()._run(user_id=1, query="python", k=2)
    assert "Resume context" in out
    assert "chunk1" in out


@pytest.mark.asyncio
async def test_llm_fallback_calls_secondary_on_primary_failure(monkeypatch):
    from backend.llm import router

    calls = []

    async def _fake_acompletion(*, model, messages, temperature, top_p):
        calls.append(model)
        if len(calls) == 1:
            raise RuntimeError("primary down")

        class _Msg:
            content = "ok"

        class _Choice:
            message = _Msg()

        class _Resp:
            choices = [_Choice()]
            provider = "fake"

        return _Resp()

    monkeypatch.setattr(router.litellm, "acompletion", _fake_acompletion)

    res = await router.complete_with_fallback(
        prompt="hi",
        system="sys",
        models=["gemini/gemini-1.5-pro", "gemini/gemini-1.5-flash"],
        timeout_s=5,
    )
    assert res is not None
    assert res.text == "ok"
    assert calls == ["gemini/gemini-1.5-pro", "gemini/gemini-1.5-flash"]

