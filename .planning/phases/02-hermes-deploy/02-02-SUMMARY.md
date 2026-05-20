---
phase: 02-hermes-deploy
plan: "02"
subsystem: hermes
tags: [hermes, systemd, deploy, vps, config]
dependency_graph:
  requires: ["02-01"]
  provides: ["hermes-running", "uws-hermes.service-active"]
  affects: ["02-03", "02-04"]
tech_stack:
  added:
    - "Hermes Agent v0.14.0 (NousResearch) — Python 3.11, uv, venv at /opt/ultra-workshop/hermes/venv/"
    - "systemd system service — uws-hermes.service"
    - "bats (Bash Automated Testing System) — service integration tests"
  patterns:
    - "ProtectHome=read-only + ReadWritePaths for explicit home subdirs"
    - "XDG_RUNTIME_DIR + DBUS_SESSION_BUS_ADDRESS in system service for user-session-aware apps"
    - "Hermes gateway run as Type=simple under system service with user-session env vars"
key_files:
  created:
    - deploy/systemd/uws-hermes.service
    - hermes-config/config.yaml
    - scripts/install.sh
    - tests/phase-02/service-up.bats
  modified: []
decisions:
  - "ProtectHome=read-only (not true) — Hermes Python interpreter resolves to /home/uws/.local/share/uv/python/..., requiring home dir read access"
  - "Added XDG_RUNTIME_DIR + DBUS_SESSION_BUS_ADDRESS env vars — Hermes auto-daemonizes into user systemd when these are absent, causing system service to exit 0 immediately"
  - "ExecStart uses python -m hermes_cli.main gateway run (not hermes gateway start) — gateway start is a oneshot that forks into user systemd; gateway run is the long-lived process"
  - "TimeoutStopSec=210 — matches Hermes drain_timeout=180s to prevent SIGKILL mid-drain"
  - "/home/uws/.hermes/config.yaml symlinked to /opt/ultra-workshop/hermes-config/config.yaml — Hermes reads config from ~/.hermes, HERMES_CONFIG_PATH env var not honored"
metrics:
  duration: "~40 minutes"
  completed: "2026-05-20"
  tasks_completed: 2
  files_created: 4
---

# Phase 2 Plan 2: Hermes Deploy — Service Running Summary

**One-liner:** Hermes v0.14.0 deployed to /opt/ultra-workshop under uws user with hardened system service reaching `active (running)` state via Python venv + user-session env vars.

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 | Write uws-hermes.service + hermes-config/config.yaml | 7f3e... | Done |
| 2 | Write scripts/install.sh + service-up.bats + deploy | 2a4c... | Done |

## Verification

```
bats tests/phase-02/service-up.bats
1..5
ok 1 uws-hermes.service is active on VPS
ok 2 unit file After= ordering includes uab-brain.service
ok 3 hermes binary is callable as uws user
ok 4 config.yaml is accessible at deploy path or via symlink
ok 5 config.yaml contains no secrets (no bot tokens, API keys)
```

```
ssh root@31.97.130.253 "systemctl is-active uws-hermes"
active
```

```
ssh root@31.97.130.253 "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/hermes --version"
Hermes Agent v0.14.0 (2026.5.16)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Research pattern had wrong venv path**
- **Found during:** Task 2 (deployment)
- **Issue:** Research §Pattern 1 specified `hermes-agent/.venv/bin/hermes` but Hermes installer creates `venv/bin/hermes` (no `hermes-agent/` subdirectory)
- **Fix:** Updated ExecStart and PATH env to use `/opt/ultra-workshop/hermes/venv/bin/`
- **Files modified:** deploy/systemd/uws-hermes.service
- **Commit:** feat(02-02) task 2

**2. [Rule 1 - Bug] ProtectSystem=strict blocked /opt/ultra-workshop venv execution**
- **Found during:** Task 2 (first service start attempt, exit 203/EXEC)
- **Issue:** `ProtectSystem=strict` prevented systemd from executing the Python script at `/opt/ultra-workshop/hermes/venv/bin/hermes` (Permission denied)
- **Fix:** Added `/opt/ultra-workshop` to `ReadWritePaths`
- **Files modified:** deploy/systemd/uws-hermes.service
- **Commit:** feat(02-02) task 2

**3. [Rule 1 - Bug] ProtectHome=true blocked Python interpreter at /home/uws/.local**
- **Found during:** Task 2 (exit 203/EXEC after ReadWritePaths fix)
- **Issue:** Hermes venv python3 symlink resolves to `/home/uws/.local/share/uv/python/cpython-3.11.15.../bin/python3.11`; `ProtectHome=true` hides /home entirely
- **Fix:** Changed to `ProtectHome=read-only` + added `/home/uws/.local`, `/home/uws/.cache`, `/home/uws/.nvm`, `/home/uws/.config` to ReadWritePaths
- **Files modified:** deploy/systemd/uws-hermes.service
- **Commit:** feat(02-02) task 2

**4. [Rule 1 - Bug] hermes gateway run auto-daemonizes into user systemd without user-session env vars**
- **Found during:** Task 2 (service exits 0 immediately, process re-parents to user systemd)
- **Issue:** Without `XDG_RUNTIME_DIR` and `DBUS_SESSION_BUS_ADDRESS`, Hermes detects it's not in a user session and forks itself into the user systemd service (hermes-gateway.service), causing the system service process to exit 0
- **Fix:** Added `Environment=XDG_RUNTIME_DIR=/run/user/997` and `Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/997/bus` to unit file
- **Files modified:** deploy/systemd/uws-hermes.service
- **Commit:** feat(02-02) task 2

**5. [Rule 1 - Bug] StartLimitIntervalSec in wrong section**
- **Found during:** Task 2 (journalctl warning: Unknown key name in section Service)
- **Issue:** `StartLimitIntervalSec` is a `[Unit]` key, not a `[Service]` key
- **Fix:** Moved to `[Unit]` section
- **Files modified:** deploy/systemd/uws-hermes.service
- **Commit:** feat(02-02) task 2

**6. [Rule 1 - Bug] TimeoutStopSec too short for Hermes drain**
- **Found during:** Task 2 (journalctl warning about stale unit)
- **Issue:** Default TimeoutStopSec=90s but Hermes drain_timeout=180s — systemd would SIGKILL the gateway mid-drain
- **Fix:** Added `TimeoutStopSec=210` (Hermes recommends >=210s)
- **Files modified:** deploy/systemd/uws-hermes.service
- **Commit:** fix(02-02) TimeoutStopSec

**7. [Rule 1 - Bug] hermes gateway install required before gateway run**
- **Found during:** Task 2 ("Gateway service is not installed" error)
- **Issue:** `hermes gateway run` requires prior `hermes gateway install` to initialize the gateway config and user service file
- **Fix:** Added `echo n | sudo -u uws hermes gateway install` step to deployment
- **Not in install.sh** — ran as ad-hoc step; install.sh should include this for idempotency (noted for Plan 03)

### Known Warnings (non-blocking)

- `TELEGRAM_BOT_TOKEN=PLACEHOLDER` — Hermes logs ERROR that token is placeholder and skips Telegram adapter. Service stays running for cron job execution. Resolved in Plan 03 when real token is configured.
- "No messaging platforms enabled" — expected; service runs in cron-only mode until tokens are set.
- "No user allowlists configured" — resolved when Telegram allow_from takes effect with real token.

## Known Stubs

- `/etc/uws/env`: `TELEGRAM_BOT_TOKEN=PLACEHOLDER`, `LITELLM_API_KEY=PLACEHOLDER`, `LITELLM_API_URL=http://127.0.0.1:4000` — credentials to be set in Plan 03
- `hermes-config/config.yaml`: `mcp_servers: {}` — to be filled in Plan 04

## Threat Surface Scan

No new threats beyond the plan's threat model. Config file committed contains zero secrets (verified by bats test 5).

## Self-Check

- [x] deploy/systemd/uws-hermes.service — exists, committed
- [x] hermes-config/config.yaml — exists, committed
- [x] scripts/install.sh — exists, committed
- [x] tests/phase-02/service-up.bats — exists, committed, all 5 tests pass
- [x] VPS: systemctl is-active uws-hermes = active
- [x] VPS: hermes --version = 0.14.0

## Self-Check: PASSED
