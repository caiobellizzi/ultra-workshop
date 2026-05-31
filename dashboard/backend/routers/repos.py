"""Repo registry endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from dashboard.backend.config import settings
from dashboard.backend.deps import require_auth
from dashboard.backend.models.api_models import AddRepoRequest, RepoEntry, RepoListResponse

router = APIRouter(prefix="/api/repos", tags=["repos"])


def _registry_path():
    from workshop.repo_registry import registry_path
    return registry_path()  # reads WORKSHOP_REPO_REGISTRY env var, same source as workshop_build.py


def _repo_entry_from_raw(r: dict[str, Any]) -> RepoEntry:
    """Construct RepoEntry from a raw registry dict, mapping last_used_at → last_used."""
    data = dict(r)
    if "last_used_at" in data and "last_used" not in data:
        data["last_used"] = data.pop("last_used_at")
    return RepoEntry(**{k: v for k, v in data.items() if k in RepoEntry.model_fields})


@router.get("", response_model=RepoListResponse)
def list_repos(_auth=Depends(require_auth)):
    try:
        from workshop.repo_registry import load_registry
        data = load_registry(_registry_path())
        repos = [_repo_entry_from_raw(r) for r in data.get("repos", [])]
        return RepoListResponse(repos=repos)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("", response_model=RepoEntry, status_code=201)
def add_repo(body: AddRepoRequest, _auth=Depends(require_auth)):
    from datetime import datetime, timezone
    from workshop.repo_registry import canonicalize_repo, upsert_repo

    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "full_name": canonicalize_repo(body.full_name),
        "active": True,
        "default_branch": body.default_branch,
        "visibility": "unknown",
        "viewer_permission": "UNKNOWN",
        "source": "dashboard",
        "created_at": now,
        "updated_at": now,
        "last_used_at": None,
        "test_command": body.test_command,
    }
    try:
        result = upsert_repo(entry, _registry_path())
        return _repo_entry_from_raw(result)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.put("/{name}", response_model=dict)
def update_repo(name: str, body: RepoEntry, _auth=Depends(require_auth)):
    """Patch a repo entry via upsert (merges into existing record)."""
    try:
        from workshop.repo_registry import canonicalize_repo, upsert_repo

        patch: dict[str, Any] = {
            k: v
            for k, v in body.model_dump(exclude_unset=True).items()
            if v is not None or k in ("last_used",)
        }
        # Ensure canonical name and remap last_used → last_used_at for the registry
        patch["full_name"] = canonicalize_repo(name)
        if "last_used" in patch:
            patch["last_used_at"] = patch.pop("last_used")
        upsert_repo(patch, _registry_path())
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/{name}", status_code=204)
def delete_repo(name: str, _auth=Depends(require_auth)):
    try:
        from workshop.repo_registry import deactivate_repo
        deactivate_repo(name, _registry_path())
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/sync-github", response_model=dict)
def sync_github(_auth=Depends(require_auth)):
    """Fetch all repos owned by the configured GitHub user and add new ones to the registry."""
    import json as _json
    import urllib.error
    import urllib.request

    pat = settings.github_pat
    if not pat:
        raise HTTPException(status_code=500, detail="GITHUB_PAT not configured (set UWS_DASH_GITHUB_PAT)")

    # Paginate GitHub /user/repos?type=owner (max 20 pages = 2,000 repos)
    all_repos: list[dict] = []
    page = 1
    max_pages = 20
    while page <= max_pages:
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
            import sys
            print(f"[sync-github] GitHub {exc.code}: {body}", file=sys.stderr)
            raise HTTPException(status_code=502, detail=f"GitHub API error {exc.code}")

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
            import sys
            print(f"[sync-github] skipping {full_name}: {exc}", file=sys.stderr)
            skipped += 1

    return {"imported": imported, "skipped": skipped}
