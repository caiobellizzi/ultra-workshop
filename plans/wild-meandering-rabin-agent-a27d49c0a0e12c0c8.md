# Frontend Design Plan — Ultra-Workshop Dashboard

## Status: DESIGN COMPLETE — awaiting implementer

---

## 1. Data Model Inventory (ground truth from codebase)

### Task State (`state.json` schema from `workshop/state.py::new_task_state`)

```
task_id, goal, repo, status, next_stage, current_step
stages: { [stage_name]: { result, attempts, ... } }
attempts: { [stage]: count }
clarifications: []
hitl_responses: []
recovery_decisions: []
approval_payload: {}      # active HITL payload when status=needs_approval
timeout_payload: {}
created_at, updated_at
workspace_dir
repo_full_name, default_branch
```

**Status enum** (exhaustive from workshop_build.py):
- `running`
- `needs_approval`         (plan approval gate)
- `needs_clarification`    (specialist asked a question)
- `needs_step_recovery`    (step retry exhausted)
- `needs_review_recovery`  (reviewer retries exhausted)
- `needs_timeout_recovery` (stage timed out)

**HITL payload shapes** (6 types, `hitl_type` discriminant):
1. `approval` — plan approved/rejected, has options[]
2. `clarification` — ClarificationRequest: questions[], options[], allow_free_text
3. `step_retry_exhausted` — step_idx, step_desc, decompose_attempted, options[]
4. `review_retry_exhausted` — blocking_issues[], branch, diff_summary, options[]
5. `timeout_recovery` — stage, attempt, reason, options[]
6. `brainstorm` — approved bool, goal_statement, follow_up

**Progress log events** (from `progress_log.jsonl`):
`triage_complete`, `requirements_complete`, `plan_complete`, `coder_complete`,
`clarification_requested`, `clarification_received`, `stage_retry`,
`step_retry_exhausted`, `timeout_recovery_requested`, `wave_complete`, `merge_complete`

### Pipeline stages in order
`brainstorm → triage → requirements → planner → coder (multi-step) → reviewer-wave (9 parallel) → merge → approval → push/PR`

### Key types (`workshop/types.py`)
- `Plan` → goal, steps: PlanStep[], affected_files[]
- `PlanStep` → id, description, files[], model_alias
- `Diff` → summary, changes: FileChange[], branch, build_passed, test_passed, output_tail
- `WaveReport` → role, passed, findings: ReviewFinding[], tokens_used, cost_cents
- `MergeReport` → block_push, critical_findings[], important_findings[], auto_fixed[], summary
- `ReviewFinding` → file, line, problem, required_fix, severity: "Critical"|"Important"|"Minor"
- `ClarificationRequest` → task_id, source_stage, reason, questions[], options[], allow_free_text, evidence[]

### Review roster (9 roles from `hermes-config/review-roster.yaml`)
correctness, security (always-on, isolation:true), python, typescript, reactjs, qa, docs, config (diff-gated, isolation:false)

### LiteLLM aliases (`deploy/litellm/config.yaml`)
orchestrator, default-worker, cheap-worker, private-worker, planner-reasoner, coder-worker, reviewer-model, cheap-fast, cloud-sonnet, cloud-groq
Fallback chains configured per alias.

### SKILL.md anatomy (from python-reviewer + planner-specialist)
YAML frontmatter: name, description, version, author, license, metadata.hermes.tags
Sections: Discipline, Behavior, Output Schema, Dry-run Behavior
Output Schema contains JSON shape the skill emits to stdout.

---

## 2. Information Architecture

```
/                           → redirect → /board
/board                      → Live Board (primary landing)
/tasks/:taskId              → Task Detail
/hitl                       → HITL Queue
/config/models              → Config — Models (agent→alias matrix)
/config/reviewers           → Config — Reviewers/Roster
/config/policies            → Config — Stage Policies + Gateway + Cron
/skills                     → Skill List
/skills/:skillName          → Skill Editor (Monaco)
/cost                       → Cost Analytics
/health                     → Health Dashboard
/repos                      → Repo Registry
/launch                     → Build Launcher
```

Auth gate wraps all routes. Login page at `/login`.

---

## 3. Page Designs

### 3.1 Live Board (`/board`)

**Purpose**: At-a-glance view of every active task as a Kanban column per stage.

**Columns** (left to right, matching `_STAGE_INDEX`):
`Brainstorm | Triage | Requirements | Planner | Coder | Reviewer | Approval/HITL | Done | Failed`

**Card content** (per task):
- Task ID (monospace, truncated) + goal (first 80 chars)
- Stage badge (colored pill matching stage)
- Status badge:
  - `running` → animated pulse dot, blue
  - `needs_approval` → orange bell icon
  - `needs_clarification` → orange question mark
  - `needs_step_recovery` / `needs_review_recovery` / `needs_timeout_recovery` → red warning triangle
- Current step / total steps (e.g. "Step 2/4") — only in coder column
- Cost-so-far in USD (from wave reports tokens_used sum)
- Time elapsed since created_at
- Click → navigate to `/tasks/:taskId`
- HITL items show "Resolve" button → navigate to `/hitl?taskId=:id`

**Key shadcn components**:
- `Card` (each task card)
- `Badge` (status + stage labels)
- `ScrollArea` (each column independently scrollable)
- `Button` (Resolve shortcut)
- `Tooltip` (truncated goal hover)

**Backend endpoints**:
- `GET /api/tasks` → `{ tasks: TaskSummary[] }` (paginated, active only by default)
  - `TaskSummary`: task_id, goal, status, next_stage, current_step, total_steps, created_at, updated_at, cost_cents_so_far, repo_full_name
- Polling: TanStack Query `refetchInterval: 5000`

**States**:
- Loading: skeleton cards in each column
- Empty board: centered illustration + "No active tasks. Launch a build →" CTA
- Error: toast + retry button

---

### 3.2 Task Detail (`/tasks/:taskId`)

**Purpose**: Full pipeline observability for one task.

**Layout** (three panes):
1. Left panel (fixed 280px): pipeline graph (stage nodes) + metadata sidebar
2. Center (flex): stage output tabs + live log
3. Right panel (360px, collapsible): HITL action panel (shown when task needs attention)

**Pipeline Graph** (left panel):
- Vertical node list, one node per stage in `_STAGE_INDEX` order
- Each node shows: stage name, status icon, attempt count (if >1), duration
- Node states: pending (gray), running (blue pulse), success (green check), failed (red X), skipped (dimmed), needs_hitl (orange bell)
- Edge arrows between nodes
- Current stage node is highlighted/enlarged
- Built with a simple SVG or flexbox — NOT a full graph library (see tricky pieces section)

**Center — Stage Output Tabs** (shadcn `Tabs`):
- Tab per stage that has data in `state.stages`
- Each stage tab shows the relevant output:
  - **triage**: task_type, complexity, summary
  - **requirements**: ready bool, context text
  - **planner**: Plan viewer — goal, step cards (each showing id, description, files[])
  - **coder**: Per-step execution status, current_step cursor, Diff viewer (file tree + unified diff per FileChange)
    - Build badge (passed/failed), Test badge (passed/failed), output_tail (collapsible code block)
  - **reviewer**: WaveReport table — one row per reviewer role, passed/failed, findings count, cost_cents
    - Expandable finding rows: file, line, severity (color-coded), problem, required_fix
    - MergeReport summary section
  - **approval**: approval_payload display with decision record

**Center — Live Log Stream** (below tabs):
- SSE-powered log tail from `GET /api/tasks/:taskId/logs/stream`
- Fixed-height scrollable textarea-style container (virtualized rows)
- Auto-scroll toggle (default on, pauses on manual scroll up)
- Filter bar: text search, level selector (info/warn/error)
- Clear / Export buttons

**Right — HITL Panel** (shown when `task.status != "running"` and `!= "completed"`):
- Rendered from `approval_payload.hitl_type` discriminant
- See Section 5 (HITL Queue) for per-type renderers

**Metadata sidebar**:
- repo_full_name (link to GitHub)
- branch name
- task_id, created_at, updated_at
- total cost (sum of wave report cents)
- attempt counts per stage

**Backend endpoints**:
- `GET /api/tasks/:taskId` → full `TaskDetail` (state.json contents + enriched stage outputs)
- `GET /api/tasks/:taskId/logs/stream` → SSE stream of `progress_log.jsonl` tail + live events
  - Event format: `data: { ts, event, ...payload }\n\n`
- `POST /api/tasks/:taskId/hitl` → submit HITL resolution `{ decision: string, free_text?: string }`

**States**:
- Loading: skeleton for graph + center pane
- Task not found: 404 card
- Completed task: read-only, no HITL panel
- Log stream connection error: banner + reconnect button

---

### 3.3 HITL Queue (`/hitl`)

**Purpose**: Single-screen triage for all tasks needing human input.

**Layout**: vertical card list, sorted by created_at ascending (oldest first = most urgent).

**Filter bar**: `All | approval | clarification | step_recovery | review_recovery | timeout_recovery | brainstorm`

**Per-card structure** (varies by `hitl_type`):

#### `approval` (plan approval)
- Goal statement
- Plan steps accordion (collapsible PlanStep list with files)
- Affected files list
- Two primary buttons: **Approve** / **Reject**
- Optional free-text override field

#### `clarification`
- source_stage badge
- reason text
- Per-question block: question text, options as radio group, free-text field (if allow_free_text)
- evidence excerpts (collapsible)
- Submit button

#### `step_retry_exhausted`
- step_idx, step description
- decompose_attempted indicator
- reason text
- 4 options as radio (numbered, from payload.options[])
- Free-text field
- Submit button

#### `review_retry_exhausted`
- diff_summary
- blocking_issues table (file, problem, required_fix) — same severity coloring as Task Detail
- branch badge
- 4 options as radio
- Submit

#### `timeout_recovery`
- stage badge, attempt count
- reason
- 4 recovery options as radio
- Submit

#### `brainstorm`
- goal_statement display
- follow_up text (if set)
- Approve / Reject buttons

**shadcn components**: `Card`, `Accordion`, `RadioGroup`, `Textarea`, `Button`, `Badge`, `Separator`, `Alert`

**Backend endpoints**:
- `GET /api/hitl` → `{ items: HITLItem[] }` where HITLItem = `{ task_id, hitl_type, payload, created_at }`
- `POST /api/tasks/:taskId/hitl` → same endpoint as Task Detail
- Polling: `refetchInterval: 3000` (HITL is time-sensitive)

**States**:
- Empty queue: "All clear — no pending decisions" with green check illustration
- Error submitting: inline error on the card, card stays in queue
- Optimistic update: card grays out + spinner while POST in flight

---

### 3.4 Config — Models (`/config/models`)

**Purpose**: Edit the agent→model-alias routing matrix and inspect LiteLLM aliases.

**Layout**: Two sections, stacked.

**Section A — Agent→Alias Matrix**:
- Table rows: one per skill/agent from `stage_policy.MODEL_ALIASES` (17 entries)
- Columns: Agent Name | Current Alias (editable Select) | Stage Policy timeout
- Alias options: the `model_list` names from `litellm/config.yaml`
- Inline edit via `Select` per cell
- "Save Changes" button → `PUT /api/config/models/aliases`
- Unsaved changes indicator (orange dot in nav)

**Section B — Alias Definitions**:
- Table: Alias Name | Provider | Model ID | Timeout | Retries | Fallback chain
- One row per `model_list` entry from `config.yaml`
- Reachability badge per alias (green/yellow/red from `/api/health/models`)
- "Pending restart" indicator when changes were saved but LiteLLM not reloaded
- "Reload LiteLLM" button → `POST /api/config/litellm/reload`

**shadcn**: `Table`, `Select`, `Badge`, `Button`, `Alert`

**Backend**:
- `GET /api/config/models` → `{ aliases: ModelAlias[], routing: AgentRouting[] }`
- `PUT /api/config/models/aliases` → save routing changes
- `GET /api/health/models` → per-alias reachability
- `POST /api/config/litellm/reload`

---

### 3.5 Config — Reviewers (`/config/reviewers`)

**Purpose**: Edit `hermes-config/review-roster.yaml` entries.

**Layout**: Table of reviewer rows, each editable inline.

**Columns**: Role | Model Alias | Isolation | File Patterns | Monthly Budget (cents) | Fallback Alias | MTD Spend | Budget % bar

- `isolation` rendered as a toggle (always-on roles: locked true, shown grayed)
- `file_patterns` as tag input (add/remove .ext strings)
- `monthly_budget_cents` as number input
- MTD spend and budget % bar pulled from `/api/cost/roles`

- "security" and "correctness" rows have a lock icon: isolation cannot be toggled off
- Add reviewer row button (for future roles)
- Delete button on non-protected rows
- Save → `PUT /api/config/reviewers`

**shadcn**: `Table`, `Switch`, `Input`, `Progress`, `Button`, `Badge`

**Backend**:
- `GET /api/config/reviewers` → roster array
- `PUT /api/config/reviewers` → save full roster
- `GET /api/cost/roles` → `{ [role]: { spend_cents, cap_cents, month } }`

---

### 3.6 Config — Policies, Gateway, Cron (`/config/policies`)

**Three subsections** via `Tabs`:

#### Stage Policies tab
- Table: Stage | Timeout (s) | Tool Timeout | Auto Retries | HITL on Timeout
- Editable inline (number inputs + toggle)
- `PUT /api/config/policies/stages`

#### Gateway tab
- Telegram chat_id display (read-only, from env)
- HITL DB location display
- Hermes service status (running/stopped) + Restart button
- `POST /api/gateway/restart`

#### Cron tab
- Table: Job Name | Schedule | Last Run | Next Run | Status | Budget Cap | Actions
- 4 cron jobs (from vault cron config)
- Enable/Disable toggle per job
- "Run Now" button
- Budget cap editor (number input)
- `GET /api/cron` / `PUT /api/cron/:job` / `POST /api/cron/:job/trigger`

---

### 3.7 Skill Editor (`/skills` + `/skills/:skillName`)

**List view** (`/skills`):
- Sidebar: grouped skill list (categories derived from metadata.hermes.tags)
  - Groups: workshop-core (triage, requirements, planner, coder, reviewer, merge), reviewers (9), tools (brain-ingest, brain-query, etc.)
- Each list item: skill name, version badge, description excerpt
- Click → navigate to `/skills/:skillName`
- Search input to filter list

**Editor view** (`/skills/:skillName`):
- Top bar: skill name, version, "Unsaved" badge, Save, Discard, Dry Run buttons
- Left panel (280px): rendered SKILL.md frontmatter viewer (name, version, tags, description) — not editable as freeform, driven from YAML parse
- Center: Monaco editor, full-height, markdown language mode
- Right panel (360px, toggle): Output Schema viewer — parsed from the `## Output Schema` section fenced JSON block, rendered as a JSON schema tree
  - **Breaking change warning**: if the user modifies any field in the Output Schema section, a yellow alert fires: "Modifying the Output Schema may break the pipeline stage that consumes this skill's output. Verify all callers."
- Bottom panel (collapsible, 200px): Dry-run output — clicking "Dry Run" calls `POST /api/skills/:skillName/dry-run` and streams the result into this panel

**Git history panel** (slide-out sheet):
- "History" button in top bar opens `Sheet` component
- List of git commits touching this file (last 20)
- Each entry: hash, date, message, "Rollback to this" button
- `POST /api/skills/:skillName/rollback` with commit hash

**shadcn**: `ResizablePanelGroup`, `Sheet`, `Alert`, `Badge`, `Button`, `Tabs`, `ScrollArea`

**Backend**:
- `GET /api/skills` → `{ skills: SkillMeta[] }` (name, version, tags, description, path)
- `GET /api/skills/:name` → `{ meta, content: string }` (raw SKILL.md text)
- `PUT /api/skills/:name` → save content
- `POST /api/skills/:name/dry-run` → SSE stream of dry-run output
- `GET /api/skills/:name/history` → git log entries
- `POST /api/skills/:name/rollback` → `{ commit: string }`

---

### 3.8 Cost Analytics (`/cost`)

**Layout**: date range picker at top, then three sections.

**Section A — Summary cards** (row of 4):
- Today's spend / daily hard limit ($20) with progress bar
- This month's spend
- Per-task average
- Most expensive model alias

**Section B — Per-Build Table**:
- Columns: Task ID | Goal | Repo | Date | Stage Costs (triage, requirements, planner, coder, reviewer, total) | Status
- Expandable row: per-wave cost breakdown (role → tokens_used, cost_cents)

**Section C — Trend Charts**:
- Daily spend bar chart (last 30 days)
- Per-model-alias pie chart (current month)
- Per-role spend bar chart vs monthly cap (progress bars)

**shadcn + charting**: shadcn `Card`, `Table`, plus `recharts` (Recharts is the standard shadcn chart companion — BarChart, PieChart, AreaChart)

**Backend**:
- `GET /api/cost/summary?from=&to=` → summary stats
- `GET /api/cost/tasks?from=&to=` → per-task breakdown
- `GET /api/cost/trends?from=&to=` → daily + model + role aggregates
- `GET /api/cost/roles` → MTD per-role spend (shared with Config — Reviewers)

---

### 3.9 Health Dashboard (`/health`)

**Layout**: Grid of status cards + recent error log.

**Cards**:
- Hermes service: running / stopped (with uptime)
- LiteLLM proxy: running / stopped + version
- Each model alias: reachability (green/yellow/red) + last latency
- VPS disk: used / total with progress bar
- Task queue depth (count of running tasks)
- Pending HITL count (links to /hitl)
- Brain connectivity (HTTP ping to Brain endpoint)

**Recent Errors panel** (bottom):
- Last 20 error entries from progress_log.jsonl across all tasks
- Columns: timestamp, task_id, event, excerpt

**Backend**:
- `GET /api/health` → `{ services: ServiceStatus[], disk: DiskStats, queue_depth: int, hitl_count: int }`
- `GET /api/health/models` → per-alias reachability map
- `GET /api/health/errors` → recent error log

**Polling**: `refetchInterval: 15000`

---

### 3.10 Repo Registry (`/repos`)

**Purpose**: Manage the repo registry (`workshop-repos.json`).

**Table**: Repo Full Name | Default Branch | Active toggle | Last Used | GitHub Link | Actions (remove)
**Add repo form**: text input + "Add" button → `POST /api/repos`
Validation: calls GitHub API to verify write permissions before registering.

**Backend**:
- `GET /api/repos`
- `POST /api/repos` → `{ repo: string }`
- `PUT /api/repos/:fullName` → toggle active
- `DELETE /api/repos/:fullName`

---

### 3.11 Build Launcher (`/launch`)

**Purpose**: Trigger new `/build` or `/fix` tasks from the dashboard.

**Form**:
- Repo selector (dropdown from registry active repos)
- Task description (textarea, with char count)
- Mode radio: Build / Fix
- Optional: scope instruction (collapsible advanced)
- Enable brainstorm stage toggle
- "Launch" button → `POST /api/build` or `POST /api/fix`
- On success: redirect to `/tasks/:newTaskId`

---

## 4. State Management Architecture

### Client-side data fetching

**TanStack Query v5** for all REST:
- `queryClient` with default `staleTime: 10_000`, `refetchOnWindowFocus: true`
- Per-page refetch intervals defined at the query level (board: 5s, HITL: 3s, health: 15s, task detail: 8s)
- Mutations (`useMutation`) for all POST/PUT/DELETE actions
- Optimistic updates on HITL resolution (mark card as resolving immediately)

**No global state store** (Zustand/Redux) is needed for v1. The only shared UI state needed:
- Auth token (context + localStorage)
- Toast queue (shadcn `Toaster`)
- Pending config changes flag (per-page local state)

### SSE (Live Logs and Dry-run)

```
src/lib/useSSE.ts   — generic hook wrapping native EventSource
```

Pattern:
```ts
function useSSELog(taskId: string, enabled: boolean) {
  const [lines, setLines] = useState<LogLine[]>([])
  useEffect(() => {
    if (!enabled) return
    const es = new EventSource(`/api/tasks/${taskId}/logs/stream`, { withCredentials: true })
    es.onmessage = (e) => setLines(prev => [...prev.slice(-2000), JSON.parse(e.data)])
    es.onerror = () => es.close()
    return () => es.close()
  }, [taskId, enabled])
  return lines
}
```

Backpressure: cap the lines buffer at 2000 entries in the hook (`.slice(-2000)`). The backend should emit at most one event per progress_log.jsonl entry. For the virtualized list renderer, use `@tanstack/react-virtual` (TanStack Virtual) — only DOM nodes for visible rows are rendered.

### Routing

**TanStack Router v1** (file-based, type-safe):
- Route tree mirrors the URL map
- Auth loader guard on every protected route: reads token from localStorage, redirects to `/login` if absent
- `defer` for expensive data on Task Detail (non-blocking pipeline graph)

### Auth

Single-user. JWT issued by FastAPI `/auth/login` (username + password). Stored in localStorage. Attached to all requests via TanStack Query's `defaultOptions.queries.queryFn` wrapper that injects `Authorization: Bearer <token>` header. 401 responses trigger a global error boundary that redirects to `/login`.

---

## 5. Component + Folder Structure

```
dashboard/                           # Vite project root
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
│
├── src/
│   ├── main.tsx                     # mount + QueryClientProvider + RouterProvider
│   ├── router.ts                    # TanStack Router route tree
│   ├── auth.ts                      # token storage + useAuth hook
│   │
│   ├── lib/
│   │   ├── api.ts                   # typed fetch wrapper (base URL, auth header injection, error normalization)
│   │   ├── useSSE.ts                # generic SSE hook
│   │   ├── queryClient.ts           # TanStack Query client + default options
│   │   └── utils.ts                 # cn(), formatDuration(), formatCents(), truncate()
│   │
│   ├── types/
│   │   ├── task.ts                  # TaskSummary, TaskDetail, StageOutput, HITLPayload types (mirrors Python types)
│   │   ├── config.ts                # ModelAlias, ReviewerEntry, StagePolicy, CronJob
│   │   ├── skill.ts                 # SkillMeta, SkillContent
│   │   └── cost.ts                  # CostSummary, TaskCost, TrendData
│   │
│   ├── components/
│   │   ├── ui/                      # shadcn-generated components (do not hand-edit)
│   │   │   └── ...
│   │   │
│   │   ├── layout/
│   │   │   ├── AppShell.tsx         # sidebar nav + header wrapper
│   │   │   ├── Sidebar.tsx          # nav links with active state + HITL badge count
│   │   │   └── PageHeader.tsx       # page title + breadcrumb
│   │   │
│   │   ├── task/
│   │   │   ├── TaskCard.tsx         # Kanban card (status badge, step progress, cost, click)
│   │   │   ├── PipelineGraph.tsx    # vertical stage node list (SVG)
│   │   │   ├── StageOutputPane.tsx  # tab router for per-stage outputs
│   │   │   ├── PlanViewer.tsx       # Plan + PlanStep cards
│   │   │   ├── DiffViewer.tsx       # FileChange list + unified diff renderer
│   │   │   ├── ReviewWaveTable.tsx  # WaveReport rows + FindingRow expand
│   │   │   └── LogStream.tsx        # SSE log viewer with virtual list
│   │   │
│   │   ├── hitl/
│   │   │   ├── HITLCard.tsx         # dispatch by hitl_type
│   │   │   ├── ApprovalCard.tsx
│   │   │   ├── ClarificationCard.tsx
│   │   │   ├── StepRecoveryCard.tsx
│   │   │   ├── ReviewRecoveryCard.tsx
│   │   │   ├── TimeoutRecoveryCard.tsx
│   │   │   └── BrainstormCard.tsx
│   │   │
│   │   ├── config/
│   │   │   ├── AgentAliasTable.tsx  # agent→alias matrix (Section 3.4)
│   │   │   ├── AliasDefTable.tsx    # alias definitions + reachability
│   │   │   ├── ReviewerTable.tsx    # roster editor
│   │   │   ├── PolicyTable.tsx      # stage policies
│   │   │   ├── CronTable.tsx        # cron jobs
│   │   │   └── GatewayPanel.tsx
│   │   │
│   │   ├── skill/
│   │   │   ├── SkillList.tsx        # grouped sidebar list
│   │   │   ├── SkillEditor.tsx      # Monaco + panels
│   │   │   ├── OutputSchemaViewer.tsx
│   │   │   ├── FrontmatterPanel.tsx
│   │   │   └── GitHistorySheet.tsx
│   │   │
│   │   ├── cost/
│   │   │   ├── SummaryCards.tsx
│   │   │   ├── CostTable.tsx
│   │   │   └── TrendCharts.tsx
│   │   │
│   │   ├── health/
│   │   │   ├── ServiceCard.tsx
│   │   │   ├── ModelReachabilityGrid.tsx
│   │   │   └── ErrorLogPanel.tsx
│   │   │
│   │   └── shared/
│   │       ├── StatusBadge.tsx      # maps status string → colored Badge
│   │       ├── SeverityBadge.tsx    # Critical/Important/Minor → red/yellow/blue Badge
│   │       ├── CostPill.tsx         # formatted cents → "$0.042" pill
│   │       ├── StageLabel.tsx       # stage name → icon + label
│   │       └── EmptyState.tsx       # reusable empty/error state
│   │
│   ├── pages/
│   │   ├── LoginPage.tsx
│   │   ├── BoardPage.tsx
│   │   ├── TaskDetailPage.tsx
│   │   ├── HITLQueuePage.tsx
│   │   ├── ModelsConfigPage.tsx
│   │   ├── ReviewersConfigPage.tsx
│   │   ├── PoliciesConfigPage.tsx
│   │   ├── SkillsPage.tsx
│   │   ├── SkillEditorPage.tsx
│   │   ├── CostPage.tsx
│   │   ├── HealthPage.tsx
│   │   ├── ReposPage.tsx
│   │   └── LaunchPage.tsx
│   │
│   └── hooks/
│       ├── useTasks.ts              # TanStack Query wrappers for task endpoints
│       ├── useHITL.ts               # HITL queue query + mutation
│       ├── useConfig.ts             # config queries + mutations
│       ├── useSkills.ts             # skill queries + mutations
│       ├── useCost.ts               # cost queries
│       └── useHealth.ts             # health queries
```

---

## 6. Per-Page API Contract Summary

| Page | Method | Endpoint | Notes |
|------|--------|----------|-------|
| Board | GET | `/api/tasks` | ?status=active&limit=100 |
| Task Detail | GET | `/api/tasks/:id` | full state.json + enriched |
| Task Detail | GET | `/api/tasks/:id/logs/stream` | SSE |
| Task Detail | POST | `/api/tasks/:id/hitl` | `{decision, free_text?}` |
| HITL Queue | GET | `/api/hitl` | all pending |
| Models Config | GET | `/api/config/models` | |
| Models Config | PUT | `/api/config/models/aliases` | |
| Models Config | POST | `/api/config/litellm/reload` | |
| Reviewers | GET | `/api/config/reviewers` | |
| Reviewers | PUT | `/api/config/reviewers` | full roster |
| Policies | GET | `/api/config/policies` | |
| Policies | PUT | `/api/config/policies/stages` | |
| Cron | GET | `/api/cron` | |
| Cron | PUT | `/api/cron/:job` | |
| Cron | POST | `/api/cron/:job/trigger` | |
| Skills List | GET | `/api/skills` | |
| Skill Editor | GET | `/api/skills/:name` | |
| Skill Editor | PUT | `/api/skills/:name` | |
| Skill Dry-run | POST | `/api/skills/:name/dry-run` | SSE |
| Skill History | GET | `/api/skills/:name/history` | git log |
| Skill Rollback | POST | `/api/skills/:name/rollback` | `{commit}` |
| Cost | GET | `/api/cost/summary` | ?from=&to= |
| Cost | GET | `/api/cost/tasks` | ?from=&to= |
| Cost | GET | `/api/cost/trends` | |
| Cost | GET | `/api/cost/roles` | MTD per-role |
| Health | GET | `/api/health` | |
| Health | GET | `/api/health/models` | reachability |
| Health | GET | `/api/health/errors` | |
| Repos | GET | `/api/repos` | |
| Repos | POST | `/api/repos` | |
| Repos | PUT | `/api/repos/:fullName` | |
| Repos | DELETE | `/api/repos/:fullName` | |
| Launch | POST | `/api/build` | |
| Launch | POST | `/api/fix` | |
| Auth | POST | `/auth/login` | returns JWT |

---

## 7. The Three Trickiest UI Pieces

### 7.1 Live Pipeline Graph with Accurate State

**Problem**: A task's active stage is tracked in `next_stage`, but stages can be retried (`attempts`). The graph must show: which stages completed successfully, which failed and retried, which is currently running, and which are pending — without a full graph library dependency.

**Solution**:
- Do NOT reach for React Flow or Dagre. The pipeline is always a linear sequence of 7 stages in a fixed order (`_STAGE_INDEX`). Build a simple `PipelineGraph.tsx` with a vertical flexbox of `StageNode` components.
- Each `StageNode` receives: `{ stage, status, attemptCount, durationMs, isCurrent }`
- Status is derived in a selector function `deriveStageStatus(taskState, stageName)`:
  - `state.stages[stageName]` exists + has result with no blocking issues → `"success"`
  - `state.stages[stageName]` exists + has review failure → `"failed_retry"` if attempt < max, else `"failed"`
  - `state.next_stage === stageName` AND `state.status === "running"` → `"running"`
  - `state.next_stage === stageName` AND `state.status !== "running"` → `"paused_hitl"`
  - not yet reached → `"pending"`
- The `isCurrent` node gets a pulsing ring (CSS animation `animate-pulse`). The coder node additionally shows a `current_step / total_steps` mini-progress bar.
- Connecting lines between nodes are a simple 2px wide div with border-left.
- No layout algorithm needed. Total component is ~80 lines.

**Risk**: `state.stages` shape varies per stage (triage result is different from diff/wave_report). The `StageOutputPane` must handle missing/partial stage data gracefully (show a "Stage in progress…" placeholder when the stage key exists but has no final result).

### 7.2 SSE Log Viewer with Backpressure

**Problem**: `progress_log.jsonl` can grow to thousands of lines for a long coder run. SSE pushes every event. A naive `useState([...prev, newLine])` crashes the browser tab.

**Solution**:
1. The `useSSE.ts` hook caps the in-memory buffer at 2000 lines (ring-buffer: `setLines(prev => [...prev.slice(-1999), newLine])`).
2. The `LogStream.tsx` component uses `@tanstack/react-virtual` for the list — only ~30 DOM nodes rendered regardless of buffer size.
3. Auto-scroll: a `useRef` tracks whether the user has manually scrolled up. When at-the-bottom, scroll the virtualizer's scroll container to `totalSize` on each new event. When user scrolls up, set `userScrolled = true` and stop auto-scrolling. Show a "Jump to bottom" button in that state.
4. Initial hydration: `GET /api/tasks/:id/logs` (non-streaming, returns last 500 lines as JSON array) populates the buffer on mount before the SSE connection opens. This prevents a blank log viewer while SSE handshake happens.
5. SSE error handling: on `EventSource.onerror`, show a yellow reconnecting banner. Implement exponential backoff (1s, 2s, 4s, max 30s) before reopening the EventSource.
6. The backend should NOT stream raw shell output lines over SSE — it should stream `progress_log.jsonl` events only (structured JSON). Raw aider output should be accessible via a separate `GET /api/tasks/:id/output` endpoint that returns the output_tail field.

### 7.3 Agent→Model Alias Matrix Editor

**Problem**: 17 agents × ~10 aliases = a table where each cell must be an interactive Select dropdown, with dirty-state tracking, save/discard, and a "pending restart" warning after save.

**Solution**:
1. Load the matrix into local `useState<Record<string, string>>` (agentName → currentAlias).
2. On mount, set `originalState` ref equal to the loaded values.
3. `isDirty = JSON.stringify(state) !== JSON.stringify(originalState.current)` — show the orange "Unsaved" badge in the header when true.
4. Each `Select` in the table is controlled: `value={state[agentName]}` + `onValueChange={(v) => setState(prev => ({...prev, [agentName]: v}))}`.
5. "Save Changes" → `PUT /api/config/models/aliases` with the full map → on success, set `originalState.current = state` and show "Pending LiteLLM restart" alert.
6. "Reload LiteLLM" → `POST /api/config/litellm/reload` → on success, clear the pending-restart alert.
7. "Discard" → `setState(originalState.current)`.
8. Prevent navigation away with dirty state: TanStack Router's `beforeLoad` guard checks `isDirty` and shows a shadcn `AlertDialog` "Unsaved changes — leave anyway?".
9. The `always-on` roles (`correctness`, `security`) in the reviewer table: the `isolation` toggle's `disabled` prop is `entry.role === "correctness" || entry.role === "security"`. Show a `Tooltip` on hover: "Always-on roles cannot be set to diff-gated."

---

## 8. Risks and Dependencies

### Risks

**R1 — Backend API contract not finalized**: This plan specifies the endpoints the frontend needs. The backend agent must implement them exactly as specified or the frontend breaks. The `TaskDetail` response shape is the most complex contract — it must serialize `state.stages[*]` with typed outputs per stage, not raw JSON blobs.

**R2 — SSE connection pooling on VPS**: Each open Task Detail page holds a persistent SSE connection. With multiple browser tabs open, this can exhaust file descriptors on the VPS. The backend should implement SSE with an async generator (FastAPI `StreamingResponse`) and enforce a maximum of N concurrent SSE connections per task_id (fail-fast with 429 if exceeded). The frontend should close the SSE when the component unmounts (the `return () => es.close()` cleanup).

**R3 — Monaco editor bundle size**: Monaco adds ~2MB to the JS bundle. Mitigate with Vite's `manualChunks` to split Monaco into its own chunk: `{ monaco: ['monaco-editor'] }`. Use `@monaco-editor/react` (lazy-loaded). The skill editor page should be code-split so Monaco only loads when navigating to `/skills/*`.

**R4 — state.json schema evolves**: The frontend types in `src/types/task.ts` must track `state.py::new_task_state()`. If the backend adds new fields or HITL types, untyped `hitl_type` values will fall through to an unrendered state. The `HITLCard.tsx` dispatcher must have an explicit `default` case that renders a raw JSON fallback view rather than silently showing nothing.

**R5 — Git operations for skill rollback**: The `POST /api/skills/:name/rollback` endpoint requires git reset on the VPS skills directory. This is a destructive write operation. The backend must validate the commit hash against the skill file's git history (not allow arbitrary commits) and require re-authentication or at minimum a confirmation token. Surface this risk to the backend agent.

**R6 — Auth on SSE**: Native `EventSource` does not support custom request headers, so JWT cannot be passed as `Authorization: Bearer`. Options: (a) pass token as a query param `?token=<jwt>` (acceptable for Tailscale-only access), (b) use an HttpOnly cookie set on login (preferred). Coordinate with the backend agent on auth strategy for SSE endpoints before implementation.

### Dependencies

- Backend agent must implement all `/api/*` endpoints listed in Section 6
- Backend must expose SSE for `/api/tasks/:id/logs/stream` as newline-delimited `data: <json>\n\n` events
- Backend must return `hitl_type` in every `approval_payload` (currently present in workshop_build.py payloads — verify this is included in the API response)
- `@monaco-editor/react` — Monaco React wrapper
- `@tanstack/react-virtual` — virtualized log list
- `recharts` — chart library (standard shadcn companion)
- `@tanstack/react-router` — typed file-based routing
- `@tanstack/react-query` v5 — data fetching
- `tailwindcss` + `shadcn/ui` — styling baseline (already decided)

