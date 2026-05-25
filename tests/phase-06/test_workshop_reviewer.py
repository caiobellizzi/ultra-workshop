from __future__ import annotations

import json
from pathlib import Path

from workshop.reviewer import review_query
from workshop.types import ClarificationRequest, Review


def _query(tmp_path: Path, changes: list[dict], goal: str | None = None, clarifications: list[str] | None = None) -> str:
    plan_goal = goal or "implement the requested workflow"
    return json.dumps(
        {
            "task_id": "ws-test",
            "plan": {
                "goal": plan_goal,
                "steps": [{"id": "1", "description": "implement", "files": ["README.md", "app.py", "tests/test_app.py"]}],
                "affected_files": ["README.md", "app.py", "tests/test_app.py"],
            },
            "diff": {
                "summary": "test diff",
                "changes": changes,
                "branch": "workshop/ws-test",
                "workspace_dir": str(tmp_path),
            },
            "clarifications": clarifications or [],
        }
    )


def test_reviewer_rejects_command_artifact_paths(tmp_path: Path) -> None:
    result = review_query(
        _query(
            tmp_path,
            [
                {"path": "README.md", "diff": "+Using HKUDS/OpenHarness"},
                {"path": "pytest", "diff": ""},
                {"path": "python app.py", "diff": "+bad"},
            ],
        )
    )

    assert isinstance(result, Review)
    assert result.passed is False
    assert any("shell command artifact" in issue for issue in result.blocking_issues)
    assert any("outside the plan" in issue for issue in result.blocking_issues)


def test_reviewer_requests_clarification_for_ambiguous_goal(tmp_path: Path) -> None:
    result = review_query(
        _query(
            tmp_path,
            [
                {"path": "README.md", "diff": "+notes"},
            ],
            goal="create a multi agent orchestration using the best 12 factory practices",
        )
    )

    assert isinstance(result, ClarificationRequest)
    assert result.source_stage == "reviewer"


def test_reviewer_passes_focused_valid_change(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("def run():\n    return 'ok'\n", encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.py").write_text("from app import run\n\ndef test_run():\n    assert run()\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("Usage notes\n", encoding="utf-8")

    result = review_query(
        _query(
            tmp_path,
            [
                {"path": "README.md", "diff": "+Usage notes"},
                {"path": "app.py", "diff": "+def run(): return 'ok'"},
                {"path": "tests/test_app.py", "diff": "+def test_run(): pass"},
            ],
            clarifications=["approved behavior"],
        )
    )

    assert isinstance(result, Review)
    assert result.passed is True
    assert result.blocking_issues == []
