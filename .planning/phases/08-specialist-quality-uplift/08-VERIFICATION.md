---
phase: "08-specialist-quality-uplift"
verified: "2026-05-26"
status: "pass_with_caveats"
---

# Phase 08 Verification

## Automated

- `python3 -m py_compile hermes-skills/aider_runner.py hermes-skills/workshop_coder.py hermes-skills/workshop_reviewer.py hermes-skills/workshop_planner.py hermes-skills/workshop_build.py hermes-skills/workshop_continue.py hermes-skills/workshop_push.py workshop/types.py workshop/reviewer.py workshop/state.py workshop/doc_resolver.py workshop/ledger.py workshop/stage_policy.py` — pass.
- `python3 -m pytest tests/phase-08/test_quality_uplift.py tests/phase-06/test_aider_runner.py tests/phase-06/test_workshop_coder.py tests/phase-06/test_workshop_reviewer.py tests/phase-04/test_reviewer.py tests/phase-04/test_workshop_build.py tests/phase-04/test_orchestrator.py tests/phase-07/test_workspace.py tests/phase-07/test_doc_resolver.py tests/phase-06/test_cli_file_args.py` — 45 passed.
- `bats tests/phase-04/ tests/phase-07/planner-smoke.bats` — 14 passed.

## Deployed VPS

- Deployed runtime and SKILL.md files to `/opt/ultra-workshop`.
- Deployed SKILL.md files to `/home/uws/.hermes/skills`.
- Restarted `uws-hermes`; `systemctl is-active uws-hermes` returned `active`.
- Hermes venv py_compile passed for changed runtime files.
- Deployed smoke: `bats tests/phase-04/build-smoke.bats tests/phase-04/model-matrix-smoke.bats tests/phase-07/planner-smoke.bats` — 11 passed.
- Deployed coder/repo smoke: `bats tests/phase-04/coder-smoke.bats tests/phase-06/repo-smoke.bats` — 6 passed.

## Live E2E Caveat

The live `/build` smoke for `ws-smoke-p7-0526a` verified the Phase 7 SC-4 planner requirement: the LLM planner produced workspace-relative `affected_files`:

- `openharness_orchestration.py`
- `tests/test_openharness_orchestration.py`
- `README.md`

The same smoke did not reach reviewer because coder/aider timed out at 900s and correctly entered `needs_timeout_recovery`. Treat reviewer/approval live confirmation as a remaining acceptance item, not a local implementation failure.
