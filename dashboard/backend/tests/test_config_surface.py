"""Tests for config-surface features (Workstream D): global policies + skill state."""
from __future__ import annotations

import pytest


@pytest.fixture()
def tmp_config(tmp_path, monkeypatch):
    from dashboard.backend import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "hermes_config_dir", str(tmp_path / "hermes-config"))
    monkeypatch.setattr(cfg_module.settings, "skills_root", str(tmp_path / "skills"))
    return tmp_path


# --- Global policies ---

def test_global_policies_default_then_roundtrip(tmp_config):
    from dashboard.backend.services import config_service as cs

    defaults = cs.get_global_policies()
    assert "quiet_hours" in defaults and "cost" in defaults

    cs.set_global_policies({"quiet_hours": {"enabled": False, "start_hour": 1, "end_hour": 2}})
    saved = cs.get_global_policies()
    assert saved["quiet_hours"]["enabled"] is False


def test_global_policies_rejects_non_object(tmp_config):
    from dashboard.backend.services import config_service as cs

    with pytest.raises(ValueError):
        cs.set_global_policies({"cost": 5})  # value must be an object


# --- Skill enabled sidecar ---

def test_skill_enabled_sidecar_roundtrip(tmp_config):
    from dashboard.backend.routers import skills as sk

    (tmp_config / "skills").mkdir(parents=True, exist_ok=True)
    assert sk._is_enabled("unset-skill") is True        # default enabled
    sk._set_skill_enabled("my-skill", False)
    assert sk._is_enabled("my-skill") is False
    sk._set_skill_enabled("my-skill", True)
    assert sk._is_enabled("my-skill") is True


# --- Skill frontmatter validation (import path) ---

def test_validate_frontmatter_accepts_valid(tmp_config):
    from dashboard.backend.routers import skills as sk

    sk._validate_frontmatter("foo", "---\nname: foo\ndescription: does foo\n---\n# body\n")


@pytest.mark.parametrize("content,reason", [
    ("no frontmatter here", "missing block"),
    ("---\ndescription: x\n---\n", "missing name"),
    ("---\nname: foo\n---\n", "missing description"),
    ("---\nname: foo\ndescription: x\ntools: [a]\n---\n", "forbidden key"),
    ("---\nname: bar\ndescription: x\n---\n", "name mismatch"),
])
def test_validate_frontmatter_rejects(tmp_config, content, reason):
    from fastapi import HTTPException
    from dashboard.backend.routers import skills as sk

    with pytest.raises(HTTPException):
        sk._validate_frontmatter("foo", content)
