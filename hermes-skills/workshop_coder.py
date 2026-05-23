# Deploy location: /opt/ultra-workshop/hermes-skills/workshop_coder.py
"""Deterministic envelope producer for the coder-specialist stage.

Replaces the LLM-driven JSON assembly in skills/coder-specialist/SKILL.md.
Clones the sandbox repo, creates the task branch, runs aider_runner.py, and
emits the Diff JSON envelope to stdout.

SECURITY: subprocess.run([...], shell=False) throughout — no shell-injection
surface. The query JSON is parsed with json.loads, not eval.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SANDBOX_REPO = "https://github.com/caiobellizzi/test-workshop-sandbox.git"
AIDER_RUNNER = Path(__file__).parent / "aider_runner.py"


def _emit_dry_run() -> None:
    payload = {
        "summary": "dry-run coder",
        "changes": [],
        "branch": "workshop/dry-run",
        "workspace_dir": "/tmp/uws-sandbox-dry-run",
    }
    print(json.dumps(payload), flush=True)
    sys.exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Workshop coder envelope producer")
    parser.add_argument("--query", type=str, required=True, help="JSON query string (task_id, plan, workspace_dir)")
    parser.add_argument("--dry-run", action="store_true", help="Emit hardcoded dry-run envelope and exit 0")
    args = parser.parse_args()

    if args.dry_run:
        _emit_dry_run()

    try:
        query = json.loads(args.query)
    except json.JSONDecodeError as exc:
        print(f"[workshop_coder] ERROR: --query is not valid JSON: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)

    task_id = query.get("task_id", "")
    plan = query.get("plan", {}) or {}
    workspace_dir = query.get("workspace_dir") or f"/tmp/uws-sandbox-{task_id}/"
    goal = plan.get("goal", "")

    if not task_id or not goal:
        print("[workshop_coder] ERROR: query missing task_id or plan.goal", file=sys.stderr, flush=True)
        sys.exit(1)

    workspace = Path(workspace_dir)
    workspace.mkdir(parents=True, exist_ok=True)

    # 1. Clone sandbox if .git absent
    if not (workspace / ".git").exists():
        clone = subprocess.run(
            ["git", "clone", SANDBOX_REPO, str(workspace)],
            capture_output=True,
            text=True,
            shell=False,
        )
        if clone.returncode != 0:
            print(f"[workshop_coder] ERROR: git clone failed: {clone.stderr}", file=sys.stderr, flush=True)
            sys.exit(1)

    branch = f"workshop/{task_id}"

    # 2. Create task branch (ignore failure if branch already exists — checkout instead)
    checkout = subprocess.run(
        ["git", "-C", str(workspace), "checkout", "-b", branch],
        capture_output=True,
        text=True,
        shell=False,
    )
    if checkout.returncode != 0:
        subprocess.run(
            ["git", "-C", str(workspace), "checkout", branch],
            capture_output=True,
            text=True,
            shell=False,
        )

    # 3. Run aider on the goal, targeting the files the plan says will be modified.
    #    Fallback to README.md if affected_files is empty (preserves prior behaviour).
    affected = plan.get("affected_files") or ["README.md"]
    target_files: list[str] = []
    scaffolded_any = False
    for rel_path in affected:
        abs_path = workspace / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        if not abs_path.exists():
            abs_path.touch()
            scaffolded_any = True
        target_files.append(str(abs_path))

    # Commit the scaffold so aider can apply edits against a clean tracked
    # state. Aider's "commit before applying edits" step silently no-ops on
    # untracked files and then skips writing the edits to disk.
    if scaffolded_any:
        subprocess.run(
            ["git", "-C", str(workspace), "add", "--", *target_files],
            capture_output=True, text=True, shell=False,
        )
        subprocess.run(
            ["git", "-C", str(workspace), "commit",
             "-m", f"scaffold for aider: {task_id}",
             "--allow-empty", "--no-gpg-sign"],
            capture_output=True, text=True, shell=False,
            env={**os.environ,
                 "GIT_AUTHOR_NAME": "uws", "GIT_AUTHOR_EMAIL": "uws@localhost",
                 "GIT_COMMITTER_NAME": "uws", "GIT_COMMITTER_EMAIL": "uws@localhost"},
        )

    aider = subprocess.run(
        [sys.executable, str(AIDER_RUNNER), "--task", goal, "--workspace-file", *target_files],
        capture_output=True,
        text=True,
        shell=False,
        env=os.environ.copy(),
    )

    if aider.returncode != 0:
        print(f"[workshop_coder] ERROR: aider_runner exited {aider.returncode}: {aider.stderr[:500]}", file=sys.stderr, flush=True)
        sys.exit(aider.returncode)

    summary = (aider.stdout or "")[:500]

    payload = {
        "summary": summary,
        "changes": [],
        "branch": branch,
        "workspace_dir": str(workspace),
    }
    print(json.dumps(payload), flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
