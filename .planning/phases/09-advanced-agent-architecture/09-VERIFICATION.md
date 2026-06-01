---
phase: 09-advanced-agent-architecture
verified: 2026-06-01
verifier: inline (Opus — Sonnet verifier tier rate-limited until 18:00)
status: pass_with_caveats
score: "6/8 requirements verified, 2 partial (REQ-ws-048, REQ-ws-050)"
requirements_checked: ["REQ-ws-043", "REQ-ws-044", "REQ-ws-045", "REQ-ws-046", "REQ-ws-047", "REQ-ws-048", "REQ-ws-049", "REQ-ws-050"]
human_verification:
  - test: "Live brainstorm HITL loop produces a scoped goal"
    expected: "/build --brainstorm runs a pre-triage conversational loop that continues until explicit owner approval, then feeds a scoped goal to triage"
    why_human: "Requires a live Hermes session + Telegram owner interaction; only the code path and flag handling are verifiable offline"
  - test: "Per-task immutable audit log written to brain"
    expected: "vault/_system/workshop-audit/{task_id}.jsonl appended via brain_http ingest with one line per pipeline event"
    why_human: "Requires a live pipeline run against the VPS brain endpoint; offline only confirms append_audit call sites exist"
  - test: "8 parallel reviewers dispatch + merge agent dedup/autofix in a live run"
    expected: "wave 2 runs correctness/security/python/typescript/reactjs/qa/docs/config concurrently; wave 3 merge agent dedups by (file,line) and auto-fixes severity:low"
    why_human: "Requires a live build with a real diff; offline confirms ThreadPoolExecutor + 8-scope roster + merge tests exist"
  - test: "Specialist auto-pause at 100% monthly budget"
    expected: "specialist pauses with Telegram alert at 80% and auto-pause at 100% utilization"
    why_human: "Requires accumulated live token spend in the brain cost-ledger over a month"
---

# Phase 9: Advanced Agent Architecture — Verification Report

**Phase Goal:** Conception/brainstorm HITL stage; per-agent job descriptions + monthly token budgets + auto-pause; immutable per-ticket audit trail; single reviewer replaced by parallel 8-scope review wave with dedup+autofix merge agent; AgentTool/SkillTool isolation policy enforced.
**Verified:** 2026-06-01 · **Status:** pass_with_caveats · **Re-verification:** No (initial — backfilled during v1.0 milestone audit)

> Backfill note: Phase 9 shipped without a VERIFICATION.md. This report was produced during the v1.0 re-audit by running the REQ-ws-043..050 acceptance checks against the live codebase. Two requirements (048, 050) are confirmed **partial** with documented caveats; the rest are code-verified with live behaviors flagged for human verification.

## Requirements

| REQ | Status | Evidence |
|-----|--------|----------|
| REQ-ws-043 (brainstorm HITL stage) | verified | `grep -E "--brainstorm|brainstorm_approved" hermes-skills/workshop_build.py` → 9 matches; `tests/phase-09/test_brainstorm_hitl.py` present. Live loop → human_needed. |
| REQ-ws-044 (monthly budgets + auto-pause) | verified (code) | `hermes-config/review-roster.yaml` monthly/budget/auto-pause → 10 matches; `tests/phase-09/test_cost_budget.py` present. Live 100% auto-pause → human_needed. |
| REQ-ws-045 (immutable audit log) | verified (code) | `append_audit`/`workshop-audit` in `hermes-skills/workshop_build.py` → 7 matches; `tests/phase-09/test_audit_log.py` present. Live brain ingest → human_needed. |
| REQ-ws-046 (8-scope wave + merge agent) | verified (location note) | `ThreadPoolExecutor` is in `hermes-skills/workshop_build.py` (not `workshop_reviewer.py` as the REQ acceptance line states — implementation placed the wave dispatch in workshop_build.py); 8 scopes present in roster; `tests/phase-09/test_review_wave.py` + `test_merge_agent.py` present. Capability exists; acceptance grep pointed at the wrong file. |
| REQ-ws-047 (isolation policy documented + registry-enforced) | verified (token note) | `hermes-config/agent-isolation-policy.md` exists (6.5K, "isolation" ×8); roster encodes per-role `isolation: true/false` (security+correctness `true`, others `false`). REQ acceptance grep used literal "isolated"; the actual key is `isolation:`. Feature present. |
| REQ-ws-048 (requirements brain pre-query) | **partial** | `skills/requirements-specialist/SKILL.md` references brain-query (1 match) ✓, BUT `workshop/requirements_gate.py` `_query_prior_clarifications` injects into `planning_notes` only (decision T-09-03-04), not the primary requirements path. SC-6 ("always queries brain before HITL") only partially wired. |
| REQ-ws-049 (review roster registry) | verified | `hermes-config/review-roster.yaml` exists; 8 reviewer scopes present (scope-term grep → 12 matches ≥8). |
| REQ-ws-050 (git-worktree isolation) | **partial (documented deferral)** | `workshop/worktree.py` exists (4.7K), `py_compile` OK, `tests/phase-09/test_worktree.py` present (creation/pruning lifecycle). **Zero production callers** — review wave runs via ThreadPoolExecutor, not worktrees. Production wiring explicitly deferred per the REQ-ws-050 caveat. |

## Success Criteria

| SC | Status | Evidence |
|----|--------|----------|
| SC-1 brainstorm loop until approval | verified (code) / human (live) | REQ-ws-043 |
| SC-2 budgets + auto-pause | verified (code) / human (live) | REQ-ws-044 |
| SC-3 immutable audit log | verified (code) / human (live) | REQ-ws-045 |
| SC-4 8 reviewers + merge agent | verified (code) / human (live) | REQ-ws-046 |
| SC-5 isolation policy enforced | verified | REQ-ws-047 + 049 |
| SC-6 requirements brain pre-query | **partial** | REQ-ws-048 (planning_notes-only) |

## Verdict

Code for all 8 requirements is present and the supporting `tests/phase-09/` suite + `09-VALIDATION.md` exist. **REQ-ws-048** is partial (brain pre-query injects planning_notes only) and **REQ-ws-050** is a partial documented deferral (worktree.py created but unwired in production). Live behaviors (brainstorm HITL, brain audit ingest, 8-reviewer dispatch, 100% auto-pause) are flagged `human_needed`. Overall: **pass_with_caveats** — appropriate to keep REQ-ws-043..050 at "Implemented" (not "Complete") until a live VPS run confirms the runtime behaviors.
