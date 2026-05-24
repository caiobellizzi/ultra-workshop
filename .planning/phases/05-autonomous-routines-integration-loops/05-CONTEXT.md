# Phase 5: Autonomous Routines & Integration Loops - Context

**Gathered:** 2026-05-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Three autonomous cron routines (`daily-research` 07:00, `nightly-tests` 02:00, `bug-scan` every 4h + 30s fast-poll) run unsupervised on the VPS; Brain→Workshop vault-signaling flows (Flow B orphan-linking, Flow E daily-digest→Telegram) dispatch correctly with two-tier vocabulary (`suggested_action:` vs `action:` + `confirmed:`); the shared trust policy symlink exists; `vault/_system/integration-contract.md` documents the frontmatter vocabulary. V1–V24 verification matrix passes.

**Not in scope** (capability additions belong in other phases):
- New cron routines beyond the three locked by L15/L23
- Brain→Workshop HTTP path (D7: forbidden; signaling stays vault-based)
- LangGraph migration (L22: deferred to Phase 2)
- Multi-repo registry expansion (Phase 6, complete)

</domain>

<decisions>
## Implementation Decisions

### Cron scheduling substrate

- **D-01:** Use **Hermes built-in cron primitive** for the three routines (preferred ecosystem alignment with L2/L4 — Hermes owns orchestration). Researcher MUST verify Hermes 0.14.0 actually exposes a cron/scheduler hook; if it does not, planner falls back to **systemd `.timer` units** (one `.timer`+`.service` pair per routine under `/etc/systemd/system/`) and documents the substitution in the plan.
- **D-02:** **Catch-up policy: run-once-on-restart-if-missed-today.** A startup hook checks marker files in `/home/uws/.ultra-workshop/cron-state/{daily-research,nightly-tests}.last` against today's date; if a slot was missed (VPS down at 07:00 or 02:00), the routine runs immediately on Hermes startup. Bounded — max one catch-up per routine per day. Applies to both substrates above.

### bug-scan runner shape

- **D-03:** **Hermes long-running skill triggered at startup** owns the 30s fast-poll on `.workshop-queue.jsonl` (ecosystem alignment with D-01). Researcher MUST verify Hermes 0.14.0 supports always-on skills (skill invoked at gateway startup, never returns) and document restart semantics. **Fallback:** dedicated `uws-bug-scan-fastpoll.service` (systemd) with internal `time.sleep(30)` loop if Hermes lacks the primitive.
- **D-04:** **Dedup via Brain-side `dispatched: true` mark.** Workshop reads `.workshop-queue.jsonl`, dispatches eligible entries (per L28 + L29 rules), then POSTs back to Brain via existing `brain_http.call_agent()` to mark the entry `dispatched: true`. Brain is single writer for the queue file; Workshop never rewrites it. D7-compliant (Workshop→Brain HTTP is allowed; D7 only forbids the reverse). Researcher MUST confirm whether Brain's existing `curator` / `ingest` endpoints can accept this update or whether a new Brain endpoint is required.
- **D-05:** Standard-poll (every 4h) reuses the same dispatch + dedup logic as fast-poll; only the schedule differs. Both implement the L28 vocabulary split (`suggested_action:` → no dispatch; `action:` + `confirmed: true` → dispatch, with quiet-hours deferral per L29) and the zero-HITL verbs bypass.

### Queue & signal file schemas

- **D-06:** `vault/_system/research-queue.md` is a **Markdown task list with frontmatter per entry**. Each entry: ``- [ ] question text`` on one line, with an attached attribute block carrying `id: r-<4hex>`, `priority: high|normal|low`, and (after consumption) `workshop.status: done`. `daily-research` picks the first unchecked + non-`done` entry, runs `Brain.research`, checks the box `[x]`, and writes `workshop.status: done` to the entry. Human-editable in Obsidian; diffable in git.
- **D-07:** `vault/_system/integration-contract.md` carries **the full frontmatter vocabulary table + ASCII flow diagrams for Flow A, B, D, E**. Single file, target ~150 lines. Every `workshop.*` field documented: `suggested_action`, `action`, `confirmed`, `status`, `task_id`, `dispatched`, `pr_url`, `created_by`, plus owner / write rules / valid values per field. Diagrams show the actual data path so future agents understand WHO writes WHAT WHEN. Written by Workshop install script to `vault/_system/integration-contract.md` (D1-compliant write path).
- **D-08:** `.workshop-queue.jsonl` path = `vault/_system/.workshop-queue.jsonl` (Brain writes; Workshop reads + POSTs `dispatched: true` updates back to Brain). Schema per line: `{"id": "...", "action": "...", "confirmed": bool, "payload": {...}, "created_by": "brain-<source>", "created_at": "...", "dispatched": bool}`.

### nightly-tests + failure/notification policy

- **D-09:** **Per-repo `test_command` field in `workshop-repos.json`.** Extend the existing registry schema (added in Phase 6) with an optional `test_command: string` field. `nightly-tests` iterates active repos: if `test_command` is set and non-empty, clones the repo to `/tmp/uws-test/<repo>` and runs it; otherwise logs "no test command configured" and skips. Explicit > convention discovery. Sandbox repo gets a noop `test_command` for V17.
- **D-10:** **Single Telegram alert per failure**, no retries. Every cron-routine failure (Brain unreachable, LLM 5xx, test command nonzero, budget breach) emits one concise Telegram message to chat ID `7113965359` and appends a structured entry to `vault/_system/workshop-cron-log.md`. Format: `[routine-name] failed: <one-line reason>. See vault/_system/workshop-cron-log.md`. Per-repo test failures are NOT alerted — they surface via REQ-ws-017's `workshop.suggested_action: fix-test-failure` in vault (intentional, per L28 vocabulary).
- **D-11:** **Daily-research delivery: short summary + vault link.** `daily-research` calls `Brain.research`, then `Brain.ingest` to write the full synthesis to `vault/Inbox/<YYYY-MM-DD>-research-<id>.md` (D1: workshop writes to `Inbox/` via Brain.ingest, not directly). Telegram message: `📑 Daily research: <title> (N sources). vault/Inbox/<YYYY-MM-DD>-research-<id>.md`. Single message, no chunking, no extra LLM call. Matches the simplicity-first principle and avoids token spend on a summary-of-a-summary.

### Claude's Discretion

- **Marker file format** for catch-up tracking — planner picks (touch-file vs JSON state vs SQLite); recommend simple `*.last` files with ISO date contents.
- **Quiet-hours implementation detail** — L29 mandates 22:00–07:00 dispatch deferral; planner picks whether deferred dispatches are queued and replayed at 07:00 (preferred) or simply skipped until next standard-poll.
- **Trust symlink installation** — D4 mandates `/opt/ultra-workshop/workshop/trust_shared.py → /opt/ultra-agents-brain/ultra_brain/trust.py`. Planner picks whether `scripts/install.sh` creates it or a new dedicated installer step. Existing `scripts/install.sh` is the natural home.
- **`workshop-cron-log.md` rotation / archival** — planner picks (append-only forever vs monthly rotation); recommend append-only for Phase 5, revisit if file grows >1MB.
- **Concrete Telegram alert chat path** — `hermes-skills/brain_http.py` doesn't currently send to Telegram. Planner picks: invoke an existing Hermes Telegram skill, write a small `hermes-skills/telegram_alert.py` helper, or call Hermes gateway's Telegram primitive directly.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Locked architectural decisions
- `.planning/PROJECT.md` — L1–L30 + D1–D10 + owner amendments. Phase-5-critical: **L15** (3 routines, exact schedules), **L23** (no overlap with Brain timers), **L28** (two-tier vocabulary), **L29** (quiet hours 22:00–07:00), **D1** (vault write zones), **D3** (cron ownership split), **D4** (trust symlink), **D7** (Brain never HTTP-calls Workshop), **D9** (task ledger paths).
- `.planning/REQUIREMENTS.md` — REQ-ws-016 through REQ-ws-023 acceptance criteria (8 requirements for this phase).
- `.planning/ROADMAP.md` §"Phase 5" — 6 success criteria; V1–V24 reference.

### Source-of-truth specs
- `docs/ingest/PLAN.md` — Original SPEC (post-grill v3) — frontmatter vocabulary table and Flow A/B/C/D/E definitions live here; integration-contract.md (D-07) must match it.

### Cross-phase context
- `.planning/phases/02-hermes-deploy/02-CONTEXT.md` — Hermes substrate decisions; restart-resilience pattern via `pending_hitl.db` and `startup-hitl-scan.py` hook (precedent for D-02 catch-up startup hook).
- `.planning/phases/04-build-fix-pipeline/04-05-SUMMARY.md` — Background-job pattern + progress logging convention (`[workshop] <stage> done`).
- `.planning/phases/06-repo-selection-builds/06-01-SUMMARY.md` — Repo registry schema and helpers (`workshop/repo_registry.py`) that D-09 extends.

### Existing code Phase 5 reuses
- `workshop/cost.py` — `check_circuit_breaker(mode="cron")` already raises `BudgetWarning` at $18 and `BudgetExhausted` at $20. All three routines MUST call this before any LLM dispatch (REQ-ws-019).
- `hermes-skills/brain_http.py` — `call_agent(agent_id, message, user_id)` for `research`, `ingest`, `curator`, `query` endpoints. Multipart form-data only (NOT JSON). Reuse for all D-04, D-11 Brain interactions.
- `workshop/repo_registry.py` — Active-repo iteration for D-09 (`nightly-tests` walks `active: true` entries).
- `workshop/ledger.py` — `append_progress()` / `write_task_ledger()` for any per-run audit trail.
- `hermes-config/config.yaml` — gateway-startup hook discovery (`~/.hermes/hooks/`); precedent for the catch-up + always-on bug-scan registration patterns.

### External docs to fetch via Context7
- Hermes Agent v0.14.0 — verify cron primitive and long-running skill support (D-01, D-03 fallback decision depends on this).
- systemd `.timer` man page (`OnCalendar=`, `Persistent=true`, `RandomizedDelaySec=`) — for the fallback substrate.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `workshop/cost.py` (95 lines) — `BudgetExhausted` / `BudgetWarning` already implemented; cron-mode circuit breaker is ready for REQ-ws-019.
- `hermes-skills/brain_http.py` — single entry point for every Brain HTTP call; routines plug straight in.
- `workshop/repo_registry.py` — `iter_active_repos()`-style helpers ready for `nightly-tests` to walk.
- `hermes-skills/startup-hitl-scan.py` + `hermes-config/config.yaml` hook block — proven precedent for "gateway startup → run a check → re-emit something" pattern that D-02 needs.
- `workshop/ledger.py` — JSONL progress log + task ledger writer; reusable for per-cron-run audit trail (e.g., daily-research run history).

### Established Patterns
- **Brain HTTP**: multipart/form-data, never JSON (422 trap). Documented inside `brain_http.py`. All D-04 / D-11 calls follow this.
- **Specialist subprocess**: `workshop/orchestrator.py::run_specialist()` invokes `hermes-skill-run.sh` with `shell=False`, 1200s timeout, Pydantic schema validation. If `daily-research` triggers Brain via a Hermes skill (not direct HTTP), reuse this pattern.
- **Vault write zone**: D1 forbids workshop writes outside `_system/workshop-*/`. Routines that need to write elsewhere (e.g., daily-research writing to `vault/Inbox/`) MUST go through `Brain.ingest`.
- **Two-ledger pattern** (D9): per-task `task_ledger.md` + `progress_log.jsonl`. Cron routines should write per-run ledgers under `~/.ultra-workshop/cron/<routine>/<YYYY-MM-DD>/`.

### Integration Points
- **Hermes gateway hooks** (`~/.hermes/hooks/`): catch-up startup hook (D-02) and bug-scan always-on skill (D-03) both register here; precedent in `hermes-config/config.yaml` lines 14–18.
- **Cost ledger** (`/srv/second-brain/_system/cost-ledger.md`): `workshop/cost.py` already parses this; cron routines invoke `check_circuit_breaker(mode="cron")` before each LLM call.
- **Vault sync** (Phase 1): all signal files transit `caiobellizzi/second-brain` private GitHub remote with VPS cron every 5 min + Mac Obsidian-Git. Eventual consistency means `dispatched: true` marks may take up to 5 min to reach the user's Mac view — acceptable.
- **Telegram chat ID `7113965359`** (REQ-ws-002): the only allowed sink for D-10 alerts and D-11 deliveries.

</code_context>

<specifics>
## Specific Ideas

- User explicitly chose Hermes-native substrates over systemd for both cron and the fast-poll runner (D-01, D-03) — preserve this preference unless researcher proves Hermes 0.14.0 lacks the primitives. Document the verification result in `05-RESEARCH.md`.
- User explicitly chose Brain-side dedup (D-04) over Workshop-side state — keep the queue file Brain-owned-writer, Workshop-only-reader (plus the dispatched-ACK POST). Researcher MUST surface whether Brain has a suitable endpoint or needs one.
- User explicitly chose link-to-vault Telegram delivery (D-11) over message-chunking — keep Telegram surface minimal.

</specifics>

<deferred>
## Deferred Ideas

- **Retry-then-alert and severity-tiered alerts** — considered for failure UX, rejected for Phase 5 simplicity. If alert fatigue or spurious-failure noise appears in operation, revisit in a hardening phase.
- **Convention-based test command discovery** — option B / C for D-09 rejected in favor of explicit `test_command` registry field. If users add many repos and find registry maintenance tedious, revisit.
- **Summary-bullet Telegram delivery for daily-research** — option requiring extra LLM call rejected as over-engineering; reconsider if vault-link-only proves friction in daily use.
- **`/status <task_id>` mid-run inspection command** — already deferred from Phase 4 (04-05-SUMMARY.md); still out of scope.
- **Concurrent-run isolation** — multiple `/build` at once not addressed; still deferred from Phase 4. Phase 5 cron routines should at least guard against overlapping invocations of the same routine (single-instance lock per routine).

</deferred>

---

*Phase: 5-Autonomous Routines & Integration Loops*
*Context gathered: 2026-05-24*
