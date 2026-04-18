from __future__ import annotations

from fastapi import Depends, HTTPException
from jose import jwt

try:
    from ..auth.security import (
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
except ImportError:
    from auth.security import (  # type: ignore
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
        from ..auth.security import _jwt_secret as jwt_secret  # type: ignore
    except Exception:
        from auth.security import _jwt_secret as jwt_secret  # type: ignore
    return jwt_secret()
