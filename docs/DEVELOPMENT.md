<!-- generated-by: gsd-doc-writer -->
# Development Guide

Target audience: a developer extending or maintaining the ultra-workshop codebase.

---

## Local Setup

### Prerequisites

- Python 3.11+ with `uv` (used for the virtualenv and test runner)
- Node.js 20+ and `pnpm` (dashboard frontend)
- Docker (LiteLLM proxy container)
- A running LiteLLM proxy at `127.0.0.1:4000` (or `:4001` for the dedicated workshop proxy)

### Clone and install

```bash
git clone <repo-url> ultra-workshop
cd ultra-workshop

# Python environment
uv venv
source .venv/bin/activate
uv pip install -r dashboard/backend/requirements.txt

# Frontend
cd dashboard/frontend
pnpm install
cd ../..
```

### Environment variables

The backend reads settings with the `UWS_DASH_` prefix from `.env` in the working directory or from real environment variables. The minimal set for local development:

```bash
# .env (project root)
UWS_DASH_COOKIE_SECRET=dev-secret-change-me   # insecure default; backend warns if unchanged
UWS_DASH_SECURE_COOKIE=false                  # allow HTTP in local dev
UWS_DASH_LOGIN_PASSWORD=yourpassword          # leave blank to fall back to cookie_secret
```

Path settings (`UWS_DASH_TASKS_BASE`, `UWS_DASH_HERMES_CONFIG_DIR`, etc.) are automatically resolved to repo-relative fallbacks by `Settings.resolve_paths()` when the VPS paths do not exist locally. See `dashboard/backend/config.py` for the full settings schema.

---

## Build Commands

### Python (workshop package + backend)

| Command | Description |
|---|---|
| `uv run pytest` | Run the full Python test suite (paths: `hermes-skills/`, `scripts/`, `tests/`) |
| `uv run pytest tests/phase-04/` | Run a single phase |
| `uv run python -m dashboard.backend.main` | Start the FastAPI backend on `127.0.0.1:7010` |

### Frontend

| Command | Description |
|---|---|
| `pnpm dev` | Start the Vite dev server; proxies `/api`, `/auth`, `/internal` to `127.0.0.1:7010` |
| `pnpm build` | Type-check then produce a production build in `dashboard/frontend/dist/` |
| `pnpm typecheck` | Run `tsc --noEmit` only (no emit, fast feedback) |
| `pnpm preview` | Preview the production build locally |

### LiteLLM proxy (Docker)

```bash
# Start the dedicated workshop proxy on :4001
docker compose -f deploy/litellm/docker-compose.workshop.yml up -d

# Health check
curl -s http://127.0.0.1:4001/health | python3 -m json.tool
```

The default Hermes config (`hermes-config/config.yaml`) points to `http://127.0.0.1:4000/v1`. Update `base_url` there to switch between ports. No code changes are needed for model routing changes — edit `model_aliases` in `hermes-config/stage-policies.yaml`.

---

## Code Style

### Python

- **Type annotations** throughout — all functions are annotated; Pydantic is used for every data contract.
- No dedicated linter config is checked in; match the existing style (snake_case, `from __future__ import annotations`, `# Deploy location:` comments on VPS-deployed files).
- All specialist scripts must emit a single JSON object to stdout. The orchestrator's `run_specialist()` in `workshop/orchestrator.py` parses `stdout` exclusively.

### Frontend (TypeScript + React)

- **TypeScript strict mode** — `tsconfig.json` enforces this; `pnpm typecheck` must pass.
- **Tailwind CSS** for styling; no CSS modules or inline styles.
- **shadcn/ui primitives** via Radix UI components (see `dashboard/frontend/package.json` for the exact Radix packages in use).
- Path alias `@/` resolves to `dashboard/frontend/src/` (configured in `vite.config.ts` and `tsconfig.json`).
- Code splitting: Monaco editor is lazily chunked as `monaco-react`; vendor/query/charts have their own named chunks (see `vite.config.ts` `manualChunks`).

---

## Branch Conventions

- `workshop/<4hex>-<slug>` — branches created by the pipeline for automated builds (e.g., `workshop/a3f1-add-auth`). Never push to these manually.
- `feat/<description>` — developer feature branches (e.g., `feat/control-dashboard`).
- `fix/<description>` — bug-fix branches.
- `main`/`master` — never touched directly in production. All pushes gate on HITL approval.

---

## Extending the Pipeline

### Adding a new specialist stage

1. Add a `SKILL.md` to `skills/<specialist-name>/` following the existing skill format.
2. Add the matching Pydantic output schema to `workshop/types.py`.
3. Register the stage in `hermes-config/stage-policies.yaml` under `stage_policies` (with `timeout`, `auto_retries`) and add a `model_aliases` entry.
4. Call `run_specialist()` from `hermes-skills/workshop_build.py` at the appropriate point in the pipeline, passing the new schema as the `output_schema` argument.

The stage index in `workshop_build.py` (`_STAGE_INDEX`) controls the ordering guard — update it if the new stage has a defined position in the sequence.

### Changing model routing

Edit only `hermes-config/stage-policies.yaml` — the `model_aliases` section maps role names to LiteLLM route aliases (`cheap-fast`, `reviewer-model`, `coder-worker`, etc.). No Python changes are needed.

### Adding a dashboard API endpoint

1. Create a new file in `dashboard/backend/routers/` (e.g., `my_feature.py`) with a `router = APIRouter()`.
2. Add Pydantic request/response models to `dashboard/backend/models/` or inline in the router.
3. Register the router in `dashboard/backend/main.py` via `application.include_router(my_feature.router)`.
4. The `internal` router (`dashboard/backend/routers/internal.py`) is unauthenticated by design — loopback only. All other routers use `require_auth` from `dashboard/backend/deps.py`.

---

## Locked Constraints

These constraints are architectural decisions — do not work around them:

| Constraint | Rationale |
|---|---|
| No LangGraph or orchestration frameworks | Hermes + Python subprocess only |
| Coder = Aider only | `hermes-skills/aider_runner.py` wraps Aider; no other coding agents |
| All LLM calls via LiteLLM at `127.0.0.1:4000` | Central routing, spend tracking, and key isolation |
| HITL required before any `git push` | `dashboard/backend/deps.py` `check_no_inflight` + HITL gate enforced in `workshop_push.py` |

---

## Budget Circuit Breaker

`workshop/cost.py` enforces two thresholds read from `cost-ledger.md`:

- **Warning** (`$18.00/day`) — in cron mode, raises `BudgetWarning` and cancels the routine.
- **Hard stop** (`$20.00/day`) — in all modes, raises `BudgetExhausted` and refuses new LLM calls.

Per-role monthly caps are also enforced (see `ROLE_MONTHLY_CAPS` in `workshop/cost.py`). Exhaustion raises `RoleBudgetExhausted`; 80% usage raises `RoleBudgetWarning` (with Telegram notification).

---

## PR Process

1. Branch from `master` using the naming convention above.
2. Run `pnpm typecheck` and `uv run pytest` locally; both must pass.
3. Open a PR against `master`. The `summary.yml` GitHub Actions workflow runs on schedule (daily) — there are no per-PR CI gates currently configured.
4. All changes that affect the pipeline path (specialists, stage policies, cost thresholds) require HITL review before merge.
5. Never merge pipeline automation branches (`workshop/<4hex>-<slug>`) manually — they are managed by the pipeline.

---

## See Also

- `docs/ARCHITECTURE.md` — component diagram and data flow
- `docs/CONFIGURATION.md` — full environment variable reference
- `deploy/DASHBOARD-DEPLOY.md` — VPS deployment runbook
- `hermes-config/stage-policies.yaml` — stage timeouts and model routing
- `hermes-config/review-roster.yaml` — reviewer roles, isolation flags, and monthly budget caps
