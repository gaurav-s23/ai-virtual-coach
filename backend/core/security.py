from __future__ import annotations

import logging
from fastapi import Depends, HTTPException
from jose import jwt

logger = logging.getLogger(__name__)

try:
    from auth.security import (
        get_current_user,
        oauth2_scheme,
        issue_token_pair,
        rotate_refresh_token,
        hash_password,
        verify_password,
        validate_password_length,
        get_rate_limit_key,
        TokenPair,
    )
except ImportError as e:
    logger.error(f"Import error in core/security.py: {e}")
    # Fallback imports for development
    try:
        from auth.security import (
            get_current_user,
            oauth2_scheme,
            issue_token_pair,
            rotate_refresh_token,
            hash_password,
            verify_password,
            validate_password_length,
            get_rate_limit_key,
            TokenPair,
        )
    except ImportError as fallback_error:
        logger.error(f"Fallback import error in core/security.py: {fallback_error}")
        raise SystemExit(f"Failed to import required modules in core/security.py: {fallback_error}")


def get_admin_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        return payload
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid admin token")


def _jwt_secret() -> str:
    try:
        from auth.security import _jwt_secret as jwt_secret
    except Exception:
        from auth.security import _jwt_secret as jwt_secret  # type: ignore
    return jwt_secret()
