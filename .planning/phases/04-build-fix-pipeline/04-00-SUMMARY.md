---
phase: 04-build-fix-pipeline
plan: "00"
subsystem: infra
tags: [github, gh-cli, pat, vps, hermes, probe]

requires:
  - phase: 03-skill-toolkit
    provides: "Hermes deployed on VPS with uws service account and /etc/uws/env"

provides:
  - "gh CLI installed on VPS (v2.45.0, apt-managed)"
  - "GITHUB_PAT injected into /etc/uws/env (fine-grained, scoped to test-workshop-sandbox)"
  - "gh CLI authenticated as uws (caiobellizzi account)"
  - "caiobellizzi/test-workshop-sandbox repo exists and is accessible"
  - "Hermes delegate_task probe result: NOT_SUPPORTED in current VPS config (informational)"
  - "Architecture B confirmed: standalone Python subprocess per specialist (no Hermes imports)"

affects:
  - 04-build-fix-pipeline/04-01
  - 04-build-fix-pipeline/04-02
  - 04-build-fix-pipeline/04-03

tech-stack:
  added:
    - "gh CLI 2.45.0 (apt: ubuntu noble-security/universe)"
    - "GitHub fine-grained PAT (github_pat_ format, scoped to test-workshop-sandbox)"
  patterns:
    - "GITHUB_PAT in /etc/uws/env; uws user reads via environment injection"
    - "gh CLI invoked via: sudo -u uws gh <cmd>"
    - "Architecture B: workshop_build.py / workshop_fix.py = standalone Python, no Hermes imports"

key-files:
  created:
    - ".planning/phases/04-build-fix-pipeline/04-00-probe-results.md"
  modified: []

key-decisions:
  - "Architecture B is FINAL: standalone Python subprocess per specialist (not delegate_task)"
  - "Fine-grained PAT uses github_pat_ prefix (not legacy ghp_ prefix) — probe-results verify updated"
  - "Hermes delegate_task NOT_SUPPORTED in current VPS config (no_db_connection); Wave 1 unaffected"

patterns-established:
  - "VPS GitHub auth: GITHUB_PAT in /etc/uws/env, gh auth via sudo -u uws"
  - "Wave 0 is a one-time infra provisioning plan; Wave 1+ are pure Python with no Wave 0 dependency"

requirements-completed:
  - REQ-ws-007
  - REQ-ws-008
  - REQ-ws-010

duration: ~20min (including human checkpoint for PAT injection)
completed: "2026-05-22"
---

# Phase 4 Plan 00: Wave 0 Infra Probe Summary

**gh CLI installed on VPS, GITHUB_PAT injected as fine-grained token, uws authenticated to github.com/caiobellizzi, and test-workshop-sandbox repo confirmed accessible — Wave 0 prerequisites READY**

## Performance

- **Duration:** ~20 min total (including human checkpoint for PAT injection)
- **Started:** 2026-05-21T23:50:00Z (Task 1 — gh CLI install)
- **Completed:** 2026-05-22T01:48:27Z (Task 3 — verification)
- **Tasks:** 3 (Task 1 auto, Task 2 human-action checkpoint, Task 3 auto)
- **Files modified:** 1

## Accomplishments

- gh CLI v2.45.0 installed on VPS via apt (ubuntu noble-security/universe)
- GITHUB_PAT (fine-grained, github_pat_ format) injected into /etc/uws/env and authenticated via `gh auth login --with-token` as uws
- caiobellizzi/test-workshop-sandbox GitHub repo verified accessible (defaultBranch=main)
- Hermes delegate_task probe result recorded: NOT_SUPPORTED due to no_db_connection in standalone CLI invocation — Architecture B (subprocess per specialist) is confirmed as the correct decision
- All Wave 0 git/PR prerequisites marked READY in probe-results.md

## Task Commits

Each task was committed atomically:

1. **Task 1: Install gh CLI and write probe results** - `21e7e2b` (feat)
2. **Task 2: GITHUB_PAT injection** - human-completed (no code commit — VPS-only action)
3. **Task 3: Verify PAT end-to-end and finalize probe results** - `a8a7650` (feat)

## Files Created/Modified

- `.planning/phases/04-build-fix-pipeline/04-00-probe-results.md` — Probe results with Architecture Decision, Q1 (Hermes delegate_task), Q3 (gh CLI), test-workshop-sandbox status, and Final Status (READY)

## Decisions Made

- **Architecture B is FINAL**: standalone Python subprocess per specialist (workshop_build.py / workshop_fix.py have no Hermes imports). The Hermes delegate_task probe returned NOT_SUPPORTED (no_db_connection error in standalone CLI context). Wave 1 proceeds as planned.
- **Fine-grained PAT uses github_pat_ prefix**: the plan's verify step checked for `ghp_` prefix (legacy PATs) but GitHub fine-grained tokens use `github_pat_` prefix. Verification adapted to check for `GITHUB_PAT=` (prefix-agnostic). Probe-results.md documents both the format and the 1-line count.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Verify 2 pattern adapted for fine-grained PAT format**
- **Found during:** Task 3 (Verify PAT end-to-end)
- **Issue:** Plan's verify step: `grep -c 'GITHUB_PAT=ghp_' /etc/uws/env` returned 0 because fine-grained tokens use `github_pat_` prefix, not `ghp_`. The PAT was correctly injected but the grep pattern didn't match.
- **Fix:** Re-ran grep as `grep -c 'GITHUB_PAT=' /etc/uws/env` (prefix-agnostic) — returned 1. Documented the fine-grained token format in probe-results.md. Final Status correctly reflects YES for GITHUB_PAT injected.
- **Files modified:** .planning/phases/04-build-fix-pipeline/04-00-probe-results.md
- **Verification:** `grep -c 'GITHUB_PAT=' /etc/uws/env` = 1; `sudo -u uws gh auth status` shows caiobellizzi
- **Committed in:** a8a7650 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — verification pattern bug)
**Impact on plan:** No scope creep. The PAT was correctly injected by the human; only the verification grep pattern needed adaptation.

## Issues Encountered

- Hermes delegate_task probe returned `Error: Error code: 400 - {'error': {'message': 'No connected db.', 'type': 'no_db_connection'}}` — expected, as standalone CLI invocations do not have access to the LiteLLM private-worker database. This is informational only and does not affect Wave 1 (Architecture B decided prior to probe).

## User Setup Required

None — human PAT injection was the only manual step and is complete.

## Next Phase Readiness

- Wave 0 prerequisites: READY
- Wave 1 (04-01: types/orchestrator/specialist skills) can proceed — it is pure Python with no Wave 0 dependency
- Wave 2 (04-02: workshop-build/workshop-fix skills) requires gh CLI + PAT — now READY
- Wave 3 (04-03: end-to-end tests + HITL gate) requires gh CLI + PAT + test-workshop-sandbox — now READY

---
*Phase: 04-build-fix-pipeline*
*Completed: 2026-05-22*
