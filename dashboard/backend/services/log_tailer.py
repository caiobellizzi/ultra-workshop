"""Log tailer service — yields new lines from aider_step_*.log files for SSE."""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

from dashboard.backend.config import settings


def _task_dir(task_id: str) -> Path:
    return Path(settings.tasks_base) / task_id


async def tail_aider_logs(task_id: str, poll_interval: float = 1.0) -> AsyncIterator[str]:
    """Async generator: yields new log lines from aider_step_*.log files.

    Yields lines as they appear. Stops when no write activity is detected for
    60 consecutive seconds (task likely finished).
    """
    task_path = _task_dir(task_id)
    seen_offsets: dict[Path, int] = {}
    idle_seconds = 0
    max_idle = 60

    while idle_seconds < max_idle:
        any_new = False
        log_files = sorted(task_path.glob("aider_step_*.log"))
        for log_file in log_files:
            offset = seen_offsets.get(log_file, 0)
            try:
                content = log_file.read_bytes()
            except OSError:
                continue
            if len(content) > offset:
                chunk = content[offset:].decode("utf-8", errors="replace")
                seen_offsets[log_file] = len(content)
                for line in chunk.splitlines():
                    yield json.dumps({
                        "ts": datetime.utcnow().isoformat() + "Z",
                        "event": "log",
                        "msg": line,
                    })
                any_new = True

        if any_new:
            idle_seconds = 0
        else:
            idle_seconds += poll_interval

        await asyncio.sleep(poll_interval)
