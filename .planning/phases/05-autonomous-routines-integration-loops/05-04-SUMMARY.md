---
phase: "05"
plan: "04"
subsystem: autonomous-routines
tags: [hermes-cron, standard-poll, integration-contract, repo-registry, install-script]
dependency_graph:
  requires: [05-01, 05-02, 05-03]
  provides: [standard-poll-cron, bootstrap-cron-jobs, integration-contract, test_command-schema]
  affects: [hermes-skills, workshop/repo_registry, scripts/install.sh, vault/_system]
tech_stack:
  added: []
  patterns:
    - one-shot cron skill (no loop, no PID file) for standard-poll cadence
    - Hermes cronjob() builtin registration via bootstrap skill
    - integration-contract.md as shared vocabulary source of truth
key_files:
  created:
    - hermes-skills/cron_standard_poll.py
    - hermes-skills/bootstrap_cron_jobs.py
    - vault/_system/integration-contract.md
  modified:
    - workshop/repo_registry.py
    - scripts/install.sh
decisions:
  - "standard-poll implemented as one-shot main() (no loop) matching cron invocation semantics"
  - "circuit-breaker with mode=cron silently skips via logging.warning (no Telegram alert)"
  - "quiet hours 22:00-06:59 applied identically to fast-poll pattern"
  - "bootstrap_cron_jobs.py relies on Hermes cronjob() builtin injected at skill runtime"
  - "integration-contract.md committed locally as source-of-truth, rsync'd to VPS vault at install"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-28"
  tasks_completed: 3
  tasks_total: 3
  files_created: 3
  files_modified: 2
---

# Phase 05 Plan 04: Standard-Poll Cron + Integration Contract + Trust Symlink + Install Script Summary

One-liner: Standard-cadence queue dispatcher as a one-shot Hermes cron skill, cron job bootstrap registration, integration-contract vocabulary doc, repo_registry test_command schema extension, and install script automation of trust symlink + systemd deploy + cron bootstrap.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | cron_standard_poll + bootstrap_cron_jobs | 77ed71c | hermes-skills/cron_standard_poll.py, hermes-skills/bootstrap_cron_jobs.py |
| 2 | repo_registry test_command + list_repos_with_tests | c1eafc4 | workshop/repo_registry.py |
| 3 | integration-contract.md + install.sh updates | da8a855 | vault/_system/integration-contract.md, scripts/install.sh |

## What Was Built

### Task 1: cron_standard_poll.py + bootstrap_cron_jobs.py

`hermes-skills/cron_standard_poll.py` implements a one-shot `main()` that:
- Calls `check_circuit_breaker(mode="cron")` at entry — silently returns on `BudgetExhausted` or `BudgetWarning` with a `logging.warning` only (no Telegram alert)
- Checks quiet hours (22:00–06:59) before any dispatch
- Reads `.workshop-queue.jsonl`, filters entries where `confirmed=true` and `dispatched` is falsy
- Dispatches each entry to the appropriate skill subprocess: `post-to-telegram`, `link-orphans`, `build`, `fix`, unknown-warn-and-ack
- ACKs each dispatched entry via `brain_http.mark_queue_entry_dispatched(entry_id)`
- No infinite loop, no PID file — designed to run once per Hermes cron invocation

`hermes-skills/bootstrap_cron_jobs.py` is a one-shot Hermes skill that registers four cron jobs via the Hermes `cronjob()` builtin:
- `daily-research` — `0 7 * * *` → `cron_daily_research`
- `nightly-tests` — `0 2 * * *` → `cron_nightly_tests`
- `standard-poll-4h` — `0 */4 * * *` → `cron_standard_poll`
- `nightly-rescan` — `0 3 * * *` → `cron_standard_poll`

### Task 2: repo_registry schema extension

- `seed_entry()` now includes `"test_command": ""` after `"last_used_at": None`
- `normalize_registry` naturally propagates the field to existing entries via `setdefault` merge pattern (no explicit change needed)
- New `list_repos_with_tests()` helper returns active repos with non-empty `test_command`

### Task 3: Integration contract + install script

`vault/_system/integration-contract.md` defines:
- Full frontmatter field vocabulary (8 fields: suggested_action, action, confirmed, status, task_id, dispatched, pr_url, created_by)
- Five dispatch flows: A (build), B (fix), D (test failure/suggested), E (post-to-telegram zero-HITL)
- Write ownership rules (Brain owns action/confirmed, Workshop owns dispatched/task_id/pr_url)

`scripts/install.sh` gains 6 new steps after the existing Step 8:
- **Step N**: Trust symlink (`trust_shared.py` → Brain's `trust.py`)
- **Step N+1**: `HERMES_CRON_TIMEOUT=1800` appended to `/etc/uws/env` (idempotent)
- **Step N+2**: `uws-bug-scan-fastpoll` systemd unit deploy + enable + start
- **Step N+3**: Catch-up hook deploy to `/home/uws/.hermes/hooks/startup-cron-catchup/`
- **Step N+4**: `bootstrap_cron_jobs.py` run via `hermes skill run` to register cron jobs
- **Step N+5**: `integration-contract.md` rsync'd to vault `_system/` on VPS

## Verification Criteria Addressed

| Criterion | Code | Coverage |
|-----------|------|---------|
| cron_standard_poll imports ok | V17 | import test passes |
| list_repos_with_tests imports ok | V16 | import test passes |
| trust symlink step in install.sh | V21 | grep confirms |
| HERMES_CRON_TIMEOUT in install.sh | V18 | grep confirms |
| bootstrap_cron_jobs runs on install | V24 | install step N+4 |
| integration-contract deployed to vault | V23 | install step N+5 |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All dispatch targets (`telegram_alert`, `link_orphans`, `workshop_build`, `workshop_fix`) are provided by sibling plans 05-01, 05-02, 05-03 which run concurrently in the same wave.

## Threat Flags

None. No new network endpoints introduced. `cron_standard_poll.py` reads a local JSONL file and calls existing Brain HTTP endpoint via `brain_http` (already threat-modelled in 05-01).

## Self-Check: PASSED

- hermes-skills/cron_standard_poll.py: FOUND
- hermes-skills/bootstrap_cron_jobs.py: FOUND
- vault/_system/integration-contract.md: FOUND
- workshop/repo_registry.py (modified): FOUND
- scripts/install.sh (modified): FOUND
- Commits 77ed71c, c1eafc4, da8a855: FOUND in git log
