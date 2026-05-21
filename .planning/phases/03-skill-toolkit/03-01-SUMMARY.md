---
phase: 03-skill-toolkit
plan: "01"
subsystem: infra
tags: [bats, aider, hermes, vps, ssh, pytest]

# Dependency graph
requires:
  - phase: 02-hermes-deploy
    provides: Hermes v0.14.0 running on VPS with uws user and venv at /opt/ultra-workshop/hermes/
provides:
  - scripts/hermes-skill-run.sh — bash wrapper translating skill invocations to `hermes chat --skills` (no native `hermes skill run` subcommand)
  - /opt/ultra-workshop/scripts/ directory on VPS with hermes-skill-run.sh deployed +x
  - bats 1.10.0 on VPS PATH (apt-get install)
  - aider-chat 0.86.2 importable in Hermes venv (pip install via ensurepip bootstrap)
  - tests/phase-03/helpers.bash with ssh_cmd() and VPS_HOST=31.97.130.253
  - tests/phase-03/scaffold.bats — 2 smoke tests validating wrapper on VPS
  - hermes-skills/test_skill_frontmatter.py — pytest validator for skills/*/SKILL.md frontmatter
  - pyproject.toml with testpaths = hermes-skills + scripts
affects: [03-02, 03-03, 03-04, 03-05]

# Tech tracking
tech-stack:
  added: [bats-1.10.0, aider-chat-0.86.2]
  patterns: [hermes-skill-run.sh --dry-run guard, ssh_cmd() helper pattern, pytest parametrize over skills glob]

key-files:
  created:
    - scripts/hermes-skill-run.sh
    - tests/phase-03/helpers.bash
    - tests/phase-03/scaffold.bats
    - hermes-skills/test_skill_frontmatter.py
    - pyproject.toml
    - .gitignore
  modified: []

key-decisions:
  - "hermes-skill-run.sh uses exec sudo -u uws for production path (no shell injection; positional args)"
  - "aider-chat installed via ensurepip bootstrap in Hermes venv (pip not pre-installed)"
  - "bats installed system-wide via apt-get (not venv-local)"
  - "pyproject.toml testpaths covers hermes-skills + scripts only (not tests/ — bats, not pytest)"

patterns-established:
  - "hermes-skill-run.sh --dry-run: echo command that would run + exit 0 (no hermes invocation)"
  - "ssh_cmd() in helpers.bash: reusable VPS exec wrapper for all Phase 3 bats tests"
  - "test_skill_frontmatter.py: parametrize over Path.glob to auto-discover skills"

requirements-completed: []

# Metrics
duration: 15min
completed: 2026-05-21
---

# Phase 3 Plan 01: VPS Prerequisites + Test Infrastructure Summary

**hermes-skill-run.sh wrapper + bats/aider-chat on VPS + pytest test infrastructure ready for Wave 1 skill porting**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-21T16:00:00Z
- **Completed:** 2026-05-21T16:15:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- VPS /opt/ultra-workshop/scripts/ created; hermes-skill-run.sh deployed +x
- bats 1.10.0 installed system-wide on VPS; aider-chat 0.86.2 importable in Hermes venv
- Phase 3 test infrastructure built: ssh_cmd() helper, scaffold.bats (2 tests), test_skill_frontmatter.py (parametrized), pyproject.toml

## Task Commits

Each task was committed atomically:

1. **Task 1+2: VPS prerequisites + hermes-skill-run.sh** - `2c750a6` (feat)
2. **Task 3: Test infrastructure scaffolding** - `9f8c1aa` (feat)

## Files Created/Modified
- `scripts/hermes-skill-run.sh` - Bash wrapper: `hermes chat --skills <name> --query <q> -Q --max-turns 3 --yolo` with --dry-run guard
- `tests/phase-03/helpers.bash` - ssh_cmd() with VPS_HOST=31.97.130.253
- `tests/phase-03/scaffold.bats` - 2 smoke tests: dry-run exit 0, hermes --version as uws
- `hermes-skills/test_skill_frontmatter.py` - pytest parametrized: required fields + name==dirname
- `pyproject.toml` - testpaths: hermes-skills, scripts
- `.gitignore` - __pycache__, *.pyc, .pytest_cache

## Decisions Made
- Installed aider-chat via `python3 -m ensurepip` bootstrap then pip install (pip not pre-installed in venv)
- Used `exec sudo -u uws` in production path of hermes-skill-run.sh (replaces shell process, prevents injection)
- bats installed system-wide (apt-get) not in venv — bats is a shell testing framework

## Deviations from Plan
None — plan executed as specified. The ensurepip bootstrap was anticipated in the research (VPS had no pip in venv).

## Issues Encountered
None significant. aider-chat install required ensurepip bootstrap as noted in RESEARCH.md Q6.

## User Setup Required
None — all VPS changes made via SSH during execution.

## Next Phase Readiness
- Wave 1 (03-02, 03-03) can run in parallel: audit script + skill porting both depend only on this plan
- hermes-skill-run.sh --dry-run verified locally and deployed on VPS
- bats + aider-chat confirmed importable on VPS
- Test infrastructure (helpers.bash, scaffold.bats) ready for skill smoke tests

---
*Phase: 03-skill-toolkit*
*Completed: 2026-05-21*
