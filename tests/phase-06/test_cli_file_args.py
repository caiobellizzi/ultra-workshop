from __future__ import annotations

import base64
import subprocess
import sys


def test_workshop_build_dry_run_accepts_quoted_task_file(tmp_path) -> None:
    task_file = tmp_path / "task.txt"
    task_file.write_text(
        'create "OpenHarness: Open Agent Harness" integration using https://github.com/HKUDS/OpenHarness\n',
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "hermes-skills/workshop_build.py",
            "--repo",
            "test-workshop-sandbox",
            "--task-file",
            str(task_file),
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        shell=False,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert 'OpenHarness: Open Agent Harness' in result.stdout


def test_workshop_build_dry_run_accepts_base64_task() -> None:
    task = 'create "OpenHarness: Open Agent Harness" integration using https://github.com/HKUDS/OpenHarness'
    encoded = base64.b64encode(task.encode("utf-8")).decode("ascii")

    result = subprocess.run(
        [
            sys.executable,
            "hermes-skills/workshop_build.py",
            "--repo",
            "test-workshop-sandbox",
            "--task-b64",
            encoded,
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        shell=False,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert 'OpenHarness: Open Agent Harness' in result.stdout


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
