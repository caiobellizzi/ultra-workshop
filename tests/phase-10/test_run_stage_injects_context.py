from __future__ import annotations

"""
Tests that run_stage correctly injects brain context into the query (Phase 10).

run_stage is a nested function inside main() in workshop_build.py.
We test the injection logic indirectly by:
  1. Exercising build_brain_context directly with mocked digest.
  2. Verifying the query-mutation logic that run_stage performs.

We also test the fail-open behavior: build_brain_context exceptions must not
propagate out — the query is used unchanged.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BRAIN_CONTEXT_MODULE = "workshop.brain_context"
_KNOWN_BRAIN_CTX = "## Brain: Repo Digest\n\n### Decisions\nWent with PostgreSQL."


def _simulate_run_stage_injection(query_json: str, repo: str, stage: str) -> str:
    """
    Replicate the injection block from run_stage:
      1. Call build_brain_context(stage, repo)
      2. If non-empty, append to query["context"]
      3. Return updated query_json
    Fail-open: return unchanged query_json if anything raises.
    """
    from workshop.brain_context import build_brain_context

    try:
        brain_ctx = build_brain_context(stage, repo)
        if brain_ctx:
            query = json.loads(query_json)
            query["context"] = query.get("context", "") + "\n\n" + brain_ctx
            query_json = json.dumps(query)
    except Exception:
        pass  # fail-open
    return query_json


# ---------------------------------------------------------------------------
# Tests: context injection present
# ---------------------------------------------------------------------------


def test_run_stage_injects_brain_context_into_query():
    """When build_brain_context returns a non-empty string, query['context'] contains it."""
    original_query = json.dumps({"task": "add feature", "context": ""})

    with patch(f"{_BRAIN_CONTEXT_MODULE}.build_brain_context", return_value=_KNOWN_BRAIN_CTX):
        updated_json = _simulate_run_stage_injection(original_query, "owner/repo", "coder")

    updated = json.loads(updated_json)
    assert "## Brain: Repo Digest" in updated["context"]
    assert "PostgreSQL" in updated["context"]


def test_run_stage_appends_to_existing_context():
    """Injection appends to pre-existing context rather than replacing it."""
    original_query = json.dumps({"task": "fix bug", "context": "Existing context line."})

    with patch(f"{_BRAIN_CONTEXT_MODULE}.build_brain_context", return_value=_KNOWN_BRAIN_CTX):
        updated_json = _simulate_run_stage_injection(original_query, "owner/repo", "coder")

    updated = json.loads(updated_json)
    assert "Existing context line." in updated["context"]
    assert "## Brain: Repo Digest" in updated["context"]


def test_run_stage_no_injection_when_brain_context_empty():
    """If build_brain_context returns '', query is not modified."""
    original_query = json.dumps({"task": "refactor", "context": "Base context."})

    with patch(f"{_BRAIN_CONTEXT_MODULE}.build_brain_context", return_value=""):
        updated_json = _simulate_run_stage_injection(original_query, "owner/repo", "coder")

    updated = json.loads(updated_json)
    assert updated["context"] == "Base context."


# ---------------------------------------------------------------------------
# Tests: fail-open behaviour
# ---------------------------------------------------------------------------


def test_run_stage_fail_open_when_build_brain_context_raises():
    """If build_brain_context raises any exception, query_json is returned unchanged."""
    original_query = json.dumps({"task": "deploy", "context": "some context"})

    with patch(f"{_BRAIN_CONTEXT_MODULE}.build_brain_context", side_effect=RuntimeError("connection refused")):
        updated_json = _simulate_run_stage_injection(original_query, "owner/repo", "coder")

    # Should be the unchanged original
    assert json.loads(updated_json) == json.loads(original_query)


def test_run_stage_fail_open_when_json_parse_fails():
    """If query_json is invalid JSON, the injection is skipped without raising."""
    bad_json = "not valid json {"

    with patch(f"{_BRAIN_CONTEXT_MODULE}.build_brain_context", return_value=_KNOWN_BRAIN_CTX):
        result = _simulate_run_stage_injection(bad_json, "owner/repo", "coder")

    # Returns original unchanged
    assert result == bad_json


# ---------------------------------------------------------------------------
# Tests: stage-specific context
# ---------------------------------------------------------------------------


def test_run_stage_reviewer_qa_includes_test_command():
    """The reviewer:qa stage path passes test_command to build_brain_context."""
    from workshop.brain_context import build_brain_context

    digest = {
        "Standards/Conventions": "Use pytest.",
        "Incidents": "Regression in auth module.",
    }
    with patch("workshop.brain_context.resolve_repo_digest", return_value=digest):
        result = build_brain_context("reviewer:qa", "owner/repo", test_command="pytest -x --tb=short")

    assert "Test command: pytest -x --tb=short" in result
    assert "## Brain: Repo Digest" in result


def test_run_stage_planner_stage_gets_architecture():
    """The planner stage should include Architecture in its context."""
    from workshop.brain_context import build_brain_context

    digest = {
        "Architecture": "Event-driven with Kafka.",
        "Standards/Conventions": "PEP 8.",
        "Decisions": "Chose Redis.",
        "Recent PRs": "Added queue retry logic.",
    }
    with patch("workshop.brain_context.resolve_repo_digest", return_value=digest):
        result = build_brain_context("planner", "owner/repo")

    assert "### Architecture" in result
    assert "Kafka" in result
