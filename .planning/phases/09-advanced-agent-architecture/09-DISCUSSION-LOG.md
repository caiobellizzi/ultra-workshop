# Phase 09: Advanced Agent Architecture - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-27
**Phase:** 09-advanced-agent-architecture
**Areas discussed:** L12 unlock gate, Review-wave roster & routing, Cost: isolation + model routing, Token budgets & auto-pause, Merge agent & severity routing, Brainstorm/worktree/budget-amounts, SC-1 reconciliation

---

## L12 unlock gate (precondition)

| Option | Description | Selected |
|--------|-------------|----------|
| Unlock L12 for Phase 9 | Owner sign-off; 5-role topology superseded by brainstorm + multi-scope review wave | ✓ |
| Unlock partially | Only some B-items in scope | |
| Don't unlock yet | Keep L12 locked, stay planning-only | |

**User's choice:** Unlock L12 — plus directive to add stack-specialized agents (security, python, typescript, reactjs, qa, "and others") and to research with `superpowers` + `paperclip` as references.
**Notes:** Recorded as PROJECT.md amendment L12-A. Triggered a research pass (paperclip schema + superpowers parallel/review skills) before gray-area discussion.

---

## Review-wave roster & routing

| Option | Description | Selected |
|--------|-------------|----------|
| Hybrid | correctness+security always-on; python/ts/reactjs diff-gated; qa test-gated; docs/config file-gated | ✓ |
| Stack-specialized only | security always-on + stack strictly diff-gated; no always-on correctness | |
| Original 6 fixed scopes | all 6 every time, language-agnostic | |

**User's choice:** Hybrid roster; registry (`review-roster.yaml`) + souls; ext+path heuristic selection; initial roster = all 8 (correctness, security, python, typescript, reactjs, qa, docs, config).
**Notes:** Registry-over-autodiscovery for auditability; deterministic selection for zero LLM cost.

---

## Cost: isolation + model routing

| Option | Description | Selected |
|--------|-------------|----------|
| Isolate judgment roles only | security+correctness isolated; rest shared-context | ✓ |
| Isolate security + all stack reviewers | broader isolation | |
| Isolate all (original B6) | all 8 + merge isolated | |

**User's choice:** Isolate judgment roles only; **all reviewers use NVIDIA NIM as primary** (not Claude tiers); frozen read-only diff artifact (reviewers no worktree); policy doc + registry-enforced.
**Notes:** NIM-primary choice reframes "isolation" as isolated Hermes dispatch (NIM token cost, not Claude 7x). Exact NIM alias/fallback left to planning.

---

## Token budgets & auto-pause

| Option | Description | Selected |
|--------|-------------|----------|
| Per-role monthly cap | brain ledger caps under $20/day breaker | ✓ |
| Per-task envelope | fixed per-build review budget | |
| Both | monthly cap + per-task soft ceiling | |

**User's choice:** Per-role monthly cap; role-tiered exhaustion fallback (security→block HITL, stack→cheaper NIM, non-critical→skip+log); Telegram warn@80%/pause@100%; ledger in `brain/_system/cost-ledger.md` in USD-cents.
**Notes:** Accepted proposed default cap amounts (D-12) — tunable in registry.

---

## Merge agent & severity routing

| Option | Description | Selected |
|--------|-------------|----------|
| Conservative / mechanical only | autofix formatting/lint/imports/docstrings/typos only | ✓ |
| Moderate | + single-line deterministic fixes | |
| No auto-fix — route only | all fixes to coder/HITL | |

**User's choice:** Conservative auto-fix; merge agent applies fixes in worktree + re-runs build/test; severity map Critical=block / Important=non-block HITL / Minor=autofix; dedup by (file,line) + brain note & HITL summary.
**Notes:** Brain kept as single source of truth (GitHub PR-comment surfacing deferred).

---

## Brainstorm / worktree / budget amounts (lighter checklist items)

| Item | Selected |
|------|----------|
| Brainstorm trigger | Explicit `/brainstorm <task>` command (not flag, not always-on) |
| Brainstorm exit | Exit only on explicit owner approval (NO turn cap) |
| Worktree cleanup | Prune on task completion, retain on failure (+ max-age sweep) |
| Budget caps | Accept proposed defaults (D-12) |

**Notes:** Audit-log format not re-asked — locked by ROADMAP SC-3 (`vault/_system/workshop-audit/{task_id}.jsonl`).

---

## SC-1 reconciliation (conflict surfaced)

| Option | Description | Selected |
|--------|-------------|----------|
| Owner override — remove ≤5 cap | brainstorm loops until explicit approval | ✓ |
| Soft cap: warn at 5, continue | continue-checkpoint at turn 5 | |
| Keep ≤5 hard cap | revert to locked SC-1 | |

**User's choice:** Owner override — the "exit on approval only" choice conflicted with locked ROADMAP SC-1 (≤5 turns). Owner authority supersedes; SC-1 amended, recorded as PROJECT.md amendment B1-A.
**Notes:** Surfaced rather than silently resolved, per think-before-coding discipline.

---

## Claude's Discretion

- `review-roster.yaml` schema shape, audit-log JSON line schema, dedup data structure — fixed behavior, not field names; left to planning.
- Exact primary NIM model alias + LiteLLM fallback chain for reviewers — research/planning detail.

## Deferred Ideas

- Additional language/domain reviewers (Go, Rust, SQL, accessibility) — add later via soul + registry line.
- LLM-based reviewer selection — only if deterministic heuristics prove insufficient.
- GitHub PR-comment surfacing of findings — deferred in favor of brain-as-single-source.
- Per-task budget envelopes — deferred in favor of per-role monthly caps.
