# Synthesized Context

source: docs/ingest/PLAN.md (classified: SPEC, precedence: 0)

---

## Topic: Project origin and timing

source: docs/ingest/PLAN.md §Context
Brain (`ultra-agents-brain` v1.0) finished Wave 4 deployment on 2026-05-19 — AgentOS + Telegram + 3 systemd timers running on Hostinger VPS `srv1381850.hstgr.cloud` (31.97.130.253). The original plan deferred `ultra-workshop` (Tier 2 — autonomous coding/PR/deploy agent team) until Brain had run daily for 2–4 weeks. The owner elected to start workshop now, while Brain's architecture is fresh in mind; the actual coding work can still wait until Brain has produced meaningful vault content.

---

## Topic: Plan revision history

source: docs/ingest/PLAN.md §header revision history
- v1: Initial plan — Hermes + Claude Code subprocess + minimal vertical slice (single coder, no graph)
- v2: Post-first-grill — model-agnostic constraint → Aider replaces Claude Code; LangGraph adopted for specialist coordination; Phase 1 ships 4-node specialist topology; ~120-skill audit pass added
- v3: Post-second-grill — LangGraph REMOVED (over-engineering for Phase 1's linear pipeline); Hermes `delegate_task` covers coordination; autonomous routines promoted into Phase 1 scope (daily-research, weekly-review, nightly-tests, bug-scan, daily-digest via Hermes cron). Phase 2 reserves LangGraph as opt-in upgrade.

Plan status at ingest: Draft v3 (post-stress-test), awaiting approval. Owner: Caio Bellizzi.

---

## Topic: Brain HTTP surface (workshop's contract with Brain)

source: docs/ingest/PLAN.md §Appendix D
Brain Agno endpoints called by Workshop (default Agno 2.6.7 routes):
- `POST /agents/query/runs` — get vault context for a coding task
- `POST /agents/research/runs` — trigger multi-angle research
- `POST /agents/ingest/runs` — write ADR / lesson learned back to vault (HITL-gated)
- `POST /agents/curator/runs` — cost-ledger updates (`message=record-cost&amount=X&task=Y`)
- `POST /agents/{id}/runs/{run_id}/continue` — resume a paused Brain agent
- `GET /health` — liveness check before any task starts

Auth: none today (single-tenant, same VPS loopback). If Workshop moves to separate VPS: enable Agno `os_security_key` + `Authorization: Bearer` header from Hermes skills.

VAULT_ROOT resolves via: `UAB_VAULT_PATH` → `SECOND_BRAIN_DIR` → `./vault`. PARA layout: `00-Projects/`, `01-Areas/`, `02-Resources/`, `03-Archives/`, `Inbox/`, `_system/`. Workshop writes only to `_system/workshop-adrs/` and `_system/cost-ledger.md` (via Brain's ingest agent).

---

## Topic: Multi-agent patterns research summary

source: docs/ingest/PLAN.md §Appendix A
10 patterns evaluated. Workshop verdicts:
- P1 Workflow-first + Coordinate Team: USE as outer skeleton
- P2 Tasks mode / Planner-loop (ReAct): USE as inner planner, cap 3 replans
- P3 Broadcast Review Board: DEFER to Phase 2 (N=3 narrow reviewers: security, tests, architecture)
- P4 Generator + Critic (Self-Refine): USE inside code stage, cap 2 cycles per file
- P5 Router: USE at entrance (classify build/fix/research/chat)
- P6 Graph / State Machine: Phase 2 if complexity warrants; Phase 1 uses Hermes's own loop
- P7 Blackboard: implicit via Hermes FTS5 + task ledger; don't build standalone
- P8 MoA / Self-MoA: DEFER; single-model Self-MoA only inside Review, Phase 2+
- P9 Group chat / Debate: DO NOT USE — sycophancy cascades (arXiv:2604.02668), quadratic cost, no termination guarantee
- P10 Swarm: Phase 2 upgrade (LangGraph Swarm if specialist topology proves valuable)

Key research findings:
- Representational collapse in LLM committees: effective rank ~2.17/3.0 even with N=3 reviewers (arXiv:2604.03809)
- Routing collapse: as cost budget rises, routers default to most expensive model (arXiv:2602.03478)
- Self-MoA outperforms cross-model MoA by 6.6pp on AlpacaEval (arXiv:2502.00674) — mixing weak models hurts
- Infinite-replan catastrophe: Claude Code sub-agent consumed 27M tokens in 4.6h without termination (GitHub issue #15909)

---

## Topic: Aider composition details

source: docs/ingest/PLAN.md §Appendix B
Composition chosen: Hermes (orchestrator) + Agno Brain via HTTP + Aider as coder subprocess.

Aider selection rationale:
- Architect/editor split = free internal MoA (one process, two LLM calls)
- Routes through LiteLLM natively (model-agnostic)
- tree-sitter RepoMap for code context
- Hermes Issue #534 is unimplemented; must be written locally

OpenHands V1 deferred: 70+ deps, optional Docker, 4GB minimum RAM = risky on shared 4GB VPS. Use only when sandboxed untrusted-code execution becomes a real need (separate VPS required).

Multi-coder MoA (OpenHands + Aider + Claude Code together): operationally brittle — three subprocess chains, shared git tree races, triply complex error handling. Rejected for Phase 1.

---

## Topic: Real-world architecture primitives adopted

source: docs/ingest/PLAN.md §Appendix C
Five primitives stolen from real-world systems:
1. Magentic-One two-ledger pattern — `task_ledger.md` (goal + plan) + `progress_log.jsonl` (executed actions). Source: Microsoft Research arXiv:2411.04468.
2. OpenHands V1 event-sourcing — append-only logs as source of truth; replay/recovery free. Source: arXiv:2511.03690.
3. Manus progressive skill disclosure — three-level skill loading (metadata / instructions / resources); minimal context waste. Source: arXiv:2505.02024.
4. Claude Agent SDK PreToolUse hook for HITL — Hermes's `clarify` callback fills same role.
5. mini-SWE-agent minimalism — start bash-only, add tools only when bash demonstrably fails.

---

## Topic: Cost envelope and model routing

source: docs/ingest/PLAN.md §Cost envelope
Per `/build` task cost breakdown:
- triage: cheap-worker (Haiku-class), 1K tokens, ~$0.001
- planner: cloud-sonnet (Sonnet 4.5), 10K tokens, ~$0.020
- coder architect: cloud-sonnet, 10K tokens, ~$0.020
- coder editor: private-worker (LM Studio gemma-4-e4b), 30K tokens, $0.000 (local)
- reviewer: default-worker (Haiku-class), 5K tokens, ~$0.005
- pr_open: cheap-worker, 1K tokens, ~$0.001
- Total per build: ~57K tokens, ~$0.047

At $20/day cap: ~420 builds/day ceiling. Realistic usage 3-10/day = $0.14-$0.47/day.

Routing strategy (L25):
- Interactive `/build` `/fix`: `private-worker` (LM Studio, Mac-local)
- Autonomous cron routines: `cloud-groq` directly (Mac asleep ~14h/day; avoid 15-min fallback chain)

---

## Topic: Verification matrix (Phase 1 done-criteria)

source: docs/ingest/PLAN.md §Verification matrix
24 verifications (V1–V24) gate Phase 1 completion. Critical path tests:
- V1: `systemctl status uws-hermes` → active
- V2: Bot replies within 5s
- V7: HITL round-trip with inline buttons + Approve/Reject
- V8: Full /build → PR URL in Telegram within ~5 min
- V13: Cost cap enforced — refuses with "budget exhausted"
- V14: Checkpoint resume after mid-flow restart
- V15: `uab-telegram` is dead
- V17: ≥80% tokens via private-worker confirmed in cost ledger
- V18–V24: Integration flows (A, B, D, E), shared ledger, trust symlink, integration contract, no cron overlap

---

## Topic: Risks

source: docs/ingest/PLAN.md §Risks and mitigations
Key risks and mitigations:
- VPS RAM exhaustion (High): Phase 1 coder is Aider subprocess (~200MB) not OpenHands Docker. Monitor `free -h` after each /build. Add 2GB swap if needed.
- Dual HITL surface confusion (High): L4 + V15 enforce single gateway.
- Aider model output drift (Medium): architect (cloud-sonnet) vs editor (gemma-4-e4b) mismatch can produce unrealizable diffs. Mitigation: log Aider tokens+cost to ledger; fall back to cloud-sonnet editor if local model fails N times.
- Cost runaway from infinite replan (Medium): hard cap max_replans=3; daily budget circuit breaker in workshop/cost.py.
- Bot token leaked again (Medium): .env in .gitignore, never commit.
- LangGraph API churn (Medium): Pin `langgraph>=0.2,<0.3`. (Note: LangGraph excluded from Phase 1 per L22; this applies if Phase 2 upgrade is triggered.)
- Hermes V0→V1 migration drift (Medium): Pin v0.14.0 exactly.

---

## Topic: Repo tree (post-bootstrap)

source: docs/ingest/PLAN.md §Repo tree
Target repo structure after Phase 1 bootstrap:
```
~/Documents/Projects/ultra-workshop/
├── README.md
├── PLAN.md
├── LICENSE (MIT)
├── pyproject.toml
├── .env.example (TELEGRAM_BOT_TOKEN, ALLOWED_CHAT_IDS, BRAIN_BASE_URL, LITELLM_BASE_URL)
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
│   └── [~10 Tier-1 ports from ~/.claude/skills/]
├── workshop/
│   ├── __init__.py
│   ├── graph.py (NOTE: no LangGraph in Phase 1 per L22; this becomes orchestrator.py)
│   ├── state.py (TypedDict)
│   ├── coder.py (Coder ABC + AiderAdapter)
│   ├── types.py (Pydantic: Plan, Diff, Review, IngestResult, etc.)
│   ├── orchestrator.py (delegate_typed helper)
│   ├── ledger.py (two-ledger writer)
│   ├── cost.py (circuit breaker)
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
    └── test_graph.py
```
Note: Repo tree in PLAN.md references `workshop/graph.py` (LangGraph) but L22 removes LangGraph from Phase 1. `graph.py` should be renamed/replaced by `orchestrator.py` with Hermes `delegate_task` pattern.

---

## Topic: Phase 1 execution timeline (7 dev days)

source: docs/ingest/PLAN.md §Repo bootstrap checklist
- Day 1: Telegram token rotation, repo init, Hermes local install, scaffold repo, skill audit script + run
- Day 2: Tier 1 skill port + Aider skill + brain-bridge skills + smoke tests
- Day 3: workshop Python package (state.py, coder.py, nodes/, orchestrator.py), unit tests
- Day 4: Brain integration, ledger, cost circuit breaker
- Day 5: HITL round-trip (Telegram inline buttons), MCP re-registration
- Day 6: VPS deploy (rsync, systemd enable, disable Brain Telegram), smoke from Telegram
- Day 7: Run V1–V24 verification matrix, fix failures, tag v0.1.0, write retro to Brain

---

## Topic: Won't ship in Phase 1

source: docs/ingest/PLAN.md §WON'T ship in Phase 1
Explicit Phase 1 exclusions:
- Discord, WhatsApp, Slack adapters
- OpenHands V1 SDK integration (Phase 2 behind Coder adapter)
- Claude Code as coder (model-agnostic constraint)
- LangGraph orchestration (v3 removal)
- Broadcast review board (P3)
- MoA / Self-MoA inside reviewer
- Auto-merge / auto-deploy
- Auto-merge of nightly-tests failures (HITL required)
- Multi-repo support beyond allowlist
- Plugin skill clusters (gsd-*, superpowers:*, dotnet-skills:*) — too claude-tool-coupled
- Vault-level structured search endpoint on Brain
