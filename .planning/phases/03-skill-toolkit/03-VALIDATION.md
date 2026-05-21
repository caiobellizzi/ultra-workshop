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
| 01-T1 | 03-01 | 0 | REQ-ws-003/004/005/006 (infra) | T-03-01,T-03-02 | hermes-skill-run.sh uses exec not eval; no shell injection | bash dry-run | `bash scripts/hermes-skill-run.sh some-skill --dry-run` exits 0 | scripts/hermes-skill-run.sh | ⬜ pending |
| 01-T2 | 03-01 | 0 | REQ-ws-003/004/005/006 (infra) | T-03-03 | sudo -u uws drop; VPS chmod +x | bats | `bats tests/phase-03/scaffold.bats` 2/2 pass | tests/phase-03/helpers.bash, tests/phase-03/scaffold.bats | ⬜ pending |
| 01-T3 | 03-01 | 0 | REQ-ws-003/004/005/006 (infra) | T-03-SC | pytest collection clean | pytest | `pytest hermes-skills/test_skill_frontmatter.py --collect-only` exits 0 | hermes-skills/test_skill_frontmatter.py | ⬜ pending |
| 02-T1 | 03-02 | 1 | REQ-ws-003 | T-03-04,T-03-05 | dry-run safety; no writes outside translated/ | pytest | `pytest scripts/test_audit.py` RED (pre-impl) | scripts/test_audit.py | ⬜ pending |
| 02-T2 | 03-02 | 1 | REQ-ws-003 | T-03-04,T-03-07 | path traversal mitigation; idempotency | pytest | `pytest scripts/test_audit.py -v` all pass (GREEN) | scripts/audit-claude-skills.py | ⬜ pending |
| 03-T1 | 03-03 | 1 | REQ-ws-004 | T-03-08,T-03-09 | no tools:/mcpServers: keys; dry-run in body | pytest | `pytest hermes-skills/test_skill_frontmatter.py -v -k "caveman or diagnose or knowledge"` | skills/caveman/SKILL.md … skills/triage/SKILL.md (7 files) | ⬜ pending |
| 03-T2 | 03-03 | 1 | REQ-ws-004 | T-03-10,T-03-11 | no subagent_type=Explore; TRANSLATION NOTE present | bats | `bats tests/phase-03/skills-smoke.bats` 10/10 | skills/commit/SKILL.md, skills/triage-issue/SKILL.md, skills/qa/SKILL.md, tests/phase-03/skills-smoke.bats | ⬜ pending |
| 04-T1 | 03-04 | 2 | REQ-ws-005 | T-03-12,T-03-13 | form-data not JSON; synchronous; error surfaced stderr | bash + ssh | VPS `python3 brain_http.py query 'ping'` returns JSON with run_id | hermes-skills/brain_http.py | ⬜ pending |
| 04-T2 | 03-04 | 2 | REQ-ws-005 | T-03-14,T-03-15 | brain-ingest HITL warning; V4 relaxation documented | bats | `bats tests/phase-03/brain-smoke.bats` 3+ pass (dry-runs) | skills/brain-query/SKILL.md, skills/brain-ingest/SKILL.md, skills/brain-research/SKILL.md, tests/phase-03/brain-smoke.bats | ⬜ pending |
| 05-T0 | 03-05 | 2 | REQ-ws-006 | T-03-20 | V5 precheck gate | checkpoint | Human confirms private-worker reachable via curl precheck | — | ⬜ pending |
| 05-T1 | 03-05 | 2 | REQ-ws-006 | T-03-16,T-03-17 | shell=False; no LITELLM_API_KEY in stdout | pytest | `pytest hermes-skills/test_skill_frontmatter.py -v -k aider` 2 pass | hermes-skills/aider_runner.py, skills/aider/SKILL.md | ⬜ pending |
| 05-T2 | 03-05 | 2 | REQ-ws-006 | T-03-18,T-03-19 | SKIP not FAIL when private-worker down; cost ledger non-blocking | bats | `bats tests/phase-03/aider-smoke.bats` exits 0 (1+ pass, rest SKIP if private-worker down) | tests/phase-03/aider-smoke.bats | ⬜ pending |

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
