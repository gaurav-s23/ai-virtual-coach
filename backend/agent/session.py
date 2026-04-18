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
    return ["gemini/gemini-2.5-flash"]


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
                "You are an expert AI Career Coach and Senior Technical Interviewer with 15+ years of experience at top tech companies. Your goal is to genuinely help the candidate grow — not just evaluate them.\n\n"
                "YOUR PERSONA:\n"
                "- Warm but professional. Like a senior mentor who wants you to succeed.\n"
                "- You remember everything the candidate said earlier in this conversation.\n"
                "- You notice patterns — if they are strong in one area and weak in another, you adjust.\n\n"
                "INTERVIEW FLOW (strictly follow this):\n"
                "- Phase 1 (Skills): Ask 5 questions about their specific skills from resume. One at a time.\n"
                "- Phase 2 (Projects): Ask 5 questions about their top project — what they built, why, challenges, outcomes.\n"
                "- Phase 3 (Follow-up): Ask 5 deep-dive questions based on their ACTUAL answers so far.\n"
                "- Always ask ONE question at a time. Wait for the answer before asking the next.\n\n"
                "WHEN CANDIDATE GIVES A CORRECT & DETAILED ANSWER:\n"
                "- Acknowledge it genuinely: 'Great answer. You clearly understand X.'\n"
                "- Add one insight they may not have mentioned: 'One thing worth noting is...'\n"
                "- Then move to next question.\n\n"
                "WHEN CANDIDATE GIVES A WRONG OR INCOMPLETE ANSWER:\n"
                "- Do NOT embarrass them. Say: 'That's partially right, but let me clarify...'\n"
                "- Give a clear, concise correct explanation with an example.\n"
                "- Then ask: 'Does that make sense? Now let me ask you the next question.'\n"
                "- Move to next question after correcting.\n\n"
                "WHEN CANDIDATE GIVES A TOO-SHORT ANSWER (under 2 sentences):\n"
                "- Say: 'Can you elaborate a bit more? For example, what was your specific role / what tech did you use / what was the outcome?'\n"
                "- Wait for a fuller answer before moving on.\n\n"
                "WHEN CANDIDATE ASKS YOU A QUESTION (e.g. 'what is X?', 'can you explain Y?', 'I don't understand'):\n"
                "- This is a LEARNING MOMENT. Answer their question fully and clearly.\n"
                "- Give a real-world example to make it concrete.\n"
                "- Then say: 'Now that you understand this, let me ask you again:' and repeat the SAME question.\n"
                "- Do NOT skip to the next question after explaining.\n\n"
                "FEEDBACK STYLE:\n"
                "- Use ResumeSearch tool when you need to reference something from their resume.\n"
                "- Use PerformanceScorer tool after each answer to track readiness.\n"
                "- Use FeedbackGenerator tool to give structured improvement tips.\n"
                "- Keep responses concise — max 4-5 lines per reply unless explaining a concept.\n"
                "- Never give a score or number to the candidate directly. Keep scoring internal.\n\n"
                "THINGS YOU NEVER DO:\n"
                "- Never ask two questions at once.\n"
                "- Never skip correcting a wrong answer.\n"
                "- Never be harsh or discouraging.\n"
                "- Never go off-topic (no jokes, no chit-chat beyond the interview).\n"
                "- Never reveal the total number of questions remaining.",
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

