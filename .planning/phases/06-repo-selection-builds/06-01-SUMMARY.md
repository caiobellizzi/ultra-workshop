---
phase: 06-repo-selection-builds
plan: 06-01
subsystem: pipeline
tags: [telegram, github, repo-registry, hitl, gh-cli]

requires:
  - phase: 04-build-fix-pipeline
    provides: "Background build/fix pipeline, deterministic coder envelope, HITL push/PR flow"
provides:
  - "Active repo registry at /srv/second-brain/_system/workshop-repos.json"
  - "Repo-targeted /build --repo and /fix issue URL validation"
  - "Repo-aware coder clone and PR creation arguments"
affects: [build-fix-pipeline, telegram-skills, github-auth, phase-05]

tech-stack:
  added: []
  patterns:
    - "Exit-code-2 JSON approval envelope for repo mutations"
    - "WORKSHOP_REPO_REGISTRY override for tests"

key-files:
  created:
    - workshop/repo_registry.py
    - hermes-skills/workshop_repo.py
    - skills/workshop-repo/SKILL.md
    - tests/test_repo_registry.py
    - tests/phase-06/repo-smoke.bats
  modified:
    - hermes-skills/workshop_build.py
    - hermes-skills/workshop_fix.py
    - hermes-skills/workshop_coder.py
    - hermes-skills/workshop_push.py
    - skills/workshop-build/SKILL.md
    - skills/workshop-fix/SKILL.md
    - skills/coder-specialist/SKILL.md

key-decisions:
  - "Registry uses canonical owner/name entries with active/inactive status; remove never deletes GitHub repos."
  - "Build dry-run without --repo exits 0 with usage so old smoke paths remain non-destructive."
  - "Live repo mutations require a second --approved invocation after Telegram clarify approval."

patterns-established:
  - "Repo registry helpers raise explicit UnknownRepoError/InactiveRepoError with /repo add hints."
  - "Pipeline scripts pass repo metadata in the specialist query payload instead of relying on hardcoded sandbox constants."

requirements-completed: [REQ-ws-029]

duration: 1h
completed: 2026-05-24
---

# Phase 6 Plan 01 Summary

**Telegram repo registry with active-repo validation, repo-targeted build/fix payloads, and selected-repo PR creation**

## Performance

- **Duration:** ~1h
- **Started:** 2026-05-24T00:00:00-03:00
- **Completed:** 2026-05-24T00:00:00-03:00
- **Tasks:** 6
- **Files modified:** 12

## Accomplishments

- Added `workshop.repo_registry` for canonical repo names, atomic JSON registry writes, bootstrap seeding, active/inactive validation, GitHub metadata mapping, and issue URL repo parsing.
- Added `workshop_repo.py` plus `skills/workshop-repo/SKILL.md` for `/repo list/add/create/remove`, with exit-code-2 approval envelopes before add/create/remove mutate registry or GitHub state.
- Updated `/build`, `/fix`, coder, and push scripts so repo metadata flows from command parsing through clone, HITL payload, and `gh pr create --repo ... --base ...`.
- Added focused unit tests and Phase 6 dry-run smoke coverage.

## Task Commits

1. **Tasks 1-6: Repo registry, command backend, pipeline threading, tests** - `70b899f` (`feat(06-01): add repo registry targeting`)

## Files Created/Modified

- `workshop/repo_registry.py` - Registry data model, canonicalization, validation, GitHub metadata conversion, active repo lookup, and issue URL parsing.
- `hermes-skills/workshop_repo.py` - `/repo` command backend with approval envelopes and approved mutation paths.
- `skills/workshop-repo/SKILL.md` - Hermes wrapper instructions for list/add/create/remove.
- `hermes-skills/workshop_build.py` - Requires and validates `--repo`, threads repo metadata through the pipeline, and includes repo/base in HITL payload.
- `hermes-skills/workshop_fix.py` - Derives repo and issue number from GitHub issue URLs, validates active repo, and delegates to build with `--repo`.
- `hermes-skills/workshop_coder.py` - Clones selected repos with `gh repo clone` and emits repo metadata in the Diff envelope.
- `hermes-skills/workshop_push.py` - Accepts `--repo-full-name` and `--base`, and writes repo/base into ADR frontmatter.
- `skills/workshop-build/SKILL.md`, `skills/workshop-fix/SKILL.md`, `skills/coder-specialist/SKILL.md` - Updated operational docs for repo-aware flow.
- `tests/test_repo_registry.py` - Unit tests for registry behavior.
- `tests/phase-06/repo-smoke.bats` - VPS dry-run smoke coverage for repo-aware commands.

## Decisions Made

- Kept registry storage as a single JSON file at `/srv/second-brain/_system/workshop-repos.json`, with `WORKSHOP_REPO_REGISTRY` override for tests.
- Used exit code 2 for repo mutation approval, matching the existing build HITL contract.
- Kept `/build --dry-run` without `--repo` as a non-error usage path so dry smoke tests remain harmless while real builds still require `--repo`.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Full VPS smoke tests and live acceptance were not run in this turn. The code is locally verified, but the new files still need to be deployed to `/opt/ultra-workshop` and `/home/uws/.hermes/skills` before `tests/phase-06/repo-smoke.bats` can pass against the VPS.
- Live acceptance still needs a human Telegram approval path for `/repo create`, one real `/build --repo uws-smoke-<date> ...`, and PR confirmation against the smoke repo.

## Verification

- `python3 -m compileall workshop/repo_registry.py hermes-skills/workshop_repo.py hermes-skills/workshop_build.py hermes-skills/workshop_fix.py hermes-skills/workshop_coder.py hermes-skills/workshop_push.py` - PASS
- `python3 -m pytest tests/test_repo_registry.py tests/phase-04/test_orchestrator.py tests/phase-04/test_extract_json.py` - PASS, 31 tests
- `WORKSHOP_REPO_REGISTRY=/private/tmp/uws-repos-build-repo.json python3 hermes-skills/workshop_build.py --repo test-workshop-sandbox --dry-run --task 'add hello endpoint'` - PASS
- `WORKSHOP_REPO_REGISTRY=/private/tmp/uws-repos-fix.json python3 hermes-skills/workshop_fix.py --issue-url 'https://github.com/caiobellizzi/test-workshop-sandbox/issues/1' --dry-run` - PASS
- `python3 hermes-skills/workshop_coder.py --query '{"task_id":"smoke","plan":{"goal":"noop"},"repo":{"full_name":"caiobellizzi/test-workshop-sandbox","default_branch":"main"},"workspace_dir":""}' --dry-run` - PASS
- `python3 hermes-skills/workshop_repo.py add demo` - PASS, exits 2 with approval envelope
- `bats --count tests/phase-06/repo-smoke.bats` - PASS, 5 tests discovered
- `git diff --check` - PASS

## User Setup Required

- Deploy updated `workshop/`, `hermes-skills/`, and `skills/` files to the VPS before running Phase 6 smoke tests.
- Expand or replace `GITHUB_PAT` on the VPS so it has minimum permissions for active registry repos: view, clone, branch push, PR creation, and private repo creation.
- Run the live Telegram acceptance sequence from `06-01-PLAN.md` when ready.

## Next Phase Readiness

Phase 6 code is locally ready for VPS deployment and live acceptance. Phase 5 remains not started in roadmap order.

---
*Phase: 06-repo-selection-builds*
*Completed: 2026-05-24*
