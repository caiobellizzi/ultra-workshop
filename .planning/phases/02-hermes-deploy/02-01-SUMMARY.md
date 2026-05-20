---
phase: 02-hermes-deploy
plan: "01"
subsystem: vps-infra
tags: [swap, systemd, nvm, node24, litellm, pre-deploy]
dependency_graph:
  requires: []
  provides: [vps-swap-2g, uab-telegram-masked, node24-uws, etc-uws-env, litellm-timeout-30]
  affects: [02-02, 02-03, 02-04, 02-05]
tech_stack:
  added: [bats-core, nvm-v0.40.3, node-v24.15.0]
  patterns: [idempotent-vps-provisioning, bats-ssh-gate-tests]
key_files:
  created:
    - tests/phase-02/helpers.bash
    - tests/phase-02/pre-deploy.bats
    - deploy/litellm/config.yaml
  modified: []
decisions:
  - "Masked uab-telegram by replacing real unit file with /dev/null symlink (systemctl mask --force failed because a real file existed; backup kept as .bak)"
  - "LiteLLM runs in Docker with bind-mount; restarted deploy-litellm-1 container to apply timeout change"
  - "Fetched config.yaml from VPS path /opt/ultra-agents-brain/deploy/litellm/config.yaml (not /opt/ultra-agents-brain/litellm/ as plan assumed)"
metrics:
  duration: "~20 minutes"
  completed: "2026-05-20"
  tasks_completed: 2
  files_created: 3
---

# Phase 2 Plan 1: VPS Pre-Deploy Gates Summary

**One-liner:** 2GB swap + uab-telegram masked + Node.js 24 via nvm + /etc/uws/env stub + LiteLLM private-worker timeout reduced 300→30s, all verified by 6-gate bats test suite.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | VPS pre-deploy gates | 819a6f8 | tests/phase-02/helpers.bash, tests/phase-02/pre-deploy.bats |
| 2 | LiteLLM private-worker timeout fix | 0033b95 | deploy/litellm/config.yaml |

## VPS State After Plan

| Gate | Status | Detail |
|------|--------|--------|
| Swap | ACTIVE | /swapfile 2G, /etc/fstab persisted |
| uab-telegram | MASKED | Unit replaced with /dev/null symlink; .bak kept |
| Node.js | v24.15.0 | nvm v0.40.3 installed for uws user |
| /etc/uws/env | EXISTS | root:uws 0640, PLACEHOLDER values |
| LiteLLM timeout | 30s | deploy-litellm-1 restarted |

## Verification

```
bats tests/phase-02/pre-deploy.bats
1..6
ok 1 VPS swap is active (2G swapfile)
ok 2 uab-telegram.service is masked
ok 3 Node.js v24 installed for uws user
ok 4 /etc/uws/env exists on VPS
ok 5 /etc/uws/env has correct permissions (0640)
ok 6 LiteLLM config has private-worker timeout 30
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] systemctl mask --force failed on uab-telegram**
- **Found during:** Task 1
- **Issue:** `systemctl mask` (and `--force`) both failed with "File already exists" because a real unit file was at `/etc/systemd/system/uab-telegram.service` instead of a symlink
- **Fix:** Moved the real file to `.bak`, created `/dev/null` symlink manually, ran `systemctl daemon-reload`
- **Files modified:** VPS only (no local files)
- **Commit:** 819a6f8

**2. [Rule 3 - Blocking] Wrong VPS path for LiteLLM config.yaml**
- **Found during:** Task 2
- **Issue:** Plan assumed `/opt/ultra-agents-brain/litellm/config.yaml`; actual path is `/opt/ultra-agents-brain/deploy/litellm/config.yaml`
- **Fix:** Used `find` to locate correct path, fetched from there, updated bats test assertion path accordingly
- **Files modified:** tests/phase-02/pre-deploy.bats (path correction)
- **Commit:** 819a6f8, 0033b95

**3. [Rule 2 - Missing] LiteLLM runs in Docker, not systemd**
- **Found during:** Task 2
- **Issue:** Plan said `systemctl restart uab-litellm || systemctl restart litellm`; LiteLLM runs as Docker container `deploy-litellm-1`
- **Fix:** `docker restart deploy-litellm-1` to apply the bind-mounted config change
- **Files modified:** VPS only

## Known Stubs

- `/etc/uws/env` on VPS contains PLACEHOLDER values for all secrets (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, LITELLM_API_KEY). Human must set real values before Wave 1 (Plan 02-02).

## Threat Surface Scan

No new network endpoints or auth paths introduced. /etc/uws/env created with correct mitigations per T-02-02 (root:uws 0640). T-02-03 (OOM) mitigated by 2GB swap.

## Self-Check: PASSED

- [x] tests/phase-02/helpers.bash exists
- [x] tests/phase-02/pre-deploy.bats exists
- [x] deploy/litellm/config.yaml exists with timeout: 30
- [x] commit 819a6f8 exists (task 1)
- [x] commit 0033b95 exists (task 2)
- [x] bats ran 6/6 green
