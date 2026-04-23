from __future__ import annotations

import hashlib
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

try:
    import models
    from database import get_db
except ImportError as e:
    logger.error(f"Import error in auth/security.py: {e}")
    # Fallback imports for development
    try:
        import models
        from database import get_db
    except ImportError as fallback_error:
        logger.error(f"Fallback import error in auth/security.py: {fallback_error}")
        raise SystemExit(f"Failed to import required modules in auth/security.py: {fallback_error}")


# Argon2 is the primary scheme. Keep bcrypt enabled for verifying legacy hashes.
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_rate_limit_key(request: Request) -> str:
    """
    Build a combined rate-limit key of user_id + IP address.

    Uses request.state.user_id when available (set by auth dependency),
    otherwise falls back to "anon".
    """
    user_id = request.state.user_id if hasattr(request.state, "user_id") else "anon"
    ip = request.client.host if request.client else "unknown"
    return f"{user_id}:{ip}"


def _jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        raise RuntimeError("JWT_SECRET_KEY is not set.")
    return secret


def _jwt_algorithm() -> str:
    return os.getenv("JWT_ALGORITHM", "HS256")


def _access_exp_minutes() -> int:
    return int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


def _refresh_exp_days() -> int:
    return int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def validate_password_length(password: str) -> None:
    """
    Prevent pathological password sizes (DoS guard).

    Argon2 does not have bcrypt's 72-byte limit, but we still cap input size to a
    sane maximum to avoid excessive CPU/memory usage during hashing/verification.
    """
    if password is None:
        raise ValueError("Password is required")
    if len(password.encode("utf-8")) > 1024:
        raise ValueError("Password too long (max 1024 bytes)")


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2."""
    validate_password_length(password)
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_access_token(*, user_id: int, role: str = "user") -> str:
    """Create a JWT access token."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=_access_exp_minutes())
    payload = {"sub": str(user_id), "type": "access", "role": role, "iat": int(now.timestamp()), "exp": exp}
    return jwt.encode(payload, _jwt_secret(), algorithm=_jwt_algorithm())


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, _jwt_secret(), algorithms=[_jwt_algorithm()])
    if payload.get("type") != "access" or not payload.get("sub"):
        raise JWTError("Invalid access token")
    return payload


def _new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """Hash refresh token for DB storage (never store refresh token plaintext)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 60 * 30


def issue_token_pair(*, db: Session, user: "models.User") -> TokenPair:
    """Issue access+refresh tokens and persist refresh token hash in DB."""
    access = create_access_token(user_id=user.id)
    refresh = _new_refresh_token()
    now = datetime.now(timezone.utc)
    refresh_exp = now + timedelta(days=_refresh_exp_days())

    rt = models.RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh),
        expires_at=refresh_exp,
        revoked=False,
        created_at=now,
    )
    db.add(rt)
    db.commit()
    return TokenPair(access_token=access, refresh_token=refresh, expires_in=_access_exp_minutes() * 60)


def rotate_refresh_token(*, db: Session, user: "models.User", refresh_token: str) -> TokenPair:
    """Rotate refresh token (revoke old, issue new)."""
    token_hash = hash_refresh_token(refresh_token)
    now = datetime.now(timezone.utc)
    row = (
        db.query(models.RefreshToken)
        .filter(models.RefreshToken.user_id == user.id)
        .filter(models.RefreshToken.token_hash == token_hash)
        .filter(models.RefreshToken.revoked.is_(False))
        .first()
    )
    if not row or (row.expires_at is not None and row.expires_at < now):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    row.revoked = True
    row.revoked_at = now
    db.add(row)
    db.commit()

    return issue_token_pair(db=db, user=user)


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> "models.User":
    """Resolve the current user from a JWT access token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[_jwt_algorithm()])
        if payload.get("type") != "access":
            raise credentials_exception
        sub = payload.get("sub")
        if not sub:
            raise credentials_exception
        user_id = int(sub)
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    # Expose user_id for rate-limiting key function.
    request.state.user_id = str(user.id)
    return user

