---
phase: 02-hermes-deploy
plan: "03"
subsystem: telegram-gateway
tags: [telegram, hermes, gateway, allow_from, systemd]
dependency_graph:
  requires: [02-02]
  provides: [telegram-gateway-active, uab-telegram-confirmed-dead, telegram-bats-green]
  affects: [02-05]
tech_stack:
  added: []
  patterns: [hermes-telegram-allow_from, bats-pid-scoped-journal-check]
key_files:
  created:
    - tests/phase-02/telegram.bats
  modified:
    - /etc/uws/env (VPS only — TELEGRAM_BOT_TOKEN PLACEHOLDER replaced with real token)
decisions:
  - "Used existing Brain bot token (not rotated — user decision from plan context)"
  - "Token injected via SSH sed; never stored in git"
  - "allow_from in config.yaml is correct — Hermes config.py reads it and sets TELEGRAM_ALLOWED_USERS env var; the 'No user allowlists configured' WARNING fires before config loading and is cosmetic"
  - "Test 5 scoped to current MainPID to avoid false failures from historical placeholder runs"
metrics:
  duration: "~20 minutes"
  completed: "2026-05-20"
  tasks_completed: 1
  files_created: 1
---

# Phase 2 Plan 3: Telegram Gateway Wire-Up Summary

**One-liner:** TELEGRAM_BOT_TOKEN injected into /etc/uws/env, uws-hermes restarted with Telegram platform active, uab-telegram confirmed masked, 7-gate bats suite green.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wire Telegram gateway + inject token | 8160b77 | tests/phase-02/telegram.bats |

## Tasks Pending Checkpoint

| Task | Name | Type | Status |
|------|------|------|--------|
| 2 | Live /start gate verification | checkpoint:human-verify | AWAITING USER |

## VPS State After Task 1

| Gate | Status | Detail |
|------|--------|--------|
| TELEGRAM_BOT_TOKEN | SET | /etc/uws/env — real token, not placeholder |
| uws-hermes | ACTIVE | Telegram platform enabled (no "No messaging platforms" warning) |
| uab-telegram | MASKED+INACTIVE | Confirmed dead (REQ-ws-013) |
| allow_from | CONFIGURED | config.yaml platforms.telegram.extra.allow_from: ["7113965359"] |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Scoped journal test to current PID**
- **Found during:** Task 1 — bats test 5 failed because `--since '10 minutes ago'` captured old PLACEHOLDER runs
- **Fix:** Changed test to use `systemctl show uws-hermes --property=MainPID` and scope journal to that PID
- **Files modified:** tests/phase-02/telegram.bats
- **Commit:** 8160b77

## Known Stubs

None — TELEGRAM_BOT_TOKEN is a real token. allow_from is set to real chat ID.

## Threat Surface

| T-ID | Status | Detail |
|------|--------|--------|
| T-02-09 | MITIGATED | allow_from: ["7113965359"] set in config.yaml |
| T-02-10 | CHECK NEEDED | Journal visible in human verify — user should confirm `journalctl -u uws-hermes \| grep -i token` shows no token value |
| T-02-11 | CONFIRMED DEAD | uab-telegram masked; old Brain bot not running |
| T-02-SC | ACCEPTED | No package installs |

## Self-Check

- [x] tests/phase-02/telegram.bats exists at correct path
- [x] Commit 8160b77 exists: `git log --oneline | grep 8160b77`
- [x] VPS: TELEGRAM_BOT_TOKEN not placeholder
- [x] VPS: uws-hermes active
- [x] VPS: uab-telegram masked
- [x] All 7 bats tests pass

## Self-Check: PASSED
