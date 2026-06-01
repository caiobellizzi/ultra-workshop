# Dashboard Missing Features Plan

Features shown in the round2 mockups that have **no backend support** and need API/data work
before the UI can be fully wired. Discovered during the layout-match pass.

> Status legend: 🔴 not started · 🟡 partial (UI shell exists, data missing)

---

## Launch Task page

The mockup shows a richer launch form than the backend currently accepts. `POST /api/tasks`
only takes `{ repo, goal, brainstorm }`.

### 🔴 Per-task base branch selector
- **Mockup shows:** "Base Branch" dropdown (main / develop / staging)
- **Missing:** `tasks.create` ignores branch; backend always uses repo default branch
- **Requires:** add `branch` to `POST /api/tasks` body + workshop_build branch checkout
- **Effort:** M · **Priority:** medium

### 🔴 Per-task coder model override
- **Mockup shows:** "Coder model" dropdown (sonnet/opus/haiku)
- **Missing:** model is resolved from Models config, no per-task override
- **Requires:** `model_alias` field on create + plumb through to coder stage
- **Effort:** M · **Priority:** low (Models config already governs this globally)

### 🔴 Per-task skill profile
- **Mockup shows:** "Skill profile" dropdown (default / backend-api / frontend-react / infra-terraform)
- **Missing:** no concept of skill profiles in backend
- **Requires:** define skill-profile presets + selection mechanism — larger design
- **Effort:** L · **Priority:** low

### 🔴 Reviewer / dry-run toggles
- **Mockup shows:** "Run reviewer after coder", "Dry run (plan only)" checkboxes
- **Missing:** create only accepts `brainstorm`; reviewer is policy-driven, no dry-run mode
- **Requires:** `run_reviewer` + `dry_run` flags on create + pipeline support for plan-only mode
- **Effort:** M (reviewer toggle) / L (dry-run) · **Priority:** medium

### 🟡 Queue stats panel
- **Mockup shows:** running / queued / hitl-pending / max-concurrency + concurrency bar
- **Wired now:** running (derived from tasks list), hitl-pending (from /api/hitl)
- **Missing:** `queued` count, `max_concurrency` — no queue-depth endpoint
- **Requires:** `GET /api/queue/stats` returning {running, queued, hitl_pending, max_concurrency}
- **Effort:** S · **Priority:** medium

### 🔴 Model cost estimate
- **Mockup shows:** "model cost est. ~$0.08 – $0.40" below launch button
- **Missing:** no estimation endpoint
- **Requires:** `POST /api/cost/estimate {repo, goal}` heuristic — larger work
- **Effort:** L · **Priority:** low

### 🔴 Per-repo policy note
- **Mockup shows:** "● policy: strict — HITL enforced for my-saas-app/main"
- **Missing:** policy is global (stage-policies), not surfaced per repo on launch
- **Requires:** expose effective policy for selected repo (reuse /api/config/stage-policies)
- **Effort:** S · **Priority:** medium

---

## Board page

### 🔴 Per-model usage breakdown on summary strip
- **Mockup shows:** "claude-sonnet-4-6 × 6 · claude-haiku-4-5 × 2" model-mix chips
- **Missing:** `TaskSummary` has no model field; can't aggregate model usage
- **Requires:** add `model_alias` to TaskSummary, or a `/api/tasks/model-mix` endpoint
- **Effort:** S · **Priority:** low
- _(running/HITL/pushed/failed counts + session cost are wired from the task list)_

## Cost page

### 🔴 Period-over-period trend deltas
- **Mockup shows:** "↑ $3.12 vs prior 30d" on each stat card
- **Missing:** `CostSummary` returns current-period totals only, no prior-period comparison
- **Requires:** `/api/cost/summary` to also return prior-period totals (or a `compare=true` param)
- **Effort:** M · **Priority:** low
- _(period selector 7d/30d/90d/all and Export CSV are now wired)_

## Health page

### 🔴 Process metrics (PID / memory / port)
- **Mockup shows:** per-service pid, mem (MB), port rows
- **Missing:** `ServiceStatus` has only name/running/uptime_seconds/version
- **Requires:** extend `/api/health` services with pid, rss_bytes, port
- **Effort:** M · **Priority:** low

## Skills page

### 🔴 Skill run stats + per-skill model/timeout/enabled
- **Mockup shows:** "Runs Today 47", "Avg Duration 4m 12s" stat cards; per-card model, timeout, enabled toggle
- **Missing:** `SkillMeta` has only name/version/description/tags/path; no run telemetry or enable flag
- **Requires:** skill-run telemetry store + `enabled` field + `/api/skills/stats`
- **Effort:** L · **Priority:** low
- _(skill count, search, tag badge, View/Edit wired)_

### 🔴 Import SKILL.md / Register Skill
- **Mockup shows:** topbar "Import SKILL.md" + "Register Skill" buttons
- **Missing:** no create-skill endpoint (only `PUT /api/skills/:name` to edit existing)
- **Requires:** `POST /api/skills` create + file upload handling
- **Effort:** M · **Priority:** medium

## Repos page

### 🔴 Per-repo task counts + activity stats
- **Mockup shows:** "Total Tasks 142", "Active Now 3" stats; per-repo task-count bar + last-task timestamp + running status
- **Missing:** `Repo` has full_name/default_branch/active/last_used; no task counts per repo
- **Requires:** `/api/repos` to include `task_count`, `active_task_count`, `last_task_at`
- **Effort:** M · **Priority:** medium
- _(table, branch chip, add, sync, delete-with-confirm, empty state wired)_

## Skill Editor page

### 🔴 Multi-file tabs (config.yml / hooks.yml) + metadata side panel
- **Mockup shows:** editor tabs for config.yml / hooks.yml; right metadata panel
- **Missing:** `SkillDetail` exposes only the SKILL.md `content` string
- **Requires:** `/api/skills/:name` to return sibling files (config.yml, hooks.yml) + metadata
- **Effort:** M · **Priority:** low
- _(breadcrumb title, Discard/Save, schema-change warning, theme-bound Monaco wired)_

## HITL Queue page

### 🔴 Per-card cost strip (stage / model / tokens / waiting time)
- **Mockup shows:** "stage planner · model claude-sonnet-4-6 · tokens 48k/3.2k · waiting 7m 14s"
- **Missing:** `HITLItem` has task_id/hitl_type/payload/created_at only
- **Requires:** enrich `/api/hitl` items with stage, model, token counts, waiting duration
- **Effort:** M · **Priority:** medium
- _("✗ N TASKS BLOCKED" header + card list wired; HITLCard already normalized_

## Pages with no backend gaps (layout fully matched)

- **Login** — centered brand card, divider, footer ✓
- **Task Detail** — 3-panel (pipeline + metadata / output + logs / review findings slide-over) ✓
- **Models / Reviewers / Policies config** — tables wired to real config endpoints ✓
  (mockup's reviewer stat cards + flat global policies like `max_cost_per_task` / `quiet_hours`
  are not in the backend's per-stage model — see below)

### 🔴 Reviewers: edit drawer + reviewer run telemetry
- **Mockup shows:** stat cards (Reviews Run / Issues Found / Avg Latency), per-row Edit drawer, priority dots, last-run
- **Missing:** no reviewer telemetry; `ReviewerEntry` has no priority/id/last_run; no edit-drawer UI
- **Requires:** reviewer-run telemetry + edit form (PUT exists) + `priority` field
- **Effort:** L · **Priority:** low

### 🔴 Policies: flat global policies (max_cost_per_task, quiet_hours, hermes_restart_on_error)
- **Mockup shows:** global runtime toggles for cost ceiling, quiet hours, auto-restart
- **Missing:** backend models policies **per-stage** (`stage_policies`), not as flat globals
- **Requires:** decide whether to add global policy keys or keep per-stage (design decision)
- **Effort:** M · **Priority:** low

