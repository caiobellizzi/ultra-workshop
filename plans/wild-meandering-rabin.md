# Plan: Ultra-Workshop Agent Dashboard (Observability + Control Plane)

> STATUS: GRILLING IN PROGRESS — decision tree being walked one branch at a time.
> This file is built incrementally. Recommendations are provisional until confirmed.

## Context

The user runs **ultra-workshop**, an autonomous coding-agent pipeline (Hermes + Aider + LiteLLM)
deployed on a Hostinger VPS (`srv1381850.hstgr.cloud`, `31.97.130.253`). Today the only human
interface is **Telegram** (HITL approvals) plus **manual SSH** (tailing `agent.log`, polling
`state.json`, editing config + restarting services). Recent pain has been operational: a missing
LiteLLM alias (`planner-reasoner`) silently broke the planner; skills drift between `/opt` and
`~/.hermes`; aider idle-timeouts; Chrome exit-127. The user wants a single web dashboard to:

1. See agents **in action** (live pipeline / agent runs)
2. Monitor **logs** + **observability**
3. **Fully manage** agents + configurations
4. **Switch the LLM model per agent**
5. (open) suggest further relevant features

## Critical findings from codebase exploration (grounding)

### The system already has a partial dashboard story
- **Brain (`ultra-agents-brain`) = Agno `AgentOS` FastAPI** at `127.0.0.1:7000` (user `uabrain`),
  systemd `uab-brain.service`. It exposes a **large HTTP API**: `/agents`, `/agents/{id}/runs`,
  `/sessions`, `/traces`, `/traces/search`, `/metrics`, `/approvals` (+ resolve), `/schedules`
  (CRUD + enable/disable/trigger), `/eval-runs`, `/memories`, `/knowledge/*`, `/workflows/ws` (WS).
- **A hosted dashboard already exists**: `os.agno.com`, CORS already whitelisted in `app.py:85`
  (also `http://localhost:3000`). The whole v2.0 milestone fed it real data.
- **No frontend in any repo** — no `static/`, `templates/`, React/Vite. Brain delegates UI to Agno cloud.

### What Agno's dashboard CANNOT see (the real gap)
Workshop runtime data lives on the **filesystem, user `uws`, no HTTP read endpoint**:
- Task state: `/home/uws/.ultra-workshop/tasks/<id>/state.json` (full pipeline state — see schema below)
- Progress events: `.../progress_log.jsonl` (append-only, ~12 event types)
- HITL queue: `/home/uws/.ultra-workshop/pending_hitl.db` (SQLite) — **separate from Agno `/approvals`**
- Cost ledger: `/srv/second-brain/_system/cost-ledger.md` (markdown, regex-parsed)
- Queue: `/srv/second-brain/_system/.workshop-queue.jsonl` (Brain has write-ACK only, no GET)
- Repo registry: `/srv/second-brain/_system/workshop-repos.json`

### `state.json` is rich (good for a task dashboard)
`status` ∈ {running, needs_clarification, needs_timeout_recovery, needs_review_recovery,
needs_step_recovery, needs_approval, stopped, approval_rejected, pushing, pushed, push_failed}.
`next_stage` ∈ {triage, requirements, brainstorm, planner, coder, reviewer, approval, timeout_recovery}.
Carries per-stage `attempts`, `current_step`, `stages.{triage,requirements,planner,diff,review}`,
and HITL payloads. Persisted atomically (tmp-rename) → safe to read externally.

### Per-agent model switching = two layers
- **Alias → real model**: `deploy/litellm/config.yaml` `model_list` (hot-reloadable). 10 aliases incl.
  `planner-reasoner`, `coder-worker`, `reviewer-model`, `cheap-fast`, `cloud-sonnet`, `cloud-groq`.
- **Agent/stage → alias**: `workshop/stage_policy.py:MODEL_ALIASES` (Python dict — **code edit + restart**).
- All 9 reviewers currently share ONE `reviewer-model` alias. Per-reviewer models need a new LiteLLM
  alias **and** a `MODEL_ALIASES` edit.
- LiteLLM has `store_model_in_db: false` → its built-in Admin UI **cannot** edit models. No `DATABASE_URL`.

### Skill/prompt editing has a DRIFT HAZARD (most dangerous gap)
Skills exist in two places: repo `/opt/ultra-workshop/skills/<n>/SKILL.md` AND runtime
`~/.hermes/skills/<n>/SKILL.md` (the copy Hermes actually loads, reached via a symlink for
orchestrator-home skills only). `install.sh` does **not** sync `~/.hermes/skills`. A dashboard editing
a prompt must write **both** paths or silently serve stale prompts. 33 skills total (6 specialists,
9 reviewer-wave, 4 brain, 4 entry-points, ~10 utilities).

### Config editability ranking (most → least dashboard-friendly)
1. `hermes-config/review-roster.yaml` (roles, model_alias, isolation, file_patterns, budgets) — YAML, restart to apply
2. `deploy/litellm/config.yaml` (model aliases + fallbacks) — YAML, hot-reload
3. `workshop/stage_policy.py` STAGE_POLICIES + MODEL_ALIASES — **Python, restart**
4. `hermes-config/config.yaml` (gateway: default model, max_turns, telegram allow_from) — restart
5. `scripts/hermes-skill-run.sh` (per-skill max-turns + specialist-home routing) — bash, hardcoded case

### Live-activity reality
**No event bus / SSE / webhooks anywhere.** Live view = poll `state.json` + tail `progress_log.jsonl`.
Agno side: agent runs are `stream:false`; but Agno DOES have `/traces` + `/workflows/ws`.
`uws-hermes.service` logs to journal but subprocess stdout is consumed as JSON (stream-lost).

### Cost observability is WEAK (decision point)
`WaveReport.tokens_used`/`cost_cents` always 0; aider cost = event marker only; no per-task total;
cost ledger is markdown. Real cost instrumentation would be net-new work.

### Hosting recommendation (from exploration)
Extend **Brain's FastAPI** with read-only `/dashboard/*` routes (it's the only HTTP server, co-located
with all stores, `uabrain` can read the vault). Frontend = SPA at `localhost:3000` (CORS ready) or
`StaticFiles` mount. `ultra-workshop-v2` is an **empty dir** (one plan file) — target **v1**.

## Decision tree (to be resolved via grilling)
1. [ROOT — RESOLVED] **Standalone Workshop dashboard, decoupled from Brain/Agno.**
   User correction: `ultra-agents-brain` is a SEPARATE project using Agno for ITS OWN agents;
   Workshop runs a totally separate agent workflow (Hermes specialists + aider + cron). The
   `os.agno.com` dashboard belongs to Brain and is out of scope. Workshop has **no HTTP server** and
   runs as user `uws`; Brain runs as `uabrain` and likely cannot read `/home/uws/.ultra-workshop/`.
   ⇒ The dashboard needs its OWN small backend service running as `uws`, reading Workshop's own
   filesystem data + config. Do NOT bolt onto Brain. "Agents" here = Workshop's Hermes specialists
   (triage, requirements, planner, coder, reviewer-wave ×9, brainstorm, merge) + aider + cron jobs.
2. [RESOLVED] **v1 = FULL CONTROL PLANE.** Observe + HITL + model switching (all layers) +
   SKILL.md prompt editing + roster/stage-policy/cron config editing — all in v1. User accepts the
   higher risk. ⇒ Hard requirements this creates: (a) defeat the `/opt` ↔ `~/.hermes` skill drift;
   (b) refactor hardcoded Python config (`MODEL_ALIASES`, `STAGE_POLICIES`) into dashboard-editable
   config OR provide safe code-write+restart; (c) validation gates so an edit can't break the JSON
   contract / leave a dangling alias; (d) restart orchestration (`systemctl restart uws-hermes`).
3. [RESOLVED] **Hybrid live view.** Poll state.json + progress_log.jsonl for the pipeline/stage graph
   (1-2s); add an additive log 'tee' → per-task log files the backend tails and pushes via SSE for
   real-time agent/aider output. No pipeline control-flow rewrite.
4. [RESOLVED] **Refactor maps to dashboard-owned config.** Move MODEL_ALIASES + STAGE_POLICIES from
   Python into editable YAML/JSON loaded at runtime (Python dict as fallback default). Dashboard manages
   both agent→alias and LiteLLM alias→real-model, with validated writes + hot-reload where possible.
5. [RESOLVED] **Fix drift structurally + edit one source.** Symlink `~/.hermes/skills` → single
   canonical skills tree. Dashboard edits that one place with: validation gate (lint frontmatter, flag
   Output-Schema edits as breaking-change) + auto git-commit per edit for audit + one-click rollback.
   No restart needed (skills read per-invocation).
6. [RESOLVED] **Config scope = all** (roster, stage policies, cron, gateway, agent-model config) per
   full-control decision. **Apply mechanism:** scoped sudoers for `uws` → `systemctl restart/reload
   uws-hermes` (+ LiteLLM reload) only; batched "Apply & restart" guarded against in-flight builds;
   hot-reloadable edits (LiteLLM aliases) apply instantly.
7. [RESOLVED] **Co-equal web + Telegram HITL.** Dashboard reads pending_hitl.db, renders all 6 HITL
   states with full context (diff/plan/clarification/recovery options), resolves via the same
   workshop_continue.py path Telegram uses; resolving from either channel stales the other.
8. [RESOLVED] **Real metering via LiteLLM spend logs.** Enable LiteLLM spend logging to a DB; tag every
   request with task_id + agent/role metadata. Dashboard shows true cost per build/stage/agent/model +
   daily/monthly trends + budget burn.
9. [RESOLVED] **Tailscale/WireGuard private network + single-owner app login.** Backend bound to
   localhost on the VPS, reachable only over the tailnet; app-level password/token as defense-in-depth.
   No public port, no inbound firewall hole.
10. [RESOLVED] **FastAPI + React/Vite SPA.** Python FastAPI backend (uvicorn, systemd as `uws`) importing
    workshop/ modules directly (reuse Pydantic models, cost/ledger, shell workshop_continue.py).
    Frontend: React + Vite + TypeScript + shadcn/ui, Monaco editor for SKILL.md, SSE for live logs.
11. Suggested extra features — prioritize

## Verification corrections (from adversarial design pass)
- **Skill drift fix (item 5) — direction corrected.** The 3 specialist-homes ALREADY symlink to
  `~/.hermes/skills` (04-UAT.md:112). `~/.hermes/skills` is the STALE copy; `/opt/ultra-workshop/skills`
  is canonical (install.sh rsyncs `/opt`, never `~/.hermes/skills`). Correct fix:
  `rm -rf /home/uws/.hermes/skills && ln -sf /opt/ultra-workshop/skills /home/uws/.hermes/skills`.
  Then dashboard edits ONE path: `/opt/ultra-workshop/skills/<n>/SKILL.md`. VPS pre-checks required:
  confirm symlink states + diff `~/.hermes/skills` vs `/opt/.../skills` for orphan skills before `rm -rf`.
- **Cost metering (item 8) — mechanism corrected.** Running LiteLLM (`:4000`) is Brain-owned
  (ultra-agents-brain docker-compose), NO DB. Spend logs are dropped without prisma. ⇒ Use
  `SPEND_LOGS_URL=http://127.0.0.1:7010/internal/spend-update` so LiteLLM POSTs batched spend to the
  DASHBOARD backend, which stores its own SQLite. Per-request tagging via `x-litellm-spend-logs-metadata`
  header (+ aider `--user <task_id>`). No Postgres needed.
- **Hot-reload (item 6) — NOT available without DB.** No `/config/reload` endpoint. Alias change =
  rewrite config.yaml + `docker restart deploy-litellm-1` (~5s, root). True hot-reload deferred to v2.
- **Refactor (item 4) is self-contained**: only `workshop/stage_policy.py` internals change; the 3
  accessor fns (`stage_model_alias`/`stage_policy`/`stage_tool_timeout`) keep signatures ⇒ ~15 call
  sites in workshop_build.py/workshop_coder.py/workshop_continue.py need ZERO change. `stage_policy()`
  must still return the `StagePolicy` dataclass. Apply `UWS_CODER_MAX` env override at load time.
- **HITL resolve blocks**: `workshop_continue.py` shells `workshop_build.py --resume` synchronously ⇒
  backend must call it via `asyncio.to_thread` and return 202; progress observed via state.json.
- **Log tee is additive & safe**: `_run_aider_runner` collects stdout via select-loop (never prints);
  add `log_file` kwarg + tee in the `if data:` block → per-task `aider_step_N.log`. JSON protocol untouched.

## Open decision (RESOLVED) — LiteLLM proxy ownership
**Dedicated Workshop LiteLLM proxy.** Stand up a Workshop-owned LiteLLM (own container/config, port
`:4001`, small SQLite for spend) and repoint ONLY the inference `base_url` in `hermes-config/config.yaml`
(+ aider `--openai-api-base`) to it. Verified two-channel separation: the `brain_http.py → :7000` channel
(Workshop→Brain agents) is independent and untouched ⇒ **full Brain access preserved.** This gives
Workshop sole ownership of model routing + true spend metering, matching the "separate projects" principle.

## Recommended approach

### Architecture
A standalone Workshop dashboard, fully decoupled from Brain:
- **Backend**: FastAPI (uvicorn) as systemd `uws-hermes-dashboard.service`, user `uws`, bound `127.0.0.1:7010`.
  Imports `workshop/` directly (reuses Pydantic models, `cost`/`ledger`, shells `workshop_continue.py`).
- **Frontend**: React + Vite + TypeScript + shadcn/ui SPA, built locally, served by the backend via
  `StaticFiles(html=True)` mount (no nginx). Monaco for SKILL.md, native `EventSource` for SSE.
- **Access**: Tailscale tailnet only (no public port) + single-owner session-cookie auth
  (`secrets.compare_digest`, HttpOnly+SameSite=Strict; cookie also authorizes SSE).
- **Dedicated LiteLLM** `:4001` with `SPEND_LOGS_URL=http://127.0.0.1:7010/internal/spend-update` →
  backend stores spend in its own SQLite; per-request tags via `x-litellm-spend-logs-metadata` +
  aider `--user <task_id>`.
- **Apply mechanism**: scoped sudoers (`systemctl restart/reload uws-hermes`,
  `systemctl restart uws-hermes-dashboard`, `docker restart` the Workshop proxy) — exact commands, no globs.

### Backend module layout (`dashboard/backend/`)
`main.py` (app factory+lifespan), `config.py` (Pydantic Settings), `deps.py` (auth + in-flight guard),
`security.py`, `routers/{tasks,cost,config_api,skills,hitl,control,repos,sse}.py`,
`services/{task_store,cost_service,hitl_service,config_service,build_trigger,log_tailer}.py`,
`models/api_models.py`. Entry: `uvicorn dashboard.backend.main:app --host 127.0.0.1 --port 7010`.

### Frontend layout (`dashboard/`)
Vite app; pages: `/board` (kanban), `/tasks/:id` (pipeline graph + SSE logs + per-stage panes),
`/hitl` (6 typed cards), `/config/{models,reviewers,policies}`, `/skills/:name` (Monaco + dry-run +
git history), `/cost`, `/health`, `/repos`, `/launch`. TanStack Query (REST) + Router (typed) +
`@tanstack/react-virtual` (log viewer) + recharts. Component tree per frontend design doc.

### Phased roadmap (each phase shippable)
- **Phase 0 — Prep (no UI).** (a) Fix skill drift: `rm -rf ~/.hermes/skills && ln -s /opt/ultra-workshop/skills`
  after VPS pre-checks. (b) Refactor `workshop/stage_policy.py` → load `hermes-config/stage-policies.yaml`
  (dicts as fallback, `StagePolicy` dataclass preserved, `UWS_CODER_MAX` applied at load, 0–30s cache).
  (c) Stand up dedicated LiteLLM `:4001` + repoint inference base_url. (d) `SPEND_LOGS_URL` wiring +
  metadata tagging. Verify pipeline still builds end-to-end (dry-run + one real build).
- **Phase 1 — Read-only observability.** Backend `task_store`/`cost_service` + `/tasks`, `/cost`, `/health`
  + SSE (`/sse/tasks/:id/{events,logs}`) with the additive aider log-tee. Frontend board + task detail +
  cost + health. (Delivers "see agents in action + monitor logs".)
- **Phase 2 — Model switching + config.** Config API (models/roster/stage-policies/cron) with validation
  gates; agent→alias matrix UI; alias→model editor + `docker restart :4001` apply; reachability checks.
- **Phase 3 — Control writes.** Skill editor (single canonical path, Output-Schema breaking-change warning,
  git-commit per edit + rollback) + dry-run playground; HITL co-equal resolve via `workshop_continue.py`
  (202 + `asyncio.to_thread`); guarded restart.
- **Phase 4 — Extras.** Build/fix launcher + repo registry; cron control + budget editor; health
  model-reachability that catches the `planner-reasoner` class of bug pre-build.

### Key validation gates (so a dashboard edit can't break the pipeline)
`validate_task_id` on every task endpoint; roster write requires security+correctness present; model-alias
write cross-checked against LiteLLM `model_list`; stage-policy write requires all stages; SKILL.md write
size-bounded + name regex + Output-Schema-edit flagged; restart blocked while a build is in-flight
(state.json scan + `pgrep workshop_build.py`, with explicit "Force" override).

## Verification
1. **Phase 0 regression**: `python -c "from workshop.stage_policy import stage_model_alias; print(stage_model_alias('coder-specialist'))"` → `coder-worker` (proves YAML refactor + fallback). Run one
   `workshop_build.py --dry-run` and one real build → pipeline unaffected; aider `--user` shows in spend SQLite.
   Confirm skill edit at `/opt/.../skills/X/SKILL.md` is seen live by a Hermes specialist run (drift gone).
2. **Backend unit tests**: `task_store` against a tmp tasks dir; config services atomic-write + validation
   rejection cases; `hitl_service.list_pending_hitl` against a seeded `pending_hitl.db`.
3. **Live e2e**: trigger a build from `/launch`; watch the board card advance triage→…→reviewer; open task
   detail and confirm SSE log stream + pipeline graph + diff/findings render; drive a HITL state and resolve
   it from the web → state.json advances; verify Telegram still resolves the same row.
4. **Model switch e2e**: change an agent's alias in the matrix → save → next build for that agent uses the
   new model (check spend SQLite `model` column). Reachability panel flags a deliberately-bad alias.
5. **Security**: confirm `:7010` is loopback-only; reachable on tailnet; unauthenticated request → 401;
   sudoers allows only the four whitelisted commands (`sudo -l` as `uws`).

## Verification
_(to be written)_
