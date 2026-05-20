# Requirements: ultra-workshop

**Source:** docs/ingest/PLAN.md (SPEC, precedence 0, post-grill v3)
**Scope:** Phase 1 — all 28 requirements are v1

---

## v1 Requirements

### Infrastructure & Deploy

**REQ-ws-001** — Hermes systemd service
Hermes Agent installed under `/opt/ultra-workshop/` on VPS, running as `uws-hermes.service` with `After=uab-brain.service`.
Acceptance: `systemctl status uws-hermes` → `active (running)` (V1)

**REQ-ws-002** — Telegram access control
Telegram bot (rotated token) gates on allowed chat ID `7113965359` only.
Acceptance: Only chat ID `7113965359` can trigger skills; `/start` replies within 5s (V2)

**REQ-ws-013** — Telegram gateway de-duplication
Brain's `uab-telegram.service` must be disabled before workshop Telegram comes up.
Acceptance: `systemctl status uab-telegram` → `inactive (dead)` (V15)

**REQ-ws-015** — MCP registration in Hermes
5 MCP servers registered in Hermes config: `github`, `context7`, `crawl4ai`, `hostinger-api`, `google-workspace`.
Acceptance: `hermes mcp list` shows all 5 (V16)

**REQ-ws-014** — Restart resilience
Workshop survives `systemctl restart uws-hermes` mid-flow; mid-flow HITL pause resumes cleanly.
Acceptance: Hermes FTS5 preserves pending approvals; tapping Approve after restart completes flow without re-triage (V14)

---

### Vault Sync (Day 1 prerequisite)

**REQ-ws-024** — Vault GitHub remote setup
`gh repo create caiobellizzi/second-brain --private`; SSH deploy key on VPS; vault remote wired.
Acceptance: VPS vault pushes successfully to `git@github.com:caiobellizzi/second-brain.git`

**REQ-ws-025** — Mac vault sync via Obsidian-Git
Obsidian-Git installed; auto-pull + auto-commit-and-sync every 5 min; Mac remote wired.
Acceptance: Mac vault changes appear on VPS within ~5 min

**REQ-ws-026** — VPS vault cron
`*/5 * * * *` cron entry using existing `scripts/git-sync.sh push && pull`.
Acceptance: VPS vault changes appear on Mac within ~5 min

**REQ-ws-027** — Vault sync environment variables
`VAULT_VPS_PATH`, `VAULT_DEFAULT_BRANCH`, `VAULT_REMOTE` set in `/etc/uab/env` (VPS) and `.env` (Mac).
Acceptance: Env vars present and correct on both systems

---

### Skill Tooling

**REQ-ws-003** — Skill audit + auto-translate script
`scripts/audit-claude-skills.py` walks `~/.claude/skills/`, tags each skill, auto-translates `requires-translation` skills to `~/.hermes/skills/translated/`, emits `skill-audit.json`.
Acceptance: Tags 4 categories; auto-translates tool map; emits `TRANSLATION_NOTES.md`; default `--dry-run`; idempotent; never writes to `~/.hermes/skills/<name>/` directly

**REQ-ws-004** — Tier 1 skill port (~10 skills)
~10 agent-agnostic skills copied to `~/.hermes/skills/` with Hermes frontmatter; smoke-tested.
Acceptance: `hermes skill run <name> --dry-run` passes for each ported skill

**REQ-ws-005** — Brain-bridge skills (3 new)
`brain-query`, `brain-ingest`, `brain-research` skills wrapping Brain HTTP endpoints.
Acceptance: `hermes skill run brain-query --question "what is PARA"` returns answer (V4)

**REQ-ws-006** — Aider Hermes skill
`skills/aider/SKILL.md` — local implementation of Hermes Issue #534; invokes Aider subprocess with architect=`cloud-sonnet`, editor=`private-worker`.
Acceptance: `hermes skill run aider --task "echo to file"` returns a diff; cost log shows two LLM calls (V5)

---

### Orchestration Pipeline

**REQ-ws-028** — Pydantic specialist output schemas
`workshop/types.py` defines `Plan`, `PlanStep`, `Diff`, `FileChange`, `Review`, `Issue`, `IngestResult`; JSON schema injected into prompts; `delegate_typed()` in `workshop/orchestrator.py`.
Acceptance: Validation + retry logic in `delegate_typed(role, output_type, ...)`; max 2 parse retries per role

**REQ-ws-007** — workshop-build skill
`workshop-build` Hermes skill orchestrates 5-role specialist pipeline via `delegate_task` calls.
Acceptance: Pipeline runs triage → planner → coder → reviewer → pr_opener; reviewer→coder retry max 2; Pydantic schemas validated; end-to-end `/build <task>` → PR URL in Telegram within ~5 min (V8)

**REQ-ws-008** — workshop-fix skill
`workshop-fix` Hermes skill for `/fix <github-issue-url>` path; same pipeline, different triage branch; fetches issue first.
Acceptance: `/fix <issue-url>` → matching PR opened linking the issue (V9)

---

### Observability & Safety

**REQ-ws-009** — Two-ledger task audit trail
Magentic-One pattern: `task_ledger.md` (goal + plan) + `progress_log.jsonl` (one event per node transition) under `~/.ultra-workshop/tasks/<task-id>/`.
Acceptance: Both files present after any `/build` or `/fix` (V10)

**REQ-ws-010** — HITL gate before PR creation
Skill body pauses via Hermes clarify callback; Telegram inline buttons (Approve/Reject).
Acceptance: Flow pauses at pr_opener; [Approve] → git push + gh pr create; [Reject] aborts cleanly (V7)

**REQ-ws-011** — ADR write-back after PR
After PR created, workshop writes ADR via Brain.ingest to `_system/workshop-adrs/<task-id>.md` with correct frontmatter.
Acceptance: ADR file present with `workshop.task_id`, `workshop.status: done`, `workshop.pr_url`, `system.created_by: workshop` (V12, V18)

**REQ-ws-012** — Cost ledger + circuit breaker
Per-`delegate_task` cost posted to Brain's `_system/cost-ledger.md`; circuit breaker checked before each LLM call.
Acceptance: Cost entry with `source: workshop` after each `/build` (V11); at $18 self-cancel + Telegram warning; at $20 LLM calls refused with "budget exhausted" (V13)

---

### Autonomous Cron Routines

**REQ-ws-016** — daily-research cron (07:00)
Reads top entry from `vault/_system/research-queue.md`, invokes Brain.research, writes synthesis to vault `Inbox/`, marks entry `workshop.status: done`, notifies Telegram.
Acceptance: Runs at 07:00 via Hermes cron; uses `cloud-groq`; budget circuit breaker enforced

**REQ-ws-017** — nightly-tests cron (02:00)
For each repo in `ALLOWED_REPOS`: clone to `/tmp/uws-test/<repo>`, run test command, write results to vault. On failures: `workshop.suggested_action: fix-test-failure` (NOT dispatched automatically).
Acceptance: Results surface in Brain's daily-digest; user confirms dispatch manually; uses `cloud-groq`

**REQ-ws-018** — bug-scan / vault polling (every 4h + fast-poll)
Three-tier polling with vocabulary-split + quiet-hours enforcement.
Acceptance: Fast-poll every 30s on `.workshop-queue.jsonl`; standard-poll every 4h dispatches only on `action:` + `confirmed: true`; nightly-rescan at 03:00; quiet-hours defer 22:00–07:00; verbs dispatched correctly

**REQ-ws-019** — Cron budget enforcement
All cron routines check circuit breaker before LLM calls; self-cancel at $18 with one Telegram warning per day.
Acceptance: Reads from `vault/_system/cost-ledger.md`; warning emitted once per budget threshold breach

---

### Brain ↔ Workshop Integration

**REQ-ws-020** — Flow B: Brain → Workshop (orphan linking)
Brain's `uab-monitor.timer` writes lint-report with `workshop.suggested_action: link-orphans`; user confirms → workshop dispatches.
Acceptance: V19: synthetic lint-report with `workshop.action: link-orphans` → bug-scan dispatches → Telegram approval prompt appears

**REQ-ws-021** — Flow E: Brain → Telegram via Workshop (daily digest)
Brain's daily-digest appends `{"action": "post-to-telegram", "confirmed": true}` to `.workshop-queue.jsonl`; Workshop fast-poll picks up within 30s.
Acceptance: Workshop posts within 30s of Brain writing; Brain's old Telegram path stays disabled

**REQ-ws-022** — Shared trust policy symlink
`/opt/ultra-workshop/workshop/trust_shared.py → /opt/ultra-agents-brain/ultra_brain/trust.py`.
Acceptance: `readlink` returns correct target; `from workshop import trust_shared; trust_shared.classify_action('git push')` returns expected risk tier (V22)

**REQ-ws-023** — Integration contract documentation
Install writes `vault/_system/integration-contract.md` with frontmatter vocabulary spec.
Acceptance: File exists and matches vocabulary table in PLAN.md (V23)

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REQ-ws-024 | Phase 1 | Pending |
| REQ-ws-025 | Phase 1 | Pending |
| REQ-ws-026 | Phase 1 | Pending |
| REQ-ws-027 | Phase 1 | Pending |
| REQ-ws-001 | Phase 2 | Pending |
| REQ-ws-002 | Phase 2 | Pending |
| REQ-ws-013 | Phase 2 | Pending |
| REQ-ws-015 | Phase 2 | Pending |
| REQ-ws-014 | Phase 2 | Pending |
| REQ-ws-003 | Phase 3 | Pending |
| REQ-ws-004 | Phase 3 | Pending |
| REQ-ws-005 | Phase 3 | Pending |
| REQ-ws-006 | Phase 3 | Pending |
| REQ-ws-028 | Phase 4 | Pending |
| REQ-ws-007 | Phase 4 | Pending |
| REQ-ws-008 | Phase 4 | Pending |
| REQ-ws-009 | Phase 4 | Pending |
| REQ-ws-010 | Phase 4 | Pending |
| REQ-ws-011 | Phase 4 | Pending |
| REQ-ws-012 | Phase 4 | Pending |
| REQ-ws-016 | Phase 5 | Pending |
| REQ-ws-017 | Phase 5 | Pending |
| REQ-ws-018 | Phase 5 | Pending |
| REQ-ws-019 | Phase 5 | Pending |
| REQ-ws-020 | Phase 5 | Pending |
| REQ-ws-021 | Phase 5 | Pending |
| REQ-ws-022 | Phase 5 | Pending |
| REQ-ws-023 | Phase 5 | Pending |

**Coverage:** 28/28 requirements mapped. No orphans.
