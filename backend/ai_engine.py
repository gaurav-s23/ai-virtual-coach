import os
import json
import asyncio
import re
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Use 1.5-flash for maximum reliability on free tier quotas
GEMINI_MODEL = "gemini-2.5-flash" 
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# =========================
# 🧠 CORE AI ENGINE
# =========================
async def call_gemini(prompt, system_instruction=""):
    """
    Neural Engine Wrapper. Handles retries and system instructions.
    """
    try:
        # We use asyncio.to_thread to keep the FastAPI event loop non-blocking
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=GEMINI_MODEL,
            config={
                "system_instruction": system_instruction,
                "temperature": 0.7,
                "top_p": 0.95,
            },
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"❌ NEURAL ENGINE ERROR: {str(e)}")
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
    raw = await call_gemini(prompt, system)
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
    raw = await call_gemini(prompt, system)
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
    raw = await call_gemini(prompt, system)
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
    raw = await call_gemini(prompt, system)
    return clean_json_response(raw)