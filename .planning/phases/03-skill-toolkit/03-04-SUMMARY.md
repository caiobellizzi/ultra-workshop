---
phase: 03-skill-toolkit
plan: "04"
subsystem: brain-skills
tags: [brain, httpx, hermes, skills, vault, form-data, V4-relaxation]
dependency_graph:
  requires: [03-01, 03-03]
  provides: [brain_http.py, brain-query-skill, brain-ingest-skill, brain-research-skill, brain-smoke-bats]
  affects: [hermes-skills/, skills/, tests/phase-03/]
tech_stack:
  added: []
  patterns:
    - synchronous httpx.post with multipart/form-data (data={}) for Brain Agno API
    - V4 relaxation: status:ERROR surfaced to stderr without sys.exit(1) — run_id always emitted
    - Brain skill body delegates to python3 brain_http.py via terminal tool
    - brain-smoke.bats: skip_if_brain_down guard for graceful skip on Brain outage
key_files:
  created:
    - hermes-skills/brain_http.py
    - skills/brain-query/SKILL.md
    - skills/brain-ingest/SKILL.md
    - skills/brain-research/SKILL.md
    - tests/phase-03/brain-smoke.bats
  modified: []
decisions:
  - "V4 relaxation: brain_http.py does not sys.exit(1) on status:ERROR — Brain returns HTTP 200 with run_id even when Groq structured-output conflict triggers an application-level error"
  - "brain-query/SKILL.md documents FOLLOW-UP BACKLOG for citation-grounded answer assertion once Groq structured-output issue is resolved"
  - "brain-ingest/SKILL.md includes HITL warning: Brain-side approval required before vault write commits"
  - "Smoke test skip guard uses curl health check to detect Brain outage and skip live test gracefully"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-21"
  tasks_completed: 2
  files_created: 5
  files_modified: 0
requirements_satisfied: [REQ-ws-005]
---

# Phase 3 Plan 04: Brain-Bridge Skills Summary

Synchronous httpx helper + 3 brain-bridge Hermes skills + bats smoke tests for Brain Agno API integration via multipart/form-data.

## What Was Built

### hermes-skills/brain_http.py

Synchronous HTTP helper that POSTs to Brain's `/agents/{id}/runs` endpoint using `data={}` (multipart/form-data), NOT `json={}`. Brain's Agno 2.6.7 API returns 422 on JSON Content-Type; form-data is required.

Key design decisions:
- `call_agent(agent_id, message, user_id)` — single function, synchronous, no asyncio
- `status:ERROR` prints to stderr but does NOT exit 1 (V4 relaxation — Brain returns run_id correctly even on application error)
- CLI entrypoint: `python3 brain_http.py <agent_id> <message>` outputs JSON with `{run_id, content, status}`
- httpx 0.28.1 was already present in Hermes venv — no install needed

### skills/brain-query/SKILL.md

Hermes skill wrapping `brain_http.py query`. Includes:
- V4 Acceptance Note explaining the Groq structured-output conflict
- FOLLOW-UP BACKLOG section tracking the deferred citation-grounded assertion
- Dry-run behavior section

### skills/brain-ingest/SKILL.md

Hermes skill wrapping `brain_http.py ingest`. Includes:
- HITL Warning: Brain's ingest agent requires human approval before vault write commits
- Dry-run behavior section

### skills/brain-research/SKILL.md

Hermes skill wrapping `brain_http.py research`. Includes:
- Multi-step synthesis delegation pattern
- Dry-run behavior section

### tests/phase-03/brain-smoke.bats

4 bats tests:
- 3 dry-run tests (brain-query, brain-ingest, brain-research) — all pass
- 1 HTTP live test with `skip_if_brain_down` guard — passes when Brain is up, skips gracefully if down

## Verification Results

| Check | Result |
|-------|--------|
| `bats tests/phase-03/brain-smoke.bats` | 4/4 pass |
| VPS: `brain_http.py query 'ping'` returns `run_id` in JSON | ok |
| `grep "data={\"message\""` in brain_http.py | match found |
| No `json=` keyword args in actual code (AST verified) | ok |
| `grep "FOLLOW-UP BACKLOG"` in brain-query/SKILL.md | match found |
| `pytest hermes-skills/test_skill_frontmatter.py` | 26/26 pass |
| VPS: `ls /home/uws/.hermes/skills/ | grep -c brain` | 3 |
| httpx version on VPS | 0.28.1 (unchanged) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] V4 relaxation: sys.exit(1) on status:ERROR prevented run_id output**

- **Found during:** Task 1 VPS verification
- **Issue:** The original `call_agent()` implementation followed PATTERNS.md exactly — it called `sys.exit(1)` when Brain returned `status:ERROR`. However, Brain's query agent always returns `status:ERROR` due to a Groq structured-output conflict in LiteLLM. With `sys.exit(1)`, the __main__ block never reached `json.dumps(...)`, so no run_id was printed. The V4 verification command (`python3 brain_http.py query 'ping' 2>/dev/null | python3 -c "... 'run_id' in d ..."`) would have failed because there was no JSON on stdout.
- **Fix:** Changed status:ERROR handling to print to stderr but NOT exit 1. The plan's V4 relaxation explicitly states "HTTP 200 and run_id are returned correctly" — the error is an application-level issue, not a transport failure. The run_id is still valid and needed by callers.
- **Files modified:** hermes-skills/brain_http.py
- **Commit:** 5c17663 (amended before final commit — both committed at 5c17663)

## Known Stubs

None — brain_http.py is fully wired to live Brain API. Dry-run tests use --dry-run flag, not stub data.

## Threat Flags

No new threat surface beyond what is documented in the plan's threat model (T-03-13 through T-03-16). All mitigations applied:
- T-03-13: stdout only prints run_id + content + status (structured JSON, not full response headers)
- T-03-14: sys.argv positional args used, no shell=True
- T-03-SC: no pip install in this plan; httpx 0.28.1 unchanged

## Self-Check: PASSED

Files exist:
- hermes-skills/brain_http.py: FOUND
- skills/brain-query/SKILL.md: FOUND
- skills/brain-ingest/SKILL.md: FOUND
- skills/brain-research/SKILL.md: FOUND
- tests/phase-03/brain-smoke.bats: FOUND

Commits:
- 5c17663: feat(03-04): add brain_http.py synchronous HTTP helper for Brain Agno API
- a9d739c: feat(03-04): add 3 brain-bridge skills and brain-smoke bats tests (REQ-ws-005)
