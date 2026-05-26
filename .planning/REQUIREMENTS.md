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
`workshop/types.py` defines `Plan`, `PlanStep`, `Diff`, `FileChange`, `Review`, `Issue`, `IngestResult`; JSON schema injected into specialist prompts; `run_specialist()` in `workshop/orchestrator.py` (Architecture B subprocess pattern).
Acceptance: Validation via `model_validate_json()` in `run_specialist()`; `RuntimeError` on non-zero subprocess exit; `subprocess.TimeoutExpired` on timeout; 18 unit tests covering all schema types and orchestrator error paths *(Note: `delegate_typed()` replaced by subprocess `run_specialist()` — same user-observable outcome)*

**REQ-ws-007** — workshop-build skill
`workshop-build` Hermes skill orchestrates 5-role specialist pipeline via `run_specialist()` subprocess calls (Architecture B).
Acceptance: Phase 4 baseline pipeline runs triage → planner → coder → reviewer → pr_opener; reviewer→coder retry max 2; Pydantic schemas validated; end-to-end `/build <task>` → PR URL in Telegram within ~5 min (V8). After REQ-ws-029 ships, repo-targeted builds use `/build --repo <repo> <task>` and missing `--repo` shows usage plus active repos.

**REQ-ws-008** — workshop-fix skill
`workshop-fix` Hermes skill for `/fix <github-issue-url>` path; same pipeline, different triage branch; fetches issue first.
Acceptance: `/fix <issue-url>` → matching PR opened linking the issue (V9)

**REQ-ws-029** — Telegram repo selection and repo-targeted builds
Workshop exposes `/repo list`, `/repo add <repo>`, `/repo create <repo>`, and `/repo remove <repo>` backed by `/srv/second-brain/_system/workshop-repos.json`; `/build --repo <repo> <task>` targets an active registry repo; `/fix <issue-url>` derives `owner/name` from the issue URL and rejects unknown or inactive repos.
Acceptance: Registry auto-seeds `caiobellizzi/test-workshop-sandbox`; add/create/remove mutations require Telegram approval; `/repo create` creates private repos with README; `/repo add` verifies WRITE, MAINTAIN, or ADMIN access; `/repo remove` only marks inactive; final PR approval shows repo, base branch, feature branch, changed files, and diff summary; live smoke confirms a PR targets a throwaway registered repo.

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
| REQ-ws-007 | Phase 4 | Complete |
| REQ-ws-008 | Phase 4 | Complete |
| REQ-ws-029 | Phase 6 | Pending |
| REQ-ws-009 | Phase 4 | Pending |
| REQ-ws-010 | Phase 4 | Complete |
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

| REQ-ws-030 | Phase 7 | Complete |
| REQ-ws-031 | Phase 7 | Complete |
| REQ-ws-032 | Phase 7 | Complete |
| REQ-ws-033 | Phase 7 | Complete |
| REQ-ws-034 | Phase 7 | Complete |

**Coverage:** 34/34 requirements mapped. No orphans.

---

### Agentic Repo-Aware Planner (Phase 7)

**REQ-ws-030** — Pre-planner workspace clone + state persistence
Repo is cloned to a deterministic path (`/tmp/uws-workspace-{task_id}/`) in `workshop_build.py` BEFORE the planner stage. `workspace_dir` key added to `new_task_state()` in `workshop/state.py`. Clone result saved to `state["workspace_dir"]` via `save_task_state()`. Resumable: on restart, existing `.git` directory is detected and re-clone is skipped.
Acceptance: `python -m pytest tests/phase-07/test_workspace.py -x` passes; `new_task_state()` returns dict containing `"workspace_dir"` key; `workshop_build.py` clones before planner query is built (SC-1)

**REQ-ws-031** — planner-specialist LLM via hermes chat with read-only tools
`hermes-skill-run.sh` short-circuit for `planner-specialist` removed; planner routes through `hermes chat` with `HERMES_HOME=specialist-home-orchestrator`, `MAX_TURNS=8`. `planner-specialist/SKILL.md` updated: `read_file`/`list_files`/`grep_files` allowed and scoped to `workspace_dir`; write/code-exec/web tools forbidden. Dry-run output reports `hermes chat` and `HERMES_HOME`.
Acceptance: `bats tests/phase-07/planner-smoke.bats` passes; `bats tests/phase-04/model-matrix-smoke.bats` passes with updated planner assertions (SC-2)

**REQ-ws-032** — 3-tier deterministic doc resolution
`workshop/doc_resolver.py` implements `resolve_doc(doc_name, workspace_dir, vault_path)`: tier 1 = `Path(workspace_dir).rglob(doc_name)`, tier 2 = `Path(vault_path).rglob(doc_name)`, tier 3 = `brain_http.call_agent("query", ...)` with 60s timeout. Non-blocking at each tier; graceful fallback. `doc_name` validated against path traversal before vault rglob. `VAULT_VPS_PATH` env var used with `/srv/second-brain` fallback.
Acceptance: `python -m pytest tests/phase-07/test_doc_resolver.py -x` passes (all 3 tiers + traversal guard) (SC-3)

**REQ-ws-033** — LLM planner output accuracy + reviewer false-block elimination
`workshop_build.py` planner query gains `workspace_dir` and `reference_doc` keys. `planner-specialist/SKILL.md` instructs LLM to use `list_files` (depth 2) + `read_file` on key files to produce `affected_files` with real repo paths. `workshop/stage_policy.py` planner timeout raised to 480s. No changes to `workshop/reviewer.py` required — accurate `affected_files` eliminates "changed files outside the plan" false-blocks automatically.
Acceptance: `python -m pytest tests/phase-07/test_planner_llm.py -x` passes (schema validation); reviewer gate integration relies on accurate affected_files from LLM (SC-4)

**REQ-ws-034** — Regression safety: Phase 4 + Phase 6 suites stay green
`tests/phase-04/model-matrix-smoke.bats` planner assertion updated to match new dry-run output format (`hermes chat`, `HERMES_HOME`). All other Phase 4 and Phase 6 bats + pytest assertions remain green. Phase 7 test directory `tests/phase-07/` created with `__init__.py` plus unit test stubs before any implementation tasks run (Wave 0).
Acceptance: `python -m pytest tests/phase-06/ tests/test_repo_registry.py -q` exits 0; `bats tests/phase-04/model-matrix-smoke.bats` exits 0 after bats update; `python -m pytest tests/phase-07/ -q` exits 0 (SC-5, SC-6)

