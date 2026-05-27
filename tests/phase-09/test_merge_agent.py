from __future__ import annotations

"""
Merge agent logic tests (implemented in 09-03).

Tests verify:
  - Same-file/same-line findings from multiple reviewers collapse to one entry
    with highest severity winning (dedup by (file, line)).
  - A Critical finding causes block_push=True in the merge result.
  - A Minor finding is routed to auto_fixed list (not block_push).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_WB_PATH = Path(__file__).parent.parent.parent / "hermes-skills" / "workshop_build.py"
_PROJECT_ROOT = Path(__file__).parent.parent.parent


def _load_wb_globals() -> dict:
    """Load the module-level namespace of workshop_build.py without calling main()."""
    project_root = str(_PROJECT_ROOT)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    source = _WB_PATH.read_text(encoding="utf-8")
    pre_main = source.split("\ndef main(")[0]
    ns: dict = {
        "__file__": str(_WB_PATH),
        "__name__": "workshop_build",
    }
    exec(compile(pre_main, str(_WB_PATH), "exec"), ns)  # noqa: S102
    return ns


def _make_finding(file: str, line: int, severity: str, problem: str = "test problem", required_fix: str = "test fix"):
    """Create a ReviewFinding for tests."""
    if str(_PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(_PROJECT_ROOT))
    from workshop.types import ReviewFinding
    return ReviewFinding(file=file, line=line, severity=severity, problem=problem, required_fix=required_fix)


def _make_wave_report(role: str, findings: list):
    """Create a WaveReport for tests."""
    if str(_PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(_PROJECT_ROOT))
    from workshop.types import WaveReport
    return WaveReport(role=role, passed=not any(f.severity == "Critical" for f in findings), findings=findings)


def test_dedup_same_file_line_collapses() -> None:
    """Two findings at same (file, line) collapse to one with highest severity."""
    ns = _load_wb_globals()
    _dedup_findings = ns["_dedup_findings"]

    f1 = _make_finding("app.py", 10, "Important", "problem A", "fix A")
    f2 = _make_finding("app.py", 10, "Critical", "problem B", "fix B")

    result = _dedup_findings([f1, f2])
    assert len(result) == 1, f"Expected 1 deduplicated finding, got {len(result)}"
    assert result[0].severity == "Critical", f"Expected highest severity 'Critical', got {result[0].severity}"


def test_critical_finding_sets_block_push() -> None:
    """A Critical finding in wave reports causes block_push=True."""
    ns = _load_wb_globals()
    _build_merge_report = ns["_build_merge_report"]

    critical = _make_finding("auth.py", 5, "Critical", "SQL injection", "Use parameterized query")
    wave_report = _make_wave_report("security", [critical])

    result = _build_merge_report([wave_report])
    assert result.block_push is True, f"Expected block_push=True for critical finding, got {result.block_push}"


def test_minor_finding_goes_to_auto_fixed() -> None:
    """A Minor finding is placed in auto_fixed, not in critical/important lists."""
    ns = _load_wb_globals()
    _build_merge_report = ns["_build_merge_report"]

    minor = _make_finding("style.py", 42, "Minor", "trailing whitespace", "remove trailing whitespace")
    wave_report = _make_wave_report("correctness", [minor])

    result = _build_merge_report([wave_report])
    assert result.block_push is False, f"Expected block_push=False for minor finding"
    assert len(result.auto_fixed) == 1, f"Expected 1 auto_fixed finding, got {len(result.auto_fixed)}"
    assert len(result.critical_findings) == 0
    assert len(result.important_findings) == 0
