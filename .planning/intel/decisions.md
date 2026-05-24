# Synthesized Decisions

source: docs/ingest/PLAN.md (classified: SPEC, precedence: 0, promoted-locked: true)

Note: The classification JSON marks this document as `locked: false`, but the source document contains an explicit "Locked decisions" section (L1–L30) established during a /grill-me session. Per synthesizer instructions, these are promoted to LOCKED status because the document author explicitly designated them as locked architectural decisions for Phase 1.

---

## LOCKED-L1 — Workshop ships as separate sibling repo

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: repo structure
decision: Workshop ships as a separate sibling repo at `~/Documents/Projects/ultra-workshop/`
rationale: Honors original architectural decision; isolates coding-agent infra from Brain's knowledge-layer infra; allows independent versioning/deploy

---

## LOCKED-L2 — Orchestrator framework: Hermes Agent

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: orchestration layer
decision: Workshop orchestrator framework is Hermes Agent (NousResearch), pinned at v0.14.0
rationale: Purpose-built for persistent personal agent with messaging gateways + skill delegation; already has working claude-code skill; ships Telegram/Discord/Slack gateway, FTS5 search, cron scheduler, MCP support

---

## LOCKED-L3 — Brain stays on Agno; workshop talks to it via HTTP only

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: inter-system communication
decision: Brain stays on Agno; workshop is a pure HTTP client of Brain's existing `/agents/{id}/runs` endpoints
rationale: No framework migration on the working Brain

---

## LOCKED-L4 — Exactly one gateway owns Telegram

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: Telegram gateway
decision: Hermes (workshop side) exclusively owns the Telegram gateway. Brain's `uab-telegram.service` is disabled when workshop ships.
rationale: Dual HITL surfaces create approval-prompt confusion and race conditions

---

## LOCKED-L5 — Workshop runs on same Hostinger VPS as Brain (Phase 1)

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: deployment infra
decision: Workshop runs on same Hostinger VPS (`31.97.130.253`) as Brain for Phase 1
rationale: $0 extra infra cost; Phase 1 coder is Aider (low RAM), not OpenHands Docker

---

## LOCKED-L6 — Shared $20/day budget cap

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: cost management
decision: Shared $20/day cap with Brain, tracked in Brain's `vault/_system/cost-ledger.md`. Workshop posts each LLM/coder invocation cost via `POST /agents/curator/runs` with task=`record-cost`.
rationale: Single budget, single ledger per integration principle P4

---

## LOCKED-L7 — Rotate Telegram bot token before deploy

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: security / pre-deploy gate
decision: Rotate Telegram bot token via BotFather `/revoke` before any deploy, then re-register against Hermes gateway
rationale: Token was exposed in a prior session; workshop deploy is the trigger to rotate

---

## LOCKED-L8 — License: MIT

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: licensing
decision: MIT license at repo root
rationale: Matches Brain's effective license and Hermes Agent

---

## LOCKED-L9 — Model-agnostic from day 1 via LiteLLM

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: LLM routing
decision: All LLM calls route through Brain's existing LiteLLM proxy at `127.0.0.1:4000` using 6 aliases: `orchestrator`, `default-worker`, `cheap-worker`, `private-worker`, `cloud-sonnet`, `cloud-groq`
rationale: LM Studio (`private-worker`) for free local edits; cloud models only when warranted; model-agnostic by construction

---

## LOCKED-L10 — Coder = Aider (NOT Claude Code) in Phase 1

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: coder substrate
decision: Phase 1 coder is Aider via new Hermes skill (local impl of Issue #534). Claude Code is disqualified by model-agnostic constraint (L9). OpenHands reserved behind `Coder` adapter for Phase 2.
rationale: Aider routes through LiteLLM natively; architect/editor split gives free internal MoA pattern

---

## LOCKED-L11 — Coordination = Hermes delegate_task (NOT LangGraph) in Phase 1

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: coordination layer
decision: Coordination = Hermes `delegate_task` from a Python skill body. LangGraph is NOT in Phase 1 (v3 revision). LangGraph reserved as Phase 2 opt-in upgrade.
rationale: Phase 1 pipeline is linear; LangGraph machinery is over-engineering; Hermes Level 0 delegation sufficient

---

## LOCKED-L12 — Phase 1 ships 5-role specialist topology

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: specialist topology
decision: 5-role specialist topology via Hermes `delegate_task`: triage → planner → coder → reviewer → pr_opener. Each role is a subagent with its own skill subset and model alias.
rationale: Matches central orchestrator mental model; Hermes spawns isolated subagents

---

## LOCKED-L13 — Skill audit first (Day 1 task)

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: skill management / execution order
decision: Day 1 task is `audit-claude-skills.py` that tags each of ~120 `~/.claude/skills/` entries as `agent-agnostic`, `claude-specific`, or `requires-translation`
rationale: Avoids "copied 50, 40 broken" surprise; informs which Tier 1 skills to port

---

## LOCKED-L14 — Tier 1 skill port scope = ~10 skills + 3 brain-bridge skills

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: skill port scope
decision: Port ~10 curated agent-agnostic skills + 3 new brain-bridge skills (`brain-query`, `brain-ingest`, `brain-research`). Full ecosystem porting deferred until concrete need emerges.
rationale: Curated subset avoids scope creep in Phase 1

---

## LOCKED-L15 — Hermes cron is IN Phase 1 (3 autonomous routines)

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: autonomous routines
decision: 3 autonomous cron routines ship in Phase 1: `daily-research` (07:00), `nightly-tests` (02:00), `bug-scan` (every 4h). `weekly-vault-review` and `daily-digest` REMOVED from workshop — Brain's existing systemd timers cover those.
rationale: v3 revision: user explicitly wants autonomous routines as Phase 1 core capability; Hermes cron is a built-in feature

---

## LOCKED-L16 — GitHub repo private

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: repo visibility
decision: `gh repo create --private` for `caiobellizzi/ultra-workshop`
rationale: Default for personal infra; flip later if useful for others

---

## LOCKED-L17 — Target repo allowlist Phase 1 sandbox baseline

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: execution safety / blast radius
decision: Phase 1 workshop was limited to `caiobellizzi/test-workshop-sandbox` repo until the owner-approved Phase 6 registry expansion (L17-A)
rationale: Zero blast radius on real projects during Phase 1; Phase 6 promotion requires active registry gating and HITL

---

## LOCKED-L18 — GitHub auth = fine-grained PAT scoped to allowlist

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: GitHub authentication
decision: Fine-grained PAT with `repo:write` scoped to `test-workshop-sandbox` until the owner-approved Phase 6 registry auth expansion (L18-A). Upgrade path to GitHub App remains.
rationale: Simpler than GitHub App for Phase 1; Phase 6 broadens scope only for active registry entries with HITL gates

---

## OWNER-L17-A — Multi-repo support unlocked for Phase 6

source: owner decision 2026-05-24 during gsd-import conflict resolution
status: APPROVED
scope: execution safety / blast radius
decision: Workshop may target repositories listed as `active: true` in `/srv/second-brain/_system/workshop-repos.json`. The registry auto-seeds `caiobellizzi/test-workshop-sandbox`; `/repo remove` marks inactive and never deletes GitHub repositories. `/build` and `/fix` reject unknown or inactive repos.
rationale: Phase 4 sandbox pipeline is complete; repo targeting is now a bounded follow-up phase with explicit registry gating.

---

## OWNER-L18-A — GitHub auth/security expanded for Phase 6

source: owner decision 2026-05-24 during gsd-import conflict resolution
status: APPROVED
scope: GitHub authentication
decision: `GITHUB_PAT` on the VPS may cover registered repos with the minimum permissions needed for view, clone, branch push, PR creation, and private repo creation. Repo creation, registration, removal, git push, and PR creation remain HITL-gated through the single allowed Telegram chat.
rationale: The registry workflow requires broader GitHub API access than the sandbox-only PAT; HITL and active-registry checks are the compensating controls until GitHub App auth replaces the PAT.

---

## LOCKED-L19 — PR description format

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: PR output format
decision: PR description generated by `reviewer` node from `task_ledger.md` + diff summary. Format = BLUF + Changes + Test plan + Co-Authored-By line.
rationale: Only reviewer has both goal AND diff context

---

## LOCKED-L20 — Branch naming convention

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: git conventions
decision: Branch naming = `workshop/<short-id>-<slug>` (4-char hex ID + lowercased dashed slug, max 30 chars)
rationale: Unique by ID, scannable by slug

---

## LOCKED-L21 — Skill audit script = tag + auto-translate (option C)

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: skill translation strategy
decision: Auto-translate pass rewrites `Read`/`Edit`/`Write`/`Bash`/`Grep`/`Glob` to Hermes equivalents; outputs to `~/.hermes/skills/translated/`. Un-translatable tools (`TaskCreate`/`AskUserQuestion`/`Skill`/`ExitPlanMode`) tagged `requires-manual-port`. Tool Translation Map in Appendix E defines substitutions.
rationale: User override of plan recommendation; broadens portable corpus from ~10 to ~30-50 skills with conservative substitution

---

## LOCKED-L22 — LangGraph removed from Phase 1

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: coordination layer
decision: LangGraph (StateGraph, conditional edges, SqliteSaver) is NOT in Phase 1. Reserved as Phase 2 opt-in upgrade if oscillation or complex branching emerges.
rationale: v3 stress-test outcome: Hermes `delegate_task` + Python skill-body for-loops cover Phase 1's linear pipeline without LangGraph over-engineering

---

## LOCKED-L23 — 3 autonomous cron routines, no overlap with Brain timers

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: cron topology
decision: Workshop runs exactly 3 cron routines: `daily-research` (07:00), `nightly-tests` (02:00), `bug-scan` (every 4h). Brain's 3 existing timers (monitor/digest/review) stay unchanged. No overlap.
rationale: Cron division of labor per integration principle P5

---

## LOCKED-L24 — Brain ↔ Workshop integration model: "one system, two tiers, vault as connective tissue"

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: integration architecture
decision: Brain and Workshop are one personal AI system with two tiers connected by the vault. File-based signaling via vault frontmatter is the structured communication channel. No event bus. 5 integration principles, 7 connection types, frontmatter vocabulary, and 10 integration decisions (D1–D10) are locked.
rationale: v3 stress-test central outcome; derives all integration decisions

---

## LOCKED-L25 — Routing strategy: split by invocation context

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: LLM routing / model selection
decision: Interactive `/build` and `/fix` use `private-worker` (LM Studio). Autonomous cron routines (`daily-research`, `nightly-tests`, `bug-scan`) use `cloud-groq` directly.
rationale: Mac is asleep ~14h/day; direct cloud-groq routing for cron avoids 15-min fallback chain; interactive uses local because Mac is awake when user triggers

---

## LOCKED-L26 — Tighten LiteLLM private-worker timeout 300s → 30s

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: LiteLLM configuration
decision: Update `deploy/litellm/config.yaml` to set `private-worker` timeout to 30s. Applies to Brain too (shared proxy). Rsync to VPS as part of workshop deploy.
rationale: Cuts worst-case fallback time from ~15 min to ~60s; acceptable for both Brain and Workshop

---

## LOCKED-L27 — Vault sync = hosted GitHub remote, Obsidian-Git + VPS cron

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: vault synchronization
decision: `caiobellizzi/second-brain` private GitHub repo as vault remote. Mac uses Obsidian-Git plugin (auto-pull + auto-push every 5 min). VPS runs `scripts/git-sync.sh push && pull` via cron every 5 min. Activate as Day-1 task BEFORE skill audit and before workshop deploy.
rationale: Without sync, Workshop writes on VPS are invisible on Mac Obsidian; integration design breaks

---

## LOCKED-L28 — Two-tier signaling vocabulary for vault frontmatter

source: docs/ingest/PLAN.md §Locked decisions + §Frontmatter signaling vocabulary
status: LOCKED
scope: cross-system signaling protocol
decision: `workshop.suggested_action: <verb>` = set by autonomous sources, NOT dispatched. `workshop.action: <verb>` + `workshop.confirmed: true` = set by humans OR Brain (only for self-confirming verbs like `post-to-telegram`) → dispatched by bug-scan. `research` actions from `vault/_system/research-queue.md` are implicitly confirmed.
rationale: Eliminates overnight HITL ping-flood; autonomous discoveries surface in Brain's daily-digest for human review

---

## LOCKED-L29 — Quiet-hours dispatch deferral (22:00–07:00)

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: dispatch timing / UX safety
decision: Bug-scan polls normally during 22:00–07:00 local but defers any dispatch that would emit a Telegram approval prompt until 07:01. Zero-HITL verbs (e.g., `post-to-telegram`) dispatch immediately regardless of quiet hours.
rationale: Belt-and-suspenders safety on top of L28's vocabulary split; prevents late-night pings

---

## LOCKED-L30 — Structured specialist outputs via Pydantic

source: docs/ingest/PLAN.md §Locked decisions
status: LOCKED
scope: specialist output schema
decision: Each specialist role returns a typed Pydantic object: `Plan` (planner), `Diff` (coder), `Review` (reviewer), `IngestResult` (brain-recorder). Defined in `workshop/types.py`. Orchestrator validates schema; retries with explicit reminder on parse failure (max 2 retries/role). `delegate_typed()` helper in `workshop/orchestrator.py`.
rationale: Real multi-agent depth via role-specific tools + model tiers + orchestrator-mediated handoffs; Pydantic schemas are foundation for Phase 2 enhancements

---

## Integration Decisions (D1–D10) — also LOCKED per L24

source: docs/ingest/PLAN.md §10 Integration decisions

D1: Workshop vault access = read everywhere, write only to `_system/workshop-*/` directly; writes elsewhere via Brain.ingest (HITL-gated)
D2: Cost ledger = `/srv/second-brain/_system/cost-ledger.md`; both systems append with `source:` field; both circuit-break against this single file
D3: Brain owns: monitor (hourly), digest (daily 20:00), review (weekly Sun 18:00). Workshop owns: daily-research (07:00), nightly-tests (02:00), bug-scan (every 4h)
D4: Trust policy: symlink `/opt/ultra-workshop/workshop/trust_shared.py → /opt/ultra-agents-brain/ultra_brain/trust.py`
D5: Skill registry: `vault/_system/skill-registry.md` maintained by Brain's curator (Phase 1.5); Workshop planner reads it
D6: Cross-system signaling via frontmatter vocabulary; documented in `vault/_system/integration-contract.md`
D7: Brain NEVER makes HTTP calls to Workshop; all Brain→Workshop signals go via vault frontmatter + polling
D8: Workshop exclusively owns Telegram gateway post-deploy; Brain's `uab-telegram.service` stays disabled
D9: Workshop task ledgers at `~/.ultra-workshop/tasks/<id>/`; compact ADR written to vault on completion; archived at 30 days
D10: Phase 1 MUST close the loop — Flows A, B, D, E mandatory; Flow C is SHOULD
