# Roadmap: ultra-workshop

## Overview

Bootstrap a Tier 2 autonomous coding agent that runs alongside Brain on the same VPS: Telegram-driven build/fix pipeline with HITL, ledgers, cost circuit breaker, autonomous cron routines, Brain↔Workshop vault signaling, an LLM repo-aware planner, an 8-scope review wave, and per-step build execution.

---

## Milestones

- ✅ **v1.0 — Autonomous Coding Agent (Tier 2)** — SHIPPED 2026-06-01. Phases 1–10 (+10.1). 50/56 requirements satisfied; Flows B/E live-verified on VPS. Archive: [`milestones/v1.0-ROADMAP.md`](milestones/v1.0-ROADMAP.md) · Audit: [`v1.0-v1.0-MILESTONE-AUDIT.md`](v1.0-v1.0-MILESTONE-AUDIT.md)

---

## v1.1 Backlog (carried from v1.0)

- **REQ-ws-015** — MCP registration in Hermes (owner-deferred in Phase 2)
- **REQ-ws-025 / REQ-ws-027** — Mac-side vault round-trip + env confirmation (Obsidian-Git)
- **REQ-ws-033** — live LLM planner `affected_files` accuracy (needs live VPS pipeline run)
- **REQ-ws-048** — requirements brain pre-query injects `planning_notes` only (wire to primary path)
- **REQ-ws-050** — git-worktree isolation not wired to production review wave
- **Brain-side queue producer** — `ultra-agents-brain` must WRITE entries to `_system/.workshop-queue.jsonl` (daily-digest/lint-report producers); workshop consumer is proven
- **Catch-up hook TZ** — hour checks use local time while cron schedules assume UTC (obs #24076)

---

## Next Milestone

Run `/gsd:new-milestone` to scope v1.1 (fresh REQUIREMENTS.md will be generated).
