from __future__ import annotations

"""
Review-wave dispatch stubs (implemented in 09-03).

Tests verify:
  - Always-on reviewers (correctness, security) are always selected.
  - Stack reviewers (python) are gated on .py files in the diff.
  - Wave dispatch returns a list of WaveReport objects.

All skipped until 09-03 wires the wave dispatcher in workshop_build.py.
"""

import pytest


@pytest.mark.skip(reason="wave dispatch not yet implemented (09-03)")
def test_select_reviewers_always_on_included() -> None:
    """
    correctness-reviewer and security-reviewer must be in the selected set
    regardless of diff file types.
    """
    raise NotImplementedError("Implement after 09-03 wires wave dispatch")


@pytest.mark.skip(reason="wave dispatch not yet implemented (09-03)")
def test_select_reviewers_python_gated_on_py_files() -> None:
    """
    python-reviewer must be selected when the diff contains .py files,
    and must NOT be selected when the diff contains only .md files.
    """
    raise NotImplementedError("Implement after 09-03 wires wave dispatch")


@pytest.mark.skip(reason="wave dispatch not yet implemented (09-03)")
def test_wave_dispatch_returns_wave_reports() -> None:
    """
    The wave dispatcher must return a list where each entry contains
    at minimum: role, passed, findings, tokens_used, cost_cents.
    """
    raise NotImplementedError("Implement after 09-03 wires wave dispatch")
