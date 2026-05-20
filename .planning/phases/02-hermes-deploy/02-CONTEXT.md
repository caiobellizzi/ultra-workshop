# Phase 2 Context: Hermes Deploy

**Created:** 2026-05-20
**Status:** Context captured — no gray areas required user discussion

---

## Domain

Install Hermes Agent v0.14.0 on the VPS as a systemd service (`uws-hermes.service`), wire the Telegram gateway exclusively to Hermes (replacing Brain's `uab-telegram.service`), and register the 5 MCP servers. HITL approval state must survive `systemctl restart` via Hermes FTS5.

---

## Locked Requirements (from REQUIREMENTS.md + ROADMAP.md)

- **REQ-ws-001** — Hermes systemd service under `/opt/ultra-workshop/`, `After=uab-brain.service`, `systemctl status uws-hermes` → `active (running)`
- **REQ-ws-002** — Telegram bot gated on chat ID `7113965359` only; `/start` reply within 5s
- **REQ-ws-013** — Brain's `uab-telegram.service` must be `inactive (dead)` before Hermes Telegram comes up
- **REQ-ws-014** — Restart resilience: HITL pause survives `systemctl restart uws-hermes` via Hermes FTS5
- **REQ-ws-015** — 5 MCPs registered: `github`, `context7`, `crawl4ai`, `hostinger-api`, `google-workspace`

---

## Carried Forward from PROJECT.md (LOCKED — do not re-decide)

- **L2** — Orchestrator = Hermes Agent v0.14.0 (pinned, no upgrade)
- **L4** — Hermes exclusively owns Telegram gateway; Brain's `uab-telegram.service` disabled
- **L5** — Same Hostinger VPS as Brain (srv1381850, 31.97.130.253)
- **L7** — **PRE-DEPLOY GATE:** Rotate Telegram bot token via BotFather `/revoke` BEFORE service install
- **L9** — All LLM calls via LiteLLM proxy at `127.0.0.1:4000`
- **L26** — Update LiteLLM `private-worker` timeout to 30s and rsync to VPS during this phase
- **D8** — Brain's `uab-telegram.service` stays disabled post-deploy (not just stopped)

---

## Decisions (this phase)

User explicitly deferred all open gray areas to downstream agents (researcher + planner discretion). The following items are NOT pre-decided and should be resolved during research/planning with sensible production defaults:

1. **Service hardening posture** — Planner picks systemd unit hardening (User/Group, ProtectSystem, MemoryMax, NoNewPrivileges, RestartSec). Recommend dedicated `uws` user, `ProtectSystem=strict`, `ProtectHome=true`, `NoNewPrivileges=true`, `MemoryMax` headroom for Aider subprocess (~200MB baseline + workload).
2. **MCP credential storage** — Planner picks storage layout. Recommend single `EnvironmentFile=/etc/uws/env` (root:uws 0640) for Phase 2; revisit systemd-creds in a later phase.
3. **google-workspace OAuth bootstrap** — Planner picks bootstrap path (tunnel, pre-auth + copy token, or defer MCP). Phase 2 success criteria require all 5 MCPs registered — deferring is NOT acceptable; researcher should investigate headless OAuth completion path.
4. **Restart-resilience smoke test (V14)** — Planner defines exact scripted scenario. Recommend: dispatch a synthetic HITL-paused flow, run `systemctl restart uws-hermes`, confirm FTS5 row persists, simulate Approve, observe completion.

---

## Pre-Deploy Gates (BLOCKING — must clear before any deploy step)

1. **Telegram bot token rotated** via BotFather `/revoke` and new token stored on VPS (L7)
2. **`uab-telegram.service` stopped + disabled + masked** on VPS (REQ-ws-013, D8)
3. **VPS RAM headroom** — `free -h` confirms ≥ 2GB free after Brain running; add 2GB swap if not
4. **Phase 1 vault sync verified live** (STATE.md confirms complete)

---

## Canonical Refs

| Path | Why |
|---|---|
| `.planning/PROJECT.md` | Locked architectural decisions L1–L30, D1–D10 (MUST read before planning) |
| `.planning/REQUIREMENTS.md` | REQ-ws-001, 002, 013, 014, 015 acceptance criteria |
| `.planning/ROADMAP.md` | Phase 2 success criteria (5 items) |
| `docs/ingest/PLAN.md` | Original SPEC (post-grill v3) — source of all REQs |

No external ADRs/specs beyond the above. Hermes Agent docs (v0.14.0) and the 5 MCP server docs are external dependencies — researcher should fetch via Context7.

---

## Code Context

No Workshop code exists yet. Phase 2 is a deployment phase, not a coding phase. Artifacts produced:
- `deploy/systemd/uws-hermes.service` (systemd unit)
- `hermes-config/hermes.toml`, `hermes-config/gateway-telegram.toml`, `hermes-config/mcps.toml`
- `scripts/install.sh` (idempotent VPS installer)
- `/etc/uws/env` (credentials, off-repo)

Reuse from Phase 1: VPS host already provisioned, `uabrain` user exists, vault git sync proven, SSH key infrastructure in place. Workshop will run under a NEW user (`uws`, recommended) — not as `uabrain`.

---

## Deferred Ideas

None captured this session.
