# GitHub Repo Sync — Design Spec

**Date:** 2026-05-30  
**Status:** Approved  
**Scope:** Single-user account sync (`caiobellizzi`) into the workshop repo registry

---

## Problem

The Repos page only shows repos manually added one at a time. There is no way to bulk-import all repos owned by the GitHub user into the registry.

## Solution

A "Sync GitHub" button on the Repos page that calls a new backend endpoint. The endpoint fetches all repos owned by `caiobellizzi` via the GitHub API and bulk-adds any not already in the registry. Returns a count of imported vs skipped repos.

---

## Backend

### New endpoint

```
POST /api/repos/sync-github
```

**Auth:** requires session cookie (same as all other repo endpoints).

**Implementation** (`dashboard/backend/routers/repos.py`):

1. Read `GITHUB_PAT` from environment. If missing, return `500` with `"GITHUB_PAT not configured"`.
2. Paginate `GET https://api.github.com/user/repos?per_page=100&type=owner` until GitHub returns an empty page.
3. Filter to repos where `owner.login == "caiobellizzi"` (defensive guard against org repos).
4. Load the current registry. Collect the set of already-registered `full_name` values.
5. For each new repo, call `upsert_repo` with the mapped entry. If a single upsert fails, log and skip — do not abort the batch.
6. Return `{"imported": N, "skipped": M}`.

**No new dependencies** — uses stdlib `urllib.request` (consistent with `health.py`).

### Data mapping

| Registry field     | Source                        |
|--------------------|-------------------------------|
| `full_name`        | GitHub `full_name`            |
| `default_branch`   | GitHub `default_branch`       |
| `visibility`       | GitHub `visibility`           |
| `viewer_permission`| Hardcoded `"ADMIN"` (owned)   |
| `active`           | `True`                        |
| `source`           | `"github-sync"`               |
| `created_at`       | Current UTC timestamp         |
| `updated_at`       | Current UTC timestamp         |
| `last_used_at`     | `None`                        |

### Error handling

| Condition | Response |
|---|---|
| `GITHUB_PAT` env var absent | `500` — "GITHUB_PAT not configured" |
| GitHub API non-200 response | `502` — GitHub error message forwarded |
| Individual `upsert_repo` failure | Log, skip that repo, continue |
| Registry file missing/unwritable | `500` — propagated from `upsert_repo` |

---

## Frontend

**File:** `dashboard/frontend/src/pages/ReposPage.tsx`

- Add a "Sync GitHub" button next to the existing `+ Add` button.
- On click, POST to `/api/repos/sync-github`, show loading spinner on the button.
- On success: toast `"{N} repos imported, {M} already registered"` and invalidate `["repos"]` query.
- On error: toast with destructive variant showing the error detail.
- Button uses a `Github` icon (lucide-react) to make its purpose immediately clear.

---

## Constraints

- Scope is `caiobellizzi` user account only — no org support.
- Import is additive: existing registry entries are never modified or removed.
- No automated tests added (matching existing pattern for repos router).
