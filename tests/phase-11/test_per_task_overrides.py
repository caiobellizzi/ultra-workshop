from __future__ import annotations

"""
Tests for per-task override contract (Workstream B).

Covers:
  - _select_reviewers keeps the security+correctness floor when optional off
  - _load_skill_profile_guidance: default no-op, known profile returns text
  - new_task_state persists the new override fields
  - build_trigger.launch_build forwards each override to a CLI flag
"""

import importlib.util
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))


def _load_workshop_build():
    spec = importlib.util.spec_from_file_location(
        "workshop_build_under_test", _REPO_ROOT / "hermes-skills" / "workshop_build.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Reviewer toggle (decision 5) — security floor always preserved
# ---------------------------------------------------------------------------

def test_select_reviewers_keeps_floor_when_optional_off():
    wb = _load_workshop_build()
    roster = [
        {"role": "security", "file_patterns": []},
        {"role": "correctness", "file_patterns": []},
        {"role": "frontend", "file_patterns": [".tsx", ".css"]},
    ]
    selected = wb._select_reviewers(roster, ["app/main.tsx"], include_optional=False)
    roles = {r["role"] for r in selected}
    assert roles == {"security", "correctness"}  # optional dropped, floor kept


def test_select_reviewers_includes_optional_when_matched():
    wb = _load_workshop_build()
    roster = [
        {"role": "security", "file_patterns": []},
        {"role": "frontend", "file_patterns": [".tsx"]},
    ]
    selected = wb._select_reviewers(roster, ["app/main.tsx"], include_optional=True)
    assert {r["role"] for r in selected} == {"security", "frontend"}


def test_select_reviewers_optional_unmatched_excluded():
    wb = _load_workshop_build()
    roster = [
        {"role": "security", "file_patterns": []},
        {"role": "frontend", "file_patterns": [".tsx"]},
    ]
    selected = wb._select_reviewers(roster, ["README.md"], include_optional=True)
    assert {r["role"] for r in selected} == {"security"}


# ---------------------------------------------------------------------------
# Skill profile guidance (decision 3, Path A)
# ---------------------------------------------------------------------------

def test_skill_profile_default_is_noop():
    wb = _load_workshop_build()
    assert wb._load_skill_profile_guidance("default") == ""
    assert wb._load_skill_profile_guidance("") == ""


def test_skill_profile_known_returns_guidance():
    wb = _load_workshop_build()
    text = wb._load_skill_profile_guidance("frontend")
    assert text  # non-empty
    assert "accessible" in text.lower()


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def test_new_task_state_persists_overrides():
    from workshop.state import new_task_state

    state = new_task_state(
        "ws-abc123",
        goal="x",
        repo="o/r",
        branch="develop",
        model_alias="coder-fast",
        skill_profile="frontend",
        run_optional_reviewers=False,
        dry_run=True,
    )
    assert state["branch"] == "develop"
    assert state["model_alias"] == "coder-fast"
    assert state["skill_profile"] == "frontend"
    assert state["run_optional_reviewers"] is False
    assert state["dry_run"] is True


# ---------------------------------------------------------------------------
# build_trigger.launch_build → CLI flag plumbing
# ---------------------------------------------------------------------------

def test_launch_build_forwards_override_flags(monkeypatch):
    from dashboard.backend.services import build_trigger

    captured: dict = {}

    class _SyncThread:
        def __init__(self, target=None, daemon=None):
            self._target = target

        def start(self):
            self._target()

    def _fake_run(cmd, *a, **kw):
        captured["cmd"] = cmd
        class _R:  # noqa: N801
            returncode = 0
            stdout = ""
            stderr = ""
        return _R()

    monkeypatch.setattr(build_trigger.threading, "Thread", _SyncThread)
    monkeypatch.setattr(build_trigger.subprocess, "run", _fake_run)

    build_trigger.launch_build(
        task_id="t1", repo="o/r", goal="do it",
        brainstorm=True, branch="develop", model_alias="coder-fast",
        skill_profile="frontend", run_optional_reviewers=False, dry_run=True,
    )
    cmd = captured["cmd"]
    assert "--brainstorm" in cmd
    assert cmd[cmd.index("--branch") + 1] == "develop"
    assert cmd[cmd.index("--model-alias") + 1] == "coder-fast"
    assert cmd[cmd.index("--skill-profile") + 1] == "frontend"
    assert "--skip-optional-reviewers" in cmd
    assert "--dry-run" in cmd


def test_launch_build_defaults_omit_flags(monkeypatch):
    from dashboard.backend.services import build_trigger

    captured: dict = {}

    class _SyncThread:
        def __init__(self, target=None, daemon=None):
            self._target = target

        def start(self):
            self._target()

    def _fake_run(cmd, *a, **kw):
        captured["cmd"] = cmd
        class _R:
            returncode = 0
            stdout = ""
            stderr = ""
        return _R()

    monkeypatch.setattr(build_trigger.threading, "Thread", _SyncThread)
    monkeypatch.setattr(build_trigger.subprocess, "run", _fake_run)

    build_trigger.launch_build(task_id="t1", repo="o/r", goal="do it")
    cmd = captured["cmd"]
    for flag in ("--branch", "--model-alias", "--skill-profile",
                 "--skip-optional-reviewers", "--dry-run", "--brainstorm"):
        assert flag not in cmd
