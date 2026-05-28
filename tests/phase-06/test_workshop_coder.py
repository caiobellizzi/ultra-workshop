from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from hermes_skills_import import load_module


workshop_coder = load_module("workshop_coder", "hermes-skills/workshop_coder.py")


def test_build_aider_task_disambiguates_12_factory_practices() -> None:
    task = workshop_coder._build_aider_task(
        "create a multi agent orchestration using the best 12 factory practices",
        {},
    )

    assert "non-interactive batch pipeline" in task
    assert "Do not ask the reviewer for clarification" in task
    assert "12-factor app methodology" not in task
    assert "HKUDS/OpenHarness" not in task


def test_build_aider_task_includes_previous_review_feedback() -> None:
    task = workshop_coder._build_aider_task(
        "create a multi agent orchestration",
        {
            "feedback": "Review blocked",
            "blocking_issues": ["Invalid changed path 'pytest'"],
        },
    )

    assert "previous attempt was rejected" in task
    assert "Review blocked" in task
    assert "Invalid changed path 'pytest'" in task


def test_no_diff_returns_clarification_request() -> None:
    request = workshop_coder._clarification_request_for_no_diff(
        "ws-test",
        "create a multi agent orchestration",
        "need more information about the desired behavior",
    )

    assert request.source_stage == "coder"
    assert request.needs_clarification is True
    assert request.allow_free_text is True


def test_run_aider_runner_kills_process_group_on_idle_timeout(monkeypatch) -> None:
    """Idle watchdog should kill process and raise TimeoutExpired when no output received."""
    killed: list[tuple[int, int]] = []

    class FakeProcess:
        pid = 12345
        returncode = None

        def poll(self):
            return None  # never exits on its own

        def communicate(self, timeout):
            return "", ""

        def wait(self, timeout=None):
            self.returncode = -15
            return self.returncode

    def fake_popen(*args, **kwargs):
        assert kwargs.get("start_new_session") is True
        assert kwargs.get("shell") is False
        return FakeProcess()

    # select returns empty readable list to simulate no output (idle)
    monkeypatch.setattr(workshop_coder.select, "select", lambda *a, **kw: ([], [], []))
    monkeypatch.setattr(workshop_coder.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(workshop_coder.os, "killpg", lambda pid, sig: killed.append((pid, sig)))

    with pytest.raises(subprocess.TimeoutExpired):
        workshop_coder._run_aider_runner(["aider"], env={}, idle_timeout=0, step_max_timeout=600)

    assert (12345, workshop_coder.signal.SIGTERM) in killed


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        shell=False,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "tester",
            "GIT_AUTHOR_EMAIL": "tester@example.com",
            "GIT_COMMITTER_NAME": "tester",
            "GIT_COMMITTER_EMAIL": "tester@example.com",
        },
    )


def test_sanitize_unreviewable_changes_removes_command_artifacts(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "base", "--no-gpg-sign")
    base_ref = _git(repo, "rev-parse", "HEAD").stdout.strip()

    (repo / "README.md").write_text("base\nupdated\n", encoding="utf-8")
    (repo / "pytest tests").write_text("", encoding="utf-8")
    (repo / "python openharness_orchestration.py").write_text("## Testing\n", encoding="utf-8")
    (repo / "notes.md").write_text("outside plan\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "aider output", "--no-gpg-sign")

    sanitized = workshop_coder._sanitize_unreviewable_changes(
        repo,
        base_ref,
        {"README.md"},
    )

    assert sanitized == [
        "notes.md",
        "pytest tests",
        "python openharness_orchestration.py",
    ]
    assert not (repo / "pytest tests").exists()
    assert not (repo / "python openharness_orchestration.py").exists()
    assert not (repo / "notes.md").exists()
    assert workshop_coder._changed_paths_since(repo, base_ref) == ["README.md"]

    log = _git(repo, "log", "--oneline", "-1").stdout
    assert "remove unreviewable aider artifacts" in log


def test_planned_reviewable_paths_includes_step_files() -> None:
    plan = {
        "affected_files": ["README.md"],
        "steps": [
            {"id": "1", "description": "implement", "files": ["app.py", "tests/test_app.py"]},
            {"id": "2", "description": "bad", "files": ["pytest tests"]},
        ],
    }

    assert workshop_coder._planned_reviewable_paths(plan, plan["affected_files"]) == {
        "README.md",
        "app.py",
        "tests/test_app.py",
    }


def test_scaffold_treats_trailing_slash_entry_as_directory(tmp_path: Path) -> None:
    """Regression: a plan affected_files list mixing a trailing-slash dir entry
    with files inside that same dir must not crash with FileExistsError."""
    targets, scaffolded = workshop_coder._scaffold_target_files(
        tmp_path,
        ["src/dashboard/", "src/index.js", "src/dashboard/TaskList.js"],
    )

    # Trailing-slash entry becomes a real directory, not a 0-byte file.
    assert (tmp_path / "src" / "dashboard").is_dir()
    # File entries are created and returned as editable targets.
    assert (tmp_path / "src" / "index.js").is_file()
    assert (tmp_path / "src" / "dashboard" / "TaskList.js").is_file()
    # The directory entry is excluded from the editable-target list.
    assert str(tmp_path / "src" / "dashboard") not in targets
    assert str(tmp_path / "src" / "index.js") in targets
    assert str(tmp_path / "src" / "dashboard" / "TaskList.js") in targets
    assert scaffolded is True


def test_scaffold_repairs_stale_empty_file_where_dir_expected(tmp_path: Path) -> None:
    """Resume safety: an empty-file stub left by a prior crashed attempt where a
    directory now belongs is repaired instead of raising FileExistsError."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "dashboard").touch()  # poison from a prior buggy run

    targets, _ = workshop_coder._scaffold_target_files(
        tmp_path,
        ["src/dashboard/", "src/dashboard/TaskList.js"],
    )

    assert (tmp_path / "src" / "dashboard").is_dir()
    assert (tmp_path / "src" / "dashboard" / "TaskList.js").is_file()


def test_scaffold_preserves_non_empty_file_collision(tmp_path: Path) -> None:
    """A non-empty file where a directory is requested must NOT be clobbered;
    real data is never silently destroyed."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "dashboard").write_text("real content")

    with pytest.raises(FileExistsError):
        workshop_coder._scaffold_target_files(tmp_path, ["src/dashboard/"])

    assert (tmp_path / "src" / "dashboard").read_text() == "real content"
