# GitHub Repo Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Sync GitHub" button to the Repos page that bulk-imports all repos owned by `caiobellizzi` not yet in the workshop registry.

**Architecture:** New `POST /api/repos/sync-github` backend endpoint paginates the GitHub `/user/repos` API using `GITHUB_PAT`, upserts new repos into the registry, and returns `{imported, skipped}`. The frontend adds a button that calls the endpoint and shows a toast with the counts.

**Tech Stack:** Python 3 stdlib `urllib.request` (backend), React + TanStack Query + shadcn/ui (frontend)

---

## File Map

| Action | File |
|--------|------|
| Modify | `dashboard/backend/config.py` |
| Modify | `dashboard/backend/routers/repos.py` |
| Modify | `dashboard/frontend/src/lib/api.ts` |
| Modify | `dashboard/frontend/src/pages/ReposPage.tsx` |

---

## Task 1: Add `github_pat` setting to backend config

**Files:**
- Modify: `dashboard/backend/config.py`

- [ ] **Step 1: Add the setting**

In `dashboard/backend/config.py`, inside the `Settings` class, add after the `litellm_base_url` line:

```python
    # --- GitHub ---
    # Personal access token for GitHub API calls (read:repo scope required).
    github_pat: str = ""
```

The full block after the edit:

```python
    # --- LiteLLM proxy ---
    # Mirrors hermes-config/config.yaml base_url (without /v1 path).
    litellm_base_url: str = "http://127.0.0.1:4000"

    # --- GitHub ---
    # Personal access token for GitHub API calls (read:repo scope required).
    github_pat: str = ""
```

`pydantic-settings` will automatically read `UWS_DASH_GITHUB_PAT` from the environment.

- [ ] **Step 2: Commit**

```bash
git add dashboard/backend/config.py
git commit -m "feat(config): add github_pat setting for GitHub API access"
```

---

## Task 2: Add `POST /api/repos/sync-github` endpoint

**Files:**
- Modify: `dashboard/backend/routers/repos.py`

- [ ] **Step 1: Add the endpoint**

Append the following function at the end of `dashboard/backend/routers/repos.py` (after the `delete_repo` function):

```python
@router.post("/sync-github", response_model=dict)
def sync_github(_auth=Depends(require_auth)):
    """Fetch all repos owned by the configured GitHub user and add new ones to the registry."""
    import json as _json
    import urllib.error
    import urllib.request

    pat = settings.github_pat
    if not pat:
        raise HTTPException(status_code=500, detail="GITHUB_PAT not configured (set UWS_DASH_GITHUB_PAT)")

    # Paginate GitHub /user/repos?type=owner
    all_repos: list[dict] = []
    page = 1
    while True:
        url = f"https://api.github.com/user/repos?type=owner&per_page=100&page={page}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {pat}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                page_repos = _json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            raise HTTPException(status_code=502, detail=f"GitHub API error {exc.code}: {body}")

        if not page_repos:
            break
        all_repos.extend(page_repos)
        page += 1

    # Filter to repos owned by caiobellizzi (guard against org repos leaking through)
    owned = [r for r in all_repos if r.get("owner", {}).get("login", "").lower() == "caiobellizzi"]

    # Load current registry to find already-registered names
    from workshop.repo_registry import load_registry, upsert_repo

    registry_p = _registry_path()
    try:
        existing_data = load_registry(registry_p)
    except Exception:
        existing_data = {"repos": []}
    registered = {r["full_name"] for r in existing_data.get("repos", [])}

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    imported = 0
    skipped = 0
    for gh in owned:
        full_name = gh["full_name"]
        if full_name in registered:
            skipped += 1
            continue
        entry = {
            "full_name": full_name,
            "active": True,
            "default_branch": gh.get("default_branch", "main"),
            "visibility": gh.get("visibility", "unknown"),
            "viewer_permission": "ADMIN",
            "source": "github-sync",
            "created_at": now,
            "updated_at": now,
            "last_used_at": None,
        }
        try:
            upsert_repo(entry, registry_p)
            imported += 1
        except Exception as exc:
            # Log and skip — don't abort the whole batch
            import sys
            print(f"[sync-github] skipping {full_name}: {exc}", file=sys.stderr)
            skipped += 1

    return {"imported": imported, "skipped": skipped}
```

- [ ] **Step 2: Verify imports are satisfied**

The function uses only:
- `json`, `urllib.error`, `urllib.request` — stdlib, always available
- `workshop.repo_registry.load_registry`, `upsert_repo` — already used by other endpoints in this file
- `dashboard.backend.config.settings` — already imported at the top of the file

No new imports needed at the module level.

- [ ] **Step 3: Commit**

```bash
git add dashboard/backend/routers/repos.py
git commit -m "feat(repos): add POST /api/repos/sync-github endpoint"
```

---

## Task 3: Add `syncGithub` to the frontend API client

**Files:**
- Modify: `dashboard/frontend/src/lib/api.ts`

- [ ] **Step 1: Add the method**

In `dashboard/frontend/src/lib/api.ts`, find the `repos` export (around line 232). Add `syncGithub` after `remove`:

```typescript
export const repos = {
  list: () => request<{ repos: Repo[] }>("/api/repos"),
  add: (repo: string) =>
    request<{ ok: boolean }>("/api/repos", {
      method: "POST",
      body: JSON.stringify({ repo }),
    }),
  update: (fullName: string, data: Partial<Repo>) =>
    request<{ ok: boolean }>(`/api/repos/${encodeURIComponent(fullName)}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  remove: (fullName: string) =>
    request<void>(`/api/repos/${encodeURIComponent(fullName)}`, {
      method: "DELETE",
    }),
  syncGithub: () =>
    request<{ imported: number; skipped: number }>("/api/repos/sync-github", {
      method: "POST",
    }),
};
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/frontend/src/lib/api.ts
git commit -m "feat(api): add syncGithub method to repos API client"
```

---

## Task 4: Add "Sync GitHub" button to ReposPage

**Files:**
- Modify: `dashboard/frontend/src/pages/ReposPage.tsx`

- [ ] **Step 1: Add the sync mutation and button**

Replace the entire contents of `dashboard/frontend/src/pages/ReposPage.tsx` with:

```tsx
import { useState } from "react";
import { Loader2, Plus, Trash2, ExternalLink, Github } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { repos as reposApi } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

export function ReposPage() {
  const qc = useQueryClient();
  const [newRepo, setNewRepo] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["repos"],
    queryFn: () => reposApi.list(),
  });

  const addMutation = useMutation({
    mutationFn: (repo: string) => reposApi.add(repo),
    onSuccess: () => {
      setNewRepo("");
      void qc.invalidateQueries({ queryKey: ["repos"] });
      toast({ title: "Repo added" });
    },
    onError: (e) => toast({ variant: "destructive", title: "Failed", description: String(e) }),
  });

  const removeMutation = useMutation({
    mutationFn: (fullName: string) => reposApi.remove(fullName),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["repos"] }),
  });

  const syncMutation = useMutation({
    mutationFn: () => reposApi.syncGithub(),
    onSuccess: (result) => {
      void qc.invalidateQueries({ queryKey: ["repos"] });
      toast({
        title: "GitHub sync complete",
        description: `${result.imported} repos imported, ${result.skipped} already registered`,
      });
    },
    onError: (e) => toast({ variant: "destructive", title: "Sync failed", description: String(e) }),
  });

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="Repos" description="Workshop repo registry" />
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        <div className="flex gap-2 max-w-md">
          <Input
            placeholder="owner/repo"
            value={newRepo}
            onChange={(e) => setNewRepo(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addMutation.mutate(newRepo)}
          />
          <Button
            onClick={() => addMutation.mutate(newRepo)}
            disabled={!newRepo || addMutation.isPending}
          >
            {addMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Add
          </Button>
          <Button
            variant="outline"
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
          >
            {syncMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Github className="h-4 w-4" />
            )}
            Sync GitHub
          </Button>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <Card>
            <CardContent className="p-0">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="p-3 font-medium text-muted-foreground">Repo</th>
                    <th className="p-3 font-medium text-muted-foreground">Branch</th>
                    <th className="p-3 font-medium text-muted-foreground">Status</th>
                    <th className="p-3 font-medium text-muted-foreground">Last Used</th>
                    <th className="p-3" />
                  </tr>
                </thead>
                <tbody>
                  {data?.repos.map((repo) => (
                    <tr key={repo.full_name} className="border-b last:border-0">
                      <td className="p-3">
                        <a
                          href={`https://github.com/${repo.full_name}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1 text-primary hover:underline font-mono text-xs"
                        >
                          {repo.full_name}
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </td>
                      <td className="p-3 text-xs">{repo.default_branch}</td>
                      <td className="p-3">
                        <Badge variant={repo.active ? "success" : "secondary"}>
                          {repo.active ? "Active" : "Inactive"}
                        </Badge>
                      </td>
                      <td className="p-3 text-xs text-muted-foreground">
                        {repo.last_used ? new Date(repo.last_used).toLocaleDateString() : "Never"}
                      </td>
                      <td className="p-3">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 w-7 p-0"
                          onClick={() => removeMutation.mutate(repo.full_name)}
                        >
                          <Trash2 className="h-4 w-4 text-muted-foreground" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/frontend/src/pages/ReposPage.tsx
git commit -m "feat(repos-ui): add Sync GitHub button to repos page"
```

---

## Task 5: Deploy to VPS

- [ ] **Step 1: Copy changed backend files to VPS**

```bash
scp dashboard/backend/config.py uws:/opt/ultra-workshop/dashboard/backend/config.py
scp dashboard/backend/routers/repos.py uws:/opt/ultra-workshop/dashboard/backend/routers/repos.py
```

- [ ] **Step 2: Build and copy frontend**

```bash
cd dashboard/frontend && npm run build
scp -r dist/* uws:/opt/ultra-workshop/dashboard/frontend/dist/
```

- [ ] **Step 3: Set `UWS_DASH_GITHUB_PAT` on the VPS service**

SSH into the VPS and add the env var to the systemd service override:

```bash
ssh uws
sudo systemctl edit uws-hermes-dashboard
```

Add inside the `[Service]` block:

```ini
Environment="UWS_DASH_GITHUB_PAT=<your-github-pat>"
```

Then reload:

```bash
sudo systemctl daemon-reload
sudo systemctl restart uws-hermes-dashboard
sudo systemctl status uws-hermes-dashboard
```

Expected: `Active: active (running)`

- [ ] **Step 4: Smoke test**

Open `https://uws-dashboard.tail1a2bcb.ts.net/repos` in a browser, click "Sync GitHub", and verify the toast shows a count and the table populates.

- [ ] **Step 5: Final commit (if any files changed during deploy)**

```bash
git add -A
git commit -m "chore: deploy github repo sync to VPS"
```
