---
phase: 04-build-fix-pipeline
plan: "01"
subsystem: workshop-package
tags: [python, pydantic, subprocess, architecture-b, circuit-breaker, ledger]
dependency_graph:
  requires: ["04-00"]
  provides: ["workshop.types", "workshop.orchestrator", "workshop.ledger", "workshop.cost"]
  affects: ["04-02", "04-03"]
tech_stack:
  added: ["pydantic>=2.0"]
  patterns: ["subprocess.run(shell=False)", "importlib for hyphenated modules", "JSONL append writer", "circuit breaker"]
key_files:
  created:
    - workshop/__init__.py
    - workshop/types.py
    - workshop/orchestrator.py
    - workshop/ledger.py
    - workshop/cost.py
    - tests/phase-04/__init__.py
    - tests/phase-04/test_orchestrator.py
    - tests/phase-04/test_ledger.py
    - tests/phase-04/test_cost.py
  modified: []
decisions:
  - "Architecture B confirmed: run_specialist() uses subprocess.run(shell=False) targeting hermes-skill-run.sh — no delegate_typed, no clarify_gateway"
  - "Diff.workspace_dir is str (not Optional) — coder always sets it, pr_opener reads it"
  - "cost.py loads brain_http via importlib to handle hyphenated filename; gracefully degrades to None if file absent (VPS-only path)"
  - "BudgetExhausted threshold $20 (hard), BudgetWarning threshold $18 (cron mode only)"
metrics:
  duration: "~8 minutes"
  completed: "2026-05-22T01:57:00Z"
  tasks_completed: 2
  files_created: 9
---

# Phase 4 Plan 01: Workshop Package Foundation Summary

**One-liner:** Pydantic v2 schemas and Architecture B subprocess runner with circuit-breaker cost control and JSONL audit ledger.

## What Was Built

The `workshop/` Python package — the pure-Python foundation all Phase 4 pipeline scripts (Plans 02 and 03) depend on. Four modules, all importable from the Hermes venv without VPS connectivity for local unit tests.

### workshop/types.py
Seven Pydantic v2 schema classes:
- `PlanStep` — step id, description, optional file list
- `Plan` — goal, steps, affected_files
- `FileChange` — path + diff text
- `Diff` — summary, changes list, branch name, `workspace_dir: str` (threaded from coder to pr_opener)
- `Review` — passed bool, feedback, blocking_issues list
- `Issue` — GitHub issue: url, title, body, number
- `IngestResult` — run_id, status, adr_path

### workshop/orchestrator.py
Architecture B subprocess runner (no delegate_typed, no clarify_gateway):
- `run_specialist(skill_name, query_json, output_schema, dry_run, timeout)` — calls `hermes-skill-run.sh` via `subprocess.run(shell=False)`, parses JSON stdout, returns validated Pydantic model
- `_extract_json(text)` — finds first `{...}` span in text; raises `ValueError` if absent
- Raises `RuntimeError` on non-zero exit, `subprocess.TimeoutExpired` on timeout, `ValidationError` on bad JSON

### workshop/ledger.py
Two-ledger task audit writer:
- `task_dir(task_id)` — returns `~/.ultra-workshop/tasks/<id>/`, creates with parents=True
- `append_progress(task_id, event, data)` — appends JSONL line with UTC timestamp to `progress_log.jsonl`
- `write_task_ledger(task_id, goal, status, pr_url)` — writes Markdown `task_ledger.md`

### workshop/cost.py
Circuit-breaker cost module:
- `get_daily_spend()` — reads `/srv/second-brain/_system/cost-ledger.md`, sums today's `amount:` entries; returns 0.0 if file absent
- `record_cost(task_id, amount, model)` — posts to Brain curator via importlib-loaded `brain_http.py`; non-blocking on failure
- `check_circuit_breaker(mode)` — raises `BudgetExhausted` at $20; raises `BudgetWarning` at $18 in cron mode
- `BudgetExhausted`, `BudgetWarning` exception classes

## Test Results

18 unit tests (9 orchestrator + 4 ledger + 5 cost) — all pass.

TDD gate sequence per task:
- Task 1: RED (`7b038b8`) → GREEN (`95e2948`)
- Task 2: RED (`728fffd`) → GREEN (`958bcdf`)

## Commits

| Hash | Type | Description |
|------|------|-------------|
| `7b038b8` | test | RED — 9 failing tests for types.py and orchestrator.py |
| `95e2948` | feat | GREEN — workshop/types.py and workshop/orchestrator.py |
| `728fffd` | test | RED — 9 failing tests for ledger.py and cost.py |
| `958bcdf` | feat | GREEN — workshop/ledger.py and workshop/cost.py |

## Verification Passed

All 6 plan-level verification checks:

```
python -m pytest tests/phase-04/ -q → 18 passed
import workshop.types, workshop.orchestrator, workshop.ledger, workshop.cost → ok
grep \.schema()\|\.parse_raw()\|\.json() workshop/ → 0 matches
grep shell=True workshop/ → 0 matches
grep delegate_typed\|_call_delegate_task\|clarify_gateway workshop/ → 0 matches
from workshop.types import Diff; assert 'workspace_dir' in Diff.model_fields → ok
```

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all modules are fully implemented with no placeholder values or hardcoded empty returns that flow to callers.

## Threat Flags

No new security-relevant surface beyond the plan's threat model:
- `run_specialist()` uses `shell=False` — argv injection mitigated (T-04-01-04)
- `cost.py` reads cost-ledger.md but never writes it directly (T-04-01-01)
- `progress_log.jsonl` written to `/home/uws/.ultra-workshop/` path (T-04-01-03)
- `run_specialist()` has `timeout=300` default (T-04-01-02)

## TDD Gate Compliance

- Task 1: RED gate `7b038b8` (test commit) → GREEN gate `95e2948` (feat commit) ✓
- Task 2: RED gate `728fffd` (test commit) → GREEN gate `958bcdf` (feat commit) ✓

## Self-Check: PASSED

Files verified to exist:
- workshop/__init__.py: FOUND
- workshop/types.py: FOUND
- workshop/orchestrator.py: FOUND
- workshop/ledger.py: FOUND
- workshop/cost.py: FOUND
- tests/phase-04/test_orchestrator.py: FOUND
- tests/phase-04/test_ledger.py: FOUND
- tests/phase-04/test_cost.py: FOUND

Commits verified:
- 7b038b8: FOUND
- 95e2948: FOUND
- 728fffd: FOUND
- 958bcdf: FOUND
