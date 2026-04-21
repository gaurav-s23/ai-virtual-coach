from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = "Candidate"


class RefreshRequest(BaseModel):
    refresh_token: str


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class ChatRequest(BaseModel):
    answer: str = Field(min_length=1)
    question: str = Field(min_length=1)
    context: str = ""
    session_id: Optional[str] = None
    time_taken_seconds: Optional[float] = None


class PivotRequest(BaseModel):
    history: list
    context: str
    role: str
    session_id: Optional[str] = None


class AnswerRelevanceResponse(BaseModel):
    is_relevant: bool
    score: float
    verdict: Literal["on-topic", "off-topic", "partial"]


class QuizRequest(BaseModel):
    category: str
    force_new: bool = False


class StatsUpdate(BaseModel):
    score: int
    type: str


class EnglishQuestionsRequest(BaseModel):
    topic: str


class EnglishReportRequest(BaseModel):
    history: list


class StartInterviewResponse(BaseModel):
    status: Literal["success"]
    intro: Optional[str] = None
    questions: Optional[list[str]] = None
    skill_questions: Optional[list[str]] = None
    project_questions: Optional[list[str]] = None
    followup_questions: Optional[list[str]] = None
    context: str
    session_id: Optional[str] = None
    rag_status: Optional[Literal["processing", "ready", "failed"]] = "processing"
    candidate_name: Optional[str] = None
    interview_status: Optional[str] = "starting"
    countdown_seconds: Optional[int] = 8


class ChatResponse(BaseModel):
    reply: str
    readiness_score: Optional[int] = None
    state: Optional[str] = None
    quality_score: Optional[float] = None
    relevance: Optional[dict[str, Any]] = None
    timing_flag: Optional[str] = None


class PivotResponse(BaseModel):
    analysis: str
    deep_dives: list[str]


class QuizQuestion(BaseModel):
    id: int
    question: str
    options: list[str]
    answer: str


class EnglishQuestionsResponse(BaseModel):
    questions: Optional[list[str]] = None


class FinalReportResponse(BaseModel):
    overall_score: int
    technical_rating: int
    communication_rating: int
    brutal_feedback: str
    ready_for_senior_role: bool


class UserStatsResponse(BaseModel):
    readiness: int
    interviews: int
    mocks: int
    streak: int
    email: str


class DashboardResponse(BaseModel):
    readiness: int
    attendance: int
    interviews: int
    mocks: int
    avgScore: int
    lastScore: int
    skills: list[dict]
    email: str


class LoginLegacyResponse(BaseModel):
    user: dict[str, Any]
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    expires_in: Optional[int] = None
    token: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class MeResponse(BaseModel):
    id: int
    email: str
    name: str


class ProctorLogRequest(BaseModel):
    session_id: str
    event_type: str
    timestamp: str
