from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

try:
    from ..rag.store import retrieve
except ImportError:
    from rag.store import retrieve


class ResumeSearchInput(BaseModel):
    user_id: int = Field(..., description="User id whose resume is indexed")
    query: str = Field(..., description="What to look for in the resume")
    k: int = Field(4, ge=1, le=10, description="Top-k chunks to return")


class ResumeSearchTool(BaseTool):
    name: str = "ResumeSearch"
    description: str = (
        "Retrieve relevant resume details from the vector DB for a given user_id. "
        "Use this when you need facts from the candidate's resume (projects, skills, experience)."
    )
    args_schema: type[BaseModel] = ResumeSearchInput

    def _run(self, user_id: int, query: str, k: int = 4) -> str:
        chunks = retrieve(user_id=user_id, query=query, k=k)
        if not chunks:
            return "No relevant resume context found."
        bullets = "\n".join([f"- {c[:600].strip()}" for c in chunks])
        return f"Resume context (top {len(chunks)}):\n{bullets}"


class PerformanceScorerInput(BaseModel):
    answer: str = Field(..., description="Candidate answer text")
    question: str = Field(..., description="Question asked")
    history_count: int = Field(0, ge=0, le=100, description="How many turns have happened so far")


class PerformanceScorerTool(BaseTool):
    name: str = "PerformanceScorer"
    description: str = (
        "Compute a real-time readiness score (0-100) from the candidate's answer and question. "
        "This is a deterministic tool; it does not call the LLM."
    )
    args_schema: type[BaseModel] = PerformanceScorerInput

    def _run(self, answer: str, question: str, history_count: int = 0) -> str:
        a = (answer or "").strip()
        q = (question or "").strip()

        # Simple rubric: length + structure signals + relevance cues.
        length = len(a)
        score = 35

        if length >= 40:
            score += 10
        if length >= 120:
            score += 10
        if length >= 240:
            score += 5

        structure_hits = sum(
            1
            for token in ["because", "therefore", "trade-off", "example", "edge case", "complexity", "time", "space"]
            if token in a.lower()
        )
        score += min(20, structure_hits * 3)

        # If the answer obviously doesn't reference the question at all, slight penalty.
        if q and not any(w in a.lower() for w in (q.lower().split()[:3] or [])):
            score -= 3

        # Small streak bonus for sustained turns.
        score += min(10, history_count // 4)

        score = max(0, min(100, score))
        return str(score)


class FeedbackGeneratorInput(BaseModel):
    question: str = Field(..., description="Question asked")
    answer: str = Field(..., description="Candidate answer")
    score: int = Field(..., ge=0, le=100, description="Readiness score produced by PerformanceScorer")


class FeedbackGeneratorTool(BaseTool):
    name: str = "FeedbackGenerator"
    description: str = (
        "Generate constructive feedback for the candidate answer given the score. "
        "Use this after scoring to produce actionable improvement notes."
    )
    args_schema: type[BaseModel] = FeedbackGeneratorInput

    def _run(self, question: str, answer: str, score: int) -> str:
        a = (answer or "").strip()
        if len(a) < 30:
            return (
                "Your answer is too short to evaluate depth. Expand with: (1) definition, (2) steps, "
                "(3) example, (4) edge cases, (5) trade-offs."
            )
        if score < 50:
            return (
                "You have the right direction, but it's missing concrete reasoning. Add a worked example, "
                "explicit assumptions, and at least one edge case + complexity."
            )
        if score < 75:
            return (
                "Solid answer. To make it senior-level: call out trade-offs, failure modes, and quantify performance. "
                "Use one crisp example and be explicit about constraints."
            )
        return (
            "Strong answer. To sharpen further: tighten structure, mention one edge case, and summarize in one line "
            "so an interviewer can quickly validate your reasoning."
        )


def build_tools() -> List[BaseTool]:
    return [ResumeSearchTool(), PerformanceScorerTool(), FeedbackGeneratorTool()]

