from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from workshop.requirements_gate import RequirementsDecision
from workshop.reviewer import review_query
from workshop.types import Diff, Plan, Review


def _load_module(module_name: str, path: str):
    spec = importlib.util.spec_from_file_location(module_name, Path(path))
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


workshop_build = _load_module("workshop_build_phase08", "hermes-skills/workshop_build.py")
workshop_planner = _load_module("workshop_planner_phase08", "hermes-skills/workshop_planner.py")


class _TriageResult:
    task_type = "BUILD"
    summary = "summary"
    complexity = "low"

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

    monkeypatch.setattr(ledger_mod, "LEDGER_BASE", tmp_path / "ledger")

    def fake_clone_repo_to_workspace(state, *, repo, clone_root=None):
        workspace = tmp_path / "workspace" / repo.split("/")[-1]
        (workspace / ".git").mkdir(parents=True, exist_ok=True)
        state["workspace_dir"] = str(workspace)
        return state

    monkeypatch.setattr(state_mod, "clone_repo_to_workspace", fake_clone_repo_to_workspace)
    return tmp_path


def test_reviewer_returns_structured_failure_for_verification_failure(tmp_path: Path) -> None:
    payload = {
        "task_id": "ws-structured",
        "plan": {
            "goal": "update app",
            "steps": [{"id": "1", "description": "implement", "files": ["app.py"]}],
            "affected_files": ["app.py"],
        },
        "diff": {
            "summary": "changed app",
            "changes": [{"path": "app.py", "diff": "+broken"}],
            "branch": "workshop/ws-structured",
            "workspace_dir": str(tmp_path),
            "build_passed": True,
            "test_passed": False,
            "output_tail": "FAILED tests/test_app.py::test_app",
        },
        "clarifications": ["approved behavior"],
    }

    result = review_query(json.dumps(payload))

    assert isinstance(result, Review)
    assert result.passed is False
    issue = result.blocking_issues[0].model_dump()
    assert set(issue) == {"file", "problem", "required_fix"}
    assert "Test verification failed" in issue["problem"]
    assert "FAILED tests/test_app.py" in issue["problem"]


def test_workshop_planner_injects_brain_context(monkeypatch) -> None:
    class FakeBrain:
        def call_agent(self, action, query):
            assert action == "query"
            assert "repo conventions and relevant ADRs" in query
            return {"content": "Use pytest and keep changes small."}

    monkeypatch.setattr(workshop_planner, "_brain_http", FakeBrain())
    query = json.dumps(
        {
            "goal": "update docs",
            "repo": {"full_name": "owner/repo"},
            "context": "Base context",
        }
    )

    enriched = json.loads(workshop_planner._inject_brain_context(query))

    assert "Base context" in enriched["context"]
    assert "Use pytest and keep changes small." in enriched["context"]


def test_workshop_build_exits_2_after_review_retry_exhaustion(monkeypatch, capsys) -> None:
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
                steps=[{"id": "1", "description": "Implement", "files": ["app.py"]}],
                affected_files=["app.py"],
            )
        if skill_name == "coder-specialist":
            return Diff(
                summary="broken",
                changes=[{"path": "app.py", "diff": "+broken"}],
                branch="workshop/ws-review-exhausted",
                workspace_dir="/tmp/ws-review-exhausted",
                build_passed=True,
                test_passed=True,
            )
        if skill_name == "reviewer-specialist":
            return Review(
                passed=False,
                feedback="Review blocked",
                blocking_issues=[
                    {
                        "file": "app.py",
                        "problem": "missing behavior",
                        "required_fix": "implement the requested behavior",
                    }
                ],
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
            "update app",
            "--task-id",
            "ws-review-exhausted",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        workshop_build.main()

    assert exc_info.value.code == 2
    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert payload["hitl_type"] == "review_retry_exhausted"
    assert payload["blocking_issues"][0] == {
        "file": "app.py",
        "problem": "missing behavior",
        "required_fix": "implement the requested behavior",
    }
