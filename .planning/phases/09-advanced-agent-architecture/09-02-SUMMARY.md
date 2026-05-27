---
phase: "09-advanced-agent-architecture"
plan: "09-02"
subsystem: "review-wave"
tags: [worktree, soul-files, isolation-policy, review-wave, git-worktree]
dependency_graph:
  requires: []
  provides:
    - workshop/worktree.py (git worktree lifecycle — create/remove/prune)
    - skills/*/SKILL.md (9 reviewer soul files with severity-aware Output Schema)
    - hermes-config/agent-isolation-policy.md (AgentTool/SkillTool policy)
    - tests/phase-09/ (test stubs for worktree + brainstorm HITL + wave dispatch + merge agent)
  affects:
    - hermes-skills/workshop_build.py (09-03 wires these souls into the wave dispatcher)
    - hermes-config/review-roster.yaml (referenced by policy as enforcement control plane)
tech_stack:
  added:
    - workshop/worktree.py (subprocess git worktree, stdlib only — no new deps)
    - 9 SKILL.md soul files under skills/
    - hermes-config/agent-isolation-policy.md (markdown policy doc)
  patterns:
    - AgentTool isolation for judgment-heavy roles (security, correctness, merge-agent)
    - SkillTool shared-context for diagnostic roles (python, typescript, reactjs, qa, docs, config)
    - Severity Literal["Critical","Important","Minor"] in all Output Schemas
    - Dry-run behavior in all soul files (hardcoded JSON example)
key_files:
  created:
    - workshop/worktree.py
    - skills/correctness-reviewer/SKILL.md
    - skills/security-reviewer/SKILL.md
    - skills/python-reviewer/SKILL.md
    - skills/typescript-reviewer/SKILL.md
    - skills/reactjs-reviewer/SKILL.md
    - skills/qa-reviewer/SKILL.md
    - skills/docs-reviewer/SKILL.md
    - skills/config-reviewer/SKILL.md
    - skills/merge-agent/SKILL.md
    - hermes-config/agent-isolation-policy.md
    - tests/phase-09/__init__.py
    - tests/phase-09/test_worktree.py
    - tests/phase-09/test_brainstorm_hitl.py
    - tests/phase-09/test_review_wave.py
    - tests/phase-09/test_merge_agent.py
  modified: []
decisions:
  - "workshop/worktree.py uses subprocess.run(check=True) with git worktree add/remove/list --porcelain; prune_stale_worktrees uses os.stat mtime vs max_age_hours"
  - "merge-agent SKILL.md explicitly prohibits auto-fixing logic/security/APIs per D-13 with NEVER auto-fix section"
  - "9 soul files follow reviewer-specialist SKILL.md format: frontmatter, Discipline, Behavior, Output Schema with severity Literal, Dry-run Behavior"
  - "agent-isolation-policy.md references review-roster.yaml as mechanical control plane per D-07"
  - "test_brainstorm_hitl.py uses pytest.skip (not NotImplementedError) as gate — stubs skip cleanly in CI until 09-03"
metrics:
  duration: "~8 minutes"
  completed: "2026-05-27T23:01:15Z"
  tasks_completed: 3
  tasks_total: 3
  files_created: 16
  files_modified: 0
---

# Phase 09 Plan 02: Soul Files, Worktree Module, and Isolation Policy Summary

**One-liner:** Created 9 reviewer SKILL.md soul files with severity-aware Output Schema, git worktree lifecycle module, and AgentTool/SkillTool isolation policy document for Phase 09 review wave.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wave 0 test stubs + workshop/worktree.py | 5c3322f | workshop/worktree.py, tests/phase-09/ (5 files) |
| 2 | Create 9 reviewer + merge-agent SKILL.md soul files | 90cf071 | 9 SKILL.md files under skills/ |
| 3 | Create hermes-config/agent-isolation-policy.md | 81a3112 | hermes-config/agent-isolation-policy.md |

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

1. `python3 -c "from workshop.worktree import ..."` — PASS
2. All 9 soul files present — PASS
3. `grep -l "Output Schema" skills/*/SKILL.md | wc -l` → 15 (includes pre-existing reviewer-specialist + new 9) — PASS
4. `hermes-config/agent-isolation-policy.md` exists with AgentTool/SkillTool terms — PASS
5. `pytest tests/phase-09/ -q` → 3 passed, 8 skipped — PASS
6. `pytest tests/ --ignore=tests/phase-09/ -x -q` → 97 passed — PASS

## Key Decisions Made

- **worktree.py subprocess pattern:** Uses `subprocess.run(check=True, capture_output=True, text=True)` matching reviewer.py pattern. `prune_stale_worktrees` uses `os.stat` mtime rather than git metadata to avoid extra subprocess calls.
- **Brainstorm HITL stubs:** Used `pytest.skip()` decorator (not `pytest.mark.xfail`) so stubs are clean CI-green skips — they won't become failures if accidentally collected before 09-03 lands.
- **merge-agent Output Schema:** Extended the base reviewer schema with `block_push`, `auto_fixed`, `hitl_summary`, and `sources` fields to support the full D-13/D-15/D-16 merge decision surface.
- **Policy doc scope:** `agent-isolation-policy.md` contains the rationale + role table but explicitly delegates enforcement to `review-roster.yaml` — which does not yet exist (created in 09-01 or 09-03). The policy doc references it by path to keep the contract clear.

## Known Stubs

- `tests/phase-09/test_brainstorm_hitl.py`: 2 tests skip until 09-03 wires the brainstorm stage in workshop_build.py.
- `tests/phase-09/test_review_wave.py`: 3 tests skip until 09-03 implements wave dispatch.
- `tests/phase-09/test_merge_agent.py`: 3 tests skip until 09-03 implements merge agent.

These stubs are intentional — they document the contract for 09-03 without blocking the current wave's CI.

## Threat Surface Scan

No new network endpoints, auth paths, or trust boundaries introduced. `workshop/worktree.py` runs subprocess git commands — the subprocess pattern is already established in `workshop/reviewer.py`. T-09-02-03 (stale worktrees) is mitigated by `prune_stale_worktrees` with `max_age_hours=48` default per the threat model.

## Self-Check: PASSED

Files verified:
- workshop/worktree.py — FOUND
- skills/correctness-reviewer/SKILL.md — FOUND
- skills/security-reviewer/SKILL.md — FOUND
- skills/merge-agent/SKILL.md — FOUND
- hermes-config/agent-isolation-policy.md — FOUND
- tests/phase-09/test_worktree.py — FOUND

Commits verified:
- 5c3322f (Task 1) — FOUND
- 90cf071 (Task 2) — FOUND
- 81a3112 (Task 3) — FOUND
