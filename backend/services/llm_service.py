from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any
import os
from datetime import datetime, timezone, timedelta

from pydantic import BaseModel, Field, ValidationError, TypeAdapter

try:
    from ..core.config import get_settings
    from ..llm.router import complete_with_fallback, get_fallback_models
    from ..database import SessionLocal
    from .. import models
except ImportError:
    from core.config import get_settings  # type: ignore
    from llm.router import complete_with_fallback, get_fallback_models  # type: ignore
    from database import SessionLocal  # type: ignore
    import models  # type: ignore

logger = logging.getLogger("ai_virtual_coach.services.llm")
settings = get_settings()
_MODELS = get_fallback_models()
_CACHE: dict[str, tuple[float, Any]] = {}
_REDIS = None
try:
    import redis.asyncio as redis  # type: ignore

    redis_url = os.getenv("REDIS_URL", "").strip()
    if redis_url:
        _REDIS = redis.from_url(redis_url, decode_responses=True)
except Exception:
    _REDIS = None


class InterviewPlan(BaseModel):
    intro: str
    skill_questions: list[str] = Field(min_length=5, max_length=5)
    project_questions: list[str] = Field(min_length=5, max_length=5)
    followup_questions: list[str] = Field(default_factory=list)


class PivotPlan(BaseModel):
    analysis: str
    deep_dives: list[str] = Field(min_length=5, max_length=5)


class QuizQuestion(BaseModel):
    id: int
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    answer: str


class FinalReport(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    technical_rating: int = Field(ge=0, le=100)
    communication_rating: int = Field(ge=0, le=100)
    brutal_feedback: str
    ready_for_senior_role: bool


class ChatFeedback(BaseModel):
    reply: str
    readiness_score: int = Field(ge=0, le=100)


def _cache_get(key: str) -> Any | None:
    item = _CACHE.get(key)
    if not item:
        return None
    expires_at, value = item
    if expires_at < time.time():
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any) -> None:
    _CACHE[key] = (time.time() + settings.llm_cache_ttl_s, value)


def _db_cache_get(key: str, schema: type[BaseModel]) -> BaseModel | None:
    db = SessionLocal()
    try:
        row = db.query(models.CacheEntry).filter(models.CacheEntry.key == key).first()
        if not row:
            return None
        if row.expires_at < datetime.now(timezone.utc):
            db.delete(row)
            db.commit()
            return None
        return schema.model_validate_json(row.value_json)
    except Exception:
        return None
    finally:
        db.close()


def _db_cache_set(key: str, value: BaseModel) -> None:
    db = SessionLocal()
    try:
        row = db.query(models.CacheEntry).filter(models.CacheEntry.key == key).first()
        if row is None:
            row = models.CacheEntry(
                key=key,
                value_json=value.model_dump_json(),
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.llm_cache_ttl_s),
            )
            db.add(row)
        else:
            row.value_json = value.model_dump_json()
            row.expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.llm_cache_ttl_s)
            db.add(row)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


async def _llm_json_call(*, cache_key: str, prompt: str, schema: type[BaseModel], fallback: BaseModel) -> BaseModel:
    cached = _cache_get(cache_key)
    if cached is None:
        db_cached = _db_cache_get(cache_key, schema)
        if db_cached is not None:
            _cache_set(cache_key, db_cached)
            return db_cached
    if cached is None and _REDIS is not None:
        try:
            raw = await _REDIS.get(cache_key)
            if raw:
                parsed = schema.model_validate_json(raw)
                _cache_set(cache_key, parsed)
                _db_cache_set(cache_key, parsed)
                return parsed
        except Exception:
            logger.warning("redis_cache_get_failed cache_key=%s", cache_key)
            db_cached = _db_cache_get(cache_key, schema)
            if db_cached is not None:
                _cache_set(cache_key, db_cached)
                return db_cached
    if cached is not None:
        return cached

    adapter = TypeAdapter(schema)
    attempts = max(1, settings.llm_retry_count + 1)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = await complete_with_fallback(
                prompt=prompt,
                system="Return strict JSON only.",
                models=_MODELS,
                timeout_s=settings.llm_timeout_s,
                temperature=settings.llm_temperature,
                top_p=settings.llm_top_p,
            )
            text = (response.text if response else "").strip()
            data = json.loads(text)
            parsed = adapter.validate_python(data)
            _cache_set(cache_key, parsed)
            _db_cache_set(cache_key, parsed)
            if _REDIS is not None:
                try:
                    await _REDIS.setex(cache_key, settings.llm_cache_ttl_s, parsed.model_dump_json())
                except Exception:
                    logger.warning("redis_cache_set_failed cache_key=%s", cache_key)
            return parsed
        except (json.JSONDecodeError, ValidationError, ValueError, TypeError) as exc:
            last_error = exc
        except Exception as exc:  # network/provider errors
            last_error = exc
        if attempt < attempts - 1:
            await asyncio.sleep(0.6 * (attempt + 1))

    if last_error:
        logger.warning("llm_json_fallback cache_key=%s error=%s", cache_key, str(last_error))
    _cache_set(cache_key, fallback)
    _db_cache_set(cache_key, fallback)
    if _REDIS is not None:
        try:
            await _REDIS.setex(cache_key, settings.llm_cache_ttl_s, fallback.model_dump_json())
        except Exception:
            logger.warning("redis_cache_set_failed cache_key=%s", cache_key)
    return fallback


async def generate_initial_interview(resume_text: str, jd_text: str, role: str) -> dict:
    prompt = (
        f"Role: {role}\n"
        f"Resume: {(resume_text or '')[:800]}\n"
        f"JD: {(jd_text or '')[:400]}\n"
        'Output schema: {"intro":"...", "skill_questions":["...x5"], "project_questions":["...x5"], "followup_questions":[]}'
    )
    fallback = InterviewPlan(
        intro=f"Welcome to your interview for {role}.",
        skill_questions=[
            "Tell me about your strongest technical skill.",
            "How do you debug production issues?",
            "How do you design reliable APIs?",
            "How do you test your changes before release?",
            "How do you handle performance bottlenecks?",
        ],
        project_questions=[
            "Describe your most impactful project.",
            "What architecture did you use and why?",
            "What trade-offs did you make?",
            "What challenge took the most effort to solve?",
            "What did you learn from that project?",
        ],
        followup_questions=[],
    )
    result = await _llm_json_call(
        cache_key=f"interview:{role}:{(resume_text or '')[:120]}:{(jd_text or '')[:120]}",
        prompt=prompt,
        schema=InterviewPlan,
        fallback=fallback,
    )
    return result.model_dump()


async def generate_pivot_deepdives(history: list, role: str, context: str) -> dict:
    prompt = (
        f"Role: {role}\n"
        f"History: {json.dumps(history)[:1400]}\n"
        f"Context: {(context or '')[:400]}\n"
        'Output schema: {"analysis":"...", "deep_dives":["...x5"]}'
    )
    fallback = PivotPlan(
        analysis="Need deeper validation on implementation depth and decision quality.",
        deep_dives=[
            "Explain a production issue you solved end-to-end with root cause.",
            "How would you redesign your project for 10x scale?",
            "Describe failure modes and mitigation strategies in your architecture.",
            "What metrics would you monitor and why?",
            "How would you reduce latency and cost simultaneously?",
        ],
    )
    result = await _llm_json_call(
        cache_key=f"pivot:{role}:{json.dumps(history)[:120]}",
        prompt=prompt,
        schema=PivotPlan,
        fallback=fallback,
    )
    return result.model_dump()


async def generate_quiz(pdf_text: str, category: str) -> list[dict]:
    prompt = (
        f"Category: {category}\n"
        f"Context: {(pdf_text or '')[:900]}\n"
        'Output schema: [{"id":1,"question":"...","options":["a","b","c","d"],"answer":"..."} x10]'
    )
    fallback = [
        QuizQuestion(
            id=1,
            question=f"Which concept is foundational in {category}?",
            options=["Option A", "Option B", "Option C", "Option D"],
            answer="Option A",
        ).model_dump()
    ]
    cached = _cache_get(f"quiz:{category.lower()}")
    if cached is not None:
        return cached

    attempts = max(1, settings.llm_retry_count + 1)
    adapter = TypeAdapter(list[QuizQuestion])
    for attempt in range(attempts):
        try:
            response = await complete_with_fallback(
                prompt=prompt,
                system="Return strict JSON array only.",
                models=_MODELS,
                timeout_s=settings.llm_timeout_s + 2,
                temperature=settings.llm_temperature,
                top_p=settings.llm_top_p,
            )
            raw = json.loads((response.text if response else "").strip())
            parsed = adapter.validate_python(raw)
            result = [item.model_dump() for item in parsed]
            _cache_set(f"quiz:{category.lower()}", result)
            return result
        except Exception:
            if attempt < attempts - 1:
                await asyncio.sleep(0.6 * (attempt + 1))
    _cache_set(f"quiz:{category.lower()}", fallback)
    return fallback


async def generate_english_questions(topic: str) -> list[str]:
    prompt = f'Topic: {topic[:200]}\nOutput schema: ["question1","question2","question3","question4","question5"]'
    fallback = [
        f"What is your perspective on {topic}?",
        "What are the key opportunities and risks?",
        "How does this affect society in the long term?",
        "What real example supports your argument?",
        "What should leaders do next?",
    ]
    cached = _cache_get(f"english_questions:{topic.lower()[:80]}")
    if cached is not None:
        return cached
    attempts = max(1, settings.llm_retry_count + 1)
    adapter = TypeAdapter(list[str])
    for attempt in range(attempts):
        try:
            response = await complete_with_fallback(
                prompt=prompt,
                system="Return strict JSON array only.",
                models=_MODELS,
                timeout_s=settings.llm_timeout_s,
                temperature=settings.llm_temperature,
                top_p=settings.llm_top_p,
            )
            parsed = adapter.validate_python(json.loads((response.text if response else "").strip()))
            if len(parsed) >= 5:
                _cache_set(f"english_questions:{topic.lower()[:80]}", parsed[:5])
                return parsed[:5]
        except Exception:
            if attempt < attempts - 1:
                await asyncio.sleep(0.6 * (attempt + 1))
    _cache_set(f"english_questions:{topic.lower()[:80]}", fallback)
    return fallback


async def generate_final_report(history: list) -> dict:
    prompt = (
        f"Transcript: {json.dumps(history)[:1400]}\n"
        'Output schema: {"overall_score":0-100,"technical_rating":0-100,"communication_rating":0-100,'
        '"brutal_feedback":"...","ready_for_senior_role":true|false}'
    )
    fallback = FinalReport(
        overall_score=55,
        technical_rating=55,
        communication_rating=55,
        brutal_feedback="Session completed. Keep improving clarity, structure, and depth.",
        ready_for_senior_role=False,
    )
    result = await _llm_json_call(
        cache_key=f"final_report:{json.dumps(history)[:120]}",
        prompt=prompt,
        schema=FinalReport,
        fallback=fallback,
    )
    return result.model_dump()


async def generate_chat_feedback(question: str, answer: str, context: str) -> tuple[str, int]:
    prompt = (
        f"Question: {question}\n"
        f"Answer: {answer}\n"
        f"Context: {context[:400]}\n"
        'Output schema: {"reply":"2-4 lines feedback","readiness_score":0-100}'
    )
    fallback = ChatFeedback(reply="Good attempt. Add more detail and structure.", readiness_score=55)
    result = await _llm_json_call(
        cache_key=f"chat:{question[:80]}:{answer[:80]}",
        prompt=prompt,
        schema=ChatFeedback,
        fallback=fallback,
    )
    return result.reply, result.readiness_score
