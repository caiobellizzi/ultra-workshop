from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

try:
    from workshop.state import new_task_state  # type: ignore[import]
except ImportError:
    new_task_state = None  # type: ignore[assignment]


def _skip_if_missing() -> None:
    if new_task_state is None:
        pytest.xfail("workshop.state.new_task_state not yet updated with workspace_dir")


def test_new_task_state_has_workspace_dir() -> None:
    """new_task_state() result contains a 'workspace_dir' key."""
    _skip_if_missing()
    state = new_task_state(task_id="ws-test-001", goal="add hello.txt", repo="owner/repo")
    assert "workspace_dir" in state
    assert state["workspace_dir"] == ""


def test_clone_saves_workspace_dir(tmp_path, monkeypatch) -> None:
    """After the clone step, state['workspace_dir'] is populated with the cloned path."""
    _skip_if_missing()
    from workshop.state import clone_repo_to_workspace  # type: ignore[import]

    monkeypatch.setenv("GITHUB_PAT", "test-token")
    fake_completed = MagicMock()
    fake_completed.returncode = 0
    fake_completed.stdout = ""
    fake_completed.stderr = ""

    with patch("subprocess.run", return_value=fake_completed):
        state = new_task_state(task_id="ws-test-002", goal="add hello.txt")
        result = clone_repo_to_workspace(
            state,
            repo="caiobellizzi/test-workshop-sandbox",
            clone_root=tmp_path,
        )

    assert result.get("workspace_dir") is not None
    assert "test-workshop-sandbox" in str(result["workspace_dir"])


def test_clone_rejects_path_traversal_task_id(tmp_path, monkeypatch) -> None:
    """Task IDs cannot escape the deterministic workspace root."""
    _skip_if_missing()
    from workshop.state import clone_repo_to_workspace  # type: ignore[import]

    monkeypatch.setenv("GITHUB_PAT", "test-token")
    state = new_task_state(task_id="ws-safe", goal="add hello.txt")
    state["task_id"] = "../../../etc"

    with pytest.raises(ValueError):
        clone_repo_to_workspace(
            state,
            repo="caiobellizzi/test-workshop-sandbox",
            clone_root=tmp_path,
        )
