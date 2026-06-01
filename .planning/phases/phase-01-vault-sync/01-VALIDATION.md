---
phase: 1
slug: vault-sync
status: validated-partial
nyquist_compliant: false
nyquist_exception: host-deploy-phase
wave_0_complete: true
created: 2026-06-01
backfilled: true
---

# Phase 1 — Validation Strategy (retroactive backfill)

> Reconstructed during the v1.0 milestone audit (State B). Phase 1 is a **VPS + Mac deploy phase** — its behavior (git-sync cron, deploy key, Obsidian-Git plugin, per-host env files) lives on the two hosts and the `second-brain` repo, not in this repo. There is no automatable in-repo behavior, so this phase is **manual-only by nature** (`nyquist_compliant: false` with a documented host-deploy exception).

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | none (no automatable in-repo unit) — `tests/phase-01/` does not exist |
| **Verification** | live host commands on VPS + Mac (see Manual-Only) |

## Per-Requirement Verification Map

| Requirement | Behavior | Test Type | Coverage | Status |
|-------------|----------|-----------|----------|--------|
| REQ-ws-024 | vault GitHub remote + VPS deploy key | manual | host-only | ⬜ MANUAL |
| REQ-ws-025 | Mac Obsidian-Git 5-min auto-sync | manual | host-only | ⬜ MANUAL |
| REQ-ws-026 | VPS `*/5` git-sync cron | manual | host-only | ⬜ MANUAL |
| REQ-ws-027 | vault env vars on both hosts | manual | host-only | ⬜ MANUAL |

**Nyquist check:** Not applicable — no in-repo behavior is automatable. All four requirements are inherently host-runtime. Marked `nyquist_compliant: false` with `nyquist_exception: host-deploy-phase` rather than fabricating automated coverage. Consistent with 01-VERIFICATION.md (`human_needed`).

## Manual-Only Verifications (VPS + Mac)
| Behavior | Requirement | Test Instructions |
|----------|-------------|-------------------|
| VPS→Mac round-trip ≤5 min | REQ-ws-024/026 | Write a file to the VPS vault; confirm it appears in Mac Obsidian within ~5 min |
| Mac→VPS round-trip ≤5 min | REQ-ws-025 | Save a note in Mac Obsidian; confirm on VPS vault within ~5 min |
| Commit parity | REQ-ws-024 | `git log -1` matches on VPS and Mac after a sync cycle |
| Env vars present | REQ-ws-027 | `grep VAULT_ /etc/uab/env` (VPS) and `.env` (Mac) show all three vars |

## Validation Sign-Off
- [x] Host-deploy exception documented (no automatable unit)
- [x] All 4 requirements have manual test instructions
- [ ] `nyquist_compliant` — **false (by exception)**; live host confirmation pending

## Validation Audit 2026-06-01
| Metric | Count |
|--------|-------|
| Requirements audited | 4 |
| Automatable | 0 (host-deploy phase) |
| Manual-only (documented) | 4 |
| New tests generated | 0 (not applicable) |
