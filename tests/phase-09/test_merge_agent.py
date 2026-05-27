from __future__ import annotations

"""
Merge agent logic stubs (implemented in 09-03).

Tests verify:
  - Same-file/same-line findings from multiple reviewers collapse to one entry
    with highest severity winning (dedup by (file, line)).
  - A Critical finding causes block_push=True in the merge result.
  - A Minor finding is routed to auto_fixed list (not block_push).

All skipped until 09-03 implements the merge agent.
"""

import pytest


@pytest.mark.skip(reason="merge agent not yet implemented (09-03)")
def test_dedup_same_file_line_collapses() -> None:
    """
    Two findings for (file='app.py', line=10) from different reviewers must
    collapse into one finding. The highest severity among the inputs wins.
    """
    raise NotImplementedError("Implement after 09-03 implements merge agent")


@pytest.mark.skip(reason="merge agent not yet implemented (09-03)")
def test_critical_finding_sets_block_push_true() -> None:
    """
    When any finding has severity='Critical', the merge output must include
    block_push=True.
    """
    raise NotImplementedError("Implement after 09-03 implements merge agent")


@pytest.mark.skip(reason="merge agent not yet implemented (09-03)")
def test_minor_finding_goes_to_auto_fixed() -> None:
    """
    A finding with severity='Minor' (e.g., lint/formatting) must appear in
    the auto_fixed list, not in the block_push findings.
    """
    raise NotImplementedError("Implement after 09-03 implements merge agent")
