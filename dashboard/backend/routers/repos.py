"""Repo registry endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from dashboard.backend.config import settings
from dashboard.backend.deps import require_auth
from dashboard.backend.models.api_models import AddRepoRequest, RepoEntry, RepoListResponse

router = APIRouter(prefix="/api/repos", tags=["repos"])


def _registry_path():
    from pathlib import Path
    return Path(settings.repo_registry_path)


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
