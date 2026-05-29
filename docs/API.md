<!-- generated-by: gsd-doc-writer -->
# API Reference

The ultra-workshop dashboard exposes a REST API served by FastAPI on port **7010**. All routes are prefixed with `/api/*` except internal loopback endpoints under `/internal/*`.

## Authentication

All endpoints require a valid session cookie **except** `POST /api/auth/login` and the internal loopback endpoints.

| Mechanism | Detail |
|-----------|--------|
| Cookie name | `uws_dash_session` |
| Flags | `HttpOnly`, `SameSite=strict` |
| Signing | HMAC — key set via `UWS_DASH_COOKIE_SECRET` |

A missing or invalid cookie returns **401 Unauthorized**:

```json
{"detail": "Not authenticated"}
```

---

## Endpoints overview

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/login` | No | Authenticate and set session cookie |
| POST | `/api/auth/logout` | No | Clear session cookie |
| GET | `/api/auth/me` | Yes | Check current session validity |
| GET | `/api/tasks` | Yes | List all tasks |
| GET | `/api/tasks/{task_id}` | Yes | Get full task detail |
| GET | `/api/tasks/{task_id}/progress` | Yes | Get task progress log entries |
| POST | `/api/tasks` | Yes | Launch a new task (202) |
| POST | `/api/tasks/{task_id}/fix` | Yes | Trigger fix run for a task (202) |
| GET | `/api/cost/daily` | Yes | Daily cost totals |
| GET | `/api/cost/roles` | Yes | Per-role spend |
| GET | `/api/cost/models` | Yes | Per-model totals |
| GET | `/api/cost/task/{task_id}` | Yes | Per-task spend |
| GET | `/api/config/stage-policies` | Yes | Get current stage policy config |
| PUT | `/api/config/stage-policies` | Yes | Update stage policies |
| GET | `/api/config/models` | Yes | Get model alias mapping |
| PUT | `/api/config/models` | Yes | Update model aliases |
| GET | `/api/config/roster` | Yes | Get reviewer roster |
| PUT | `/api/config/roster` | Yes | Update reviewer roster |
| GET | `/api/config/cron` | Yes | Get cron job config |
| PUT | `/api/config/cron` | Yes | Update cron job config |
| GET | `/api/skills` | Yes | List all skills with metadata |
| GET | `/api/skills/{name}` | Yes | Get skill content and frontmatter |
| PUT | `/api/skills/{name}` | Yes | Update skill content |
| GET | `/api/skills/{name}/history` | Yes | Git log for a skill file |
| POST | `/api/skills/{name}/rollback` | Yes | Roll back skill to last backup |
| POST | `/api/skills/{name}/dry-run` | Yes | SSE dry-run validation stream |
| GET | `/api/hitl` | Yes | List pending HITL items |
| POST | `/api/hitl/{row_id}/resolve` | Yes | Resolve a HITL item (202) |
| POST | `/api/control/restart` | Yes | Restart uws-hermes.service |
| POST | `/api/control/reload-litellm` | Yes | Restart uws-litellm Docker container |
| GET | `/api/repos` | Yes | List registered repos |
| POST | `/api/repos` | Yes | Register a new repo (201) |
| DELETE | `/api/repos/{repo_name}` | Yes | Deactivate a repo (204) |
| GET | `/api/sse/tasks/{task_id}/events` | Yes | SSE stream — state + progress events |
| GET | `/api/sse/tasks/{task_id}/logs` | Yes | SSE stream — raw aider log lines |
| GET | `/api/health` | Yes | Service health check |
| POST | `/internal/spend-update` | No | LiteLLM spend log ingest (loopback only) |

---

## Auth — `/api/auth`

### POST /api/auth/login

Authenticate with the dashboard password. On success, sets the `uws_dash_session` cookie.

**Request body:**
```json
{"password": "s3cr3t"}
```

**Response `200 OK`:**
```json
{"ok": true, "detail": ""}
```

**Response `401 Unauthorized`:**
```json
{"detail": "Invalid password"}
```

---

### POST /api/auth/logout

Clears the session cookie. No request body required.

**Response `200 OK`:**
```json
{"ok": true}
```

---

### GET /api/auth/me

Returns `200` with `{"authenticated": true}` for a valid session. Returns `401` otherwise.

**Response `200 OK`:**
```json
{"authenticated": true}
```

---

## Tasks — `/api/tasks`

### GET /api/tasks

Returns all tasks as a summary list, newest first.

**Response `200 OK`:** `list[TaskSummary]`
```json
[
  {
    "task_id": "a1b2c3d4e5f60001",
    "status": "running",
    "goal": "Add dark mode to dashboard",
    "repo": "myorg/my-repo",
    "stage": "build",
    "created_at": "2026-05-29T18:00:00+00:00",
    "updated_at": "2026-05-29T18:05:00+00:00"
  }
]
```

> Note: `stage` maps to `next_stage` in the underlying state file.

---

### GET /api/tasks/{task_id}

Returns the full task state, including stage history, attempts, approval payloads, and clarifications.

**Response `200 OK`:** `TaskDetail`
```json
{
  "task_id": "a1b2c3d4e5f60001",
  "status": "needs_approval",
  "goal": "Add dark mode to dashboard",
  "repo": "myorg/my-repo",
  "next_stage": "review",
  "created_at": "2026-05-29T18:00:00+00:00",
  "updated_at": "2026-05-29T18:10:00+00:00",
  "stages": {},
  "attempts": {},
  "current_step": 3,
  "approval_payload": {},
  "timeout_payload": {},
  "clarifications": []
}
```

**Response `400`:** Invalid task ID format.  
**Response `404`:** Task not found.

---

### GET /api/tasks/{task_id}/progress

Returns raw entries from the task's `progress_log.jsonl` file, in order.

**Response `200 OK`:** `list[dict]`
```json
[
  {"ts": "2026-05-29T18:01:00Z", "stage": "build", "message": "Starting build..."},
  {"ts": "2026-05-29T18:03:00Z", "stage": "build", "message": "Build complete"}
]
```

---

### POST /api/tasks

Launch a new task. Returns `202 Accepted` immediately; the task runs asynchronously via `uws-hermes`.

**Request body:** `LaunchRequest`
```json
{
  "repo": "myorg/my-repo",
  "goal": "Add dark mode to dashboard",
  "brainstorm": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `repo` | string | Yes | `owner/repo` from the registered registry |
| `goal` | string | Yes | Natural-language task description |
| `brainstorm` | boolean | No | When `true`, runs brainstorm phase before building (default: `false`) |

**Response `202 Accepted`:** `LaunchResponse`
```json
{"task_id": "a1b2c3d4e5f60001"}
```

---

### POST /api/tasks/{task_id}/fix

Trigger a fix run for an existing task. Returns `202 Accepted`.

**Response `202 Accepted`:**
```json
{"ok": true, "task_id": "a1b2c3d4e5f60001"}
```

---

## Cost — `/api/cost`

All cost endpoints return aggregated spend data from `spend.sqlite`.

### GET /api/cost/daily

Returns daily cost totals (list of `DailyCost`).

```json
[
  {"date": "2026-05-29", "total_usd": 1.42}
]
```

### GET /api/cost/roles

Returns per-role monthly spend with cap utilization.

```json
[
  {
    "role": "builder",
    "monthly_cents": 142.0,
    "cap_cents": 5000,
    "pct": 2.84
  }
]
```

### GET /api/cost/models

Returns per-model totals.

```json
[
  {"model": "claude-sonnet-4-5", "total_usd": 0.85, "request_count": 47}
]
```

### GET /api/cost/task/{task_id}

Returns spend for a single task.

```json
{
  "task_id": "a1b2c3d4e5f60001",
  "total_usd": 0.23,
  "breakdown": [
    {"model": "claude-sonnet-4-5", "total_usd": 0.23, "tokens": 12000}
  ]
}
```

---

## Config — `/api/config`

### GET /api/config/stage-policies

Returns the parsed stage policy YAML as a nested object.

```json
{
  "stage_policies": {
    "build": {"timeout_minutes": 30, "max_attempts": 3}
  }
}
```

### PUT /api/config/stage-policies

**Request body:**
```json
{
  "stage_policies": {
    "build": {"timeout_minutes": 45, "max_attempts": 5}
  }
}
```

**Response `200 OK`:** `{"ok": true}`  
**Response `422`:** Validation error with detail string.

### GET /api/config/models

Returns the model alias mapping.

```json
{"model_aliases": {"fast": "claude-haiku-4-5", "strong": "claude-sonnet-4-5"}}
```

### PUT /api/config/models

**Request body:** `{"model_aliases": {"fast": "claude-haiku-4-5"}}`

### GET /api/config/roster

Returns the reviewer roster.

```json
{"reviewers": [{"name": "reviewer-1", "model": "claude-sonnet-4-5"}]}
```

### PUT /api/config/roster

**Request body:** `{"reviewers": [...]}`

### GET /api/config/cron

Returns cron job configuration.

```json
{"jobs": [{"schedule": "0 2 * * *", "task": "daily-sweep"}]}
```

### PUT /api/config/cron

**Request body:** `{"jobs": [...]}`

---

## Skills — `/api/skills`

Skill names must match `[a-z0-9_-]+`. Maximum skill size is 128,000 bytes.

### GET /api/skills

Returns all skills found under the configured `SKILLS_ROOT`.

**Response `200 OK`:** `list[SkillSummary]`
```json
[
  {
    "name": "code-review",
    "path": "/path/to/skills/code-review/SKILL.md",
    "size": 4096,
    "has_output_schema": true
  }
]
```

### GET /api/skills/{name}

Returns full skill content.

**Response `200 OK`:** `SkillDetail`
```json
{
  "name": "code-review",
  "content": "# Code Review Skill\n...",
  "path": "/path/to/skills/code-review/SKILL.md",
  "size": 4096,
  "has_output_schema": true
}
```

**Response `400`:** Invalid skill name.  
**Response `404`:** Skill not found.

### PUT /api/skills/{name}

Update skill content. Creates a `.bak` backup of the previous version before writing.

**Request body:**
```json
{"content": "# Updated skill content\n..."}
```

**Response `200 OK`:**
```json
{
  "ok": true,
  "output_schema_changed": false,
  "warning": null
}
```

If the presence of an `## Output Schema` block changed, `output_schema_changed` will be `true` and `warning` will contain an advisory message.

### GET /api/skills/{name}/history

Returns the last 20 git log entries for the skill file (if under version control).

```json
{"history": ["abc1234 Update code-review thresholds", "def5678 Initial skill"]}
```

### POST /api/skills/{name}/rollback

Restores the skill from its `.bak` backup file.

**Response `200 OK`:**
```json
{"ok": true, "restored_from": "/path/to/skills/code-review/SKILL.bak"}
```

**Response `404`:** No backup found.

### POST /api/skills/{name}/dry-run

SSE validation stream. Validates content without writing. Returns `text/event-stream`.

**Request body:**
```json
{"content": "# Skill content to validate...", "test_input": ""}
```

**SSE events emitted:**
```
data: [dry-run] Validating skill content...
data: [WARN] No Output Schema block detected
data: [dry-run] Syntax check passed
data: [dry-run] Done
```

---

## HITL — `/api/hitl`

Human-in-the-loop items are stored in a SQLite database and require human resolution before the task can continue.

### GET /api/hitl

Returns all pending HITL items.

**Response `200 OK`:** `list[HitlRow]`
```json
[
  {
    "id": 42,
    "session_id": "sess_abc123",
    "message_id": null,
    "task_description": "Approve deployment to production?",
    "created_at": "2026-05-29T18:00:00",
    "status": "pending",
    "telegram_chat_id": "123456789",
    "telegram_message_id": null
  }
]
```

### POST /api/hitl/{row_id}/resolve

Resolve a HITL item and unblock the waiting task. Returns `202 Accepted`.

**Request body:** `HitlResolveRequest`
```json
{
  "task_id": "a1b2c3d4e5f60001",
  "hitl_type": "approval",
  "choice": "approve"
}
```

---

## Control — `/api/control`

Both control endpoints are guarded: they return `409 Conflict` if tasks are in-flight, unless `force: true` is passed.

### POST /api/control/restart

Restarts `uws-hermes.service` via `sudo systemctl restart`.

**Request body:** `RestartRequest`
```json
{"force": false}
```

**Response `200 OK`:** `RestartResponse`
```json
{"ok": true, "detail": "uws-hermes.service restarted"}
```

**Response `409`:** Tasks are in-flight and `force` was not set.

### POST /api/control/reload-litellm

Restarts the `uws-litellm` Docker container via `sudo docker restart`.

**Request body:** `{"force": false}`

**Response `200 OK`:**
```json
{"ok": true, "detail": "uws-litellm container restarted"}
```

---

## Repos — `/api/repos`

The repo registry is backed by `workshop-repos.json`.

### GET /api/repos

Returns all registered repos.

**Response `200 OK`:** `list[RepoEntry]`
```json
[
  {
    "full_name": "myorg/my-repo",
    "active": true,
    "default_branch": "main",
    "visibility": "private",
    "viewer_permission": "ADMIN",
    "source": "dashboard",
    "created_at": "2026-05-01T00:00:00+00:00",
    "updated_at": "2026-05-29T00:00:00+00:00",
    "last_used_at": null,
    "test_command": "npm test"
  }
]
```

### POST /api/repos

Register a new repo. Returns `201 Created`.

**Request body:** `AddRepoRequest`
```json
{
  "full_name": "myorg/new-repo",
  "default_branch": "main",
  "test_command": "npm test"
}
```

**Response `201 Created`:** Full `RepoEntry` object.

### DELETE /api/repos/{repo_name}

Deactivates (soft-deletes) a repo entry. Returns `204 No Content`.

---

## SSE Streams — `/api/sse`

Both SSE endpoints require auth (session cookie) and return `Content-Type: text/event-stream`. Clients should reconnect on disconnect.

### GET /api/sse/tasks/{task_id}/events

Polls `state.json` and `progress_log.jsonl` every 2 seconds and emits two event types:

**`state` event** — emitted when `status` changes:
```
event: state
data: {"task_id": "a1b2c3d4e5f60001", "status": "running", "next_stage": "build", "updated_at": "2026-05-29T18:05:00Z"}
```

**`progress` event** — emitted for each new progress log entry:
```
event: progress
data: {"ts": "2026-05-29T18:05:01Z", "stage": "build", "message": "Step 1 complete"}
```

### GET /api/sse/tasks/{task_id}/logs

Tails the aider step log files for a task and emits raw log lines:

```
event: log
data: aider | Applying changes to src/components/Dashboard.tsx...
```

---

## Health — `/api/health`

### GET /api/health

Returns the operational status of all backend services. Requires auth.

**Response `200 OK`:** `HealthResponse`
```json
{
  "ok": true,
  "services": [
    {"name": "uws-hermes", "ok": true, "detail": "active"},
    {"name": "litellm", "ok": true, "detail": ""},
    {"name": "spend-db", "ok": true, "detail": "/var/lib/uws/spend.sqlite"}
  ],
  "queue_depth": 2,
  "disk_free_gb": 48.5
}
```

`ok` at the top level is `true` only if all service checks pass. `queue_depth` counts tasks currently in a live (non-terminal) status.

---

## Internal — `/internal` (loopback only)

These endpoints have **no authentication**. They are only reachable from `127.0.0.1` by design — the server must not expose port 7010 externally without a firewall rule blocking `/internal/*`.

### POST /internal/spend-update

Receives LiteLLM spend log batches (configured via `SPEND_LOGS_URL`). Accepts either a bare JSON array or a dict with a `logs`, `spend_logs`, or `data` key.

**Request body (array form):**
```json
[
  {
    "request_id": "req_abc",
    "model": "claude-sonnet-4-5",
    "total_tokens": 1200,
    "response_cost": 0.0036,
    "user": "a1b2c3d4e5f60001"
  }
]
```

**Response `200 OK`:**
```json
{"ok": true, "inserted": 1}
```

---

## Error responses

All error responses follow FastAPI's standard envelope:

```json
{"detail": "human-readable error message"}
```

| Status | Meaning |
|--------|---------|
| 400 | Invalid request (e.g., malformed task ID or skill name) |
| 401 | Missing or invalid session cookie |
| 404 | Resource not found |
| 409 | Conflict — tasks in-flight, use `force: true` to override |
| 422 | Validation error (Pydantic) or business rule violation |
| 500 | Internal server error |
