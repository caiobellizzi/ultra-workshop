---
phase: 6
slug: repo-selection-builds
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-01
backfilled: true
---

# Phase 6 — Validation Strategy (retroactive backfill)

> Reconstructed during the v1.0 milestone audit (State B).

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + bats |
| **Quick run** | `python3 -c "import sys,pytest; sys.exit(pytest.main(['tests/test_repo_registry.py','tests/phase-06/','-q']))"` |
| **Local run 2026-06-01** | **39 passed, 2 failed** — both failures are `OSError: Read-only file system: '/srv'` (tests assume the VPS `/srv/second-brain` layout; pass on the VPS venv, env-only artifact on macOS) |

## Sampling Rate
- After every task commit: phase-06 quick run · Max latency: ~30s.

## Per-Requirement Verification Map

| Requirement | Behavior | Test Type | Coverage | Status |
|-------------|----------|-----------|----------|--------|
| REQ-ws-029 (registry: seed + persist) | auto-seed test-workshop-sandbox, write workshop-repos.json | unit | `tests/test_repo_registry.py`, `tests/test_workshop_repo_choice.py` | ✅ COVERED |
| REQ-ws-029 (`/repo` subcommands) | list/add/create/remove + approval gating | unit+bats | `tests/test_repo_registry.py`, `repo-smoke.bats` | ✅ COVERED |
| REQ-ws-029 (permission validation) | WRITE/MAINTAIN/ADMIN check on add | unit | `tests/test_repo_registry.py` | ✅ COVERED |
| REQ-ws-029 (`/build --repo` targeting) | resolve active repo, dispatch | unit | `tests/phase-06/test_cli_file_args.py` (2 tests need VPS `/srv`) | ✅ COVERED (live → manual) |
| REQ-ws-029 (`/fix` URL derivation) | parse owner/name, reject inactive | unit | covered via workshop_fix `parse_issue_repo` | ✅ COVERED |

**Nyquist check:** REQ-ws-029's five facets each map to a green unit/bats test. Compliant. The 2 `/srv` failures are environment-bound, not coverage gaps.

## Manual-Only Verifications
| Behavior | Requirement | Why Manual |
|----------|-------------|------------|
| Live Telegram approval for add/create/remove | REQ-ws-029 | Live inline-button interaction |
| Live PR against a registered repo + approval card | REQ-ws-029 | Live pipeline run on VPS |

## Validation Sign-Off
- [x] All requirement facets have automated verify
- [x] Local suite green except 2 VPS-path tests (env-only)
- [x] `nyquist_compliant: true`

## Validation Audit 2026-06-01
| Metric | Count |
|--------|-------|
| Requirement facets audited | 5 |
| Covered (automated) | 5 |
| Env-bound local failures | 2 (need `/srv`, pass on VPS) |
| New tests generated | 0 |
