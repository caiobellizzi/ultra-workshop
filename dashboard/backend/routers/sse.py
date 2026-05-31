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
            # Emit state if status changed — unnamed frame so es.onmessage fires
            if task.status != last_status:
                last_status = task.status
                yield {
                    "data": json.dumps({
                        "ts": task.updated_at,
                        "event": "state",
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

        # Emit new progress entries — unnamed frames, entry already has ts+event
        try:
            progress = get_progress(task_id)
            if len(progress) > last_progress_count:
                for entry in progress[last_progress_count:]:
                    yield {"data": json.dumps(entry)}
                last_progress_count = len(progress)
        except Exception:
            pass

        await asyncio.sleep(2.0)


async def _log_event_generator(request: Request, task_id: str) -> AsyncIterator[dict[str, str]]:
    """Stream progress_log.jsonl (replay + follow) and aider_step_*.log files."""
    from datetime import datetime, timezone
    task_path = Path(settings.tasks_base) / task_id
    progress_file = task_path / "progress_log.jsonl"
    progress_offset = 0
    aider_offsets: dict[Path, int] = {}
    idle_seconds = 0

    while idle_seconds < 120:
        if await request.is_disconnected():
            break

        any_new = False

        # Progress log: replay all existing entries on first pass, then follow new ones
        if progress_file.exists():
            try:
                raw = progress_file.read_bytes()
                if len(raw) > progress_offset:
                    for line in raw[progress_offset:].decode("utf-8", errors="replace").splitlines():
                        line = line.strip()
                        if line:
                            yield {"data": line}
                    progress_offset = len(raw)
                    any_new = True
            except OSError:
                pass

        # Aider step logs: only present during coder stage
        for log_file in sorted(task_path.glob("aider_step_*.log")):
            offset = aider_offsets.get(log_file, 0)
            try:
                raw = log_file.read_bytes()
            except OSError:
                continue
            if len(raw) > offset:
                for line in raw[offset:].decode("utf-8", errors="replace").splitlines():
                    yield {"data": json.dumps({
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "event": "log",
                        "msg": line,
                    })}
                aider_offsets[log_file] = len(raw)
                any_new = True

        idle_seconds = 0 if any_new else idle_seconds + 1
        await asyncio.sleep(1.0)


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
