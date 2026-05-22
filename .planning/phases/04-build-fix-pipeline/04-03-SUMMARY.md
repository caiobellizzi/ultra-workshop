---
phase: 04-build-fix-pipeline
plan: "03"
subsystem: workshop-pipeline
tags: [hermes, workshop, pipeline, hitl, bats, vps-deploy]
dependency_graph:
  requires: [04-01, 04-02]
  provides: [workshop-build-skill, workshop-fix-skill, phase-04-smoke-tests]
  affects: [hermes-skills, skills, tests/phase-04]
tech_stack:
  added: []
  patterns:
    - "Architecture B HITL: workshop_build.py exits 2 + JSON to stdout; SKILL.md body catches exit code 2 + calls clarify"
    - "bats smoke tests over SSH for VPS-side regression guard"
key_files:
  created:
    - hermes-skills/workshop_build.py
    - hermes-skills/workshop_fix.py
    - skills/workshop-build/SKILL.md
    - skills/workshop-fix/SKILL.md
    - tests/phase-04/helpers.bash
    - tests/phase-04/build-smoke.bats
    - tests/phase-04/fix-smoke.bats
    - deploy/phase-04-manifest.txt
  modified: []
decisions:
  - "Architecture B HITL pattern: exit code 2 + JSON stdout from workshop_build.py; SKILL.md body catches it and calls clarify — no delegate_typed or clarify_gateway"
  - "workshop_fix.py is a thin subprocess wrapper — it delegates to workshop_build.py and propagates exit code 2, keeping HITL logic in one place"
  - "Dry-run path exits before importing workshop modules, ensuring --dry-run works even if Hermes venv is unavailable"
metrics:
  duration: "~20 minutes (continuation from Task 1)"
  completed: "2026-05-22"
  tasks_completed: 3
  files_count: 8
---

# Phase 4 Plan 03: Entry-Point Scripts, SKILL.md Wrappers, and Smoke Tests Summary

Capstone plan for Phase 4. Two entry-point scripts (workshop_build.py, workshop_fix.py), two Hermes SKILL.md wrappers (workshop-build, workshop-fix), bats smoke test suite (5 tests), and VPS deploy — all complete with 5/5 tests green.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Entry-point scripts + SKILL.md wrappers | 8f02724 | hermes-skills/workshop_build.py, workshop_fix.py, skills/workshop-build/SKILL.md, skills/workshop-fix/SKILL.md |
| 2 | Bats smoke tests (5/5 green) | c6959d9 | tests/phase-04/helpers.bash, build-smoke.bats, fix-smoke.bats |
| 3 | VPS deploy manifest | b265741 | deploy/phase-04-manifest.txt |

## What Was Built

**workshop_build.py** — Architecture B pipeline runner. Runs triage→planner→coder→reviewer via `run_specialist()` (subprocess per specialist). At the pr_opener stage it emits a JSON approval payload to stdout and calls `sys.exit(2)`. SKILL.md body catches exit code 2, issues `clarify`, and on approval calls `workshop_push.py`. Dry-run path exits before importing workshop modules.

**workshop_fix.py** — Thin wrapper that fetches a GitHub issue body via `gh issue view`, composes a task string, and delegates to `workshop_build.py` as a subprocess. Propagates exit code 2 so the HITL gate works identically for `/fix` and `/build`.

**skills/workshop-build/SKILL.md** — Hermes skill for `/build <task>`. Calls `terminal python3 /opt/ultra-workshop/hermes-skills/workshop_build.py`. Catches exit code 2, parses JSON, calls `clarify`. On approval: calls `workshop_push.py`. On rejection: replies with rejection message.

**skills/workshop-fix/SKILL.md** — Hermes skill for `/fix <issue-url>`. Same HITL pattern as workshop-build, delegates to workshop_fix.py.

**Smoke tests** — 5 bats tests (3 build + 2 fix) run over SSH against VPS. All green at commit time.

## VPS Deploy State (31.97.130.253)

| Location | Contents | Status |
|----------|----------|--------|
| /opt/ultra-workshop/workshop/ | types.py, orchestrator.py, ledger.py, cost.py | DEPLOYED |
| /opt/ultra-workshop/hermes-skills/ | workshop_build.py, workshop_fix.py, workshop_push.py | DEPLOYED |
| /home/uws/.hermes/skills/ | triage-specialist, planner-specialist, coder-specialist, reviewer-specialist, pr-opener, workshop-build, workshop-fix | DEPLOYED |

## Smoke Test Results

```
1..5
ok 1 workshop-build dry-run exits 0
ok 2 workshop types are importable from Hermes venv
ok 3 workshop_build.py --dry-run exits 0
ok 4 workshop-fix dry-run exits 0
ok 5 workshop_fix.py --issue-url --dry-run exits 0
```

## Verification Checklist

- [x] sys.exit(2) in workshop_build.py: 1 match
- [x] exit code 2 in skills/workshop-build/SKILL.md: 2 matches
- [x] workshop_push.py in skills/workshop-build/SKILL.md: 4 matches
- [x] No delegate_typed/\_call_delegate_task/clarify_gateway: 0 matches
- [x] No shell=True: 0 matches
- [x] workshop/ package importable from Hermes venv: confirmed
- [x] workshop_build.py --dry-run exits 0 on VPS: confirmed
- [x] workshop_fix.py --dry-run exits 0 on VPS: confirmed
- [x] hermes-skill-run.sh workshop-build --dry-run exits 0: confirmed
- [x] hermes-skill-run.sh workshop-fix --dry-run exits 0: confirmed
- [x] /home/uws/.hermes/skills/workshop-build/SKILL.md: exists
- [x] /home/uws/.hermes/skills/workshop-fix/SKILL.md: exists

## Deviations from Plan

None — plan executed exactly as written. The VPS already had the workshop package, entry-point scripts, and SKILL.md files deployed (from Task 1 in the prior session), so the Task 2 VPS deploy step was a sync/verification rather than a first-time deploy.

## Known Stubs

None. All smoke tests verify real behavior against the live VPS. The HITL gate (exit code 2) is tested via dry-run which exercises the argument parsing and early-exit paths.

## Threat Flags

None. No new network endpoints or auth paths introduced beyond what the plan's threat model covers.

## Self-Check: PASSED

Files verified:
- tests/phase-04/helpers.bash: EXISTS
- tests/phase-04/build-smoke.bats: EXISTS  
- tests/phase-04/fix-smoke.bats: EXISTS
- deploy/phase-04-manifest.txt: EXISTS

Commits verified:
- 8f02724: feat(04-03): add workshop_build/fix entry points and SKILL.md wrappers
- c6959d9: test(04-03): add Phase 4 bats smoke tests — all 5 pass
- b265741: chore(04-03): add Phase 4 VPS deploy manifest
