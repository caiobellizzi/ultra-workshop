from __future__ import annotations

"""
Review-wave dispatch tests (implemented in 09-03).

Tests verify:
  - _STAGE_INDEX has brainstorm=0 and triage=1 after Phase 9 reindex.
  - Always-on reviewers (correctness, security) are always selected.
  - Stack reviewers (python) are gated on .py files in the diff.
  - wave_dispatch raises ValueError on empty roster.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Helper to load workshop_build module-level code without executing main()
_WB_PATH = Path(__file__).parent.parent.parent / "hermes-skills" / "workshop_build.py"
_PROJECT_ROOT = Path(__file__).parent.parent.parent


def _load_wb_globals() -> dict:
    """Load the module-level namespace of workshop_build.py without calling main()."""
    project_root = str(_PROJECT_ROOT)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    source = _WB_PATH.read_text(encoding="utf-8")
    # Only execute the code before def main() to avoid side effects
    pre_main = source.split("\ndef main(")[0]
    ns: dict = {
        "__file__": str(_WB_PATH),
        "__name__": "workshop_build",
    }
    exec(compile(pre_main, str(_WB_PATH), "exec"), ns)  # noqa: S102
    return ns


def test_stage_index_brainstorm_is_zero() -> None:
    """_STAGE_INDEX must have brainstorm at 0 and triage at 1 after Phase 9 reindex."""
    ns = _load_wb_globals()
    stage_index = ns["_STAGE_INDEX"]
    assert stage_index["brainstorm"] == 0, f"brainstorm index should be 0, got {stage_index['brainstorm']}"
    assert stage_index["triage"] == 1, f"triage index should be 1, got {stage_index['triage']}"


def test_stage_should_run_brainstorm_before_triage() -> None:
    """_stage_should_run returns True when next_stage is 'brainstorm' and checking 'brainstorm'."""
    ns = _load_wb_globals()
    _stage_should_run = ns["_stage_should_run"]
    assert _stage_should_run({"next_stage": "brainstorm"}, "brainstorm") is True


def test_stage_should_run_brainstorm_skipped_when_triage_next() -> None:
    """_stage_should_run returns False for brainstorm when next_stage is triage (already past)."""
    ns = _load_wb_globals()
    _stage_should_run = ns["_stage_should_run"]
    assert _stage_should_run({"next_stage": "triage"}, "brainstorm") is False


def test_select_reviewers_always_on_included() -> None:
    """correctness and security reviewers are always included regardless of diff files."""
    ns = _load_wb_globals()
    _select_reviewers = ns["_select_reviewers"]

    import yaml
    roster_path = _PROJECT_ROOT / "hermes-config" / "review-roster.yaml"
    roster_data = yaml.safe_load(roster_path.read_text())
    roster = roster_data["reviewers"]

    selected = _select_reviewers(roster, [".md"])
    roles = [r["role"] for r in selected]
    assert "correctness" in roles, f"correctness should always be in {roles}"
    assert "security" in roles, f"security should always be in {roles}"


def test_select_reviewers_python_gated_on_py_files() -> None:
    """python reviewer is selected for .py files but not for .md-only diffs."""
    ns = _load_wb_globals()
    _select_reviewers = ns["_select_reviewers"]

    import yaml
    roster_path = _PROJECT_ROOT / "hermes-config" / "review-roster.yaml"
    roster_data = yaml.safe_load(roster_path.read_text())
    roster = roster_data["reviewers"]

    with_py = _select_reviewers(roster, ["foo.py"])
    without_py = _select_reviewers(roster, ["foo.md"])

    assert "python" in [r["role"] for r in with_py], "python should be selected for .py files"
    assert "python" not in [r["role"] for r in without_py], "python should NOT be selected for .md-only files"


def test_wave_dispatch_raises_on_empty_roster() -> None:
    """wave_dispatch must raise ValueError when the roster is empty."""
    ns = _load_wb_globals()
    wave_dispatch = ns["wave_dispatch"]

    mock_diff = MagicMock()
    mock_diff.changes = []
    mock_plan = MagicMock()

    with pytest.raises(ValueError, match="[Rr]oster"):
        wave_dispatch(mock_diff, mock_plan, "ws-test01", [])
