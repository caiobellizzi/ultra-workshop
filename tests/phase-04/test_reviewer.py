from __future__ import annotations

import json
from pathlib import Path

from workshop.reviewer import review_query
from workshop.types import ClarificationRequest, Review


def _query(tmp_path: Path, *, goal: str, changes: list[dict], clarifications: list[str] | None = None) -> str:
    return json.dumps(
        {
            "task_id": "ws-review",
            "plan": {
                "goal": goal,
                "steps": [{"id": "1", "description": "implement", "files": ["README.md", "app.py", "tests/test_app.py"]}],
                "affected_files": ["README.md", "app.py", "tests/test_app.py"],
            },
            "diff": {
                "summary": "test diff",
                "changes": changes,
                "branch": "workshop/ws-review",
                "workspace_dir": str(tmp_path),
            },
            "clarifications": clarifications or [],
        }
    )


def test_reviewer_requests_clarification_for_ambiguous_goal(tmp_path: Path) -> None:
    result = review_query(
        _query(
            tmp_path,
            goal="create a multi agent orchestration using the best 12 factory practices",
            changes=[{"path": "README.md", "diff": "+notes"}],
        )
    )

    assert isinstance(result, ClarificationRequest)
    assert result.source_stage == "reviewer"
    assert result.allow_free_text is True


def test_reviewer_returns_blocking_review_for_concrete_defects(tmp_path: Path) -> None:
    result = review_query(
        _query(
            tmp_path,
            goal="implement the requested app update",
            changes=[
                {"path": "README.md", "diff": "+notes"},
                {"path": "pytest", "diff": ""},
                {"path": "python app.py", "diff": "+bad"},
            ],
            clarifications=["approved interpretation"],
        )
    )

    assert isinstance(result, Review)
    assert result.passed is False
    assert any("shell command artifact" in issue for issue in result.blocking_issues)
