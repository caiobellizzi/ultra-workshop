# Phase 5: Autonomous Routines & Integration Loops — Research

**Researched:** 2026-05-28
**Domain:** Hermes 0.14.0 cron/hook system, Brain HTTP endpoints, vault queue schema, systemd fallback
**Confidence:** HIGH (primary decisions resolved against live Hermes docs + codebase reads)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Use Hermes built-in cron primitive for the three routines. Fallback: systemd `.timer` units if Hermes lacks the primitive.
- **D-02:** Catch-up policy: run-once-on-restart-if-missed-today. Startup hook checks marker files in `/home/uws/.ultra-workshop/cron-state/{daily-research,nightly-tests}.last` against today's date. Max one catch-up per routine per day.
- **D-03:** Hermes long-running skill triggered at startup owns the 30s fast-poll. Fallback: dedicated `uws-bug-scan-fastpoll.service` (systemd) if Hermes lacks the primitive.
- **D-04:** Dedup via Brain-side `dispatched: true` mark. Workshop reads `.workshop-queue.jsonl`, dispatches eligible entries, then POSTs back to Brain via `brain_http.call_agent()`. Brain is single writer; Workshop never rewrites the queue file.
- **D-05:** Standard-poll (every 4h) reuses same dispatch + dedup logic; only schedule differs.
- **D-06:** `vault/_system/research-queue.md` is a Markdown task list with frontmatter per entry.
- **D-07:** `vault/_system/integration-contract.md` — full frontmatter vocabulary table + ASCII flow diagrams.
- **D-08:** `.workshop-queue.jsonl` path = `vault/_system/.workshop-queue.jsonl`. Schema: `{"id": "...", "action": "...", "confirmed": bool, "payload": {...}, "created_by": "brain-<source>", "created_at": "...", "dispatched": bool}`.
- **D-09:** Per-repo `test_command` field in `workshop-repos.json`. Explicit field, not convention discovery.
- **D-10:** Single Telegram alert per failure. Per-repo test failures NOT alerted — surface via `workshop.suggested_action: fix-test-failure` only.
- **D-11:** Daily-research: Brain.research → Brain.ingest → `vault/Inbox/<YYYY-MM-DD>-research-<id>.md`. Telegram message: short title + vault link, no extra LLM summary call.

### Claude's Discretion

- Marker file format for catch-up tracking (touch-file vs JSON vs SQLite).
- Quiet-hours implementation detail (queue-and-replay at 07:00 vs skip-until-next-poll).
- Trust symlink installation location (scripts/install.sh is natural home).
- `workshop-cron-log.md` rotation/archival policy.
- Concrete Telegram alert delivery path.

### Deferred Ideas (OUT OF SCOPE)

- Retry-then-alert and severity-tiered alerts.
- Convention-based test command discovery.
- Summary-bullet Telegram delivery for daily-research (extra LLM call).
- `/status <task_id>` mid-run inspection command.
- Concurrent-run isolation (beyond single-instance lock per routine).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-ws-016 | daily-research cron at 07:00 via Hermes cron; Brain.research → Brain.ingest → vault Inbox/; marks entry done; Telegram notification | D-01 CONFIRMED: Hermes cron supports `0 7 * * *`; D-11: `call_agent("research", ...)` + `call_agent("ingest", ...)` |
| REQ-ws-017 | nightly-tests at 02:00; clone active repos; run `test_command`; write vault results with `suggested_action: fix-test-failure` | D-01 CONFIRMED: `0 2 * * *`; repo_registry.list_active_repos() is the iteration primitive |
| REQ-ws-018 | Three-tier polling: fast-poll 30s + standard-poll 4h + nightly-rescan 03:00; vocabulary split; quiet hours 22:00–07:00 | D-03 ABSENT: Hermes has no always-on primitive → systemd fallback for fast-poll; standard/nightly use Hermes cron |
| REQ-ws-019 | All cron routines check `check_circuit_breaker(mode="cron")` before LLM calls; $18 warn / $20 hard | Already implemented in `workshop/cost.py` |
| REQ-ws-020 | Flow B: Brain writes lint-report with `workshop.suggested_action: link-orphans`; user confirms; bug-scan dispatches | Queue polling + dispatch logic; no new Brain endpoint needed for Flow B (uses frontmatter, not queue) |
| REQ-ws-021 | Flow E: Brain appends `post-to-telegram` entry to `.workshop-queue.jsonl`; Workshop fast-poll picks up within 30s | D-04 MISSING: Brain has no endpoint that marks `dispatched: true` — new endpoint needed |
| REQ-ws-022 | `/opt/ultra-workshop/workshop/trust_shared.py → /opt/ultra-agents-brain/ultra_brain/trust.py` symlink; `readlink` returns correct target | trust.py confirmed at `/Users/caiobellizzi/Documents/Projects/ultra-agents-brain/ultra_brain/trust.py` |
| REQ-ws-023 | Install writes `vault/_system/integration-contract.md` with vocabulary table | New file; content derived from docs/ingest/PLAN.md vocabulary table |
</phase_requirements>

---

## Summary

Research resolves all three critical decisions (D-01, D-03, D-04). The results require a hybrid substrate: Hermes cron handles the two daily/nightly routines (D-01 CONFIRMED), but the 30s fast-poll requires a systemd service fallback (D-03 ABSENT — Hermes has no always-on/daemon skill primitive). A new Brain endpoint is needed for the dispatched-ACK (D-04 MISSING).

**D-01 — Hermes cron: CONFIRMED.** Hermes 0.14.0 ships a full cron subsystem with standard 5-field cron expressions (`0 7 * * *`, `0 2 * * *`, `0 3 * * *`). Jobs fire in isolated agent sessions, run every 60s tick, and store output in `~/.hermes/cron/jobs.json`. The planner uses Hermes cron for `daily-research`, `nightly-tests`, and the 4h standard-poll + 03:00 rescan legs of `bug-scan`.

**D-03 — Hermes always-on: ABSENT.** The Hermes hook system only supports event-driven hooks (`gateway:startup`, `session:start`, etc.). There is no `daemon:`, `always_on:`, or long-running skill mode. Cron jobs themselves are ephemeral (fresh agent session per tick). The 30s fast-poll on `.workshop-queue.jsonl` cannot be implemented natively in Hermes — the `uws-bug-scan-fastpoll.service` systemd fallback is required.

**D-04 — Brain dispatched-ACK endpoint: MISSING.** `brain_http.call_agent()` routes to 5 registered agents (`chat`, `curator`, `ingest`, `query`, `research`). None accept a structured `dispatched: true` update for a specific queue entry. The `curator` agent takes keyword commands (`digest`, `review`, `lint`, `poll_feeds`) and is the closest candidate, but its tool set (`run_digest`, `run_review`, `lint_vault`, `poll_feeds`) has no queue-mutation capability. Brain needs a new dedicated FastAPI route (`PUT /workshop/queue/{entry_id}/dispatched`) similar to the already-implemented `PUT /workshop/repos` pattern.

**Primary recommendation:** Hermes cron for 4 of 5 scheduled triggers; dedicated systemd service (`uws-bug-scan-fastpoll.service`) for the 30s loop; one new Brain endpoint for dispatched-ACK; `brain_http.call_agent("notify", ...)` path needs a `notify` agent registered in Brain (currently absent — cost.py references it optimistically but it is not in `app.py`'s `agents=[]`).

---

## Critical Decision Resolutions

### D-01: Hermes Cron Primitive

**CONFIRMED** — Hermes 0.14.0 exposes a first-class cron subsystem. `[CITED: hermes-agent.nousresearch.com/docs/user-guide/features/cron]`

**Evidence:**
- Official docs document a `cronjob` tool with `action="create"` and `schedule=` supporting standard 5-field cron expressions.
- `~/.hermes/cron/jobs.json` stores all jobs with atomic write semantics.
- Scheduler runs in a dedicated background thread in gateway mode (`_start_cron_ticker` in `gateway/run.py`), ticking every 60 seconds.
- Each job fires in a fresh, isolated agent session — no conversation history leak.
- Jobs can carry `skills=["skill-name"]` to load Workshop skills before running the prompt.
- Delivery target `telegram:7113965359` sends the result directly to Telegram.

**Constraint confirmed:** Cron jobs run with `cronjob`, `messaging`, and `clarify` toolsets **disabled**. Prompts must be completely self-contained. Skills loaded by cron jobs must not rely on `clarify()` — this means all three routines must handle failures by Telegram-alerting through an external path, not interactive HITL.

**Substrate decision: Hermes-native cron.** Use `cronjob(action="create", schedule="0 7 * * *", ...)` for `daily-research`, `0 2 * * *` for `nightly-tests`, `0 */4 * * *` for standard-poll, `0 3 * * *` for nightly-rescan.

**Cron session timeout:** Default 600s (`HERMES_CRON_TIMEOUT`). Set `HERMES_CRON_TIMEOUT=1800` in `/etc/uws/env` for nightly-tests (clone + run can take >10 min per repo).

---

### D-03: Hermes Always-On Skill

**ABSENT** — Hermes 0.14.0 has no always-on, daemon, or long-running skill primitive. `[CITED: hermes-agent.nousresearch.com/docs/user-guide/features/hooks]`

**Evidence:**
- The hook event system supports: `gateway:startup`, `session:start`, `session:end`, `session:reset`, `agent:start`, `agent:step`, `agent:end`, `command:*`. No `daemon:`, `always_on:`, `loop:`, or persistent-skill event exists.
- Cron jobs are ephemeral — each tick creates a fresh agent session and terminates it after the job completes.
- The `~/.hermes/cron/` directory stores job definitions and outputs, not persistent processes.
- No `startup:` or `always_running:` key is documented in `config.yaml`.

**Runner decision: systemd fallback.** The 30s fast-poll loop requires a dedicated `uws-bug-scan-fastpoll.service` unit running as the `uws` user with an internal `time.sleep(30)` loop. This is the designed fallback per D-03 in 05-CONTEXT.md.

**Restart semantics for the fallback service:**
- `Restart=always` + `RestartSec=5` — recovers from Python exceptions.
- Offset file at `~/.ultra-workshop/state/queue-offset.txt` persists the last-read byte position across restarts (avoids re-dispatching already-seen entries).
- The service should read the offset file on startup and resume from that position.

---

### D-04: Brain Dispatched-ACK Endpoint

**MISSING** — No existing Brain endpoint accepts a `dispatched: true` update for a `.workshop-queue.jsonl` entry. `[VERIFIED: codebase read — agentos/app.py, agentos/workshop_registry.py]`

**Existing Brain agent roster (from `agentos/app.py`):**

| Agent ID | Purpose | Can ACK queue? |
|----------|---------|----------------|
| `chat` | Conversational agent | No |
| `curator` | vault maintenance (digest/review/lint/poll_feeds) | No — no queue tools |
| `ingest` | Writes content to vault | No |
| `query` | RAG search over vault | No |
| `research` | Web research → vault synthesis | No |

The `curator` agent is the closest fit (periodic maintenance), but its tool set is locked to `run_digest`, `run_review`, `lint_vault`, `poll_feeds` — none touch the queue file.

**Precedent for new endpoint:** `agentos/workshop_registry.py` already implements `PUT /workshop/repos` as a FastAPI route injected at the front of the AgentOS router. The same pattern applies here.

**Required new endpoint shape:**

```python
# agentos/workshop_queue.py (new file)
# Route: PUT /workshop/queue/{entry_id}/dispatched
# Body: {"dispatched": true, "dispatched_at": "<ISO timestamp>"}
# Action: reads vault/_system/.workshop-queue.jsonl, finds entry by id,
#         rewrites the line with dispatched=true, atomic write
# Returns: {"ok": true, "id": "<entry_id>"}
# Auth: localhost-only (Brain binds 127.0.0.1:7000, same as /workshop/repos)
```

**Alternative considered (passing `dispatched=true` through `curator` natural language):** NOT viable. The queue file is owned by Brain's vault directory (`/srv/second-brain/_system/`), which the `uws` user cannot write. The curator agent could theoretically parse a message like `mark-dispatched&id=abc123`, but this bypasses schema validation and is fragile. The direct route pattern is already proven and should be replicated.

---

## Technical Findings

### Queue File Schema

**Path:** `vault/_system/.workshop-queue.jsonl` = `/srv/second-brain/_system/.workshop-queue.jsonl` on VPS. `[VERIFIED: 05-CONTEXT.md D-08; docs/ingest/PLAN.md WS-021]`

**Per-line schema (D-08):**
```json
{
  "id": "<ulid or uuid4 hex>",
  "action": "<verb>",
  "confirmed": true,
  "payload": {},
  "created_by": "brain-<source>",
  "created_at": "<ISO-8601>",
  "dispatched": false
}
```

**Vocabulary:**
- `action: "post-to-telegram"` + `confirmed: true` — Brain self-confirming verb; dispatched immediately (even in quiet hours, per L28 zero-HITL exception).
- `action: "fix-bug"` / `action: "link-orphans"` + `confirmed: true` — Human-confirmed; dispatched by standard-poll with quiet-hours deferral.
- `workshop.suggested_action: <verb>` — Set in vault frontmatter by Brain/Workshop autonomous sources; NOT dispatched; surfaces in daily-digest only.

**Offset tracking:** `~/.ultra-workshop/state/queue-offset.txt` stores byte offset of last-read position in the JSONL file. `[VERIFIED: docs/ingest/PLAN.md WS-018]`

**Brain writes, Workshop reads + ACKs.** Workshop never appends or modifies the JSONL file directly — only POSTs `dispatched: true` updates to the new Brain endpoint.

---

### Telegram Alert Path

**Current state:** No `send_telegram` helper exists in the Workshop codebase. The memory observation `23229 11:24a — No send_telegram Helper Exists — ISSUE-04 Fix References a Non-Existent Import Path` is confirmed by reading `brain_http.py` (no Telegram function) and searching Workshop `hermes-skills/`.

**Brain `notify` agent:** Referenced by `workshop/cost.py` as `_brain_http.call_agent("notify", ...)` but the `notify` agent is **NOT registered** in `agentos/app.py`'s `agents=[]` list. Brain registers: `chat`, `curator`, `ingest`, `query`, `research`. Calling `call_agent("notify", ...)` would return HTTP 404 from AgentOS.

**Available Telegram send path in Brain:** `ultra_brain/telegram.py::send_message(text, chat_id=None)` — used by the Brain's `uab-telegram.service` (now disabled per L4/D8). This is a direct `urllib.request` call to the Telegram Bot API. However, Workshop cannot import this directly (different user, different Python environment).

**Recommended Telegram alert path for Phase 5:** Two-option analysis:

**Option A (Preferred): New `hermes-skills/telegram_alert.py` helper**
```python
# hermes-skills/telegram_alert.py
# Direct Telegram Bot API call using TELEGRAM_BOT_TOKEN from environment.
# Called by cron skill bodies: from hermes_skills import telegram_alert; telegram_alert.send(msg)
# No Brain dependency — cron-safe (no clarify/messaging toolset needed).
```
This is the correct path for cron routines because cron sessions have `messaging` toolset disabled. The skill body calls the Bot API directly using the token already in `/etc/uws/env`.

**Option B: Route through Brain `curator` with a `notify` message**
Would require adding a `notify` agent to Brain OR extending `curator` to handle `notify` messages — more work, more coupling.

**Decision for planner:** Implement Option A — a small `hermes-skills/telegram_alert.py` that calls `https://api.telegram.org/bot{token}/sendMessage` directly. This mirrors how `ultra_brain/telegram.py` works on the Brain side. Chat ID `7113965359` is hardcoded (same as `ALLOWED_CHAT_ID` in startup-hitl-scan-hook/handler.py).

**Note for `cost.py` cleanup:** `workshop/cost.py`'s `check_role_budget()` calls `call_agent("notify", ...)` — this is currently a no-op in production (HTTP 404, swallowed by `except Exception: pass`). Phase 5 should either add the `notify` agent to Brain or replace these calls with `telegram_alert.send()`.

---

### Trust Symlink

**Source file confirmed:** `/Users/caiobellizzi/Documents/Projects/ultra-agents-brain/ultra_brain/trust.py` exists locally. `[VERIFIED: filesystem read]`

**VPS deploy path:** `/opt/ultra-agents-brain/ultra_brain/trust.py`

**Required symlink:**
```
/opt/ultra-workshop/workshop/trust_shared.py → /opt/ultra-agents-brain/ultra_brain/trust.py
```

**REQ-ws-022 acceptance test:**
```bash
readlink /opt/ultra-workshop/workshop/trust_shared.py
# Must return: /opt/ultra-agents-brain/ultra_brain/trust.py
python3 -c "
import sys; sys.path.insert(0, '/opt/ultra-workshop')
from workshop import trust_shared
result = trust_shared.classify_action('git push')
print(result.risk)  # should be 'medium'
"
```

**`trust.py` API summary** (read from source):
- `classify_action(description, *, target_path="", private_worker_available=False) -> TrustDecision`
- Returns `TrustDecision(risk, allowed, needs_approval, route, reason, sanitized_text)`
- Risk tiers: `"low"` (auto), `"medium"` (approval required), `"high"` (refused)
- Regex patterns: `HIGH_RISK_RE` (rm -rf, delete repo, drop database...), `MEDIUM_RISK_RE` (write, modify, publish, push, commit, send, email, telegram)

---

### Hermes Hook Events (Complete List)

The following hook events are supported in Hermes 0.14.0 HOOK.yaml files. `[CITED: hermes-agent.nousresearch.com/docs/user-guide/features/hooks]`

| Event | Trigger | Relevant to Phase 5? |
|-------|---------|----------------------|
| `gateway:startup` | Gateway process starts | YES — D-02 catch-up hook |
| `session:start` | New messaging session created | No |
| `session:end` | Session ended | No |
| `session:reset` | User ran `/new` or `/reset` | No |
| `agent:start` | Agent begins processing a message | No |
| `agent:step` | Each iteration of tool-calling loop | No |
| `agent:end` | Agent finishes processing | No |
| `command:*` | Any slash command (wildcard) | No |

**No cron/schedule/daemon/always-on events exist.** `gateway:startup` is the only lifecycle hook available for Phase 5's catch-up pattern (D-02).

---

## Reusable Code Assets

| File | Lines | Reusable API | Phase 5 Usage |
|------|-------|-------------|---------------|
| `workshop/cost.py` | `check_circuit_breaker(mode="cron")` | REQ-ws-019 — all 3 routines call before any LLM dispatch |
| `workshop/cost.py` | `BudgetWarning`, `BudgetExhausted` | Caught in cron routine bodies to trigger Telegram alert |
| `hermes-skills/brain_http.py` | `call_agent(agent_id, message, user_id)` | All Brain calls: `research`, `ingest`, `curator`, `query` |
| `hermes-skills/startup-hitl-scan-hook/HOOK.yaml` | `events: [gateway:startup]` HOOK.yaml pattern | D-02 catch-up hook: same YAML structure, different handler.py |
| `hermes-skills/startup-hitl-scan.py` | `ensure_schema()`, importlib hyphen-name pattern | Reference for state DB bootstrap + importlib for hyphenated filenames |
| `workshop/repo_registry.py` | `list_active_repos(path=None)` | `nightly-tests` iterates active repos with `test_command` set |
| `workshop/ledger.py` | `append_progress(task_id, event, data)` | Per-cron-run audit trail under `~/.ultra-workshop/cron/<routine>/<date>/` |
| `hermes-skills/startup-hitl-scan-hook/handler.py` | `async def handle(event_type, context)` signature | D-02 catch-up hook handler.py — same async signature |
| `agentos/workshop_registry.py` | `register_workshop_routes(app)` + `APIRoute` insert-at-front pattern | D-04 new Brain endpoint follows identical pattern |
| `ultra_brain/telegram.py::send_message` | Direct Bot API call pattern | Reference for `hermes-skills/telegram_alert.py` implementation |

---

## Architecture Patterns

### System Architecture Diagram

```
VPS Clock (systemd)
  │
  ├── [uws-hermes.service] — Hermes gateway
  │     │
  │     ├── Hermes Cron (jobs.json, 60s tick)
  │     │     ├── 07:00 daily-research job → call_agent("research") → call_agent("ingest") → telegram_alert
  │     │     ├── 02:00 nightly-tests job  → list_active_repos() → clone+run → vault write → telegram_alert
  │     │     ├── */4h  standard-poll job  → scan vault → dispatch eligible → Brain ACK
  │     │     └── 03:00 nightly-rescan job → full scan + dedup rebuild
  │     │
  │     └── Hook: gateway:startup → catch-up handler
  │           └── reads /home/uws/.ultra-workshop/cron-state/*.last
  │               → if missed today → run routine immediately
  │
  ├── [uws-bug-scan-fastpoll.service] — new systemd service
  │     └── workshop/bug_scan_fastpoll.py
  │           └── time.sleep(30) loop
  │                 ├── read queue-offset.txt → tail .workshop-queue.jsonl
  │                 ├── filter: action + confirmed=true, not dispatched
  │                 ├── quiet-hours check (22:00–07:00 deferral)
  │                 ├── dispatch verb → hermes skill / telegram_alert
  │                 └── PUT /workshop/queue/{id}/dispatched → Brain
  │
  └── [uab-brain.service] — Brain (Agno AgentOS on 127.0.0.1:7000)
        ├── POST /agents/research/runs   — Brain.research
        ├── POST /agents/ingest/runs     — Brain.ingest
        ├── PUT  /workshop/repos         — existing
        └── PUT  /workshop/queue/{id}/dispatched  — NEW (Phase 5)

Vault (/srv/second-brain/_system/)
  ├── .workshop-queue.jsonl   — Brain writes; fastpoll reads+ACKs
  ├── research-queue.md       — Human edits; daily-research consumes
  ├── workshop-repos.json     — Active repos for nightly-tests
  ├── cost-ledger.md          — Budget tracking
  ├── workshop-cron-log.md    — Cron run history (append-only)
  └── integration-contract.md — Vocabulary spec (REQ-ws-023)
```

### Recommended Project Structure (new files only)

```
hermes-skills/
├── telegram_alert.py          # New — direct Bot API Telegram sender
├── cron-daily-research/       # New Hermes cron skill dir
│   └── SKILL.md
├── cron-nightly-tests/        # New Hermes cron skill dir
│   └── SKILL.md
├── cron-standard-poll/        # New Hermes cron skill dir
│   └── SKILL.md
└── cron-catchup-hook/         # New gateway:startup hook
    ├── HOOK.yaml
    └── handler.py

workshop/
├── bug_scan_fastpoll.py       # New — systemd service entry point (30s loop)
├── daily_research.py          # New — daily-research logic
├── nightly_tests.py           # New — nightly-tests logic
├── vault_poll.py              # New — standard-poll + dedup logic
├── trust_shared.py            # New — symlink target
└── cron_lock.py               # New — single-instance lock per routine

deploy/systemd/
├── uws-bug-scan-fastpoll.service  # New systemd unit

scripts/
└── install.sh                 # Extend: create trust symlink, write integration-contract.md

ultra-agents-brain (separate repo)
└── agentos/
    ├── workshop_queue.py      # New — PUT /workshop/queue/{id}/dispatched route
    └── app.py                 # Extend: register_workshop_queue_routes(app)
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cron scheduling (07:00, 02:00, */4h, 03:00) | Custom Python schedule loop in systemd | Hermes `cronjob(action="create", schedule="0 7 * * *")` | Built-in tick, jobs.json persistence, delivery targets, skill injection |
| Vault file atomic write | `open().write()` | Python `tmp.replace(target)` pattern (already in `workshop_registry.py`) | POSIX atomic rename; prevents partial-read corruption |
| Circuit breaker | Custom budget check | `workshop/cost.py::check_circuit_breaker(mode="cron")` | Already raises `BudgetWarning` at $18 and `BudgetExhausted` at $20 |
| Brain HTTP calls | Raw `httpx.post` with `json=` | `brain_http.call_agent(agent_id, message)` | Handles form-data (not JSON), error logging, SystemExit semantics |
| Active repo iteration | Parse workshop-repos.json manually | `workshop/repo_registry.py::list_active_repos()` | Schema normalization, bootstrap, error handling all done |
| Progress audit log | Custom file writer | `workshop/ledger.py::append_progress()` | JSONL format, thread-safe, task-scoped directories |
| Process single-instance lock | PID file + os.kill | `fcntl.flock()` or `filelock` on `.lock` file | Portable, auto-releases on crash |
| Telegram send (cron context) | `clarify()` or Hermes `messaging` toolset | Direct Bot API via `telegram_alert.py` | Hermes cron disables `messaging` toolset; direct call works in all contexts |

**Key insight:** Hermes cron context disables `clarify`, `messaging`, and `cronjob` toolsets. Any routine that tries to use `clarify()` for HITL will silently fail inside a cron session. All interactive paths must be pre-validated and bypassed in cron mode.

---

## Common Pitfalls

### Pitfall 1: Hermes Cron Disables messaging/clarify Toolsets
**What goes wrong:** A cron skill body calls `clarify()` or uses `send_message` — these are silently unavailable in a cron session. The job hangs on inactivity timeout (600s default).
**Why it happens:** Cron jobs run headless to prevent recursive cron creation and interactive stalls.
**How to avoid:** All Telegram notifications from cron routines must use `telegram_alert.py` (direct Bot API), never Hermes's `clarify` or `messaging` tools. Test by running the skill prompt manually in a cron-simulated context.
**Warning signs:** Cron job output in `~/.hermes/cron/output/` shows empty or truncated responses; Telegram message never arrives.

### Pitfall 2: Brain `notify` Agent Does Not Exist
**What goes wrong:** `cost.py::check_role_budget()` and `check_circuit_breaker()` call `call_agent("notify", ...)` — Brain returns HTTP 404 (no `notify` agent registered in `agentos/app.py`). The exception is swallowed silently.
**Why it happens:** `cost.py` was written optimistically assuming a `notify` agent would be added; it never was.
**How to avoid:** Phase 5 must replace `call_agent("notify", ...)` in `cost.py` with `telegram_alert.send(msg)`, OR add a `notify` agent to Brain. The `telegram_alert.py` helper is already needed for cron alerts — reuse it here.
**Warning signs:** Budget threshold breaches produce no Telegram alert even though `check_role_budget()` does not raise an exception.

### Pitfall 3: Queue Fast-Poll Reprocesses Already-Dispatched Entries After Restart
**What goes wrong:** `uws-bug-scan-fastpoll.service` restarts (crash, systemctl restart). Without a persistent offset, it re-reads the entire queue file and re-dispatches entries where `dispatched: true` was written by Brain but not yet reflected in the local file (vault sync has ~5 min lag).
**Why it happens:** The `dispatched: true` mark lives in Brain's copy of the vault; the local copy may be up to 5 min stale.
**How to avoid:** Use `~/.ultra-workshop/state/queue-offset.txt` as the primary dedup mechanism — store the byte offset of the last fully-processed line. On restart, seek to that offset. Additionally, check `dispatched: true` in the line itself as a secondary guard. The offset file must survive service restarts (written to disk, not memory).
**Warning signs:** Duplicate Telegram approval prompts appearing within 5-minute windows after service restarts.

### Pitfall 4: Hermes Cron Job Timeout for nightly-tests
**What goes wrong:** `nightly-tests` at 02:00 clones multiple repos and runs test commands. Default cron timeout is 600s (10 min). A single repo's test suite could exceed this.
**Why it happens:** `HERMES_CRON_TIMEOUT` defaults to 600. nightly-tests is a sequential loop over potentially many repos.
**How to avoid:** Set `HERMES_CRON_TIMEOUT=1800` in `/etc/uws/env`. Alternatively, set per-job timeout via `cronjob` update if Hermes supports it. Implement a per-repo timeout cap (e.g., 120s per repo) inside the skill body so a single hung test doesn't consume the entire budget.
**Warning signs:** `nightly-tests` cron job output truncated; `~/.hermes/cron/output/nightly-tests/` shows partial results.

### Pitfall 5: Standard-Poll (Hermes Cron) and Fast-Poll (systemd) Double-Dispatching
**What goes wrong:** The fast-poll (30s) and standard-poll (4h) both see the same eligible queue entry and dispatch it twice — once from each service.
**Why it happens:** The `dispatched: true` ACK written by Brain takes up to 5 min to appear in Workshop's local vault copy.
**How to avoid:** The fast-poll service must maintain a local in-memory set of `dispatched_this_session` IDs. On startup, rebuild this set from the queue file's current `dispatched: true` entries. Standard-poll uses the same set + a persistent `~/.ultra-workshop/state/dispatched-ids.jsonl` log. Both poll services check this log before dispatching.
**Warning signs:** Duplicate HITL Telegram prompts for the same entry within a 5-minute window.

### Pitfall 6: Quiet-Hours Deferred Dispatches Lost on Service Restart
**What goes wrong:** `uws-bug-scan-fastpoll.service` holds deferred dispatches in memory (quiet hours 22:00–07:00). Service restarts at 23:00 → deferred entries are lost.
**Why it happens:** In-memory deferred queue not persisted.
**How to avoid:** Write deferred entries to `~/.ultra-workshop/state/deferred-queue.jsonl` before each sleep. On startup, load deferred entries and process them if it's past 07:00.
**Warning signs:** Expected Telegram approval prompts never arrive after overnight VPS maintenance.

---

## Implementation Risks

### RISK-01: Brain codebase is in a separate repo
The new `PUT /workshop/queue/{id}/dispatched` endpoint must be built in `ultra-agents-brain` and deployed to VPS before Phase 5 Workshop code can ACK dispatched entries. This creates a cross-repo deploy dependency.

**Mitigation:** Plan 05-01 (Brain endpoint) must complete before Plan 05-04 (bug-scan dispatch logic). The planner should sequence these plans as a strict dependency chain.

### RISK-02: test_command field missing from existing registry
D-09 requires adding `test_command` to `workshop-repos.json` schema. Existing entries don't have this field. `nightly-tests` must gracefully skip repos where `test_command` is absent or empty — otherwise it errors on every existing registered repo.

**Mitigation:** `list_active_repos()` already returns normalized entries with `setdefault` patterns. `nightly-tests` skill body checks `entry.get("test_command")` and skips if falsy.

### RISK-03: Hermes cron job bootstrap is interactive
`cronjob(action="create", ...)` is a tool call — it must be executed inside a Hermes agent session, not from a script. The planner needs a Wave 0 bootstrap step that triggers Hermes to create the 4 cron jobs (daily-research, nightly-tests, standard-poll, nightly-rescan) on first deploy.

**Mitigation:** Install script sends a Telegram message (or calls Hermes API) to create the jobs. Alternative: Hermes supports a `script:` field in cron jobs and a startup hook could call `cronjob create` if jobs.json is empty. Simplest path: include a `scripts/bootstrap-cron-jobs.sh` that sends a `hermes api` call to create the jobs.

### RISK-04: 5-minute vault sync lag vs 30s fast-poll
`.workshop-queue.jsonl` reaches Workshop via git sync (caiobellizzi/second-brain, every 5 min). Fast-poll reads the local clone. A Brain-written entry may take up to 5 min to appear. REQ-ws-021 requires "within 30s of Brain writing" — this is only achievable if Workshop reads from the canonical vault path directly (`/srv/second-brain/_system/.workshop-queue.jsonl`), not from a synced copy.

**Resolution:** Both Brain and Workshop run on the same VPS. Workshop's `/srv/second-brain` is the same filesystem path Brain writes to. There is no sync lag on the VPS — the 5 min sync is for the Mac Obsidian copy. The fast-poll service on the VPS reads directly from `/srv/second-brain/_system/.workshop-queue.jsonl`. `[VERIFIED: 05-CONTEXT.md integration points section — vault sync is Mac↔VPS; VPS processes share the same filesystem]`

---

## Recommended Plan Breakdown

### Plan 05-01: Brain Dispatcher Endpoint (cross-repo, blocking dependency)
**Scope:** `ultra-agents-brain` repo. Add `agentos/workshop_queue.py` with `PUT /workshop/queue/{entry_id}/dispatched` route. Register in `app.py`. Deploy to VPS.

**Why first:** Plans 05-03 and 05-04 depend on this endpoint existing before they can ACK dispatched entries.

### Plan 05-02: Hermes Cron Routines (daily-research + nightly-tests)
**Scope:** `hermes-skills/cron-daily-research/`, `hermes-skills/cron-nightly-tests/`, `hermes-skills/telegram_alert.py`, `workshop/daily_research.py`, `workshop/nightly_tests.py`, cron catch-up startup hook, marker files.

**Includes:**
- `telegram_alert.py` helper (shared dependency for all alert paths)
- `cost.py` fix: replace `call_agent("notify", ...)` with `telegram_alert.send()`
- `hermes-skills/cron-catchup-hook/` (HOOK.yaml + handler.py) for D-02
- Bootstrap script to create cron jobs in Hermes

### Plan 05-03: Bug-Scan Fast-Poll Service
**Scope:** `workshop/bug_scan_fastpoll.py`, `deploy/systemd/uws-bug-scan-fastpoll.service`, offset file + deferred-queue persistence.

**Includes:**
- Vocabulary-split dispatch logic (L28)
- Quiet-hours deferral (L29)
- Single-instance lock
- Offset + dispatched-ids dedup

### Plan 05-04: Hermes Standard-Poll + Nightly-Rescan + Integration Contract
**Scope:** `hermes-skills/cron-standard-poll/`, `workshop/vault_poll.py`, `workshop/trust_shared.py` symlink, `vault/_system/integration-contract.md` install.

**Includes:**
- 4h standard-poll Hermes cron skill
- 03:00 nightly-rescan Hermes cron skill
- `scripts/install.sh` extension for trust symlink creation
- Integration contract file written by install script

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `/srv/second-brain/_system/.workshop-queue.jsonl` on VPS is written and readable by both Brain (`uabrain` user) and Workshop (`uws` user) via shared group or world-readable permissions | Queue Schema | fast-poll can't read the queue; would need a dedicated read endpoint |
| A2 | `uws-bug-scan-fastpoll.service` running as `uws` user has read access to `/srv/second-brain/_system/` | Architecture | systemd service needs supplementary group membership |
| A3 | Hermes cron jobs survive `systemctl restart uws-hermes` — `jobs.json` is persisted at `~/.hermes/cron/jobs.json` | D-01 | cron jobs lost on restart; bootstrap script needs to be idempotent |
| A4 | Brain's AgentOS runs on `127.0.0.1:7000` (same as existing) when the new queue endpoint is added | D-04 | Workshop's `brain_http.py` BRAIN_BASE_URL needs updating |
| A5 | `HERMES_CRON_TIMEOUT` env var is respected by Hermes 0.14.0 | Pitfall 4 | nightly-tests may hit default 600s timeout on repos with slow test suites |

**If A1 is wrong:** Add a `GET /workshop/queue` endpoint to Brain that returns pending (undispatched) entries. Workshop polls this endpoint instead of reading the file directly.

---

## Open Questions (RESOLVED)

1. **Hermes cron bootstrap mechanism** — RESOLVED: Use `bootstrap_cron_jobs.py` called from `scripts/install.sh` via `hermes skill run`. No static `config.yaml` block exists for cron job declaration; jobs are created programmatically via the `cronjob` tool inside a Hermes session. Confirmed by absence of any `cron:` key in `config.yaml` and research finding D-01.

2. **`/srv/second-brain` filesystem permissions** — RESOLVED: 05-04 Task 3 (install script additions) includes a permission verification step: `sudo -u uws ls /srv/second-brain/_system/`. If access is denied, the install script adds `uws` to the `second-brain` group or fixes the directory group permissions (chmod g+rx) before proceeding. This gate runs before the cron bootstrap step.

3. **Hermes cron delivery target for `daily-research`** — RESOLVED: Use `deliver=None` in all `cronjob(action="create", ...)` calls. Telegram notifications are sent explicitly via `telegram_alert.py` inside each cron skill body. This gives full control over message formatting (vault links, emoji prefixes) and avoids any dependency on Hermes's internal delivery adapter behavior.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Hermes cron subsystem | D-01 | ✓ | 0.14.0 (confirmed) | — |
| systemd (VPS) | D-03 fast-poll service | ✓ | systemd 249+ | — |
| `/srv/second-brain/_system/` read access for `uws` | fast-poll reads queue | UNKNOWN | — | Brain `GET /workshop/queue` endpoint |
| `workshop-repos.json` `test_command` field | nightly-tests | ✗ (field not in schema yet) | — | Schema extension in Plan 05-02 |
| `ultra-agents-brain` new queue endpoint | dispatched ACK | ✗ (not built yet) | — | Workshop writes dedup state locally (risky) |
| `hermes-skills/telegram_alert.py` | All cron alert paths | ✗ (not built yet) | — | Must be built in Plan 05-02 |
| `HERMES_CRON_TIMEOUT` in `/etc/uws/env` | nightly-tests | ✗ (not set yet) | — | Default 600s (risky for slow test suites) |

**Missing dependencies with no fallback:**
- Brain `PUT /workshop/queue/{id}/dispatched` endpoint — Workshop dispatch ACK is architecturally blocked until Brain is updated.

**Missing dependencies with fallback:**
- `/srv/second-brain` `uws` read access — fallback: Brain `GET /workshop/queue` read endpoint.
- `HERMES_CRON_TIMEOUT` — fallback: default 600s (acceptable for initial deploy, risky for large repos).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing), bash smoke scripts |
| Config file | `pytest.ini` / `pyproject.toml` (existing) |
| Quick run command | `pytest tests/phase-05/ -x -q` |
| Full suite command | `pytest tests/phase-05/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-ws-016 | daily-research skill reads research-queue.md, calls Brain.research | unit (mocked Brain) | `pytest tests/phase-05/test_daily_research.py -x` | ❌ Wave 0 |
| REQ-ws-017 | nightly-tests iterates active repos, runs test_command, writes vault | unit (mocked subprocess) | `pytest tests/phase-05/test_nightly_tests.py -x` | ❌ Wave 0 |
| REQ-ws-018 | fast-poll reads queue, dispatches on action+confirmed=true, defers in quiet hours | unit | `pytest tests/phase-05/test_bug_scan_fastpoll.py -x` | ❌ Wave 0 |
| REQ-ws-019 | check_circuit_breaker(mode="cron") raises BudgetWarning at $18 | unit | `pytest tests/workshop/test_cost.py -k cron` | ✅ (existing) |
| REQ-ws-020 | Flow B: vault file with action+confirmed triggers dispatch | integration (synthetic vault file) | `pytest tests/phase-05/test_flow_b.py -x` | ❌ Wave 0 |
| REQ-ws-021 | Flow E: queue entry with post-to-telegram dispatches within 30s | smoke (VPS only) | `bash scripts/smoke-test-phase5.sh --flow-e` | ❌ Wave 0 |
| REQ-ws-022 | readlink returns correct trust.py target | smoke | `bash scripts/smoke-test-phase5.sh --trust-symlink` | ❌ Wave 0 |
| REQ-ws-023 | integration-contract.md exists with vocabulary table | smoke | `bash scripts/smoke-test-phase5.sh --integration-contract` | ❌ Wave 0 |

### Wave 0 Gaps
- [ ] `tests/phase-05/test_daily_research.py` — covers REQ-ws-016
- [ ] `tests/phase-05/test_nightly_tests.py` — covers REQ-ws-017
- [ ] `tests/phase-05/test_bug_scan_fastpoll.py` — covers REQ-ws-018 (vocabulary split, quiet hours, offset tracking)
- [ ] `tests/phase-05/test_flow_b.py` — covers REQ-ws-020
- [ ] `scripts/smoke-test-phase5.sh` — covers REQ-ws-021, 022, 023
- [ ] `tests/phase-05/conftest.py` — shared fixtures (mocked Brain HTTP, mock vault files)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Cron routines are server-side only, no user auth |
| V3 Session Management | no | Hermes cron sessions are ephemeral, no user sessions |
| V4 Access Control | yes | systemd `User=uws`; fast-poll service must not run as root; `/srv/second-brain` permissions |
| V5 Input Validation | yes | `test_command` from registry must not allow shell injection; `brain_http.call_agent` input sanitization |
| V6 Cryptography | no | No custom crypto; Telegram token in `/etc/uws/env` (0640) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| `test_command` shell injection | Tampering | Run via `subprocess.run(shlex.split(cmd), shell=False)` — never `shell=True` |
| Queue entry action injection | Tampering | Validate `action` against allowlist: `["post-to-telegram", "fix-bug", "fix-test-failure", "link-orphans", "research"]` before dispatch |
| Telegram alert flooding | Denial of Service | Single-alert-per-day-per-threshold enforcement in `check_circuit_breaker`; alert dedup state in `~/.ultra-workshop/state/alerts-today.json` |
| Vault path traversal via `research-queue.md` entry | Information disclosure | Sanitize research topic strings before passing to `call_agent("research", ...)` — strip path separators and shell metacharacters |

---

## Sources

### Primary (HIGH confidence)
- `hermes-agent.nousresearch.com/docs/user-guide/features/cron` — Full cron API: schedule formats, `cronjob` tool, job schema, timeout behavior, toolset restrictions [CITED]
- `hermes-agent.nousresearch.com/docs/user-guide/features/hooks` — Complete hook event type list; `gateway:startup` confirmed as the only lifecycle hook [CITED]
- `/Users/caiobellizzi/Documents/Projects/ultra-workshop/hermes-skills/brain_http.py` — Brain agent IDs: `chat`, `curator`, `ingest`, `query`, `research`; multipart form-data requirement [VERIFIED: codebase]
- `/Users/caiobellizzi/Documents/Projects/ultra-agents-brain/agentos/app.py` — Brain registered agents confirm no `notify` agent; `PUT /workshop/repos` precedent [VERIFIED: codebase]
- `/Users/caiobellizzi/Documents/Projects/ultra-agents-brain/agentos/workshop_registry.py` — `register_workshop_routes()` pattern for new endpoint [VERIFIED: codebase]
- `/Users/caiobellizzi/Documents/Projects/ultra-agents-brain/ultra_brain/trust.py` — trust.py exists locally; API surface confirmed [VERIFIED: codebase]
- `/Users/caiobellizzi/Documents/Projects/ultra-workshop/.planning/phases/05-autonomous-routines-integration-loops/05-CONTEXT.md` — Locked decisions D-01 through D-11 [VERIFIED: codebase]

### Secondary (MEDIUM confidence)
- WebSearch: `hermes-agent NousResearch 0.14.0 cron schedule hook events HOOK.yaml` — confirmed cron subsystem architecture, `cron/scheduler.py` existence, GitHub issue #21172 for loop contract [CITED: hermes-agent.nousresearch.com]
- `/Users/caiobellizzi/Documents/Projects/ultra-workshop/.planning/phases/02-hermes-deploy/02-RESEARCH.md` — VPS state, hook system constraints, FTS5 behavior [CITED: prior research]

### Tertiary (LOW confidence)
- WebFetch of `hermes-agent.nousresearch.com/docs/user-guide/configuration` — confirmed no `cron:` or `schedule:` block in config.yaml for static job declaration [single source, no cross-reference]

---

## Metadata

**Confidence breakdown:**
- D-01 (Hermes cron): HIGH — official docs verified, cron subsystem is documented and stable
- D-03 (always-on absent): HIGH — official hooks page enumerates all events; no daemon primitive exists
- D-04 (Brain endpoint missing): HIGH — verified by reading all Brain agent registrations in app.py
- Telegram alert path: HIGH — codebase confirms no existing helper; direct Bot API is the correct pattern
- Assumptions A1/A2 (filesystem permissions): LOW — not verified on VPS; must check at execute time

**Research date:** 2026-05-28
**Valid until:** 2026-06-28 (Hermes cron API is mature; Brain endpoint is greenfield — won't change)
