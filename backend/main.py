import os
import json
import io
import re
import asyncio
import traceback
import hashlib
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import PyPDF2
from pydantic import BaseModel

# --- IMPORT FROM YOUR AI_ENGINE.PY ---
from ai_engine import (
    generate_initial_interview, 
    generate_pivot_deepdives, 
    generate_neural_quiz, 
    generate_final_report,
    call_gemini,
    clean_json_response
)

# Local database imports
import models
import database
from database import engine, get_db
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ai_virtual_coach Neural API")

origins = [
    "http://localhost:5173",    # Tera local Vite frontend
    "http://127.0.0.1:5173",    # Alternate local IP
    # "https://your-frontend.vercel.app", # Baad mein yahan Vercel ka link dalna
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # Sirf inhi origins ko allow karega
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
models.Base.metadata.create_all(bind=engine)

# =========================
# 🔐 SCHEMAS
# =========================
class LoginRequest(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    answer: str
    question: str
    context: str = ""

class PivotRequest(BaseModel):
    history: list
    context: str
    role: str

class QuizRequest(BaseModel):
    category: str 

class StatsUpdate(BaseModel):
    score: int
    type: str 

# =========================
# 📄 PDF UTILS
# =========================
def extract_text_from_pdf_bytes(file_bytes):
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = " ".join([p.extract_text() for p in pdf_reader.pages if p.extract_text()])
        return text.strip()
    except:
        return ""

def extract_text_from_local_pdf(file_path):
    try:
        with open(file_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text = " ".join([p.extract_text() for p in pdf_reader.pages if p.extract_text()])
            return text.strip()
    except:
        return ""

# =========================
# 🎤 INTERVIEW MODULE (8+5 LOGIC)
# =========================

@app.post("/api/start-interview")
async def start_interview(
    resume: UploadFile = File(...),
    jd: str = Form(""),
    role: str = Form("Software Engineer"),
):
    try:
        content = await resume.read()
        resume_text = extract_text_from_pdf_bytes(content)
        
        # Call the refactored engine
        data = await generate_initial_interview(resume_text, jd, role)
        
        if not data:
            raise HTTPException(status_code=500, detail="AI Node failed to respond.")

        return {
            "status": "success",
            "intro": data.get("intro"),
            "questions": data.get("questions"),
            "context": resume_text[:1500] 
        }
    except:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Interview initialization failed")

@app.post("/api/interview/chat")
async def interview_chat(data: ChatRequest):
    # Short Turn Feedback logic
    prompt = f"Context: {data.context}\nQuestion: {data.question}\nAnswer: {data.answer}\nTask: Give 2-line brutal feedback."
    reply = await call_gemini(prompt, "You are a brutal recruiter. Focus on accuracy.")
    return {"reply": reply or "Weak signal. Rephrase."}

@app.post("/api/interview/pivot")
async def interview_pivot(data: PivotRequest):
    # Using 8+5 Logic helper from engine
    result = await generate_pivot_deepdives(data.history, data.role, data.context)
    if not result:
        raise HTTPException(status_code=500, detail="Pivot logic failed.")
    return result

# =========================
# 📝 MOCK TEST (Zero-Upload)
# =========================

@app.post("/api/generate-quiz")
async def generate_quiz(data: QuizRequest):
    category = data.category.lower()
    pdf_path = f"./data/{category}.pdf"
    
    text = ""
    if os.path.exists(pdf_path):
        text = extract_text_from_local_pdf(pdf_path)

    # Uses the fail-safe logic in generate_neural_quiz (If text empty, AI uses knowledge)
    quiz_data = await generate_neural_quiz(text, data.category)
    
    if not quiz_data:
        raise HTTPException(status_code=500, detail="Assessment synthesis failed.")
    
    return quiz_data

# =========================
# 📚 ENGLISH PRACTICE (5+5 LOGIC)
# =========================

@app.get("/api/english/topic")
async def get_english_topic():
    topic = await call_gemini("Generate 1 advanced discussion topic for English speaking practice. 1 line.")
    return {"topic": topic.strip() if topic else "Modern Leadership Ethics"}

@app.post("/api/english/questions")
async def get_english_questions(data: dict):
    topic = data.get("topic")
    prompt = f"Topic: {topic}. Generate 5 primary discussion questions. Return JSON list of strings."
    raw = await call_gemini(prompt, "Return ONLY JSON.")
    return {"questions": clean_json_response(raw)}

@app.post("/api/english/report")
async def english_report(data: dict):
    # Using report helper from engine
    return await generate_final_report(data.get("history"))

# =========================
# 📊 PERSISTENT DASHBOARD
# =========================

@app.get("/api/user/stats/{user_id}")
async def get_stats(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(status_code=404)
    return {
        "readiness": user.readiness_score,
        "interviews": user.total_interviews,
        "mocks": user.total_mocks,
        "streak": user.streak_count,
        "email": user.email
    }

@app.post("/api/user/update-stats/{user_id}")
async def update_stats(user_id: int, data: StatsUpdate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        if data.type == "interview":
            user.total_interviews += 1
            user.readiness_score = min(100, user.readiness_score + 3)
        else:
            user.total_mocks += 1
            user.readiness_score = min(100, user.readiness_score + 1)
        db.commit()
    return {"status": "ok"}

# =========================
# 🔐 AUTH
# =========================

@app.post("/api/login")
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    hashed = hashlib.sha256(data.password.encode()).hexdigest()
    user = db.query(models.User).filter(models.User.email == data.email).first()

    if not user:
        # Initial user config to prevent Dashboard crashes
        new_user = models.User(
            email=data.email, 
            password=hashed, 
            name="Candidate", 
            readiness_score=45, 
            total_interviews=0, 
            total_mocks=0,
            streak_count=1
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"user": {"id": new_user.id, "email": new_user.email}}
    
    if user.password == hashed:
        return {"user": {"id": user.id, "email": user.email}}
    
    raise HTTPException(status_code=400, detail="Invalid Credentials")

@app.get("/")
def root():
    return {"message": "Neural Core Synced with Engine v2.5"}