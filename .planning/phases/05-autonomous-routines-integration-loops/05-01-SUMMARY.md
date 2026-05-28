---
phase: "05"
plan: "01"
subsystem: autonomous-routines-integration-loops
tags: [brain-http, queue, dispatch-ack, fastapi, hermes-skills]
dependency_graph:
  requires: []
  provides: [brain-queue-dispatched-ack, mark-queue-entry-dispatched-helper]
  affects: [05-02, 05-03, 05-04]
tech_stack:
  added: []
  patterns: [atomic-jsonl-rewrite, fastapi-route-insertion]
key_files:
  created:
    - ultra-agents-brain/agentos/workshop_queue.py
  modified:
    - ultra-agents-brain/agentos/app.py
    - hermes-skills/brain_http.py
decisions:
  - "Used same route-insertion-at-position-0 pattern as workshop_registry.py to beat AgentOS catch-all sub-app"
  - "Atomic JSONL rewrite via tempfile+os.replace avoids partial writes on crash"
  - "mark_queue_entry_dispatched raises HTTPStatusError (not sys.exit) — caller decides error handling"
metrics:
  duration_minutes: 8
  completed_date: "2026-05-28"
  tasks_completed: 3
  tasks_total: 3
  files_created: 1
  files_modified: 2
---

# Phase 5 Plan 01: Brain Dispatched-ACK Endpoint Summary

**One-liner:** FastAPI `PUT /workshop/queue/{entry_id}/dispatched` route + httpx helper so cron skills can mark JSONL queue entries as dispatched after acting on them.

## Tasks Completed

| Task | Description | Commit | Repo |
|------|-------------|--------|------|
| 1 | Create `agentos/workshop_queue.py` with `register_queue_routes()` | 784deb7 | ultra-agents-brain |
| 2 | Wire `register_queue_routes(app)` into `agentos/app.py` | 784deb7 | ultra-agents-brain |
| 3 | Add `mark_queue_entry_dispatched` to `hermes-skills/brain_http.py` | 8c4d189 | ultra-workshop |

## Verification Results

- `python -c "import agentos.workshop_queue; print('ok')"` from Brain venv: **PASSED**
- `grep -c "mark_queue_entry_dispatched" hermes-skills/brain_http.py` returns `1`: **PASSED**
- Import of module succeeds with no FastAPI/httpx import errors: **PASSED**

## Implementation Notes

`workshop_queue.py` follows the exact pattern established by `workshop_registry.py`:

- Route inserted at position 0 of `app.router.routes` to beat the AgentOS catch-all sub-app
- Atomic JSONL file update: parse all lines, mutate target, write via `tempfile.mkstemp` + `os.replace`
- HTTP 404 for missing queue file or unknown `entry_id` (consistent with plan spec)
- `fastapi.HTTPException` used for error responses (not raw dicts — let FastAPI serialize)

`mark_queue_entry_dispatched` in `brain_http.py` uses the existing `BRAIN_BASE_URL` constant and `httpx` import with no new dependencies.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — the new route is loopback-only (same constraint as `PUT /workshop/repos`). No new network surface beyond what was already present.

## Self-Check: PASSED

- `/Users/caiobellizzi/Documents/Projects/ultra-agents-brain/agentos/workshop_queue.py`: FOUND
- `/Users/caiobellizzi/Documents/Projects/ultra-agents-brain/agentos/app.py` (modified): FOUND
- `hermes-skills/brain_http.py` (modified): FOUND
- Commit 784deb7 in ultra-agents-brain: FOUND
- Commit 8c4d189 in ultra-workshop worktree: FOUND
