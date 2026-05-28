---
phase: 09-advanced-agent-architecture
reviewed: 2026-05-28T14:15:00Z
depth: standard
files_reviewed: 34
files_reviewed_list:
  - hermes-config/agent-isolation-policy.md
  - hermes-config/review-roster.yaml
  - hermes-skills/workshop_brainstorm.py
  - hermes-skills/workshop_build.py
  - hermes-skills/workshop_merge_agent.py
  - hermes-skills/workshop_reviewer.py
  - skills/brainstorm-specialist/SKILL.md
  - skills/config-reviewer/SKILL.md
  - skills/correctness-reviewer/SKILL.md
  - skills/docs-reviewer/SKILL.md
  - skills/merge-agent/SKILL.md
  - skills/planner-specialist/SKILL.md
  - skills/python-reviewer/SKILL.md
  - skills/qa-reviewer/SKILL.md
  - skills/reactjs-reviewer/SKILL.md
  - skills/requirements-specialist/SKILL.md
  - skills/security-reviewer/SKILL.md
  - skills/typescript-reviewer/SKILL.md
  - tests/phase-08/test_quality_uplift.py
  - tests/phase-09/__init__.py
  - tests/phase-09/test_audit_log.py
  - tests/phase-09/test_brainstorm_hitl.py
  - tests/phase-09/test_cost_budget.py
  - tests/phase-09/test_merge_agent.py
  - tests/phase-09/test_requirements_brain.py
  - tests/phase-09/test_review_wave.py
  - tests/phase-09/test_worktree.py
  - workshop/cost.py
  - workshop/ledger.py
  - workshop/requirements_gate.py
  - workshop/stage_policy.py
  - workshop/types.py
  - workshop/worktree.py
findings:
  critical: 5
  warning: 6
  info: 4
  total: 15
status: issues_found
---

# Phase 09: Code Review Report

**Reviewed:** 2026-05-28T14:15:00Z
**Depth:** standard
**Files Reviewed:** 34
**Status:** issues_found

## Summary

Phase 09 delivers the wave review architecture (parallel reviewer dispatch, merge agent, brainstorm HITL, per-role budgets, worktree lifecycle, audit logging). The core abstractions are well-structured and the fallback safety logic for the roster is sound. However, five blockers were found: the `correctness` reviewer's budget exhaustion silently skips the review rather than blocking to HITL (violating the written policy); `concurrent.futures.TimeoutError` from `as_completed` is unhandled and will crash the pipeline process; the `isolation` field in the roster is parsed but never actually used to differentiate dispatch; the brainstorm approval gate can be bypassed on resume; and `worktree.py`'s `create_worktree` performs no task-ID or branch-name validation before passing values to subprocess. Six warnings and four info items follow.

---

## Critical Issues

### CR-01: `correctness` budget exhaustion silently skips review instead of blocking

**File:** `hermes-skills/workshop_build.py:196-210`

**Issue:** In `_run_one`, when `check_role_budget` raises `RoleBudgetExhausted`, only `role == "security"` re-raises. For `correctness` — which has `fallback_model_alias: null` in the roster — the code falls through to the "Non-critical exhausted, no fallback → skip" branch and returns `WaveReport(role="correctness", passed=True, findings=[])`. This silently removes the correctness review from the wave. The policy document (`agent-isolation-policy.md`, line 54) states: correctness exhaustion → `BLOCK to HITL — always-on, no substitute`.

**Fix:**
```python
except RoleBudgetExhausted:
    if role in ("security", "correctness"):  # both always-on, no substitute
        raise  # blocks pipeline; outer except in wave_dispatch re-raises
    fallback = entry.get("fallback_model_alias")
    ...
```
The outer `except RoleBudgetExhausted: raise` in the `as_completed` loop already propagates the error correctly — only the guard condition in `_run_one` needs updating.

---

### CR-02: `concurrent.futures.TimeoutError` from `as_completed` is unhandled — pipeline crash

**File:** `hermes-skills/workshop_build.py:232-237`

**Issue:** `as_completed(futures, timeout=wave_timeout)` raises `concurrent.futures.TimeoutError` at the `for` statement level when the wave-level timeout (180 s) is hit. This exception is outside the `try` block that wraps `future.result()`. It propagates up through `wave_dispatch` into `main()`, where the only outer handlers are `except ClarificationNeeded` and `except StageTimeoutForHITL`. The `TimeoutError` matches neither, so the pipeline process crashes with an unhandled exception, losing pipeline state update and leaving `state["status"]` as `"running"`.

**Fix:**
```python
try:
    for future in as_completed(futures, timeout=wave_timeout):
        try:
            results.append(future.result())
        except RoleBudgetExhausted:
            raise
        except Exception as exc:
            entry = futures[future]
            print(f"[workshop] reviewer {entry['role']!r} future failed: {exc}", ...)
except TimeoutError:
    # Wave-level timeout: cancel pending futures, surface as StageTimeoutForHITL
    for f in futures:
        f.cancel()
    raise StageTimeoutForHITL(
        "reviewer", 0,
        f"Review wave timed out after {wave_timeout}s",
    )
```
Import `from concurrent.futures import TimeoutError as FuturesTimeoutError` to avoid shadowing the builtin.

---

### CR-03: `isolation` field is parsed but never used — AgentTool isolation policy not enforced

**File:** `hermes-skills/workshop_build.py:157-248` (entire `wave_dispatch`)

**Issue:** `review-roster.yaml` sets `isolation: true` for `correctness` and `security` and `isolation: false` for the rest. `agent-isolation-policy.md` (lines 22-45) specifies that `isolation: true` roles must be dispatched via `delegate_task(..., fresh_context=True)` (AgentTool — isolated context window), while `isolation: false` roles use shared-context skill invocations. In `wave_dispatch`, the `isolation` field is loaded into `entry` from the roster but never read. All roles are dispatched identically via `run_specialist`. The stated correctness benefit (preventing prior pipeline context from biasing blocking decisions) is not implemented.

**Fix:** Read `entry.get("isolation", False)` inside `_run_one` and dispatch accordingly:
```python
if entry.get("isolation", False):
    result = delegate_task(skill_name, reviewer_query, WaveReport, timeout=per_reviewer_timeout)
else:
    result = run_specialist(skill_name, reviewer_query, WaveReport, timeout=per_reviewer_timeout)
```
If `delegate_task` is not yet implemented in the orchestrator, this is a deferred enforcement gap that must be tracked.

---

### CR-04: Brainstorm approval gate bypassed when `--resume` omits `--brainstorm`

**File:** `hermes-skills/workshop_build.py:815-854`

**Issue:** When a task is started with `--brainstorm`, exits at turn 1 with `state["next_stage"] = "brainstorm"` and `state["brainstorm_approved"]` absent/False, then resumed without the `--brainstorm` flag, the gate is silently skipped. The brainstorm block is guarded by `if args.brainstorm and ...` — if `args.brainstorm` is `False`, the block is never entered. Then `_stage_should_run(state, "triage")` returns `True` because `_STAGE_INDEX["triage"] (1) >= _STAGE_INDEX["brainstorm"] (0)`, so triage proceeds despite the unapproved brainstorm. The owner's goal-statement approval is bypassed.

**Fix:** After the brainstorm block, before the triage block, add a guard:
```python
# Enforce brainstorm approval gate if task was started with brainstorm mode
if state.get("brainstorm_turn", 0) > 0 and not state.get("brainstorm_approved"):
    print("[workshop] brainstorm gate not satisfied — re-run with --brainstorm to continue", flush=True)
    sys.exit(1)
```

---

### CR-05: `create_worktree` passes unvalidated `task_id` and `branch_name` to subprocess

**File:** `workshop/worktree.py:37-43`

**Issue:** `worktree_path = WORKTREE_BASE / task_id` — pathlib resolves `..` components, so `task_id="../etc/bad"` resolves to `/tmp/etc/bad`, escaping `WORKTREE_BASE`. Confirmed: `Path("/tmp/uws-worktrees") / "../etc/passwd"` resolves to `/tmp/etc/passwd`. Additionally, `branch_name` is passed as the last positional argument to `["git", "-C", ..., "worktree", "add", ..., "-b", branch_name]`. If `branch_name` begins with `--` (e.g., `"--detach"`), git interprets it as an option, enabling argument injection. Neither parameter is validated before use.

**Fix:**
```python
from workshop.ledger import validate_task_id

def create_worktree(repo_path: str, branch_name: str, task_id: str) -> Path:
    validate_task_id(task_id)  # raises ValueError on traversal chars
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9/_.-]{0,199}', branch_name) or branch_name.startswith('-'):
        raise ValueError(f"invalid branch_name: {branch_name!r}")
    worktree_path = WORKTREE_BASE / task_id
    # Verify path didn't escape base (defense-in-depth)
    worktree_path.resolve().relative_to(WORKTREE_BASE.resolve())
    ...
```

---

## Warnings

### WR-01: `merge` and `brainstorm` budget caps defined but `check_role_budget` never called

**File:** `workshop/cost.py:98-99` / `hermes-skills/workshop_build.py`

**Issue:** `ROLE_MONTHLY_CAPS` defines `"merge": 1500` and `"brainstorm": 2000`. The agent-isolation-policy.md states that merge budget exhaustion must block to HITL. Neither `_build_merge_report` nor the brainstorm stage call `check_role_budget` for their respective roles, so these caps are never enforced. Spend accumulates uncapped in practice.

**Fix:** Call `check_role_budget("merge")` before `_build_merge_report(wave_reports)` in `main()` (line ~1015), and `check_role_budget("brainstorm")` before each brainstorm `run_stage` call. Handle `RoleBudgetExhausted` by raising `StageTimeoutForHITL`.

---

### WR-02: `get_role_monthly_spend` uses substring match — false positive on role names

**File:** `workshop/cost.py:122-129`

**Issue:** The filter `if month_prefix in line and role in line` is a bare substring match. Role `"python"` matches any ledger line containing `"python-reviewer"`, `"python3"`, etc. Role `"docs"` could match task descriptions mentioning docs. Role `"qa"` is two characters — extremely collision-prone. Over time, the monthly spend figure for short-named roles will be inflated by false matches, causing premature budget exhaustion errors.

**Fix:** Require the role to appear as a whole word or delimited token, e.g.:
```python
import re as _re
_ROLE_PAT = _re.compile(r'\brole=' + _re.escape(role) + r'\b')
if month_prefix in line and _ROLE_PAT.search(line)
```
This assumes the curator writes `role={role}` in the ledger line, consistent with how `record_role_cost` formats the curator call.

---

### WR-03: Important findings appear in `blocking_issues` but do not block — misleading API

**File:** `hermes-skills/workshop_build.py:1022-1029`

**Issue:** `compat_review.blocking_issues` includes both `critical_findings` and `important_findings`, but `compat_review.passed = not merge_report.block_push` which is `True` whenever there are no critical findings. So a wave with only important findings produces `Review(passed=True, blocking_issues=[...non-empty...])` — a passed review with blocking issues. The review loop then `break`s immediately and proceeds to the HITL approval payload, which contains no review findings at all. Important issues are silently dropped from the owner's decision surface.

**Fix:** Either (a) rename the list to `advisory_issues` in the compat path to match its non-blocking semantics, or (b) surface important findings in the HITL approval payload:
```python
hitl_payload["advisory_findings"] = [
    f.model_dump() for f in merge_report.important_findings
]
```

---

### WR-04: `planner_query_template` parameter in `_handle_step_retry_exhausted` is unused dead code

**File:** `hermes-skills/workshop_build.py:465`

**Issue:** `planner_query_template: str` is declared as a parameter but never referenced in the function body. It is always passed as `""` from the call site (line ~997). The decompose query is built from scratch inside the function. This dead parameter inflates the function signature (13 parameters) and misleads readers into thinking a template is being applied.

**Fix:** Remove the `planner_query_template` parameter from the signature and the `""` positional argument from the call site.

---

### WR-05: `agent-isolation-policy.md` references non-existent YAML fields

**File:** `hermes-config/agent-isolation-policy.md:89,97` / `hermes-config/review-roster.yaml`

**Issue:** The policy document references `always_on: true` (line 89) and `exhaustion_behavior` (line 97 in the References section) as fields in `review-roster.yaml`. Neither field exists in the YAML. The YAML uses `isolation: true/false` (boolean) for always-on semantics, and there is no `exhaustion_behavior` field. The policy also describes `isolation` as accepting the string values `"agent"` or `"skill"` (enforcement block diagram, line 73), but the YAML and fallback roster use booleans. This creates a control-plane vs. rationale-plane divergence that will cause confusion when anyone attempts to configure a new role by following the policy doc.

**Fix:** Update the policy document to match the actual YAML schema: replace `always_on: true` references with `isolation: true`, remove the `exhaustion_behavior` field reference, and correct the dispatch diagram to show `isolation: true | false`.

---

### WR-06: Stale `@pytest.mark.skip` in `test_brainstorm_hitl.py` — brainstorm stage is now implemented

**File:** `tests/phase-09/test_brainstorm_hitl.py:17,31`

**Issue:** Both `test_brainstorm_loop_does_not_exit_without_approval` and `test_brainstorm_loop_exits_when_approved` are marked `skip(reason="brainstorm stage not yet implemented (09-03)")`. The brainstorm stage block IS implemented in `workshop_build.py` (lines 815-854) as part of Phase 09. These are the only tests covering the brainstorm approval gate; leaving them skipped means zero test coverage for a security-relevant gate (CR-04 above has no test to catch it). The test bodies raise `NotImplementedError`, which would produce a misleading error if the skip marker were removed without implementing the test body.

**Fix:** Implement both tests by patching `subprocess.run` / `run_specialist` to control `BrainstormResult.approved`, driving `main()` via `sys.argv` with `--brainstorm --resume`, and asserting `state["next_stage"]` after each path. Remove the `@pytest.mark.skip` decorators.

---

## Info

### IN-01: `workshop_merge_agent.py` and `workshop_reviewer.py` use `exec(compile(...))` to load `workshop_build.py`

**File:** `hermes-skills/workshop_merge_agent.py:52-56` / `hermes-skills/workshop_reviewer.py:19-23`

**Issue:** Both shims load `workshop_build.py` by reading its source text, splitting on `"\ndef main("`, and `exec`-compiling the result. This is fragile: any refactor that moves, renames, or overloads `main` in `workshop_build.py` will silently produce an incorrect namespace (the split fails open, compiling the entire file and executing `main()` on import). The `# noqa: S102` suppression hides the bandit warning. A proper `importlib.util.spec_from_file_location` import would be both safer and cleaner given the file is local.

**Suggestion:** Refactor `_build_merge_report`, `wave_dispatch`, and `load_review_roster` into a `workshop/wave.py` module importable without loading the entire CLI entrypoint.

---

### IN-02: `test_quality_uplift.py` uses relative path for module loading

**File:** `tests/phase-08/test_quality_uplift.py:24-25`

**Issue:** `_load_module("workshop_build_phase08", "hermes-skills/workshop_build.py")` uses a relative path. This works only when pytest is invoked from the project root. Running `pytest tests/phase-08/` from any other directory silently fails with `FileNotFoundError` (or, in some pytest configurations, a confusing `ImportError`).

**Suggestion:** Use `Path(__file__).parent.parent.parent / "hermes-skills" / "workshop_build.py"` (the same pattern already used in `tests/phase-09/test_review_wave.py` and `test_merge_agent.py`).

---

### IN-03: Budget ledger parsing relies on implicit brain curator format

**File:** `workshop/cost.py:33-46`, `workshop/cost.py:112-129`

**Issue:** `get_daily_spend` and `get_role_monthly_spend` parse `LEDGER_PATH` looking for `amount:\s*([\d.]+)` lines. `record_cost` and `record_role_cost` send `record-cost&amount={value}&...` to the brain curator via HTTP. The mapping from the HTTP query string to `amount: {value}` in the markdown ledger is an implicit contract with the brain curator agent — undocumented and unverifiable from this codebase. If the curator writes a different format, all budget checks permanently return `0.0` and caps are never enforced.

**Suggestion:** Add a `LEDGER_FORMAT_NOTE` constant or docstring explaining the expected line format, and add a test that parses a known ledger file snippet to validate the regex against the format the curator actually writes.

---

### IN-04: `remove_worktree` uses `worktree_path.parent` as default `repo_path` — semantically wrong

**File:** `workshop/worktree.py:67-68`

**Issue:** When `repo_path is None`, the fallback is `str(worktree_path.parent)`. For `WORKTREE_BASE = /tmp/uws-worktrees` and `worktree_path = /tmp/uws-worktrees/ws-abc`, this sets `repo_path = /tmp/uws-worktrees` — which is not a git repository. The `git -C /tmp/uws-worktrees worktree remove ...` command will fail (not a git repo), and the shutil fallback on line 79 will then silently remove the directory without releasing the git worktree metadata in the main repo. The worktree entry remains in the main repo's `.git/worktrees/` indefinitely.

**Suggestion:** Remove the `repo_path is None` default; require callers to always pass `repo_path`. Raise `ValueError` if it is None.

---

_Reviewed: 2026-05-28T14:15:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
