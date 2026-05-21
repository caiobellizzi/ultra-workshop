---
phase: 3
slug: skill-toolkit
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-21
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | bats 1.x (smoke) + pytest 7.x (audit script unit tests) |
| **Config file** | `tests/bats/helpers.bash`, `pyproject.toml` |
| **Quick run command** | `bats tests/bats/skill-smoke.bats` |
| **Full suite command** | `bats tests/bats/*.bats && pytest tests/python/` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run `bats tests/bats/skill-smoke.bats` (subset for the affected skill)
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

> Populated by gsd-planner. Each plan task produces a row here.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _planner fills_ | _ | _ | _ | _ | _ | _ | _ | _ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/bats/helpers.bash` — shared bats helpers (Hermes path, smoke wrapper)
- [ ] `tests/python/test_audit.py` — pytest stubs for REQ-ws-003 audit script
- [ ] `tests/python/conftest.py` — shared fixtures (tmp Claude skill tree, mock Hermes target)
- [ ] `scripts/hermes-skill-run.sh` — wrapper that maps `hermes skill run <name> --dry-run` to the real CLI (per RESEARCH.md finding 1)
- [ ] bats install verified on VPS (`which bats`)

*If existing infrastructure covers a Wave 0 item, the planner records "N/A — already present".*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `private-worker` (LM Studio on Mac) reachable from VPS LiteLLM | REQ-ws-006 | Requires Mac to be awake and LM Studio process running | Wake Mac, confirm LM Studio is loaded, then run `curl http://127.0.0.1:4000/v1/models \| jq '.data[].id' \| grep private-worker` from VPS |
| brain-query returns a real vault-grounded answer with citations | REQ-ws-005 | Brain's Groq + tool-calling path currently returns ERROR — per-phase decision relaxed V5 to HTTP round-trip only. Real answer test deferred. | Once Brain's Groq/structured-output is fixed, run `hermes-skill-run brain-query --question "what is PARA"` and inspect citations |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
