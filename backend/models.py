from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import JSONB  # PostgreSQL specific optimized JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime
# Use absolute imports for Docker compatibility
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
    mock_sessions = relationship("MockSession", back_populates="candidate", cascade="all, delete-orphan")
    english_sessions = relationship("EnglishSession", back_populates="candidate", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_user_id_created_at", "user_id", "created_at"),
        Index("ix_refresh_tokens_token_hash", "token_hash"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="refresh_tokens")

class Interview(Base):
    __tablename__ = "interviews"
    __table_args__ = (
        Index("ix_interviews_user_id_created_at", "user_id", "created_at"),
        Index("ix_interviews_session_id", "session_id"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(64), nullable=True, unique=True)
    
    role = Column(String(100), index=True)
    candidate_name = Column(String(120), nullable=True)
    status = Column(String(32), default="starting", nullable=False)
    current_question = Column(Integer, default=0, nullable=False)
    resume_context = Column(Text, nullable=True)
    overall_score = Column(Float)
    brutal_feedback = Column(Text) # Large text storage
    # JSONB in Postgres, JSON elsewhere (SQLite-friendly for tests/dev).
    transcript = Column(JSON().with_variant(JSONB, "postgresql"))
    
    had_pivot = Column(Boolean, default=True) # 8+5 sequence marker
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    candidate = relationship("User", back_populates="interviews")

class MockTest(Base):
    __tablename__ = "mock_tests"
    __table_args__ = (
        Index("ix_mock_tests_user_id_created_at", "user_id", "created_at"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    category = Column(String(50), index=True)
    score = Column(Integer)
    total_questions = Column(Integer, default=20)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    candidate = relationship("User", back_populates="mocks")

class MockSession(Base):
    __tablename__ = "mock_sessions"
    __table_args__ = (
        Index("ix_mock_sessions_user_id_created_at", "user_id", "created_at"),
        Index("ix_mock_sessions_session_id", "session_id"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(64), nullable=True, unique=True)
    
    session_type = Column(String(32), default="mock_test", nullable=False)  # mock_test, practice, etc.
    category = Column(String(50), index=True)
    score = Column(Integer)
    total_questions = Column(Integer, default=20)
    correct_answers = Column(Integer, default=0)
    
    # JSON data for questions and answers
    questions = Column(JSON().with_variant(JSONB, "postgresql"))
    answers = Column(JSON().with_variant(JSONB, "postgresql"))
    
    status = Column(String(32), default="in_progress", nullable=False)  # in_progress, completed, abandoned
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    abandoned_at = Column(DateTime(timezone=True), nullable=True)
    
    candidate = relationship("User", back_populates="mock_sessions")


class GlobalMock(Base):
    __tablename__ = "global_mocks"
    __table_args__ = (Index("ix_global_mocks_created_at", "created_at"),)

    id = Column(Integer, primary_key=True, index=True)
    questions = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RagStatus(Base):
    __tablename__ = "rag_status"
    __table_args__ = (
        Index("ix_rag_status_user_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    status = Column(String(16), default="processing", nullable=False)
    message = Column(String(255), default="Resume embedding in progress", nullable=False)
    chunks = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CacheEntry(Base):
    __tablename__ = "cache_entries"
    __table_args__ = (
        Index("ix_cache_entries_key", "key"),
        Index("ix_cache_entries_expires_at", "expires_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False)
    value_json = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EnglishSession(Base):
    __tablename__ = "english_sessions"
    __table_args__ = (
        Index("ix_english_sessions_user_id_created_at", "user_id", "created_at"),
        Index("ix_english_sessions_session_id", "session_id"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(64), nullable=True, unique=True)
    
    topic = Column(String(255))
    grammar_score = Column(Integer)
    vocab_score = Column(Integer)
    fluency_score = Column(Integer)
    rating = Column(String(10)) 
    critique = Column(Text)
    
    # Session tracking fields
    status = Column(String(32), default="in_progress", nullable=False)  # in_progress, completed, abandoned
    interactions = Column(JSON().with_variant(JSONB, "postgresql"))  # Store conversation history
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    abandoned_at = Column(DateTime(timezone=True), nullable=True)
    
    candidate = relationship("User", back_populates="english_sessions")

class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        Index("ix_attendance_user_id_date", "user_id", "date"),
    )
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(DateTime(timezone=True), server_default=func.now())