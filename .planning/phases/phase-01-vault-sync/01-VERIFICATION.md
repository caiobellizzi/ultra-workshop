---
phase: phase-01-vault-sync
verified: 2026-06-01
verifier: inline (Opus — Sonnet verifier tier rate-limited until 18:00)
status: human_needed
score: "0/4 success criteria locally verifiable; 4/4 claimed complete by SUMMARYs — pending live VPS+Mac confirmation"
requirements_checked: ["REQ-ws-024", "REQ-ws-025", "REQ-ws-026", "REQ-ws-027"]
human_verification:
  - test: "VPS→Mac vault sync round-trip"
    expected: "A file written to the vault on the VPS appears in Mac Obsidian within ~5 min with no manual action"
    why_human: "Sync machinery (git-sync.sh cron, deploy key) is deployed to the VPS and the second-brain repo — not present in this repo. Requires live VPS + Mac to observe."
  - test: "Mac→VPS vault sync round-trip"
    expected: "A note saved in Mac Obsidian appears on the VPS vault within ~5 min via Obsidian-Git auto-commit+push"
    why_human: "Obsidian-Git plugin runs inside the Mac Obsidian app; cannot be observed from this repo."
  - test: "Commit parity after a sync cycle"
    expected: "git log on both VPS and Mac shows the same HEAD commit after one sync cycle"
    why_human: "Requires SSH access to the VPS vault checkout and the Mac vault checkout."
  - test: "Vault env vars present on both hosts"
    expected: "VAULT_VPS_PATH, VAULT_DEFAULT_BRANCH, VAULT_REMOTE present in /etc/uab/env (VPS) and .env (Mac)"
    why_human: "These files live on the two hosts, not in this repo."
---

# Phase 1: Vault Sync — Verification Report

**Phase Goal:** The vault is a live GitHub-backed shared store that both Brain (VPS) and Obsidian (Mac) read and write without manual intervention.
**Verified:** 2026-06-01 · **Status:** human_needed · **Re-verification:** No (initial — backfilled during v1.0 milestone audit)

> Backfill note: Phase 1 is a **VPS + Mac deploy phase**. Its acceptance machinery — `scripts/git-sync.sh`, the `*/5` VPS crontab entry, the VPS SSH deploy key, the Mac Obsidian-Git plugin config, and the per-host env files — is deployed to the two hosts and the `second-brain` repo, and is **not present in the ultra-workshop repo**. Therefore almost nothing is locally verifiable. The SUMMARYs document completion; this report records that as claim-level evidence pending host confirmation.

## In-repo evidence (limited)

| Artifact | Found | Note |
|----------|-------|------|
| `VAULT_VPS_PATH` consumer | yes | `scripts/install.sh:112` rsyncs to `${VAULT_VPS_PATH:-/srv/second-brain}/_system/`; `workshop/doc_resolver.py` uses `VAULT_VPS_PATH` with `/srv/second-brain` fallback. Confirms the env var name is the integration contract, not that it's set on the hosts. |
| `scripts/git-sync.sh` | no | Lives in the `second-brain` repo / on the VPS, not here. |

## Requirements (claim vs. local proof)

| REQ | Local proof | SUMMARY claim |
|-----|-------------|---------------|
| REQ-ws-024 (GitHub remote + VPS deploy key) | none in-repo | 01-01-SUMMARY: deploy key wired, vault remote pushes to `git@github.com:caiobellizzi/second-brain.git` |
| REQ-ws-025 (Mac Obsidian-Git 5-min sync) | none in-repo | 01-02-SUMMARY: Obsidian-Git v2.38.3 installed, 5-min auto-sync, end-to-end smoke passed |
| REQ-ws-026 (VPS */5 cron) | none in-repo | 01-01-SUMMARY: `*/5` crontab entry installed via `crontab -u` |
| REQ-ws-027 (env vars both hosts) | partial (name referenced in install.sh/doc_resolver) | 01-01-SUMMARY: vars added to `/etc/uab/env` (VPS) and `~/.env` (Mac) |

## Verdict

Nothing in this phase is falsifiable from the repo alone — it is inherently a host-deploy phase. The two SUMMARYs report all four requirements complete (including a passing end-to-end smoke test). Status is **human_needed**: a maintainer with VPS + Mac access should confirm the four `human_verification` checks above. Until then, REQ-ws-024..027 should be treated as implemented-but-unverified.
