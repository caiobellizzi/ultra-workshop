# Forensic Verification: Two Assumptions + Deploy/Ops Design

---

## ASSUMPTION 1 — "Fix skill drift by making ~/.hermes/skills a symlink to ONE canonical skills tree"

### Hypothesis
The plan proposes one symlink: `~/.hermes/skills` → a single canonical tree. The concern is that three specialist homes exist and each might need its own skills directory independently.

### Evidence FOR (single symlink is correct)
- **All three specialist homes already share one symlink target** (confirmed from VPS work in 04-UAT.md:112–113):
  > "Provisioned the orchestrator home with SOUL.md + skills symlink + config.yaml pointing to alias `orchestrator`."
  > "provisioned specialist-home-private/ and specialist-home-research/ on VPS. All three homes now have config.yaml + skills symlink → /home/uws/.hermes/skills."
- The only thing that differs between homes is `config.yaml` (which sets `model.default`). The `skills/` content is identical across all three and already points to the same target.
- `hermes-skill-run.sh:105–111` injects `HERMES_HOME` per skill but does not set a skill-specific override; the skills resolution falls through to `${HERMES_HOME}/skills/` which all three homes resolve to the same place.
- `install.sh` does NOT sync `skills/` from `/opt/ultra-workshop/skills/` to `/home/uws/.hermes/skills/` at deploy time (confirmed: no `rsync` of `skills/` in steps 1–N+5 of install.sh). The gap is real.

### Evidence AGAINST (single symlink is too simple)
- **Specialist homes live at `/opt/ultra-workshop/specialist-home-{orchestrator,private,research}/`**, not under `~/.hermes/`. If the symlink is inside `/home/uws/.hermes/skills/`, it is NOT inside any specialist-home directory. Hermes must resolve skills from `HERMES_HOME/skills/` i.e. from the specialist-home directories. The question is whether those homes' `skills/` entries also symlink to `~/.hermes/skills/` (VPS-only fact — cannot confirm from local repo, but the UAT note says they do).
- `requirements-specialist`, `reviewer-specialist`, `coder-specialist` are Python short-circuits (`hermes-skill-run.sh:82–97`) and do not invoke `hermes chat --skills` at all — so skill resolution for those three is irrelevant. Only `triage-specialist`, `planner-specialist`, `brainstorm-specialist` and the wildcard `*` path actually use Hermes skill loading.

### VERDICT: PARTIALLY CONFIRMED, BUT THE PLAN'S FRAMING IS IMPRECISE

The plan says "symlink `~/.hermes/skills` → single canonical skills tree." This is almost right but the real drift problem has a different shape:

**What actually exists on VPS (confirmed from 04-UAT.md):**
```
/opt/ultra-workshop/specialist-home-orchestrator/skills  →  /home/uws/.hermes/skills
/opt/ultra-workshop/specialist-home-private/skills       →  /home/uws/.hermes/skills
/opt/ultra-workshop/specialist-home-research/skills      →  /home/uws/.hermes/skills
```
i.e. all three specialist-home `skills/` dirs are already symlinks pointing to `~/.hermes/skills`. The canonical single location IS `~/.hermes/skills`. The symlinks are already there.

**The actual drift hazard** (confirmed from plan wild-meandering-rabin.md:57–59):
The repo has `/opt/ultra-workshop/skills/<n>/SKILL.md` and at runtime Hermes reads `/home/uws/.hermes/skills/<n>/SKILL.md`. `install.sh` never rsyncs the repo `skills/` tree to `~/.hermes/skills/`. So edits in the repo do not propagate to the live location without a manual `rsync` or `scp`.

**Corrected drift-elimination strategy:**

The ONE canonical source should be the repo's `skills/` dir. The fix is to make `/home/uws/.hermes/skills` a symlink to `/opt/ultra-workshop/skills` (the rsync'd repo copy), not to keep them as two separate trees that must be manually kept in sync.

Exact paths:
```bash
# On VPS (one-time migration, idempotent after):
rm -rf /home/uws/.hermes/skills                         # remove current dir/symlink
ln -sf /opt/ultra-workshop/skills /home/uws/.hermes/skills
# Verify: all three specialist-home skills symlinks already point here,
# so no changes needed in the specialist homes.
chown -h uws:uws /home/uws/.hermes/skills
```

Then `install.sh` step 5 (CONFIG DEPLOY) already rsyncs to `/opt/ultra-workshop/`, so after any deploy the skills are live immediately. The dashboard edits `/opt/ultra-workshop/skills/<n>/SKILL.md` directly — one path, no dual-write.

**VPS-only facts that MUST be verified on the server before executing:**
1. Confirm symlink chain: `ls -la /opt/ultra-workshop/specialist-home-orchestrator/skills` — should show `→ /home/uws/.hermes/skills`. If any home has a real directory (not a symlink), the above migration alone is insufficient for that home.
2. Confirm `/home/uws/.hermes/skills` is currently a real directory (not already pointing to `/opt/ultra-workshop/skills`).
3. Check for any skills in `/home/uws/.hermes/skills/` that are NOT in `/opt/ultra-workshop/skills/` — those would be lost by the symlink swap (e.g. translated skills from `translated/` subdir).

---

## ASSUMPTION 2 — "Enable LiteLLM spend logging + per-request metadata tagging + hot-reload model aliases without restart"

### Hypothesis
The plan claims (a) LiteLLM spend logs can be enabled with just DATABASE_URL, (b) per-request `task_id`/agent metadata can be tagged and queried, (c) model aliases can be hot-reloaded without restart.

### Evidence FOR
- `deploy/litellm/config.yaml:144`: `disable_spend_logs: false` — the flag is already set to allow spend logging.
- `litellm/proxy/_types.py:3464`: `SpendLogsMetadata` TypedDict exists and includes `spend_logs_metadata: Optional[dict]` for arbitrary k,v pairs (confirmed in installed version at `ultra-agents-brain/.venv`).
- `litellm/proxy/litellm_pre_call_utils.py:669–677`: spend logs metadata can be injected via HTTP header `x-litellm-spend-logs-metadata` — callers do not need to modify LiteLLM itself.
- `litellm/proxy/proxy_cli.py:173–191`: `--reload` flag with `_get_reload_options` exists for uvicorn hot-reload.

### Evidence AGAINST

**(a) Spend logs require Prisma/DB — not just DATABASE_URL optionally:**

`litellm/proxy/utils.py:5070`: The spend log flush path calls `prisma_client.db.litellm_spendlogs.create_many(...)` directly. There is no code path that writes spend logs to disk, to a file, or to an alternate store when `prisma_client is None`. The monitoring task itself (`_monitor_spend_logs_queue`, line 7233) only starts `if general_settings.get("disable_spend_logs", False) is False` AND `prisma_client` is active.

`litellm/proxy/proxy_server.py:825–827`: Prisma is initialized from `DATABASE_URL` env var. Without `DATABASE_URL`, `prisma_client = None` and the entire spend log pipeline is a no-op.

**Current state:** `deploy/litellm/config.yaml:145` has `store_model_in_db: false` and there is no `DATABASE_URL` in `ultra-agents-brain/deploy/docker-compose.yml`. The container is running without a DB. `disable_spend_logs: false` is meaningless without a live Prisma connection — the flag does not enable a DB-less logging path.

**(b) Per-request metadata tagging is contingent on (a) working:**

Tags passed via `x-litellm-spend-logs-metadata` header or `metadata.tags` in the request body are written to `LiteLLM_SpendLogs` rows. Without a DB, those tags are never persisted anywhere. The tag feature itself is real and works as designed; it just requires the DB.

**(c) Hot-reload model aliases WITHOUT restart does not exist in this version:**

`litellm/proxy/proxy_server.py:13590–13611`: The `/config/update` endpoint raises `"No DB Connected"` when `prisma_client is None`. It also requires `PROXY_ADMIN` role. Even if it worked, it writes to `LiteLLM_Config` DB rows, not to the YAML file.

`litellm/proxy/management_endpoints/model_management_endpoints.py:253,1193`: The "clear cache and reload models" path in model management endpoints also requires `prisma_client` (calls `prisma_client.db.litellm_proxymodeltable.update`).

The YAML `--reload` flag (proxy_cli.py:679) is uvicorn dev-mode only — it restarts the entire Python process on file change. This is NOT "without restart"; it IS a restart with file-watch automation.

**There is NO `/config/reload` endpoint in the installed version** — only two comments mentioning it as a future possibility (proxy_server.py:918, 2931).

**LiteLLM is Brain's Docker container, not Workshop's:**

`ultra-agents-brain/deploy/docker-compose.yml`: LiteLLM runs as service `litellm` (`deploy-litellm-1`), owned by Brain. Workshop's `deploy/litellm/config.yaml` is a copy that gets rsynced to Brain's config path. The "reload" mechanism for Workshop changes is: rsync config → `docker restart deploy-litellm-1`. The dashboard cannot call `systemctl restart uws-hermes` and also restart Brain's Docker container — those are different users and processes.

### VERDICT: ALL THREE SUB-CLAIMS ARE REFUTED AS STATED

**Corrected minimal mechanism per sub-claim:**

**(a) Spend logging — what it actually takes:**
Minimum viable: add `DATABASE_URL=postgresql://...` to Brain's `.env`, provision a Postgres instance (Brain already has `ops/systemd/uab-postgres.service` — it exists), run LiteLLM's Prisma migration once. `store_model_in_db` can stay `false`. This activates the spend log pipeline without giving LiteLLM write control over model config.

Cost if skipping DB: use `SPEND_LOGS_URL` env var (proxy_server.py:5048–5058) to point LiteLLM at a custom HTTP endpoint that receives `POST /spend/update` with batched log payloads. The dashboard backend could expose this endpoint, store to SQLite, and serve it — zero Postgres required. This is the DB-less alternative.

**(b) Per-request tagging — works once (a) is resolved:**
Workshop callers (Hermes/aider) add header `x-litellm-spend-logs-metadata: {"task_id": "...", "stage": "..."}` to each request. No LiteLLM config change needed. The Hermes config at `hermes-config/config.yaml:4–5` points to `http://127.0.0.1:4000/v1` — header injection needs to happen inside workshop Python code (e.g. in `aider_runner.py` and the hermes-skill-run subprocess environment).

**(c) Hot-reload alias changes — what actually works:**
Without DB: write updated YAML → `docker restart deploy-litellm-1`. Takes ~5s. The dashboard must call this via `sudo -u uabrain docker restart deploy-litellm-1` or similar — requires a cross-user sudoers grant (Brain owns Docker, Workshop is `uws`). The dashboard cannot own this restart unilaterally.

With DB (option above): the Admin UI at port 4000 can add/edit virtual model aliases at runtime. No restart needed. This is the "hot-reload" path the plan envisions — but it requires the DB investment.

**Practical recommendation for v1 dashboard:** Use the `SPEND_LOGS_URL` custom endpoint approach (SQLite + FastAPI `/spend/update` receiver in the dashboard backend). Tag headers injected by Workshop callers. Model alias changes trigger a `docker restart` via a dedicated sudoers rule. No Postgres needed.

---

## DEPLOY / OPS LAYER DESIGN

### 1. FastAPI backend systemd unit (`uws-hermes-dashboard.service`)

```ini
[Unit]
Description=ultra-workshop Dashboard FastAPI backend
After=network-online.target uws-hermes.service
Wants=network-online.target

[Service]
Type=simple
User=uws
Group=uws
WorkingDirectory=/opt/ultra-workshop
EnvironmentFile=/etc/uws/env
Environment=HOME=/home/uws
Environment=PATH=/opt/ultra-workshop/.venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/opt/ultra-workshop/.venv/bin/uvicorn \
    workshop.dashboard.main:app \
    --host 127.0.0.1 \
    --port 7010 \
    --workers 1 \
    --no-access-log
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/uws/.ultra-workshop /home/uws/.hermes /var/log/ultra-workshop /tmp /opt/ultra-workshop
TimeoutStopSec=30
StandardOutput=journal
StandardError=journal
SyslogIdentifier=uws-dashboard

[Install]
WantedBy=multi-user.target
```

**Port choice:** 7010 (Brain is at 7000, avoids clash). Bound to `127.0.0.1` only — no public exposure.

**React build serving:** Mount the Vite build output as `StaticFiles` inside the FastAPI app:
```python
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="/opt/ultra-workshop/dashboard-dist", html=True), name="spa")
```
No separate nginx/caddy needed. The SPA catches all non-API routes. Deploy step: `pnpm build` locally → `rsync dashboard/dist/ root@VPS:/opt/ultra-workshop/dashboard-dist/`. No separate static-file service unit.

### 2. Tailscale access model + single-owner auth

**Network layer:** Dashboard backend bound to `127.0.0.1:7010`. Access via Tailscale only:
- Tailscale MagicDNS: `http://srv1381850:7010` resolves on the tailnet.
- No inbound firewall rule change needed — Tailscale traffic is loopback-equivalent on the VPS.
- VPS already on Tailscale (confirmed from memory: VPS is `31.97.130.253` / `srv1381850.hstgr.cloud`).

**App-level auth (defense-in-depth):** Single static token stored in `/etc/uws/env` as `DASHBOARD_SECRET`. Browser receives it as a session cookie (HttpOnly, SameSite=Strict) on first POST to `/auth`. All API routes check `Authorization: Bearer <token>` or cookie. Token never in HTML/JS bundle. Rotation: update env file + `systemctl restart uws-hermes-dashboard`.

Sketch:
```python
DASHBOARD_SECRET = os.environ["DASHBOARD_SECRET"]

@app.post("/auth")
async def login(token: str, response: Response):
    if not secrets.compare_digest(token, DASHBOARD_SECRET):
        raise HTTPException(401)
    response.set_cookie("session", token, httponly=True, samesite="strict", secure=False)
    return {"ok": True}

async def verify_session(request: Request):
    tok = request.cookies.get("session") or request.headers.get("Authorization", "").removeprefix("Bearer ")
    if not secrets.compare_digest(tok, DASHBOARD_SECRET):
        raise HTTPException(401)
```

No OAuth, no JWT rotation, no user DB. Single-owner home tool — one token is correct scope.

### 3. Minimal sudoers rule for `uws`

**Requirements:** `uws` needs to restart/reload `uws-hermes` (and `uws-hermes-dashboard`) and signal a LiteLLM container restart (owned by root via Docker). The LiteLLM restart requires special handling because the container is Brain's.

```
# /etc/sudoers.d/uws-dashboard
# Allow uws to restart/reload only its own services
uws ALL=(root) NOPASSWD: /usr/bin/systemctl restart uws-hermes.service
uws ALL=(root) NOPASSWD: /usr/bin/systemctl reload uws-hermes.service
uws ALL=(root) NOPASSWD: /usr/bin/systemctl restart uws-hermes-dashboard.service

# LiteLLM is Brain's container; uws can only restart it, not manage it broadly
uws ALL=(root) NOPASSWD: /usr/bin/docker restart deploy-litellm-1
```

**What this intentionally excludes:**
- No `systemctl stop` (avoids accidental shutdown with no restart)
- No `systemctl daemon-reload` (prevents unit file substitution attacks)
- No `docker` subcommands besides `restart` of the exact named container
- No `systemctl restart uws-hermes-*` glob — exact service names only

Validate sudoers with `visudo -c -f /etc/sudoers.d/uws-dashboard` before applying.

### 4. In-flight build guard

**Goal:** prevent `systemctl restart uws-hermes` from killing an active build mid-step.

**Detection mechanism:** check `state.json` before triggering any restart. The state machine's `status` field is the authoritative signal:

```python
import json, pathlib

TASKS_DIR = pathlib.Path("/home/uws/.ultra-workshop/tasks")
LIVE_STATUSES = {"running", "needs_clarification", "needs_timeout_recovery",
                 "needs_step_recovery", "needs_review_recovery", "pushing"}

def any_build_in_flight() -> bool:
    """Return True if any task is in a non-terminal state."""
    for state_file in TASKS_DIR.glob("*/state.json"):
        try:
            data = json.loads(state_file.read_text())
            if data.get("status") in LIVE_STATUSES:
                return True
        except (json.JSONDecodeError, OSError):
            continue
    return False
```

The dashboard's "Apply & restart" endpoint calls `any_build_in_flight()` first:
- If True → return HTTP 409 with a message like `"Build <task_id> is in status 'running' — wait for it to complete or approve the override."` Dashboard shows a warning modal with "Force anyway" option.
- If False → proceed with the restart.

**Secondary guard via pgrep** (belt-and-suspenders, for cases where state.json is stale):
```python
import subprocess
def workshop_build_process_running() -> bool:
    result = subprocess.run(
        ["pgrep", "-u", "uws", "-f", "workshop_build.py"],
        capture_output=True
    )
    return result.returncode == 0
```

Both checks must pass (no in-flight state AND no workshop_build.py process under uws) before restart proceeds without override.

**No aider guard needed separately:** aider runs as a child of `workshop_coder.py` which is a child of the Hermes subprocess. If `uws-hermes` restarts, systemd sends SIGTERM to the process group; the `TimeoutStopSec=210` in `uws-hermes.service` gives aider up to 3.5 minutes to finish its current token before hard kill. The state.json check above prevents the restart from being initiated while a coder step is in progress.

---

## Summary of corrected assumptions

| | Original claim | Verdict | Corrected strategy |
|---|---|---|---|
| A1 drift fix | Single `~/.hermes/skills` symlink | Partially confirmed — direction correct, source wrong | Make `~/.hermes/skills` → `/opt/ultra-workshop/skills` (repo copy). All 3 specialist-home `skills/` dirs already point to `~/.hermes/skills`. VPS confirm required. |
| A2a spend logs | Just need `DATABASE_URL` | Refuted — no DB = no logs at all | Use `SPEND_LOGS_URL` env to point LiteLLM at dashboard's `/spend/update` endpoint; store to SQLite. No Postgres needed for v1. |
| A2b metadata tags | Pass task_id/role metadata | Confirmed (mechanism correct) — contingent on (a) | Inject `x-litellm-spend-logs-metadata` header in Workshop caller code. Works with both DB and SPEND_LOGS_URL paths. |
| A2c hot-reload | Reload aliases without restart | Refuted — no `/config/reload` endpoint exists without DB | Write YAML → `docker restart deploy-litellm-1` (~5s). Cross-user sudo grant required. True hot-reload requires DB (Admin UI path). |

