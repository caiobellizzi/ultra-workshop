# Dashboard Implementation Spec (authoritative contract)

Shared source of truth for all implementation agents. Read alongside `plans/wild-meandering-rabin.md`
(decisions) and `plans/wild-meandering-rabin-agent-a27d49c0a0e12c0c8.md` (frontend design detail).

## Repo conventions
- Python: the `workshop/` package (importable). Tests live under `tests/phase-*/`, run with `pytest`.
  Dashboard backend = NEW top-level package `dashboard/backend/` (importable as `dashboard.backend.*`).
- Frontend = NEW `dashboard/frontend/` (Vite + React + TS). Build output → `dashboard/frontend/dist/`.
- Deploy artifacts → `deploy/` (systemd, sudoers, litellm).
- Atomic file writes: replicate `workshop/state.py` pattern (`.tmp` sibling + `os.replace`).
- NEVER write secrets. Bind services to `127.0.0.1` only.

## SCOPE OF THIS WORKFLOW = LOCAL CODE ONLY
Implement code + deploy artifacts + a runbook. DO NOT run VPS ops (no ssh, no rm -rf, no docker,
no systemctl, no rsync). Those are captured in `deploy/DASHBOARD-DEPLOY.md` for human execution.

---

## PART A — Foundation refactor (Phase 0 code)

### A1. `hermes-config/stage-policies.yaml` (NEW) — seed from current dicts
```yaml
stage_policies:
  brainstorm:   {timeout: 300, auto_retries: 0, hitl_on_timeout: true}
  triage:       {timeout: 180, auto_retries: 1}
  requirements: {timeout: 180, auto_retries: 1}
  planner:      {timeout: 900, auto_retries: 1}
  coder:        {timeout: 7200, tool_timeout: 7200, auto_retries: 0, hitl_on_timeout: false}
  reviewer:     {timeout: 300, auto_retries: 1}
model_aliases:
  triage-specialist: cheap-fast
  requirements-specialist: cheap-fast
  planner-specialist: planner-reasoner
  coder-specialist: coder-worker
  reviewer-specialist: reviewer-model
  correctness-reviewer: reviewer-model
  security-reviewer: reviewer-model
  python-reviewer: reviewer-model
  typescript-reviewer: reviewer-model
  reactjs-reviewer: reviewer-model
  qa-reviewer: reviewer-model
  docs-reviewer: reviewer-model
  config-reviewer: reviewer-model
  merge-agent: reviewer-model
  brainstorm-specialist: default-worker
  brainstorm: default-worker
```

### A2. `workshop/_config_loader.py` (NEW)
- `load_stage_policies() -> dict[str, StagePolicy]`: read `hermes-config/stage-policies.yaml`; on missing/malformed,
  fall back to the original `STAGE_POLICIES` dict (keep the dict literal in this module as `_FALLBACK_STAGE_POLICIES`).
  Reconstruct `StagePolicy` dataclass instances. Apply `UWS_CODER_MAX` env override to coder timeout/tool_timeout
  at load time. Cache result with a ~10s TTL (module-level timestamp; no `time.time()` ban issue — this is runtime code).
- `load_model_aliases() -> dict[str, str]`: same pattern with `_FALLBACK_MODEL_ALIASES`.
- Path resolution: locate `hermes-config/stage-policies.yaml` relative to repo root (env `UWS_CONFIG_DIR`
  override, default `/opt/ultra-workshop/hermes-config`, dev fallback to repo `hermes-config/`).

### A3. `workshop/stage_policy.py` (MODIFY)
- Keep `StagePolicy` dataclass. Move the `STAGE_POLICIES` + `MODEL_ALIASES` dict LITERALS into
  `_config_loader.py` as fallbacks (or import them there). Re-implement the 4 accessors to delegate to the loader:
  `stage_model_alias(skill)` → `load_model_aliases().get(skill, "default-worker")`;
  `stage_policy(stage)` → `load_stage_policies()[stage]` (raise KeyError w/ known stages on miss);
  `stage_timeout`/`stage_tool_timeout` unchanged signatures.
- CRITICAL: accessor signatures + return types MUST be identical (≈15 call sites in
  workshop_build.py / workshop_coder.py / workshop_continue.py must need ZERO changes). `stage_policy()` MUST
  still return a `StagePolicy` dataclass (workshop_continue.py:174 reads `.timeout`/`.tool_timeout`).

### A4. Aider log-tee (MODIFY, additive — Phase 1 dependency)
- `hermes-skills/aider_runner.py` `_run_aider_runner(...)`: add kwarg `log_file: Path | None = None`.
  In the `if data:` decode block, also `log_file.write(decoded); log_file.flush()` when set. No other behavior change.
- `hermes-skills/workshop_coder.py`: before each step's `_run_aider_runner` call, open
  `task_dir(task_id) / f"aider_step_{step_idx}.log"` (append) and pass as `log_file`. Use `workshop.ledger.task_dir`.
- Must NOT disturb the final `Diff` JSON emitted to stdout.

### A5. Verification for Foundation
`python -c "from workshop.stage_policy import stage_model_alias, stage_policy; print(stage_model_alias('coder-specialist')); print(stage_policy('coder').timeout)"` → `coder-worker` / `7200`.
Run `pytest tests/phase-04/test_planner.py tests/phase-04/test_orchestrator.py tests/phase-06 -q` → still green.

---

## PART B — Backend (`dashboard/backend/`)

### Layout
`main.py` (FastAPI factory + lifespan warms config cache + StaticFiles mount of `../frontend/dist` at `/`),
`config.py` (Pydantic Settings, env prefix `UWS_DASH_`), `deps.py` (auth dep + in-flight guard),
`security.py` (session cookie, `secrets.compare_digest`), `routers/{tasks,cost,config_api,skills,hitl,control,repos,sse,internal}.py`,
`services/{task_store,cost_service,hitl_service,config_service,build_trigger,log_tailer}.py`, `models/api_models.py`.

### Settings (paths; all overridable via env)
tasks_base=`/home/uws/.ultra-workshop/tasks`, hitl_db=`/home/uws/.ultra-workshop/pending_hitl.db`,
spend_db=`<dashboard data>/spend.sqlite` (NEW, dashboard-owned), workshop_root=`/opt/ultra-workshop`,
hermes_config_dir=`/opt/ultra-workshop/hermes-config`, cost_ledger_md=`/srv/second-brain/_system/cost-ledger.md`,
api_token (optional), port 7010, host 127.0.0.1. Dev fallbacks to repo-relative paths so it boots locally.

### Reuse (import from workshop/)
`workshop.state.load_task_state`, `workshop.ledger.{validate_task_id,task_dir,LEDGER_BASE,append_progress}`,
`workshop.cost.{get_daily_spend,get_role_monthly_spend,ROLE_MONTHLY_CAPS}`, `workshop.types.*` (Plan/Diff/Review/
WaveReport/MergeReport/ClarificationRequest as response models), `workshop.repo_registry.*`,
`hermes-skills/startup-hitl-scan.py`:`fetch_pending` (via importlib).

### Endpoints (method path → behavior)
- GET `/api/tasks` → list task dirs w/ status,goal,stage,created/updated (task_store.list_tasks)
- GET `/api/tasks/{id}` → full state + embedded Plan/Diff/Review from state["stages"]
- GET `/api/tasks/{id}/progress` → progress_log.jsonl entries
- POST `/api/tasks` {repo,goal,brainstorm?} → build_trigger.launch_build (background thread) → {task_id}
- POST `/api/tasks/{id}/fix` → resume
- GET `/api/cost/{daily,roles,models}`, GET `/api/cost/task/{id}` → cost_service (spend.sqlite, fallback ledger md)
- GET/PUT `/api/config/stage-policies` `/api/config/models` `/api/config/roster` `/api/config/cron` → config_service (validated atomic writes + cache invalidate)
- GET `/api/skills`, GET `/api/skills/{name}`, PUT `/api/skills/{name}` {content}, GET `/api/skills/{name}/history`, POST `/api/skills/{name}/rollback`, POST `/api/skills/{name}/dry-run` (SSE)
- GET `/api/hitl` → fetch_pending; POST `/api/hitl/{row_id}/resolve` {task_id,hitl_type,choice} → hitl_service (asyncio.to_thread → workshop_continue.py, return 202)
- GET `/api/repos`, POST `/api/repos`, DELETE `/api/repos/{name}`
- GET `/api/health` → service/process checks + model reachability (ping each LiteLLM alias) + queue depth + disk
- POST `/api/control/restart` (guarded: in-flight check → 409 unless force), POST `/api/control/reload-litellm`
- POST `/internal/spend-update` → receive LiteLLM SPEND_LOGS_URL batches → write spend.sqlite (NO auth; loopback only)
- GET `/api/sse/tasks/{id}/events` (poll state.json + progress_log every 2s), GET `/api/sse/tasks/{id}/logs` (tail aider_step_*.log) — use `sse-starlette`

### Validation gates (MUST)
validate_task_id on every task endpoint; roster write requires security+correctness present; model-alias write
cross-checked vs LiteLLM model_list names (read deploy/litellm/config.yaml); stage-policy write requires all 6 stages;
SKILL.md write: name regex `^[a-z0-9_-]+$`, size < 128000, backup `.bak`, flag if Output Schema block changed;
restart blocked when build in-flight (state.json LIVE_STATUSES scan + `pgrep -u uws -f workshop_build.py`).

### Tests
`tests/phase-11/` (or `dashboard/backend/tests/`): task_store against tmp dir; config_service atomic write + rejection;
hitl_service against seeded sqlite. Keep CI-green (pytest.skip if VPS-only).

---

## PART C — Frontend (`dashboard/frontend/`)
Vite + React + TS + shadcn/ui + TanStack Query/Router + recharts + @monaco-editor/react + @tanstack/react-virtual.
Read `plans/wild-meandering-rabin-agent-a27d49c0a0e12c0c8.md` for the full page/component design.
THIS workflow builds: app shell + auth gate + `/board` (kanban) + `/tasks/:id` (PipelineGraph + LogStream SSE +
stage panes incl DiffViewer + ReviewWaveTable) + `/cost` + `/health`. Scaffold remaining routes
(`/config/*`, `/skills`, `/hitl`, `/repos`, `/launch`) as typed stubs that call the API and render a basic table/form
(full polish in a later phase). `src/lib/api.ts` typed client; `src/lib/useSSE.ts` ring-buffer (cap 2000) + backoff.
`vite.config` manualChunks monaco. Must `tsc --noEmit` clean and `vite build` succeed.

---

## PART D — Deploy artifacts (files only) + runbook
- `deploy/systemd/uws-hermes-dashboard.service` — User=uws, WorkingDirectory=/opt/ultra-workshop,
  ExecStart uvicorn `dashboard.backend.main:app --host 127.0.0.1 --port 7010 --workers 1`, EnvironmentFile=/etc/uws/env,
  ProtectSystem=strict, ReadWritePaths=/home/uws/.ultra-workshop /home/uws/.hermes /tmp /opt/ultra-workshop,
  Restart=always, SyslogIdentifier=uws-dashboard. Mirror `deploy/systemd/uws-hermes.service`.
- `deploy/sudoers.d/uws-dashboard` — EXACTLY 4 NOPASSWD lines, no globs:
  `/usr/bin/systemctl restart uws-hermes.service`, `/usr/bin/systemctl reload uws-hermes.service`,
  `/usr/bin/systemctl restart uws-hermes-dashboard.service`, `/usr/bin/docker restart uws-litellm`.
- `deploy/litellm/workshop-config.yaml` — copy of current aliases for the DEDICATED Workshop proxy; add
  `general_settings` with `SPEND_LOGS_URL` note; intended to run as container `uws-litellm` on `:4001`.
- `deploy/litellm/docker-compose.workshop.yml` — dedicated proxy container (port 127.0.0.1:4001, env
  `SPEND_LOGS_URL=http://127.0.0.1:7010/internal/spend-update`, reuse provider keys from env file).
- `deploy/DASHBOARD-DEPLOY.md` — runbook (HUMAN-EXECUTED, with pre-checks):
  1. Drift fix: pre-check `ls -la /home/uws/.hermes/skills` + `diff -r` vs `/opt/ultra-workshop/skills`; then
     `rm -rf /home/uws/.hermes/skills && ln -sf /opt/ultra-workshop/skills /home/uws/.hermes/skills && chown -h uws:uws`.
  2. Bring up `uws-litellm` :4001; repoint `hermes-config/config.yaml` base_url → :4001 + aider `--openai-api-base`/`--user`.
  3. Install systemd unit + sudoers; `systemctl daemon-reload; enable --now uws-hermes-dashboard`.
  4. Build frontend, rsync `dist/`. Tailscale reachability + cookie-auth check. Verification checklist.
