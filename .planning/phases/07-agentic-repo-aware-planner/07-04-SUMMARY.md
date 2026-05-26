---
plan: 07-04
phase: 07-agentic-repo-aware-planner
status: complete
completed_at: 2026-05-26
---

# Plan 07-04 Summary: Clone-Before-Planner Wiring

## What Was Built

Wired the clone-before-planner step into `workshop_build.py`, connecting the Phase 7 infrastructure (doc_resolver, workspace_dir state, planner SKILL.md) into the running pipeline.

## Changes Made

### `workshop/state.py`
- Added `clone_repo_to_workspace(state, *, repo, clone_root=None)` — clones repo into `/tmp/uws-workspace-{task_id}/{repo_name}/`, skips re-clone if `.git` already exists (idempotent resume path), sets `state["workspace_dir"]`, returns updated state
- Made `repo` parameter optional (default `""`) in `new_task_state()` for test compatibility

### `hermes-skills/workshop_build.py`
- Added `import os`, `import re` to top-level imports
- Added try/except import guard for `from workshop.doc_resolver import resolve_doc`
- Added `_extract_doc_reference(text)` helper — returns first `*.md` filename found via regex
- After registry validation: calls `clone_repo_to_workspace()`, saves state, appends `workspace_cloned` progress event
- Between clone and planner: calls `resolve_doc()` with extracted doc name and vault path
- `planner_query` now includes `workspace_dir` and `reference_doc` keys
- `coder_payload.workspace_dir` now uses `state.get("workspace_dir")` as authoritative source (falls back to diff.workspace_dir)

### `tests/phase-07/test_workspace.py`
- Activated `test_clone_saves_workspace_dir` (removed xfail decorator) — both workspace tests now pass

## Test Results

- `tests/phase-07/test_workspace.py`: 2/2 passed
- Full test suite: **84 passed, 1 xfailed** (xfail is test_plan_schema_valid, addressed in Plan 07-05)
- Phase-06 + repo-registry regression: green

## Key Files

- `hermes-skills/workshop_build.py` — clone-before-planner block + workspace_dir in state + resolve_doc call + planner query update
- `workshop/state.py` — new clone_repo_to_workspace() function

## Self-Check: PASSED

All must_haves verified:
- [x] workshop_build.py clones repo BEFORE building planner_query
- [x] state["workspace_dir"] populated and saved to state.json immediately after clone
- [x] planner_query contains "workspace_dir" and "reference_doc" keys
- [x] coder_payload reuses state["workspace_dir"] (not recomputing from diff)
- [x] existing .git directory detected → re-clone skipped (resume path)
- [x] doc_resolver.resolve_doc() called between clone and planner stage
