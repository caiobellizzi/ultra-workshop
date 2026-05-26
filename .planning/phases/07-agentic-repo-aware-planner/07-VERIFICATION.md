---
phase: 07-agentic-repo-aware-planner
verified: 2026-05-26T14:30:00Z
status: human_needed
score: 5/6
overrides_applied: 0
human_verification:
  - test: "Run a real /build task referencing a doc (e.g. prd.md) and confirm the planner produces affected_files that match what the coder actually changes"
    expected: "reviewer raises zero 'changed files outside the plan' false-blocks for a task whose affected_files come from workspace file listing (not keyword guesses)"
    why_human: "SC-4 depends on live LLM planner output reading the cloned workspace; cannot verify without a real hermes chat execution against a live VPS with an actual repo clone"
---

# Phase 7: Agentic Repo-Aware Planner — Verification Report

**Phase Goal:** Upgrade the planner from a blind keyword-heuristic to an LLM planner that reads a pre-cloned repo and resolved reference docs. Keeps subprocess + HERMES_HOME transport and the deterministic state machine. No `delegate_task`.
**Verified:** 2026-05-26T14:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | Repo cloned before planner stage; single `workspace_dir` persisted in `state.json`; resumable after restart | VERIFIED | `clone_repo_to_workspace()` in `workshop/state.py:88` skips re-clone if `.git` exists; `workshop_build.py:322` clones before planner query; `state["workspace_dir"]` saved via `save_task_state(state)`; both workspace tests pass |
| SC-2 | `planner-specialist` runs as LLM via `hermes chat`; read-only tools scoped to `workspace_dir`; write/web/code-exec forbidden | VERIFIED | `scripts/hermes-skill-run.sh` has zero occurrences of `workshop_planner.py`; dry-run output confirmed `hermes chat` + `HERMES_HOME=specialist-home-orchestrator`; SKILL.md v2.0.0 lists `read_file`/`search_files` allowed and write/execute/web explicitly forbidden; both planner-smoke.bats tests pass |
| SC-3 | `resolve_doc()` — repo-first → vault-grep → Brain HTTP; path-traversal guard; VAULT_VPS_PATH env var | VERIFIED | `workshop/doc_resolver.py` implements 3-tier logic; `_validate_doc_name()` raises `ValueError` on `..`, `/`, null bytes; `VAULT_VPS_PATH` env var with `/srv/second-brain` fallback at line 24; all 4 doc_resolver tests pass (tier1, tier2, tier3 degraded, traversal blocked) |
| SC-4 | For a task whose true target files differ from keyword guesses, planner's `affected_files` match what coder actually changes; reviewer raises zero false-blocks | UNCERTAIN | SKILL.md correctly instructs LLM to use exact paths from `search_files` output; `workshop_build.py` injects `workspace_dir` and `reference_doc` into `planner_query`; cannot verify live LLM output without real VPS execution — routes to human check |
| SC-5 | Subprocess + HERMES_HOME isolation, state.json resumability, exit(2) HITL, reviewer safety gates unchanged; no `delegate_task` | VERIFIED | grep confirms no `delegate_task` in any modified file; `_path_issue`, secret regex, `py_compile` not modified in phase-07; state machine unchanged; all phase-04 and phase-06 regression suites green (88 pytest passed, all 6 bats passed) |
| SC-6 | Phase-4 and Phase-6 suites stay green; planner timeout accommodates repo I/O | VERIFIED | `workshop/stage_policy.py:17` `StagePolicy(timeout=480, auto_retries=1)` confirmed; `python -m pytest tests/ -q` → 88 passed; `bats tests/phase-04/model-matrix-smoke.bats` → 6/6 ok; `bats tests/phase-07/planner-smoke.bats` → 2/2 ok |

**Score:** 5/6 truths verified (SC-4 is UNCERTAIN — routes to human verification)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `workshop/state.py` | `workspace_dir` key in `new_task_state()` + `clone_repo_to_workspace()` | VERIFIED | Line 47: `"workspace_dir": ""`; `clone_repo_to_workspace()` at line 88 with `.git` resume guard |
| `workshop/stage_policy.py` | planner `StagePolicy(timeout=480, ...)` | VERIFIED | Line 17 confirmed |
| `workshop/doc_resolver.py` | 3-tier `resolve_doc()` with traversal guard + VAULT_VPS_PATH | VERIFIED | File exists (3.1 KB); `_validate_doc_name()` rejects `..`/`/`/null; VAULT_VPS_PATH at line 24; brain_http optional import |
| `scripts/hermes-skill-run.sh` | planner-specialist removed from Python short-circuit; dry-run reports hermes chat | VERIFIED | Zero matches for `workshop_planner` in file; dry-run block at lines 50-52 outputs hermes chat + HERMES_HOME |
| `skills/planner-specialist/SKILL.md` | LLM behavior with confirmed tool IDs (`read_file`/`search_files`); workspace_dir; clarification_needed | VERIFIED | Version 2.0.0; uses VPS-confirmed tool IDs (`search_files` not `list_files`/`grep_files` per hermes-tool-notes.txt); 3 occurrences of `workspace_dir`; `clarification_needed` documented |
| `hermes-skills/workshop_build.py` | clone block; workspace_dir in planner_query; reference_doc in planner_query; coder uses state workspace_dir | VERIFIED | Lines 320-327 clone block; lines 407-408 planner_query keys; line 442 coder_payload uses `state.get("workspace_dir")` |
| `tests/phase-07/test_workspace.py` | both tests activated and passing | VERIFIED | `test_new_task_state_has_workspace_dir` + `test_clone_saves_workspace_dir` — both PASSED |
| `tests/phase-07/test_doc_resolver.py` | all 4 tests passing | VERIFIED | tier1, tier2, tier3_degraded, traversal_blocked — all PASSED |
| `tests/phase-07/test_planner_llm.py` | 4 tests activated (no xfail) | VERIFIED | test_plan_schema_valid, test_plan_affected_files_real_paths, test_plan_empty_affected_files, test_clarification_needed_is_not_a_plan — all PASSED |
| `tests/phase-07/planner-smoke.bats` | 2 activated (not skipped) @test entries passing | VERIFIED | 2/2 ok |
| `tests/phase-04/model-matrix-smoke.bats` | updated planner assertion (hermes chat, not workshop_planner.py) | VERIFIED | @test "planner-specialist resolves to hermes chat with specialist-home-orchestrator" — ok |
| `tests/phase-07/hermes-tool-notes.txt` | VPS-confirmed tool IDs documented | VERIFIED | Documents `read_file` + `search_files` (corrects RESEARCH.md assumption); no `list_files`/`grep_files` in this binary |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `workshop/doc_resolver.py` | `brain_http.call_agent` | `try: from brain_http import call_agent as _call_agent` | VERIFIED | Optional import with `_BRAIN_AVAILABLE` guard; graceful when brain_http absent |
| `workshop/doc_resolver.py` | `VAULT_VPS_PATH` env var | `os.environ.get("VAULT_VPS_PATH", "/srv/second-brain")` | VERIFIED | Line 24 |
| `hermes-skills/workshop_build.py` | `workshop/state.py` | `clone_repo_to_workspace(state, ...); save_task_state(state)` | VERIFIED | Lines 218, 323-324 |
| `hermes-skills/workshop_build.py` | `workshop/doc_resolver.py` | `from workshop.doc_resolver import resolve_doc as _resolve_doc`; call at line 394 | VERIFIED | ImportError guard + positional call maps correctly to `(doc_name, workspace_dir, vault_dir)` |
| `hermes-skills/workshop_build.py` | planner_query JSON | `"workspace_dir": state.get("workspace_dir") or ""` and `"reference_doc": _reference_doc` | VERIFIED | Lines 407-408 |
| `scripts/hermes-skill-run.sh` | hermes chat binary | `elif [ "$SKILL" = "planner-specialist" ]` → echoes `hermes chat` + `HERMES_HOME=specialist-home-orchestrator` | VERIFIED | Lines 50-52; no `workshop_planner.py` in production path |
| `skills/planner-specialist/SKILL.md` | `workspace_dir` | SKILL.md instructs LLM to use `search_files(path=workspace_dir, ...)` | VERIFIED | VPS-confirmed tool IDs from hermes-tool-notes.txt used throughout |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `workshop_build.py` planner_query | `workspace_dir` | `state.get("workspace_dir")` populated by `clone_repo_to_workspace()` | Yes — set from actual clone path | FLOWING |
| `workshop_build.py` planner_query | `reference_doc` | `_resolve_doc()` → workspace rglob → vault rglob → Brain HTTP | Yes — 3-tier resolution with real filesystem reads | FLOWING |
| `workshop_build.py` coder_payload | `workspace_dir` | `state.get("workspace_dir") or (diff.workspace_dir if diff else "")` | Yes — prefers pre-cloned state path | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| planner-specialist dry-run routes through hermes chat | `bash scripts/hermes-skill-run.sh planner-specialist --dry-run "x"` | outputs "hermes chat" + "HERMES_HOME=/opt/ultra-workshop/specialist-home-orchestrator", no "workshop_planner.py" | PASS |
| planner timeout = 480s | `grep 'timeout=480' workshop/stage_policy.py` | match found at line 17 | PASS |
| workspace_dir in new_task_state | `pytest tests/phase-07/test_workspace.py -v` | 2/2 PASSED | PASS |
| doc_resolver traversal guard | `pytest tests/phase-07/test_doc_resolver.py -v` | 4/4 PASSED | PASS |
| Full test suite regression | `.venv/bin/pytest tests/ -q` | 88 passed in 0.85s | PASS |

---

### Probe Execution

No conventional probe scripts found under `scripts/*/tests/probe-*.sh`. Phase deliverables verified via bats and pytest. Probe step: SKIPPED (no probe scripts).

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| REQ-ws-030 | 07-02, 07-04 | Pre-planner workspace clone + state persistence | SATISFIED | `clone_repo_to_workspace()` in state.py; `workspace_dir` in `new_task_state()`; clone before planner in workshop_build.py; both workspace tests pass |
| REQ-ws-031 | 07-03 | planner-specialist LLM via hermes chat with read-only tools | SATISFIED | hermes-skill-run.sh short-circuit removed; SKILL.md v2.0.0 rewritten; planner-smoke.bats 2/2 pass |
| REQ-ws-032 | 07-02 | 3-tier deterministic doc resolution | SATISFIED | workshop/doc_resolver.py; 4/4 doc_resolver tests pass |
| REQ-ws-033 | 07-04, 07-05 | LLM planner output accuracy + reviewer false-block elimination | PARTIALLY SATISFIED | workspace_dir + reference_doc in planner_query; SKILL.md instructs exact paths; schema tests pass; live accuracy requires human verification (SC-4) |
| REQ-ws-034 | 07-01, 07-05 | Regression safety: Phase 4 + Phase 6 suites stay green | SATISFIED | 88 pytest passed; model-matrix-smoke.bats 6/6; planner-smoke.bats 2/2 |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/phase-07/test_doc_resolver.py` | 13 | `pytest.xfail("workshop.doc_resolver not yet implemented")` — stale message in fallback guard | Info | Guard only fires if `resolve_doc is None` (import failure). Module IS implemented; tests pass. Dead path in production; no behavioral impact. |

No TBD, FIXME, or XXX markers found in any phase-07 modified files.

---

### Human Verification Required

#### 1. LLM Planner Produces Real Workspace Paths (SC-4)

**Test:** Run a live `/build` command referencing a doc (e.g., `prd.md`) on the VPS against a real repo. Inspect the resulting Plan's `affected_files`.

**Expected:** The planner's `affected_files` list contains actual file paths that match files the coder subsequently modifies. The reviewer's pass/fail decision is not blocked by "changed files outside the plan" errors caused by keyword-guessed paths.

**Why human:** SC-4 requires a live LLM execution inside hermes chat reading the pre-cloned workspace via `read_file`/`search_files`. Cannot verify the LLM's path choices without running the full pipeline on a real VPS with an actual cloned repo. All infrastructure is wired and verified; the quality of LLM output against that infrastructure requires empirical observation.

---

### Gaps Summary

No blocking gaps found. All infrastructure artifacts exist, are substantive, and are wired correctly. The 88-test regression suite is green. The single uncertain item (SC-4 — LLM planner output quality) requires a live pipeline run to observe actual affected_files accuracy.

---

_Verified: 2026-05-26T14:30:00Z_
_Verifier: Claude (gsd-verifier)_
