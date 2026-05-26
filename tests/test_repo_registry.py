from __future__ import annotations

import json

import pytest

from workshop import repo_registry as registry


def test_canonicalize_repo_adds_default_owner() -> None:
    assert registry.canonicalize_repo("my-app") == "caiobellizzi/my-app"


def test_canonicalize_repo_accepts_github_url() -> None:
    assert registry.canonicalize_repo("https://github.com/acme/widget.git") == "acme/widget"


def test_parse_issue_repo_extracts_repo_and_number() -> None:
    repo, number = registry.parse_issue_repo("https://github.com/acme/widget/issues/42")
    assert repo == "acme/widget"
    assert number == 42


def test_missing_registry_bootstrap_seeds_sandbox(tmp_path) -> None:
    path = tmp_path / "workshop-repos.json"
    data = registry.load_registry(path)

    assert data["repos"][0]["full_name"] == "caiobellizzi/test-workshop-sandbox"
    assert data["repos"][0]["active"] is True
    assert path.exists()


def test_validate_active_repo_rejects_unknown_repo(tmp_path) -> None:
    path = tmp_path / "workshop-repos.json"
    registry.load_registry(path)

    with pytest.raises(registry.UnknownRepoError, match="/repo add caiobellizzi/missing"):
        registry.validate_active_repo("missing", path)


def test_deactivate_repo_marks_inactive_without_deleting(tmp_path) -> None:
    path = tmp_path / "workshop-repos.json"
    registry.load_registry(path)

    entry = registry.deactivate_repo("test-workshop-sandbox", path)
    data = registry.load_registry(path)

    assert entry["active"] is False
    assert len(data["repos"]) == 1
    with pytest.raises(registry.InactiveRepoError):
        registry.validate_active_repo("test-workshop-sandbox", path)


def test_entry_from_gh_metadata_maps_permissions() -> None:
    entry = registry.entry_from_gh_metadata(
        {
            "nameWithOwner": "acme/widget",
            "defaultBranchRef": {"name": "trunk"},
            "visibility": "PRIVATE",
            "viewerPermission": "MAINTAIN",
        },
        source="add",
    )

    assert entry["full_name"] == "acme/widget"
    assert entry["default_branch"] == "trunk"
    assert entry["visibility"] == "private"
    assert entry["viewer_permission"] == "MAINTAIN"


def test_entry_from_gh_metadata_rejects_read_permission() -> None:
    with pytest.raises(registry.RepoPermissionError, match="insufficient"):
        registry.entry_from_gh_metadata(
            {
                "nameWithOwner": "acme/widget",
                "defaultBranchRef": {"name": "main"},
                "viewerPermission": "READ",
            },
            source="add",
        )


def test_upsert_reactivates_existing_repo(tmp_path) -> None:
    path = tmp_path / "workshop-repos.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "repos": [
                    {
                        "full_name": "acme/widget",
                        "active": False,
                        "default_branch": "main",
                        "visibility": "private",
                        "viewer_permission": "WRITE",
                        "source": "add",
                        "created_at": "2026-01-01T00:00:00+00:00",
                        "updated_at": "2026-01-01T00:00:00+00:00",
                        "last_used_at": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    entry = registry.upsert_repo(
        registry.entry_from_gh_metadata(
            {
                "nameWithOwner": "acme/widget",
                "defaultBranchRef": {"name": "main"},
                "visibility": "PRIVATE",
                "viewerPermission": "ADMIN",
            },
            source="add",
        ),
        path,
    )

    assert entry["active"] is True
    assert entry["viewer_permission"] == "ADMIN"


def test_mark_last_used_persists_timestamp(tmp_path) -> None:
    path = tmp_path / "workshop-repos.json"
    registry.load_registry(path)

    entry = registry.mark_last_used("test-workshop-sandbox", path)
    reloaded = registry.validate_active_repo("test-workshop-sandbox", path)

    assert entry["last_used_at"] is not None
    assert reloaded["last_used_at"] == entry["last_used_at"]


# --- Remote write routing (Brain-persisted registry) ---------------------------

import urllib.error
from unittest.mock import MagicMock, patch


class _FakeResp:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_remote_routing_puts_to_brain_when_targeting_real_path(tmp_path, monkeypatch):
    real = tmp_path / "workshop-repos.json"
    monkeypatch.setenv(registry.REGISTRY_ENV, str(real))
    monkeypatch.setenv(registry.REMOTE_ENV, "http://127.0.0.1:7000/workshop/repos")
    data = registry.empty_registry()

    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["body"] = req.data
        return _FakeResp()

    with patch.object(registry.urllib.request, "urlopen", side_effect=fake_urlopen):
        registry.atomic_write_registry(data)  # path=None -> resolves to real path

    assert captured["url"] == "http://127.0.0.1:7000/workshop/repos"
    assert captured["method"] == "PUT"
    assert json.loads(captured["body"]) == data
    assert not real.exists()  # nothing written locally


def test_remote_env_set_but_explicit_path_writes_locally(tmp_path, monkeypatch):
    real = tmp_path / "workshop-repos.json"
    other = tmp_path / "override.json"
    monkeypatch.setenv(registry.REGISTRY_ENV, str(real))
    monkeypatch.setenv(registry.REMOTE_ENV, "http://127.0.0.1:7000/workshop/repos")

    with patch.object(registry.urllib.request, "urlopen", side_effect=AssertionError("should not call remote")):
        registry.atomic_write_registry(registry.empty_registry(), other)

    assert other.exists()  # explicit path stays hermetic


def test_remote_failure_raises_repo_registry_error(tmp_path, monkeypatch):
    real = tmp_path / "workshop-repos.json"
    monkeypatch.setenv(registry.REGISTRY_ENV, str(real))
    monkeypatch.setenv(registry.REMOTE_ENV, "http://127.0.0.1:7000/workshop/repos")

    def boom(req, timeout=None):
        raise urllib.error.URLError("connection refused")

    with patch.object(registry.urllib.request, "urlopen", side_effect=boom):
        with pytest.raises(registry.RepoRegistryError):
            registry.atomic_write_registry(registry.empty_registry())


def test_upsert_repo_routes_through_remote(tmp_path, monkeypatch):
    real = tmp_path / "workshop-repos.json"
    # Seed locally WITH the sandbox so load_registry won't fire a bootstrap
    # write; only the upsert write should route remote.
    registry.atomic_write_registry({"version": 1, "repos": [registry.seed_entry()]}, real)
    monkeypatch.setenv(registry.REGISTRY_ENV, str(real))
    monkeypatch.setenv(registry.REMOTE_ENV, "http://127.0.0.1:7000/workshop/repos")

    entry = registry.entry_from_gh_metadata(
        {"nameWithOwner": "caiobellizzi/new-test", "viewerPermission": "ADMIN", "visibility": "public"},
        source="add",
    )
    calls = []
    with patch.object(registry.urllib.request, "urlopen", side_effect=lambda req, timeout=None: calls.append(req) or _FakeResp()):
        registry.upsert_repo(entry)

    assert len(calls) == 1
    body = json.loads(calls[0].data)
    assert any(r["full_name"] == "caiobellizzi/new-test" for r in body["repos"])


def test_mark_last_used_is_best_effort_on_remote_failure(tmp_path, monkeypatch):
    real = tmp_path / "workshop-repos.json"
    entry = registry.entry_from_gh_metadata(
        {"nameWithOwner": "caiobellizzi/new-test", "viewerPermission": "ADMIN", "visibility": "public"},
        source="add",
    )
    data = {"version": 1, "repos": [registry.seed_entry(), entry]}
    registry.atomic_write_registry(data, real)
    monkeypatch.setenv(registry.REGISTRY_ENV, str(real))
    monkeypatch.setenv(registry.REMOTE_ENV, "http://127.0.0.1:7000/workshop/repos")

    def boom(req, timeout=None):
        raise urllib.error.URLError("down")

    with patch.object(registry.urllib.request, "urlopen", side_effect=boom):
        # must not raise — last_used is best-effort
        result = registry.mark_last_used("caiobellizzi/new-test")
    assert result["last_used_at"] is not None
