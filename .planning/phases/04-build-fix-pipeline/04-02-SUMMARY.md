---
phase: 04-build-fix-pipeline
plan: "02"
subsystem: workshop-pipeline-skills
tags: [workshop, skills, hermes, specialist, triage, planner, coder, reviewer, pr-opener, git, adr]
dependency_graph:
  requires: [04-00]
  provides: [triage-specialist/SKILL.md, planner-specialist/SKILL.md, coder-specialist/SKILL.md, reviewer-specialist/SKILL.md, pr-opener/SKILL.md, hermes-skills/workshop_push.py]
  affects: [workshop/orchestrator.py, scripts/hermes-skill-run.sh, workshop-build/SKILL.md]
tech_stack:
  added: []
  patterns: [hermes-skill-run.sh subprocess pattern, shell=False security invariant, non-blocking try/except ADR write-back, dotted-namespace frontmatter keys]
key_files:
  created:
    - skills/triage-specialist/SKILL.md
    - skills/planner-specialist/SKILL.md
    - skills/coder-specialist/SKILL.md
    - skills/reviewer-specialist/SKILL.md
    - skills/pr-opener/SKILL.md
    - hermes-skills/workshop_push.py
  modified: []
decisions:
  - "Each specialist SKILL.md emits JSON to stdout — captured by subprocess.run(capture_output=True) in workshop_build.py"
  - "coder-specialist creates /tmp/uws-sandbox-{task_id}/ as workspace_dir and passes it through to reviewer and pr-opener"
  - "workshop_push.py uses shell=False for both git push and gh pr create, GH_TOKEN from env (GITHUB_PAT)"
  - "ADR write-back is non-blocking try/except — PR failure does not abort if only ADR write fails"
  - "All five skills include Dry-run Behavior section returning hardcoded example JSON for testing without VPS"
metrics:
  duration: "4m"
  completed_date: "2026-05-22"
  tasks_completed: 2
  files_created: 6
---

# Phase 4 Plan 02: Specialist SKILL.md Files + workshop_push.py Summary

Five Architecture-B specialist Hermes SKILL.md files and standalone workshop_push.py post-approval helper: triage, planner, coder, reviewer, pr-opener each emit JSON to stdout; workshop_push.py does git push + gh pr create (shell=False) + non-blocking ADR write-back with dotted-namespace frontmatter.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Four specialist SKILL.md files | 1f3d8e9 | skills/triage-specialist/SKILL.md, skills/planner-specialist/SKILL.md, skills/reviewer-specialist/SKILL.md, skills/coder-specialist/SKILL.md |
| 2 | pr-opener SKILL.md and workshop_push.py | 0aee047 | skills/pr-opener/SKILL.md, hermes-skills/workshop_push.py |

## What Was Built

### Task 1: Four Specialist SKILL.md Files

All four skills follow the `skills/aider/SKILL.md` structural pattern with YAML frontmatter, Behavior section, Output Schema section, and Dry-run Behavior section.

**triage-specialist/SKILL.md** — Classifies the goal as `BUILD` (new feature) or `FIX` (bug/issue reference) and assesses complexity (`low`/`medium`/`high`). Emits `{"task_type", "summary", "complexity"}` JSON to stdout.

**planner-specialist/SKILL.md** — Generates a 2–5 step Plan from the goal and triage result, optionally querying Brain for related code patterns. Emits Plan JSON per `workshop/types.py` schema with `goal`, `steps`, and `affected_files`.

**reviewer-specialist/SKILL.md** — Compares diff changes against plan steps and affected files, checks for regressions and quality issues. Emits Review JSON with `passed`, `feedback`, and `blocking_issues`.

**coder-specialist/SKILL.md** — Determines or creates `/tmp/uws-sandbox-{task_id}/`, clones test-workshop-sandbox, creates `workshop/{task_id}` branch, runs `aider_runner.py`, and emits Diff JSON with `summary`, `changes`, `branch`, and **`workspace_dir`** (required by downstream steps).

### Task 2: pr-opener SKILL.md + workshop_push.py

**hermes-skills/workshop_push.py** — Standalone post-approval script:
- STEP 1: `git push origin {branch}` with `shell=False`, `GH_TOKEN` from env
- STEP 2: `gh pr create --repo caiobellizzi/test-workshop-sandbox` with `shell=False`, `GH_TOKEN` from env
- STEP 3: ADR write-back via `brain_http.call_agent("ingest", ...)` — non-blocking, wrapped in try/except; uses dotted-namespace frontmatter keys (`workshop.task_id`, `workshop.status`, `workshop.pr_url`, `system.created_by`, `date`)

**skills/pr-opener/SKILL.md** — Hermes skill that invokes `workshop_push.py` via `terminal python3` after HITL approval, extracts `pr_url` from stdout, and emits `{"pr_url", "status": "opened"}`.

## Verification Results

| Check | Result |
|-------|--------|
| All 5 SKILL.md files exist | PASS |
| workspace_dir in coder-specialist output schema | PASS (10 occurrences) |
| ADR dotted-namespace keys in workshop_push.py | PASS (5 matches) |
| shell=False for all subprocess calls | PASS (2 code occurrences) |
| shell=True absent from workshop_push.py | PASS (0 matches) |
| No delegate_typed or clarify_gateway in any SKILL.md | PASS (0 matches) |
| Python AST syntax check on workshop_push.py | PASS |
| All SKILL.md frontmatter: name, version, platforms | PASS (3 keys each) |
| def main() in workshop_push.py | PASS |
| No unexpected file deletions | PASS |

## Threat Model Compliance

All mitigations from the plan threat register are in place:

| Threat ID | Status |
|-----------|--------|
| T-04-02-01 (coder workspace tmpdir) | Addressed — coder-specialist creates /tmp/uws-sandbox-{task_id}/ |
| T-04-02-02 (gh pr create GH_TOKEN) | Addressed — shell=False; GH_TOKEN from env, never hardcoded |
| T-04-02-03 (specialist stdout injection) | Addressed — orchestrator.py validates via model_validate_json() |
| T-04-02-04 (diff_summary in ADR) | Addressed — truncated to 400 chars in workshop_push.py |

## Deviations from Plan

None — plan executed exactly as written. All five SKILL.md files and workshop_push.py implemented per the task specifications. No architectural changes required.

## Known Stubs

None. All skills emit concrete JSON schemas. The `changes: []` field in coder-specialist's dry-run example is intentional per plan spec — the reviewer uses `summary` for assessment when `changes` is empty.

## Self-Check: PASSED

Files exist:
- FOUND: skills/triage-specialist/SKILL.md
- FOUND: skills/planner-specialist/SKILL.md
- FOUND: skills/reviewer-specialist/SKILL.md
- FOUND: skills/coder-specialist/SKILL.md
- FOUND: skills/pr-opener/SKILL.md
- FOUND: hermes-skills/workshop_push.py

Commits exist:
- FOUND: 1f3d8e9 (task 1 — four specialist SKILL.md files)
- FOUND: 0aee047 (task 2 — pr-opener + workshop_push.py)
