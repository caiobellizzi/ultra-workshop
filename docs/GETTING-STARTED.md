<!-- generated-by: gsd-doc-writer -->
# Getting Started

This guide walks you through setting up ultra-workshop for the first time — whether for local development or deploying to the production VPS.

## Prerequisites

| Requirement | Version / Notes |
|---|---|
| Python | `3.11` (required by Hermes Agent) |
| uv | Latest — `pip install uv` or `brew install uv` |
| Node.js | `>= 18.0.0` |
| pnpm | Latest — `npm install -g pnpm` |
| Telegram bot token | Obtain from [BotFather](https://t.me/BotFather) |
| GitHub fine-grained PAT | Repo read/write/PR scope |
| LiteLLM proxy | Running locally at `127.0.0.1:4000` |
| SSH access (production only) | `root@31.97.130.253` |

## Local Development Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd ultra-workshop
```

### 2. Install Python dependencies

```bash
uv venv
uv pip install -e .
```

The root `pyproject.toml` declares all Hermes Agent dependencies.

### 3. Install dashboard backend dependencies

```bash
cd dashboard/backend
pip install -r requirements.txt
cd ../..
```

### 4. Install dashboard frontend dependencies

```bash
cd dashboard/frontend
pnpm install
cd ../..
```

### 5. Configure environment

Create a `.env` file at the project root. Minimum required values for local development:

```env
UWS_DASH_COOKIE_SECRET=<any-random-string>
UWS_DASH_LOGIN_PASSWORD=<your-chosen-password>
UWS_DASH_SECURE_COOKIE=false
```

See [CONFIGURATION.md](CONFIGURATION.md) for the full variable reference.

### 6. Start the dashboard backend

```bash
uvicorn dashboard.backend.main:app --reload --port 7010
```

### 7. Start the dashboard frontend

In a separate terminal:

```bash
cd dashboard/frontend
pnpm dev
```

The dev server proxies `/api` requests to `:7010` automatically.

### 8. Open the dashboard

Navigate to [http://localhost:5173](http://localhost:5173) and log in with the password set in `UWS_DASH_LOGIN_PASSWORD`.

## Running Tests

### Python unit tests

```bash
pytest
```

Test paths are configured in `pyproject.toml` (`hermes-skills`, `scripts`, `tests`).

### Shell integration tests (bats)

```bash
bats tests/phase-02/*.bats
```

Replace `phase-02` with the relevant phase directory.

## Production Deployment (VPS)

### 1. Set required environment variables on the VPS

The following must be present in `/etc/uws/env` on the VPS before deploying:

```
VAULT_VPS_PATH=<path>
TELEGRAM_BOT_TOKEN=<token>
LITELLM_API_KEY=<key>
```

### 2. Run the install script

```bash
bash scripts/install.sh
```

The script is idempotent — safe to re-run for updates. It uses SSH/rsync to sync files and starts the following systemd services:

- `uws-hermes.service`
- `uws-bug-scan-fastpoll.service`

> **Note:** `uws-hermes-dashboard.service` is **not** started by `install.sh`. The dashboard must be started manually or via a separate deployment step.

## Verifying the Setup

After completing either local or production setup, run through these checks:

1. **Telegram bot** — send `/start` to the bot; it should respond.
2. **Dashboard login** — open the dashboard URL and log in with `UWS_DASH_LOGIN_PASSWORD`.
3. **Health endpoint** — check `/api/health` in the dashboard for service status.
4. **End-to-end pipeline** — send the following command to the bot to trigger a full build:

   ```
   /build caiobellizzi/test-workshop-sandbox "add hello world"
   ```

## Common Setup Issues

**Wrong Python version** — Hermes Agent requires Python 3.11 exactly. Run `python --version` and switch versions with `pyenv` or your version manager if needed.

**`uv` not found** — Install with `brew install uv` (macOS) or `pip install uv`.

**`pnpm dev` fails to proxy API calls** — Ensure the backend is running on port `7010` before starting the frontend dev server.

**Dashboard login fails** — Confirm `UWS_DASH_LOGIN_PASSWORD` in your `.env` matches what you are entering. On production, verify `/etc/uws/env` is loaded by the service.

**`UWS_DASH_SECURE_COOKIE` cookie warning** — Set `UWS_DASH_SECURE_COOKIE=false` for local HTTP development. Leave unset or set to `true` for HTTPS production deployments.

## Next Steps

- [ARCHITECTURE.md](ARCHITECTURE.md) — system overview and component diagram
- [CONFIGURATION.md](CONFIGURATION.md) — full environment variable reference
- [DEVELOPMENT.md](DEVELOPMENT.md) — build commands, code style, and PR process
