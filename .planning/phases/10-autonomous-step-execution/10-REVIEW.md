---
phase: 10-autonomous-step-execution
reviewed: 2026-05-26T23:45:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - deploy/litellm/config.yaml
  - hermes-skills/aider_runner.py
  - hermes-skills/workshop_coder.py
  - hermes-skills/workshop_build.py
  - workshop/stage_policy.py
  - workshop/state.py
  - workshop/orchestrator.py
  - workshop/planner.py
  - workshop/types.py
  - skills/planner-specialist/SKILL.md
  - tests/phase-06/test_aider_runner.py
  - tests/phase-06/test_workshop_coder.py
  - tests/phase-04/model-matrix-smoke.bats
  - tests/phase-04/test_workshop_build.py
  - tests/phase-04/test_workshop_continue.py
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-05-26T23:45:00Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Phase 10 introduces per-step autonomous execution in `workshop_coder.py`, an idle watchdog (`_run_aider_runner`), step cursor persistence for resume, auto-decompose of failing steps (`_handle_step_retry_exhausted`), and per-stage NIM model aliases in `config.yaml`. The architecture is generally sound, but two blockers were found: the resume path unconditionally resets the task branch (destroying previously committed steps), and `_terminate_process_group` has an unguarded `subprocess.TimeoutExpired` after `SIGKILL`. Five warnings cover an empty-GH_TOKEN injection, an overly broad path blocklist, a dead `planner_query_template` parameter, and minor JSON extraction brittleness.

---

## Critical Issues

### CR-01: Resume path destroys previously committed step commits

**File:** `hermes-skills/workshop_coder.py:462-465`

**Issue:** `git checkout -B branch default_branch` unconditionally force-resets the `workshop/<task_id>` branch to `default_branch`, even when `start_step > 0` (resume). The comment at line 456–458 says "Prior steps' commits must survive" but the code does the opposite: every invocation of `workshop_coder.py` resets the branch pointer to the default branch, discarding all commits made by prior steps. On a resume run, the skipped steps (lines 522–525) produce no new commits, so the branch ends up containing only the work done from `start_step` onward, with prior steps permanently lost.

**Fix:**
```python
# Only hard-reset the branch when starting from step 0.
# On resume (start_step > 0) keep the existing branch pointer so prior commits survive.
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
```

---

### CR-02: Unhandled `subprocess.TimeoutExpired` in `_terminate_process_group` after SIGKILL

**File:** `hermes-skills/workshop_coder.py:284`

**Issue:** After sending `SIGKILL`, the code calls `process.wait(timeout=5)` (line 284) with no exception handler. If the kernel does not reap the process within 5 seconds (possible in container environments where cgroups freeze the process), `subprocess.TimeoutExpired` propagates uncaught out of `_terminate_process_group`, bypassing the `TimeoutExpired` re-raise in `_run_aider_runner` and surfacing as an unhandled exception in the caller. The first `process.wait(timeout=5)` after `SIGTERM` is correctly wrapped (lines 278–283), but the post-SIGKILL wait is not.

**Fix:**
```python
try:
    os.killpg(process.pid, signal.SIGKILL)
except ProcessLookupError:
    return
try:
    process.wait(timeout=5)
except subprocess.TimeoutExpired:
    pass  # SIGKILL was sent; process will be reaped by OS eventually
```

---

## Warnings

### WR-01: Empty `GH_TOKEN` injected into `gh repo clone` environment when `GITHUB_PAT` is unset

**File:** `hermes-skills/workshop_coder.py:448`

**Issue:** `os.environ.get("GITHUB_PAT", "")` returns `""` when `GITHUB_PAT` is not set, and `""` is then injected as `GH_TOKEN`. Setting `GH_TOKEN=""` in the subprocess environment explicitly overrides any `GH_TOKEN` that `gh` would otherwise inherit from the parent environment (e.g., a CI-injected token), causing `gh repo clone` to fail authentication even when a valid token exists. The `state.py` helper at line 110 handles this correctly with `os.environ.get("GITHUB_PAT") or os.environ.get("GH_TOKEN")`, but `workshop_coder.py` does not apply the same pattern.

**Fix:**
```python
github_token = os.environ.get("GITHUB_PAT") or os.environ.get("GH_TOKEN", "")
clone = subprocess.run(
    ["gh", "repo", "clone", repo_full_name, str(workspace)],
    capture_output=True,
    text=True,
    shell=False,
    env={**os.environ, "GH_TOKEN": github_token},
)
```

---

### WR-02: `_valid_reviewable_path` false-positive blocks legitimate `pytests/` directories

**File:** `hermes-skills/workshop_coder.py:112`

**Issue:** The blocklist check `rel_path.startswith(("bash ", "curl ", "pip ", "pytest", "python ", "sh "))` uses `"pytest"` without a trailing space or separator. This means any path beginning with `pytest` is rejected — including legitimate test directories named `pytests/`, files like `pytest_results.txt`, or paths like `pytest_helpers/base.py`. The intent is to block aider's shell-command artifacts (e.g., the literal string `"pytest tests"`), but the guard is broader than necessary. Notably `"python "` and `"sh "` include a space, but `"pytest"` and `"pip "` are inconsistent.

**Fix:**
```python
# Replace bare "pytest" with "pytest " (trailing space) to match only command invocations
if rel_path.startswith(("bash ", "curl ", "pip ", "pytest ", "python ", "sh ")):
    return False
# Keep exact-match blocklist for the remaining bare words
if rel_path in {"pytest", "python", "pip"}:
    return False
```

---

### WR-03: Dead `planner_query_template` parameter in `_handle_step_retry_exhausted`

**File:** `hermes-skills/workshop_build.py:250` (parameter declaration), `733–737` (call site)

**Issue:** `_handle_step_retry_exhausted` accepts a `planner_query_template: str` parameter at position 5, but the parameter is never read inside the function body — the decompose query is built from scratch at lines 335–347. The caller (line 734) passes an empty string `""` as a positional argument. This dead parameter is a maintenance hazard: any future reader may think the template is being used when it is not, and future changes to add template logic will produce silent no-ops if they use this parameter.

**Fix:** Remove the dead parameter from the signature and the corresponding `""` argument at the call site:
```python
# In _handle_step_retry_exhausted signature, remove:
#     planner_query_template: str,

# At line 734, remove the "" positional argument:
diff = _handle_step_retry_exhausted(
    exc, state, task_id, plan,
    run_stage, stage_model_alias, append_progress, save_task_state, Diff, Plan,
    task_start,
)
```

---

### WR-04: `_extract_json` uses `rfind("}")` — can silently extract malformed multi-object output

**File:** `workshop/orchestrator.py:58–68`

**Issue:** The extractor finds the first `{` and the **last** `}` in the cleaned text. If a specialist emits a preamble JSON object followed by the real output (e.g., a status blob then the plan), the extractor returns the span from the first `{` to the last `}`, which is not valid JSON and causes `json.loads` to raise. The actual failure mode is a cryptic `JSONDecodeError` rather than a clear "multiple JSON objects found" diagnostic. While `<think>` blocks are stripped, non-think prose containing braces is not. The `_FENCE_RE` path mitigates for fenced output, but unfenced multi-object output is a realistic NIM model behavior.

**Fix:** After extracting `text[start:end+1]`, validate the extracted span immediately before `json.loads` to surface a cleaner error:
```python
candidate = text[start: end + 1]
# Reject if there is another "{" after the first balanced "}" (multiple objects)
try:
    payload = json.loads(candidate)
except json.JSONDecodeError as exc:
    prefix = f"[{skill_name}] " if skill_name else ""
    raise ValueError(f"{prefix}JSON extraction produced invalid JSON: {exc}") from exc
return candidate
```

---

### WR-05: `_run_aider_runner` does not reset `cwd` — inherits caller's working directory

**File:** `hermes-skills/workshop_coder.py:300–308`

**Issue:** `subprocess.Popen` is called without a `cwd` argument. The working directory inherited by the aider subprocess is whatever `workshop_coder.py` was launched from (e.g., `/opt/ultra-workshop`), not the workspace directory. Aider resolves relative file paths against `cwd`, so any relative `step_files` paths passed via `--workspace-file` (lines 553–557) would resolve incorrectly unless they are absolute. `step_files` are built as `str(workspace / f)` (line 515), which produces absolute paths — so in practice this is safe today. However, the missing `cwd` creates a fragile coupling: if `step_files` ever omits the `workspace /` prefix, the bug silently activates.

**Fix:**
```python
process = subprocess.Popen(
    argv,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    shell=False,
    cwd=str(workspace),   # add this
    env=env,
    start_new_session=True,
)
```
`workspace` is available in the calling scope (`main()`) but not in `_run_aider_runner`. Pass it as a parameter or document the absolute-paths invariant explicitly.

---

## Info

### IN-01: `private-worker` timeout of 30s is likely too low for LLM inference

**File:** `deploy/litellm/config.yaml:58`

**Issue:** `private-worker` has `timeout: 30` seconds. LM Studio inference for any non-trivial prompt typically exceeds 30 seconds, especially for models > 7B parameters. If `private-worker` is used for any real task (not just health checks), this will produce chronic timeouts before falling through to `cheap-worker`. The comment says "local only" but does not explain the 30s choice.

**Fix:** Either document that `private-worker` is intentionally reserved for sub-second health checks, or raise the timeout to match `cheap-worker` (180s).

---

### IN-02: `Diff` model silently drops `repo_full_name` and `default_branch` fields emitted by `workshop_coder.py`

**File:** `hermes-skills/workshop_coder.py:655–661`, `workshop/types.py:29–37`

**Issue:** `workshop_coder.py` emits `repo_full_name` and `default_branch` in the JSON payload (lines 656–657), but `Diff` (in `types.py`) has no corresponding fields. Pydantic v2 ignores unknown fields by default, so these values are silently discarded when `workshop_build.py` deserializes the coder output via `Diff.model_validate(payload)`. The downstream code (`workshop_build.py` approval path) reads `repo_full_name` from local state variables rather than from `diff`, so there is no functional breakage today. The emitted fields are dead weight, creating a misleading contract between `workshop_coder.py` and its consumer.

**Fix:** Either add `repo_full_name: str = ""` and `default_branch: str = ""` to `Diff`, or remove the two fields from the `workshop_coder.py` payload.

---

### IN-03: `test_sanitize_unreviewable_changes_removes_command_artifacts` asserts order-dependent list equality

**File:** `tests/phase-06/test_workshop_coder.py:126–130`

**Issue:** The test at line 126 asserts `sanitized == ["notes.md", "pytest tests", "python openharness_orchestration.py"]` using list equality, which requires exact ordering. The ordering depends on `git diff --name-only -z` output, which is alphabetical. Alphabetical order holds here (`n < p < p`), but if a future test case introduces a path that sorts differently, the test fails without a logic error. Using `assert set(sanitized) == {...}` or `assert sorted(sanitized) == sorted([...])` would be more robust.

**Fix:**
```python
assert sorted(sanitized) == sorted([
    "notes.md",
    "pytest tests",
    "python openharness_orchestration.py",
])
```

---

_Reviewed: 2026-05-26T23:45:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
