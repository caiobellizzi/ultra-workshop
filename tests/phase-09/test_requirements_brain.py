from __future__ import annotations

"""
Requirements gate brain pre-query tests (B7 - 09-03).

Tests verify:
  - _query_prior_clarifications calls brain with "prior clarifications" message.
  - _query_prior_clarifications returns "" when brain raises (fail-open).
  - evaluate_requirements still works when brain is unreachable.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_query_prior_clarifications_called() -> None:
    """_query_prior_clarifications calls brain with a message containing 'prior clarifications'."""
    from workshop import requirements_gate

    mock_brain = MagicMock()
    mock_brain.call_agent = MagicMock(return_value={"content": "no prior clarifications"})

    with patch.object(requirements_gate, "_brain_http", mock_brain):
        result = requirements_gate._query_prior_clarifications("myorg/myrepo")

    mock_brain.call_agent.assert_called_once()
    args = mock_brain.call_agent.call_args[0]
    assert "prior clarifications" in args[1].lower(), f"Expected 'prior clarifications' in call message, got: {args[1]}"


def test_query_prior_clarifications_fail_open() -> None:
    """_query_prior_clarifications returns '' when brain raises an exception."""
    from workshop import requirements_gate

    mock_brain = MagicMock()
    mock_brain.call_agent = MagicMock(side_effect=Exception("Brain unreachable"))

    with patch.object(requirements_gate, "_brain_http", mock_brain):
        result = requirements_gate._query_prior_clarifications("myorg/myrepo")

    assert result == "", f"Expected empty string on brain failure, got: {result!r}"


def test_evaluate_requirements_still_works_when_brain_fails() -> None:
    """evaluate_requirements returns RequirementsDecision even when brain is unreachable."""
    from workshop import requirements_gate

    mock_brain = MagicMock()
    mock_brain.call_agent = MagicMock(side_effect=ConnectionError("Brain down"))

    query = json.dumps({
        "task_id": "ws-abc123",
        "goal": "Add user authentication",
        "repo": {"full_name": "myorg/myrepo"},
        "clarifications": [],
    })

    with patch.object(requirements_gate, "_brain_http", mock_brain):
        result = requirements_gate.evaluate_requirements(query)

    from workshop.requirements_gate import RequirementsDecision
    assert isinstance(result, RequirementsDecision), f"Expected RequirementsDecision, got {type(result)}"
