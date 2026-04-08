import os
import json
import asyncio
import re
import logging
from dotenv import load_dotenv

load_dotenv()

# Logger used by API + AI engine
logger = logging.getLogger("ai_virtual_coach.ai_engine")

try:
    # Package import
    from .llm.router import complete_with_fallback
except ImportError:
    # Local import (when running from backend/ dir)
    from llm.router import complete_with_fallback

# =========================
# 🧠 CORE AI ENGINE
# =========================
async def call_llm(prompt, system_instruction=""):
    """
    Neural Engine Wrapper (self-healing).
    Uses a tiered fallback strategy across providers via LiteLLM.
    """
    try:
        result = await complete_with_fallback(
            prompt=prompt,
            system=system_instruction or None,
            timeout_s=float(os.getenv("LLM_TIMEOUT_S", "30")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            top_p=float(os.getenv("LLM_TOP_P", "0.95")),
        )
        return result.text if result else None
    except Exception as e:
        logger.exception("LLM call failed: %s", str(e))
        return None

def clean_json_response(raw_text):
    """
    Uses Regex to extract JSON from AI markdown blocks safely.
    """
    try:
        json_match = re.search(r'\[.*\]|\{.*\}', raw_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return None
    except:
        return None

# =========================
# 🎤 INTERVIEW MODULE
# =========================
async def generate_initial_interview(resume_text, jd_text, role):
    system = "You are a Principal Technical Recruiter. Return ONLY JSON."
    prompt = f"""
    Target Role: {role}
    Resume: {resume_text[:1500]}
    JD: {jd_text[:1000]}

    Task:
    Generate a short professional intro and 10 high-context questions.
    
    JSON Format:
    {{
      "intro": "2-line simulation initialization message",
      "questions": ["q1", "q2", ..., "q10"]
    }}
    """
    raw = await call_llm(prompt, system)
    return clean_json_response(raw)

async def generate_pivot_deepdives(history, role, context):
    """
    ROADMAP A: The 8+5 Logic Pivot
    """
    system = "You are a Senior Principal Engineer. Analyze and Probe. Return ONLY JSON."
    prompt = f"""
    The candidate is applying for {role}. 
    Based on their first 8 answers: {json.dumps(history)}
    
    1. Identify 'shaky' technical claims or weaknesses.
    2. Generate 5 brutal, deep-dive follow-up questions to test their true depth.

    JSON Format:
    {{
      "analysis": "1-line summary of weakness found",
      "deep_dives": ["q1", "q2", "q3", "q4", "q5"]
    }}
    """
    raw = await call_llm(prompt, system)
    return clean_json_response(raw)

# =========================
# 📝 MOCK TEST GENERATOR
# =========================
async def generate_neural_quiz(pdf_text, category):
    system = "You are an Elite Exam Controller. Return ONLY JSON."
    
    # Fail-safe: If pdf_text is empty, Gemini generates from its own knowledge
    context_type = "TEXT_BASED" if len(pdf_text) > 100 else "KNOWLEDGE_BASED"
    
    prompt = f"""
    Category: {category}
    Mode: {context_type}
    Reference Text: {pdf_text[:3000]}

    Task: Generate 20 high-quality MCQs.
    Include 5 Easy, 10 Medium, 5 Hard questions.

    JSON Format:
    [
      {{
        "id": 1,
        "question": "...",
        "options": ["A", "B", "C", "D"],
        "answer": "The Correct String"
      }}
    ]
    """
    raw = await call_llm(prompt, system)
    return clean_json_response(raw)

# =========================
# 📊 FINAL PERFORMANCE REPORT
# =========================
async def generate_final_report(history):
    system = "You are a Brutally Honest Interviewer. No sugarcoating. Return ONLY JSON."
    prompt = f"""
    Analyze this transcript: {json.dumps(history)}
    
    JSON Format:
    {{
      "overall_score": 0-100,
      "technical_rating": 0-100,
      "communication_rating": 0-100,
      "brutal_feedback": "3 sentences detailing why they would or would not be hired.",
      "ready_for_senior_role": true/false
    }}
    """
    raw = await call_llm(prompt, system)
    return clean_json_response(raw)