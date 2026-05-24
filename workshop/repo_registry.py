from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

DEFAULT_OWNER = "caiobellizzi"
DEFAULT_REPO = f"{DEFAULT_OWNER}/test-workshop-sandbox"
REGISTRY_ENV = "WORKSHOP_REPO_REGISTRY"
DEFAULT_REGISTRY_PATH = Path("/srv/second-brain/_system/workshop-repos.json")
ALLOWED_WRITE_PERMISSIONS = {"WRITE", "MAINTAIN", "ADMIN"}

_FULL_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class RepoRegistryError(ValueError):
    """Base class for repo registry validation failures."""


class UnknownRepoError(RepoRegistryError):
    """Raised when a repo is not present in the registry."""


class InactiveRepoError(RepoRegistryError):
    """Raised when a repo is present but disabled."""


class RepoPermissionError(RepoRegistryError):
    """Raised when GitHub metadata does not grant write-level access."""


def registry_path(path: str | Path | None = None) -> Path:
    if path is not None:
        return Path(path)
    return Path(os.environ.get(REGISTRY_ENV, DEFAULT_REGISTRY_PATH))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonicalize_repo(value: str, *, default_owner: str = DEFAULT_OWNER) -> str:
    """Return a normalized owner/name repository identifier."""
    repo = value.strip()
    if not repo:
        raise RepoRegistryError("repo is required")

    if repo.startswith("git@github.com:"):
        repo = repo.removeprefix("git@github.com:").removesuffix(".git")
    elif repo.startswith(("http://", "https://")):
        parsed = urlparse(repo)
        if parsed.netloc.lower() != "github.com":
            raise RepoRegistryError(f"unsupported GitHub host: {parsed.netloc}")
        repo = parsed.path.strip("/").removesuffix(".git")

    if "/" not in repo:
        repo = f"{default_owner}/{repo}"

    repo = repo.strip("/")
    if not _FULL_NAME_RE.match(repo):
        raise RepoRegistryError(f"invalid repo name: {value!r}")
    owner, name = repo.split("/", 1)
    return f"{owner}/{name}"


def repo_hint(repo: str) -> str:
    return f"Unknown or inactive repo: {repo}. Add it first with /repo add {repo}"


def parse_issue_repo(issue_url: str) -> tuple[str, int]:
    parsed = urlparse(issue_url.strip())
    if parsed.netloc.lower() != "github.com":
        raise RepoRegistryError("issue URL must be on github.com")
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 4 or parts[2] != "issues":
        raise RepoRegistryError("issue URL must look like https://github.com/<owner>/<repo>/issues/<number>")
    try:
        number = int(parts[3])
    except ValueError as exc:
        raise RepoRegistryError("issue URL has a non-numeric issue number") from exc
    return canonicalize_repo(f"{parts[0]}/{parts[1]}"), number


def empty_registry() -> dict[str, Any]:
    return {"version": 1, "repos": []}


def seed_entry(now: str | None = None) -> dict[str, Any]:
    ts = now or utc_now()
    return {
        "full_name": DEFAULT_REPO,
        "active": True,
        "default_branch": "main",
        "visibility": "unknown",
        "viewer_permission": "ADMIN",
        "source": "bootstrap",
        "created_at": ts,
        "updated_at": ts,
        "last_used_at": None,
    }


def normalize_registry(data: Any) -> dict[str, Any]:
    if isinstance(data, list):
        data = {"version": 1, "repos": data}
    if not isinstance(data, dict):
        raise RepoRegistryError("registry JSON must be an object")
    repos = data.get("repos")
    if not isinstance(repos, list):
        raise RepoRegistryError("registry JSON must contain a repos list")

    normalized = {"version": int(data.get("version", 1)), "repos": []}
    seen: set[str] = set()
    for raw in repos:
        if not isinstance(raw, dict):
            raise RepoRegistryError("registry entries must be objects")
        full_name = canonicalize_repo(str(raw.get("full_name", "")))
        if full_name in seen:
            continue
        seen.add(full_name)
        entry = dict(raw)
        entry["full_name"] = full_name
        entry["active"] = bool(entry.get("active", True))
        entry.setdefault("default_branch", "main")
        entry.setdefault("visibility", "unknown")
        entry.setdefault("viewer_permission", "UNKNOWN")
        entry.setdefault("source", "manual")
        entry.setdefault("created_at", utc_now())
        entry.setdefault("updated_at", entry["created_at"])
        entry.setdefault("last_used_at", None)
        normalized["repos"].append(entry)
    return normalized


def atomic_write_registry(data: dict[str, Any], path: str | Path | None = None) -> None:
    target = registry_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(target)


def load_registry(path: str | Path | None = None, *, bootstrap: bool = True) -> dict[str, Any]:
    target = registry_path(path)
    if not target.exists():
        data = empty_registry()
        if bootstrap:
            data["repos"].append(seed_entry())
            atomic_write_registry(data, target)
        return data

    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RepoRegistryError(f"registry JSON is invalid: {exc}") from exc

    data = normalize_registry(raw)
    if bootstrap and not any(r["full_name"] == DEFAULT_REPO for r in data["repos"]):
        data["repos"].append(seed_entry())
        atomic_write_registry(data, target)
    return data


def find_repo(data: dict[str, Any], repo: str) -> dict[str, Any] | None:
    full_name = canonicalize_repo(repo)
    for entry in data.get("repos", []):
        if entry.get("full_name") == full_name:
            return entry
    return None


def list_active_repos(path: str | Path | None = None) -> list[dict[str, Any]]:
    data = load_registry(path)
    return [entry for entry in data["repos"] if entry.get("active")]


def validate_active_repo(repo: str, path: str | Path | None = None) -> dict[str, Any]:
    data = load_registry(path)
    full_name = canonicalize_repo(repo)
    entry = find_repo(data, full_name)
    if entry is None:
        raise UnknownRepoError(repo_hint(full_name))
    if not entry.get("active"):
        raise InactiveRepoError(repo_hint(full_name))
    return entry


def mark_last_used(repo: str, path: str | Path | None = None) -> dict[str, Any]:
    target = registry_path(path)
    data = load_registry(target)
    full_name = canonicalize_repo(repo)
    entry = find_repo(data, full_name)
    if entry is None:
        raise UnknownRepoError(repo_hint(full_name))
    if not entry.get("active"):
        raise InactiveRepoError(repo_hint(full_name))
    entry["last_used_at"] = utc_now()
    entry["updated_at"] = entry["last_used_at"]
    atomic_write_registry(data, target)
    return entry


def require_write_permission(permission: str) -> str:
    normalized = permission.upper()
    if normalized not in ALLOWED_WRITE_PERMISSIONS:
        allowed = ", ".join(sorted(ALLOWED_WRITE_PERMISSIONS))
        raise RepoPermissionError(f"repo permission {permission!r} is insufficient; need one of {allowed}")
    return normalized


def entry_from_gh_metadata(payload: dict[str, Any], *, source: str) -> dict[str, Any]:
    full_name = canonicalize_repo(str(payload.get("nameWithOwner") or payload.get("fullName") or payload.get("full_name") or ""))
    permission = require_write_permission(str(payload.get("viewerPermission") or payload.get("viewer_permission") or ""))
    branch_ref = payload.get("defaultBranchRef") or payload.get("default_branch") or {}
    if isinstance(branch_ref, dict):
        default_branch = str(branch_ref.get("name") or "main")
    else:
        default_branch = str(branch_ref or "main")
    now = utc_now()
    return {
        "full_name": full_name,
        "active": True,
        "default_branch": default_branch,
        "visibility": str(payload.get("visibility") or "unknown").lower(),
        "viewer_permission": permission,
        "source": source,
        "created_at": now,
        "updated_at": now,
        "last_used_at": None,
    }


def upsert_repo(entry: dict[str, Any], path: str | Path | None = None) -> dict[str, Any]:
    target = registry_path(path)
    data = load_registry(target)
    full_name = canonicalize_repo(entry["full_name"])
    existing = find_repo(data, full_name)
    if existing is None:
        data["repos"].append(entry)
    else:
        created_at = existing.get("created_at")
        existing.update(entry)
        existing["created_at"] = created_at or entry.get("created_at") or utc_now()
        existing["updated_at"] = utc_now()
        existing["active"] = True
        entry = existing
    atomic_write_registry(data, target)
    return entry


def deactivate_repo(repo: str, path: str | Path | None = None) -> dict[str, Any]:
    target = registry_path(path)
    data = load_registry(target)
    full_name = canonicalize_repo(repo)
    entry = find_repo(data, full_name)
    if entry is None:
        raise UnknownRepoError(repo_hint(full_name))
    entry["active"] = False
    entry["updated_at"] = utc_now()
    atomic_write_registry(data, target)
    return entry
