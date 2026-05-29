<!-- generated-by: gsd-doc-writer -->
# Deployment

This document covers deploying ultra-workshop to a Hostinger VPS. All services run under a dedicated `uws` system user and are managed by systemd.

---

## Deployment Targets

| Component | Mechanism | Config File |
|---|---|---|
| Hermes gateway | systemd service | `deploy/systemd/uws-hermes.service` |
| Dashboard backend | systemd service | `deploy/systemd/uws-hermes-dashboard.service` |
| Bug-scan fast-poll | systemd service | `deploy/systemd/uws-bug-scan-fastpoll.service` |
| LiteLLM proxy | Docker Compose | `deploy/litellm/docker-compose.workshop.yml` |

**VPS target:** <!-- VERIFY: current VPS IP address --> `root@31.97.130.253`
**Install directory:** `/opt/ultra-workshop/`
**Service user:** `uws` (system user, home `/home/uws`)
**Python environment:** uv-managed `.venv` at `/opt/ultra-workshop/.venv`

---

## Pre-Deploy Checklist

Complete these steps before running `install.sh`:

- [ ] Rotate the Telegram bot token via BotFather `/revoke` (L7 LOCKED constraint)
- [ ] Verify `uab-telegram.service` is **inactive** on the VPS (L4 LOCKED constraint)
- [ ] Verify `uab-brain.service` is **running** — `uws-hermes.service` has a hard `Requires=` dependency on it
- [ ] Confirm all required environment variables are set in `/etc/uws/env` (see [Environment Setup](#environment-setup) below)

---

## Build Pipeline

There is no CI/CD deploy pipeline. Deployment is triggered manually by running `scripts/install.sh` from your local machine over SSH.

The CI workflow (`.github/workflows/summary.yml`) runs a nightly brain summary on a schedule — it does not deploy any service.

---

## Running a Deploy

`scripts/install.sh` is an idempotent rsync-based installer. It is safe to re-run.

```bash
# Full deploy
bash scripts/install.sh

# Preview commands without executing
bash scripts/install.sh --dry-run
```

### What install.sh does (in order)

1. SSH reachability check against the VPS
2. Create `uws` system user if absent
3. Create directories: `/opt/ultra-workshop/{hermes,hermes-config,deploy/systemd}`, `/var/log/ultra-workshop`
4. Install Hermes Agent via curl installer (skipped if already installed)
5. Rsync `hermes-config/` to `/opt/ultra-workshop/hermes-config/`
6. Symlink `/home/uws/.hermes/config.yaml` → `/opt/ultra-workshop/hermes-config/config.yaml`
7. Copy systemd unit file → `/etc/systemd/system/uws-hermes.service`
8. `systemctl daemon-reload && systemctl enable uws-hermes` (register unit)
9. `systemctl start uws-hermes` (start the service)
10. Create trust symlink: `/opt/ultra-workshop/workshop/trust_shared.py` → `/opt/ultra-agents-brain/ultra_brain/trust.py`
11. Set `HERMES_CRON_TIMEOUT` in `/etc/uws/env`
12. Deploy `uws-bug-scan-fastpoll` systemd unit
13. Deploy cron catchup startup hook
14. Register Hermes cron jobs via `bootstrap_cron_jobs.py`
15. Deploy `integration-contract.md` to vault

---

## Systemd Services

All services are enabled at system boot and run as `User=uws`. Logs go to the systemd journal (`journalctl -u <service-name> -f`).

### uws-hermes.service — Hermes Agent gateway

| Setting | Value |
|---|---|
| ExecStart | `/opt/ultra-workshop/hermes/venv/bin/python -m hermes_cli.main gateway run --replace` |
| MemoryMax | 4G |
| CPUQuota | 200% |
| EnvironmentFile | `/etc/uws/env` |
| Depends on | `uab-brain.service` (hard `Requires=`) |

```bash
# Check status
ssh root@31.97.130.253 "systemctl status uws-hermes"

# Tail logs
ssh root@31.97.130.253 "journalctl -u uws-hermes -f"
```

### uws-hermes-dashboard.service — FastAPI dashboard

Binds to `127.0.0.1:7010` only. Not exposed publicly.

```bash
ExecStart: /opt/ultra-workshop/hermes/venv/bin/uvicorn dashboard.backend.main:app --host 127.0.0.1 --port 7010 --workers 1
MemoryMax: 1G
CPUQuota: 100%
```

### uws-bug-scan-fastpoll.service — Bug scan poller

30-second polling loop that reads `.workshop-queue.jsonl`. Starts after `uws-hermes.service`.

```bash
ExecStart: /opt/ultra-workshop/.venv/bin/python /opt/ultra-workshop/hermes-skills/cron_bug_scan_fastpoll.py
```

---

## LiteLLM Proxy (Docker)

LiteLLM runs as a Docker container using host networking so it can reach the dashboard's internal spend-update endpoint.

**Config:** `deploy/litellm/docker-compose.workshop.yml`
**Image:** `ghcr.io/berriai/litellm:main-stable`
**Container name:** `uws-litellm`
**Port:** `127.0.0.1:4001` (host) → `:4000` (container internal)
**Spend logs callback:** `http://127.0.0.1:7010/internal/spend-update`

```bash
# Start LiteLLM
docker compose -f deploy/litellm/docker-compose.workshop.yml up -d

# Restart after config changes
sudo docker restart uws-litellm

# Tail logs
docker logs -f uws-litellm
```

Provider keys (`NVIDIA_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `LITELLM_MASTER_KEY`, etc.) are read from `/etc/uws/env` via `env_file`. The container config is mounted read-only from `deploy/litellm/workshop-config.yaml`.

> After starting LiteLLM for the first time, update `hermes-config/config.yaml` to point `base_url` to `:4001`.

---

## Environment Setup

All runtime secrets live in `/etc/uws/env` on the VPS. This file is never committed to the repository.

| Variable | Required | Description |
|---|---|---|
| `LITELLM_API_KEY` | Required | Master key for the LiteLLM proxy (also `LITELLM_MASTER_KEY` inside the container) |
| `TELEGRAM_BOT_TOKEN` | Required | Telegram bot token — rotate via BotFather before deploy |
| `GITHUB_PAT` | Required | GitHub personal access token for vault and repo access |
| `UWS_DASH_COOKIE_SECRET` | Required | Cookie-signing secret for the dashboard |
| `UWS_DASH_LOGIN_PASSWORD` | Required | Dashboard login password (separate from cookie secret) |
| `VAULT_VPS_PATH` | Required | Path to vault on VPS (default: `/srv/second-brain`) |
| `VAULT_DEFAULT_BRANCH` | Optional | Git branch for the vault remote |
| `VAULT_REMOTE` | Optional | Git remote URL for the vault |
| `HERMES_CRON_TIMEOUT` | Optional | Cron job timeout in seconds (default: `1800`) — set by `install.sh` |

For additional provider keys consumed by LiteLLM (e.g., `NVIDIA_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `LM_STUDIO_API_BASE`, `LM_STUDIO_API_KEY`), see `deploy/litellm/docker-compose.workshop.yml`.

See [CONFIGURATION.md](CONFIGURATION.md) for the full environment variable reference.

---

## Accessing the Dashboard

The dashboard is not exposed publicly. Access it via SSH port forwarding:

```bash
ssh -L 7010:127.0.0.1:7010 root@31.97.130.253
```

Then open `http://localhost:7010` in your browser.

---

## Rollback Procedure

There is no automated rollback. To revert:

1. Identify the previous working commit: `git log --oneline`
2. Check out that commit locally and re-run `bash scripts/install.sh` — the installer is idempotent and will overwrite deployed files with the checked-out version
3. For the LiteLLM container: revert `deploy/litellm/workshop-config.yaml` and run `docker compose -f deploy/litellm/docker-compose.workshop.yml up -d`
4. Restart affected services: `ssh root@31.97.130.253 "systemctl restart uws-hermes uws-hermes-dashboard"`

---

## Monitoring

Logs are written to the systemd journal on the VPS. No external monitoring service is configured.

```bash
# All ultra-workshop service logs
ssh root@31.97.130.253 "journalctl -u 'uws-*' -f"

# Specific service
ssh root@31.97.130.253 "journalctl -u uws-hermes -n 100"
ssh root@31.97.130.253 "journalctl -u uws-hermes-dashboard -n 100"
ssh root@31.97.130.253 "journalctl -u uws-bug-scan-fastpoll -n 100"

# LiteLLM container
ssh root@31.97.130.253 "docker logs -f uws-litellm"
```

<!-- VERIFY: whether a monitoring dashboard or alerting service (Sentry, Datadog, etc.) is configured on the VPS -->
