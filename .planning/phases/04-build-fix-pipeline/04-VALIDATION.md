---
phase: 4
slug: build-fix-pipeline
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-01
backfilled: true
---

# Phase 4 — Validation Strategy (retroactive backfill)

> Reconstructed during the v1.0 milestone audit (State B). Phase shipped with a test suite; this contract maps each requirement to its existing automated coverage.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (Python) + bats (shell smoke) |
| **Quick run** | `python3 -c "import sys,pytest; sys.exit(pytest.main(['tests/phase-04/','-q']))"` |
| **Full suite** | `python3 -m pytest tests/ -q` (needs VPS venv with httpx) + `bats tests/phase-04/*.bats` |
| **Local run 2026-06-01** | `tests/phase-04/` → **45 passed** (RTK-bypassed) |

## Sampling Rate
- After every task commit: `tests/phase-04/` quick run · After every wave: full suite · Max latency: ~30s.

## Per-Requirement Verification Map

| Requirement | Behavior | Test Type | Coverage | Status |
|-------------|----------|-----------|----------|--------|
| REQ-ws-028 | Pydantic schemas + run_specialist validation | unit | `test_orchestrator.py`, `test_extract_json.py` | ✅ COVERED |
| REQ-ws-007 | workshop-build pipeline | unit+bats | `test_workshop_build.py`, `build-smoke.bats` | ✅ COVERED (+live 04-UAT) |
| REQ-ws-008 | workshop-fix path | bats+live | `fix-smoke.bats` | ✅ COVERED (+live 04-UAT) |
| REQ-ws-009 | two-ledger audit trail | unit | `test_ledger.py` | ✅ COVERED |
| REQ-ws-010 | HITL gate before PR | unit+live | `test_workshop_build.py` + 04-UAT Test 5 | ✅ COVERED |
| REQ-ws-011 | ADR write-back | unit | `test_workshop_continue.py` | ✅ COVERED (live ADR → manual) |
| REQ-ws-012 | cost ledger + circuit breaker | unit | `test_cost.py` | ✅ COVERED (live $18/$20 → manual) |

**Nyquist check:** No 3 consecutive requirements without automated verify. Every REQ maps to a green unit/bats test. Compliant.

## Manual-Only Verifications
| Behavior | Requirement | Why Manual |
|----------|-------------|------------|
| Live $18 self-cancel / $20 refusal | REQ-ws-012 | Needs real accumulated spend in brain cost-ledger |
| Fresh live ADR file write to vault | REQ-ws-011 | Needs live brain ingest on VPS (path is unit-tested) |

## Validation Sign-Off
- [x] All requirements have automated verify
- [x] Sampling continuity: no 3-consecutive automation gap
- [x] Local suite green (45 passed, 2026-06-01)
- [x] `nyquist_compliant: true`

## Validation Audit 2026-06-01
| Metric | Count |
|--------|-------|
| Requirements audited | 7 |
| Covered (automated) | 7 |
| Manual-only residual | 2 (live budget breach, live ADR) |
| New tests generated | 0 (existing suite sufficient) |
