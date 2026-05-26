from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from workshop.orchestrator import ClarificationNeeded, SpecialistFailed
from workshop.requirements_gate import RequirementsDecision
from workshop.types import ClarificationRequest, Diff, Plan, Review


def _load_module(module_name: str, path: str):
    spec = importlib.util.spec_from_file_location(module_name, Path(path))
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


workshop_build = _load_module("workshop_build", "hermes-skills/workshop_build.py")


class _TriageResult:
    def __init__(self) -> None:
        self.task_type = "BUILD"
        self.summary = "summary"
        self.complexity = "low"

    def model_dump(self) -> dict[str, str]:
        return {
            "task_type": self.task_type,
            "summary": self.summary,
            "complexity": self.complexity,
        }


@pytest.fixture(autouse=True)
def isolated_ledger(tmp_path, monkeypatch) -> Path:
    import workshop.ledger as ledger_mod
    import workshop.state as state_mod

    monkeypatch.setattr(ledger_mod, "LEDGER_BASE", tmp_path)

    def fake_clone_repo_to_workspace(state, *, repo, clone_root=None):
        workspace = tmp_path / "workspace" / repo.split("/")[-1]
        (workspace / ".git").mkdir(parents=True, exist_ok=True)
        state["workspace_dir"] = str(workspace)
        return state

    monkeypatch.setattr(state_mod, "clone_repo_to_workspace", fake_clone_repo_to_workspace)
    return tmp_path


def test_workshop_build_emits_clarification_payload(monkeypatch, capsys) -> None:
    import workshop.cost as cost_mod
    import workshop.ledger as ledger_mod
    import workshop.orchestrator as orchestrator_mod
    import workshop.repo_registry as repo_mod

    monkeypatch.setattr(cost_mod, "check_circuit_breaker", lambda: None)
    monkeypatch.setattr(
        repo_mod,
        "mark_last_used",
        lambda repo: {"full_name": "caiobellizzi/test-workshop-sandbox", "default_branch": "main"},
    )
    monkeypatch.setattr(ledger_mod, "write_task_ledger", lambda *a, **kw: None)
    monkeypatch.setattr(ledger_mod, "append_progress", lambda *a, **kw: None)

    def fake_run_specialist(skill_name, query_json, output_schema, dry_run=False, timeout=1200):
        if skill_name == "triage-specialist":
            return _TriageResult()
        raise ClarificationNeeded(
            ClarificationRequest(
                task_id="ws-fixed",
                source_stage="requirements",
                reason="Ambiguous phrase",
                questions=[{"question": "What did you mean?", "options": ["A", "B"], "context": "task"}],
                options=["A", "B"],
                allow_free_text=True,
                evidence=["phrase"],
                summary="Clarification needed before planning.",
            )
        )

    monkeypatch.setattr(orchestrator_mod, "run_specialist", fake_run_specialist)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "workshop_build.py",
            "--repo",
            "test-workshop-sandbox",
            "--task",
            "use the best 12 factory practices",
            "--task-id",
            "ws-fixed",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        workshop_build.main()

    assert exc_info.value.code == 2
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["hitl_type"] == "clarification"
    assert payload["task_id"] == "ws-fixed"
    assert payload["source_stage"] == "requirements"

    from workshop.state import load_task_state

    state = load_task_state("ws-fixed")
    assert state["status"] == "needs_clarification"
    assert state["next_stage"] == "requirements"


def test_workshop_build_resume_preserves_task_id_and_clarifications(tmp_path, monkeypatch, capsys) -> None:
    import workshop.cost as cost_mod
    import workshop.ledger as ledger_mod
    import workshop.orchestrator as orchestrator_mod
    import workshop.repo_registry as repo_mod

    monkeypatch.setattr(cost_mod, "check_circuit_breaker", lambda: None)
    monkeypatch.setattr(
        repo_mod,
        "mark_last_used",
        lambda repo: {"full_name": "caiobellizzi/test-workshop-sandbox", "default_branch": "main"},
    )
    monkeypatch.setattr(ledger_mod, "write_task_ledger", lambda *a, **kw: None)
    monkeypatch.setattr(ledger_mod, "append_progress", lambda *a, **kw: None)

    seen_queries: dict[str, dict] = {}

    def fake_run_specialist(skill_name, query_json, output_schema, dry_run=False, timeout=1200):
        payload = json.loads(query_json)
        seen_queries[skill_name] = payload
        if skill_name == "triage-specialist":
            return _TriageResult()
        if skill_name == "requirements-specialist":
            return RequirementsDecision(
                goal=payload["goal"],
                planning_notes=["authoritative clarification"],
                clarifications=["Meaning: Use the 12-factor app methodology"],
            )
        if skill_name == "planner-specialist":
            return Plan(
                goal=payload["goal"],
                steps=[{"id": "1", "description": "Implement", "files": ["README.md"]}],
                affected_files=["README.md"],
            )
        if skill_name == "coder-specialist":
            return Diff(summary="done", changes=[{"path": "README.md", "diff": "+text"}], branch="workshop/ws-fixed", workspace_dir="/tmp/ws-fixed")
        if skill_name == "reviewer-specialist":
            return Review(passed=True, feedback="ok", blocking_issues=[])
        raise AssertionError(skill_name)

    monkeypatch.setattr(orchestrator_mod, "run_specialist", fake_run_specialist)

    clarifications_file = tmp_path / "clarifications.json"
    clarifications_file.write_text(
        json.dumps({"answers": [{"question": "Meaning", "answer": "Use the 12-factor app methodology"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "workshop_build.py",
            "--repo",
            "test-workshop-sandbox",
            "--task",
            "use the best 12 factory practices",
            "--task-id",
            "ws-fixed",
            "--clarifications-file",
            str(clarifications_file),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        workshop_build.main()

    assert exc_info.value.code == 2
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["hitl_type"] == "approval"
    assert payload["task_id"] == "ws-fixed"
    assert seen_queries["requirements-specialist"]["clarifications"]
    assert seen_queries["planner-specialist"]["clarifications"] == [
        "Meaning: Use the 12-factor app methodology"
    ]

    from workshop.state import load_task_state

    state = load_task_state("ws-fixed")
    assert state["status"] == "needs_approval"
    assert state["next_stage"] == "approval"
    assert state["approval_payload"]["task_id"] == "ws-fixed"


def test_workshop_build_stops_for_coder_timeout_recovery(monkeypatch, capsys) -> None:
    import workshop.cost as cost_mod
    import workshop.ledger as ledger_mod
    import workshop.orchestrator as orchestrator_mod
    import workshop.repo_registry as repo_mod

    monkeypatch.setattr(cost_mod, "check_circuit_breaker", lambda: None)
    monkeypatch.setattr(
        repo_mod,
        "mark_last_used",
        lambda repo: {"full_name": "caiobellizzi/test-workshop-sandbox", "default_branch": "main"},
    )
    monkeypatch.setattr(ledger_mod, "write_task_ledger", lambda *a, **kw: None)
    monkeypatch.setattr(ledger_mod, "append_progress", lambda *a, **kw: None)

    def fake_run_specialist(skill_name, query_json, output_schema, dry_run=False, timeout=1200):
        payload = json.loads(query_json)
        if skill_name == "triage-specialist":
            return _TriageResult()
        if skill_name == "requirements-specialist":
            return RequirementsDecision(goal=payload["goal"], clarifications=[])
        if skill_name == "planner-specialist":
            return Plan(
                goal=payload["goal"],
                steps=[{"id": "1", "description": "Implement", "files": ["README.md"]}],
                affected_files=["README.md"],
            )
        if skill_name == "coder-specialist":
            # tool_timeout is now UWS_CODER_MAX (default 7200) — not the old 900s
            assert payload["stage_policy"]["tool_timeout"] >= 7200
            raise SpecialistFailed(
                "coder-specialist",
                124,
                "[workshop_coder] ERROR: aider_runner timed out",
            )
        raise AssertionError(skill_name)

    monkeypatch.setattr(orchestrator_mod, "run_specialist", fake_run_specialist)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "workshop_build.py",
            "--repo",
            "test-workshop-sandbox",
            "--task",
            "create a multi agent orchestration",
            "--task-id",
            "ws-timeout",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        workshop_build.main()

    assert exc_info.value.code == 2
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["hitl_type"] == "timeout_recovery"
    assert payload["task_id"] == "ws-timeout"
    assert payload["stage"] == "coder"

    from workshop.state import load_task_state

    state = load_task_state("ws-timeout")
    assert state["status"] == "needs_timeout_recovery"
    assert state["next_stage"] == "coder"
    # Phase 10: coder may be attempted once directly + once via auto-decompose sub-step
    assert state["attempts"]["coder"] >= 1
