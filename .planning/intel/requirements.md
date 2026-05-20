# Synthesized Requirements

source: docs/ingest/PLAN.md (classified: SPEC, section: "MUST ship in Phase 1")

Note: Source document is classified as SPEC (not PRD), but the "MUST ship in Phase 1" section contains discrete, acceptance-criteria-bearing requirements equivalent to PRD line items. Extracted as requirements with IDs derived from the document's own WS-NNN numbering.

---

## REQ-ws-001

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-001 (WS-001)
scope: Hermes installation / systemd
description: Hermes Agent installed under `/opt/ultra-workshop/` on VPS, running as `uws-hermes.service`
acceptance-criteria:
  - systemd unit file at `deploy/systemd/uws-hermes.service`
  - Service depends on `uab-brain.service` (`After=uab-brain.service`)
  - `systemctl status uws-hermes` → `active (running)` (V1)

---

## REQ-ws-002

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-002 (WS-002)
scope: Telegram access control
description: Telegram bot (rotated token) gates on the existing allowed chat ID `7113965359`
acceptance-criteria:
  - Bot token rotated before deploy (L7)
  - Only chat ID `7113965359` can trigger skills
  - `/start` command → bot replies within 5s (V2)

---

## REQ-ws-003

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-003 (WS-003)
scope: skill audit tooling
description: Skill-audit + auto-translate script `scripts/audit-claude-skills.py` walks `~/.claude/skills/`, tags each skill, auto-translates `requires-translation` skills using Tool Translation Map (Appendix E), writes to `~/.hermes/skills/translated/<name>/`, emits `skill-audit.json`
acceptance-criteria:
  - Tags: `agent-agnostic` / `claude-specific` / `requires-translation` / `requires-manual-port`
  - Auto-translates: `Read`→`read_file`, `Write`→`write_file`, `Edit`→`edit_file`, `Bash`→`terminal`, `Grep`→`search`, `Glob`→`find_files`, `WebFetch`→`http_request` (2-step), `WebSearch`→`web_search`
  - Emits `TRANSLATION_NOTES.md` per skill with substitutions + line numbers
  - Default `--dry-run` mode; requires `--apply` to commit
  - Idempotent re-runs (deterministic ID hashing, stable JSON)
  - Never writes directly to `~/.hermes/skills/<name>/` — only to `translated/`

---

## REQ-ws-004

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-004 (WS-004)
scope: skill porting
description: Tier 1 skill port — ~10 agent-agnostic skills copied to `~/.hermes/skills/` and smoke-tested in local Hermes
acceptance-criteria:
  - Frontmatter updated to Hermes spec (name, description, version, platforms)
  - Each smoke-tested: `hermes skill run <name> --dry-run` passes

---

## REQ-ws-005

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-005 (WS-005)
scope: Brain bridge skills
description: 3 new brain-bridge skills: `brain-query`, `brain-ingest`, `brain-research` — thin Hermes skills wrapping HTTP calls to Brain's Agno endpoints
acceptance-criteria:
  - `brain-query`: `POST /agents/query/runs` → synthesized vault answer with citations
  - `brain-ingest`: `POST /agents/ingest/runs` → write ADR/lesson to vault (HITL-gated on Brain side)
  - `brain-research`: `POST /agents/research/runs` → trigger multi-angle research
  - Smoke: `hermes skill run brain-query --question "what is PARA"` returns answer (V4)

---

## REQ-ws-006

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-006 (WS-006)
scope: Aider Hermes skill
description: Aider Hermes skill (`skills/aider/SKILL.md`) — local implementation of Hermes Issue #534
acceptance-criteria:
  - Invokes Aider subprocess with: architect=`cloud-sonnet`, editor=`private-worker`, `--yes-always --no-stream --message <task>`
  - Smoke: `hermes skill run aider --task "echo to file"` returns a diff (V5)
  - Cost log shows two LLM calls (cloud-sonnet + private-worker) (V5)

---

## REQ-ws-007

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-007 (WS-007)
scope: workshop-build skill / orchestration
description: `workshop-build` Hermes skill orchestrates the 5-role specialist pipeline via `delegate_task` calls
acceptance-criteria:
  - Pipeline: triage → planner → coder → reviewer → pr_opener
  - Reviewer→coder retry loop: max 2 attempts
  - Each specialist returns a Pydantic-typed object: `Plan`, `Diff`, `Review`, `IngestResult`
  - Orchestrator validates schema; retries with explicit reminder on parse failure (max 2 retries/role)
  - Specialists read predecessors' typed outputs from in-process task ledger when prompted
  - `delegate_typed()` helper in `workshop/orchestrator.py`

---

## REQ-ws-008

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-008 (WS-008)
scope: workshop-fix skill
description: `workshop-fix` Hermes skill for `/fix <github-issue-url>` path
acceptance-criteria:
  - Same pipeline as workshop-build; different triage branch
  - Fetches issue first via gh CLI/MCP
  - PR created end-to-end: `/fix <issue-url>` → matching PR opened linking the issue (V9)

---

## REQ-ws-009

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-009 (WS-009)
scope: task ledger / audit trail
description: Magentic-One two-ledger pattern — each task writes `task_ledger.md` + `progress_log.jsonl` under `~/.ultra-workshop/tasks/<task-id>/`
acceptance-criteria:
  - `task_ledger.md` contains goal + plan
  - `progress_log.jsonl` contains one event per node transition
  - Both files present after any `/build` or `/fix` (V10)

---

## REQ-ws-010

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-010 (WS-010)
scope: HITL gate
description: HITL gate before `gh pr create` — skill body pauses via Hermes clarify callback; user approval resumes
acceptance-criteria:
  - Flow pauses at pr_opener; Telegram inline buttons appear (V7)
  - [Approve] resumes → git push + gh pr create
  - [Reject] aborts cleanly with state preserved (V7)

---

## REQ-ws-011

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-011 (WS-011)
scope: ADR write-back
description: After PR created, workshop writes ADR via Brain.ingest to `_system/workshop-adrs/<task-id>.md`
acceptance-criteria:
  - ADR frontmatter includes: `workshop.task_id`, `workshop.status: done`, `workshop.pr_url`, `system.created_by: workshop`
  - File present after PR creation (V12, V18)

---

## REQ-ws-012

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-012 (WS-012)
scope: cost ledger / circuit breaker
description: Per-`delegate_task` cost posted to Brain's `_system/cost-ledger.md`; circuit breaker checked before each LLM call (shared $20/day cap)
acceptance-criteria:
  - Cost entry in ledger after each `/build` with per-node breakdown (V11)
  - `source: workshop` field in each entry (V21)
  - When `$daily_spend ≥ $18`: routines self-cancel + emit single Telegram warning per day (WS-019)
  - When `$daily_spend ≥ $20`: LLM calls refused with "budget exhausted" message (V13)

---

## REQ-ws-013

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-013 (WS-013)
scope: Telegram gateway de-duplication
description: Brain's `uab-telegram.service` must be disabled before workshop's Telegram is brought up
acceptance-criteria:
  - `systemctl status uab-telegram` → `inactive (dead)` (V15)
  - No dual-gateway responses possible

---

## REQ-ws-014

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-014 (WS-014)
scope: state persistence / restart resilience
description: Workshop survives `systemctl restart uws-hermes` mid-flow
acceptance-criteria:
  - Hermes session FTS5 preserves pending approvals
  - Task ledger files preserve flow state
  - Mid-flow restart at HITL pause: tapping Approve from Telegram completes flow without restarting from triage (V14)

---

## REQ-ws-015

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-015 (WS-015)
scope: MCP registration in Hermes
description: 5 MCP servers registered in Hermes config: `github`, `context7`, `crawl4ai`, `hostinger-api`, `google-workspace`
acceptance-criteria:
  - `hermes mcp list` shows all 5 servers (V16)
  - Sources from `~/.claude.json` equivalents

---

## REQ-ws-016

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-016 (WS-016)
scope: autonomous cron — daily-research
description: `daily-research` autonomous cron (`0 7 * * *`) reads top entry from `vault/_system/research-queue.md`, invokes Brain.research, writes synthesis to vault `Inbox/`, marks queue entry `workshop.status: done`, notifies Telegram with link
acceptance-criteria:
  - Runs at 07:00 daily via Hermes cron scheduler
  - Uses `cloud-groq` (L25 routing strategy)
  - Budget circuit breaker enforced (WS-019)

---

## REQ-ws-017

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-017 (WS-017)
scope: autonomous cron — nightly-tests
description: `nightly-tests` autonomous cron (`0 2 * * *`) for each repo in `ALLOWED_REPOS`: clone to `/tmp/uws-test/<repo>`, run declared test command, write results to `vault/_system/workshop-routines/nightly-tests/<date>.md`
acceptance-criteria:
  - On failures: frontmatter `workshop.suggested_action: fix-test-failure` (NOT `action` + `confirmed`)
  - Results surface in Brain's 20:00 daily digest for human review
  - User manually flips `suggested_action → action` + `confirmed: true` to dispatch (or ignores)
  - Uses `cloud-groq` (L25 routing strategy)

---

## REQ-ws-018

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-018 (WS-018)
scope: autonomous cron — bug-scan / vault polling
description: Three-tier polling for vault signals with vocabulary-split + quiet-hours enforcement
acceptance-criteria:
  - Fast-poll every 30s on `vault/_system/.workshop-queue.jsonl`; offset at `~/.ultra-workshop/state/queue-offset.txt`
  - Standard-poll every 4h (Hermes cron): full vault scan; dispatches ONLY when BOTH `workshop.action:` AND `workshop.confirmed: true` present
  - Nightly-rescan at 03:00: full scan + dedup index rebuild
  - Quiet-hours guard: 22:00–07:00 local — Telegram approval prompts queued until 07:01; zero-HITL verbs dispatch immediately
  - Verbs: `post-to-telegram`→notify, `fix-bug`/`fix-test-failure`→workshop-fix, `link-orphans`→linker, `research`→workshop-research

---

## REQ-ws-019

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-019 (WS-019)
scope: cron budget enforcement
description: All cron routines respect the daily budget circuit breaker
acceptance-criteria:
  - If `$daily_spend ≥ $18`: routine self-cancels + emits single Telegram warning per day
  - Circuit breaker reads from shared `vault/_system/cost-ledger.md`

---

## REQ-ws-020

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-020 (WS-020)
scope: Brain → Workshop loop closure (Flow B)
description: Brain's hourly `uab-monitor.timer` writes `vault/_system/lint-report.md` with frontmatter `workshop.suggested_action: link-orphans` when orphans found; aggregated into Brain's daily-digest; user confirms via Obsidian to dispatch
acceptance-criteria:
  - Verified end-to-end via V19: synthetic lint-report with `workshop.action: link-orphans` → Workshop bug-scan dispatches to link-orphans skill → Telegram approval prompt appears

---

## REQ-ws-021

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-021 (WS-021)
scope: Brain → Telegram via Workshop (Flow E)
description: Brain's daily-digest appends one line to `vault/_system/.workshop-queue.jsonl` with `post-to-telegram` action (self-confirming verb); Workshop fast-poll picks it up within 30s
acceptance-criteria:
  - `{"action": "post-to-telegram", "ref": "<digest-path>", "urgency": "urgent", "confirmed": true}` format
  - Workshop posts within 30s of Brain writing to queue
  - Brain's old direct-to-Telegram path stays disabled

---

## REQ-ws-022

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-022 (WS-022)
scope: shared trust policy
description: Install script creates trust policy symlink
acceptance-criteria:
  - `/opt/ultra-workshop/workshop/trust_shared.py → /opt/ultra-agents-brain/ultra_brain/trust.py`
  - `readlink` returns correct target (V22)
  - `from workshop import trust_shared; trust_shared.classify_action('git push')` returns expected risk tier

---

## REQ-ws-023

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-023 (WS-023)
scope: integration contract documentation
description: Install writes `vault/_system/integration-contract.md` with the frontmatter vocabulary spec (D6)
acceptance-criteria:
  - File exists and matches vocabulary table in PLAN.md (V23)

---

## REQ-ws-024

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-024 (WS-024)
scope: vault sync — GitHub remote setup
description: Day 1 vault sync wiring via GitHub remote
acceptance-criteria:
  - `gh repo create caiobellizzi/second-brain --private`
  - SSH deploy key generated on VPS + added to repo deploy keys (read+write)
  - VPS vault remote wired: `git remote add origin git@github.com:caiobellizzi/second-brain.git && git push -u origin main`

---

## REQ-ws-025

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-025 (WS-025)
scope: vault sync — Mac side
description: Mac side vault sync via Obsidian-Git plugin
acceptance-criteria:
  - Obsidian-Git installed at `~/Documents/second-brain/.obsidian/plugins/obsidian-git/`
  - Auto-pull every 5 min + auto-commit-and-sync every 5 min configured
  - Mac vault remote wired: `git remote add origin git@github.com:caiobellizzi/second-brain.git`

---

## REQ-ws-026

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-026 (WS-026)
scope: vault sync — VPS cron
description: VPS cron sync using existing `scripts/git-sync.sh`
acceptance-criteria:
  - Entry in `/opt/ultra-agents-brain/deploy/cron/ultra-agents-brain.cron`: `*/5 * * * * uabrain /opt/ultra-agents-brain/scripts/git-sync.sh push "vps-auto $(date -u +%H:%M)" && /opt/ultra-agents-brain/scripts/git-sync.sh pull`

---

## REQ-ws-027

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-027 (WS-027)
scope: vault sync — environment variables
description: Vault sync env vars set in `/etc/uab/env` on VPS and `.env` on Mac
acceptance-criteria:
  - `VAULT_VPS_PATH=/srv/second-brain` (VPS) or `VAULT_VPS_PATH=$HOME/Documents/second-brain` (Mac)
  - `VAULT_DEFAULT_BRANCH=main`
  - `VAULT_REMOTE=origin`

---

## REQ-ws-028

source: docs/ingest/PLAN.md §MUST ship in Phase 1
id: REQ-ws-028 (WS-028)
scope: Pydantic specialist output schemas
description: `workshop/types.py` defines Pydantic schemas for all specialist communication
acceptance-criteria:
  - Schemas: `Plan`, `PlanStep`, `Diff`, `FileChange`, `Review`, `Issue`, `IngestResult`
  - JSON schema injected into each specialist's prompt
  - Validation + retry logic in `workshop/orchestrator.py`'s `delegate_typed(role, output_type, ...)` helper
