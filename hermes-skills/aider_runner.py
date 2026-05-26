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
_brain_http = None
try:
    _spec = importlib.util.spec_from_file_location("brain_http", _BRAIN_HTTP)
    _brain_http = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_brain_http)
except Exception as _exc:
    print(f"[aider_runner] WARNING: brain_http not loaded: {_exc}", file=sys.stderr, flush=True)


def _git_root_for(path: Path) -> Path | None:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        shell=False,
        check=False,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def _resolve_workspace(workspace_files: Optional[list[str]]) -> tuple[Path, list[str]]:
    if workspace_files:
        absolute_files = [Path(path).resolve() for path in workspace_files]
        root = _git_root_for(absolute_files[0].parent)
        if root is not None:
            return root, [str(path.relative_to(root)) for path in absolute_files]
        return absolute_files[0].parent, [str(path) for path in absolute_files]

    workspace_dir = Path(tempfile.mkdtemp(prefix="uws-aider-workspace-"))
    subprocess.run(
        ["git", "init"],
        cwd=str(workspace_dir),
        capture_output=True,
        check=False,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init", "--no-gpg-sign"],
        cwd=str(workspace_dir),
        capture_output=True,
        check=False,
        env={**os.environ, "GIT_AUTHOR_NAME": "uws", "GIT_AUTHOR_EMAIL": "uws@localhost",
             "GIT_COMMITTER_NAME": "uws", "GIT_COMMITTER_EMAIL": "uws@localhost"},
    )
    target = workspace_dir / "workspace.py"
    target.write_text("# aider workspace\n")
    return workspace_dir, [str(target.relative_to(workspace_dir))]


def _build_aider_argv(
    *,
    aider_bin: str,
    task: str,
    target_files: list[str],
    litellm_api_key: str,
    history_dir: Path,
) -> list[str]:
    return [
        aider_bin,
        "--model", "openai/orchestrator",
        "--editor-model", "openai/private-worker",
        "--architect",
        "--openai-api-base", "http://127.0.0.1:4000/v1",
        "--openai-api-key", litellm_api_key,
        "--yes-always",
        "--no-stream",
        "--no-fancy-input",
        "--no-pretty",
        "--no-detect-urls",
        "--no-show-model-warnings",
        "--no-check-update",
        "--no-gitignore",
        "--input-history-file", str(history_dir / "input.history"),
        "--chat-history-file", str(history_dir / "chat.history.md"),
        "--llm-history-file", str(history_dir / "llm.history"),
        "--message", task,
        *target_files,
    ]


def run_aider(task: str, workspace_files: Optional[list[str]] = None) -> None:
    """Run aider on *task* inside a temp git workspace.

    Creates a temporary git-initialised workspace under /tmp, invokes aider
    with architect=orchestrator (NIM DSv4 Pro) + editor=private-worker (local
    Gemma via LM Studio) routed through the LiteLLM proxy,
    prints the diff summary, then posts a cost-ledger marker to Brain curator.

    Args:
        task:            The coding task description to pass to aider.
        workspace_files: Optional list of file paths for aider to edit. All
                         paths are passed as positional arguments to aider so
                         they are added to the chat. If not given, a blank
                         workspace.py is created in the temp workspace dir.
    """
    workspace_dir, target_files = _resolve_workspace(workspace_files)
    print(f"[aider_runner] workspace: {workspace_dir}", flush=True)

    # --- Build aider argv (shell=False — task is a single list element) ---
    litellm_api_key = os.environ.get("LITELLM_API_KEY", "")
    if not litellm_api_key:
        print("[aider_runner] ERROR: LITELLM_API_KEY not set in environment", file=sys.stderr, flush=True)
        sys.exit(1)

    # Resolve aider binary: prefer sibling venv bin/ next to the running Python
    # so the correct version is used regardless of PATH.
    _venv_aider = Path(sys.executable).parent / "aider"
    aider_bin = str(_venv_aider) if _venv_aider.exists() else "aider"
    history_dir = Path(tempfile.mkdtemp(prefix="uws-aider-history-"))
    argv = _build_aider_argv(
        aider_bin=aider_bin,
        task=task,
        target_files=target_files,
        litellm_api_key=litellm_api_key,
        history_dir=history_dir,
    )

    print(f"[aider_runner] running aider on task: {task[:80]!r}", flush=True)

    # --- Run aider (shell=False — no shell injection) ---
    result = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        shell=False,
        cwd=str(workspace_dir),
        stdin=subprocess.DEVNULL,
        env={**os.environ, "TERM": "dumb", "CI": "1"},
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
    if _brain_http is None:
        print("[cost-ledger] WARNING: brain_http not available (non-blocking)", file=sys.stderr, flush=True)
        return
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
        dest="workspace_files",
        action="append",
        default=None,
        help="Path to a file for aider to edit. Repeat for multiple files; or pass several paths after a single flag.",
        nargs="+",
    )
    args = parser.parse_args()
    # argparse with action="append" + nargs="+" yields a list of lists; flatten.
    flat: Optional[list[str]] = None
    if args.workspace_files:
        flat = [p for group in args.workspace_files for p in group]
    run_aider(args.task, flat)
