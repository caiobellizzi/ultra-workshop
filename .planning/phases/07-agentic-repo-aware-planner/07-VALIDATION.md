---
phase: 7
slug: agentic-repo-aware-planner
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-25
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (Python) + bats (shell smoke) |
| **Config file** | none for pytest (test discovery); bats in `tests/phase-04`, `tests/phase-06`, `tests/phase-07` |
| **Quick run command** | `python -m pytest tests/phase-07/ tests/phase-06/ tests/test_repo_registry.py -q` |
| **Full suite command** | `python -m pytest tests/ -q && bats tests/phase-04/model-matrix-smoke.bats && bats tests/phase-06/repo-smoke.bats && bats tests/phase-07/planner-smoke.bats` |
| **Estimated runtime** | ~90 seconds (excludes live VPS hermes calls) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command
- **After every plan wave:** Run the full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

> Every task with a Plan-affecting behavior maps to an automated verify command or Wave 0 dependency.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-01-T1 | 01 | 0 | REQ-ws-034 | — | test scaffold isolation (no production side effects) | unit | `python -m pytest tests/phase-07/ -v --no-header` | ❌ W0 creates | ⬜ pending |
| 07-01-T2 | 01 | 0 | REQ-ws-031 | T-07-01-01 | hermes tools list is read-only VPS command | manual | Manual VPS: `hermes tools list` + `cat HERMES.md` | N/A manual | ⬜ pending |
| 07-02-T1 | 02 | 1 | REQ-ws-030 | — | workspace_dir default value in state.json | unit | `python -m pytest tests/phase-07/test_workspace.py::test_new_task_state_has_workspace_dir -xvs` | ❌ W0 creates | ⬜ pending |
| 07-02-T2 | 02 | 1 | REQ-ws-032 | T-07-02-01, T-07-02-02 | doc traversal guard + 3-tier resolution | unit | `python -m pytest tests/phase-07/test_doc_resolver.py -xvs` | ❌ W0 creates | ⬜ pending |
| 07-03-T1 | 03 | 2 | REQ-ws-031, REQ-ws-034 | T-07-03-01 | planner routes hermes chat; bats regression green | bats | `bats tests/phase-04/model-matrix-smoke.bats && bats tests/phase-07/planner-smoke.bats` | Phase-04 exists; phase-07 W0 creates | ⬜ pending |
| 07-03-T2 | 03 | 2 | REQ-ws-031, REQ-ws-033 | T-07-03-02 | reference_doc injected as context not instructions | unit | `python -m pytest tests/phase-07/test_planner_llm.py::test_plan_schema_valid -xvs` | ❌ W0 creates | ⬜ pending |
| 07-04-T1 | 04 | 3 | REQ-ws-030, REQ-ws-033 | T-07-04-01, T-07-04-02 | clone-before-planner; workspace_dir in state | unit | `python -m pytest tests/phase-07/test_workspace.py -xvs` | ❌ W0 creates | ⬜ pending |
| 07-05-T1 | 05 | 4 | REQ-ws-033, REQ-ws-034 | — | full regression suite green | mixed | `python -m pytest tests/phase-07/ -q && python -m pytest tests/phase-06/ tests/test_repo_registry.py -q && bats tests/phase-04/model-matrix-smoke.bats` | Phase-06, phase-04 exist | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Nyquist check:** No 3 consecutive tasks without automated verify. Task 07-01-T2 (manual) is the only manual step and is immediately followed by 07-02-T1 (automated). Compliant.

---

## Wave 0 Requirements

- [ ] `tests/phase-07/` — new test directory (Plan 01 Task 1)
- [ ] `tests/phase-07/__init__.py` — empty init for pytest discovery (Plan 01 Task 1)
- [ ] `tests/phase-07/test_doc_resolver.py` — 4 xfail stubs for REQ-ws-032 (Plan 01 Task 1; activated in Plan 02 Task 2)
- [ ] `tests/phase-07/test_workspace.py` — 2 xfail stubs for REQ-ws-030 (Plan 01 Task 1; activated in Plans 02 + 04)
- [ ] `tests/phase-07/test_planner_llm.py` — 1+ xfail stubs for REQ-ws-033 (Plan 01 Task 1; activated in Plan 05)
- [ ] `tests/phase-07/planner-smoke.bats` — 2 skip stubs for REQ-ws-031 (Plan 01 Task 1; activated in Plan 03)
- [ ] `tests/phase-07/hermes-tool-notes.txt` — Hermes tool names confirmed (Plan 01 Task 2 checkpoint)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `planner-specialist` runs as LLM via `hermes chat` with read-only repo tools scoped to `workspace_dir` | REQ-ws-031 | Requires live VPS hermes runtime + LiteLLM orchestrator model | On VPS: `HERMES_HOME=/opt/ultra-workshop/specialist-home-orchestrator /opt/ultra-workshop/hermes/venv/bin/hermes tools list`; confirm read tool IDs allowed and write/web/code-exec forbidden |
| End-to-end `affected_files` accuracy vs coder changes (zero reviewer false-blocks) | REQ-ws-033 | Needs full pipeline run on VPS with a real task whose files differ from keyword guesses | Run `/build --repo caiobellizzi/test-workshop-sandbox "add logging to orchestrator"` and confirm reviewer raises zero "changed files outside the plan" blocks |
| Pipeline latency: planner stage completes within 480s with LM Studio + repo I/O | REQ-ws-034 (SC-6) | Requires live VPS with LM Studio running | Time the planner stage on VPS; confirm no StageTimeoutExpired in logs |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING test references
- [x] No watch-mode flags
- [x] Feedback latency < 90s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending execution
