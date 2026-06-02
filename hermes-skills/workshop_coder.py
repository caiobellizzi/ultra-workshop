# Deploy location: /opt/ultra-workshop/hermes-skills/workshop_coder.py
"""Deterministic envelope producer for the coder-specialist stage.

Replaces the LLM-driven JSON assembly in skills/coder-specialist/SKILL.md.
Clones the selected active repo, creates the task branch, runs aider_runner.py
per step, and emits the Diff JSON envelope to stdout.

Phase 10: Each PlanStep is a separate Aider call with its own commit.
Idle watchdog kills hung Aider processes at UWS_IDLE_TIMEOUT (default 120s).
Step cursor is persisted after each commit for --resume support.

SECURITY: subprocess.run([...], shell=False) throughout — no shell-injection
surface. The query JSON is parsed with json.loads, not eval.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import select
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from aider_runner import verify_workspace  # noqa: E402
from workshop.requirements_gate import maybe_clarification_request  # noqa: E402
from workshop.repo_registry import DEFAULT_REPO, canonicalize_repo  # noqa: E402
from workshop.stage_policy import stage_tool_timeout  # noqa: E402
from workshop.types import ClarificationQuestion, ClarificationRequest  # noqa: E402

AIDER_RUNNER = Path(__file__).parent / "aider_runner.py"
DEFAULT_AIDER_RUN_TIMEOUT = int(os.environ.get("AIDER_RUN_TIMEOUT", str(stage_tool_timeout("coder") or 900)))

# Per-step timeouts (Phase 10 constants)
IDLE_TIMEOUT = int(os.environ.get("UWS_IDLE_TIMEOUT", "120"))
STEP_MAX_TIMEOUT = int(os.environ.get("UWS_STEP_MAX_TIMEOUT", "600"))
MAX_STEP_RETRIES = 2

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")


class StepRetryExhausted(RuntimeError):
    """Raised when a single step exhausts all build/test retries."""
    def __init__(self, step_idx: int, step_id: str, output: str):
        self.step_idx = step_idx
        self.step_id = step_id
        self.output = output
        super().__init__(f"Step {step_id} (idx={step_idx}) exhausted retries. output_tail={output[-300:]!r}")


def _git_env() -> dict[str, str]:
    return {
        **os.environ,
        "GIT_AUTHOR_NAME": "uws",
        "GIT_AUTHOR_EMAIL": "uws@localhost",
        "GIT_COMMITTER_NAME": "uws",
        "GIT_COMMITTER_EMAIL": "uws@localhost",
    }


def _ensure_scaffold_dir(path: Path) -> None:
    """``mkdir -p`` that repairs a stale empty-file stub sitting where *path*
    must be a directory.

    A prior crashed attempt could have ``touch()``ed a 0-byte file at a path that
    a later entry needs as a directory; ``mkdir(exist_ok=True)`` still raises
    FileExistsError on a non-directory, so we remove the empty stub first. A
    non-empty file is left untouched (mkdir then raises) — real data is never
    silently destroyed.
    """
    if path.exists() and not path.is_dir() and path.stat().st_size == 0:
        path.unlink()
    path.mkdir(parents=True, exist_ok=True)


def _scaffold_target_files(workspace: Path, rel_paths: list[str]) -> tuple[list[str], bool]:
    """Create scaffold files/dirs for plan-relative *rel_paths* under *workspace*.

    Entries ending in ``/`` denote directories: they are created as directories
    (never ``touch()``ed as files) and excluded from the returned editable-target
    list. File entries get their parent directory created and are ``touch()``ed if
    missing. Returns ``(target_files, scaffolded_any)``.

    Trailing-slash directory entries used to be touched as 0-byte files, which
    then collided with the ``mkdir`` of a later file inside the same directory
    (FileExistsError) — see test_scaffold_treats_trailing_slash_entry_as_directory.
    """
    target_files: list[str] = []
    scaffolded_any = False
    for rel_path in rel_paths:
        if not rel_path:
            continue
        if rel_path.endswith("/"):
            _ensure_scaffold_dir(workspace / rel_path)
            continue
        abs_path = workspace / rel_path
        _ensure_scaffold_dir(abs_path.parent)
        if not abs_path.exists():
            abs_path.touch()
            scaffolded_any = True
        target_files.append(str(abs_path))
    return target_files, scaffolded_any


def _resolve_step_files(
    workspace: Path,
    step_files_raw: list[str],
    all_target_files: list[str],
) -> list[str]:
    """Resolve the editable target files passed to aider for a plan step.

    Scaffolds the step's declared files under *workspace*. A step that lists only
    directory entries (trailing slash) scaffolds the dirs but yields no editable
    targets — fall back to the full affected-file set so aider always receives at
    least one real ``--workspace-file``. An empty list crashes aider_runner's
    argparse (``--workspace-file`` is ``nargs='+'``), and dropping the flag would
    route aider to a throwaway temp workspace instead of the cloned repo.
    """
    if step_files_raw:
        step_files, _ = _scaffold_target_files(workspace, step_files_raw)
    else:
        step_files = []
    return step_files or all_target_files


def _changed_paths_since(workspace: Path, base_ref: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(workspace), "diff", "--name-only", "-z", base_ref],
        capture_output=True,
        shell=False,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [item.decode("utf-8", errors="replace") for item in result.stdout.split(b"\0") if item]


def _path_exists_at_ref(workspace: Path, ref: str, rel_path: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(workspace), "cat-file", "-e", f"{ref}:{rel_path}"],
        capture_output=True,
        text=True,
        shell=False,
        check=False,
    )
    return result.returncode == 0


def _safe_workspace_child(workspace: Path, rel_path: str) -> Path | None:
    try:
        child = (workspace / rel_path).resolve()
        child.relative_to(workspace.resolve())
    except (OSError, ValueError):
        return None
    return child


def _valid_reviewable_path(rel_path: str) -> bool:
    if not rel_path or rel_path.strip() != rel_path:
        return False
    path = Path(rel_path)
    if path.is_absolute() or ".." in path.parts:
        return False
    if _CONTROL_CHARS_RE.search(rel_path) or any(ch in rel_path for ch in {'"', "'", "`"}):
        return False
    if any(ch.isspace() for ch in rel_path):
        return False
    if rel_path in {"pytest", "python", "pip"}:
        return False
    if rel_path.startswith(("bash ", "curl ", "pip ", "pytest ", "python ", "sh ")):
        return False
    return True


def _sanitize_unreviewable_changes(workspace: Path, base_ref: str, allowed_paths: set[str]) -> list[str]:
    """Remove committed Aider artifacts that reviewer will reject."""
    changed_paths = _changed_paths_since(workspace, base_ref)
    unreviewable = [
        path
        for path in changed_paths
        if path not in allowed_paths or not _valid_reviewable_path(path)
    ]
    if not unreviewable:
        return []

    for rel_path in unreviewable:
        if _path_exists_at_ref(workspace, base_ref, rel_path):
            subprocess.run(
                ["git", "-C", str(workspace), "checkout", base_ref, "--", rel_path],
                capture_output=True,
                text=True,
                shell=False,
                check=False,
            )
        else:
            child = _safe_workspace_child(workspace, rel_path)
            if child is not None and child.exists():
                child.unlink()
        subprocess.run(
            ["git", "-C", str(workspace), "add", "-A", "--", rel_path],
            capture_output=True,
            text=True,
            shell=False,
            check=False,
        )

    staged = subprocess.run(
        ["git", "-C", str(workspace), "diff", "--cached", "--quiet"],
        capture_output=True,
        text=True,
        shell=False,
        check=False,
    )
    if staged.returncode == 1:
        subprocess.run(
            [
                "git", "-C", str(workspace), "commit",
                "-m", "remove unreviewable aider artifacts",
                "--no-gpg-sign",
            ],
            capture_output=True,
            text=True,
            shell=False,
            env=_git_env(),
            check=False,
        )

    return unreviewable


def _planned_reviewable_paths(plan: dict, fallback_files: list[str]) -> set[str]:
    paths = set(fallback_files)
    for step in plan.get("steps") or []:
        if isinstance(step, dict):
            paths.update(step.get("files") or [])
    return {str(Path(path)) for path in paths if _valid_reviewable_path(str(Path(path)))}


def _emit_dry_run(repo_full_name: str = DEFAULT_REPO, default_branch: str = "main") -> None:
    payload = {
        "summary": "dry-run coder",
        "changes": [],
        "branch": "workshop/dry-run",
        "workspace_dir": "/tmp/uws-sandbox-dry-run",
        "repo_full_name": repo_full_name,
        "default_branch": default_branch,
        "build_passed": True,
        "test_passed": True,
        "output_tail": "dry-run",
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
            bullets = "\n".join(f"- {_format_blocking_issue(item)}" for item in blocking)
            retry_parts.append(f"Blocking issues that MUST be fixed:\n{bullets}")
        parts.append("\n\n".join(retry_parts))
    parts.append(f"Original goal: {goal}")
    return "\n\n".join(parts)


def _format_blocking_issue(item: object) -> str:
    if isinstance(item, dict):
        file_name = str(item.get("file") or "*")
        problem = str(item.get("problem") or "").strip()
        required_fix = str(item.get("required_fix") or "").strip()
        pieces = [f"file={file_name}"]
        if problem:
            pieces.append(f"problem={problem}")
        if required_fix:
            pieces.append(f"required_fix={required_fix}")
        return "; ".join(pieces)
    return str(item)


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


def _terminate_process_group(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass  # SIGKILL was sent; process will be reaped by OS eventually


def _run_aider_runner(
    argv: list[str],
    *,
    env: dict[str, str],
    idle_timeout: int = IDLE_TIMEOUT,
    step_max_timeout: int = STEP_MAX_TIMEOUT,
    log_file: Optional[Path] = None,
) -> subprocess.CompletedProcess:
    """Run aider with idle watchdog.

    Kills the process if no output is produced for *idle_timeout* seconds,
    or if total elapsed time exceeds *step_max_timeout* seconds.
    The old blind process.communicate(timeout=900) is replaced by this.
    """
    process = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,  # bytes mode — TextIOWrapper.read() blocks after select(); read1() does not
        shell=False,
        env=env,
        start_new_session=True,
    )

    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    last_output_at = time.monotonic()
    start_at = time.monotonic()

    while True:
        elapsed = time.monotonic() - start_at
        idle_secs = time.monotonic() - last_output_at

        # Absolute backstop
        if elapsed >= step_max_timeout:
            print(
                f"[workshop_coder] step_max_timeout={step_max_timeout}s exceeded — killing aider",
                file=sys.stderr,
                flush=True,
            )
            _terminate_process_group(process)
            raise subprocess.TimeoutExpired(argv, step_max_timeout)

        # Idle watchdog
        if idle_secs >= idle_timeout:
            print(
                f"[workshop_coder] idle_timeout={idle_timeout}s exceeded (no output) — killing aider",
                file=sys.stderr,
                flush=True,
            )
            _terminate_process_group(process)
            raise subprocess.TimeoutExpired(argv, idle_timeout)

        # Non-blocking read with select — 1s poll interval
        # read1() returns immediately with whatever bytes are available (no buffering block)
        readable, _, _ = select.select(
            [process.stdout, process.stderr], [], [], 1.0
        )
        for stream in readable:
            data = stream.read1(4096)
            if data:
                last_output_at = time.monotonic()
                decoded = data.decode("utf-8", errors="replace")
                if stream is process.stdout:
                    stdout_chunks.append(decoded)
                else:
                    stderr_chunks.append(decoded)
                if log_file is not None:
                    try:
                        log_file.write(decoded)
                        log_file.flush()
                    except OSError:
                        pass

        # Check if process has exited
        if process.poll() is not None:
            # Drain any remaining output
            try:
                remaining_out, remaining_err = process.communicate(timeout=5)
                if remaining_out:
                    decoded_out = remaining_out.decode("utf-8", errors="replace")
                    stdout_chunks.append(decoded_out)
                    if log_file is not None:
                        try:
                            log_file.write(decoded_out)
                            log_file.flush()
                        except OSError:
                            pass
                if remaining_err:
                    decoded_err = remaining_err.decode("utf-8", errors="replace")
                    stderr_chunks.append(decoded_err)
                    if log_file is not None:
                        try:
                            log_file.write(decoded_err)
                            log_file.flush()
                        except OSError:
                            pass
            except subprocess.TimeoutExpired:
                pass
            break

    return subprocess.CompletedProcess(
        argv,
        process.returncode,
        "".join(stdout_chunks),
        "".join(stderr_chunks),
    )


def _run_build_test_gate(workspace: Path) -> tuple[bool, str]:
    """Run verify_workspace and return (passed, output_tail)."""
    result = verify_workspace(workspace)
    passed = bool(result["build_passed"]) and bool(result["test_passed"])
    return passed, str(result["output_tail"])


def _commit_step(workspace: Path, task_id: str, step_idx: int, step_description: str) -> bool:
    """Stage all changes and commit for this step. Returns True if commit was made."""
    # Stage all changes
    subprocess.run(
        ["git", "-C", str(workspace), "add", "-A"],
        capture_output=True, text=True, shell=False, check=False,
    )
    # Check if there is anything to commit
    staged = subprocess.run(
        ["git", "-C", str(workspace), "diff", "--cached", "--quiet"],
        capture_output=True, text=True, shell=False, check=False,
    )
    if staged.returncode == 0:
        # Nothing staged
        return False

    short_desc = step_description[:60]
    commit_msg = f"step {step_idx + 1}: {short_desc}"
    result = subprocess.run(
        ["git", "-C", str(workspace), "commit", "-m", commit_msg, "--no-gpg-sign"],
        capture_output=True, text=True, shell=False, env=_git_env(), check=False,
    )
    return result.returncode == 0


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
    # model_alias for coder stage — provided by the caller via stage_model_alias()
    model_alias = str(query.get("model_alias") or "coder-worker")
    # Resume cursor: which step index to start from
    start_step = int(query.get("current_step") or 0)

    if not task_id or not goal:
        print("[workshop_coder] ERROR: query missing task_id or plan.goal", file=sys.stderr, flush=True)
        sys.exit(1)

    workspace = Path(workspace_dir)
    workspace.mkdir(parents=True, exist_ok=True)

    # 1. Clone target repo if .git absent
    if not (workspace / ".git").exists():
        clone = subprocess.run(
            ["gh", "repo", "clone", repo_full_name, str(workspace)],
            capture_output=True,
            text=True,
            shell=False,
            env={**os.environ, "GH_TOKEN": os.environ.get("GITHUB_PAT") or os.environ.get("GH_TOKEN", "")},
        )
        if clone.returncode != 0:
            print(f"[workshop_coder] ERROR: gh repo clone failed: {clone.stderr}", file=sys.stderr, flush=True)
            sys.exit(1)

    branch = f"workshop/{task_id}"

    # 2. Reset task branch from base ONLY on fresh start (start_step == 0).
    # On resume (start_step > 0), check out the existing branch so prior commits survive.
    if start_step == 0:
        subprocess.run(
            ["git", "-C", str(workspace), "checkout", default_branch],
            capture_output=True, text=True, shell=False,
        )
        checkout = subprocess.run(
            ["git", "-C", str(workspace), "checkout", "-B", branch, default_branch],
            capture_output=True, text=True, shell=False,
        )
    else:
        checkout = subprocess.run(
            ["git", "-C", str(workspace), "checkout", branch],
            capture_output=True, text=True, shell=False,
        )
    if checkout.returncode != 0:
        print(f"[workshop_coder] ERROR: git checkout failed: {checkout.stderr}", file=sys.stderr, flush=True)
        sys.exit(1)

    # 3. Scaffold all affected files so aider can edit them
    affected = plan.get("affected_files") or ["README.md"]
    all_target_files, scaffolded_any = _scaffold_target_files(workspace, affected)

    if scaffolded_any:
        subprocess.run(
            ["git", "-C", str(workspace), "add", "--", *all_target_files],
            capture_output=True, text=True, shell=False,
        )
        subprocess.run(
            ["git", "-C", str(workspace), "commit",
             "-m", f"scaffold for aider: {task_id}",
             "--allow-empty", "--no-gpg-sign"],
            capture_output=True, text=True, shell=False, env=_git_env(),
        )

    # Capture HEAD SHA before any aider step runs (after scaffold commit if any)
    head_before_aider = subprocess.run(
        ["git", "-C", str(workspace), "rev-parse", "HEAD"],
        capture_output=True, text=True, shell=False, check=False,
    ).stdout.strip()

    litellm_api_key = os.environ.get("LITELLM_API_KEY", "")
    if not litellm_api_key:
        print("[workshop_coder] ERROR: LITELLM_API_KEY not set in environment", file=sys.stderr, flush=True)
        sys.exit(1)

    steps = plan.get("steps") or []
    allowed_paths = _planned_reviewable_paths(plan, affected)
    all_changes: list[dict] = []
    all_summary_parts: list[str] = []

    # 4. Per-step execution loop
    for step_idx, step in enumerate(steps):
        if isinstance(step, dict):
            step_id = str(step.get("id") or str(step_idx + 1))
            step_description = str(step.get("description") or "")
            step_files_raw = [f for f in (step.get("files") or []) if f]
        else:
            # PlanStep model object (if deserialized)
            step_id = str(getattr(step, "id", str(step_idx + 1)))
            step_description = str(getattr(step, "description", ""))
            step_files_raw = [f for f in (getattr(step, "files", None) or []) if f]

        # Resume: skip already-committed steps
        if step_idx < start_step:
            print(f"[workshop_coder] skipping step {step_idx + 1} (already committed, resume from {start_step})", flush=True)
            continue

        # Scaffold step-specific files (dirs for trailing-slash entries), falling
        # back to the full affected-file set when the step yields no editable
        # targets (lists no files, or lists only directories).
        step_files = _resolve_step_files(workspace, step_files_raw, all_target_files)

        step_head_before = subprocess.run(
            ["git", "-C", str(workspace), "rev-parse", "HEAD"],
            capture_output=True, text=True, shell=False, check=False,
        ).stdout.strip()

        # Build the aider task message for this step
        batch_contract = "\n".join([
            "You are running inside a non-interactive batch pipeline.",
            "Implement only the described step. Do not ask for clarification.",
            "Keep edits focused to the provided files.",
        ])
        step_msg = f"{batch_contract}\n\nGoal: {goal}\n\nStep {step_idx + 1}: {step_description}"

        if previous_review:
            step_msg += "\n\n" + _build_aider_task("", previous_review).split("Original goal:")[0].strip()

        aider_argv = [
            sys.executable, str(AIDER_RUNNER),
            "--task", step_msg,
            "--workspace-file", *step_files,
        ]

        gate_passed = False
        gate_output = ""

        # Open per-step log file for tee (additive — dashboard tail via SSE).
        # Non-blocking: failure to open the log does NOT abort the step.
        _step_log_file = None
        try:
            from workshop.ledger import task_dir as _task_dir
            _step_log_path = _task_dir(task_id) / f"aider_step_{step_idx}.log"
            _step_log_file = _step_log_path.open("a", encoding="utf-8", errors="replace")
        except Exception as _log_exc:
            print(
                f"[workshop_coder] WARNING: could not open step log: {_log_exc}",
                file=sys.stderr, flush=True,
            )

        for retry in range(MAX_STEP_RETRIES + 1):
            if retry > 0:
                step_msg_retry = (
                    f"{step_msg}\n\nPrevious attempt {retry} failed build/test gate:\n{gate_output[-500:]}"
                )
                aider_argv = [
                    sys.executable, str(AIDER_RUNNER),
                    "--task", step_msg_retry,
                    "--workspace-file", *step_files,
                ]

            print(f"[workshop_coder] step {step_idx + 1}/{len(steps)} '{step_id}' attempt {retry + 1}", flush=True)

            try:
                aider = _run_aider_runner(
                    aider_argv,
                    env={**os.environ.copy(), "LITELLM_API_KEY": litellm_api_key},
                    idle_timeout=IDLE_TIMEOUT,
                    step_max_timeout=STEP_MAX_TIMEOUT,
                    log_file=_step_log_file,
                )
            except subprocess.TimeoutExpired as exc:
                print(
                    f"[workshop_coder] step {step_idx + 1} timed out: {exc}",
                    file=sys.stderr, flush=True,
                )
                if retry >= MAX_STEP_RETRIES:
                    raise StepRetryExhausted(step_idx, step_id, f"timeout after {exc.timeout}s")
                continue

            if aider.returncode != 0:
                print(
                    f"[workshop_coder] step {step_idx + 1} aider exited {aider.returncode}: {aider.stderr[:300]}",
                    file=sys.stderr, flush=True,
                )
                gate_output = aider.stderr[:500]
                if retry >= MAX_STEP_RETRIES:
                    raise StepRetryExhausted(step_idx, step_id, gate_output)
                continue

            # Run per-step build/test gate
            gate_passed, gate_output = _run_build_test_gate(workspace)
            if gate_passed:
                break

            print(
                f"[workshop_coder] step {step_idx + 1} build/test gate failed (retry {retry + 1}/{MAX_STEP_RETRIES + 1})",
                file=sys.stderr, flush=True,
            )
            if retry >= MAX_STEP_RETRIES:
                raise StepRetryExhausted(step_idx, step_id, gate_output)

        # Close per-step log file (opened before the retry loop)
        if _step_log_file is not None:
            try:
                _step_log_file.close()
            except OSError:
                pass

        # Sanitize unreviewable artifacts before committing
        sanitized = _sanitize_unreviewable_changes(workspace, step_head_before, allowed_paths)
        if sanitized:
            print(
                "[workshop_coder] removed unreviewable artifacts: " + ", ".join(sanitized[:10]),
                file=sys.stderr, flush=True,
            )

        # Commit this step's changes
        committed = _commit_step(workspace, task_id, step_idx, step_description)
        if committed:
            print(f"[workshop_coder] step {step_idx + 1} committed", flush=True)
        else:
            print(f"[workshop_coder] step {step_idx + 1} no changes to commit", flush=True)

        # Collect diff for this step
        for file_path in _changed_paths_since(workspace, step_head_before):
            per_file = subprocess.run(
                ["git", "-C", str(workspace), "diff", step_head_before, "--", file_path],
                capture_output=True, text=True, shell=False, check=False,
            )
            all_changes.append({"path": file_path, "diff": per_file.stdout[:4000]})

        all_summary_parts.append(f"Step {step_idx + 1}: {step_description[:80]}")

        # Persist step cursor for resume support
        # Write current_step marker alongside state if state file available
        _persist_step_cursor(task_id, step_idx + 1)

    # 5. Final diff over all steps
    combined_summary = "; ".join(all_summary_parts) or goal
    combined_output = combined_summary  # used for ambiguity check

    if not all_changes or _looks_like_ambiguity(combined_output):
        request = _clarification_request_for_no_diff(task_id, goal, combined_summary)
        print(request.model_dump_json(), flush=True)
        sys.exit(0)

    verification = verify_workspace(workspace)
    payload = {
        "summary": combined_summary[:500],
        "changes": all_changes,
        "branch": branch,
        "workspace_dir": str(workspace),
        "repo_full_name": repo_full_name,
        "default_branch": default_branch,
        "build_passed": verification["build_passed"],
        "test_passed": verification["test_passed"],
        "output_tail": verification["output_tail"],
    }
    print(json.dumps(payload), flush=True)
    sys.exit(0)


def _persist_step_cursor(task_id: str, current_step: int) -> None:
    """Persist the current_step cursor to the task state file if it exists."""
    try:
        from workshop.ledger import task_dir
        from workshop.state import load_task_state, save_task_state
        state_file = task_dir(task_id) / "state.json"
        if state_file.exists():
            state = load_task_state(task_id)
            state["current_step"] = current_step
            save_task_state(state)
    except Exception as exc:
        # Non-blocking — cursor persistence failure does not abort the step
        print(f"[workshop_coder] WARNING: failed to persist step cursor: {exc}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
