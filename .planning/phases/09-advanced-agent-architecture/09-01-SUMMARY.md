---
phase: "09-advanced-agent-architecture"
plan: "09-01"
subsystem: "workshop-core"
tags: ["pydantic", "budget", "audit", "reviewer-types", "phase-09-foundation"]
dependency_graph:
  requires: []
  provides:
    - "workshop.types.ReviewFinding"
    - "workshop.types.WaveReport"
    - "workshop.types.MergeReport"
    - "workshop.cost.ROLE_MONTHLY_CAPS"
    - "workshop.cost.RoleBudgetExhausted"
    - "workshop.cost.RoleBudgetWarning"
    - "workshop.cost.check_role_budget"
    - "workshop.cost.get_role_monthly_spend"
    - "workshop.cost.record_role_cost"
    - "workshop.ledger.append_audit"
    - "hermes-config/review-roster.yaml"
  affects:
    - "09-02 (parallel reviewer wave)"
    - "09-03 (brainstorm stage)"
tech_stack:
  added: []
  patterns:
    - "Pydantic field_validator with mode=before for case-normalizing enums"
    - "importlib.util dynamic module load for hyphenated filenames"
    - "threading.Thread daemon=True fire-and-forget pattern"
    - "fail-open try/except around external Brain calls"
key_files:
  created:
    - "tests/phase-09/__init__.py"
    - "tests/phase-09/test_cost_budget.py"
    - "tests/phase-09/test_audit_log.py"
    - "hermes-config/review-roster.yaml"
  modified:
    - "workshop/types.py"
    - "workshop/cost.py"
    - "workshop/ledger.py"
    - "pyproject.toml"
decisions:
  - "Per-role budget caps stored as int cents (not float USD) to avoid float precision edge cases in 80% threshold comparisons"
  - "append_audit uses daemon thread so it never blocks pipeline shutdown; failures silently swallowed (fail-open)"
  - "check_role_budget calls brain notify before raising exception to ensure Telegram alert fires even if caller catches and swallows the exception"
  - "Severity normalization handles HIGH/CRITICAL→Critical, MEDIUM/IMPORTANT→Important, LOW/MINOR→Minor case-insensitively"
metrics:
  duration: "~6 minutes"
  completed: "2026-05-27"
  tasks_completed: 3
  tasks_total: 3
  files_created: 4
  files_modified: 4
requirements_satisfied:
  - REQ-ws-044
  - REQ-ws-045
---

# Phase 09 Plan 01: Data Model and Infrastructure Foundation Summary

**One-liner:** Per-role Pydantic review types (ReviewFinding/WaveReport/MergeReport) with severity normalization, per-role monthly budget tracking with Telegram alerts (check_role_budget), fire-and-forget audit logging (append_audit), and 8-entry review roster YAML.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wave 0 — Create SC-2 and SC-3 test stubs (RED) | 858fb4e | tests/phase-09/__init__.py, test_cost_budget.py, test_audit_log.py, pyproject.toml |
| 2 | Add ReviewFinding/WaveReport/MergeReport + review-roster.yaml | a3ab8bf | workshop/types.py, hermes-config/review-roster.yaml |
| 3 | Extend cost.py with per-role budget + ledger.py with append_audit (GREEN) | 498cc6f | workshop/cost.py, workshop/ledger.py |

## Verification Results

All plan verification steps passed:

1. `pytest tests/phase-09/ -x -q` — 9 passed (SC-2 and SC-3 GREEN)
2. `pytest tests/ -x -q` — 106 passed (97 pre-existing + 9 new, no regressions)
3. `ReviewFinding(severity='HIGH').severity == 'Critical'` — confirmed
4. `ROLE_MONTHLY_CAPS['security'] == 4000` — confirmed
5. `from workshop.ledger import append_audit` — confirmed
6. `review-roster.yaml` has exactly 8 entries — confirmed

## Key Implementation Details

### workshop/types.py — ReviewFinding severity normalization

`field_validator("severity", mode="before")` maps:
- `"CRITICAL"` / `"HIGH"` → `"Critical"`
- `"IMPORTANT"` / `"MEDIUM"` → `"Important"`
- `"MINOR"` / `"LOW"` → `"Minor"`

Unrecognized values raise `ValueError`.

### workshop/cost.py — Per-role budget layer

`ROLE_MONTHLY_CAPS` has 11 roles (all Wave 2 reviewer roles plus merge, brainstorm, pipeline_pool). `check_role_budget` enforces:
- At 80%: sends `notify` agent Telegram warning, raises `RoleBudgetWarning`
- At 100%: sends `notify` agent Telegram alert with AUTO-PAUSE message, raises `RoleBudgetExhausted`

Both notify calls are wrapped in `try/except` (fail-open). The `_brain_http` module-level object from the existing importlib load is reused — no second load.

### workshop/ledger.py — append_audit

Uses a separate importlib load of `brain_http.py` (module name `brain_http_ledger` to avoid collision with cost.py's load). Launches `threading.Thread(daemon=True)` for fire-and-forget delivery to the `ingest` agent. Returns immediately — the non-blocking test confirms return in < 0.5s even with a slow mock.

### hermes-config/review-roster.yaml

8 reviewer entries:
- `correctness`, `security`: `isolation: true`, `file_patterns: []`, `fallback_model_alias: null` (always-on)
- `python`, `typescript`, `reactjs`, `qa`, `docs`, `config`: `isolation: false`, `fallback_model_alias: cheap-fast`

## Deviations from Plan

None — plan executed exactly as written.

## Threat Surface Scan

No new network endpoints or auth paths were introduced. All Brain HTTP calls route to `127.0.0.1:7000` (loopback) via the existing `_brain_http` module. The new `notify` agent routing in `check_role_budget` uses the same loopback transport — no new external surface.

Threat T-09-01-04 (role tag injection in `record_role_cost`) mitigated: `record_role_cost` validates `role` against `ROLE_MONTHLY_CAPS` keys before constructing the curator message string.

## Self-Check

Files exist:
- [x] tests/phase-09/__init__.py
- [x] tests/phase-09/test_cost_budget.py
- [x] tests/phase-09/test_audit_log.py
- [x] hermes-config/review-roster.yaml
- [x] workshop/types.py (modified)
- [x] workshop/cost.py (modified)
- [x] workshop/ledger.py (modified)

Commits exist:
- [x] 858fb4e — test(09-01): add RED test stubs
- [x] a3ab8bf — feat(09-01): add ReviewFinding/WaveReport/MergeReport types and review-roster.yaml
- [x] 498cc6f — feat(09-01): extend cost.py with per-role budget and ledger.py with append_audit

## Self-Check: PASSED
