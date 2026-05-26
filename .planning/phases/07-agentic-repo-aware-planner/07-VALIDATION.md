---
phase: 7
slug: agentic-repo-aware-planner
status: draft
nyquist_compliant: false
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
| **Config file** | none for pytest (test discovery); bats in `tests/phase-04`, `tests/phase-06` |
| **Quick run command** | `python -m pytest tests/phase-06 tests/test_repo_registry.py -q` |
| **Full suite command** | `python -m pytest tests -q && bats tests/phase-04 tests/phase-06` |
| **Estimated runtime** | ~60 seconds (excludes live VPS hermes calls) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command
- **After every plan wave:** Run the full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

> Filled by the planner. Every task with a Plan-affecting behavior must map to an automated verify command or a Wave 0 dependency.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | TBD | — | N/A | unit | `python -m pytest tests/phase-07 -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/phase-07/` — new test directory + stubs for Phase 7 REQ ids
- [ ] `tests/phase-07/test_doc_resolver.py` — unit coverage for the 3-tier doc resolution function
- [ ] `tests/phase-07/test_state_workspace.py` — `workspace_dir` persisted in `state.json` and resumable
- [ ] bats smoke for clone-before-planner ordering (mirror `tests/phase-04` / `tests/phase-06` patterns)

*Planner refines this list against the real REQ ids it mints.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `planner-specialist` runs as LLM via `hermes chat` with read-only repo tools scoped to `workspace_dir` | TBD | Requires live VPS hermes runtime + LiteLLM orchestrator model | On VPS: `HERMES_HOME=/opt/ultra-workshop/specialist-home-orchestrator hermes tools list`; confirm `read_file`/`list_files`/`grep_files` allowed and write/web/code-exec forbidden; run a `/build --repo` against a known repo and confirm `affected_files` match real paths |
| End-to-end `affected_files` accuracy vs coder changes (zero reviewer false-blocks) | TBD | Needs full pipeline run on VPS with a real divergent task | Run a task whose true targets differ from keyword guesses; confirm reviewer raises zero "changed files outside the plan" blocks |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
