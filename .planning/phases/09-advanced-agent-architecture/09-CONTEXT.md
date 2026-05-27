# Phase 09: Advanced Agent Architecture - Context

**Gathered:** 2026-05-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Restructure the workshop pipeline from the locked 5-role topology into a richer team model. The pipeline becomes:

**brainstorm → triage → requirements → planner → coder → parallel review-wave → HITL → push**

This phase delivers seven architectural changes (B1–B7 from the design-intent doc `09-01-PLAN.md`):
- **B1** Conception/brainstorm pre-triage HITL stage
- **B2** Agent personas + per-role monthly token budgets + auto-pause (Paperclip employee model)
- **B3** Immutable per-task_id audit log in the brain
- **B4** Parallel multi-scope review wave (replaces the single `reviewer-specialist`) + dedup/autofix merge agent
- **B5** git-worktree isolation for the (one) file-editing agent in the wave
- **B6** AgentTool/SkillTool isolation policy, documented + enforced
- **B7** `requirements-specialist` reads the brain for prior clarifications before triggering HITL

**Owner unlock (this session):** L12 (5-role topology) is unlocked for Phase 9 — see PROJECT.md amendment **L12-A**. Coder substrate (Aider, L10), coordination (Hermes `delegate_task`, L11), and "no LangGraph" (L22) remain in force.

**Out of scope (deferred):** LangGraph orchestration (L22 — Phase 2 reservation), OpenHands coder (L10), additional language reviewers beyond the initial roster (Go/Rust/SQL/a11y — add later via registry + soul).
</domain>

<decisions>
## Implementation Decisions

### Review-wave roster & routing (B4)
- **D-01:** **Hybrid roster.** Cross-cutting reviewers `correctness` + `security` run on EVERY wave (always-on). Stack reviewers `python` / `typescript` / `reactjs` are diff-gated by file type. `qa` is gated on the presence of test/spec files. `docs` + `config` are gated on relevant files. Initial Phase 9 roster = all 8 (correctness, security, python, typescript, reactjs, qa, docs, config).
- **D-02:** **Registry + souls.** Routing rules (extension→specialist map, model, isolation flag, budget) live in a new `hermes-config/review-roster.yaml`. Each specialist is a `SKILL.md` soul under `skills/<name>-reviewer/`. Adding a specialist = new soul + one registry line. Not auto-discovery, not hardcoded Python.
- **D-03:** **Selection = extension + path heuristics.** Deterministic, zero-LLM-cost selection: `.py`→python, `.ts/.tsx`→typescript, `.tsx/.jsx`→reactjs, path contains `test`/`spec`→qa, deploy/env/secrets paths→config. Fully auditable. No LLM classifier.

### Cost: isolation + model routing (B6)
- **D-04:** **Isolate judgment roles only.** `security` + `correctness` run as isolated dispatches (fresh per-reviewer context window, only their diff slice injected). `python` / `typescript` / `reactjs` / `qa` / `docs` / `config` run as shared-context (SkillTool-style) passes. The merge agent is isolated.
- **D-05:** **All reviewers use NVIDIA NIM as the primary model**, routed through the LiteLLM proxy — NOT Claude tiers. Implication: "isolation" here means isolated *Hermes agent dispatch* (fresh context per reviewer), so the VILA-Lab ~7x Claude-AgentTool cost finding does not apply directly; the cost lever is NIM token spend. *(Open detail for research/planning: exact primary NIM model alias + LiteLLM fallback chain.)*
- **D-06:** **Frozen read-only diff artifact.** Coder produces one diff snapshot; all reviewers read it in parallel and never write. Reviewers need NO worktrees. Only the merge agent's auto-fix step needs a worktree.
- **D-07:** **Policy doc + registry-enforced.** Write `hermes-config/agent-isolation-policy.md` (rationale/rules) AND encode per-specialist isolation + model in `review-roster.yaml` so the policy is enforced in code, not just documented.

### Token budgets & auto-pause (B2)
- **D-08:** **Per-role monthly cap**, tracked in the brain ledger, sitting UNDER the existing global $20/day circuit breaker ($18 self-cancel / $20 refuse).
- **D-09:** **Role-tiered exhaustion fallback:** `security` exhausted → BLOCK to HITL (never skip security). Stack reviewers (`python`/`typescript`/`reactjs`) → substitute a cheaper NIM fallback model. Non-critical (`qa`/`docs`/`config`) → skip & log the gap in the audit trail.
- **D-10:** **Telegram alerts:** warn at 80% utilization, auto-pause at 100%; human resumes via the existing Telegram control surface.
- **D-11:** **Ledger location + unit:** per-role monthly spend in `brain/_system/cost-ledger.md`, tracked in **USD-equivalent cents** (normalizes across NIM/fallback models), wired into existing `workshop/cost.py` + `hermes-skills/brain_http.py`.
- **D-12:** **Default per-role monthly caps (USD-cents, owner-accepted defaults — tune in `review-roster.yaml`):** security $40, correctness $30, python/typescript/reactjs $20 each, qa $10, docs $10, config $10, merge-agent $15, brainstorm $20, shared planner/triage/requirements pipeline pool $30.

### Merge agent & severity routing (B4)
- **D-13:** **Conservative auto-fix scope.** The merge agent auto-fixes ONLY safe mechanical items: formatting, lint, import order, missing docstrings, obvious typos. It NEVER auto-touches logic, security, public APIs, or behavior. Anything ambiguous escalates.
- **D-14:** **Merge agent applies fixes in its worktree + re-runs build/test gate.** If build/test fails after autofix → escalate to coder retry / HITL. Keeps the coder out of trivial loops.
- **D-15:** **Severity → action map:** `Critical` → hard-block the push, require human approval at the HITL gate. `Important` → non-blocking, surfaced to HITL + logged, push may proceed on approval. `Minor` → auto-fixed (per D-13) or noted.
- **D-16:** **Dedup by `(file, line)`** — same location cited by multiple specialists collapses to one entry (highest severity wins, `fix_hint`s merged). `Important` findings written as a brain note via `brain_http.py` AND included in the HITL approval summary (brain = single source of truth).

### Brainstorm / conception (B1)
- **D-17:** **Trigger = explicit `/brainstorm <task>` command**, separate from `/build`. `/build` stays a direct fast-path (no forced conception). Owner opts into the Socratic loop when a task is fuzzy.
- **D-18:** **Exit = explicit owner approval only, NO turn cap** (owner override of ROADMAP SC-1; recorded as PROJECT.md amendment **B1-A**). The loop never auto-proceeds to triage; it produces a scoped goal statement that feeds triage on approval.

### Audit log (B3)
- **D-19:** **Locked by ROADMAP SC-3 (not re-discussed):** every pipeline event appended to an append-only `vault/_system/workshop-audit/{task_id}.jsonl` via brain ingest (`brain_http.call_agent("ingest", ...)`). Entries cover wave start, each specialist completion (with token/cost + finding counts), and merge completion (block decision).

### Worktree lifecycle (B5)
- **D-20:** **Prune on task completion, retain on failure.** Worktree removed when a task finishes successfully; retained on failure for post-mortem, with a configurable max-age sweep so stale failed worktrees don't accumulate (VPS RAM/disk pressure noted in STATE.md).

### requirements-specialist brain read (B7)
- **D-21:** **Locked by ROADMAP SC-6 (not re-discussed):** `requirements-specialist` queries the brain for `"prior clarifications for {repo_full_name}"` before triggering HITL, to avoid re-asking resolved ambiguities.

### Claude's Discretion
- Exact `review-roster.yaml` schema shape, the audit-log JSON line schema, and the dedup data structure are left to planning — the decisions above fix behavior, not field names.
- Exact primary NIM model alias + LiteLLM fallback chain for reviewers (D-05) is a research/planning detail.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase intent & requirements
- `.planning/phases/09-advanced-agent-architecture/09-01-PLAN.md` — design-intent doc; B1–B7 architectural changes, inherited grill decisions, locked-decision compatibility notes. **This phase's primary source.**
- `.planning/ROADMAP.md` §"Phase 9: Advanced Agent Architecture" — Goal + 6 locked success criteria (SC-1 amended by B1-A).
- `.planning/REQUIREMENTS.md` — REQ-ws-043…REQ-ws-050 to be minted during planning.

### Locked decisions / owner amendments
- `.planning/PROJECT.md` §"Locked Decisions" (L10, L11, L12, L22) and §"Owner Amendments — 2026-05-27 (Phase 9)" (**L12-A** topology unlock, **B1-A** brainstorm no-cap). Also §budget ($20/day circuit breaker at $18/$20).

### Integration code (existing — to extend)
- `hermes-skills/workshop_reviewer.py` + `workshop/reviewer.py` — the single reviewer being replaced by the wave.
- `workshop/cost.py` + `hermes-skills/brain_http.py` — cost/budget tracking + brain ingest (B2/B3).
- `hermes-skills/aider_runner.py` + `hermes-skills/workshop_build.py` — coder + orchestration; diff snapshot source (D-06), exit-code-2 HITL path (Phase 8).
- `skills/reviewer-specialist/SKILL.md` — soul to split into the multi-scope roster.
- `hermes-config/config.yaml` — existing Hermes config; new `review-roster.yaml` + `agent-isolation-policy.md` land alongside it.

### Reference architectures (research, 2026-05-27)
- `paperclipai/paperclip` — `packages/db/src/schema/{agents,budget_policies,activity_log,cost_events}.ts` — persona + budget + audit schema mirrored by B2/B3.
- `~/.claude/plugins/cache/superpowers-marketplace/superpowers/5.0.7/skills/{dispatching-parallel-agents,subagent-driven-development,requesting-code-review,receiving-code-review}/SKILL.md` — parallel-isolation discipline, diff-gated dispatch, severity-merge patterns mirrored by B4/B6.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `workshop/reviewer.py` / `hermes-skills/workshop_reviewer.py`: existing single-reviewer logic, two-pass review, structured `[{file, problem, required_fix}]` failures (Phase 8) — the report shape generalizes to per-specialist findings + severity.
- `workshop/cost.py` + `brain_http.py`: existing cost tracking + $20/day circuit breaker — extend to per-role monthly ledger (D-08/D-11).
- `skills/*-specialist/SKILL.md`: the lean/behavioral soul format (Phase 8) — new reviewer souls follow it.
- Existing Telegram control surface (Phase 2/6): reused for budget warn/pause alerts (D-10).
- Phase 8 exit-code-2 HITL path in `workshop_build.py`: the gate where Critical findings block (D-15).

### Established Patterns
- Hermes `delegate_task` dispatch (L11) — review wave uses agent dispatch, NOT LangGraph graph edges (L22). Parallelism is "N isolated Hermes dispatches over one frozen diff", not a state graph.
- Brain reads/writes via `brain_http.py` (Phase 7/8) — audit log (B3) and prior-clarification reads (B7) ride this shim.
- Lean/behavioral SKILL.md discipline (Phase 8) — no persona flavor for gates; B2 adds richer personas ONLY for judgment-heavy roles.

### Integration Points
- Coder emits one frozen diff artifact → review-wave reads it (D-06).
- Review wave (wave 2, parallel) → merge agent (wave 3, sequential, one worktree) → HITL gate → push.
- Per-dispatch budget check reads `brain/_system/cost-ledger.md` before dispatch; writes spend after (D-08/D-09).
- Every event appends to `vault/_system/workshop-audit/{task_id}.jsonl` (D-19).
</code_context>

<specifics>
## Specific Ideas

- Stack-specialized reviewers explicitly requested by the owner: `security`, `python`, `typescript`, `reactjs`, `qa`, "and others" — map to the existing reviewer-agent family (security-reviewer, python-reviewer, typescript-reviewer, test-coverage-reviewer) plus a new react soul. Roster is extensible (D-02) so Go/Rust/SQL/a11y can be added later without re-architecting.
- Grounding references named by the owner: the `superpowers` repo (parallel-agent + review patterns) and `paperclip` (employee/budget/audit model). Both researched 2026-05-27; patterns captured in canonical_refs.
</specifics>

<deferred>
## Deferred Ideas

- Additional language/domain reviewers beyond the initial 8 (Go, Rust, SQL, accessibility) — add post-Phase-9 via a new soul + one `review-roster.yaml` line. No re-architecture needed.
- LLM-based reviewer selection (vs deterministic ext/path heuristics) — only if mixed/unusual file types prove the heuristic insufficient.
- GitHub PR-comment surfacing of findings (vs brain-only) — considered (D-16 alt); deferred to keep the brain as single source of truth and avoid per-wave GitHub API calls.
- Per-task budget envelopes (vs per-role monthly caps) — considered (D-08 alt); deferred in favor of simpler role caps.
</deferred>

---

*Phase: 09-advanced-agent-architecture*
*Context gathered: 2026-05-27*
