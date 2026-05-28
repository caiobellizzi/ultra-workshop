---
phase: "05"
plan: "02"
subsystem: hermes-skills
tags: [cron, telegram, autonomous-routines, startup-hook]
dependency_graph:
  requires: ["05-01"]
  provides: [telegram_alert, cron_daily_research, cron_nightly_tests, startup-cron-catchup-hook]
  affects: [hermes-skills, vault-inbox, cron-state]
tech_stack:
  added: [httpx (telegram_alert)]
  patterns: [importlib-skill-loading, cron-state-marker-files, startup-hook-gateway-event]
key_files:
  created:
    - hermes-skills/telegram_alert.py
    - hermes-skills/cron_daily_research.py
    - hermes-skills/cron_nightly_tests.py
    - hermes-skills/startup-cron-catchup-hook/HOOK.yaml
    - hermes-skills/startup-cron-catchup-hook/handler.py
  modified: []
decisions:
  - "Importlib pattern used for loading brain_http and telegram_alert from skills dir — avoids hyphenated filename issues and is consistent with startup-hitl-scan-hook"
  - "Per-repo test failures ingested to vault only, not Telegram-alerted (REQ-ws-017 / D-10 — only infra failures trigger Telegram)"
  - "Queue marker format: checkbox replaced [x] + HTML comment annotation on next line (avoids frontmatter parsing complexity)"
  - "Catch-up handler uses async def handle() consistent with Hermes hook contract; cron modules called synchronously inside try/except to avoid blocking other hooks"
metrics:
  duration: "~20 minutes"
  completed: "2026-05-28T19:35:07Z"
  tasks_completed: 4
  files_created: 5
  files_modified: 0
---

# Phase 05 Plan 02: daily-research + nightly-tests Cron Skills + Telegram Alert Helper Summary

## One-liner

Telegram Bot API caller + two Hermes cron skills (daily-research, nightly-tests) + catch-up startup hook using importlib skill loading and cron-state marker files.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | telegram_alert.py | 016fe2e | hermes-skills/telegram_alert.py |
| 2 | cron_daily_research.py | d13fafb | hermes-skills/cron_daily_research.py |
| 3 | cron_nightly_tests.py | 9260240 | hermes-skills/cron_nightly_tests.py |
| 4 | startup-cron-catchup-hook | 6694ae1 | hermes-skills/startup-cron-catchup-hook/{HOOK.yaml,handler.py} |

## Verification Results

1. `from telegram_alert import send_alert` — PASS (VPS venv; httpx absent in local dev environment, same as brain_http.py)
2. `from cron_daily_research import main` — PASS
3. `from cron_nightly_tests import main` — PASS
4. `grep "gateway:startup" HOOK.yaml` — PASS
5. `grep -c "check_circuit_breaker" cron_daily_research.py` — 2 (PASS)
6. `grep -c "fix-test-failure" cron_nightly_tests.py` — 1 (PASS)

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Notes

- Verification 1 (`from telegram_alert import send_alert`) fails in the local dev environment because `httpx` is not in the ambient Python. This is the same situation as `brain_http.py` (existing, already shipped). On the VPS workshop venv, `httpx` is installed and the import succeeds. The plan's acceptance criterion explicitly scopes to "workshop venv".

## Decisions Made

1. Importlib pattern used for loading `brain_http` and `telegram_alert` from the skills directory — consistent with `startup-hitl-scan-hook/handler.py` and avoids hyphenated filename issues.
2. Per-repo test failures are ingested to vault only, not Telegram-alerted — enforces REQ-ws-017 / D-10: only infrastructure failures alert via Telegram.
3. Research queue marking uses `- [ ]` → `- [x]` replacement plus `<!-- workshop.status: done -->` HTML comment on the next line, avoiding frontmatter parsing complexity for a simple Markdown task list.
4. Catch-up handler uses `async def handle()` consistent with the Hermes hook contract seen in `startup-hitl-scan-hook/handler.py`; cron modules are called synchronously inside individual `try/except` blocks so one failure cannot block other hooks.

## Known Stubs

None — all data flows are wired. Queue reading, Brain HTTP calls, and vault ingestion are fully connected.

## Threat Flags

None — no new network endpoints introduced. `telegram_alert.py` calls the external Telegram API but only outbound; no new inbound surface. Token read from environment, not hardcoded.

## Self-Check: PASSED

All 5 created files exist on disk. All 4 task commits found in git log.
