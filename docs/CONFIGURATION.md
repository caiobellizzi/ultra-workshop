<!-- generated-by: gsd-doc-writer -->
# Configuration

ultra-workshop is configured through four complementary layers: Dashboard backend environment variables (prefix `UWS_DASH_`), Hermes agent config YAML, LiteLLM proxy config YAML, and system-level environment variables on the VPS host. This document covers all configuration surfaces.

---

## Table of Contents

1. [Dashboard Backend](#1-dashboard-backend)
2. [Hermes Agent Config](#2-hermes-agent-config)
3. [Stage Policies](#3-stage-policies)
4. [LiteLLM Proxy](#4-litellm-proxy)
5. [System-Level Environment Variables](#5-system-level-environment-variables)
6. [Dev vs Production Path Resolution](#6-dev-vs-production-path-resolution)

---

## 1. Dashboard Backend

**Source:** `dashboard/backend/config.py`  
**Loaded by:** Pydantic Settings — reads env vars with prefix `UWS_DASH_`, then `.env` file if present.

### Service Binding

| Variable | Default | Description |
|---|---|---|
| `UWS_DASH_HOST` | `127.0.0.1` | Bind address for the dashboard HTTP server |
| `UWS_DASH_PORT` | `7010` | Bind port for the dashboard HTTP server |

### Authentication

| Variable | Required | Default | Description |
|---|---|---|---|
| `UWS_DASH_COOKIE_SECRET` | Required in prod | `dev-secret-change-me` | HMAC key used to sign session cookies. A WARNING is emitted at startup if the default value is detected. Change this before any public-facing deployment. |
| `UWS_DASH_LOGIN_PASSWORD` | Optional | _(falls back to `cookie_secret`)_ | The password presented on the login screen. Kept separate from `COOKIE_SECRET` so it can be memorable without weakening cookie signing security. |
| `UWS_DASH_API_TOKEN` | Optional | _(empty — disabled)_ | Bearer token for simple API auth. When set, requests must include `Authorization: Bearer <token>`. |
| `UWS_DASH_SESSION_COOKIE_NAME` | Optional | `uws_dash_session` | Name of the HTTP session cookie. |
| `UWS_DASH_SECURE_COOKIE` | Optional | `true` | Sends the session cookie over HTTPS only. Set to `false` only for local HTTP development. |

### File System Paths

All paths below default to production VPS locations. On a local dev machine they are automatically patched by `Settings.resolve_paths()` — see [Dev vs Production Path Resolution](#6-dev-vs-production-path-resolution).

| Variable | Default (production) | Description |
|---|---|---|
| `UWS_DASH_TASKS_BASE` | `/home/uws/.ultra-workshop/tasks` | Root directory where task workspaces are stored |
| `UWS_DASH_HITL_DB` | `/home/uws/.ultra-workshop/pending_hitl.db` | SQLite database for pending human-in-the-loop approvals |
| `UWS_DASH_SPEND_DB` | `/home/uws/.ultra-workshop/dashboard/spend.sqlite` | Dashboard-owned SQLite database for LiteLLM spend tracking |
| `UWS_DASH_WORKSHOP_ROOT` | `/opt/ultra-workshop` | Root of the workshop installation |
| `UWS_DASH_HERMES_CONFIG_DIR` | `/opt/ultra-workshop/hermes-config` | Directory containing `config.yaml` and `stage-policies.yaml` |
| `UWS_DASH_COST_LEDGER_MD` | `/srv/second-brain/_system/cost-ledger.md` | Markdown cost ledger in the Obsidian vault (fallback for spend tracking) |
| `UWS_DASH_SKILLS_ROOT` | `/opt/ultra-workshop/skills` | Root of the canonical skills tree |
| `UWS_DASH_REPO_REGISTRY_PATH` | `/srv/second-brain/_system/workshop-repos.json` | JSON registry of repositories managed by the workshop |

### Workshop Binary Paths

| Variable | Default (production) | Description |
|---|---|---|
| `UWS_DASH_WORKSHOP_BUILD_PY` | `/opt/ultra-workshop/hermes-skills/workshop_build.py` | Path to the `workshop_build.py` skill invoked by the dashboard |
| `UWS_DASH_WORKSHOP_CONTINUE_PY` | `/opt/ultra-workshop/hermes-skills/workshop_continue.py` | Path to the `workshop_continue.py` skill invoked by the dashboard |

---

## 2. Hermes Agent Config

**Source:** `hermes-config/config.yaml`  
**Loaded by:** Hermes gateway at startup.

```yaml
model:
  default: "private-worker"   # Default LiteLLM alias used for tasks
  provider: "custom"
  base_url: "http://127.0.0.1:4000/v1"   # LiteLLM proxy endpoint
  api_key: "${LITELLM_API_KEY}"           # Resolves from env at runtime

agent:
  max_turns: 50               # Maximum agentic turns per task

approvals:
  mode: smart                 # HITL approval mode

clarify:
  timeout: 300                # Seconds to wait for user clarification (seconds)

platforms:
  telegram:
    token: "${TELEGRAM_BOT_TOKEN}"        # Resolves from env at runtime
    allow_from:
      - "7113965359"          # Allowlist of Telegram user IDs
```

### Key Settings

| Setting | Value | Description |
|---|---|---|
| `model.default` | `private-worker` | LiteLLM alias used when no stage-specific alias overrides it |
| `model.base_url` | `http://127.0.0.1:4000/v1` | LiteLLM proxy URL — change to `:4001` when using the dedicated workshop proxy |
| `agent.max_turns` | `50` | Hard cap on agentic turns per task to prevent runaway loops |
| `approvals.mode` | `smart` | Hermes decides when to pause for human approval |
| `clarify.timeout` | `300` | Seconds Hermes waits for a clarification reply before timing out |

---

## 3. Stage Policies

**Source:** `hermes-config/stage-policies.yaml`  
**Loaded by:** `workshop/_config_loader.py` at runtime (cached for ~10 s).

The config loader resolves the YAML path in this order:
1. `$UWS_CONFIG_DIR/stage-policies.yaml` — explicit env override
2. `/opt/ultra-workshop/hermes-config/stage-policies.yaml` — production default
3. `<repo_root>/hermes-config/stage-policies.yaml` — dev/test fallback

### Stage Timeout and Retry Policy

| Stage | `timeout` (s) | `tool_timeout` (s) | `auto_retries` | `hitl_on_timeout` |
|---|---|---|---|---|
| `brainstorm` | 300 | — | 0 | `true` |
| `triage` | 180 | — | 1 | — |
| `requirements` | 180 | — | 1 | — |
| `planner` | 900 | — | 1 | — |
| `coder` | 7200 | 7200 | 0 | `false` |
| `reviewer` | 300 | — | 1 | — |

The coder stage timeout can be overridden at runtime without editing the YAML:

| Variable | Default | Description |
|---|---|---|
| `UWS_CODER_MAX` | `7200` | Overrides `coder` stage `timeout` and `tool_timeout` (seconds) |

### Model Alias Mapping

Stage specialists are mapped to LiteLLM model aliases defined in [LiteLLM Proxy](#4-litellm-proxy):

| Specialist role | LiteLLM alias |
|---|---|
| `triage-specialist` | `cheap-fast` |
| `requirements-specialist` | `cheap-fast` |
| `planner-specialist` | `planner-reasoner` |
| `coder-specialist` | `coder-worker` |
| `reviewer-specialist` | `reviewer-model` |
| `correctness-reviewer` | `reviewer-model` |
| `security-reviewer` | `reviewer-model` |
| `python-reviewer` | `reviewer-model` |
| `typescript-reviewer` | `reviewer-model` |
| `reactjs-reviewer` | `reviewer-model` |
| `qa-reviewer` | `reviewer-model` |
| `docs-reviewer` | `reviewer-model` |
| `config-reviewer` | `reviewer-model` |
| `merge-agent` | `reviewer-model` |
| `brainstorm-specialist` | `default-worker` |
| `brainstorm` | `default-worker` |

---

## 4. LiteLLM Proxy

Two config files are provided:

| File | Container | Port | Purpose |
|---|---|---|---|
| `deploy/litellm/config.yaml` | General / standalone | — | Standalone LiteLLM instance for ad-hoc use |
| `deploy/litellm/workshop-config.yaml` | `uws-litellm` | `127.0.0.1:4001` | Dedicated workshop proxy; posts spend events to the dashboard |

The workshop proxy is launched via:

```bash
docker compose -f deploy/litellm/docker-compose.workshop.yml up -d
```

Provider keys are read from `/etc/uws/env` on the VPS host (mounted as `env_file` in the compose file).

### Model Aliases

| Alias | Model | Provider | Notes |
|---|---|---|---|
| `orchestrator` | `google/gemma-4-e4b` (LM Studio) | LM Studio | Heavy model; falls back to `cloud-sonnet` |
| `default-worker` | `google/gemma-4-e4b` (LM Studio) | LM Studio | Falls back to `cloud-sonnet`, `cloud-groq` |
| `cheap-worker` | `google/gemma-4-e4b` (LM Studio) | LM Studio | Falls back to `default-worker`, `cloud-groq` |
| `private-worker` | `google/gemma-4-e4b` (LM Studio) | LM Studio | Falls back to `cheap-worker` |
| `planner-reasoner` | `mistralai/mistral-large-3-675b-instruct-2512` | NVIDIA NIM | Falls back to `cloud-sonnet` |
| `coder-worker` | `deepseek-ai/deepseek-v4-flash` | NVIDIA NIM | Falls back to `cloud-sonnet` |
| `reviewer-model` | `nvidia/llama-3.3-nemotron-super-49b-v1` | NVIDIA NIM | Falls back to `cloud-sonnet` |
| `cheap-fast` | `meta/llama-3.1-8b-instruct` | NVIDIA NIM | Falls back to `cheap-worker`, `cloud-groq` |
| `cloud-sonnet` | `claude-sonnet-4-6` | Anthropic | Cloud fallback |
| `cloud-groq` | `llama-3.3-70b-versatile` | Groq | Cloud fallback |

### LiteLLM Environment Variables

| Variable | Required | Description |
|---|---|---|
| `LITELLM_MASTER_KEY` | Required | Master key for the LiteLLM proxy (`general_settings.master_key`). Also referenced as `LITELLM_API_KEY` by Hermes. |
| `LM_STUDIO_API_BASE` | Required (local tiers) | Base URL for LM Studio (e.g. `http://localhost:1234/v1` locally, or LM Link endpoint on VPS) |
| `LM_STUDIO_API_KEY` | Required (local tiers) | API key for LM Studio (any non-empty string for local) |
| `NVIDIA_API_KEY` | Required (NIM tiers) | API key for NVIDIA NIM — used by `planner-reasoner`, `coder-worker`, `reviewer-model`, `cheap-fast` |
| `ANTHROPIC_API_KEY` | Required (cloud fallback) | Anthropic API key — used by `cloud-sonnet` fallback |
| `GROQ_API_KEY` | Required (cloud fallback) | Groq API key — used by `cloud-groq` fallback |
| `SPEND_LOGS_URL` | Optional | URL where LiteLLM posts per-request spend batches. Set automatically to `http://127.0.0.1:7010/internal/spend-update` by `docker-compose.workshop.yml`. |

---

## 5. System-Level Environment Variables

These variables are set in `/etc/uws/env` on the VPS and are not read by Pydantic Settings directly — they are consumed by hermes-skills, cron jobs, and the deploy tooling.

| Variable | Default | Description |
|---|---|---|
| `LITELLM_API_KEY` | — | LiteLLM proxy master key (same value as `LITELLM_MASTER_KEY`); passed to `hermes-config/config.yaml` via `${LITELLM_API_KEY}` |
| `TELEGRAM_BOT_TOKEN` | — | Hermes Telegram gateway bot token; passed to `hermes-config/config.yaml` via `${TELEGRAM_BOT_TOKEN}` |
| `GITHUB_PAT` | — | Fine-grained GitHub PAT for repo registry operations (`workshop_push.py`). Falls back to `GH_TOKEN` if unset. |
| `VAULT_VPS_PATH` | `/srv/second-brain` | Root path of the Obsidian vault on the VPS (used by cron skills and install scripts) |
| `HERMES_CRON_TIMEOUT` | `1800` | Timeout in seconds for cron-triggered hermes skills (written to `/etc/uws/env` by `scripts/install.sh`) |
| `UWS_CONFIG_DIR` | — | Optional override for the directory containing `stage-policies.yaml` (see [Stage Policies](#3-stage-policies)) |

> **VAULT_DEFAULT_BRANCH** and **VAULT_REMOTE** are documented in the project context but were not found in any source file at doc-generation time. <!-- VERIFY: VAULT_DEFAULT_BRANCH and VAULT_REMOTE env vars — confirm whether they are used and in which script -->

---

## 6. Dev vs Production Path Resolution

`Settings.resolve_paths()` in `dashboard/backend/config.py` automatically patches VPS-only paths when the production directory does not exist on the local machine. No manual configuration is needed for local development.

| Setting | Production path | Local dev fallback |
|---|---|---|
| `tasks_base` | `/home/uws/.ultra-workshop/tasks` | `<repo_root>/tests/phase-11/tmp-tasks` |
| `hermes_config_dir` | `/opt/ultra-workshop/hermes-config` | `<repo_root>/hermes-config` |
| `workshop_root` | `/opt/ultra-workshop` | `<repo_root>` (`.`) |
| `skills_root` | `/opt/ultra-workshop/skills` | `<repo_root>/skills` |

Paths that are **not** in the mapping (`hitl_db`, `spend_db`, `cost_ledger_md`, `repo_registry_path`, binary paths) retain their production defaults locally. Create stub files or point these variables to local equivalents via `.env` if a feature under development requires them.

### Minimal `.env` for Local Development

```bash
# dashboard/backend — local dev overrides
UWS_DASH_SECURE_COOKIE=false
UWS_DASH_COOKIE_SECRET=local-dev-only-not-secret
UWS_DASH_LOGIN_PASSWORD=devpass

# LiteLLM (only if running the proxy locally)
LM_STUDIO_API_BASE=http://localhost:1234/v1
LM_STUDIO_API_KEY=lm-studio
LITELLM_MASTER_KEY=sk-dev-master
```
