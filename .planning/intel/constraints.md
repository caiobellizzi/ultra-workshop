# Synthesized Constraints

source: docs/ingest/PLAN.md (classified: SPEC, precedence: 0)

---

## CONSTRAINT-stack-orchestrator

source: docs/ingest/PLAN.md §Stack (locked for Phase 1)
type: protocol
title: Orchestrator — Hermes Agent v0.14.0 pinned
content: Hermes Agent (NousResearch) pinned at v0.14.0. Central orchestrator + gateway + skill runtime + MCP host + cron scheduler in a single process. No version upgrade without explicit re-evaluation.

---

## CONSTRAINT-stack-no-langgraph

source: docs/ingest/PLAN.md §Stack (locked for Phase 1)
type: protocol
title: No LangGraph in Phase 1
content: LangGraph is explicitly excluded from Phase 1. All coordination is Hermes `delegate_task` + Python skill-body for-loops. LangGraph reserved as Phase 2 opt-in upgrade if oscillation or complex-branching failure modes emerge. Pin for Phase 2 consideration: `langgraph>=0.2,<0.3`.

---

## CONSTRAINT-stack-coder-aider

source: docs/ingest/PLAN.md §Stack (locked for Phase 1)
type: protocol
title: Coder substrate = Aider (aider-chat latest stable)
content: Aider invoked as subprocess by a Hermes skill. Architect model: `cloud-sonnet`. Editor model: `private-worker` (LM Studio gemma-4-e4b via LM Link). Flags: `--yes-always --no-stream --message <task>`. Claude Code is disqualified by model-agnostic constraint. OpenHands reserved for Phase 2 behind `Coder` ABC.

---

## CONSTRAINT-stack-llm-gateway

source: docs/ingest/PLAN.md §Stack (locked for Phase 1)
type: api-contract
title: LiteLLM proxy at 127.0.0.1:4000 — 6 aliases
content: All LLM calls MUST use Brain's existing LiteLLM proxy at `127.0.0.1:4000/v1`. Aliases: `orchestrator`, `default-worker`, `cheap-worker`, `private-worker`, `cloud-sonnet`, `cloud-groq`. No direct API calls to Anthropic/OpenAI/etc. `private-worker` timeout must be set to 30s (L26).

---

## CONSTRAINT-stack-state-stores

source: docs/ingest/PLAN.md §Stack (locked for Phase 1)
type: schema
title: Exactly two state stores; no third store in Phase 1
content: Hermes FTS5 at `~/.hermes/state.db` (sessions, skill memory, cron history). Brain SqliteDb at `/var/lib/uab/` (Agno session + HITL state, unchanged). Per-task ledgers are files under `~/.ultra-workshop/tasks/<id>/` — NOT DB-backed. LangGraph SqliteSaver is NOT introduced.

---

## CONSTRAINT-stack-python

source: docs/ingest/PLAN.md §Stack (locked for Phase 1)
type: nfr
title: Python 3.11 (matches Hermes requirement), venv via uv
content: Python version 3.11 required by Hermes installer. Virtual environment managed via `uv`. Do not use Python 3.12+ unless Hermes explicitly supports it.

---

## CONSTRAINT-model-agnostic

source: docs/ingest/PLAN.md §Key invariants
type: nfr
title: Model-agnostic by construction — no direct Anthropic dependency
content: All LLM calls go through LiteLLM aliases. No hardcoded model names from a single provider. Claude Code is explicitly excluded as a coder substrate (would introduce Anthropic-only dependency). Local model (`private-worker` = gemma-4-e4b via LM Studio) must handle ≥80% of token volume.

---

## CONSTRAINT-single-telegram-gateway

source: docs/ingest/PLAN.md §Key invariants
type: protocol
title: One Telegram gateway — Hermes only
content: Exactly one process may own the Telegram long-poll at any time. `uab-telegram.service` (Brain) must be `inactive (dead)` before `uws-hermes.service` is enabled. Verified by V15. Dual HITL surfaces are a hard anti-pattern in this design.

---

## CONSTRAINT-blast-radius

source: docs/ingest/PLAN.md §LOCKED-L17
type: nfr
title: Phase 1 target repo allowlist = caiobellizzi/test-workshop-sandbox ONLY
content: Workshop may only push branches and open PRs against `caiobellizzi/test-workshop-sandbox`. GitHub auth is a fine-grained PAT scoped to this repo only (`repo:write`). Multi-repo support is Phase 2+. All task branches follow naming `workshop/<short-id>-<slug>`. Never touch `main` directly.

---

## CONSTRAINT-hitl-on-push

source: docs/ingest/PLAN.md §Key invariants
type: protocol
title: HITL required before any git push or PR creation
content: Every flow that produces a PR must pause at the pr_opener role and emit a Hermes clarify callback → Telegram inline buttons. Auto-merge and auto-deploy are Phase 1 WONT. No code lands in any repo without user approval.

---

## CONSTRAINT-budget-circuit-breaker

source: docs/ingest/PLAN.md §Cost envelope + WS-019
type: nfr
title: $20/day shared budget; circuit breaker at $18
content: Daily LLM spend cap = $20/day shared between Brain and Workshop. Circuit breaker MUST be checked before every LLM call in every node and cron routine. At $18 spent: cron routines self-cancel + emit one Telegram warning. At $20: all LLM calls refused. Ledger: `vault/_system/cost-ledger.md`. Per-build cost estimate: ~$0.047 (57K tokens).

---

## CONSTRAINT-retry-caps

source: docs/ingest/PLAN.md §Key invariants + §Risks
type: nfr
title: Hard retry caps on all loops
content: Planner node: max_replans=3. Reviewer→coder retry loop: max 2 attempts. Pydantic parse failure retry: max 2 per role. Hermes delegation depth: max 2 (Level 0 only; no recursive delegate_task). These caps prevent the infinite-replan catastrophe documented in arXiv:2511.03690.

---

## CONSTRAINT-vault-write-zones

source: docs/ingest/PLAN.md §Integration Decision D1
type: protocol
title: Vault write access restricted by zone
content: Workshop may write directly ONLY to `_system/workshop-*/`. Writes to any other vault path MUST go via Brain.ingest (HITL-gated). Brain reads all vault paths; writes to its own zones. Disjoint write zones keep git conflicts rare; ff-only merge fails loudly on conflict.

---

## CONSTRAINT-brain-http-one-way

source: docs/ingest/PLAN.md §Integration Decision D7
type: api-contract
title: HTTP between systems is one-way only: Workshop → Brain
content: Workshop calls Brain via HTTP (`POST :7000/agents/{id}/runs`). Brain NEVER makes HTTP calls to Workshop. All Brain→Workshop signals go via vault frontmatter + Workshop's polling crons. One-way HTTP = small failure surface.

---

## CONSTRAINT-no-event-bus

source: docs/ingest/PLAN.md §Integration Principles P3
type: protocol
title: No event bus; file-based signaling only
content: Cross-system requests are vault frontmatter tags + filesystem polling. No Kafka, Redis pub/sub, or custom event bus. Simple, debuggable, survives restarts. The entire Brain↔Workshop conversation must be `rg`-able from one vault directory.

---

## CONSTRAINT-cron-no-overlap

source: docs/ingest/PLAN.md §Integration Principles P5
type: protocol
title: Cron division of labor — no overlap between Brain and Workshop timers
content: Brain owns: uab-monitor (hourly), uab-digest (daily 20:00), uab-review (weekly Sun 18:00). Workshop owns: daily-research (07:00), nightly-tests (02:00), bug-scan (every 4h). No workshop cron may duplicate a Brain timer's purpose. Verified by V24.

---

## CONSTRAINT-systemd-dependency

source: docs/ingest/PLAN.md §WS-001
type: protocol
title: uws-hermes.service must declare After=uab-brain.service
content: Workshop's systemd unit must not start before Brain is up. Pattern matches `uab-brain.service` in `ultra-agents-brain`. Brain's VPS address: `31.97.130.253`.

---

## CONSTRAINT-skill-translation-safety

source: docs/ingest/PLAN.md §Appendix E — safety rules
type: protocol
title: Skill audit/translate output must never shadow production Hermes skills
content: Auto-translate output MUST go to `~/.hermes/skills/translated/<name>/` only. Promotion to `~/.hermes/skills/<name>/` requires explicit user action (manual `cp -r` after smoke-test). A broken translation may never silently override a working skill.

---

## CONSTRAINT-no-excluded-patterns

source: docs/ingest/PLAN.md §Anti-patterns the plan explicitly avoids
type: protocol
title: Excluded architectural patterns (hard exclusions for Phase 1)
content:
  - Group chat / debate pattern (arXiv:2604.02668 sycophancy cascades): DO NOT USE
  - Multi-coder auto-committing to same repo simultaneously: DO NOT USE
  - Heavy Docker sandbox (OpenHands V1) on the shared 4GB VPS in Phase 1: DO NOT USE
  - Circular agent calls Hermes → Agno → Hermes via MCP (no infinite-loop circuit breaker): DO NOT USE
  - Mixing different-capability models in MoA (2025 research shows it hurts): DO NOT USE

---

## CONSTRAINT-branch-protection

source: docs/ingest/PLAN.md §Risks
type: protocol
title: All workshop tasks run on feature branches; never touch main directly
content: Branch naming: `workshop/<short-id>-<slug>`. Approval gate (HITL) required before push. Main branch of any allowed repo may not be directly committed to by any Workshop agent or cron routine.
