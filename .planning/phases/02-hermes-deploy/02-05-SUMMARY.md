---
phase: 02-hermes-deploy
plan: "05"
subsystem: hitl-restart-resilience
tags: [hitl, sqlite, hermes-hooks, gateway-startup, telegram, bats, pytest, REQ-ws-014]
dependency_graph:
  requires: [02-03]
  provides: [hitl-restart-resilience, pending-hitl-db, startup-hitl-scan-hook, hitl-bats-green, req-ws-014-partial]
  affects: []
tech_stack:
  added:
    - "stdlib sqlite3 (pending_hitl.db — no new deps)"
    - "Hermes gateway:startup hook system (HOOK.yaml + handler.py pattern)"
  patterns:
    - "hermes-hook-print-for-journald: use print() not logging.info() for hook output visible in journalctl"
    - "hermes-hook-importlib: load hyphenated .py files via importlib.util.spec_from_file_location"
    - "hermes-hook-asyncio-sleep-before-adapter: await asyncio.sleep(5) to let Telegram adapter settle after gateway:startup"
    - "systemd-ReadWritePaths-for-new-home-dirs: add /home/uws/.ultra-workshop to ReadWritePaths when ProtectHome=read-only"
key_files:
  created:
    - hermes-skills/startup-hitl-scan.py
    - hermes-skills/startup-hitl-scan-hook/HOOK.yaml
    - hermes-skills/startup-hitl-scan-hook/handler.py
    - hermes-skills/test_startup_hitl_scan.py
    - tests/phase-02/hitl-restart.bats
  modified:
    - hermes-config/config.yaml
    - deploy/systemd/uws-hermes.service
key-decisions:
  - "Hermes hooks (HOOK.yaml + handler.py in ~/.hermes/hooks/) are the correct mechanism for gateway:startup — not SKILL.md files; config.yaml has no skills_dir key for this purpose"
  - "Use print() for hook log output instead of logging.INFO — the logging module root logger is WARNING-level in gateway context; print() goes to stdout which journald captures"
  - "handler.py loads startup-hitl-scan.py via importlib.util because hyphens in filenames are invalid Python identifiers"
  - "Added /home/uws/.ultra-workshop to ReadWritePaths in uws-hermes.service — ProtectHome=read-only blocked DB creation (Rule 1 fix during task execution)"
  - "asyncio.sleep(5) in handle() allows Telegram adapter to fully connect before send_clarify — gateway:startup fires before PTB application is ready"
metrics:
  duration: "~90 minutes"
  completed: "2026-05-21"
  tasks_completed: 2
  files_created: 5
  files_modified: 2
---

# Phase 2 Plan 5: HITL Restart Resilience Summary

**SQLite pending_hitl.db + Hermes gateway:startup hook re-emits Telegram inline keyboards for interrupted HITL sessions after systemctl restart — 5/5 bats assertions pass, 13/13 pytest pass.**

## Performance

- **Duration:** ~90 minutes (Tasks 1+2 complete; Task 3 at checkpoint)
- **Completed:** 2026-05-21
- **Tasks:** 2 auto complete + 1 checkpoint pending
- **Files created:** 5
- **Files modified:** 2

## Accomplishments

### Task 1: startup-hitl-scan.py + hook infrastructure

- Created `hermes-skills/startup-hitl-scan.py` with 5 public functions:
  `ensure_schema()`, `record_hitl_pause()`, `fetch_pending()`,
  `resolve_hitl_row()`, `update_hitl_message_id()`. Uses stdlib `sqlite3`
  only (no new dependencies). T-02-18: DB created 0600 uws:uws.

- Created `hermes-skills/startup-hitl-scan-hook/HOOK.yaml` declaring
  `gateway:startup` event registration.

- Created `hermes-skills/startup-hitl-scan-hook/handler.py` implementing
  Option A restart-resilience pattern:
  - Loads startup-hitl-scan.py via `importlib.util` (hyphen-safe)
  - On startup: `await asyncio.sleep(5)` → fetch pending rows → for each:
    register clarify entry, call `adapter.send_clarify()`, spawn background
    thread to wait for resolution and update DB status + log T-02-20 audit
  - T-02-17: validates chat_id == `7113965359` before re-emitting

- Created `hermes-skills/test_startup_hitl_scan.py`: 13 pytest tests
  covering all helper functions with tmp_path fixtures. All pass.

- Updated `hermes-config/config.yaml`: added comment documenting hook
  deployment location (no Hermes config key exists for hook dirs).

- Updated `deploy/systemd/uws-hermes.service`: added
  `/home/uws/.ultra-workshop` to `ReadWritePaths` (required under
  `ProtectHome=read-only`).

### Task 2: hitl-restart.bats V14 smoke test

- Created `tests/phase-02/hitl-restart.bats` with 5 assertions:
  1. Seed row written to pending_hitl.db before restart
  2. uws-hermes restarts cleanly (active after 25s)
  3. Journal shows `startup-hitl-scan.*re-emitting`
  4. DB row retains `status=pending` (awaiting human approval)
  5. pending_hitl.db permissions are 0600 owned by uws

- Full suite: `bats tests/phase-02/` → 23/23 pass

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Hermes hook system uses HOOK.yaml + handler.py, not Python skills**
- **Found during:** Task 1
- **Issue:** Plan said "Hermes startup skill" implying a SKILL.md file in a skills_dir. Research revealed Hermes hooks are discovered from `~/.hermes/hooks/` via `HOOK.yaml` + `handler.py` pattern; config.yaml has no `skills_dir` key.
- **Fix:** Implemented as a Hermes hook in `~/.hermes/hooks/startup-hitl-scan/`. The `hermes-skills/startup-hitl-scan.py` serves as the deployed helper module loaded by the hook.
- **Files modified:** hermes-skills/startup-hitl-scan-hook/ (new), hermes-config/config.yaml (comment only)

**2. [Rule 3 - Blocking] ProtectHome=read-only blocked pending_hitl.db creation**
- **Found during:** Task 1 VPS verification
- **Issue:** `systemctl restart uws-hermes` failed with "unable to open database file" because `ProtectHome=read-only` blocked writes to `/home/uws/.ultra-workshop/`.
- **Fix:** Added `/home/uws/.ultra-workshop` to `ReadWritePaths` in `deploy/systemd/uws-hermes.service`. Applied via `sed` on VPS and updated repo file.
- **Files modified:** deploy/systemd/uws-hermes.service

**3. [Rule 1 - Bug] Python logging.INFO not captured by journald at hook startup**
- **Found during:** Task 1 VPS verification
- **Issue:** `logging.getLogger("startup-hitl-scan").info(...)` output was not visible in journalctl — Hermes gateway sets root logger to WARNING level. The bats test assertion (`grep 'startup-hitl-scan.*re-emitting'`) would have failed.
- **Fix:** Added `print(..., flush=True)` alongside logger calls for all critical hook output. Hermes' own hook system uses `print()` for the same reason.
- **Files modified:** hermes-skills/startup-hitl-scan-hook/handler.py

**4. [Rule 1 - Bug] PlatformKind import path was wrong**
- **Found during:** Task 1 VPS verification
- **Issue:** Handler imported `from gateway.platforms.base import PlatformKind` but `PlatformKind` doesn't exist there. Adapter enumeration uses `Platform` from `gateway.config`.
- **Fix:** Removed the unused import; the adapter loop uses duck typing (`kind.value`) which works with the actual `Platform` enum.
- **Files modified:** hermes-skills/startup-hitl-scan-hook/handler.py

**5. [Rule 3 - Blocking] gateway:startup fires before Telegram PTB adapter is ready**
- **Found during:** Task 1 VPS verification
- **Issue:** After the `PlatformKind` fix, `_get_telegram_adapter()` returned None because the hook fires synchronously right as adapters are wired — before the python-telegram-bot Application has polled the first update.
- **Fix:** Added `await asyncio.sleep(5)` in `handle()` before calling `_get_telegram_adapter()`.
- **Files modified:** hermes-skills/startup-hitl-scan-hook/handler.py

## Threat Surface Scan

No new network endpoints introduced. The hook sends to an existing Telegram bot (T-02-17 mitigated by chat_id validation). No new trust boundaries beyond the plan's threat model.

## Known Stubs

The inline keyboard re-emission calls `send_clarify()` which sends buttons to Telegram. The button-tap resolution (updating DB status and sending confirmation) is wired via a background thread that watches the clarify entry's `threading.Event`. This thread-based resolution is verified only at the Task 3 checkpoint (human taps [Approve]).

The `record_hitl_pause()` helper in `startup-hitl-scan.py` is deployed but not yet called by any skill (no HITL-issuing skill exists in this phase). The DB row seeding in bats and future HITL flows will call it. This is intentional — the helper is ready for Phase 3 integration.

## Self-Check

- [x] hermes-skills/startup-hitl-scan.py exists on VPS at /opt/ultra-workshop/hermes-skills/
- [x] hermes-skills/startup-hitl-scan-hook/HOOK.yaml on VPS at /home/uws/.hermes/hooks/startup-hitl-scan/
- [x] hermes-skills/startup-hitl-scan-hook/handler.py on VPS at /home/uws/.hermes/hooks/startup-hitl-scan/
- [x] pending_hitl.db created at /home/uws/.ultra-workshop/pending_hitl.db (0600 uws:uws)
- [x] tests/phase-02/hitl-restart.bats: 5/5 pass
- [x] bats tests/phase-02/: 23/23 pass
- [x] hermes-skills/test_startup_hitl_scan.py: 13/13 pytest pass
- [x] commit acd82f2: feat(02-05) startup-hitl-scan skill
- [x] commit 25ff375: test(02-05) bats V14 restart-resilience smoke test

## Self-Check: PASSED
