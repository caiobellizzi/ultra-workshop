<!-- generated-by: gsd-doc-writer -->
# ultra-workshop

An autonomous coding and PR pipeline that listens on Telegram, orchestrates a multi-role specialist agent pipeline, and requires human approval before any code is pushed.

## Architecture

Workshop is a two-layer system:

```
Telegram Bot
     │
     ▼
Hermes Agent (v0.14.0)
     │  hermes-skill-run.sh subprocess transport
     ▼
workshop/ pipeline engine
  ├── brainstorm → triage → requirements → planner
  ├── coder (Aider)
  ├── parallel review wave
  └── HITL pause → git push / PR creation
     │
     ▼
LiteLLM proxy (127.0.0.1:4000)
  └── 6 model aliases: orchestrator, default-worker, cheap-worker,
      private-worker, cloud-sonnet, cloud-groq
```

**Key components:**

| Directory | Purpose |
|-----------|---------|
| `workshop/` | Core pipeline engine — orchestrator, planner, reviewer, types, cost ledger |
| `dashboard/` | FastAPI backend + React/TypeScript control plane (port 7010) |
| `hermes-skills/` | Hermes Agent skill scripts — build, fix, coder, reviewer, cron routines |
| `skills/` | 33 SKILL.md files consumed by Hermes Agent |
| `deploy/` | systemd units, LiteLLM docker-compose, deploy runbook |
| `scripts/` | `install.sh` — idempotent VPS deployer via rsync + SSH |

**Hard constraints:**
- Hermes Agent v0.14.0 pinned
- All LLM calls routed through LiteLLM proxy — never directly to providers
- Coder role uses Aider exclusively (not Claude Code)
- HITL gate required before any `git push` or PR creation
- Shared $20/day budget with Brain; circuit breaker at $18

## Prerequisites

- Python 3.11
- [`uv`](https://github.com/astral-sh/uv) for virtual environment management
- Node.js >= 18 + pnpm (dashboard frontend only)
- A running LiteLLM proxy at `127.0.0.1:4000`
- Hermes Agent v0.14.0 installed

## Quick Start

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd ultra-workshop

# 2. Create the Python virtualenv and install dependencies
uv venv
source .venv/bin/activate
uv pip install -r dashboard/backend/requirements.txt

# 3. Set required environment variables (see Environment Variables below)
export UWS_DASH_COOKIE_SECRET=<secret>
export UWS_DASH_LOGIN_PASSWORD=<password>
export LITELLM_API_KEY=<key>
export TELEGRAM_BOT_TOKEN=<token>
export GITHUB_PAT=<pat>

# 4. Start the dashboard backend
uvicorn dashboard.backend.main:app --port 7010

# 5. (Optional) Build and serve the frontend
cd dashboard/frontend
pnpm install
pnpm build
# Vite output is served as a SPA by the FastAPI backend
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `UWS_DASH_COOKIE_SECRET` | Required | Cookie-signing secret for session auth |
| `UWS_DASH_LOGIN_PASSWORD` | Required | Password for the dashboard login form |
| `LITELLM_API_KEY` | Required | API key for the LiteLLM proxy at `127.0.0.1:4000` |
| `TELEGRAM_BOT_TOKEN` | Required | Telegram bot token for the `/build` and `/fix` commands |
| `GITHUB_PAT` | Required | GitHub personal access token for PR creation |

## Running the Dashboard

**Development (backend only):**

```bash
source .venv/bin/activate
uvicorn dashboard.backend.main:app --port 7010 --reload
```

**Development (with frontend hot-reload):**

```bash
# Terminal 1 — backend
uvicorn dashboard.backend.main:app --port 7010 --reload

# Terminal 2 — frontend dev server
cd dashboard/frontend
pnpm dev
```

**API routes served by the backend:**

| Route prefix | Purpose |
|-------------|---------|
| `/api/tasks` | Pipeline task list and status |
| `/api/auth` | Login / session check (`/api/auth/me`) |
| `/api/cost` | Budget and cost ledger |
| `/api/config` | Hermes / stage-policy configuration |
| `/api/skills` | Skill manifest |
| `/api/hitl` | Human-in-the-loop approval queue |
| `/api/control` | Pipeline start/stop controls |
| `/api/repos` | Repository registry |
| `/api/health` | Health check |

## Running Tests

```bash
# Python unit and integration tests
source .venv/bin/activate
pytest

# Shell integration tests (requires bats)
bats tests/
```

Test files live under `hermes-skills/`, `scripts/`, and `tests/` (configured in `pyproject.toml`).

## Pipeline Commands (Telegram)

Once the Hermes Agent is running with the workshop skills loaded:

| Command | Description |
|---------|-------------|
| `/build <task description>` | Start a full build pipeline: brainstorm → plan → code → review → HITL |
| `/fix <issue description>` | Start a focused fix pipeline for a specific bug |

The pipeline pauses at the HITL gate and waits for human approval before pushing any code.

## Cron Routines

Hermes runs three scheduled routines:

| Script | Schedule | Purpose |
|--------|----------|---------|
| `cron_daily_research.py` | 07:00 daily | Research and brain ingest |
| `cron_nightly_tests.py` | 02:00 daily | Nightly test run across registered repos |
| `cron_bug_scan_fastpoll.py` | Every 4 hours | Fast-poll bug scan |

## Deployment (VPS)

The project deploys to a Hostinger VPS at `/opt/ultra-workshop/`.

```bash
# Deploy to VPS (idempotent — safe to re-run)
bash scripts/install.sh
```

`install.sh` rsyncs the project to `root@31.97.130.253`, installs Python dependencies, and restarts the systemd units. See `deploy/DASHBOARD-DEPLOY.md` for the full runbook.

**systemd units** are in `deploy/systemd/`. LiteLLM runs via Docker Compose (`deploy/litellm/`).

## License

Private — all rights reserved.
