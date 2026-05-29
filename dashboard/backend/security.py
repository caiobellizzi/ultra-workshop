"""Session-cookie authentication helpers.

Uses secrets.compare_digest for timing-safe comparison.
Cookie is HttpOnly + SameSite=Strict.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Optional

from fastapi import Cookie, HTTPException, Request, Response, status

from dashboard.backend.config import settings

# Token TTL: 8 hours in seconds
SESSION_TTL = 8 * 3600
_ALGORITHM = "sha256"


def _sign(value: str, secret: str) -> str:
    """Return an HMAC-SHA256 hex digest of *value*."""
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def create_session_token(payload: str = "authenticated") -> str:
    """Create a signed session token: '<timestamp>.<payload>.<signature>'."""
    ts = str(int(time.time()))
    raw = f"{ts}.{payload}"
    sig = _sign(raw, settings.cookie_secret)
    return f"{raw}.{sig}"


def verify_session_token(token: str) -> bool:
    """Return True iff the token signature is valid and not expired."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return False
        ts_str, payload, provided_sig = parts
        raw = f"{ts_str}.{payload}"
        expected_sig = _sign(raw, settings.cookie_secret)
        if not secrets.compare_digest(provided_sig, expected_sig):
            return False
        ts = int(ts_str)
        if time.time() - ts > SESSION_TTL:
            return False
        return True
    except Exception:
        return False


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        samesite="strict",
        max_age=SESSION_TTL,
        secure=settings.secure_cookie,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.session_cookie_name)


def check_token_header(request: Request) -> bool:
    """Check bearer token from Authorization header (optional auth layer)."""
    if not settings.api_token:
        return True  # no token configured — skip
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    provided = auth.removeprefix("Bearer ").strip()
    return secrets.compare_digest(provided, settings.api_token)
