from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Configure logger
logger = logging.getLogger(__name__)

try:
    from models import User
    from database import get_db
    from core.security import (
        get_current_user,
        hash_password,
        issue_token_pair,
        rotate_refresh_token,
        validate_password_length,
        verify_password,
    )
    from auth.security import hash_refresh_token
    from routes.schemas import LoginLegacyResponse, LoginRequest, MeResponse, RefreshRequest, SignupRequest, TokenResponse
except ImportError as e:
    logger.error(f"Import error in auth.py: {e}")
    # Fallback imports for development
    try:
        import models
        from database import get_db
        from core.security import (
            get_current_user,
            hash_password,
            issue_token_pair,
            rotate_refresh_token,
            validate_password_length,
            verify_password,
        )
        from auth.security import hash_refresh_token
        from routes.schemas import LoginLegacyResponse, LoginRequest, MeResponse, RefreshRequest, SignupRequest, TokenResponse
    except ImportError as fallback_error:
        logger.error(f"Fallback import error in auth.py: {fallback_error}")
        raise SystemExit(f"Failed to import required modules in auth.py: {fallback_error}")

router = APIRouter(prefix="/api", tags=["Auth"])


@router.post("/login", response_model=LoginLegacyResponse)
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    email = (data.email or "").strip().lower()
    validate_password_length(data.password)
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid input")
    tokens = issue_token_pair(db=db, user=user)
    return {
        "user": {"id": user.id, "email": user.email, "name": user.name},
        "token": tokens.access_token,
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": tokens.token_type,
        "expires_in": tokens.expires_in,
    }


@router.post("/auth/signup", status_code=status.HTTP_201_CREATED, response_model=MeResponse)
async def auth_signup(data: SignupRequest, db: Session = Depends(get_db)):
    email = (data.email or "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="Invalid input")
    validate_password_length(data.password)
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Invalid input")
    user = models.User(
        email=email,
        password=hash_password(data.password),
        name=(data.name or "Candidate").strip()[:100],
        readiness_score=45,
        total_interviews=0,
        total_mocks=0,
        streak_count=1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "name": user.name}


@router.post("/auth/login", response_model=LoginLegacyResponse)
async def auth_login(data: LoginRequest, db: Session = Depends(get_db)):
    email = (data.email or "").strip().lower()
    validate_password_length(data.password)
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid input")
    tokens = issue_token_pair(db=db, user=user)
    return {
        "user": {"id": user.id, "email": user.email, "name": user.name},
        "token": tokens.access_token,
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": tokens.token_type,
        "expires_in": tokens.expires_in,
    }


@router.post("/auth/refresh", response_model=TokenResponse)
async def auth_refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    token_hash = hash_refresh_token(data.refresh_token)
    row = db.query(models.RefreshToken).filter(models.RefreshToken.token_hash == token_hash).first()
    if not row:
        raise HTTPException(status_code=401, detail="Invalid input")
    user = db.query(models.User).filter(models.User.id == row.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid input")
    tokens = rotate_refresh_token(db=db, user=user, refresh_token=data.refresh_token)
    return tokens.__dict__


@router.get("/auth/me", response_model=MeResponse)
async def auth_me(current_user: "models.User" = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "name": current_user.name}
