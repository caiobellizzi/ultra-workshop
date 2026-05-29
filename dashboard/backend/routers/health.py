"""Health check endpoint."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

from dashboard.backend.config import settings
from dashboard.backend.deps import require_auth
from dashboard.backend.models.api_models import HealthResponse, ServiceStatus

router = APIRouter(prefix="/api", tags=["health"])


def _check_hermes_service() -> ServiceStatus:
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "uws-hermes.service"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        active = result.stdout.strip() == "active"
        return ServiceStatus(
            name="uws-hermes",
            ok=active,
            detail=result.stdout.strip(),
        )
    except FileNotFoundError:
        return ServiceStatus(name="uws-hermes", ok=True, detail="(dev mode)")
    except Exception as exc:
        return ServiceStatus(name="uws-hermes", ok=False, detail=str(exc))


def _check_litellm() -> ServiceStatus:
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:4001/health", timeout=3) as resp:
            ok = resp.status == 200
        return ServiceStatus(name="litellm", ok=ok)
    except Exception as exc:
        return ServiceStatus(name="litellm", ok=False, detail=str(exc))


def _check_spend_db() -> ServiceStatus:
    db_path = Path(settings.spend_db)
    ok = db_path.exists() or True  # always ok — will be created on first write
    return ServiceStatus(name="spend-db", ok=ok, detail=str(db_path))


def _queue_depth() -> int:
    """Count tasks currently in a live status."""
    import json

    live_statuses = {
        "running",
        "needs_clarification",
        "needs_timeout_recovery",
        "needs_review_recovery",
        "needs_step_recovery",
        "needs_approval",
        "pushing",
    }
    base = Path(settings.tasks_base)
    if not base.exists():
        return 0
    count = 0
    for sf in base.glob("*/state.json"):
        try:
            data = json.loads(sf.read_text(encoding="utf-8"))
            if data.get("status") in live_statuses:
                count += 1
        except Exception:
            continue
    return count


def _disk_free_gb() -> float:
    try:
        usage = shutil.disk_usage("/")
        return round(usage.free / (1024 ** 3), 2)
    except Exception:
        return 0.0


@router.get("/health", response_model=HealthResponse)
def health(_auth=Depends(require_auth)):
    services = [
        _check_hermes_service(),
        _check_litellm(),
        _check_spend_db(),
    ]
    all_ok = all(s.ok for s in services)
    return HealthResponse(
        ok=all_ok,
        services=services,
        queue_depth=_queue_depth(),
        disk_free_gb=_disk_free_gb(),
    )
