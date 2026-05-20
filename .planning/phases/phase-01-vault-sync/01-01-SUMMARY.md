# Plan 01-01 Summary — VPS Vault Remote + Cron Sync Setup

**Status:** Complete  
**Completed:** 2026-05-20  
**Plan:** Phase 1, Wave 1

## What Was Built

- `caiobellizzi/second-brain` private GitHub repo created
- SSH ed25519 deploy key generated on VPS, owned by `uabrain:uabrain 600`
  - Key stored at `/opt/ultra-agents-brain/.ssh/second-brain-deploy` (uabrain home is `/opt/ultra-agents-brain`, not `/home/uabrain`)
  - SSH config at `/opt/ultra-agents-brain/.ssh/config` maps `github.com` → deploy key
  - GitHub's host key added to `/opt/ultra-agents-brain/.ssh/known_hosts`
- Deploy key registered on GitHub with write access (title: `vps-uabrain-deploy`)
- `/srv/second-brain` initialized as git repo, remote wired, 41 files pushed to `main` branch
  - Ownership fixed from uid 501 (Mac) to `uabrain:uabrain` via `chown -R`
  - `safe.directory` exception added for root operations on `/srv/second-brain`
- `VAULT_VPS_PATH`, `VAULT_DEFAULT_BRANCH`, `VAULT_REMOTE` added to `/etc/uab/env` (VPS) and `~/.env` (Mac)
- 5-min cron entry added to `/opt/ultra-agents-brain/deploy/cron/ultra-agents-brain.cron` and installed via `crontab -u uabrain`

## Deviations from Plan

1. **SSH hostname**: Plan referenced `srv1381850.hstgr.cloud` but VPS hostname is `srv847330.hstgr.cloud` (IP `31.97.130.253`). Used IP for all SSH commands.
2. **Key location**: Plan assumed uabrain home = `/home/uabrain`. Actual home is `/opt/ultra-agents-brain`. All SSH assets moved to `/opt/ultra-agents-brain/.ssh/`.
3. **VPS vault not a git repo**: `/srv/second-brain` existed with PARA content but needed `git init`. Ownership was uid 501 (Mac copy artifact) — fixed with `chown -R uabrain:uabrain`.
4. **GitHub known_hosts**: Had to explicitly run `ssh-keyscan github.com` to populate `known_hosts` before SSH auth worked.

## Verification Results

| Check | Result |
|-------|--------|
| `gh repo view caiobellizzi/second-brain` | `second-brain private=true` ✓ |
| VPS `/etc/uab/env` contains VAULT_VPS_PATH | `1` match ✓ |
| Mac `~/.env` contains VAULT_VPS_PATH | `1` match ✓ |
| Deploy key ownership | `uabrain:uabrain 600` ✓ |
| `git remote get-url origin` on VPS | `git@github.com:caiobellizzi/second-brain.git` ✓ |
| `crontab -u uabrain -l` | `*/5 * * * *` git-sync entry ✓ |
| GitHub `main` branch exists | Confirmed ✓ |
| SSH auth as uabrain | "You've successfully authenticated" ✓ |
| Manual `git-sync.sh push` as uabrain | "nothing to commit" (clean exit) ✓ |

## Requirements Fulfilled

- REQ-ws-024: GitHub-backed vault remote ✓
- REQ-ws-026: 5-min VPS cron sync ✓
- REQ-ws-027 (VPS side): VAULT_* env vars on VPS ✓
