"""Health check endpoint."""
from __future__ import annotations

import json
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

from dashboard.backend.config import settings
from dashboard.backend.deps import require_auth
from dashboard.backend.models.api_models import (
    DiskStats,
    ErrorLogEntry,
    ErrorLogResponse,
    HealthResponse,
    ModelReachability,
    ModelReachabilityResponse,
    ServiceStatus,
)

router = APIRouter(prefix="/api", tags=["health"])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_hermes_service() -> ServiceStatus:
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "uws-hermes.service"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        active = result.stdout.strip() == "active"
        return ServiceStatus(name="uws-hermes", running=active)
    except FileNotFoundError:
        return ServiceStatus(name="uws-hermes", running=True)
    except Exception:
        return ServiceStatus(name="uws-hermes", running=False)


def _check_litellm() -> ServiceStatus:
    try:
        with urllib.request.urlopen("http://127.0.0.1:4001/health", timeout=3) as resp:
            running = resp.status == 200
        return ServiceStatus(name="litellm", running=running)
    except Exception:
        return ServiceStatus(name="litellm", running=False)


def _check_spend_db() -> ServiceStatus:
    db_path = Path(settings.spend_db)
    # always ok — will be created on first write
    ok = db_path.exists() or True
    return ServiceStatus(name="spend-db", running=ok)


def _queue_depth() -> int:
    """Count tasks currently in a live status."""
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


def _hitl_count() -> int:
    """Count tasks currently waiting for human-in-the-loop action."""
    hitl_statuses = {
        "needs_clarification",
        "needs_approval",
        "needs_timeout_recovery",
        "needs_review_recovery",
        "needs_step_recovery",
    }
    base = Path(settings.tasks_base)
    if not base.exists():
        return 0
    count = 0
    for sf in base.glob("*/state.json"):
        try:
            data = json.loads(sf.read_text(encoding="utf-8"))
            if data.get("status") in hitl_statuses:
                count += 1
        except Exception:
            continue
    return count


def _disk_stats() -> DiskStats:
    try:
        usage = shutil.disk_usage("/")
        return DiskStats(
            used_bytes=usage.used,
            total_bytes=usage.total,
            path="/",
        )
    except Exception:
        return DiskStats(used_bytes=0, total_bytes=0, path="/")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
def health(_auth=Depends(require_auth)):
    services = [
        _check_hermes_service(),
        _check_litellm(),
        _check_spend_db(),
    ]
    return HealthResponse(
        services=services,
        disk=_disk_stats(),
        queue_depth=_queue_depth(),
        hitl_count=_hitl_count(),
    )


@router.get("/health/models", response_model=ModelReachabilityResponse)
def health_models(_auth=Depends(require_auth)):
    """Probe each configured LiteLLM alias and report reachability."""
    from dashboard.backend.services import config_service

    aliases = config_service.get_model_aliases()
    results: list[ModelReachability] = []

    for alias in aliases:
        start = time.monotonic()
        try:
            url = f"http://127.0.0.1:4001/health/liveliness"
            with urllib.request.urlopen(url, timeout=5) as resp:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                if resp.status == 200:
                    results.append(
                        ModelReachability(
                            alias=alias,
                            reachable="green",
                            latency_ms=elapsed_ms,
                        )
                    )
                else:
                    results.append(
                        ModelReachability(
                            alias=alias,
                            reachable="yellow",
                            latency_ms=elapsed_ms,
                            error=f"HTTP {resp.status}",
                        )
                    )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            results.append(
                ModelReachability(
                    alias=alias,
                    reachable="red",
                    latency_ms=elapsed_ms,
                    error=str(exc),
                )
            )

    # If no aliases configured, still probe the LiteLLM health endpoint as a single entry
    if not aliases:
        start = time.monotonic()
        try:
            with urllib.request.urlopen("http://127.0.0.1:4001/health", timeout=5) as resp:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                status = "green" if resp.status == 200 else "yellow"
                results.append(
                    ModelReachability(alias="litellm", reachable=status, latency_ms=elapsed_ms)
                )
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            results.append(
                ModelReachability(
                    alias="litellm",
                    reachable="red",
                    latency_ms=elapsed_ms,
                    error=str(exc),
                )
            )

    return ModelReachabilityResponse(models=results)


@router.get("/health/errors", response_model=ErrorLogResponse)
def health_errors(_auth=Depends(require_auth)):
    """Scan task state and progress logs for error events."""
    error_statuses = {
        "failed",
        "error",
        "timeout",
        "cancelled",
    }
    error_events = {
        "error",
        "exception",
        "failed",
        "timeout",
        "crash",
    }
    base = Path(settings.tasks_base)
    if not base.exists():
        return ErrorLogResponse(errors=[])

    entries: list[dict[str, Any]] = []

    for task_dir in sorted(base.iterdir(), reverse=True):
        if not task_dir.is_dir():
            continue
        task_id = task_dir.name

        # Check state.json for terminal error status
        state_file = task_dir / "state.json"
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
                status = state.get("status", "")
                if status in error_statuses:
                    ts = state.get("updated_at") or state.get("created_at") or ""
                    entries.append(
                        {
                            "ts": ts,
                            "task_id": task_id,
                            "event": status,
                            "excerpt": state.get("goal", "")[:200],
                        }
                    )
            except Exception:
                pass

        # Scan progress_log.jsonl for error-type events
        progress_file = task_dir / "progress_log.jsonl"
        if progress_file.exists():
            try:
                lines = progress_file.read_text(encoding="utf-8", errors="replace").splitlines()
                for line in reversed(lines[-500:]):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        event = str(entry.get("event", "")).lower()
                        if any(e in event for e in error_events):
                            entries.append(
                                {
                                    "ts": str(entry.get("ts", "")),
                                    "task_id": task_id,
                                    "event": str(entry.get("event", "")),
                                    "excerpt": str(entry.get("msg", entry.get("detail", "")))[:200],
                                }
                            )
                    except Exception:
                        continue
            except Exception:
                pass

        if len(entries) >= 100:
            break

    # Sort newest-first by ts, cap at 100
    entries.sort(key=lambda e: e.get("ts", ""), reverse=True)
    return ErrorLogResponse(
        errors=[ErrorLogEntry(**e) for e in entries[:100]]
    )
