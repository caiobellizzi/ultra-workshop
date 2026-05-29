"""Task store service — reads workshop task state from the filesystem.

All reads are non-blocking file I/O; writes (launch/fix) delegate to
build_trigger / workshop_continue.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dashboard.backend.config import settings
from dashboard.backend.models.api_models import TaskDetail, TaskSummary


def _tasks_base() -> Path:
    return Path(settings.tasks_base)


def list_tasks() -> list[TaskSummary]:
    """Return summary rows for all tasks found under tasks_base."""
    base = _tasks_base()
    if not base.exists():
        return []

    results: list[TaskSummary] = []
    for state_file in sorted(base.glob("*/state.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data: dict[str, Any] = json.loads(state_file.read_text(encoding="utf-8"))
            results.append(
                TaskSummary(
                    task_id=str(data.get("task_id", state_file.parent.name)),
                    status=str(data.get("status", "unknown")),
                    goal=str(data.get("goal", "")),
                    repo=str(data.get("repo", "")),
                    stage=str(data.get("next_stage", "")),
                    created_at=str(data.get("created_at", "")),
                    updated_at=str(data.get("updated_at", "")),
                )
            )
        except Exception:
            continue
    return results


def get_task(task_id: str) -> TaskDetail:
    """Return full task detail for the given task_id.

    Raises FileNotFoundError if the state.json does not exist.
    """
    from workshop.state import load_task_state

    data = load_task_state(task_id)
    return TaskDetail(
        task_id=str(data.get("task_id", task_id)),
        status=str(data.get("status", "unknown")),
        goal=str(data.get("goal", "")),
        repo=str(data.get("repo", "")),
        next_stage=str(data.get("next_stage", "")),
        created_at=str(data.get("created_at", "")),
        updated_at=str(data.get("updated_at", "")),
        stages=data.get("stages", {}),
        attempts=data.get("attempts", {}),
        current_step=int(data.get("current_step", 0)),
        approval_payload=data.get("approval_payload", {}),
        timeout_payload=data.get("timeout_payload", {}),
        clarifications=data.get("clarifications", []),
    )


def get_progress(task_id: str) -> list[dict[str, Any]]:
    """Return all progress_log.jsonl entries for a task."""
    from workshop.ledger import validate_task_id

    validate_task_id(task_id)
    log_path = _tasks_base() / task_id / "progress_log.jsonl"
    if not log_path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries
