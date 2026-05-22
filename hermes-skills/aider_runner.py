"""
aider_runner — subprocess wrapper for Aider coder with architect/editor model split.

Wraps aider as a subprocess with:
  - Architect model: openai/orchestrator (NIM DeepSeek V4 Pro, thinking on; cloud-sonnet via proxy failover)
  - Editor model: openai/private-worker (via LM Link → LM Studio on Mac)
  - All LLM calls routed through LiteLLM proxy at 127.0.0.1:4000/v1

SECURITY: subprocess.run([...], shell=False) — no shell injection vector.
Task string is passed as a single list element; no shell expansion occurs.

Deploy location: /opt/ultra-workshop/hermes-skills/aider_runner.py
Run as: sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 /opt/ultra-workshop/hermes-skills/aider_runner.py --task "<task>"

Cost ledger (OPTION B): After aider completes, posts a completion event to Brain's
curator agent (HTTP 200 + run_id). Full 2-LLM-call cost verification is deferred.

# BACKLOG: The cost ledger currently records an event marker only (OPTION B).
# Strengthen to verify 2 LLM-call entries (orchestrator + private-worker) once
# Brain exposes a queryable cost-history endpoint. Decided 2026-05-21.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Load brain_http.py for cost ledger call (importlib — no hyphen in filename)
# ---------------------------------------------------------------------------
_BRAIN_HTTP = Path(__file__).parent / "brain_http.py"
_spec = importlib.util.spec_from_file_location("brain_http", _BRAIN_HTTP)
_brain_http = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_brain_http)


def run_aider(task: str, workspace_file: Optional[str] = None) -> None:
    """Run aider on *task* inside a temp git workspace.

    Creates a temporary git-initialised workspace under /tmp, invokes aider
    with architect=orchestrator + editor=private-worker via the LiteLLM proxy,
    prints the diff summary, then posts a cost-ledger marker to Brain curator.

    Args:
        task:           The coding task description to pass to aider.
        workspace_file: Optional path to a specific file for aider to edit.
                        If not given, a blank workspace.py is created in the
                        temp workspace directory.
    """
    # --- Create temp git workspace (aider requires a git repo) ---
    workspace_dir = Path(tempfile.mkdtemp(prefix="uws-aider-workspace-"))
    print(f"[aider_runner] workspace: {workspace_dir}", flush=True)

    # git init
    subprocess.run(
        ["git", "init"],
        cwd=str(workspace_dir),
        capture_output=True,
        check=False,
    )
    # git commit --allow-empty (aider expects at least one commit)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init", "--no-gpg-sign"],
        cwd=str(workspace_dir),
        capture_output=True,
        check=False,
        env={**os.environ, "GIT_AUTHOR_NAME": "uws", "GIT_AUTHOR_EMAIL": "uws@localhost",
             "GIT_COMMITTER_NAME": "uws", "GIT_COMMITTER_EMAIL": "uws@localhost"},
    )

    # Resolve the target file aider will edit
    if workspace_file:
        target_file = workspace_file
    else:
        target = workspace_dir / "workspace.py"
        target.write_text("# aider workspace\n")
        target_file = str(target)

    # --- Build aider argv (shell=False — task is a single list element) ---
    litellm_api_key = os.environ.get("LITELLM_API_KEY", "")
    if not litellm_api_key:
        print("[aider_runner] ERROR: LITELLM_API_KEY not set in environment", file=sys.stderr, flush=True)
        sys.exit(1)

    # Resolve aider binary: prefer sibling venv bin/ next to the running Python
    # so the correct version is used regardless of PATH.
    _venv_aider = Path(sys.executable).parent / "aider"
    aider_bin = str(_venv_aider) if _venv_aider.exists() else "aider"

    argv = [
        aider_bin,
        "--model", "openai/orchestrator",
        "--editor-model", "openai/private-worker",
        "--architect",
        "--openai-api-base", "http://127.0.0.1:4000/v1",
        "--openai-api-key", litellm_api_key,
        "--yes-always",
        "--no-stream",
        "--message", task,
        target_file,
    ]

    print(f"[aider_runner] running aider on task: {task[:80]!r}", flush=True)

    # --- Run aider (shell=False — no shell injection) ---
    result = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        shell=False,
        cwd=str(workspace_dir),
    )

    # Print diff summary to stdout (skill body captures this)
    if result.stdout:
        print(result.stdout, flush=True)

    if result.returncode != 0:
        print(result.stderr, file=sys.stderr, flush=True)
        # Post cost-ledger marker even on failure (non-blocking)
        _post_cost_ledger(task, success=False)
        sys.exit(result.returncode)

    # --- Cost ledger (OPTION B — curator liveness only) ---
    _post_cost_ledger(task, success=True)


def _post_cost_ledger(task: str, success: bool) -> None:
    """Post a cost-ledger completion event to Brain's curator agent (OPTION B).

    Non-blocking: cost ledger failure does NOT abort the aider result.

    # BACKLOG: Strengthen to assert 2 LLM-call entries (orchestrator + private-worker)
    # once Brain exposes a queryable cost-history endpoint. Decided 2026-05-21.
    """
    status_tag = "success" if success else "failed"
    try:
        ledger_result = _brain_http.call_agent(
            "curator",
            f"aider task completed: cost_ledger_event status={status_tag} "
            f"model=orchestrator+private-worker task={task[:80]}",
        )
        run_id = ledger_result.get("run_id", "unknown")
        print(f"[cost-ledger] curator run_id={run_id}", flush=True)
    except Exception as exc:
        print(
            f"[cost-ledger] WARNING: curator call failed (non-blocking): {exc}",
            file=sys.stderr,
            flush=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run aider with architect/editor split via LiteLLM proxy.",
    )
    parser.add_argument(
        "--task",
        required=True,
        help="The coding task description to pass to aider.",
    )
    parser.add_argument(
        "--workspace-file",
        default=None,
        help="Optional path to a specific file for aider to edit.",
    )
    args = parser.parse_args()
    run_aider(args.task, args.workspace_file)
