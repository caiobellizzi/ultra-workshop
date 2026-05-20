# Plan 01-02 Summary — Mac Obsidian-Git Setup + Bidirectional Smoke Test

**Status:** Complete  
**Completed:** 2026-05-20  
**Plan:** Phase 1, Wave 2 (depends on 01-01)

## What Was Built

- Mac vault `~/Documents/second-brain` remote wired to `git@github.com:caiobellizzi/second-brain.git`
- Unrelated-histories merge completed (Mac + VPS had independent initial commits); Mac authoritative for conflicts
- Obsidian-Git v2.38.3 installed at `.obsidian/plugins/obsidian-git/` (repo moved to `Vinzent03/obsidian-git`)
- Plugin configured with 5-min auto-save and auto-pull, pull-before-push merge strategy
- Obsidian expanded `data.json` on first load confirming plugin is active
- End-to-end smoke test passed: VPS→Mac file appeared after `git pull`; Mac→VPS auto-sync already producing commits on GitHub before test ran

## Deviations from Plan

1. **obsidian-git repo moved**: `denolehov/obsidian-git` → `Vinzent03/obsidian-git`. Download URLs updated.
2. **Unrelated-histories merge required**: Plan assumed ff-only or simple rebase would work. Both repos had independent root commits; needed `--allow-unrelated-histories` with Mac authoritative for conflicts.
3. **VPS .git directory lost**: Between initial push and smoke test, the `.git` directory disappeared from `/srv/second-brain` (cause unclear, possibly Brain process). Re-initialized with `git init` + `git reset --hard origin/main`.
4. **uabrain home is `/opt/ultra-agents-brain`**: `safe.directory` exception needed for uabrain, not just root.
5. **Obsidian vault switch required**: Obsidian was open on `ultra-agents-brain/vault`, not `second-brain`. User switched vaults in UI to activate the plugin.
6. **Mac→VPS already working before Leg 2**: Obsidian-Git auto-sync had already committed to GitHub twice before the manual smoke test ran, confirming the direction was functional.

## Verification Results

| Check | Result |
|-------|--------|
| VPS remote URL | `git@github.com:caiobellizzi/second-brain.git` ✓ |
| Mac remote URL | `git@github.com:caiobellizzi/second-brain.git` ✓ |
| VPS 5-min cron | `*/5 * * * * uabrain ...git-sync.sh` ✓ |
| VPS env vars | VAULT_VPS_PATH, VAULT_DEFAULT_BRANCH, VAULT_REMOTE present ✓ |
| Mac env vars | Same three vars in `~/.env` ✓ |
| Smoke test VPS→Mac | `sync-test-vps.md` appeared on Mac via `git pull` ✓ |
| Smoke test Mac→VPS | 2 auto-sync commits already on GitHub before test ✓ |
| git HEAD agreement | Both sides at same SHA after cron pull ✓ |

## Requirements Fulfilled

- REQ-ws-024: VPS pushes to GitHub remote ✓
- REQ-ws-025: Mac changes appear on VPS within ~5 min (Obsidian-Git auto-commit → VPS cron pull) ✓
- REQ-ws-026: VPS crontab contains 5-min git-sync entry ✓
- REQ-ws-027: VAULT_* env vars present on both systems ✓

## Phase 1 Complete

Bidirectional vault sync is live. A note written on either side appears on the other within ~5 minutes without any manual action.
