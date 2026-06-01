from __future__ import annotations

import importlib.util
import base64
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace


def _load_module(module_name: str, path: str):
    spec = importlib.util.spec_from_file_location(module_name, Path(path))
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_QUOTED_TASK = 'create "OpenHarness: Open Agent Harness" integration using https://github.com/HKUDS/OpenHarness'


def test_resolve_task_reads_quoted_task_file(tmp_path) -> None:
    """--task-file is read verbatim, preserving embedded quotes and stripping the trailing newline."""
    workshop_build = _load_module("workshop_build_for_test", "hermes-skills/workshop_build.py")
    task_file = tmp_path / "task.txt"
    task_file.write_text(_QUOTED_TASK + "\n", encoding="utf-8")

    result = workshop_build._resolve_task("", str(task_file), "")

    assert result == _QUOTED_TASK


def test_resolve_task_decodes_base64() -> None:
    """--task-b64 round-trips a quote-bearing task without shell mangling."""
    workshop_build = _load_module("workshop_build_for_test", "hermes-skills/workshop_build.py")
    encoded = base64.b64encode(_QUOTED_TASK.encode("utf-8")).decode("ascii")

    result = workshop_build._resolve_task("", "", encoded)

    assert result == _QUOTED_TASK


def test_resolve_task_file_takes_precedence_over_b64_and_inline(tmp_path) -> None:
    """Precedence is file > base64 > inline, matching the CLI contract."""
    workshop_build = _load_module("workshop_build_for_test", "hermes-skills/workshop_build.py")
    task_file = tmp_path / "task.txt"
    task_file.write_text("from-file", encoding="utf-8")
    b64 = base64.b64encode(b"from-b64").decode("ascii")

    assert workshop_build._resolve_task("from-inline", str(task_file), b64) == "from-file"
    assert workshop_build._resolve_task("from-inline", "", b64) == "from-b64"
    assert workshop_build._resolve_task("from-inline", "", "") == "from-inline"


def test_workshop_push_exposes_file_args() -> None:
    result = subprocess.run(
        [sys.executable, "hermes-skills/workshop_push.py", "--help"],
        capture_output=True,
        text=True,
        shell=False,
        check=False,
    )

    assert result.returncode == 0
    assert "--plan-goal-file" in result.stdout
    assert "--diff-summary-file" in result.stdout


def test_workshop_push_quotes_adr_frontmatter(monkeypatch, tmp_path) -> None:
    workshop_push = _load_module("workshop_push_for_test", "hermes-skills/workshop_push.py")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("GITHUB_PAT", "test-token")

    class FakeBrain:
        def __init__(self) -> None:
            self.calls = []

        def call_agent(self, action, payload):
            self.calls.append((action, payload))

    fake_brain = FakeBrain()
    monkeypatch.setattr(workshop_push, "_brain_http", fake_brain)

    def fake_run(argv, **kwargs):
        if argv[:3] == ["git", "push", "origin"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if argv[:3] == ["gh", "pr", "create"]:
            return SimpleNamespace(returncode=0, stdout="https://example.test/pr/1\n", stderr="")
        raise AssertionError(argv)

    monkeypatch.setattr(workshop_push.subprocess, "run", fake_run)
    monkeypatch.setattr(
        workshop_push.sys,
        "argv",
        [
            "workshop_push.py",
            "--task-id",
            "ws-safe",
            "--branch",
            "workshop/ws-safe",
            "--workspace-dir",
            str(workspace),
            "--repo-full-name",
            "owner/repo\nworkshop.status: pwned",
            "--base",
            "main\nbad: true",
            "--plan-goal",
            "goal\n---\ninjected: true",
            "--diff-summary",
            "summary",
        ],
    )

    workshop_push.main()

    assert fake_brain.calls
    action, payload = fake_brain.calls[0]
    assert action == "ingest"
    adr_content = payload.split("\n\n", 1)[1]
    frontmatter = adr_content.split("---", 2)[1]
    assert "\nworkshop.status: pwned" not in frontmatter
    assert "\nbad: true" not in frontmatter
    assert "workshop.repo: 'owner/repo workshop.status: pwned'" in frontmatter
