---
phase: "04-build-fix-pipeline"
plan: "04-07"
status: completed
completed_at: 2026-05-25
---

# Plan 04-07 - HITL-first ambiguity handling for workshop agents - SUMMARY

## What changed

Added a first-class clarification path to the deterministic workshop pipeline so ambiguous product intent no longer gets silently resolved by planner, coder, or reviewer.

The core behavior change is:

- `requirements-specialist` now runs before planner and emits either a ready decision or a typed clarification request.
- `run_specialist()` now recognizes clarification control JSON and raises a typed exception instead of trying to validate it as a normal schema.
- `workshop_build.py` now preserves `task_id` across clarification resumes, accepts `--clarifications-file`, and emits distinct HITL payloads for `clarification` vs `approval`.
- `workshop_coder.py` no longer hardcodes OpenHarness/12-factor assumptions and escalates no-diff or ambiguity-shaped runs as clarification requests.
- `workshop/reviewer.py` no longer contains HKUDS/OpenHarness-specific semantic checks; it keeps generic safety checks and can escalate ambiguity as clarification.

## Files changed

| File | Change |
|------|--------|
| `workshop/types.py` | Added `ClarificationQuestion` and `ClarificationRequest` models. |
| `workshop/orchestrator.py` | Added `ClarificationNeeded` and pre-schema clarification routing in `run_specialist()`. |
| `workshop/requirements_gate.py` | New deterministic requirements gate plus clarification normalization/context helpers. |
| `hermes-skills/workshop_requirements.py` | New deterministic CLI wrapper for requirements-stage execution. |
| `scripts/hermes-skill-run.sh` | Routed `requirements-specialist` through deterministic Python execution and dry-run support. |
| `hermes-skills/workshop_build.py` | Added requirements stage, same-task resume flags, clarification file loading, and distinct HITL payload types. |
| `hermes-skills/workshop_coder.py` | Removed task-specific domain assumptions; added clarification escalation for no-diff/ambiguity output. |
| `workshop/reviewer.py` | Removed hardcoded OpenHarness semantics; added clarification escalation for ambiguous review conditions. |
| `skills/requirements-specialist/SKILL.md` | Added skill contract for requirements-stage clarification handling. |
| `skills/workshop-build/SKILL.md` | Documented clarification-resume flow alongside the existing approval gate. |
| `tests/phase-04/test_orchestrator.py` | Added clarification-routing coverage. |
| `tests/phase-04/test_workshop_build.py` | Added same-task clarification payload/resume coverage. |
| `tests/phase-04/test_reviewer.py` | Added reviewer clarification vs defect coverage. |
| `tests/phase-06/test_workshop_coder.py` | Updated coder tests to match generic, non-hardcoded behavior. |
| `tests/phase-06/test_workshop_reviewer.py` | Updated reviewer tests to match generic clarification behavior. |

## Verification

- `python3 -m pytest tests/phase-04 -q` -> **38 passed**
- `python3 -m pytest tests/phase-06/test_aider_runner.py tests/phase-06/test_cli_file_args.py tests/phase-06/test_workshop_coder.py tests/phase-06/test_workshop_reviewer.py -q` -> **10 passed**
- `python3 hermes-skills/workshop_requirements.py --dry-run` -> emitted valid ready JSON
- `bash scripts/hermes-skill-run.sh requirements-specialist --dry-run --query '{"task_id":"ws-test","goal":"use the best 12 factory practices"}'` -> resolved deterministic requirements path

## Notes

- The Telegram skill wrapper now documents the clarification resume path, but live Telegram/Hermes UX for multi-question free-text clarification still needs end-to-end acceptance on the VPS.
- This plan closes the imported Phase 4 follow-up and returns roadmap focus to Phase 5.
