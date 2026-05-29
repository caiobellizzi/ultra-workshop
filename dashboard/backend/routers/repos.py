"""Repo registry endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from dashboard.backend.config import settings
from dashboard.backend.deps import require_auth
from dashboard.backend.models.api_models import AddRepoRequest, RepoEntry

router = APIRouter(prefix="/api/repos", tags=["repos"])


def _registry_path():
    from pathlib import Path
    return Path(settings.repo_registry_path)


@router.get("", response_model=list[RepoEntry])
def list_repos(_auth=Depends(require_auth)):
    try:
        from workshop.repo_registry import load_registry
        data = load_registry(_registry_path())
        return [RepoEntry(**r) for r in data.get("repos", [])]
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
        return RepoEntry(**result)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/{name}", status_code=204)
def delete_repo(name: str, _auth=Depends(require_auth)):
    try:
        from workshop.repo_registry import deactivate_repo
        deactivate_repo(name, _registry_path())
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))
