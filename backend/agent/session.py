from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Iterable, List

from langchain_litellm import ChatLiteLLM
from langchain_classic.memory import ConversationSummaryBufferMemory
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

from .tools import build_tools


def _chat_model_candidates() -> list[str]:
    """
    Tiered fallback for the agent (tool-calling chat):
    prefer Gemini, fall back to faster Gemini, then local Ollama.
    """
    raw = os.getenv("LLM_CHAT_FALLBACK_MODELS", "").strip()
    if raw:
        return [x.strip() for x in raw.split(",") if x.strip()]
    return [
        "gemini/gemini-1.5-pro",
        "gemini/gemini-1.5-flash",
        "ollama/llama3.1",
    ]


def build_llm(model: Optional[str] = None) -> ChatLiteLLM:
    chosen = model or os.getenv("LLM_CHAT_MODEL") or _chat_model_candidates()[0]
    return ChatLiteLLM(model=chosen, temperature=float(os.getenv("LLM_CHAT_TEMPERATURE", "0.4")))


def build_memory(llm: ChatLiteLLM) -> ConversationSummaryBufferMemory:
    # Summary buffer keeps long-term context while limiting token growth.
    return ConversationSummaryBufferMemory(
        llm=llm,
        max_token_limit=int(os.getenv("MEMORY_MAX_TOKENS", "1200")),
        return_messages=True,
        memory_key="chat_history",
    )


def build_agent(tools: list[BaseTool], *, model: Optional[str] = None) -> AgentExecutor:
    llm = build_llm(model=model)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a professional AI Career Coach and Technical Interviewer.\n"
                "You run an interview in phases, but you can switch to DISCUSSION mode when the user asks for clarification.\n"
                "Rules:\n"
                "- Use ResumeSearch when you need resume facts.\n"
                "- Use PerformanceScorer to compute readiness score for each answer.\n"
                "- Use FeedbackGenerator to give actionable feedback.\n"
                "- If the user's answer is too short, ask a follow-up question.\n"
                "- If the answer is wrong, gently correct it before moving forward.\n"
                "- Always steer back to the next interview question after discussion.\n"
                "Return concise, structured responses.",
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=False)


@dataclass
class AgentSession:
    session_id: str
    user_id: int
    executor: AgentExecutor
    memory: ConversationSummaryBufferMemory
    state: str = "INTERVIEW"
    model_idx: int = 0
    model: str = ""


class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, AgentSession] = {}

    def _seed_memory_from_transcript(self, memory: ConversationSummaryBufferMemory, transcript: list[dict]) -> None:
        """
        Seed ConversationSummaryBufferMemory from a persisted transcript.

        Transcript format: [{"role": "user"|"assistant", "content": str, "timestamp": str}, ...]
        """
        try:
            # Pair up user->assistant turns in order.
            pending_user: Optional[str] = None
            for turn in transcript or []:
                role = (turn or {}).get("role")
                content = (turn or {}).get("content", "")
                if role == "user":
                    pending_user = content
                elif role == "assistant":
                    if pending_user is not None:
                        memory.save_context({"input": pending_user}, {"output": content})
                        pending_user = None
        except Exception:
            # Best-effort seeding; do not block requests.
            return

    def create(self, user_id: int, *, session_id: Optional[str] = None, transcript: Optional[list[dict]] = None) -> AgentSession:
        tools = build_tools()
        models = _chat_model_candidates()
        executor = build_agent(tools, model=models[0])
        memory = build_memory(build_llm(models[0]))
        session_id = session_id or str(uuid.uuid4())
        if transcript:
            self._seed_memory_from_transcript(memory, transcript)
        sess = AgentSession(
            session_id=session_id,
            user_id=user_id,
            executor=executor,
            memory=memory,
            model_idx=0,
            model=models[0],
        )
        self._sessions[session_id] = sess
        return sess

    def get(self, session_id: str) -> Optional[AgentSession]:
        return self._sessions.get(session_id)

    async def invoke(self, session_id: str, user_id: int, text: str) -> Dict[str, Any]:
        sess = self._sessions.get(session_id)
        if not sess:
            # Create a session using the provided session_id so we can
            # reconstruct state across restarts.
            sess = self.create(user_id=user_id, session_id=session_id)

        # Load memory vars into agent
        memory_vars = sess.memory.load_memory_variables({})

        models = _chat_model_candidates()
        last_exc: Optional[BaseException] = None
        for idx in range(sess.model_idx, len(models)):
            try:
                # If we are switching models, rebuild executor+memory LLM (keep stored memory content).
                if idx != sess.model_idx:
                    sess.model_idx = idx
                    sess.model = models[idx]
                    tools = build_tools()
                    sess.executor = build_agent(tools, model=sess.model)
                    # Reuse same memory object; it will call the new llm for summarization.
                    sess.memory.llm = build_llm(sess.model)  # type: ignore[attr-defined]

                result = await sess.executor.ainvoke({"input": text, **memory_vars})
                break
            except Exception as e:
                last_exc = e
                continue
        else:
            # Total failure across all models: do not crash the app.
            return {"output": "AI is temporarily unavailable. Please retry in a moment."}

        # Save interaction to memory
        sess.memory.save_context({"input": text}, {"output": result.get("output", "")})
        return result


session_manager = SessionManager()

