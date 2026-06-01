"""Internal endpoints (no auth — loopback only).

/internal/spend-update: receives LiteLLM SPEND_LOGS_URL batches.
/internal/run-event:    receives pipeline stage/reviewer telemetry.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from dashboard.backend.services import cost_service, run_events

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/spend-update")
async def spend_update(request: Request):
    """Receive LiteLLM spend log batch and persist to spend.sqlite.

    LiteLLM may POST a list or a dict. We handle both.
    No authentication required — bind to 127.0.0.1 and this endpoint is
    only reachable from localhost.
    """
    try:
        body: Any = await request.json()
    except Exception:
        return {"ok": False, "detail": "invalid JSON"}

    entries: list[dict[str, Any]] = []
    if isinstance(body, list):
        entries = body
    elif isinstance(body, dict):
        # LiteLLM may wrap in {"logs": [...]} or send the list at a known key
        for key in ("logs", "spend_logs", "data"):
            if isinstance(body.get(key), list):
                entries = body[key]
                break
        if not entries:
            # Treat the dict itself as a single entry
            entries = [body]

    inserted = cost_service.record_spend_batch(entries)
    return {"ok": True, "inserted": inserted}


@router.post("/run-event")
async def run_event(request: Request):
    """Receive a pipeline run-event and persist to spend.sqlite.

    Accepts a single event dict or a list of events. Fail-open: malformed
    payloads return ok=False rather than raising, since the pipeline emits
    fire-and-forget and must never be blocked by telemetry.
    """
    try:
        body: Any = await request.json()
    except Exception:
        return {"ok": False, "detail": "invalid JSON"}

    entries: list[dict[str, Any]] = body if isinstance(body, list) else [body]
    inserted = 0
    for entry in entries:
        if isinstance(entry, dict):
            try:
                inserted += run_events.record_run_event(entry)
            except Exception:
                pass
    return {"ok": True, "inserted": inserted}
