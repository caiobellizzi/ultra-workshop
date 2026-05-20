---
phase: 02
slug: hermes-deploy
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-20
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Phase 02 is a deployment phase — most verification is shell-based on the VPS, not unit tests.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | bats-core (bash test runner) + ssh-driven shell assertions |
| **Config file** | `tests/phase-02/` (Wave 0 creates) |
| **Quick run command** | `bats tests/phase-02/smoke.bats` |
| **Full suite command** | `bats tests/phase-02/` |
| **Estimated runtime** | ~60 seconds (most assertions are ssh round-trips) |

---

## Sampling Rate

- **After every task commit:** Run `bats tests/phase-02/smoke.bats`
- **After every plan wave:** Run `bats tests/phase-02/`
- **Before `/gsd:verify-work`:** Full suite must be green AND HITL restart-resilience smoke executed manually
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-XX | 01 | 0 | gates | — | bot token rotated, brain telegram masked, swap ≥ 2GB | shell | `bats tests/phase-02/pre-deploy.bats` | ❌ W0 | ⬜ pending |
| 02-02-XX | 02 | 1 | REQ-ws-001 | — | `systemctl status uws-hermes` → active(running) | shell | `bats tests/phase-02/service-up.bats` | ❌ W0 | ⬜ pending |
| 02-03-XX | 03 | 2 | REQ-ws-013, REQ-ws-002 | — | Brain telegram inactive; `/start` reply ≤ 5s for chat 7113965359 | shell | `bats tests/phase-02/telegram.bats` | ❌ W0 | ⬜ pending |
| 02-04-XX | 04 | 2 | REQ-ws-015 | — | `hermes mcp list` shows 5 MCPs healthy | shell | `bats tests/phase-02/mcps.bats` | ❌ W0 | ⬜ pending |
| 02-05-XX | 05 | 3 | REQ-ws-014 | — | HITL pause survives `systemctl restart uws-hermes` via FTS5 | shell + scripted Telegram | `bats tests/phase-02/hitl-restart.bats` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/phase-02/pre-deploy.bats` — token rotation, brain telegram masked, swap ≥ 2GB, vault sync live
- [ ] `tests/phase-02/service-up.bats` — `uws-hermes.service` active, `After=uab-brain.service` honored
- [ ] `tests/phase-02/telegram.bats` — chat-ID gate (7113965359 only), `/start` reply latency
- [ ] `tests/phase-02/mcps.bats` — 5 MCPs registered & reachable
- [ ] `tests/phase-02/hitl-restart.bats` — scripted HITL pause + `systemctl restart` + resume via FTS5
- [ ] `tests/phase-02/helpers.bash` — shared ssh + assertion helpers
- [ ] `bats` installed locally (or container) — if not present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| BotFather token revoke + new token issued | L7 pre-gate | BotFather is interactive Telegram-side; cannot be scripted | Open Telegram → BotFather → `/revoke` → confirm → copy new token to `/etc/uws/env` |
| GCP service account creation + key download for google-workspace | REQ-ws-015 | One-time GCP console workflow; manual key download | Create GCP project → enable Workspace APIs → service account → download JSON → scp to VPS at `/etc/uws/gcp-sa.json` (0640 root:uws) |
| HITL approval flow visual check via Telegram | REQ-ws-014 | Inline-keyboard render verification needs human eyes | After restart-resilience bats passes, manually approve a real HITL prompt and confirm flow completes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
