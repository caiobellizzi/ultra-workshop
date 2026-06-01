---
phase: 5
slug: autonomous-routines-integration-loops
status: validated-partial
nyquist_compliant: false
nyquist_exception: vps-runtime-phase
wave_0_complete: true
created: 2026-06-01
backfilled: true
---

# Phase 5 — Validation Strategy (retroactive backfill)

> Reconstructed during the v1.0 milestone audit (State B). Phase 5 is largely a **VPS-runtime phase** (Hermes crons, systemd fast-poll service, trust symlink). It shipped **without a `tests/phase-05/` directory**. The dispatch facet of the polling loop is now covered by `tests/phase-10.1/` (created in Phase 10.1); the cron-routine bodies and VPS service lifecycle remain manual-only. This is an honest partial — some automated gaps are documented, not papered over.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (no `tests/phase-05/`; dispatch covered by `tests/phase-10.1/`) |
| **Quick run (dispatch facet)** | `python3 -c "import sys,pytest; sys.exit(pytest.main(['tests/phase-10.1/test_dispatch_entry.py','-q']))"` (needs httpx on path) |

## Per-Requirement Verification Map

| Requirement | Behavior | Test Type | Coverage | Status |
|-------------|----------|-----------|----------|--------|
| REQ-ws-016 | daily-research cron (07:00) | — | none | ❌ MISSING (manual) |
| REQ-ws-017 | nightly-tests cron (02:00) | — | none | ❌ MISSING (manual) |
| REQ-ws-018 | 3-tier poll: fast 30s / standard 4h / quiet hours | unit (dispatch) | `tests/phase-10.1/test_dispatch_entry.py` covers verb dispatch | ⚠️ PARTIAL |
| REQ-ws-019 | cron budget self-cancel at $18 | — | none (cost.py breaker unit-tested in phase-04) | ⚠️ PARTIAL (manual) |
| REQ-ws-020 | Flow B orphan linking | unit | `tests/phase-10.1/test_link_orphans.py` + `test_dispatch_entry.py` | ✅ COVERED |
| REQ-ws-021 | Flow E daily digest | unit | `tests/phase-10.1/test_telegram_alert_main.py` + dispatch | ✅ COVERED |
| REQ-ws-022 | shared trust policy symlink | — | none (VPS deploy artifact) | ❌ MISSING (manual) |
| REQ-ws-023 | integration contract doc | grep | `grep` `vault/_system/integration-contract.md` content | ✅ COVERED (doc) |

**Nyquist check:** FAILS strict continuity — REQ-ws-016, 017, 022 have no automated verify, and the dispatch/budget facets are only partially covered. Marked `nyquist_compliant: false`. Closing this properly needs a `tests/phase-05/` suite for the cron bodies (deferred — would require the gsd-nyquist-auditor, rate-limited until 18:00, plus a VPS-shaped fixture for the cron schedule/quiet-hours logic).

## Manual-Only Verifications (VPS — see 05-HUMAN-UAT.md)
| Behavior | Requirement | Why Manual |
|----------|-------------|------------|
| Trust symlink resolves + classify_action returns risk tier | REQ-ws-022 | VPS-only deploy artifact (install.sh) |
| Fast-poll post-to-telegram within 30s | REQ-ws-021 | Needs running `uws-bug-scan-fastpoll.service` + live Brain |
| Hermes cron jobs registered (daily-research 0 7 * * *) | REQ-ws-016 | Needs live Hermes `cronjob()` builtin |
| systemd unit active post-deploy | REQ-ws-018 | Needs VPS systemd |
| Startup catch-up hook fires on restart | REQ-ws-016 | Needs VPS Hermes restart |

## Documented Validation Gaps (v1.1 backlog)
- `tests/phase-05/` does not exist. Unit coverage for cron-routine bodies (daily-research synthesis, nightly-tests clone/run, quiet-hours partition, $18 self-cancel) should be added with mocked Hermes/Brain stubs.

## Validation Sign-Off
- [x] Dispatch + Flow B/E facets covered (via phase-10.1)
- [ ] Cron-routine bodies automated — **gap (deferred)**
- [x] VPS behaviors documented manual-only (05-HUMAN-UAT)
- [ ] `nyquist_compliant` — **false** (documented gaps + VPS exception)

## Validation Audit 2026-06-01
| Metric | Count |
|--------|-------|
| Requirements audited | 8 |
| Covered (automated) | 3 (020, 021, 023) |
| Partial | 2 (018, 019) |
| Missing automated (manual/gap) | 3 (016, 017, 022) |
| New tests generated | 0 (gen deferred — auditor rate-limited) |
