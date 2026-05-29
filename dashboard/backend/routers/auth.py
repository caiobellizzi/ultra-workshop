"""Auth endpoints: login, logout."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, Response, status

from dashboard.backend.config import settings
from dashboard.backend.models.api_models import LoginRequest, LoginResponse
from dashboard.backend.security import clear_session_cookie, create_session_token, set_session_cookie

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, response: Response):
    """Authenticate with the dashboard password (cookie_secret).

    In production, the cookie_secret is set via UWS_DASH_COOKIE_SECRET env var.
    """
    if not secrets.compare_digest(body.password, settings.cookie_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )
    token = create_session_token()
    set_session_cookie(response, token)
    return LoginResponse(ok=True)


@router.post("/logout")
def logout(response: Response):
    clear_session_cookie(response)
    return {"ok": True}
