from __future__ import annotations

import base64
import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _load_module(module_name: str, path: str):
    spec = importlib.util.spec_from_file_location(module_name, Path(path))
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


workshop_continue = _load_module("workshop_continue", "hermes-skills/workshop_continue.py")


@pytest.fixture(autouse=True)
def isolated_ledger(tmp_path, monkeypatch) -> Path:
    import workshop.ledger as ledger_mod

    monkeypatch.setattr(ledger_mod, "LEDGER_BASE", tmp_path)
    return tmp_path


def test_continue_clarification_preserves_task_id_and_resumes(monkeypatch, tmp_path) -> None:
    from workshop.state import load_task_state, new_task_state, save_task_state

    state = new_task_state(
        "ws-original",
        goal="use the best 12 factory practices",
        repo="test-workshop-sandbox",
    )
    state["repo_entry"] = {"full_name": "caiobellizzi/test-workshop-sandbox", "default_branch": "main"}
    save_task_state(state)

    response_file = tmp_path / "response.json"
    response_file.write_text(
        json.dumps(
            {
                "user_responses": [
                    {
                        "question": "What did you mean?",
                        "answer": "12-factor app methodology",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    captured: dict[str, object] = {}

    class Result:
        returncode = 0

    def fake_run(argv, shell):
        captured["argv"] = argv
        captured["shell"] = shell
        return Result()

    monkeypatch.setattr(workshop_continue.subprocess, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "workshop_continue.py",
            "--task-id",
            "ws-original",
            "--hitl-type",
            "clarification",
            "--response-file",
            str(response_file),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        workshop_continue.main()

    assert exc_info.value.code == 0
    argv = captured["argv"]
    assert captured["shell"] is False
    assert "--task-id" in argv
    assert argv[argv.index("--task-id") + 1] == "ws-original"
    assert "--resume" in argv

    updated = load_task_state("ws-original")
    assert updated["next_stage"] == "requirements"
    assert updated["clarifications"] == ["What did you mean?: 12-factor app methodology"]


def test_continue_timeout_recovery_reenters_planning(monkeypatch, tmp_path) -> None:
    from workshop.state import load_task_state, new_task_state, save_task_state

    state = new_task_state(
        "ws-timeout",
        goal="create a multi agent orchestration",
        repo="test-workshop-sandbox",
    )
    state["next_stage"] = "coder"
    state["stages"] = {
        "planner": {"goal": "goal", "steps": [{"id": "1", "description": "big"}], "affected_files": []},
        "diff": {"summary": "old", "changes": [], "branch": "workshop/ws-timeout", "workspace_dir": "/tmp/ws"},
    }
    save_task_state(state)

    response_file = tmp_path / "response.txt"
    response_file.write_text("1", encoding="utf-8")

    captured: dict[str, object] = {}

    class Result:
        returncode = 0

    def fake_run(argv, shell):
        captured["argv"] = argv
        captured["shell"] = shell
        return Result()

    monkeypatch.setattr(workshop_continue.subprocess, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "workshop_continue.py",
            "--task-id",
            "ws-timeout",
            "--hitl-type",
            "timeout_recovery",
            "--response-file",
            str(response_file),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        workshop_continue.main()

    assert exc_info.value.code == 0
    assert captured["shell"] is False
    updated = load_task_state("ws-timeout")
    assert updated["next_stage"] == "planner"
    assert "planner" not in updated["stages"]
    assert "diff" not in updated["stages"]
    assert "smallest first vertical slice" in updated["scope_instruction"]


def test_continue_timeout_recovery_choice_increases_coder_timeout(monkeypatch) -> None:
    from workshop.state import load_task_state, new_task_state, save_task_state

    state = new_task_state(
        "ws-choice",
        goal="create a multi agent orchestration",
        repo="test-workshop-sandbox",
    )
    state["next_stage"] = "coder"
    save_task_state(state)

    captured: dict[str, object] = {}

    class Result:
        returncode = 0

    def fake_run(argv, shell):
        captured["argv"] = argv
        captured["shell"] = shell
        return Result()

    monkeypatch.setattr(workshop_continue.subprocess, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "workshop_continue.py",
            "--task-id",
            "ws-choice",
            "--hitl-type",
            "timeout_recovery",
            "--choice",
            "2",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        workshop_continue.main()

    assert exc_info.value.code == 0
    assert captured["shell"] is False
    updated = load_task_state("ws-choice")
    assert updated["next_stage"] == "coder"
    assert updated["stage_overrides"]["coder"] == {
        "timeout": 1920,
        "tool_timeout": 1800,
    }
    assert updated["hitl_responses"][-1]["response"] == "2"


def test_continue_clarification_accepts_response_b64(monkeypatch) -> None:
    from workshop.state import load_task_state, new_task_state, save_task_state

    state = new_task_state(
        "ws-b64",
        goal="use the best 12 factory practices",
        repo="test-workshop-sandbox",
    )
    state["repo_entry"] = {"full_name": "caiobellizzi/test-workshop-sandbox", "default_branch": "main"}
    save_task_state(state)

    response = {
        "user_responses": [
            {
                "question": "What did you mean?",
                "answer": "12-factor app methodology",
            }
        ]
    }
    encoded = base64.b64encode(json.dumps(response).encode("utf-8")).decode("ascii")

    captured: dict[str, object] = {}

    class Result:
        returncode = 0

    def fake_run(argv, shell):
        captured["argv"] = argv
        captured["shell"] = shell
        return Result()

    monkeypatch.setattr(workshop_continue.subprocess, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "workshop_continue.py",
            "--task-id",
            "ws-b64",
            "--hitl-type",
            "clarification",
            "--response-b64",
            encoded,
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        workshop_continue.main()

    assert exc_info.value.code == 0
    assert captured["shell"] is False
    updated = load_task_state("ws-b64")
    assert updated["next_stage"] == "requirements"
    assert updated["clarifications"] == ["What did you mean?: 12-factor app methodology"]
