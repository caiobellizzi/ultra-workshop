---
phase: "07"
plan: "01"
subsystem: test-scaffold
tags: [testing, phase-07, hermes, vps-verification]
dependency_graph:
  requires: []
  provides:
    - tests/phase-07/ pytest package (all xfail/skip, exits 0)
    - tests/phase-07/hermes-tool-notes.txt (confirmed tool IDs for Plan 03)
  affects:
    - plans/07-02 (uses hermes-tool-notes.txt for doc_resolver implementation)
    - plans/07-03 (uses hermes-tool-notes.txt for SKILL.md planner rewrite)
tech_stack:
  added: []
  patterns:
    - pytest xfail stubs (from __future__ annotations, no test classes, tmp_path)
    - bats skip stubs (skip directive pending implementation)
key_files:
  created:
    - tests/phase-07/__init__.py
    - tests/phase-07/test_doc_resolver.py
    - tests/phase-07/test_workspace.py
    - tests/phase-07/test_planner_llm.py
    - tests/phase-07/planner-smoke.bats
    - tests/phase-07/hermes-tool-notes.txt
  modified: []
decisions:
  - "Hermes file tool names are read_file and search_files — NOT list_files/grep_files (RESEARCH.md A2/A3 assumptions corrected)"
  - "specialist-home-orchestrator has no HERMES.md and no tool restrictions; planner write/web/exec forbidding must be enforced via SKILL.md only"
  - "test_plan_schema_valid tests doc_refs field (not yet in Plan) rather than existing Plan fields, ensuring it truly xfails"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-26"
  tasks_completed: 2
  files_created: 6
---

# Phase 07 Plan 01: Test Scaffold and Hermes VPS Verification Summary

Wave 0 prerequisite complete: phase-07 test package created with 7 xfail stubs plus 2 skipped bats entries, and the two medium-risk assumptions from RESEARCH.md resolved via live VPS verification.

## What Was Built

### Task 1 — Test scaffold (commit cfd5908)

Created `tests/phase-07/` as a pytest-discoverable package mirroring the style of `tests/test_repo_registry.py`:

- `__init__.py` — empty package init
- `test_doc_resolver.py` — 4 xfail stubs: tier-1 repo lookup, tier-2 vault grep, tier-3 Brain degraded, path-traversal rejection
- `test_workspace.py` — 2 xfail stubs: `workspace_dir` key in `new_task_state()`, clone saves workspace_dir
- `test_planner_llm.py` — 1 xfail stub: `Plan.doc_refs` field validation (new field to be added in Plan 02)
- `planner-smoke.bats` — 2 bats entries with `skip` directive (pending `hermes-skill-run.sh` update in Plan 03)

`python -m pytest tests/phase-07/ -v` exits 0 with all 7 tests xfailed. Phase-06 + `test_repo_registry.py` regression (29 tests) stays green.

### Task 2 — VPS verification (commit aa6e099)

Human ran `hermes tools list` equivalent against the live VPS. Key findings documented in `tests/phase-07/hermes-tool-notes.txt`:

**Critical correction (Assumptions A2/A3 from RESEARCH.md):**
- RESEARCH.md assumed tool names: `read_file`, `list_files`, `grep_files`
- Actual names in `/opt/ultra-workshop/hermes/toolsets.py`: `read_file`, `search_files`
- `list_files` and `grep_files` do NOT exist in this binary

**Orchestrator state:**
- No `HERMES.md` in `specialist-home-orchestrator/`
- `config.yaml` has `approvals.mode=off`, no tool restrictions, all toolsets enabled by default
- Planner `write_file`/`patch`/`web_*` forbidding must be enforced via SKILL.md forbidden list (not config)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_plan_schema_valid unexpectedly xpassed on first run**
- **Found during:** Task 1 verification
- **Issue:** The original test used `{"goal": "test", "steps": [], "affected_files": []}` which matches the CURRENT Plan schema exactly, so it passed rather than xfailed. This would mask the Phase 7 schema change.
- **Fix:** Updated test to validate the NEW `doc_refs` field (not yet present in Plan model), ensuring it truly xfails until Plan 02 adds the field.
- **Files modified:** `tests/phase-07/test_planner_llm.py`
- **Commit:** cfd5908 (included in same task commit)

### VPS Assumption Corrections

**Assumption A2 corrected:** Tool name `list_files` does not exist — correct name is `search_files`. Plan 03 must use `read_file` and `search_files` in SKILL.md allowed tools.

**Assumption A3 corrected:** No `HERMES.md` exists and no tool restrictions are present in specialist-home-orchestrator. All write/web/exec restrictions must be SKILL.md-only.

## Verification Results

- `python -m pytest tests/phase-07/ -v` — 7 xfailed, 0 failures (exits 0)
- `python -m pytest tests/phase-06/ tests/test_repo_registry.py -q` — 29 passed (regression clean)
- `tests/phase-07/hermes-tool-notes.txt` exists with confirmed tool IDs and allowlist state

## Self-Check: PASSED

- [x] tests/phase-07/__init__.py exists
- [x] tests/phase-07/test_doc_resolver.py exists (4 test functions)
- [x] tests/phase-07/test_workspace.py exists (2 test functions)
- [x] tests/phase-07/test_planner_llm.py exists (1 test function)
- [x] tests/phase-07/planner-smoke.bats exists (2 @test entries)
- [x] tests/phase-07/hermes-tool-notes.txt exists with confirmed tool names
- [x] Commit cfd5908 exists (test scaffold)
- [x] Commit aa6e099 exists (hermes-tool-notes.txt)
