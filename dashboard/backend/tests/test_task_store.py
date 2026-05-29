"""Tests for task_store service against a tmp directory."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_tasks(tmp_path, monkeypatch):
    """Monkeypatch settings.tasks_base + workshop.ledger.LEDGER_BASE to a tmp dir."""
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()

    # Patch settings
    from dashboard.backend import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "tasks_base", str(tasks_dir))

    # Patch ledger LEDGER_BASE so workshop.state.load_task_state uses the same dir
    import workshop.ledger as ledger_module
    monkeypatch.setattr(ledger_module, "LEDGER_BASE", tasks_dir)

    return tasks_dir


def _make_state(tasks_dir: Path, task_id: str, **overrides) -> dict:
    """Write a minimal state.json and return the state dict."""
    state = {
        "schema_version": 1,
        "task_id": task_id,
        "goal": "test goal",
        "repo": "owner/repo",
        "status": "running",
        "next_stage": "triage",
        "stages": {},
        "attempts": {},
        "current_step": 0,
        "approval_payload": {},
        "timeout_payload": {},
        "clarifications": [],
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    state.update(overrides)
    task_dir = tasks_dir / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return state


class TestListTasks:
    def test_empty_base(self, tmp_tasks):
        from dashboard.backend.services.task_store import list_tasks
        assert list_tasks() == []

    def test_single_task(self, tmp_tasks):
        _make_state(tmp_tasks, "task001")
        from dashboard.backend.services.task_store import list_tasks
        results = list_tasks()
        assert len(results) == 1
        assert results[0].task_id == "task001"
        assert results[0].status == "running"

    def test_multiple_tasks(self, tmp_tasks):
        _make_state(tmp_tasks, "task001")
        _make_state(tmp_tasks, "task002", status="stopped")
        from dashboard.backend.services.task_store import list_tasks
        results = list_tasks()
        assert len(results) == 2
        task_ids = {r.task_id for r in results}
        assert "task001" in task_ids
        assert "task002" in task_ids

    def test_skips_invalid_state_file(self, tmp_tasks):
        # Create a task dir with invalid JSON
        bad_dir = tmp_tasks / "bad-task"
        bad_dir.mkdir()
        (bad_dir / "state.json").write_text("not-json", encoding="utf-8")
        _make_state(tmp_tasks, "good-task")
        from dashboard.backend.services.task_store import list_tasks
        results = list_tasks()
        assert len(results) == 1
        assert results[0].task_id == "good-task"


class TestGetTask:
    def test_existing_task(self, tmp_tasks):
        _make_state(tmp_tasks, "task123", goal="build a feature")
        from dashboard.backend.services.task_store import get_task
        detail = get_task("task123")
        assert detail.task_id == "task123"
        assert detail.goal == "build a feature"

    def test_not_found(self, tmp_tasks):
        from dashboard.backend.services.task_store import get_task
        with pytest.raises(FileNotFoundError):
            get_task("nonexistent")


class TestGetProgress:
    def test_empty_progress(self, tmp_tasks):
        _make_state(tmp_tasks, "taskprog")
        from dashboard.backend.services.task_store import get_progress
        assert get_progress("taskprog") == []

    def test_with_progress_entries(self, tmp_tasks):
        _make_state(tmp_tasks, "taskprog2")
        log_path = tmp_tasks / "taskprog2" / "progress_log.jsonl"
        log_path.write_text(
            '{"ts":"2026-01-01T00:00:00","event":"stage_start","stage":"triage"}\n'
            '{"ts":"2026-01-01T00:01:00","event":"stage_end","stage":"triage"}\n',
            encoding="utf-8",
        )
        from dashboard.backend.services.task_store import get_progress
        entries = get_progress("taskprog2")
        assert len(entries) == 2
        assert entries[0]["event"] == "stage_start"
        assert entries[1]["event"] == "stage_end"

    def test_invalid_task_id_rejected(self, tmp_tasks):
        from dashboard.backend.services.task_store import get_progress
        with pytest.raises(ValueError):
            get_progress("../escape")
