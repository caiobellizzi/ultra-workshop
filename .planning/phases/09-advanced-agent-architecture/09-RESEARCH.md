# Phase 9 Research: Advanced Agent Architecture

**Researched:** 2026-05-27
**Domain:** Python orchestration pipeline extension — multi-scope review wave, HITL brainstorm stage, token budgets, audit log
**Confidence:** HIGH (all findings from direct codebase inspection + locked decisions in 09-CONTEXT.md)

---

## User Constraints (from CONTEXT.md)

### Locked Decisions
- L10: Coder = Aider subprocess only (NOT Claude Code, NOT OpenHands)
- L11: Hermes `delegate_task` coordination (review wave = N isolated Hermes dispatches, NOT LangGraph)
- L12: 5-role topology UNLOCKED for Phase 9 only (owner amendment L12-A)
- L22: No LangGraph — parallel review uses AgentTool dispatch + frozen diff artifact
- B1-A: Brainstorm stage has NO turn cap — loops until explicit owner approval
- Daily budget circuit breaker: $18 self-cancel / $20 hard refuse (global, in `workshop/cost.py`)
- All reviewers use NVIDIA NIM as primary model routed through LiteLLM proxy

### Claude's Discretion
- Exact `review-roster.yaml` schema shape
- Audit-log JSON line schema field names
- Dedup data structure field names
- Exact primary NIM model alias + LiteLLM fallback chain for reviewers (D-05)

### Deferred Ideas (OUT OF SCOPE)
- Additional language/domain reviewers beyond initial 8 (Go, Rust, SQL, a11y)
- LLM-based reviewer selection (vs deterministic ext/path heuristics)
- GitHub PR-comment surfacing of findings
- Per-task budget envelopes (vs per-role monthly caps)

---

## 1. Current Architecture Overview

- **`hermes-skills/workshop_build.py`** (33.8K) — Main orchestrator entry point. Implements the state machine `triage → requirements → planner → coder → reviewer → approval`. All stage dispatch goes through `run_stage(stage, skill_name, query_json, output_schema)`. Contains `StageTimeoutForHITL` exception, `_stage_should_run()` cursor logic, HITL payload construction, and the review-retry loop (max 3 attempts before `needs_review_recovery`). **This is the primary file for Phase 9 modification.**
- **`workshop/reviewer.py`** (9.5K) — Current single-reviewer logic. `review_query(query_json)` is the entry point. Implements brain-query for review context, pass-1 (spec compliance + build/test gate), pass-2 (quality/security/static). Returns `Review` or `ClarificationRequest` (Pydantic models). Contains `_compile_changed_python`, path validation, secret regex, ambiguity regex.
- **`hermes-skills/workshop_reviewer.py`** (1.3K) — Thin CLI shim. Calls `review_query()` from `workshop/reviewer.py`, emits JSON to stdout, handles `--dry-run`. Called by `hermes-skill-run.sh`.
- **`workshop/cost.py`** (2.8K) — Global daily budget tracking. `check_circuit_breaker()` reads `brain/_system/cost-ledger.md`, raises `BudgetExhausted` or `BudgetWarning`. `record_cost(task_id, amount, model)` posts to Brain curator. **Extend to per-role monthly tracking.**
- **`hermes-skills/brain_http.py`** (3.0K) — HTTP shim for Brain agents. `call_agent(agent_id, message, user_id)` POSTs multipart/form-data to `http://127.0.0.1:7000/agents/{id}/runs`. **Critical: must use `data={}` NOT `json={}` (422 otherwise).** Agents: `query`, `ingest`, `research`, `curator`, `chat`.
- **`workshop/requirements_gate.py`** (3.9K) — `evaluate_requirements(query_json)` entry. Currently only does hardcoded ambiguity detection (`_TWELVE_FACTORY_RE`). No brain read yet — **B7 adds brain pre-query here.**
- **`hermes-skills/workshop_requirements.py`** (1.4K) — CLI shim calling `evaluate_requirements()`.
- **`workshop/types.py`** (2.6K) — Pydantic models: `Plan`, `PlanStep`, `Diff`, `FileChange`, `Review`, `ReviewIssue`, `ClarificationRequest`, `ClarificationQuestion`, `IngestResult`. **Phase 9 adds `ReviewFinding` (with `severity` field) and `WaveReport` models.**
- **`workshop/stage_policy.py`** (2.1K) — Stage timeouts, auto_retries, `MODEL_ALIASES` dict. `run_stage()` in `workshop_build.py` reads this. **Phase 9 adds reviewer wave model aliases.**
- **`workshop/ledger.py`** (1.6K) — Local task progress log (`/home/uws/.ultra-workshop/tasks/{task_id}/progress_log.jsonl`). `append_progress()` writes JSONL. **Phase 9's audit log goes to brain vault instead; ledger stays for local fast-append.**
- **`hermes-skills/startup-hitl-scan.py`** (4.5K) — HITL restart-resilience. `record_hitl_pause()` writes to SQLite `pending_hitl.db`. Pattern for brainstorm HITL registration.
- **`skills/reviewer-specialist/SKILL.md`** — Current single-reviewer soul. **Phase 9 splits this into 8 scoped souls.**
- **`hermes-config/config.yaml`** — Hermes config (model, telegram, approvals mode). **Phase 9 adds `review-roster.yaml` + `agent-isolation-policy.md` alongside.**

---

## 2. Extension Points Per Success Criterion

### SC-1 / B1: Brainstorm HITL Stage

**Current state:** Pipeline starts at `triage`. `_STAGE_INDEX` dict maps stages to integers for cursor logic. No brainstorm concept exists.

**What needs to change:**
- Add `"brainstorm": -1` (or 0, shifting others) to `_STAGE_INDEX` in `workshop_build.py`
- Add `_stage_should_run(state, "brainstorm")` check before triage block
- New `/brainstorm` command handler in the Hermes skill layer (new `hermes-skills/workshop_brainstorm.py` or extend `workshop_build.py` via `--brainstorm` flag)
- Brainstorm is conversational multi-turn: exits ONLY on explicit owner approval (`clarify()` loop with explicit "approve" path). Uses existing `StageTimeoutForHITL` / `record_hitl_pause` pattern — but unlike other HITL escalations, brainstorm is the intentional start, not a failure path.
- Output: scoped goal statement string fed into `triage_query` as `goal`.
- D-17: trigger = explicit `/brainstorm <task>` (separate from `/build`, which stays a direct fast path)
- D-18: NO turn cap — loop runs until `state.get("brainstorm_approved") == True`

**Key files:** `workshop_build.py`, new `hermes-skills/workshop_brainstorm.py`, `startup-hitl-scan.py` (HITL registration)

---

### SC-2 / B2: Agent Personas + Per-Role Monthly Token Budgets

**Current state:** `workshop/cost.py` tracks daily global spend only. `LEDGER_PATH = /srv/second-brain/_system/cost-ledger.md`. `record_cost(task_id, amount, model)` calls Brain curator. No per-role tracking.

**What needs to change:**
- Add `get_role_monthly_spend(role: str) -> float` reading `brain/_system/cost-ledger.md` for role+month
- Add `record_role_cost(role: str, amount: float, model: str)` writing to Brain curator with role tag
- Add `check_role_budget(role: str)` raising role-appropriate exception
- Per-role caps from D-12 (in USD-cents): security=$40, correctness=$30, python/ts/reactjs=$20 each, qa=$10, docs=$10, config=$10, merge=$15, brainstorm=$20, pipeline-pool=$30
- Fallback behavior per D-09: security exhausted → BLOCK (no substitution), stack reviewers → use cheaper NIM fallback, non-critical (qa/docs/config) → skip + audit log entry
- D-10: Telegram warn at 80%, auto-pause at 100%. Reuse existing Telegram control surface.
- D-11: Tracked in USD-cents in `brain/_system/cost-ledger.md`, via `workshop/cost.py` + `brain_http.py`
- Personas (job descriptions) go in each specialist `SKILL.md` — richer framing for judgment-heavy roles (requirements, planner); lean discipline kept for gates

**Key files:** `workshop/cost.py` (extend), `hermes-config/review-roster.yaml` (caps config), each `skills/<name>-specialist/SKILL.md` (persona text), `workshop_build.py` (budget check before dispatch)

---

### SC-3 / B3: Immutable Per-Task Audit Log

**Current state:** `workshop/ledger.py` writes local JSONL to `/home/uws/.ultra-workshop/tasks/{task_id}/progress_log.jsonl`. This is local-only and not brain-backed.

**What needs to change:**
- New `append_audit(task_id: str, event: str, data: dict)` function — calls `brain_http.call_agent("ingest", ...)` with structured payload
- Log location: `vault/_system/workshop-audit/{task_id}.jsonl` (Brain manages the vault path)
- Events to log: wave start, each specialist completion (tokens/cost + finding counts), merge agent completion (block decision), brainstorm start/approval, HITL gate decisions
- Append-only guarantee: Brain ingest agent handles vault writes; no delete API exposed
- The local `append_progress` in `ledger.py` can remain for fast local writes; audit log is the authoritative brain-backed trail
- Format per D-19: `{"ts": ..., "task_id": ..., "event": ..., "role": ..., "tokens": ..., "cost_cents": ..., "findings": ..., "decision": ...}` (field names at planning discretion)

**Key files:** `workshop/ledger.py` (add `append_audit`), `hermes-skills/brain_http.py` (already has `call_agent("ingest")`), `workshop_build.py` (add audit calls at each pipeline event)

---

### SC-4 / B4: Parallel Multi-Scope Review Wave

**Current state:** Single `reviewer-specialist` stage. `run_stage("reviewer", "reviewer-specialist", ...)` in `workshop_build.py`. Returns one `Review` object. `review_query()` in `workshop/reviewer.py` does all checks monolithically.

**What needs to change:**

**New orchestration in `workshop_build.py`:**
- Replace single `run_stage("reviewer", ...)` with a parallel wave dispatcher
- `wave_2_dispatch(diff, plan, task_id, roster)` — selects active reviewers from `review-roster.yaml` based on D-03 heuristics (file extensions + path patterns), dispatches N parallel Hermes agent calls (one per reviewer), collects `[WaveReport]`
- Wave-3 sequential merge agent: `run_merge_agent(wave_reports, diff, task_id)` — deduplicates by `(file, line)`, auto-fixes `Minor` severity items (formatting/lint/imports/docstrings/typos only per D-13), escalates `Critical` to HITL block, surfaces `Important` to HITL summary

**New Python types needed:**
```python
class ReviewFinding(BaseModel):
    file: str
    line: int | None
    problem: str
    required_fix: str
    severity: Literal["Critical", "Important", "Minor"]

class WaveReport(BaseModel):
    role: str
    passed: bool
    findings: list[ReviewFinding]
    tokens_used: int
    cost_cents: float
```

**New soul files (each in `skills/<name>-reviewer/SKILL.md`):**
- `correctness-reviewer` — always-on, spec compliance, logic correctness
- `security-reviewer` — always-on, OWASP/secrets/auth (split from current reviewer.py `_SECRET_RE`)
- `python-reviewer` — gated on `.py` files
- `typescript-reviewer` — gated on `.ts/.tsx` files
- `reactjs-reviewer` — gated on `.tsx/.jsx` files
- `qa-reviewer` — gated on `test`/`spec` paths
- `docs-reviewer` — gated on `*.md`, `*.rst`, docstrings
- `config-reviewer` — gated on deploy/env/secrets paths

**New config file: `hermes-config/review-roster.yaml`** — roster of all 8 specialists with: `role`, `model_alias`, `isolation` (true/false per D-04), `file_patterns`, `monthly_budget_cents`, `fallback_model_alias` (for stack reviewers)

**Merge agent:** New `hermes-skills/workshop_merge_agent.py` + `skills/merge-agent/SKILL.md`

**Key files:** `workshop_build.py`, `workshop/reviewer.py` (split into specialized reviewers), `workshop/types.py` (new models), 8 new soul files, `hermes-config/review-roster.yaml`, `hermes-skills/workshop_merge_agent.py`

---

### SC-5 / B5 + B6: Worktree Isolation + AgentTool/SkillTool Policy

**Current state:** No worktree management exists. The coder uses `workspace_dir` (a `/tmp/uws-sandbox-<task-id>/` clone). No explicit isolation policy.

**What needs to change:**
- Merge agent gets a git worktree for auto-fix step only (reviewers read frozen diff, no writes per D-06)
- `workshop/worktree.py` (new): `create_worktree(repo_path, branch, task_id)`, `remove_worktree(path)`, `prune_stale_worktrees(max_age_hours)` — uses `git worktree add/remove/prune`
- D-20: prune on task success, retain on failure (for post-mortem), configurable max-age sweep
- `hermes-config/agent-isolation-policy.md` (new): documents the AgentTool (fresh context per dispatch) vs SkillTool (shared context pass) distinction. Isolated: security + correctness + merge-agent. Shared-context: python/ts/reactjs/qa/docs/config reviewers.
- No LangGraph — isolation = separate Hermes `delegate_task`-style dispatch with frozen diff injected, not a graph edge

**Key files:** New `workshop/worktree.py`, new `hermes-config/agent-isolation-policy.md`

---

### SC-6 / B7: requirements-specialist Brain Pre-Query

**Current state:** `workshop/requirements_gate.py` `evaluate_requirements()` does no brain query. The reviewer already does a brain query via `_query_review_memory()` in `workshop/reviewer.py` — same pattern.

**What needs to change:**
- Add `_query_prior_clarifications(repo_full_name: str) -> str` in `workshop/requirements_gate.py` mirroring `_query_review_memory()` in `reviewer.py`
- Query: `"prior clarifications for {repo_full_name}"`
- Inject result into `RequirementsDecision.planning_notes` so planner inherits it
- Fail-open: if Brain unreachable, log warning and continue (same as reviewer pattern)

**Key files:** `workshop/requirements_gate.py` (add brain pre-query)

---

## 3. Risk Areas and Landmines

**Risk 1: Parallel wave timeout accumulation**
Six parallel reviewer dispatches each have their own timeout. If reviewers run sequentially (not truly parallel), the wave could take 6× the single-reviewer timeout. The dispatch mechanism (`delegate_task` / subprocess-per-specialist) must actually parallelize — likely requires Python `concurrent.futures.ThreadPoolExecutor` or `asyncio.gather`. The current `run_stage()` is purely synchronous. This needs explicit parallel dispatch implementation, not just N sequential calls.
- Mitigation: Use `concurrent.futures.ThreadPoolExecutor(max_workers=8)` with per-reviewer timeout, collect results in a list. Stage timeout for the wave = max reviewer timeout + buffer (not sum).

**Risk 2: Frozen diff artifact handoff**
D-06 says reviewers read a frozen diff, never write. The diff is currently embedded in the `run_stage()` query JSON. The frozen artifact pattern requires serializing the `Diff` object to a temp file or passing it as a base64-encoded arg so all 6 dispatches read the same snapshot. If the `workspace_dir` changes between dispatches (e.g., from a concurrent coder retry), reviewers could read stale or incorrect state.
- Mitigation: Freeze `diff.model_dump_json()` to a temp file before wave dispatch. All reviewers receive the path as a read-only input.

**Risk 3: Per-role cost ledger write contention**
Six reviewers write cost entries concurrently to `brain/_system/cost-ledger.md` via Brain curator. Brain is a single HTTP endpoint at `127.0.0.1:7000` — concurrent writes could cause race conditions if the curator agent does a read-modify-write on the ledger file.
- Mitigation: Each reviewer records its cost after completion (not during). Consider a dedicated `cost-ingest` endpoint or queue pattern. For MVP, accept sequential cost recording after wave completion.

**Risk 4: Severity enum mismatch between soul and merge agent**
The merge agent deduplicates by `(file, line)` and routes by severity. If reviewer souls return inconsistent severity labels (e.g., "HIGH" vs "Critical", "low" vs "Minor"), the merge agent will fail silently or route incorrectly.
- Mitigation: Define severity as a strict `Literal["Critical", "Important", "Minor"]` in `ReviewFinding` Pydantic model with `field_validator` that normalizes casing. Reinforce in each soul's Output Schema section.

**Risk 5: Brain ingest latency blocking the pipeline**
`append_audit()` calls `brain_http.call_agent("ingest", ...)` synchronously at each pipeline event. If Brain is slow (VPS load, Groq quota), audit writes block the pipeline. The `DEFAULT_TIMEOUT = 60.0` in `brain_http.py` means a slow ingest can add 60s per event.
- Mitigation: Make audit writes fire-and-forget (non-blocking). Add `non_blocking=True` flag to `append_audit()` using `threading.Thread(target=..., daemon=True)`. Mirror the `record_cost()` pattern in `cost.py` which is already "non-blocking on failure."

**Risk 6: `_STAGE_INDEX` integer ordering with brainstorm**
Adding `"brainstorm": -1` (or renumbering to accommodate it as 0) requires updating every stage cursor check in `workshop_build.py`. There are ~10 places using `_STAGE_INDEX`. Missing one means brainstorm is silently skipped on resume.
- Mitigation: Add `"brainstorm"` at index 0 and shift `triage` to 1, etc. Write a unit test asserting the `_stage_should_run` returns correct values for each combination of `next_stage` + stage being tested.

**Risk 7: review-roster.yaml loading failure silently degrades to zero reviewers**
If the YAML file is missing or malformed, the wave dispatcher has no reviewers to run. If this silently passes (empty wave = empty findings = merge agent approves), security is bypassed.
- Mitigation: `load_review_roster()` must raise (not return empty list) if the file is missing or unparseable. Add a startup validation step. Always include `correctness` + `security` as hardcoded fallback for always-on roles even if YAML load fails.

---

## 4. Files to Create / Modify

| File | Action | SC / B |
|------|--------|--------|
| `workshop_build.py` | MODIFY — add brainstorm stage cursor, wave-2 parallel dispatch, wave-3 merge, audit calls, per-role budget check before dispatch | B1, B2, B3, B4 |
| `workshop/cost.py` | MODIFY — add `get_role_monthly_spend`, `record_role_cost`, `check_role_budget`, Telegram warn/pause at 80/100% | B2 |
| `workshop/types.py` | MODIFY — add `ReviewFinding` (with `severity`), `WaveReport`, `MergeReport` Pydantic models | B4 |
| `workshop/reviewer.py` | MODIFY — extract security checks + path checks into importable helpers; existing `review_query` becomes `correctness_review_query` used by correctness-reviewer soul | B4 |
| `workshop/requirements_gate.py` | MODIFY — add `_query_prior_clarifications()` brain pre-query before HITL trigger | B7 |
| `workshop/stage_policy.py` | MODIFY — add `"brainstorm"` stage policy + `MODEL_ALIASES` entries for all 8 reviewer roles | B1, B2, B4 |
| `workshop/ledger.py` | MODIFY — add `append_audit(task_id, event, data)` calling brain ingest (non-blocking) | B3 |
| `workshop/worktree.py` | CREATE — `create_worktree`, `remove_worktree`, `prune_stale_worktrees` via `git worktree` subprocess | B5 |
| `hermes-skills/workshop_brainstorm.py` | CREATE — CLI entry point for `/brainstorm` command, conversational HITL loop, outputs scoped goal | B1 |
| `hermes-skills/workshop_reviewer.py` | MODIFY — swap `review_query` call for `wave_dispatch` + `merge_agent` orchestration | B4 |
| `hermes-skills/workshop_merge_agent.py` | CREATE — CLI shim for merge agent | B4 |
| `hermes-skills/workshop_requirements.py` | No change needed (logic is in `requirements_gate.py`) | B7 |
| `hermes-config/review-roster.yaml` | CREATE — 8 reviewer entries: role, model_alias, isolation, file_patterns, monthly_budget_cents, fallback_model_alias | B2, B4, B6 |
| `hermes-config/agent-isolation-policy.md` | CREATE — AgentTool vs SkillTool policy doc | B6 |
| `skills/correctness-reviewer/SKILL.md` | CREATE — correctness soul (always-on) | B4 |
| `skills/security-reviewer/SKILL.md` | CREATE — security soul (always-on) | B4 |
| `skills/python-reviewer/SKILL.md` | CREATE — Python soul (diff-gated) | B4 |
| `skills/typescript-reviewer/SKILL.md` | CREATE — TypeScript soul (diff-gated) | B4 |
| `skills/reactjs-reviewer/SKILL.md` | CREATE — React soul (diff-gated) | B4 |
| `skills/qa-reviewer/SKILL.md` | CREATE — QA soul (diff-gated on test paths) | B4 |
| `skills/docs-reviewer/SKILL.md` | CREATE — Docs soul (diff-gated) | B4 |
| `skills/config-reviewer/SKILL.md` | CREATE — Config soul (diff-gated on deploy/env paths) | B4 |
| `skills/merge-agent/SKILL.md` | CREATE — Merge agent soul | B4 |
| `skills/reviewer-specialist/SKILL.md` | RETIRE — replaced by wave roster (keep for reference, do not delete) | B4 |
| `skills/brainstorm-specialist/SKILL.md` | CREATE — brainstorm soul (Socratic loop, persona-rich) | B1 |
| `skills/requirements-specialist/SKILL.md` | MODIFY — add brain pre-query behavior to discipline section | B7 |
| `skills/planner-specialist/SKILL.md` | MODIFY — add richer persona framing | B2 |
| `skills/requirements-specialist/SKILL.md` | MODIFY — add richer persona framing | B2 |

---

## 5. Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (unit) + bats (smoke/integration) |
| Existing test count | 45 pytest + 14 bats (both must stay green after Phase 9) |
| Quick run | `cd /opt/ultra-workshop && python -m pytest tests/ -x -q` |
| Full suite | `cd /opt/ultra-workshop && python -m pytest tests/ && bats tests/*.bats` |

### SC Verification Map

| SC | Behavior | Test Type | Command / Check |
|----|----------|-----------|-----------------|
| SC-1 | Brainstorm stage runs before triage | Unit | `pytest tests/test_workshop_build.py -k brainstorm` |
| SC-1 | No turn cap — loop doesn't auto-exit | Unit | Assert loop exits only on `brainstorm_approved=True` in state |
| SC-1 | `/brainstorm` separate from `/build` | Smoke | `hermes skill run brainstorm-specialist --dry-run` |
| SC-2 | Per-role monthly spend tracked | Unit | `pytest tests/test_cost.py -k role_budget` |
| SC-2 | Auto-pause at 100% sends Telegram | Integration | Mock budget at 100%, assert `StageRoleBudgetExhausted` raised |
| SC-3 | Audit entry written per pipeline event | Unit | Mock `brain_http.call_agent`, assert called with `"ingest"` at each event |
| SC-3 | Audit path is `vault/_system/workshop-audit/{task_id}.jsonl` | Unit | Assert ingest message contains correct path |
| SC-4 | 6 reviewers run on a `.py` diff | Unit | `pytest tests/test_review_wave.py -k wave_dispatch` |
| SC-4 | Only correctness+security run on non-gated diff | Unit | Assert roster selection returns only always-on roles for `.md`-only diff |
| SC-4 | Merge agent deduplicates `(file, line)` | Unit | `pytest tests/test_merge_agent.py -k dedup` |
| SC-4 | Critical finding blocks push | Unit | Assert `merge_result.block_push == True` when any `Critical` finding |
| SC-5 | Worktree created for merge agent | Unit | `pytest tests/test_worktree.py -k create` |
| SC-5 | Worktree pruned on task success | Unit | Assert `remove_worktree` called after successful push |
| SC-5 | `agent-isolation-policy.md` exists | Check | `test -f hermes-config/agent-isolation-policy.md` |
| SC-6 | requirements brain pre-query fires | Unit | Mock `brain_http`, assert `call_agent("query", ...)` called in `evaluate_requirements` |

### Wave 0 Gaps (must be created before implementation)

- [ ] `tests/test_review_wave.py` — covers SC-4 wave dispatch, roster selection, parallel execution
- [ ] `tests/test_merge_agent.py` — covers SC-4 dedup, severity routing, auto-fix scope
- [ ] `tests/test_cost.py` additions — covers SC-2 per-role tracking, warn/pause thresholds
- [ ] `tests/test_worktree.py` — covers SC-5 create/remove/prune
- [ ] `tests/test_audit_log.py` — covers SC-3 append_audit non-blocking call, correct path

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Brain `ingest` agent writes to `vault/_system/workshop-audit/` path as passed in message | SC-3 | Audit entries go to wrong path; need to verify Brain ingest API message format with curator |
| A2 | `concurrent.futures.ThreadPoolExecutor` is available on VPS Python 3.x runtime | SC-4 | Wave dispatch is sequential, 6× slower |
| A3 | `git worktree add` is available at VPS git version | SC-5 | Worktree isolation cannot be implemented; fallback = no isolation for merge agent |
| A4 | LiteLLM proxy at `127.0.0.1:4000` has NIM aliases for reviewer roles configured | SC-2/SC-4 | Reviewers fail at dispatch; need to add aliases to LiteLLM config |
| A5 | Brain curator endpoint accepts a `role` tag in the cost-record message for per-role parsing | SC-2 | Per-role ledger parsing won't work; need to verify curator agent message schema |

---

## Open Questions (RESOLVED)

1. **NIM model alias for reviewers (D-05 open detail)** — what exact LiteLLM alias to use for the 8 reviewer roles? Current aliases: `cheap-fast`, `planner-reasoner`, `coder-worker`, `reviewer-model`, `default-worker`. Need a decision before `review-roster.yaml` can be written. Recommendation: use `reviewer-model` as default for all reviewers, with a cheaper fallback (e.g., `cheap-fast`) for stack reviewers per D-09.
   **RESOLVED (09-01 Task 2):** Use `reviewer-model` for all 8 roles; `cheap-fast` as fallback for stack reviewers (python/typescript/reactjs/docs/config) per D-09.

2. **Brain ingest message format for audit log** — `brain_http.call_agent("ingest", message)` takes a free-text message string. How does the Brain ingest agent determine the vault path? Does it parse a prefix like `workshop-audit/{task_id}:` or is there a structured format? This must be confirmed against the Brain ingest agent configuration before writing `append_audit()`.
   **RESOLVED (09-01 Task 3):** Use prefix format `f"workshop-audit/{task_id}: " + json.dumps(payload)` — Brain ingest agent parses the leading path token as the vault key.

3. **Brainstorm HITL mechanism** — The brainstorm stage is conversational (multi-turn). The existing `StageTimeoutForHITL` and `record_hitl_pause` patterns handle single HITL pause points, not multi-turn conversation loops. The brainstorm loop needs a different pattern: Hermes `clarify()` in a loop, not a single exception-based pause. Research how Hermes `clarify()` supports multi-turn within a skill before implementing.
   **RESOLVED (09-03 Task 1):** Use the exit-2 resumption pattern in a loop: emit HITL payload with `hitl_type: "brainstorm"` + `brainstorm_turn` counter, call `sys.exit(2)`. On resume, `workshop_build.py` re-enters the brainstorm stage with the next turn. Loop exits when `state["brainstorm_approved"] == True`. No turn cap (B1-A).

---

## RESEARCH COMPLETE

**Phase:** 09 — Advanced Agent Architecture
**Confidence:** HIGH

### Key Findings

1. `workshop_build.py` is the primary orchestrator and must absorb the bulk of Phase 9 changes: brainstorm stage cursor, wave-2 parallel dispatch, per-role budget check, and audit calls.
2. The current single `review_query()` in `workshop/reviewer.py` can be decomposed — its existing checks map cleanly to the new scope-split reviewers (security checks → security-reviewer, path/spec compliance → correctness-reviewer, compile checks → python-reviewer).
3. `brain_http.py` is already the right shim for audit writes (ingest agent) and cost recording (curator agent) — Phase 9 extends calling patterns, not the shim itself.
4. `workshop/cost.py` needs a per-role layer added on top of the existing daily global circuit breaker — the two systems coexist (daily global cap remains the hard ceiling).
5. The largest implementation complexity is the parallel wave dispatch mechanism — the current `run_stage()` is synchronous; true parallelism requires `ThreadPoolExecutor` or equivalent.
6. `requirements_gate.py` brain pre-query (B7) is the simplest change — direct clone of the `_query_review_memory()` pattern already in `reviewer.py`.
7. Seven new SKILL.md soul files are needed for the reviewer roster — lean/behavioral discipline applies, with severity in the output schema as `Literal["Critical", "Important", "Minor"]`.

### Files Created
`.planning/phases/09-advanced-agent-architecture/09-RESEARCH.md`

### Ready for Planning
Research complete. Planner can now create sub-PLAN.md files for Phase 9.
