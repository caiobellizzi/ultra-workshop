"""SSE endpoints: task events and aider log stream.

Uses sse-starlette for proper SSE framing.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from dashboard.backend.config import settings
from dashboard.backend.deps import require_auth
from dashboard.backend.services.log_tailer import tail_aider_logs

router = APIRouter(prefix="/api/sse", tags=["sse"])


async def _task_event_generator(request: Request, task_id: str) -> AsyncIterator[dict[str, str]]:
    """Poll state.json + progress_log.jsonl every 2s and yield SSE events."""
    from dashboard.backend.services.task_store import get_task, get_progress

    last_progress_count = 0
    last_status = None

    while True:
        if await request.is_disconnected():
            break

        try:
            task = get_task(task_id)
            # Emit state if status changed
            if task.status != last_status:
                last_status = task.status
                yield {
                    "event": "state",
                    "data": json.dumps({
                        "task_id": task_id,
                        "status": task.status,
                        "next_stage": task.next_stage,
                        "updated_at": task.updated_at,
                    }),
                }
        except FileNotFoundError:
            pass
        except Exception:
            pass

        # Emit new progress entries
        try:
            progress = get_progress(task_id)
            if len(progress) > last_progress_count:
                for entry in progress[last_progress_count:]:
                    yield {"event": "progress", "data": json.dumps(entry)}
                last_progress_count = len(progress)
        except Exception:
            pass

        await asyncio.sleep(2.0)


async def _log_event_generator(request: Request, task_id: str) -> AsyncIterator[dict[str, str]]:
    """Tail aider_step_*.log files and yield SSE log-line events."""
    async for line in tail_aider_logs(task_id):
        if await request.is_disconnected():
            break
        yield {"event": "log", "data": line}


@router.get("/tasks/{task_id}/events")
async def task_events(task_id: str, request: Request, _auth=Depends(require_auth)):
    try:
        from workshop.ledger import validate_task_id
        validate_task_id(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return EventSourceResponse(
        _task_event_generator(request, task_id),
        media_type="text/event-stream",
    )


@router.get("/tasks/{task_id}/logs")
async def task_logs(task_id: str, request: Request, _auth=Depends(require_auth)):
    try:
        from workshop.ledger import validate_task_id
        validate_task_id(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return EventSourceResponse(
        _log_event_generator(request, task_id),
        media_type="text/event-stream",
    )
