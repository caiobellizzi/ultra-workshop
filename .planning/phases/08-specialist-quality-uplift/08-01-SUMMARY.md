---
phase: "08-specialist-quality-uplift"
plan: "08-01"
status: "completed_with_caveats"
completed: "2026-05-26"
key_files:
  created:
    - tests/phase-08/test_quality_uplift.py
  modified:
    - hermes-skills/aider_runner.py
    - hermes-skills/workshop_build.py
    - hermes-skills/workshop_coder.py
    - hermes-skills/workshop_continue.py
    - hermes-skills/workshop_planner.py
    - hermes-skills/workshop_push.py
    - scripts/hermes-skill-run.sh
    - skills/triage-specialist/SKILL.md
    - skills/requirements-specialist/SKILL.md
    - skills/planner-specialist/SKILL.md
    - skills/coder-specialist/SKILL.md
    - skills/reviewer-specialist/SKILL.md
    - skills/workshop-build/SKILL.md
    - skills/workshop-fix/SKILL.md
    - workshop/doc_resolver.py
    - workshop/ledger.py
    - workshop/reviewer.py
    - workshop/stage_policy.py
    - workshop/state.py
    - workshop/types.py
    - deploy/phase-04-manifest.txt
---

# 08-01 Summary

Implemented the Specialist Quality Uplift in place.

## Delivered

- Added lean/behavioral discipline sections to the five specialist SKILL.md files.
- Added Diff verification fields: `build_passed`, `test_passed`, `output_tail`.
- Added repo verification command detection/execution in `aider_runner.py`.
- Added structured review failures as `{file, problem, required_fix}` objects.
- Added reviewer pass-1 build/test gate before static checks.
- Added review retry exhaustion HITL payload and continuation handling.
- Added planner and reviewer Brain read hooks for repo conventions, ADRs, and review rules.
- Fixed workshop-fix documentation to use `workshop_continue.py` and include requirements stage.
- Preserved Phase 7 security fixes: task_id validation, confined doc reads, ADR frontmatter escaping, resume re-clone, GH token checks, and dry-run quoting.

## Verification

- `python3 -m pytest tests/phase-08/test_quality_uplift.py tests/phase-06/test_aider_runner.py tests/phase-06/test_workshop_coder.py tests/phase-06/test_workshop_reviewer.py tests/phase-04/test_reviewer.py tests/phase-04/test_workshop_build.py tests/phase-04/test_orchestrator.py tests/phase-07/test_workspace.py tests/phase-07/test_doc_resolver.py tests/phase-06/test_cli_file_args.py` — 45 passed.
- `bats tests/phase-04/ tests/phase-07/planner-smoke.bats` — 14 passed.
- Deployed changed runtime and SKILL.md files to the VPS, restarted `uws-hermes`, confirmed service active, py_compile passed under Hermes venv, deployed dry/import smoke passed 11/11, and coder/repo smoke passed 6/6.

## Caveats

- Phase 7 live `/build` smoke verified SC-4 planner behavior: the LLM planner emitted workspace-relative `affected_files` for `openharness_orchestration.py`, `tests/test_openharness_orchestration.py`, and `README.md`.
- The same live smoke did not reach reviewer because coder/aider timed out at the configured 900s and correctly entered `needs_timeout_recovery`.
- No root `README.md` exists in this repository, so the deployment note was recorded in `deploy/phase-04-manifest.txt` instead of updating a nonexistent README.
