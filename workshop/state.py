from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workshop import ledger

STATE_VERSION = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def state_path(task_id: str) -> Path:
    return ledger.task_dir(task_id) / "state.json"


def state_exists(task_id: str) -> bool:
    return state_path(task_id).exists()


def new_task_state(
    task_id: str,
    *,
    goal: str,
    repo: str,
    session_id: str = "",
    chat_id: str = "",
) -> dict[str, Any]:
    now = utc_now()
    return {
        "schema_version": STATE_VERSION,
        "task_id": task_id,
        "goal": goal,
        "repo": repo,
        "repo_entry": {},
        "repo_full_name": "",
        "default_branch": "",
        "session_id": session_id,
        "chat_id": chat_id,
        "status": "running",
        "next_stage": "triage",
        "attempts": {},
        "clarifications": [],
        "hitl_responses": [],
        "recovery_decisions": [],
        "scope_instruction": "",
        "stage_overrides": {},
        "stages": {},
        "approval_payload": {},
        "timeout_payload": {},
        "created_at": now,
        "updated_at": now,
    }


def load_task_state(task_id: str) -> dict[str, Any]:
    path = state_path(task_id)
    if not path.exists():
        raise FileNotFoundError(f"state not found for task {task_id}: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_task_state(state: dict[str, Any]) -> None:
    task_id = str(state["task_id"])
    path = state_path(task_id)
    state["updated_at"] = utc_now()
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def append_state_item(state: dict[str, Any], key: str, item: Any) -> None:
    values = state.setdefault(key, [])
    if not isinstance(values, list):
        values = []
        state[key] = values
    values.append(item)
