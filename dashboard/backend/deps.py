"""FastAPI dependency providers: auth guard + in-flight build guard."""
from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, Request, status

from dashboard.backend.config import settings
from dashboard.backend.security import verify_session_token


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

def require_auth(
    request: Request,
    session: str | None = Cookie(default=None, alias=None),
) -> None:
    """Raise 401 if the request has no valid session cookie.

    The cookie name is dynamic (from settings), so we read it from the
    request cookies dict directly rather than relying on the FastAPI Cookie
    annotation alias (which cannot be set at declaration time from a setting).
    """
    cookie_val = request.cookies.get(settings.session_cookie_name)
    if not cookie_val or not verify_session_token(cookie_val):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Cookie"},
        )


# ---------------------------------------------------------------------------
# In-flight build guard (used by /api/control/restart)
# ---------------------------------------------------------------------------

def _has_inflight_build() -> bool:
    """Return True if any task is in a live status OR workshop_build.py is running."""
    import subprocess
    from pathlib import Path

    # Check state files
    tasks_base = Path(settings.tasks_base)
    live_statuses = {
        "running",
        "needs_clarification",
        "needs_timeout_recovery",
        "needs_review_recovery",
        "needs_step_recovery",
        "needs_approval",
        "pushing",
    }
    if tasks_base.exists():
        import json

        for state_file in tasks_base.glob("*/state.json"):
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
                if data.get("status") in live_statuses:
                    return True
            except Exception:
                continue

    # pgrep check
    try:
        result = subprocess.run(
            ["pgrep", "-u", "uws", "-f", "workshop_build.py"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True
    except Exception:
        pass

    return False


def check_no_inflight(force: bool = False) -> None:
    """Raise 409 if a build is in-flight and *force* is not set."""
    if not force and _has_inflight_build():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A build is currently in flight. Pass force=true to override.",
        )
