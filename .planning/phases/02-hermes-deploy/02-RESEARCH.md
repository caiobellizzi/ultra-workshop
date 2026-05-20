# Phase 2: Hermes Deploy — Research

**Researched:** 2026-05-20
**Domain:** Hermes Agent v0.14.0 systemd deployment, Telegram gateway, MCP registration, headless OAuth
**Confidence:** MEDIUM (Hermes is ~8 months old, docs verified via official site; FTS5 HITL behavior has a critical gap — see § Pitfall 1)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **L2** — Orchestrator = Hermes Agent v0.14.0 (pinned, no upgrade)
- **L4** — Hermes exclusively owns Telegram gateway; Brain's `uab-telegram.service` disabled
- **L5** — Same Hostinger VPS (srv1381850, 31.97.130.253)
- **L7** — Rotate Telegram bot token via BotFather `/revoke` BEFORE service install
- **L9** — All LLM calls via LiteLLM proxy at `127.0.0.1:4000`
- **L26** — Update LiteLLM `private-worker` timeout to 30s and rsync to VPS during this phase
- **D8** — Brain's `uab-telegram.service` stays disabled post-deploy (not just stopped)

### Claude's Discretion
1. **Service hardening posture** — systemd unit hardening (User/Group, ProtectSystem, MemoryMax, NoNewPrivileges, RestartSec)
2. **MCP credential storage** — EnvironmentFile layout; recommend `/etc/uws/env` (root:uws 0640)
3. **google-workspace OAuth bootstrap** — headless path; NOT deferrable
4. **Restart-resilience smoke test (V14)** — exact scripted scenario

### Deferred Ideas (OUT OF SCOPE)
None.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-ws-001 | Hermes systemd service under `/opt/ultra-workshop/`, `After=uab-brain.service`, `systemctl status uws-hermes` → `active (running)` | § Standard Stack + Architecture Patterns: unit file template |
| REQ-ws-002 | Telegram bot gated on chat ID `7113965359` only; `/start` reply within 5s | § Telegram Config: `TELEGRAM_ALLOWED_USERS` env var |
| REQ-ws-013 | Brain's `uab-telegram.service` must be `inactive (dead)` before Hermes Telegram comes up | § Pre-Deploy Gates + unit ordering |
| REQ-ws-014 | HITL pause survives `systemctl restart uws-hermes` via Hermes FTS5 | § CRITICAL FINDING: `delegate_task` is NOT durable — see Pitfall 1 |
| REQ-ws-015 | 5 MCPs registered: `github`, `context7`, `crawl4ai`, `hostinger-api`, `google-workspace` | § Standard Stack + MCP Config Pattern |
</phase_requirements>

---

## Summary

Phase 2 deploys Hermes Agent v0.14.0 as a hardened systemd service (`uws-hermes.service`) under a dedicated `uws` system user, wires the Telegram gateway exclusively to this service, and registers 5 MCP servers. The deployment pattern is well-documented and straightforward — Hermes provides a standard installer and config.yaml schema.

**Critical finding (REQ-ws-014):** `delegate_task` is explicitly documented as NOT durable across restarts. The Hermes FTS5 store (`~/.hermes/state.db`) persists session history and message content, but in-flight `delegate_task` coroutines (including pending `clarify` HITL callbacks) are NOT re-hydrated after a `systemctl restart`. REQ-ws-014's acceptance criterion requires this to "resume cleanly" — the planner must implement a workaround using Hermes's `terminal(background=True)` + FTS5 state polling rather than relying on `delegate_task` alone.

**google-workspace OAuth:** Fully solvable headlessly via service account mode (key file + `USER_GOOGLE_EMAIL`) or one-time interactive OAuth on a local machine followed by refresh token export. The service account path is preferred for VPS because it never expires.

**VPS state at research time:** Python 3.12.3 installed, Node.js/npm/uv NOT installed, no swap (0B), `uab-telegram.service` still active (running — must be stopped/disabled/masked as pre-deploy gate), `uws` user does not exist, FTS5 module available in Python's sqlite3.

**Primary recommendation:** Use `sudo hermes gateway install --system` via the official installer, then layer the hardened unit file on top. Do NOT hand-roll the installer — it handles uv, Node.js, binary symlinking, and config scaffolding.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Telegram message routing | Hermes gateway process | systemd (lifecycle) | Hermes owns the bot token + long-polling loop |
| HITL approval state | Hermes FTS5 (SQLite WAL) | JSONL session transcripts | FTS5 is the durable store; in-flight coroutines are NOT persisted |
| MCP tool dispatch | Hermes process (config.yaml mcp_servers) | Each MCP subprocess | Hermes launches, handshakes, and reconnects MCP servers |
| Credential storage | `/etc/uws/env` (EnvironmentFile) | — | Single file, root:uws 0640, not in git |
| Service lifecycle | systemd (`uws-hermes.service`) | — | Restart, boot persistence, resource limits |
| LLM routing | LiteLLM proxy (127.0.0.1:4000) | — | L9 locked; Hermes config.yaml `model:` points here |

---

## Standard Stack

### Core

| Library / Package | Version | Purpose | Why Standard |
|-------------------|---------|---------|--------------|
| hermes-agent | 0.14.0 (pinned) | Orchestrator, gateway, MCP client | L2 locked |
| `@modelcontextprotocol/server-github` | 2025.4.8 | GitHub MCP stdio server | Official MCP reference impl |
| `@upstash/context7-mcp` | 2.2.5 | Context7 docs MCP stdio server | Official Upstash package |
| `crawl4ai-mcp-sse-stdio` | 1.2.1 | Crawl4AI MCP bridge (SSE→stdio) | Connects to existing Crawl4AI Docker container |
| `hostinger-api-mcp` | 0.2.1 | Hostinger API MCP stdio server | Official Hostinger package |
| `workspace-mcp` | 1.21.0 | Google Workspace MCP (PyPI/uvx) | Official taylorwilsdon/google_workspace_mcp |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| uv | latest | Python + venv management for Hermes | Hermes installer uses it |
| Node.js | 24.x (LTS) | Required for npm MCP servers (github, context7, crawl4ai, hostinger) | All 4 npm-based MCPs need node |
| nvm | latest | Node version management on VPS | Hostinger docs require Node ≥24 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `crawl4ai-mcp-sse-stdio` | Raw SSE URL `http://localhost:11235/mcp/sse` | Hermes supports `url:` for SSE natively — no npm package needed if Crawl4AI Docker already running |
| Service account OAuth | One-time refresh token export | Simpler for single-user; service account requires GCP project + DWD config |

**Installation (VPS):**
```bash
# 1. Install Node.js 24 via nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
source ~/.bashrc
nvm install 24 && nvm use 24

# 2. Install Hermes
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | HERMES_INSTALL_DIR=/opt/ultra-workshop/hermes bash

# 3. Install npm MCP servers globally (as uws user)
npm install -g @modelcontextprotocol/server-github @upstash/context7-mcp crawl4ai-mcp-sse-stdio hostinger-api-mcp

# 4. Install google-workspace MCP (Python/uvx)
uvx workspace-mcp --tool-tier core   # run once to warm cache; configure via env
```

---

## Package Legitimacy Audit

> slopcheck was not available at research time. All packages verified against official registries and authoritative sources.

| Package | Registry | Source Repo | Auth Source | npm postinstall | Disposition |
|---------|----------|-------------|-------------|-----------------|-------------|
| `@modelcontextprotocol/server-github` | npm 2025.4.8 | github.com/modelcontextprotocol/servers | Official MCP org | none | Approved `[CITED: modelcontextprotocol.io]` |
| `@upstash/context7-mcp` | npm 2.2.5 | github.com/upstash/context7 | Official Upstash | none | Approved `[CITED: context7.com/docs]` |
| `crawl4ai-mcp-sse-stdio` | npm 1.2.1 | github.com/stgmt/crawl4ai-mcp | Community; low downloads | none | `[ASSUMED]` — planner must add checkpoint:human-verify before install |
| `hostinger-api-mcp` | npm 0.2.1 | github.com/hostinger/api-mcp-server | Official Hostinger | none (build script only) | Approved `[CITED: hostinger.com/support/11079316-hostinger-api-mcp-server]` |
| `workspace-mcp` | PyPI 1.21.0 | github.com/taylorwilsdon/google_workspace_mcp | Community but high activity, 80+ releases | N/A (Python) | `[ASSUMED]` — planner must add checkpoint:human-verify |

**Packages removed due to slopcheck [SLOP] verdict:** none

**Packages flagged as suspicious [SUS]:** `crawl4ai-mcp-sse-stdio` (community package, unknown download volume), `workspace-mcp` (community, not Google-official). Planner must insert `checkpoint:human-verify` before each install.

**Alternative for crawl4ai:** Since the Crawl4AI Docker container already runs on the VPS at `http://localhost:11235/mcp/sse`, Hermes can register it directly as an SSE URL in `config.yaml` without any npm package. This is the preferred approach. `[CITED: hermes-agent.nousresearch.com/docs/user-guide/features/mcp]`

---

## Architecture Patterns

### System Architecture Diagram

```
Telegram ──► [Hermes Gateway] ──► [config.yaml mcp_servers]
                  │                    ├── github (npx stdio)
                  │                    ├── context7 (npx stdio)
                  │                    ├── crawl4ai (SSE url: localhost:11235)
                  │                    ├── hostinger-api (npx stdio)
                  │                    └── workspace-mcp (uvx stdio)
                  │
                  ├── ~/.hermes/state.db (SQLite WAL + FTS5)
                  │        └── sessions, messages, messages_fts
                  │
                  └── LiteLLM proxy (127.0.0.1:4000)
                           └── private-worker → LM Studio / cloud fallback

systemd ──► uws-hermes.service
               ├── User=uws / Group=uws
               ├── EnvironmentFile=/etc/uws/env
               ├── After=uab-brain.service network-online.target
               └── MemoryMax=4G (Aider subprocess headroom)
```

### Recommended Project Structure
```
/opt/ultra-workshop/
├── hermes/                   # Hermes install dir (HERMES_INSTALL_DIR)
│   └── hermes-agent/         # cloned repo
├── hermes-config/            # symlinked or copied from repo
│   ├── config.yaml           # main Hermes config (no secrets)
│   └── SOUL.md               # agent identity
└── deploy/
    └── systemd/
        └── uws-hermes.service

/etc/uws/
└── env                       # root:uws 0640 — all secrets here

~uws/.hermes/                 # Hermes runtime data (as uws user)
├── state.db                  # SQLite WAL + FTS5 session store
├── sessions/                 # JSONL transcripts
├── logs/
└── memories/
```

### Pattern 1: Hardened systemd Unit (Claude's discretion — research recommendation)

```ini
# Source: uab-brain.service on VPS (existing Brain pattern) + lumadock.com/tutorials/run-hermes-agent-with-systemd
[Unit]
Description=ultra-workshop Hermes Agent gateway
After=network-online.target uab-brain.service
Wants=network-online.target
Requires=uab-brain.service

[Service]
Type=simple
User=uws
Group=uws
WorkingDirectory=/opt/ultra-workshop

# Credentials — all secrets in one file, never in git
EnvironmentFile=/etc/uws/env

# Hermes environment
Environment=HERMES_INSTALL_DIR=/opt/ultra-workshop/hermes
Environment=HOME=/home/uws
Environment=PATH=/home/uws/.local/bin:/opt/ultra-workshop/hermes/hermes-agent/.venv/bin:/home/uws/.nvm/versions/node/v24/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

ExecStart=/opt/ultra-workshop/hermes/hermes-agent/.venv/bin/hermes gateway start

Restart=on-failure
RestartSec=10
StartLimitIntervalSec=120
StartLimitBurst=5

# Resource limits — sized for Hermes + future Aider subprocess
MemoryMax=4G
CPUQuota=200%

# Hardening (matching Brain's posture)
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/uws/.hermes /var/log/ultra-workshop /tmp

StandardOutput=journal
StandardError=journal
SyslogIdentifier=uws-hermes

[Install]
WantedBy=multi-user.target
```

**Key decisions:**
- `MemoryMax=4G` — Brain uses ~5.1GB of 7.8GB total; Hermes baseline ~200MB + 2GB headroom for future Aider subprocess (Phase 3). 4G is a hard kill limit, not reservation.
- `RestartSec=10` — 10s backoff; Brain uses 5s but Hermes has longer cold-start (~19s per v0.14.0 release notes).
- `ProtectHome=true` + `ReadWritePaths=/home/uws/.hermes` — matches Brain's posture.
- **Known bug:** `hermes gateway install --system` has a `User=` / `WorkingDirectory` path-mismatch bug when installed as root. Do NOT use `sudo hermes gateway install --system` — write the unit file manually. `[CITED: github.com/NousResearch/hermes-agent/issues/6989]`

### Pattern 2: Hermes config.yaml (no secrets)

```yaml
# Source: hermes-agent.nousresearch.com/docs/user-guide/configuration
# File: /opt/ultra-workshop/hermes-config/config.yaml
# Symlink or set HERMES_CONFIG_PATH to point here

model: "openai/private-worker"
# base_url/api_key for LiteLLM proxy come from .env via ${} substitution

agent:
  max_turns: 50

approvals:
  mode: smart   # HITL for dangerous commands

clarify:
  timeout: 300  # 5 min for Telegram HITL approval

mcp_servers:
  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_PAT}"

  context7:
    command: "npx"
    args: ["-y", "@upstash/context7-mcp"]

  crawl4ai:
    # Direct SSE — no npm package needed; Docker container already on VPS
    url: "http://localhost:11235/mcp/sse"
    connect_timeout: 60
    timeout: 180

  hostinger-api:
    command: "npx"
    args: ["-y", "hostinger-api-mcp"]
    env:
      API_TOKEN: "${HOSTINGER_API_TOKEN}"

  google-workspace:
    command: "uvx"
    args: ["workspace-mcp", "--tool-tier", "core"]
    env:
      GOOGLE_SERVICE_ACCOUNT_KEY_FILE: "/etc/uws/gcp-service-account.json"
      USER_GOOGLE_EMAIL: "${GOOGLE_USER_EMAIL}"

platforms:
  telegram:
    extra:
      allow_from:
        - "7113965359"
```

### Pattern 3: /etc/uws/env credential file

```bash
# /etc/uws/env — root:uws 0640 — NEVER commit to git
# Source: Research recommendation (Claude's discretion)

# LiteLLM
LITELLM_BASE_URL=http://127.0.0.1:4000/v1
LITELLM_API_KEY=sk-workshop-internal

# Telegram
TELEGRAM_BOT_TOKEN=<new-rotated-token>

# GitHub (fine-grained PAT, scoped to test-workshop-sandbox)
GITHUB_PAT=<github-fine-grained-pat>

# Hostinger
HOSTINGER_API_TOKEN=<hostinger-api-token>

# Google Workspace (service account path preferred — no expiry)
GOOGLE_USER_EMAIL=caiobellizzi@gmail.com
# GCP service account key at /etc/uws/gcp-service-account.json (separate file, root:uws 0640)
```

### Anti-Patterns to Avoid

- **Using `delegate_task` for durable HITL state:** `delegate_task` is NOT restart-safe. Mid-flow HITL must be implemented via Hermes's `terminal(background=True, notify_on_complete=True)` + FTS5 session search, or the HITL callback must be re-dispatched on gateway reconnect.
- **`sudo hermes gateway install --system`:** Triggers the User=/WorkingDirectory path-mismatch bug. Write the unit file manually.
- **Storing secrets in config.yaml:** Hermes supports `${VAR}` substitution. Secrets belong in `/etc/uws/env`, not config.yaml.
- **Installing Hermes as root:** Hermes reads/writes `~/.hermes/` relative to `HOME`. Running as root puts everything under `/root/` which conflicts with `User=uws`.
- **Missing `loginctl enable-linger uws`:** Required for user-level services to survive SSH logout. Not relevant for system service (`--system`), but worth verifying.

---

## CRITICAL FINDING: REQ-ws-014 and HITL Durability

**This is the most important research finding for the planner.**

REQ-ws-014 requires: "HITL pause survives `systemctl restart uws-hermes` via Hermes FTS5."

**What Hermes FTS5 actually persists:** `[CITED: hermes-agent.nousresearch.com/docs/user-guide/sessions]`
- SQLite WAL database at `~/.hermes/state.db`
- Tables: `sessions`, `messages`, `messages_fts` (FTS5), `messages_fts_trigram`
- All past conversation turns, including tool calls and results
- Session metadata (model, user, timestamps)

**What does NOT survive restart:** `[CITED: github.com/NousResearch/hermes-agent issues + deepwiki]`
- Live asyncio coroutines — `delegate_task` is "not durable for long-running work"
- In-flight `clarify` callback registrations (the callback handler is in process memory)
- Pending Telegram inline button handlers

**Implication for REQ-ws-014:** The acceptance criterion "tapping Approve after restart completes flow without re-triage" requires one of:

**Option A (Recommended): Re-dispatch on gateway reconnect via FTS5 polling**
- Before issuing `clarify`, write a `pending_hitl` row to a durable store (Hermes FTS5 or a separate SQLite table in `~/.ultra-workshop/`)
- On Hermes startup, a `SessionStart` skill queries for `pending_hitl` rows and re-registers the Telegram inline button handler
- Implementation: custom Python skill or Hermes `cron` entry that runs on startup

**Option B: `terminal(background=True)` pattern**
- Spawn the approval-waiting logic as a background terminal subprocess that writes its result to a file
- Hermes gateway reconnects to the subprocess via the notify callback
- More complex, requires the subprocess to survive independently of the Hermes process

**Option C: Accept soft restart only (weakest)**
- Document that `systemctl restart` in the test scenario is a controlled restart (< 30s); Telegram's message queue holds the [Approve] button tap for re-delivery
- Hermes re-registers clarify handlers on reconnect if the session is still in `state.db`
- Only works if the restart completes before the Telegram button expires (usually 48h for inline keyboards)

**Planner recommendation:** Implement Option A — a startup skill that scans FTS5 for interrupted HITL sessions and re-emits the Telegram inline keyboard. This is the only approach that strictly satisfies "resumes cleanly."

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Hermes install + venv | Custom pip install | Official `install.sh` script | Handles uv, Node, symlinking, PATH setup |
| Telegram bot long-polling | Custom asyncio bot | Hermes gateway | Reconnection, fallback IPs, button UI all built in |
| MCP process management | Subprocess management | Hermes config.yaml `mcp_servers` | Auto-reconnect, exponential backoff, tool discovery |
| Google OAuth on headless | Custom OAuth server | Service account key file | GCP service account supports server-to-server with no browser |
| FTS5 session DB schema | Custom SQLite schema | Hermes `state.db` | Already created by Hermes with WAL + FTS5 tables |

---

## Common Pitfalls

### Pitfall 1: `delegate_task` Not Durable (BLOCKS REQ-ws-014)
**What goes wrong:** Team assumes FTS5 = HITL state survives restart. FTS5 stores conversation history, not live coroutine state. After `systemctl restart`, all pending `clarify` callbacks are lost.
**Why it happens:** Hermes docs describe FTS5 as "persistent session search" — this is for recall, not for resuming in-flight workflows.
**How to avoid:** Implement a durable pending-approval store outside of in-process coroutines (see CRITICAL FINDING above).
**Warning signs:** V14 smoke test passes on first run but fails after `systemctl restart uws-hermes` mid-flow.

### Pitfall 2: Root/User Path Mismatch in systemd Unit
**What goes wrong:** `hermes gateway install --system` generates a unit file with `User=ubuntu` but `WorkingDirectory=/root/.hermes/hermes-agent` → `status=200/CHDIR`.
**Why it happens:** Known upstream bug (issue #6989): `PROJECT_ROOT` and `python_path` aren't remapped when a non-root user is detected via `SUDO_USER`.
**How to avoid:** Write the unit file manually. Set `HERMES_INSTALL_DIR=/opt/ultra-workshop/hermes` before running the installer to ensure all paths are under `/opt/ultra-workshop/`.
**Warning signs:** `systemctl status uws-hermes` shows `status=200/CHDIR`.

### Pitfall 3: Node.js Not Installed on VPS
**What goes wrong:** 4 of 5 MCP servers require npx. VPS has Node.js not installed (verified at research time).
**How to avoid:** Install Node.js 24 via nvm as the first step. Add `~/.nvm/versions/node/v24/bin` to the `PATH` environment variable in the systemd unit.
**Warning signs:** `hermes mcp list` shows 0 tools for github/context7/hostinger-api MCP servers.

### Pitfall 4: uab-telegram.service Not Masked (REQ-ws-013)
**What goes wrong:** `systemctl disable` doesn't prevent manual or dependency-driven restart. The service must be masked.
**How to avoid:** `systemctl stop uab-telegram && systemctl disable uab-telegram && systemctl mask uab-telegram`. Verify with `systemctl status uab-telegram` → `masked`.
**Warning signs:** Both bots respond to the same Telegram token until the token is rotated.

### Pitfall 5: No Swap on VPS (OOM Risk)
**What goes wrong:** VPS has 0B swap (verified). Total RAM = 7.8GB; Brain uses ~5.1GB; Hermes baseline ~200MB; Aider subprocess in Phase 3 needs ~2GB. Under load: OOM kill.
**How to avoid:** Add 2GB swap before deploying: `fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile`. Add to `/etc/fstab` for persistence.
**Warning signs:** `systemctl status uws-hermes` shows `status=137` (OOM killed by kernel).

### Pitfall 6: google-workspace OAuth Requires Upfront GCP Setup
**What goes wrong:** Service account mode requires a GCP project, OAuth 2.0 credentials, enabling Google APIs (Gmail, Calendar, Drive), and downloading a service account key JSON. This is a multi-step manual process that can't be scripted.
**How to avoid:** Plan a manual "GCP setup" task that must be completed before the google-workspace MCP registration task. The key JSON goes to `/etc/uws/gcp-service-account.json` (root:uws 0640).
**Warning signs:** `workspace-mcp` subprocess fails with `GOOGLE_APPLICATION_CREDENTIALS` errors.

### Pitfall 7: LiteLLM private-worker Timeout Still at 300s
**What goes wrong:** L26 requires updating `private-worker` timeout to 30s. Current VPS config shows `timeout: 300` (verified). This must be done before Hermes is wired up or Hermes will use the stale config.
**How to avoid:** Update `deploy/litellm/config.yaml` locally and rsync to VPS as part of this phase's Wave 0.
**Warning signs:** Hermes Telegram responses timeout after 300s instead of failing fast.

### Pitfall 8: FTS5 Module Availability
**What goes wrong:** Hermes's SQLite session store refuses to open if FTS5 is not compiled in, with `Error: Could not open session database: no such module: fts5`.
**Status:** VERIFIED SAFE — Python 3.12.3 on VPS has FTS5 available (tested at research time).

---

## Code Examples

### Verified: Hermes config.yaml mcp_servers schema
```yaml
# Source: hermes-agent.nousresearch.com/docs/user-guide/features/mcp
mcp_servers:
  # stdio server
  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "${GITHUB_PAT}"
    timeout: 120
    connect_timeout: 60

  # HTTP/SSE server (no subprocess)
  crawl4ai:
    url: "http://localhost:11235/mcp/sse"
    connect_timeout: 60
    timeout: 180

  # Tool filtering
  github:
    tools:
      include: [create_issue, list_issues, get_file_contents]
```

### Verified: Telegram allowed_users config
```yaml
# Source: hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram
platforms:
  telegram:
    extra:
      allow_from:
        - "7113965359"   # numeric user ID, not username
```

Or via environment variable in `/etc/uws/env`:
```bash
TELEGRAM_ALLOWED_USERS=7113965359
```

### Verified: systemd pre-deploy gate commands
```bash
# Stop, disable, and mask Brain's Telegram service
systemctl stop uab-telegram
systemctl disable uab-telegram
systemctl mask uab-telegram
# Verify
systemctl status uab-telegram  # must show: loaded (masked)
```

### Verified: Add swap (VPS has 0B swap)
```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### Verified: LiteLLM private-worker timeout update
```yaml
# File: deploy/litellm/config.yaml
# Change private-worker timeout from 300 to 30
- model_name: private-worker
  litellm_params:
    timeout: 30   # was 300 — L26
```

### Verified: Create uws system user
```bash
useradd --system --home-dir /home/uws --create-home --shell /bin/bash uws
# Hermes data dir
mkdir -p /home/uws/.hermes
chown -R uws:uws /home/uws
```

### Verified: /etc/uws/env permissions
```bash
mkdir -p /etc/uws
touch /etc/uws/env
chown root:uws /etc/uws/env
chmod 0640 /etc/uws/env
```

### Restart-resilience smoke test (V14 — recommended scripted scenario)
```bash
#!/usr/bin/env bash
# Smoke test for REQ-ws-014

# 1. Trigger a HITL-paused flow (send /build test-hitl-smoke via Telegram)
#    Hermes should issue inline keyboard [Approve] [Reject]
echo "Step 1: Dispatch synthetic HITL flow — wait for Telegram prompt"
sleep 15

# 2. Confirm FTS5 has a session row with 'hitl' or 'clarify' state
HITL_COUNT=$(sudo -u uws sqlite3 /home/uws/.hermes/state.db \
  "SELECT count(*) FROM messages_fts WHERE messages_fts MATCH 'clarify OR approve';")
echo "FTS5 HITL rows: $HITL_COUNT"
[ "$HITL_COUNT" -gt 0 ] || { echo "FAIL: no HITL state in FTS5"; exit 1; }

# 3. Restart the service
systemctl restart uws-hermes
sleep 20  # allow cold-start (~19s per release notes)

# 4. Verify service is back up
systemctl is-active uws-hermes || { echo "FAIL: service not active after restart"; exit 1; }

# 5. Tap [Approve] in Telegram
echo "Step 5: Tap [Approve] in Telegram now — flow should complete"
# Expected: flow resumes without re-triage
# Failure: 'This message is no longer available' or bot ignores the button
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `hermes gateway install --system` (scripted) | Manual unit file (avoid bug #6989) | v0.14.x era | Write unit file explicitly |
| SSE transport for MCP (deprecated) | Streamable HTTP or stdio | Context7 note | For crawl4ai, native SSE `url:` still works in Hermes config |
| PyPI `hermes-agent 0.13.0` | Git installer for v0.14.0 | PyPI lags ~1 version | Must use installer, not `pip install hermes-agent` |

---

## Runtime State Inventory

> Step 2.5 required — this phase modifies live VPS state.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `~/.hermes/state.db` does not exist yet (uws user not created) | None — created on first Hermes run |
| Live service config | `uab-telegram.service` ACTIVE (running, PID 2947016) — must be killed | stop + disable + mask BEFORE Hermes deploy |
| OS-registered state | `uws` user does not exist | `useradd --system uws` in Wave 0 |
| Secrets/env vars | Telegram bot token in `/opt/ultra-agents-brain/.env` (old token) — still live | Rotate via BotFather `/revoke` → new token in `/etc/uws/env` |
| Build artifacts | LiteLLM `private-worker` timeout = 300s in `deploy/litellm/config.yaml` | Update to 30s + rsync (L26) |

**Pre-deploy gates (BLOCKING):**
1. VPS RAM: 2.6GB available — MARGINAL (Brain uses 5.1/7.8GB). Add 2GB swap before deploy.
2. `uab-telegram.service`: active (running) — must be stopped/disabled/masked.
3. Telegram token: needs rotation via BotFather `/revoke`.
4. Phase 1 vault sync: must be verified live (per ROADMAP phase dependency).
5. Node.js 24: not installed — must install via nvm in Wave 0.
6. `uv`: not installed — Hermes installer will install it, but verify first.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Hermes Agent | ✓ | 3.12.3 | — |
| SQLite FTS5 | Hermes session store | ✓ | verified at research | — |
| Node.js 24 | 4 npm MCP servers | ✗ | not installed | Install via nvm in Wave 0 |
| npm | MCP server install | ✗ | not installed | Comes with Node.js |
| uv | Hermes installer + workspace-mcp | ✗ | not installed | Hermes installer installs it |
| Crawl4AI Docker | crawl4ai MCP | ✓ (assumed) | container at :11235 | — |
| LiteLLM proxy | Hermes LLM calls | ✓ | running at :4000 | — |
| uab-brain.service | `After=` dependency | ✓ | active (running) | — |

**Missing, blocking:** Node.js 24, npm, uv — all must be installed in Wave 0.

---

## Validation Architecture

> nyquist_validation not explicitly false in config — included.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | bash smoke tests (no pytest for deploy phase) |
| Config file | `scripts/smoke-test-phase2.sh` (Wave 0 gap) |
| Quick run command | `bash scripts/smoke-test-phase2.sh --quick` |
| Full suite command | `bash scripts/smoke-test-phase2.sh` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-ws-001 | `systemctl status uws-hermes` → active | smoke | `systemctl is-active uws-hermes` | ❌ Wave 0 |
| REQ-ws-002 | `/start` reply from chat 7113965359 within 5s | manual + smoke | Telegram bot ping script | ❌ Wave 0 |
| REQ-ws-013 | `systemctl status uab-telegram` → inactive/masked | smoke | `systemctl is-active uab-telegram && exit 1 \|\| exit 0` | ❌ Wave 0 |
| REQ-ws-014 | HITL survives restart | manual smoke | V14 scripted scenario above | ❌ Wave 0 |
| REQ-ws-015 | `hermes mcp list` shows 5 servers | smoke | `hermes mcp list \| grep -c 'tools'` | ❌ Wave 0 |

### Wave 0 Gaps
- [ ] `scripts/smoke-test-phase2.sh` — covers REQ-ws-001, 002, 013, 015
- [ ] `scripts/v14-hitl-smoke.sh` — covers REQ-ws-014

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Telegram `allow_from` user ID allowlist |
| V3 Session Management | yes | Hermes FTS5 SQLite WAL; no cross-session token leakage |
| V4 Access Control | yes | systemd `User=uws` + `NoNewPrivileges=true`; `PrivateTmp=true` |
| V5 Input Validation | partial | Hermes does Telegram sender validation; command injection via tool use mitigated by `approvals: smart` |
| V6 Cryptography | no | No custom crypto; secrets at rest in `/etc/uws/env` (0640, not encrypted) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unauthorized Telegram control | Spoofing | `allow_from: ["7113965359"]` allowlist |
| Secret exfiltration via Hermes skill | Information disclosure | Hermes v0.7.0+ secret redaction; `ProtectSystem=strict` limits FS write |
| MCP server process escalation | Elevation of privilege | `NoNewPrivileges=true`; `PrivateTmp=true` |
| Bot token reuse after rotation | Spoofing | Old token must be revoked via BotFather `/revoke` before any deploy |
| Google service account over-permission | Information disclosure | Restrict service account scopes to minimum required APIs |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Crawl4AI Docker container is running at `localhost:11235` on VPS | Standard Stack / MCP Config | crawl4ai MCP registration fails; switch to `crawl4ai-mcp-sse-stdio` npm package |
| A2 | `hermes mcp list` is the correct CLI command to verify MCP registration | Standard Stack | REQ-ws-015 acceptance test uses wrong command |
| A3 | `workspace-mcp` (PyPI) is the correct package for taylorwilsdon/google_workspace_mcp | Standard Stack | Wrong package installs; confirmed via `pip3 index versions workspace-mcp` showing 1.21.0 |
| A4 | Telegram chat ID `7113965359` is a user ID (not group ID) | Telegram Config | Wrong `allow_from` key needed (group vs user) |
| A5 | The FTS5 session store can be queried directly with sqlite3 for V14 smoke test | V14 smoke | Smoke test script uses wrong approach |

---

## Open Questions

1. **Does Hermes support `HERMES_CONFIG_PATH` env var to point config.yaml to `/opt/ultra-workshop/hermes-config/config.yaml`?**
   - What we know: Hermes reads `~/.hermes/config.yaml` by default
   - What's unclear: Whether config path is overrideable via env var or CLI flag
   - Recommendation: If not, symlink `~/.hermes/config.yaml → /opt/ultra-workshop/hermes-config/config.yaml`; run `hermes config` as uws to verify

2. **How does `workspace-mcp` (uvx) find service account credentials when launched by Hermes as a subprocess?**
   - What we know: `GOOGLE_SERVICE_ACCOUNT_KEY_FILE` env var is supported
   - What's unclear: Whether uvx subprocess inherits the env from Hermes's EnvironmentFile
   - Recommendation: Pass explicitly via `env:` in config.yaml `mcp_servers.google-workspace`

3. **Does Hermes v0.14.0 ship a `hermes mcp list` command?**
   - What we know: `hermes mcp` is documented since v0.4.0
   - What's unclear: Exact output format for V16 acceptance test (`hermes mcp list` shows all 5)
   - Recommendation: Verify on VPS after install; REQ-ws-015 acceptance may need to use gateway logs instead

---

## Sources

### Primary (HIGH confidence)
- [Hermes Agent docs — configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration) — config.yaml schema, env var precedence
- [Hermes Agent docs — Telegram](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram) — `allow_from`, `TELEGRAM_ALLOWED_USERS`
- [Hermes Agent docs — MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp) — mcp_servers schema, tool filtering
- [Hermes Agent docs — sessions](https://hermes-agent.nousresearch.com/docs/user-guide/sessions) — FTS5 persistence model
- [Hermes v0.14.0 release notes](https://github.com/NousResearch/hermes-agent/blob/main/RELEASE_v0.14.0.md) — what changed in this version
- [Hostinger API MCP Server](https://www.hostinger.com/support/11079316-hostinger-api-mcp-server/) — official install guide
- [taylorwilsdon/google_workspace_mcp](https://github.com/taylorwilsdon/google_workspace_mcp) — service account headless mode
- VPS live state (`ssh root@31.97.130.253`) — Node.js missing, FTS5 OK, swap=0B, uab-telegram active

### Secondary (MEDIUM confidence)
- [Hermes systemd bug #6989](https://github.com/NousResearch/hermes-agent/issues/6989) — User=/WorkingDirectory mismatch
- [lumadock.com — run-hermes-agent-with-systemd](https://lumadock.com/tutorials/run-hermes-agent-with-systemd) — hardening directives
- [deepwiki — hermes memory/sessions](https://deepwiki.com/NousResearch/hermes-agent/4.3-memory-and-sessions) — FTS5 schema, delegate_task durability

### Tertiary (LOW confidence)
- Community search results on crawl4ai-mcp-sse-stdio download volumes — not verified against npmjs stats

---

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM — Hermes docs verified via official site; versions confirmed via npm/PyPI registry
- Architecture: MEDIUM — systemd pattern derived from existing Brain unit + official Hermes guidance
- HITL durability (REQ-ws-014): HIGH confidence that `delegate_task` is NOT durable — multiple sources corroborate; planner must address
- Pitfalls: HIGH — all confirmed via VPS live state probe or official GitHub issues

**Research date:** 2026-05-20
**Valid until:** 2026-06-20 (Hermes releases frequently — re-verify if upgrading from 0.14.0)
