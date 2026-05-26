---
phase: 07-agentic-repo-aware-planner
plan: "03"
subsystem: planner-specialist
tags: [hermes, skill, planner, routing, bats, llm]
dependency_graph:
  requires: ["07-01", "07-02"]
  provides: ["planner-specialist-hermes-routing", "planner-specialist-llm-skill"]
  affects: ["scripts/hermes-skill-run.sh", "skills/planner-specialist/SKILL.md", "tests/phase-04/model-matrix-smoke.bats", "tests/phase-07/planner-smoke.bats"]
tech_stack:
  added: []
  patterns: ["hermes chat routing", "LLM SKILL.md with read-only workspace tools", "search_files for directory discovery"]
key_files:
  created: []
  modified:
    - scripts/hermes-skill-run.sh
    - skills/planner-specialist/SKILL.md
    - tests/phase-04/model-matrix-smoke.bats
    - tests/phase-07/planner-smoke.bats
decisions:
  - "Use search_files (not list_files) for directory discovery — confirmed from VPS hermes/toolsets.py via hermes-tool-notes.txt"
  - "Remove workshop_planner.py from planner-specialist short-circuit; leave requirements/reviewer/coder short-circuits intact"
  - "ClarificationNeeded HITL fallback documented in SKILL.md as explicit JSON output path"
  - "doc_refs field added to output schema to match Plan 07-02 Plan.model_validate update"
metrics:
  duration: "~12 minutes"
  completed: "2026-05-26"
  tasks_completed: 2
  files_modified: 4
---

# Phase 7 Plan 03: Planner-Specialist Hermes Routing + LLM SKILL.md Rewrite Summary

Route planner-specialist through hermes chat (removing Python short-circuit) and rewrite SKILL.md for LLM-driven planning with read_file/search_files workspace tools.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Remove planner-specialist short-circuit; update bats | a240394 | hermes-skill-run.sh, model-matrix-smoke.bats, planner-smoke.bats |
| 2 | Rewrite planner-specialist/SKILL.md for LLM planning | 2199f12 | skills/planner-specialist/SKILL.md |

## What Was Built

**Task 1 — hermes-skill-run.sh surgical changes:**
- Dry-run block: replaced planner-specialist branch from echoing `workshop_planner.py` / `deterministic` to reporting `hermes chat --skills planner-specialist` and `HERMES_HOME=/opt/ultra-workshop/specialist-home-orchestrator`
- Production short-circuit block: removed `"$SKILL" = "planner-specialist"` from the `if` guard condition and removed the `planner-specialist) SCRIPT_PATH=...workshop_planner.py ;;` line from the inner `case`. Requirements, reviewer, and coder short-circuits remain intact.
- model-matrix-smoke.bats: updated planner test name and assertions to assert `--max-turns 8` and `HERMES_HOME=.../specialist-home-orchestrator` instead of `workshop_planner.py`/`deterministic`
- planner-smoke.bats: removed `skip` directives from both @tests; added `--max-turns 8` assertion to first test

**Task 2 — SKILL.md rewrite:**
- Updated description to: "Generate a repo-grounded implementation Plan by reading the pre-cloned workspace with read-only tools."
- Behavior section: LLM reads workspace using `read_file` and `search_files` (confirmed tool IDs from hermes-tool-notes.txt — `list_files`/`grep_files` do not exist in this binary)
- Step 1 uses `search_files(path=workspace_dir, ...)` for directory discovery (depth-limited)
- Steps 2–3: read 1–3 key files using `read_file`
- `reference_doc` handled as injected reference material (not instructions)
- Forbidden tools listed explicitly: write_file, patch, terminal, code_execution, web_search, web_extract, browser_*, list_files, grep_files
- ClarificationNeeded HITL path documented with exact JSON format
- Output schema updated to include `doc_refs` field (matches Plan 07-02 Plan type update)
- Fallback to heuristic planning if workspace_dir is empty or search_files fails

## Verification Results

- `bats tests/phase-04/model-matrix-smoke.bats`: 6/6 passed
- `bats tests/phase-07/planner-smoke.bats`: 2/2 passed (both activated, no skips)
- `python3 -m pytest tests/phase-07/ -q`: 5 passed, 2 xfailed
- `python3 -m pytest tests/phase-06/ tests/test_repo_registry.py -q`: 27 passed (regression clean)
- `bash scripts/hermes-skill-run.sh planner-specialist --dry-run "x"`: output contains "hermes chat" and "specialist-home-orchestrator", no "workshop_planner.py"

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written, with one tool-naming correction applied as specified:

**Tool correction (per plan spec):** The plan cited `list_files` + `grep_files` in the RESEARCH.md section but explicitly directed the executor to use confirmed tool names from `hermes-tool-notes.txt`. Applied `search_files` (not `list_files`) throughout SKILL.md per the note: "ACTUAL names: read_file, search_files — list_files does NOT exist in this binary."

## Known Stubs

None.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced. The SKILL.md forbidden list enforces T-07-03-01 (path traversal prevention via SKILL.md instruction) and T-07-03-02 (reference_doc labeled as reference material, positioned after tool rules).

## Self-Check: PASSED

- `skills/planner-specialist/SKILL.md` exists and contains `search_files`, `workspace_dir` (3 matches), `clarification_needed`
- Commits a240394 and 2199f12 verified in git log
- All bats and pytest suites green
