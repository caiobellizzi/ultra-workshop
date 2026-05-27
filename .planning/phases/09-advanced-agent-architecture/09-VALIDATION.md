---
phase: 9
slug: advanced-agent-architecture
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-27
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + bats 14 integration tests |
| **Config file** | `pyproject.toml` (`testpaths = ["hermes-skills", "scripts"]`) |
| **Quick run command** | `python -m pytest hermes-skills/ tests/ -q` |
| **Full suite command** | `python -m pytest hermes-skills/ scripts/ tests/ -v && bash tests/phase-08/*.bats 2>/dev/null` |
| **Estimated runtime** | ~15 seconds (unit), ~60 seconds (full with bats) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest hermes-skills/ tests/ -q`
- **After every plan wave:** Run `python -m pytest hermes-skills/ scripts/ tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green (45 pytest + bats) — run `python -m pytest hermes-skills/ scripts/ tests/ -v && bash tests/phase-08/*.bats 2>/dev/null`
- **Max feedback latency:** 15 seconds (quick run)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-SC1-brainstorm-soul | TBD | 1 | REQ-ws-043 | — | Brainstorm exits only on `brainstorm_approved=True` | unit | `pytest tests/phase-09/test_brainstorm_hitl.py -v` | ❌ W0 | ⬜ pending |
| 09-SC1-stage-index | TBD | 1 | REQ-ws-043 | — | `_STAGE_INDEX` cursor ordering preserved after brainstorm insertion | unit | `pytest tests/phase-09/test_stage_policy.py -v 2>/dev/null || pytest hermes-skills/test_stage_policy.py -v` | ✅ | ⬜ pending |
| 09-SC2-budget-layer | TBD | 1 | REQ-ws-044 | — | Per-role cap checked before dispatch; auto-pause fires at 100% | unit | `pytest tests/phase-09/test_cost_budget.py -v` | ❌ W0 | ⬜ pending |
| 09-SC3-audit-log | TBD | 1 | REQ-ws-045 | — | JSONL written to `vault/_system/workshop-audit/{task_id}.jsonl` | unit | `pytest tests/phase-09/test_audit_log.py -v` | ❌ W0 | ⬜ pending |
| 09-SC4-review-wave-dispatch | TBD | 2 | REQ-ws-046 | — | 8 reviewer souls dispatched via ThreadPoolExecutor, not sequentially (per D-01/D-04) | unit | `pytest tests/phase-09/test_review_wave.py -v` | ❌ W0 | ⬜ pending |
| 09-SC4-merge-agent | TBD | 2 | REQ-ws-046 | — | Merge agent deduplicates by (file, line) and auto-fixes severity:low | unit | `pytest tests/phase-09/test_merge_agent.py -v` | ❌ W0 | ⬜ pending |
| 09-SC5-isolation-policy | TBD | 2 | REQ-ws-047 | — | Isolation policy doc exists; all code/review agents use isolated context | manual | Read `docs/agent-isolation-policy.md` — verify all agent dispatches | ❌ W0 | ⬜ pending |
| 09-SC6-brain-prereq | TBD | 1 | REQ-ws-048 | — | `requirements-specialist` calls brain before HITL trigger | unit | `pytest tests/phase-09/test_requirements_gate.py -k brain_prereq 2>/dev/null || pytest hermes-skills/test_requirements_gate.py -k brain_prereq` | ✅ | ⬜ pending |
| 09-regression | TBD | 3 | all | — | Existing 45+14 tests still green after all changes | regression | `python -m pytest hermes-skills/ scripts/ tests/ -q && bash tests/phase-08/*.bats` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/phase-09/test_brainstorm_hitl.py` — stubs for SC-1 (brainstorm loop does NOT exit without brainstorm_approved=True; exits when approval signal set); created in 09-02 Task 1
- [ ] `tests/phase-09/test_cost_budget.py` — stubs for SC-2 (per-role monthly cap + auto-pause + Telegram warn at 80%, alert at 100%); created in 09-01 Task 1
- [ ] `tests/phase-09/test_audit_log.py` — stubs for SC-3 (append_audit fire-and-forget via daemon thread); created in 09-01 Task 1
- [ ] `tests/phase-09/test_review_wave.py` — stubs for SC-4 (parallel dispatch, not sequential); created in 09-02 Task 1
- [ ] `tests/phase-09/test_merge_agent.py` — stubs for SC-4 (dedup by (file, line), severity routing); created in 09-02 Task 1

*Wave 0 must be committed before any implementation tasks begin.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| AgentTool/SkillTool isolation policy documented | REQ-ws-047 | Documentation completeness, not behavior | Read `docs/agent-isolation-policy.md`; verify all agent dispatch sites reference the policy |
| Brainstorm HITL exit via owner approval | REQ-ws-043 | Multi-turn human interaction required | Run a workshop build, enter brainstorm stage, provide approval signal; verify `brainstorm_approved=True` in state |
| Audit trail appended to correct vault path | REQ-ws-045 | Requires live Brain integration | Run a build, inspect `vault/_system/workshop-audit/{task_id}.jsonl` for event entries |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
