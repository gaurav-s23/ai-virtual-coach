from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB  # PostgreSQL specific optimized JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), default="Cadet")
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    
    # --- PERFORMANCE TRACKING (Dashboard Support) ---
    target_role = Column(String(100), default="Senior Software Architect")
    readiness_score = Column(Integer, default=45) 
    streak_count = Column(Integer, default=1)
    
    # --- COUNTERS ---
    total_interviews = Column(Integer, default=0)
    total_mocks = Column(Integer, default=0)
    total_english_sessions = Column(Integer, default=0)
    
    last_login = Column(DateTime(timezone=True), onupdate=func.now(), default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    interviews = relationship("Interview", back_populates="candidate", cascade="all, delete-orphan")
    mocks = relationship("MockTest", back_populates="candidate", cascade="all, delete-orphan")
    english_sessions = relationship("EnglishSession", back_populates="candidate", cascade="all, delete-orphan")

class Interview(Base):
    __tablename__ = "interviews"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    
    role = Column(String(100)) 
    overall_score = Column(Float)
    brutal_feedback = Column(Text) # Large text storage
    transcript = Column(JSONB) # Optimized JSON storage for search and performance
    
    had_pivot = Column(Boolean, default=True) # 8+5 sequence marker
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    candidate = relationship("User", back_populates="interviews")

class MockTest(Base):
    __tablename__ = "mock_tests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    
    category = Column(String(50)) 
    score = Column(Integer)
    total_questions = Column(Integer, default=20)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    candidate = relationship("User", back_populates="mocks")

class EnglishSession(Base):
    __tablename__ = "english_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    
    topic = Column(String(255))
    grammar_score = Column(Integer)
    vocab_score = Column(Integer)
    fluency_score = Column(Integer)
    rating = Column(String(10)) 
    critique = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    candidate = relationship("User", back_populates="english_sessions")

class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    date = Column(DateTime(timezone=True), server_default=func.now())