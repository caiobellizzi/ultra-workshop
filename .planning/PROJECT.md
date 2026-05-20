# Project: ultra-workshop

**Owner:** Caio Bellizzi
**Created:** 2026-05-20
**Repository:** caiobellizzi/ultra-workshop (private)
**Runtime:** Python 3.11, Hermes Agent v0.14.0, uv-managed
**VPS:** Hostinger srv1381850.hstgr.cloud (31.97.130.253) — same as Brain
**Sibling project:** ultra-agents-brain (Brain Tier 1, deployed, Agno 2.6.7)

---

## Core Value

An autonomous coding/PR/deploy agent team running on the same VPS as Brain, reachable via Telegram, that takes a task description and produces a reviewed pull request — with human approval as the only gate before any code lands.

---

## Problem

Brain (ultra-agents-brain) is running and producing vault content. The next tier — autonomous code generation, test execution, and PR creation — does not exist yet. Every code change still requires full manual developer attention.

---

## Solution

Workshop (ultra-workshop) is Tier 2 of the personal AI system. It listens on Telegram, orchestrates a 5-role specialist pipeline (triage → planner → coder → reviewer → pr_opener) using Hermes Agent's `delegate_task` primitive, and pauses for human HITL approval before any PR is pushed. It also runs 3 autonomous cron routines (daily-research, nightly-tests, bug-scan) and closes the loop with Brain via vault frontmatter signaling and HTTP calls to Brain's Agno endpoints.

---

## Constraints

- **Hermes Agent v0.14.0 pinned** — no upgrade without explicit re-evaluation
- **No LangGraph in Phase 1** — Hermes `delegate_task` + Python for-loops only; reserved Phase 2 opt-in
- **Coder = Aider only** — routes through LiteLLM natively; Claude Code excluded (model-agnostic constraint)
- **Model-agnostic** — all LLM calls via LiteLLM proxy at `127.0.0.1:4000`; 6 aliases: `orchestrator`, `default-worker`, `cheap-worker`, `private-worker`, `cloud-sonnet`, `cloud-groq`
- **Python 3.11** — required by Hermes; venv via `uv`
- **Single Telegram gateway** — Hermes owns it; `uab-telegram.service` must be dead before deploy
- **Phase 1 target repo = `caiobellizzi/test-workshop-sandbox` ONLY** — fine-grained PAT scoped to this repo
- **HITL required before any git push or PR creation** — no auto-merge, no auto-deploy
- **$20/day shared budget** with Brain — circuit breaker at $18 (self-cancel), $20 (refuse LLM calls)
- **Vault write zones** — workshop writes directly only to `_system/workshop-*/`; all other vault writes via Brain.ingest
- **HTTP one-way: Workshop → Brain** — Brain never calls Workshop; Brain→Workshop signals are vault frontmatter + polling
- **No event bus** — file-based signaling only; all cross-system state is `rg`-able from vault
- **Hard retry caps** — max_replans=3, reviewer→coder max 2 cycles, Pydantic parse retry max 2 per role
- **Skill translation safety** — auto-translate output to `~/.hermes/skills/translated/` only; never auto-promote to production
- **Branch protection** — all work on `workshop/<short-id>-<slug>` branches; never touch `main` directly
- **No excluded patterns** — no group-chat/debate (sycophancy cascades), no multi-coder auto-commit, no OpenHands Docker on shared VPS, no circular Hermes→Agno→Hermes calls, no cross-model MoA

---

## Decisions

<decisions>

### LOCKED Architectural Decisions (L1–L30)

These decisions were established during a /grill-me session and are LOCKED for Phase 1. They may only be changed by explicit owner decision with documented rationale.

| ID | Decision | Scope |
|----|----------|-------|
| L1 | Workshop ships as separate sibling repo at `~/Documents/Projects/ultra-workshop/` | repo structure |
| L2 | Orchestrator = Hermes Agent v0.14.0 | orchestration layer |
| L3 | Brain stays on Agno; workshop talks to it via HTTP only (`POST :7000/agents/{id}/runs`) | inter-system comms |
| L4 | Hermes (workshop) exclusively owns Telegram gateway; Brain's `uab-telegram.service` disabled on deploy | Telegram gateway |
| L5 | Workshop runs on same Hostinger VPS as Brain for Phase 1 ($0 extra infra) | deployment infra |
| L6 | Shared $20/day cap; workshop posts costs via `POST /agents/curator/runs` task=`record-cost` | cost management |
| L7 | Rotate Telegram bot token via BotFather `/revoke` before any deploy | security / pre-deploy gate |
| L8 | MIT license | licensing |
| L9 | All LLM calls via LiteLLM proxy at `127.0.0.1:4000`; 6 aliases | LLM routing |
| L10 | Coder = Aider (NOT Claude Code) — routes through LiteLLM natively | coder substrate |
| L11 | Coordination = Hermes `delegate_task` (NOT LangGraph) in Phase 1 | coordination layer |
| L12 | 5-role specialist topology: triage → planner → coder → reviewer → pr_opener | specialist topology |
| L13 | Day 1 task = `audit-claude-skills.py` (tag + auto-translate) | skill management |
| L14 | Tier 1 port scope = ~10 agent-agnostic skills + 3 brain-bridge skills | skill port scope |
| L15 | 3 autonomous cron routines in Phase 1: daily-research (07:00), nightly-tests (02:00), bug-scan (every 4h) | autonomous routines |
| L16 | `gh repo create --private` for `caiobellizzi/ultra-workshop` | repo visibility |
| L17 | Phase 1 target repo allowlist = `caiobellizzi/test-workshop-sandbox` ONLY | blast radius |
| L18 | GitHub auth = fine-grained PAT scoped to allowlist; upgrade to GitHub App in Phase 2 | GitHub auth |
| L19 | PR description format = BLUF + Changes + Test plan + Co-Authored-By (generated by reviewer from task_ledger + diff) | PR output format |
| L20 | Branch naming = `workshop/<short-id>-<slug>` (4-char hex ID + lowercased dashed slug, max 30 chars) | git conventions |
| L21 | Skill audit = tag + auto-translate to `~/.hermes/skills/translated/`; Tool Translation Map (Appendix E) | skill translation |
| L22 | LangGraph NOT in Phase 1; reserved Phase 2 opt-in | coordination layer |
| L23 | Exactly 3 cron routines; no overlap with Brain's 3 timers | cron topology |
| L24 | Integration model: "one system, two tiers, vault as connective tissue" | integration architecture |
| L25 | Interactive `/build`/`/fix` → `private-worker`; autonomous cron → `cloud-groq` directly | LLM routing |
| L26 | LiteLLM `private-worker` timeout 30s (down from 300s); rsync to VPS on deploy | LiteLLM config |
| L27 | Vault sync = `caiobellizzi/second-brain` private GitHub remote + Obsidian-Git (Mac) + VPS cron every 5 min | vault synchronization |
| L28 | Two-tier signaling: `workshop.suggested_action` (not dispatched) vs `workshop.action` + `workshop.confirmed: true` (dispatched) | frontmatter signaling |
| L29 | Quiet-hours dispatch deferral 22:00–07:00 local; zero-HITL verbs dispatch immediately regardless | dispatch timing |
| L30 | Specialist outputs = Pydantic schemas in `workshop/types.py`; `delegate_typed()` in `workshop/orchestrator.py` | specialist output schema |

### Integration Decisions (D1–D10) — also LOCKED per L24

| ID | Decision |
|----|----------|
| D1 | Workshop vault: read everywhere, write only to `_system/workshop-*/` directly; elsewhere via Brain.ingest |
| D2 | Cost ledger = `/srv/second-brain/_system/cost-ledger.md`; `source:` field distinguishes entries |
| D3 | Brain owns: monitor (hourly), digest (daily 20:00), review (weekly Sun 18:00). Workshop owns: daily-research (07:00), nightly-tests (02:00), bug-scan (every 4h) |
| D4 | Trust policy: symlink `/opt/ultra-workshop/workshop/trust_shared.py → /opt/ultra-agents-brain/ultra_brain/trust.py` |
| D5 | Skill registry: `vault/_system/skill-registry.md` maintained by Brain's curator (Phase 1.5); Workshop planner reads it |
| D6 | Cross-system signaling via frontmatter vocabulary; documented in `vault/_system/integration-contract.md` |
| D7 | Brain NEVER makes HTTP calls to Workshop; all Brain→Workshop signals via vault frontmatter + polling |
| D8 | Workshop exclusively owns Telegram gateway post-deploy; Brain's `uab-telegram.service` stays disabled |
| D9 | Workshop task ledgers at `~/.ultra-workshop/tasks/<id>/`; compact ADR written to vault on completion; archived at 30 days |
| D10 | Phase 1 MUST close the loop — Flows A, B, D, E mandatory; Flow C is SHOULD |

</decisions>

---

## Phase 2 Reservations (Do Not Build in Phase 1)

- LangGraph StateGraph + SqliteSaver + conditional edges (opt-in upgrade if oscillation emerges)
- OpenHands V1 SDK behind `Coder` ABC (requires separate VPS with Docker)
- Broadcast review board (N=3 narrow reviewers: security, tests, architecture)
- MoA / Self-MoA inside reviewer role
- Multi-repo allowlist expansion (after 10+ clean PRs on sandbox)
- GitHub App auth (replaces fine-grained PAT)
- Discord, WhatsApp, Slack adapters

---

## Repo Structure

```
ultra-workshop/
├── README.md
├── LICENSE (MIT)
├── pyproject.toml
├── .env.example
├── hermes-config/
│   ├── hermes.toml
│   ├── gateway-telegram.toml
│   └── mcps.toml
├── skills/
│   ├── aider/SKILL.md
│   ├── brain-query/SKILL.md
│   ├── brain-ingest/SKILL.md
│   ├── brain-research/SKILL.md
│   ├── workshop-build/SKILL.md
│   ├── workshop-fix/SKILL.md
│   └── [~10 Tier-1 ports]
├── workshop/
│   ├── __init__.py
│   ├── orchestrator.py       ← delegate_typed() helper (NOT graph.py — L22)
│   ├── state.py              ← TypedDict
│   ├── coder.py              ← Coder ABC + AiderAdapter
│   ├── types.py              ← Pydantic: Plan, Diff, Review, IngestResult
│   ├── ledger.py             ← two-ledger writer
│   ├── cost.py               ← circuit breaker
│   └── nodes/
│       ├── triage.py
│       ├── planner.py
│       ├── coder.py
│       ├── reviewer.py
│       └── pr_open.py
├── scripts/
│   ├── audit-claude-skills.py
│   ├── smoke-build.py
│   └── install.sh
├── deploy/
│   └── systemd/uws-hermes.service
└── tests/
    └── test_pipeline.py
```

---

## Brain HTTP Contract

Brain Agno endpoints called by Workshop:
- `POST /agents/query/runs` — vault context for coding task
- `POST /agents/research/runs` — multi-angle research
- `POST /agents/ingest/runs` — write ADR/lesson to vault (HITL-gated on Brain side)
- `POST /agents/curator/runs` — cost-ledger updates (`message=record-cost&amount=X&task=Y`)
- `POST /agents/{id}/runs/{run_id}/continue` — resume paused Brain agent
- `GET /health` — liveness check before any task

Auth: none (single-tenant, same VPS loopback). Future: `Authorization: Bearer` from Hermes skills if systems separate.

---

## Key Metrics

- Per-build cost target: ~$0.047 (~57K tokens)
- Daily budget: $20 shared with Brain; ~420 builds ceiling; realistic 3-10/day
- Local model (`private-worker`) must handle ≥80% of token volume (V17)
- Phase 1 verification: V1–V24 must all pass before tagging v0.1.0
