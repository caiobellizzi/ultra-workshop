# Deploy location: /opt/ultra-workshop/hermes-skills/workshop_coder.py
"""Deterministic envelope producer for the coder-specialist stage.

Replaces the LLM-driven JSON assembly in skills/coder-specialist/SKILL.md.
Clones the selected active repo, creates the task branch, runs aider_runner.py, and
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

sys.path.insert(0, str(Path(__file__).parent.parent))

from workshop.requirements_gate import maybe_clarification_request  # noqa: E402
from workshop.repo_registry import DEFAULT_REPO, canonicalize_repo  # noqa: E402
from workshop.types import ClarificationQuestion, ClarificationRequest  # noqa: E402

AIDER_RUNNER = Path(__file__).parent / "aider_runner.py"
AIDER_RUN_TIMEOUT = int(os.environ.get("AIDER_RUN_TIMEOUT", "900"))


def _emit_dry_run(repo_full_name: str = DEFAULT_REPO, default_branch: str = "main") -> None:
    payload = {
        "summary": "dry-run coder",
        "changes": [],
        "branch": "workshop/dry-run",
        "workspace_dir": "/tmp/uws-sandbox-dry-run",
        "repo_full_name": repo_full_name,
        "default_branch": default_branch,
    }
    print(json.dumps(payload), flush=True)
    sys.exit(0)


def _build_aider_task(goal: str, previous_review: dict) -> str:
    batch_contract = [
        "You are running inside a non-interactive batch pipeline.",
        "Implement the approved plan and any concrete reviewer defects only.",
        "Do not ask the reviewer for clarification.",
        "Keep edits focused to the provided files and include tests for Python source changes.",
    ]

    parts = ["\n".join(batch_contract)]
    if previous_review:
        feedback = (previous_review.get("feedback") or "").strip()
        blocking = previous_review.get("blocking_issues") or []
        retry_parts = [
            "RETRY: the previous attempt was rejected by the reviewer.",
            "You MUST address the following before producing new code:",
        ]
        if feedback:
            retry_parts.append(f"Reviewer feedback: {feedback}")
        if blocking:
            bullets = "\n".join(f"- {item}" for item in blocking)
            retry_parts.append(f"Blocking issues that MUST be fixed:\n{bullets}")
        parts.append("\n\n".join(retry_parts))
    parts.append(f"Original goal: {goal}")
    return "\n\n".join(parts)


def _looks_like_ambiguity(text: str) -> bool:
    lowered = text.lower()
    phrases = (
        "need more information",
        "need more info",
        "please clarify",
        "which one",
        "unclear",
        "ambiguous",
        "not enough context",
    )
    return any(phrase in lowered for phrase in phrases)


def _clarification_request_for_no_diff(task_id: str, goal: str, summary: str) -> ClarificationRequest:
    request = maybe_clarification_request(task_id, goal, source_stage="coder")
    if request is not None:
        return request
    return ClarificationRequest(
        task_id=task_id,
        source_stage="coder",
        reason="Coder completed without producing a file diff.",
        questions=[
            ClarificationQuestion(
                question="The coder did not produce a diff. What behavior should be implemented?",
                options=[],
                context=goal,
            )
        ],
        allow_free_text=True,
        evidence=[summary[:200] or "Aider returned no diff and no concrete file changes."],
        summary="Clarification needed because the coder produced no concrete change.",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Workshop coder envelope producer")
    parser.add_argument("--query", type=str, required=True, help="JSON query string (task_id, plan, workspace_dir)")
    parser.add_argument("--dry-run", action="store_true", help="Emit hardcoded dry-run envelope and exit 0")
    args = parser.parse_args()

    try:
        query = json.loads(args.query)
    except json.JSONDecodeError as exc:
        print(f"[workshop_coder] ERROR: --query is not valid JSON: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)

    repo = query.get("repo") or {}
    repo_full_name = canonicalize_repo(str(repo.get("full_name") or query.get("repo_full_name") or DEFAULT_REPO))
    default_branch = str(repo.get("default_branch") or query.get("default_branch") or "main")

    if args.dry_run:
        _emit_dry_run(repo_full_name, default_branch)

    task_id = query.get("task_id", "")
    plan = query.get("plan", {}) or {}
    workspace_dir = query.get("workspace_dir") or f"/tmp/uws-sandbox-{task_id}/"
    goal = plan.get("goal", "")
    previous_review = query.get("previous_review") or {}

    if not task_id or not goal:
        print("[workshop_coder] ERROR: query missing task_id or plan.goal", file=sys.stderr, flush=True)
        sys.exit(1)

    aider_task = _build_aider_task(goal, previous_review)

    workspace = Path(workspace_dir)
    workspace.mkdir(parents=True, exist_ok=True)

    # 1. Clone target repo if .git absent
    if not (workspace / ".git").exists():
        clone = subprocess.run(
            ["gh", "repo", "clone", repo_full_name, str(workspace)],
            capture_output=True,
            text=True,
            shell=False,
            env={**os.environ, "GH_TOKEN": os.environ.get("GITHUB_PAT", "")},
        )
        if clone.returncode != 0:
            print(f"[workshop_coder] ERROR: gh repo clone failed: {clone.stderr}", file=sys.stderr, flush=True)
            sys.exit(1)

    branch = f"workshop/{task_id}"

    subprocess.run(
        ["git", "-C", str(workspace), "checkout", default_branch],
        capture_output=True,
        text=True,
        shell=False,
    )

    # 2. Reset the task branch from the base branch on every attempt. A retry
    # must not inherit rejected files from a previous coder attempt.
    checkout = subprocess.run(
        ["git", "-C", str(workspace), "checkout", "-B", branch, default_branch],
        capture_output=True,
        text=True,
        shell=False,
    )
    if checkout.returncode != 0:
        print(f"[workshop_coder] ERROR: git checkout failed: {checkout.stderr}", file=sys.stderr, flush=True)
        sys.exit(1)

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

    # Capture HEAD SHA before aider runs so the post-run diff captures only
    # aider's edits (and not the scaffold commit we just made above).
    head_before_aider = subprocess.run(
        ["git", "-C", str(workspace), "rev-parse", "HEAD"],
        capture_output=True, text=True, shell=False, check=False,
    ).stdout.strip()

    try:
        aider = subprocess.run(
            [sys.executable, str(AIDER_RUNNER), "--task", aider_task, "--workspace-file", *target_files],
            capture_output=True,
            text=True,
            shell=False,
            env=os.environ.copy(),
            timeout=AIDER_RUN_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        print(
            f"[workshop_coder] ERROR: aider_runner timed out after {AIDER_RUN_TIMEOUT}s",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(124)

    if aider.returncode != 0:
        print(f"[workshop_coder] ERROR: aider_runner exited {aider.returncode}: {aider.stderr[:500]}", file=sys.stderr, flush=True)
        sys.exit(aider.returncode)

    summary = (aider.stdout or "")[:500]
    combined_output = "\n".join(part for part in (aider.stdout, aider.stderr) if part)

    # Walk the diff aider produced (committed + working-tree). Per-file diff
    # is capped at 4000 chars to keep the Diff envelope JSON small — large
    # files imply the reviewer should flag scope anyway.
    changes: list[dict] = []
    if head_before_aider:
        name_only = subprocess.run(
            ["git", "-C", str(workspace), "diff", "--name-only", head_before_aider],
            capture_output=True, text=True, shell=False, check=False,
        )
        for file_path in [p for p in name_only.stdout.splitlines() if p.strip()]:
            per_file = subprocess.run(
                ["git", "-C", str(workspace), "diff", head_before_aider, "--", file_path],
                capture_output=True, text=True, shell=False, check=False,
            )
            changes.append({"path": file_path, "diff": per_file.stdout[:4000]})

    if not changes or _looks_like_ambiguity(combined_output):
        request = _clarification_request_for_no_diff(task_id, goal, summary or combined_output)
        print(request.model_dump_json(), flush=True)
        sys.exit(0)

    payload = {
        "summary": summary,
        "changes": changes,
        "branch": branch,
        "workspace_dir": str(workspace),
        "repo_full_name": repo_full_name,
        "default_branch": default_branch,
    }
    print(json.dumps(payload), flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
