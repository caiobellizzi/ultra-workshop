"""
aider_runner — subprocess wrapper for Aider coder with single-model alias routing.

Wraps aider as a subprocess with:
  - Single --model <alias> routed through LiteLLM proxy at 127.0.0.1:4000/v1
  - model_alias is passed by the caller (e.g. "coder-worker" for coder stage)
  - All LLM calls routed through LiteLLM proxy at 127.0.0.1:4000/v1

SECURITY: subprocess.run([...], shell=False) — no shell injection vector.
Task string is passed as a single list element; no shell expansion occurs.

Deploy location: /opt/ultra-workshop/hermes-skills/aider_runner.py
Run as: sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 /opt/ultra-workshop/hermes-skills/aider_runner.py --task "<task>"

Cost ledger (OPTION B): After aider completes, posts a completion event to Brain's
curator agent (HTTP 200 + run_id). Full 2-LLM-call cost verification is deferred.

# BACKLOG: The cost ledger currently records an event marker only (OPTION B).
# Strengthen to verify LLM-call entries once Brain exposes a queryable cost-history
# endpoint. Decided 2026-05-21.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Scrub common secret patterns from verification output before persisting.
_OUTPUT_SECRET_RE = re.compile(
    r"(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}",
    re.IGNORECASE,
)

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


def _tail_lines(text: str, limit: int = 50) -> str:
    return "\n".join(text.splitlines()[-limit:])


def _package_scripts(workspace_dir: Path) -> dict[str, str]:
    package_json = workspace_dir / "package.json"
    if not package_json.exists():
        return {}
    try:
        payload = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    scripts = payload.get("scripts")
    return scripts if isinstance(scripts, dict) else {}


def _has_bats_tests(workspace_dir: Path) -> bool:
    tests_dir = workspace_dir / "tests"
    return tests_dir.exists() and any(tests_dir.rglob("*.bats"))


def _has_pytest_tests(workspace_dir: Path) -> bool:
    has_pytest_config = any(
        (workspace_dir / name).exists()
        for name in ("pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini")
    )
    tests_dir = workspace_dir / "tests"
    has_pytest_files = tests_dir.exists() and any(tests_dir.glob("test_*.py"))
    return has_pytest_config or has_pytest_files


def _detect_verification_commands(workspace_dir: Path) -> tuple[list[str] | None, list[str] | None]:
    scripts = _package_scripts(workspace_dir)
    if scripts:
        build_cmd = ["npm", "run", "build"] if "build" in scripts else None
        test_cmd = ["npm", "test"] if "test" in scripts else None
        if build_cmd or test_cmd:
            return build_cmd, test_cmd

    makefile = workspace_dir / "Makefile"
    if makefile.exists():
        try:
            content = makefile.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            content = ""
        if "\ntest:" in f"\n{content}":
            return None, ["make", "test"]

    if _has_pytest_tests(workspace_dir):
        return None, [sys.executable, "-m", "pytest"]

    if _has_bats_tests(workspace_dir):
        return None, ["bats", "tests"]

    return None, None


def _run_verification_command(
    workspace_dir: Path,
    command: list[str],
    *,
    timeout: int,
) -> tuple[bool, str]:
    result = subprocess.run(
        command,
        cwd=str(workspace_dir),
        capture_output=True,
        text=True,
        shell=False,
        timeout=timeout,
        check=False,
        env={**os.environ, "TERM": "dumb", "CI": "1", "NO_COLOR": "1"},
    )
    output = (
        f"$ {shlex.join(command)}\n"
        f"exit={result.returncode}\n"
        f"{result.stdout or ''}"
        f"{result.stderr or ''}"
    )
    return result.returncode == 0, output


def verify_workspace(workspace_dir: Path | str, *, timeout: int = 120) -> dict[str, object]:
    workspace = Path(workspace_dir)
    build_cmd, test_cmd = _detect_verification_commands(workspace)
    outputs: list[str] = []

    build_passed = True
    test_passed = True

    if build_cmd:
        try:
            build_passed, output = _run_verification_command(workspace, build_cmd, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            build_passed = False
            output = f"$ {shlex.join(build_cmd)}\nverification command failed: {exc}"
        outputs.append(output)

    if test_cmd:
        try:
            test_passed, output = _run_verification_command(workspace, test_cmd, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            test_passed = False
            output = f"$ {shlex.join(test_cmd)}\nverification command failed: {exc}"
        outputs.append(output)

    if not build_cmd and not test_cmd:
        outputs.append("$ echo no-test-command\nexit=0\nno-test-command")

    return {
        "build_passed": build_passed,
        "test_passed": test_passed,
        "output_tail": _tail_lines(_OUTPUT_SECRET_RE.sub("[REDACTED]", "\n".join(outputs))),
    }


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
    model_alias: str = "coder-worker",
) -> list[str]:
    return [
        aider_bin,
        "--model", f"openai/{model_alias}",
        "--openai-api-base", "http://127.0.0.1:4000/v1",
        "--openai-api-key", litellm_api_key,
        "--yes-always",
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


def run_aider(task: str, workspace_files: Optional[list[str]] = None, model_alias: str = "coder-worker") -> None:
    """Run aider on *task* inside a temp git workspace.

    Creates a temporary git-initialised workspace under /tmp, invokes aider
    with a single --model <model_alias> routed through the LiteLLM proxy,
    prints the diff summary, then posts a cost-ledger marker to Brain curator.

    Args:
        task:            The coding task description to pass to aider.
        workspace_files: Optional list of file paths for aider to edit. All
                         paths are passed as positional arguments to aider so
                         they are added to the chat. If not given, a blank
                         workspace.py is created in the temp workspace dir.
        model_alias:     LiteLLM alias for the model to use (default: "coder-worker").
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
        model_alias=model_alias,
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
        _post_cost_ledger(task, model_alias=model_alias, success=False)
        sys.exit(result.returncode)

    verification = verify_workspace(workspace_dir)
    print(f"[aider_runner] verification: {json.dumps(verification, sort_keys=True)}", flush=True)

    # --- Cost ledger (OPTION B — curator liveness only) ---
    _post_cost_ledger(task, model_alias=model_alias, success=True)


def _post_cost_ledger(task: str, success: bool, model_alias: str = "coder-worker") -> None:
    """Post a cost-ledger completion event to Brain's curator agent (OPTION B).

    Non-blocking: cost ledger failure does NOT abort the aider result.

    # BACKLOG: Strengthen to assert LLM-call entries once Brain exposes a queryable
    # cost-history endpoint. Decided 2026-05-21.
    """
    status_tag = "success" if success else "failed"
    if _brain_http is None:
        print("[cost-ledger] WARNING: brain_http not available (non-blocking)", file=sys.stderr, flush=True)
        return
    try:
        ledger_result = _brain_http.call_agent(
            "curator",
            f"aider task completed: cost_ledger_event status={status_tag} "
            f"model={model_alias} task={task[:80]}",
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
