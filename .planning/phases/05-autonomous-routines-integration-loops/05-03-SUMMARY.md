---
phase: "05"
plan: "03"
subsystem: hermes-skills
tags: [cron, systemd, dispatch-loop, queue, autonomous]
dependency_graph:
  requires: [05-01, 05-02]
  provides: [uws-bug-scan-fastpoll.service, cron_bug_scan_fastpoll.py]
  affects: [workshop-queue, deploy/systemd]
tech_stack:
  added: []
  patterns: [pid-file-singleton, quiet-hours-deferral, zero-hitl-partition, circuit-breaker-guard]
key_files:
  created:
    - hermes-skills/cron_bug_scan_fastpoll.py
    - deploy/systemd/uws-bug-scan-fastpoll.service
  modified: []
decisions:
  - Zero-HITL verbs (post-to-telegram) dispatched unconditionally, bypassing quiet-hours guard
  - Unknown verbs ACK'd immediately to prevent infinite queue re-processing
  - PID file written at module level before imports to prevent race window
metrics:
  duration: "8 minutes"
  completed: "2026-05-28T19:40:00Z"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 05 Plan 03: Bug-Scan Fast-Poll systemd Service Summary

**One-liner:** 30-second dispatch loop with quiet-hours deferral, PID-lock singleton, and systemd unit targeting the uws venv Python.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | `cron_bug_scan_fastpoll.py` infinite poll loop | 180488b | hermes-skills/cron_bug_scan_fastpoll.py |
| 2 | `uws-bug-scan-fastpoll.service` systemd unit | cfef477 | deploy/systemd/uws-bug-scan-fastpoll.service |

## What Was Built

### `cron_bug_scan_fastpoll.py`

An infinite poll loop that runs every 30 seconds dispatching workshop queue entries (`vault/_system/.workshop-queue.jsonl`) that are confirmed, not yet dispatched, and have an action verb.

Key behaviors:
- **Single-instance lock:** PID file at `/tmp/uws-fastpoll.pid` with stale-PID detection via `os.kill(pid, 0)`.
- **Circuit breaker:** Calls `check_circuit_breaker(mode="cron")` on each poll; skips dispatch if budget is exhausted or warned.
- **Verb partitioning:** `post-to-telegram` is zero-HITL and dispatched unconditionally. All other verbs (`build`, `fix`, `link-orphans`) respect quiet hours.
- **Quiet-hours deferral:** 22:00–07:00 local time — HITL-required entries are logged and deferred without modification.
- **Dispatch targets:**
  - `post-to-telegram` → `telegram_alert.send_alert()` + ACK
  - `link-orphans` → no-op ACK only (pre-approved, logged)
  - `build` → `subprocess.run(workshop_build.py repo task)` + ACK
  - `fix` → `subprocess.run(workshop_fix.py issue_url)` + ACK
  - unknown → warning log + ACK (prevents infinite re-processing)
- **PID cleanup:** `atexit.register` + `try/finally` around the main loop.

### `uws-bug-scan-fastpoll.service`

systemd unit with exact spec from plan:
- `User=uws`, `EnvironmentFile=/etc/uws/env`
- `ExecStart` uses `/opt/ultra-workshop/.venv/bin/python`
- `Restart=always`, `RestartSec=10s`
- `After=network.target uws-hermes.service`

## Verification Results

1. `python3 -c "import ast; ast.parse(...); print('syntax ok')"` → **syntax ok**
2. `grep -c "_in_quiet_hours\|quiet" cron_bug_scan_fastpoll.py` → **5** (>= 1 required)
3. `grep -c "mark_queue_entry_dispatched" cron_bug_scan_fastpoll.py` → **5** (>= 1 required)
4. `grep "ExecStart" uws-bug-scan-fastpoll.service` → correct venv python path confirmed
5. VPS smoke test (post-deploy): deferred to integration testing after deploy

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The script uses real imports from:
- `brain_http.mark_queue_entry_dispatched` (created in 05-01, will exist post-merge)
- `telegram_alert.send_alert` (created in 05-02, will exist post-merge)
- `workshop.cost.check_circuit_breaker` (existing)

## Threat Flags

None. This script reads a local JSONL file and dispatches to known local scripts. No new network endpoints or auth paths introduced. `brain_http` calls are internal (127.0.0.1:7000).

## Self-Check: PASSED

- `hermes-skills/cron_bug_scan_fastpoll.py` — exists, syntax valid
- `deploy/systemd/uws-bug-scan-fastpoll.service` — exists, ExecStart correct
- Commit `180488b` — Task 1
- Commit `cfef477` — Task 2
