# Deploy location: /opt/ultra-workshop/workshop/ledger.py
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

LEDGER_BASE = Path("/home/uws/.ultra-workshop/tasks")
_TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def validate_task_id(task_id: str) -> None:
    """Reject task IDs that could escape filesystem roots or shell-adjacent names."""
    if not _TASK_ID_RE.fullmatch(task_id):
        raise ValueError(
            "invalid task_id: expected 1-64 letters, numbers, hyphens, or underscores"
        )


def task_dir(task_id: str) -> Path:
    """Return (and create) the task directory for the given task ID."""
    validate_task_id(task_id)
    p = LEDGER_BASE / task_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def append_progress(task_id: str, event: str, data: dict) -> None:
    """Append a JSONL entry to the task's progress_log.jsonl file."""
    p = task_dir(task_id) / "progress_log.jsonl"
    entry = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **data}
    with p.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def write_task_ledger(task_id: str, goal: str, status: str, pr_url: str = "") -> None:
    """Write a Markdown task ledger file to the task directory."""
    p = task_dir(task_id) / "task_ledger.md"
    content = (
        f"# Task {task_id}\n\n"
        f"**Goal:** {goal}\n"
        f"**Status:** {status}\n"
        f"**PR:** {pr_url or 'N/A'}\n"
        f"**Created:** {datetime.now(timezone.utc).isoformat()}\n"
    )
    p.write_text(content, encoding="utf-8")
