# Phase 5: Autonomous Routines & Integration Loops - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-24
**Phase:** 5-autonomous-routines-integration-loops
**Areas discussed:** Cron scheduling substrate, bug-scan fast-poll runner shape, Queue & signal file schemas, nightly-tests + failure/notification policy

---

## Cron scheduling substrate

| Option | Description | Selected |
|--------|-------------|----------|
| systemd .timer units | Recommended. One .timer + .service pair per routine; OnCalendar=, Persistent=true, journalctl observability. | |
| Hermes built-in cron skill | Stays in Hermes ecosystem; survives whatever Hermes survives. Risk: unverified primitive in 0.14.0. | ✓ |
| Plain OS crontab | Simplest, weakest observability, no catch-up. | |
| systemd timers + dedicated long-running bug-scan service | Two mechanisms — timers for daily-research/nightly-tests, persistent service for fast-poll. | |

**User's choice:** Hermes built-in cron skill
**Notes:** Researcher must verify Hermes 0.14.0 actually exposes a cron primitive. If absent, fall back to systemd .timer units (documented in CONTEXT.md D-01).

### Follow-up — Catch-up policy

| Option | Description | Selected |
|--------|-------------|----------|
| Run once on restart if missed today | Marker file per routine; bounded — one catch-up per day. | ✓ |
| Skip missed runs entirely | Simpler; risk of silent gaps. | |
| Catch-up daily-research only | Research queue accumulates; tests are state-of-the-moment. | |
| Researcher decides based on Hermes primitive capabilities | Defer to research. | |

**User's choice:** Run once on restart if missed today
**Notes:** Applies to both Hermes-native and systemd-fallback substrates.

---

## bug-scan fast-poll runner shape

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated systemd service with internal sleep loop | Independent of Hermes; predictable resource footprint. | |
| Hermes long-running skill triggered at startup | Stays inside Hermes; unverified primitive. | ✓ |
| inotifywait watcher | Zero idle CPU; risk on file rotation. | |
| Hermes built-in cron at 30s tick | Aggressive — most schedulers don't fire reliably below 60s. | |

**User's choice:** Hermes long-running skill triggered at startup
**Notes:** Researcher must verify Hermes 0.14.0 supports always-on skills. Fallback: dedicated `uws-bug-scan-fastpoll.service`.

### Follow-up — Dedup mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Byte-offset cursor in state file | Cheap, survives restarts; needs rotation/truncation detection. | |
| Per-entry processed-set in SQLite | Robust; grows unbounded. | |
| Brain marks entries `dispatched: true` after Workshop ACKs | Brain is single writer; D7-compliant. | ✓ |
| Append-only `.workshop-queue.processed.jsonl` mirror | Two files to sync, more git noise. | |

**User's choice:** Brain marks entries `dispatched: true` after Workshop ACKs
**Notes:** Researcher must confirm whether Brain's existing `curator` / `ingest` endpoints can accept this update, or whether a new Brain endpoint is required.

---

## Queue & signal file schemas

| Option | Description | Selected |
|--------|-------------|----------|
| Markdown task list with frontmatter per entry | `- [ ] question` + id/priority attributes; status flips on consumption. Human-editable in Obsidian, diffable in git. | ✓ |
| JSONL queue (rename to research-queue.jsonl) | Structured, atomic line-append; less Obsidian-friendly. | |
| Markdown table with status column | Readable; awkward for atomic writes. | |
| Frontmatter-per-note in `vault/_system/research-queue/` directory | Cleaner state model; more file churn. | |

**User's choice:** Markdown task list with frontmatter per entry

### Follow-up — integration-contract.md scope

| Option | Description | Selected |
|--------|-------------|----------|
| Vocabulary table + flow diagrams | Recommended. Single file ~150 lines covering all `workshop.*` fields + Flow A/B/D/E diagrams. | ✓ |
| Vocabulary table only | Smaller; future agents miss flow context. | |
| Vocabulary + flows + worked examples | Most thorough; most maintenance. | |
| Vocabulary table + link out to per-flow docs | Easier flow evolution; spec spread across N files. | |

**User's choice:** Frontmatter vocabulary table + flow diagrams

---

## nightly-tests + failure/notification policy

| Option | Description | Selected |
|--------|-------------|----------|
| Optional `test_command` field in `workshop-repos.json` | Explicit; no convention guessing. | ✓ |
| Convention discovery only | Probes scripts/test.sh, Makefile, package.json; silent on missing. | |
| Registry field + convention fallback | Best of both; more code paths. | |
| Skip nightly-tests entirely in this phase | Defer REQ-ws-017 to a follow-up plan. | |

**User's choice:** Optional `test_command` field in `workshop-repos.json`
**Notes:** Extends the Phase 6 registry schema. Repos without `test_command` are skipped with a "no test command configured" log entry.

### Follow-up — Failure UX

| Option | Description | Selected |
|--------|-------------|----------|
| Single Telegram alert per failure | Recommended. One concise message + vault log entry. | ✓ |
| Silent fail, log only | Lowest noise; risk of silent rot. | |
| Retry-then-alert | Avoids flaky-network spurious alerts; more code. | |
| Severity-tiered alerts | Most nuanced; most code. | |

**User's choice:** Single Telegram alert per failure

### Follow-up — Daily-research Telegram delivery

| Option | Description | Selected |
|--------|-------------|----------|
| Short summary + link to vault note | Telegram clean; user opens Obsidian for body. D1-compliant via Brain.ingest to `vault/Inbox/`. | ✓ |
| Full text, split into ~4KB messages | Noisy, hard to re-find. | |
| Title + first para + 'reply MORE' | Adds an interactive primitive Workshop lacks. | |
| Title + bullet summary + vault link | Useful preview; extra LLM call (~$0.001). | |

**User's choice:** Short summary + link to vault note

---

## Claude's Discretion

Areas where the user deferred to Claude / planner (captured in CONTEXT.md `<decisions>` § "Claude's Discretion"):
- Marker file format for catch-up tracking
- Quiet-hours implementation detail (queue-and-replay vs skip-until-next)
- Trust symlink installation home (existing `scripts/install.sh` recommended)
- `workshop-cron-log.md` rotation / archival
- Concrete Telegram alert chat plumbing (existing Hermes skill vs new `telegram_alert.py` helper)

## Deferred Ideas

Captured in CONTEXT.md `<deferred>`:
- Retry-then-alert and severity-tiered alert policies (revisit if alert fatigue appears)
- Convention-based test command discovery (revisit if registry maintenance becomes tedious)
- Summary-bullet Telegram delivery for daily-research (revisit if vault-link-only proves friction)
- `/status <task_id>` mid-run inspection command (still deferred from Phase 4)
- Concurrent-run isolation across `/build` invocations (deferred from Phase 4; Phase 5 routines should at minimum guard against same-routine overlap)
