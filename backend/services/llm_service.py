from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from typing import Any
import os
from datetime import datetime, timezone, timedelta

from pydantic import BaseModel, Field, ValidationError, TypeAdapter

logger = logging.getLogger(__name__)

try:
    from core.config import get_settings
    from llm.router import complete_with_fallback, get_fallback_models
    from database import SessionLocal
    import models
except ImportError as e:
    logger.error(f"Import error in llm_service.py: {e}")
    # Fallback imports for development
    try:
        from core.config import get_settings
        from llm.router import complete_with_fallback, get_fallback_models
        from database import SessionLocal
        import models
    except ImportError as fallback_error:
        logger.error(f"Fallback import error in llm_service.py: {fallback_error}")
        raise SystemExit(f"Failed to import required modules in llm_service.py: {fallback_error}")
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


def _hash(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:32]

def _cache_key_with_user(prefix: str, user_id: int, *values: str) -> str:
    """Generate cache key that includes user context to prevent cross-user collisions"""
    key_parts = [prefix, str(user_id)] + [v or "" for v in values]
    return ":".join(key_parts)


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
        cache_key=f"interview:{_hash(role)}:{_hash(resume_text)}:{_hash(jd_text)}",
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
        cache_key=f"pivot:{_hash(role)}:{_hash(json.dumps(history))}:{_hash(context)}",
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
    # Natural conversational prompt for "Baat-chit" style English practice
    prompt = f'''
    Topic: {topic[:200]}
    
    Generate 5 natural, conversational questions for English speaking practice. 
    These should feel like a friendly chat, not a formal interview.
    Make them open-ended and encouraging.
    
    Style: Natural conversation ("Baat-chit" style)
    Tone: Friendly, encouraging, conversational
    Avoid: Formal, academic, or overly complex questions
    
    Output schema: ["question1","question2","question3","question4","question5"]
    
    Examples of good style:
    - "So, what are your thoughts on..."
    - "Tell me about a time when..."
    - "How do you feel about..."
    - "What's your take on..."
    - "I'd love to hear your perspective on..."
    '''
    
    fallback = [
        f"So, what are your thoughts on {topic}? I'd love to hear your perspective.",
        "That's interesting! Can you share a personal experience related to this?",
        "How do you feel this impacts our daily lives? Tell me more.",
        "What's something people often misunderstand about this topic?",
        "If you could give one piece of advice on this, what would it be?",
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
        cache_key=f"final_report:{_hash(json.dumps(history))}",
        prompt=prompt,
        schema=FinalReport,
        fallback=fallback,
    )
    return result.model_dump()


async def generate_chat_feedback(question: str, answer: str, context: str) -> tuple[str, int]:
    # Natural conversational feedback for English practice
    prompt = f'''
    Question: {question}
    Answer: {answer}
    Context: {context[:400]}
    
    Generate friendly, encouraging feedback for English speaking practice.
    This should feel like a supportive conversation partner, not a strict evaluator.
    
    Style: Natural, encouraging, conversational ("Baat-chit" style)
    Tone: Supportive, friendly, helpful
    Focus: Encouragement and gentle suggestions
    
    Output schema: {{"reply":"2-4 friendly, encouraging lines","readiness_score":0-100}}
    
    Examples of good feedback style:
    - "That's a great point! I really like how you..."
    - "Nice! You could also try adding..."
    - "Wonderful! Your pronunciation is clear, and..."
    - "Good job! To make it even better, maybe..."
    '''
    
    fallback = ChatFeedback(reply="That's a great start! I can see you're thinking about this carefully. Keep up the good work!", readiness_score=65)
    result = await _llm_json_call(
        cache_key=f"chat:{_hash(question)}:{_hash(answer)}:{_hash(context)}",
        prompt=prompt,
        schema=ChatFeedback,
        fallback=fallback,
    )
    return result.reply, result.readiness_score
