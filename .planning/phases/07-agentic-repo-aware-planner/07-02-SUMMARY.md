---
phase: 07-agentic-repo-aware-planner
plan: "02"
subsystem: workshop-state-doc-resolver
tags: [state, doc-resolver, planner-timeout, tdd, security]
dependency_graph:
  requires: ["07-01"]
  provides: ["workspace_dir-state-field", "doc-resolver-module", "planner-timeout-480"]
  affects: ["workshop/state.py", "workshop/stage_policy.py", "workshop/doc_resolver.py"]
tech_stack:
  added: []
  patterns: ["3-tier-doc-resolution", "path-traversal-guard-ASVS-V5.1.1", "graceful-brain-degradation"]
key_files:
  created:
    - workshop/doc_resolver.py
    - conftest.py
  modified:
    - workshop/state.py
    - workshop/stage_policy.py
    - tests/phase-07/test_workspace.py
    - tests/phase-07/test_doc_resolver.py
decisions:
  - "resolve_doc() signature uses keyword args (workspace_dir, vault_dir, brain_error) to match test stubs from plan 07-01"
  - "brain_error=True parameter enables test-time Brain degradation simulation without monkeypatching"
  - "conftest.py added at repo root to ensure workshop package importable in pytest (Rule 2 - missing critical functionality)"
metrics:
  duration: "~18 minutes"
  completed: "2026-05-26T14:00:00Z"
  tasks_completed: 2
  files_changed: 6
---

# Phase 7 Plan 2: Core State and Infrastructure Summary

Wave 1 foundational modules: workspace_dir state field, planner timeout increase, and 3-tier doc resolver — all implemented via TDD with traversal guard.

## Tasks Completed

### Task 1: Add workspace_dir to new_task_state() and raise planner timeout to 480s

Added `"workspace_dir": ""` to the return dict of `new_task_state()` in `workshop/state.py`. Changed planner `StagePolicy` timeout from 300 to 480 in `workshop/stage_policy.py`. Activated `test_new_task_state_has_workspace_dir` (removed xfail marker, added `repo="owner/repo"` arg).

**Commits:**
- `4b1af52` — feat(07-02): add workspace_dir to state and raise planner timeout to 480s

### Task 2: Create workshop/doc_resolver.py with 3-tier resolution

Created `workshop/doc_resolver.py` implementing `resolve_doc(doc_name, workspace_dir, vault_dir, brain_error)` with:
- **Tier 1**: `workspace_dir` rglob — repo-first lookup
- **Tier 2**: `vault_dir` (or `VAULT_VPS_PATH` env var, defaulting to `/srv/second-brain`) rglob with OSError guard
- **Tier 3**: Brain HTTP via `call_agent()` — guarded by try/except ImportError (skipped in unit tests), `brain_error=True` flag for test injection

Path-traversal guard validates `doc_name` rejects `..`, leading `/`, and null bytes raising `ValueError` per ASVS V5.1.1.

Activated all 4 test stubs in `test_doc_resolver.py` (removed xfail markers).

**Commits:**
- `94f614f` — feat(07-02): create workshop/doc_resolver.py with 3-tier resolution

## Verification Results

```
tests/phase-07/ — 5 passed, 2 xfailed
tests/phase-06/ + test_repo_registry.py — 27 passed (regression clean)

test_doc_resolver.py::test_tier1_repo_first PASSED
test_doc_resolver.py::test_tier2_vault_grep PASSED
test_doc_resolver.py::test_tier3_brain_degraded PASSED
test_doc_resolver.py::test_doc_name_traversal_blocked PASSED
test_workspace.py::test_new_task_state_has_workspace_dir PASSED
```

## Deviations from Plan

### Auto-added: conftest.py (Rule 2 - Missing Critical Functionality)

**Found during:** Task 1 RED phase
**Issue:** `workshop` package not on sys.path in pytest sessions — `new_task_state is None` in test stubs, causing all workshop tests to trigger `pytest.xfail()` via `_skip_if_missing()` even after removing the `@pytest.mark.xfail` decorator. Phase-04 tests have the same issue.
**Fix:** Added `conftest.py` at repo root that inserts `repo_root` into `sys.path[0]`.
**Files modified:** `conftest.py` (new)
**Commit:** `4b1af52`

### API signature adapted to test stubs

**Found during:** Task 2 analysis
**Issue:** Plan described `resolve_doc(doc_name, workspace_dir, vault_path)` positionally, but test stubs from plan 07-01 used keyword args `workspace_dir=`, `vault_dir=`, `brain_error=True`.
**Fix:** Implemented function signature as `resolve_doc(doc_name, workspace_dir=None, vault_dir=None, brain_error=False)` to match existing test contracts. The `brain_error` param serves as a test-injection flag replacing monkeypatching of `call_agent`.
**Impact:** None — the test stubs are the authoritative API contract.

## Threat Surface Scan

No new network endpoints or auth paths introduced. `doc_resolver.py` makes outbound HTTP to Brain only via `call_agent()` which already exists in `brain_http.py`. The path-traversal guard satisfies T-07-02-01 from the plan's threat model.

## Known Stubs

`test_clone_saves_workspace_dir` in `tests/phase-07/test_workspace.py` remains `@pytest.mark.xfail` — intentional, activates in Plan 04 when `clone_repo_to_workspace()` is added to `workshop_build.py`.

## Self-Check: PASSED

- `workshop/state.py` — exists, contains `"workspace_dir": ""`
- `workshop/stage_policy.py` — exists, contains `StagePolicy(timeout=480`
- `workshop/doc_resolver.py` — exists, exports `resolve_doc`, contains `VAULT_VPS_PATH`, contains `ValueError.*unsafe`
- `conftest.py` — exists at repo root
- Commit `4b1af52` — verified in git log
- Commit `94f614f` — verified in git log
