# Workshop Agents Uplift — Phases A & B

## Origin

Derived from a `/grill-me` session researching `obra/superpowers`, `paperclipai/paperclip`, `VILA-Lab/Dive-into-Claude-Code`, and `GetBindu/awesome-claude-code-and-skills` to level up the ultra-workshop multi-agent pipeline. Decisions agreed interactively; this document captures both phases for GSD import.

---

## Phase A — In-Place Soul/Discipline/Context Uplift

### Context

The ultra-workshop pipeline (`triage → requirements → planner → coder(aider) → reviewer(2 retries) → HITL → push`) works structurally but its specialist SKILL.md "souls" are terse behavior specs with real quality gaps: no build/test verification gate, blind retries without structured feedback, brain reads nearly absent, and two documented inconsistencies between `workshop-fix` and `workshop-build`.

**Goal:** In-place uplift — pure `SKILL.md`/context edits plus one sandbox verify command and two bug fixes. Zero `workshop_build.py` flow restructure. Ships as a single PR.

### Requirements

- **REQ-uplift-A1:** All five specialist SKILL.md souls rewritten with lean/behavioral discipline (decision-rules, explicit "never do" lists, escalation behavior). No persona flavor. Model: Superpowers-style mandatory discipline, not Paperclip persona.
- **REQ-uplift-A2:** Coder stage runs repo's build/test command after applying the diff; includes `{build_passed, test_passed, output_tail}` in Diff JSON. TDD-first where test harness exists.
- **REQ-uplift-A3:** Reviewer evaluates build/test result *before* static checks. Failing build = automatic FAIL, feeds retry loop.
- **REQ-uplift-A4:** Reviewer emits failures as `[{file, problem, required_fix}]` (not prose). Coder retry injects this list as primary task. Two-pass review: pass 1 = spec compliance + build/test; pass 2 = quality/security/secrets. Pass-1 failure short-circuits to retry.
- **REQ-uplift-A5:** After 2nd failed retry, exit to HITL gate (exit-code-2 machinery) — human chooses accept-with-notes / more guidance / abort — instead of emitting a broken diff. Retry count stays at 2.
- **REQ-uplift-A6:** Planner promotes `brain-query` from opt-in to standard: retrieve repo conventions + most-relevant prior ADRs, injected as context *after* behavior rules.
- **REQ-uplift-A7:** Reviewer queries brain for project-specific review rules / prior incident ADRs before both review passes.
- **REQ-uplift-A8:** `workshop-fix/SKILL.md` push path updated from heredoc/`workshop_push.py` to `workshop_continue.py` (matches `workshop-build`). Requirements stage added to workshop-fix pipeline flow.

### Files to change

- `skills/{triage,requirements,planner,coder,reviewer}-specialist/SKILL.md`
- `skills/workshop-fix/SKILL.md`
- `hermes-skills/aider_runner.py` — run + capture test output
- `hermes-skills/workshop_reviewer.py` — structured failure shape + two-pass logic
- `hermes-skills/workshop_build.py` — retry-input wiring + escalate-on-exhaustion exit (exit code 2)
- `hermes-skills/workshop_planner.py` — standard brain-query call
- `deploy/phase-04-manifest.txt`, `README.md`

### Verification

1. `rtk bats tests/phase-04/` — existing smoke suite stays green.
2. New smoke tests assert: structured-failure `{file,problem,required_fix}` contract; escalate-to-HITL on 2nd-retry-exhaustion (exit code 2).
3. One real end-to-end run on `new-test` sandbox repo: build/test-verify + structured retry + planner/reviewer brain-read all fire in the log.
4. Manual HITL gate check via Telegram (clarification path + new escalation gate).

### Deploy

Copy changed `SKILL.md` + `.py` to `ultra-workshop/hermes-skills/` and uws `~/.hermes/skills/`, restart gateway, update `deploy/phase-04-manifest.txt` and `README.md` in same commit.

---

## Phase B — Structural Redesign (queued, do not build during Phase A)

### Context

Phase A hardens the existing 5-stage pipeline. Phase B restructures it into a richer "team" model, taking the pipeline from triage-first to conception-first and adding parallel quality gates. Architectural changes touch `workshop_build.py` orchestration, HITL routing, brain integration, and agent composition.

### Requirements

- **REQ-uplift-B1 — Conception/Brainstorm stage:** New role before triage. Socratic problem-space exploration loop — is this the right thing to build? Proposes alternative approaches. Conversational (multi-turn HITL), not fire-and-forget. Superpowers brainstorm-gate pattern.
- **REQ-uplift-B2 — Agent personas + token budgets:** Paperclip employee model. Each specialist gets a job description, a monthly token budget tracked against brain ledger, and auto-pause at 100% utilization. Richer persona framing for judgment-heavy roles (requirements, planner, reviewer).
- **REQ-uplift-B3 — Immutable per-ticket audit log:** Every instruction, tool call, and decision appended to an append-only log keyed by `task_id`, written to the brain. Debuggable, recoverable pipeline. No silent failures.
- **REQ-uplift-B4 — Parallel six-scope review wave:** Split reviewer into 6 non-overlapping AgentTool-isolated subagents: correctness, security, performance, test-coverage, documentation, config/deploy. Each produces a bounded report. A dedup+autofix merge agent collapses results and auto-fixes minor issues.
- **REQ-uplift-B5 — git-worktree parallelism:** Each file-editing agent gets a dedicated git worktree. Lock-based coordination. Enables safe concurrent agent work without merge conflicts.
- **REQ-uplift-B6 — AgentTool vs SkillTool discipline:** Code and review agents isolated via AgentTool (separate context, prevents ~7× token cost multiplier); planning and verification gates run as SkillTool (shared context, cheap).
- **REQ-uplift-B7 — Requirements reads brain:** Requirements-specialist queries brain for prior clarifications on this repo before triggering HITL — catches ambiguities that were already resolved in past tasks.

### Key architectural decisions (captured from grill session)

| Decision | Choice | Rationale |
|---|---|---|
| Soul style | Lean/behavioral (A) → richer personas (B) | Personas add cost/noise in JSON-in-JSON-out stages; only worth it where judgment depth matters |
| Verification | In-stage execute-and-verify (A) vs new verify stage (B) | A is zero-restructure; B can promote to a dedicated verify agent |
| Retry count | Stay at 2 throughout | Informed retries converge; 3rd retry = human decision |
| Brain reads | Planner + reviewer (A) → all stages including requirements (B) | Incremental; requirements brain-read deferred to B to avoid noise risk |
| Conception | Deferred to B | Structural HITL loop, not a SKILL.md edit |
| Parallelism | Deferred to B | Requires orchestration changes + worktree infra |

---

## Phase sequencing

```
Phase A (this PR) → Phase B (next milestone)
    ↑
No orchestration changes
Pure SKILL.md + .py edits
Ships fast, immediately raises quality
```
