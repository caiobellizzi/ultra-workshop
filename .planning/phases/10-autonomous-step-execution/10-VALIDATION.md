---
phase: 10
slug: autonomous-step-execution
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-01
backfilled: true
---

# Phase 10 — Validation Strategy (retroactive backfill)

> Reconstructed during the v1.0 milestone audit (State B). Each REQ has automated coverage for its code-level facet; the live step-execution timing/commit behaviors are inherently manual (see 10-HUMAN-UAT.md).

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + bats |
| **Quick run** | `python3 -c "import sys,pytest; sys.exit(pytest.main(['tests/phase-10/','tests/phase-04/test_workshop_build.py','tests/phase-04/test_workshop_continue.py','-q']))"` |
| **Local run 2026-06-01** | `tests/phase-10/` green (part of 62-passed batch); `tests/phase-04/` 45 passed |

## Sampling Rate
- After every task commit: phase-10 + phase-04 step-loop tests · Max latency: ~30s.

## Per-Requirement Verification Map

| Requirement | Behavior (code facet) | Test Type | Coverage | Status |
|-------------|------------------------|-----------|----------|--------|
| REQ-ws-051 | per-stage model map + NIM; no --architect/--no-stream | bats+grep | `model-matrix-smoke.bats` + `grep` aider_runner.py | ✅ COVERED |
| REQ-ws-052 | step loop + per-step commit | unit | `test_workshop_build.py`, `test_workshop_continue.py` | ✅ COVERED (live 3-commit chain → manual) |
| REQ-ws-053 | idle watchdog (no communicate(timeout=900)) | unit+grep | `grep "communicate(timeout=900"` → 0; mock-timeout unit | ✅ COVERED (live ~120s timing → manual) |
| REQ-ws-054 | recovery ladder retry→decompose→HITL | unit | `test_workshop_build.py` | ✅ COVERED (live ladder → manual) |
| REQ-ws-055 | planner many-small-steps; `[:6]` removed | unit+grep | `test_planner.py` + `grep "[:6]"` → 0 | ✅ COVERED |
| REQ-ws-056 | state cursor + resume | unit | state.py cursor tests + `test_workshop_continue.py` | ✅ COVERED (live resume → manual) |

**Nyquist check:** Every REQ maps to a green unit/bats/grep verify for its code facet. The runtime timing/commit behaviors below are legitimately manual. Compliant.

## Manual-Only Verifications (live execution — see 10-HUMAN-UAT.md)
| Behavior | Requirement | Why Manual |
|----------|-------------|------------|
| 3-step plan → 3 commits on `workshop/<task_id>`; prior commits survive a later retry | REQ-ws-052 | Live Aider + LiteLLM proxy run |
| Idle watchdog kills at ~120s not 900s | REQ-ws-053 | Real subprocess + controlled slow endpoint |
| retry(2)→decompose(depth=1)→HITL ladder; global caps trip | REQ-ws-054 | Live failing step in a real repo |
| Kill after step 2 of 5 → `--resume` continues from step 3 | REQ-ws-056 | Live kill/restart cycle |

## Validation Sign-Off
- [x] All requirements have automated verify for the code facet
- [x] Local suites green (2026-06-01)
- [x] Live-execution behaviors documented manual-only (10-HUMAN-UAT)
- [x] `nyquist_compliant: true`

## Validation Audit 2026-06-01
| Metric | Count |
|--------|-------|
| Requirements audited | 6 |
| Covered (automated code facet) | 6 |
| Manual-only live behaviors | 4 |
| New tests generated | 0 |
