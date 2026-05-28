---
phase: "09-advanced-agent-architecture"
plan: "09-04"
subsystem: "workshop-pipeline"
tags: [stage-policy, brainstorm, reviewer-aliases, souls, hitl]
dependency_graph:
  requires: ["09-01", "09-02", "09-03"]
  provides: ["brainstorm-stage-policy", "brainstorm-soul", "reviewer-model-aliases"]
  affects: ["workshop/stage_policy.py", "skills/brainstorm-specialist", "skills/requirements-specialist", "skills/planner-specialist"]
tech_stack:
  added: []
  patterns: ["Socratic loop soul pattern", "No-turn-cap brainstorm discipline (B1-A)", "Brain pre-query in requirements gate (B7)"]
key_files:
  created:
    - skills/brainstorm-specialist/SKILL.md
  modified:
    - workshop/stage_policy.py
    - skills/requirements-specialist/SKILL.md
    - skills/planner-specialist/SKILL.md
decisions:
  - "brainstorm stage timeout=300, auto_retries=0, hitl_on_timeout=True — conversational stage escalates to HITL on timeout rather than failing hard"
  - "brainstorm-specialist model alias is default-worker (not reviewer-model) — Socratic conversation does not need code-analysis heavy model"
  - "All 8 reviewer roles + merge-agent use reviewer-model alias, consistent with review-roster.yaml"
  - "Brain pre-query added to requirements-specialist discipline (fail-open: unreachable Brain is logged and skipped)"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-28"
  tasks_completed: 3
  tasks_total: 3
  files_created: 1
  files_modified: 3
---

# Phase 09 Plan 04: Final Integration Pass — Stage Policy + Brainstorm Soul Summary

Stage policy extended with brainstorm stage and all reviewer model aliases; brainstorm-specialist soul created with Socratic loop discipline and explicit no-turn-cap (B1-A); requirements and planner souls enriched with Persona sections and brain pre-query behavior.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend stage_policy.py for brainstorm + reviewer aliases | 358c7e0 | workshop/stage_policy.py |
| 2 | Create brainstorm-specialist soul + update requirements/planner souls | 2534514 | skills/brainstorm-specialist/SKILL.md, skills/requirements-specialist/SKILL.md, skills/planner-specialist/SKILL.md |
| 3 | End-to-end smoke verification on VPS | (human verify) | /opt/ultra-workshop — all 7 checks passed |

## Task 3: COMPLETE — All 7 VPS Checks Passed

Human smoke verification completed on VPS at `/opt/ultra-workshop`:

1. 121 tests passed, 2 skipped — no regressions
2. Stage index: `{'brainstorm': 0, 'triage': 1, 'requirements': 2, 'planner': 3, 'coder': 4, 'reviewer': 5, 'approval': 6}`
3. Brainstorm dry-run: `{"approved": true, "goal_statement": "dry-run goal statement"}`
4. Merge agent dry-run: `{"block_push": false, ...}`
5. Reviewer shim dry-run: `{"passed": true, ...}`
6. All 10 souls present: correctness, security, python, typescript, reactjs, qa, docs, config, merge-agent, brainstorm-specialist
7. Policy OK

## What Was Built

### Task 1: stage_policy.py extension

Added `brainstorm` to `STAGE_POLICIES` with:
- `timeout=300` (5 minutes — conversational, more than triage's 180s)
- `auto_retries=0` (no auto-retry — brainstorm is interactive, retries don't make sense)
- `hitl_on_timeout=True` (escalates to owner on timeout rather than hard-failing)

Added `MODEL_ALIASES` entries for:
- All 8 reviewer roles: `correctness-reviewer`, `security-reviewer`, `python-reviewer`, `typescript-reviewer`, `reactjs-reviewer`, `qa-reviewer`, `docs-reviewer`, `config-reviewer` — all mapped to `reviewer-model`
- `merge-agent` → `reviewer-model`
- `brainstorm-specialist` and `brainstorm` → `default-worker`

### Task 2: Soul files

**skills/brainstorm-specialist/SKILL.md** (created):
- Socratic loop discipline — one focused question at a time
- No-turn-cap behavior (B1-A) — loop runs until explicit owner approval
- Explicit exit signal detection ("approve", "looks good", "yes", etc.)
- Output schema: `{"approved": true, "goal_statement": "..."}` 
- Dry-run behavior: hardcoded approved response
- Brain pre-query at start (scan prior clarifications before first question)
- Prohibited: no code/plans/file paths during brainstorm loop

**skills/requirements-specialist/SKILL.md** (updated):
- Added `## Persona` section before `## Discipline`
- Added brain pre-query rule to Discipline: query Brain for prior clarifications, treat as resolved context, fail-open if unreachable (B7)
- No existing discipline rules removed

**skills/planner-specialist/SKILL.md** (updated):
- Added `## Persona` section before `## Behavior`
- No existing behavior or discipline sections modified

## Deviations from Plan

None — plan executed exactly as written. Both MODEL_ALIASES keys (`brainstorm` and `brainstorm-specialist`) were added since the plan text used both terms, ensuring both lookup paths work.

## Verification Results

- `python3 -c "from workshop.stage_policy import MODEL_ALIASES, STAGE_POLICIES; ..."` — all assertions pass
- `python3 -m pytest tests/ -x -q` — 121 passed, 2 skipped (no regressions)
- `grep -c "brainstorm_approved\|goal_statement" skills/brainstorm-specialist/SKILL.md` — 6 matches
- `grep -c "prior clarifications" skills/requirements-specialist/SKILL.md` — 1 match

## Known Stubs

None. All functionality is fully wired. Task 3 (human smoke test) verifies end-to-end pipeline dry-runs on the VPS at `/opt/ultra-workshop`.

## Threat Surface Scan

No new network endpoints or auth paths introduced. The `goal_statement` injection threat (T-09-04-01) is handled by passing goal_statement as a JSON string value — not interpolated into shell commands. This was verified by reviewing the output schema definition which uses typed JSON fields only.

## Self-Check: PASSED

- skills/brainstorm-specialist/SKILL.md — EXISTS (created in commit 2534514)
- workshop/stage_policy.py brainstorm entry — VERIFIED (import test passed)
- requirements-specialist "prior clarifications" — VERIFIED (grep count = 1)
- Commit 358c7e0 — VERIFIED (git log confirms)
- Commit 2534514 — VERIFIED (git log confirms)
- Test suite: 121 passed, 2 skipped — NO REGRESSIONS
