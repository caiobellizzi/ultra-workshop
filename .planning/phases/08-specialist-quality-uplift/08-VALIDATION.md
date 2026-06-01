---
phase: 8
slug: specialist-quality-uplift
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-01
backfilled: true
---

# Phase 8 — Validation Strategy (retroactive backfill)

> Reconstructed during the v1.0 milestone audit (State B). Phase 8 acceptance is a mix of behavioral unit tests (structured failure contract, build/test gate) and grep-level SKILL.md content checks.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + bats + grep content assertions |
| **Quick run** | `python3 -c "import sys,pytest; sys.exit(pytest.main(['tests/phase-08/','-q']))"` |
| **Local run 2026-06-01** | `tests/phase-08/` green (part of the 62-passed batch); 08-VERIFICATION recorded 45 passed across phase-04/06/07/08 |

## Sampling Rate
- After every task commit: `tests/phase-08/` · Max latency: ~10s.

## Per-Requirement Verification Map

| Requirement | Behavior | Test Type | Coverage | Status |
|-------------|----------|-----------|----------|--------|
| REQ-ws-035 | lean soul rewrite (5 specialists) | grep | `grep` decision-rules/escalation in `skills/*-specialist/SKILL.md`; `hermes skill run --dry-run` | ✅ COVERED (content) |
| REQ-ws-036 | coder build/test gate in Diff JSON | unit | `test_quality_uplift.py` + `grep build_passed aider_runner.py` | ✅ COVERED |
| REQ-ws-037 | reviewer pass-1 build/test gate | unit | `test_quality_uplift.py` + `grep build_passed workshop_reviewer.py` | ✅ COVERED |
| REQ-ws-038 | structured failure contract {file,problem,required_fix} | unit | `test_quality_uplift.py` (schema validated) | ✅ COVERED |
| REQ-ws-039 | two-pass review (spec+build / quality+security) | unit | `test_quality_uplift.py` | ✅ COVERED |
| REQ-ws-040 | HITL escalation exit code 2 | unit+live | `tests/phase-04/test_workshop_build.py` + 08-UAT Test 5 (live VPS hitl-test-002) | ✅ COVERED |
| REQ-ws-041 | planner/reviewer brain reads | grep | `grep brain-query` in planner/reviewer SKILL.md (≥2) + `planner-smoke.bats` | ✅ COVERED (content) |
| REQ-ws-042 | workshop-fix push path + requirements stage | grep | `grep workshop_continue` + `grep requirements` in workshop-fix SKILL.md | ✅ COVERED (content) |

**Nyquist check:** Behavioral requirements (036–040) have unit coverage; soul/skill-content requirements (035, 041, 042) have deterministic grep assertions. No 3-consecutive uncovered. Compliant.

## Manual-Only Verifications
| Behavior | Requirement | Why Manual |
|----------|-------------|------------|
| Live full-pipeline reviewer/approval on a real completing task | REQ-ws-036..040 | Phase 8 smoke had coder timeout at 900s (superseded by Phase 10 idle-watchdog); needs live re-proof |

## Validation Sign-Off
- [x] All requirements have automated/grep verify
- [x] REQ-ws-040 live-confirmed (08-UAT Test 5)
- [x] `nyquist_compliant: true`

## Validation Audit 2026-06-01
| Metric | Count |
|--------|-------|
| Requirements audited | 8 |
| Covered (unit) | 5 |
| Covered (deterministic grep) | 3 |
| New tests generated | 0 |
