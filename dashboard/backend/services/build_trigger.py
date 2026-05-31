"""Build trigger service — launches workshop_build.py in a background thread."""
from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path

from dashboard.backend.config import settings


def launch_build(task_id: str, repo: str, goal: str, brainstorm: bool = False) -> None:
    """Fire-and-forget: start workshop_build.py in a daemon thread.

    Returns immediately. Progress is observable via state.json + progress_log.jsonl.
    """
    workshop_build = Path(settings.workshop_build_py)
    if not workshop_build.exists():
        repo_root = Path(__file__).parent.parent.parent.parent
        workshop_build = repo_root / "hermes-skills" / "workshop_build.py"

    cmd = [
        sys.executable,
        str(workshop_build),
        "--task-id", task_id,
        "--repo", repo,
        "--task", goal,
    ]
    if brainstorm:
        cmd.append("--brainstorm")

    def _run() -> None:
        try:
            subprocess.run(cmd, capture_output=True, text=True)
        except Exception:
            pass

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def launch_fix(task_id: str) -> None:
    """Resume a stopped/failed task by re-running workshop_build.py --resume."""
    workshop_build = Path(settings.workshop_build_py)
    if not workshop_build.exists():
        repo_root = Path(__file__).parent.parent.parent.parent
        workshop_build = repo_root / "hermes-skills" / "workshop_build.py"

    cmd = [sys.executable, str(workshop_build), "--task-id", task_id, "--resume"]

    def _run() -> None:
        try:
            subprocess.run(cmd, capture_output=True, text=True)
        except Exception:
            pass

    t = threading.Thread(target=_run, daemon=True)
    t.start()
