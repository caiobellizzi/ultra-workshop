from __future__ import annotations

"""
Unit tests for workshop/brain_context.py (Phase 10).

Covers:
  - parse_digest_sections: full/empty/partial markdown
  - resolve_repo_digest: happy path, FileNotFoundError, ValueError, other exceptions
  - _sanitize_repo_name: valid slugs, traversal attacks
  - build_brain_context: stage section slices, reviewer:qa test_command, empty digest, exception
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from workshop.brain_context import (
    _sanitize_repo_name,
    build_brain_context,
    parse_digest_sections,
    resolve_repo_digest,
)

# ---------------------------------------------------------------------------
# parse_digest_sections
# ---------------------------------------------------------------------------

FULL_MARKDOWN = """\
## Product
This is the product section.

## Architecture
Service mesh with Kafka.

## Standards/Conventions
PEP 8, Conventional Commits.

## Decisions
Chose PostgreSQL over MySQL.

## Recent PRs
- Added OAuth2 support

## Prior Clarifications
No prior clarifications yet.

## Incidents
None so far.
"""

ALL_7_SECTIONS = [
    "Product",
    "Architecture",
    "Standards/Conventions",
    "Decisions",
    "Recent PRs",
    "Prior Clarifications",
    "Incidents",
]


def test_parse_digest_sections_full_markdown():
    result = parse_digest_sections(FULL_MARKDOWN)
    for section in ALL_7_SECTIONS:
        assert section in result, f"Expected section {section!r} in result"
    assert "product section" in result["Product"].lower()
    assert "kafka" in result["Architecture"].lower()
    assert "postgresql" in result["Decisions"].lower()


def test_parse_digest_sections_empty_string():
    result = parse_digest_sections("")
    assert result == {}


def test_parse_digest_sections_none_equivalent():
    # Empty string and whitespace-only produce {}
    assert parse_digest_sections("  \n  ") == {}


def test_parse_digest_sections_partial_sections():
    md = "## Product\nShort product.\n## Decisions\nWent with Redis.\n"
    result = parse_digest_sections(md)
    assert set(result.keys()) == {"Product", "Decisions"}
    assert "redis" in result["Decisions"].lower()


def test_parse_digest_sections_single_section():
    md = "## Architecture\nMicroservices.\n"
    result = parse_digest_sections(md)
    assert result == {"Architecture": "Microservices."}


def test_parse_digest_sections_strips_trailing_whitespace():
    md = "## Product\nLine one.\n\n"
    result = parse_digest_sections(md)
    assert result["Product"] == "Line one."


# ---------------------------------------------------------------------------
# _sanitize_repo_name
# ---------------------------------------------------------------------------


def test_sanitize_repo_name_slash_becomes_dash():
    assert _sanitize_repo_name("owner/repo") == "owner-repo"


def test_sanitize_repo_name_uppercase_lowercased():
    assert _sanitize_repo_name("OWNER/REPO") == "owner-repo"


def test_sanitize_repo_name_dotdot_raises():
    with pytest.raises(ValueError):
        _sanitize_repo_name("../evil")


def test_sanitize_repo_name_leading_slash_raises():
    with pytest.raises(ValueError):
        _sanitize_repo_name("/etc/passwd")


def test_sanitize_repo_name_null_byte_raises():
    with pytest.raises(ValueError):
        _sanitize_repo_name("null\x00byte")


# ---------------------------------------------------------------------------
# resolve_repo_digest
# ---------------------------------------------------------------------------


def test_resolve_repo_digest_happy_path():
    sample_md = "## Product\nGreat product.\n## Architecture\nMonolith.\n"
    m = mock_open(read_data=sample_md)
    with patch("builtins.open", m):
        result = resolve_repo_digest("owner/repo", vault_dir="/fake/vault")
    assert "Product" in result
    assert "Architecture" in result


def test_resolve_repo_digest_file_not_found():
    with patch("builtins.open", side_effect=FileNotFoundError("not found")):
        result = resolve_repo_digest("owner/repo", vault_dir="/fake/vault")
    assert result == {}


def test_resolve_repo_digest_value_error_traversal():
    # _sanitize_repo_name raises ValueError for traversal — resolve should return {}
    result = resolve_repo_digest("../evil", vault_dir="/fake/vault")
    assert result == {}


def test_resolve_repo_digest_other_exception():
    with patch("builtins.open", side_effect=PermissionError("denied")):
        result = resolve_repo_digest("owner/repo", vault_dir="/fake/vault")
    assert result == {}


# ---------------------------------------------------------------------------
# build_brain_context
# ---------------------------------------------------------------------------


def _mock_digest(sections: list[str]) -> dict[str, str]:
    return {s: f"Content of {s}." for s in sections}


def test_build_brain_context_coder_stage():
    """Stage 'coder' gets Standards/Conventions + Architecture + Decisions."""
    digest = _mock_digest(ALL_7_SECTIONS)
    with patch("workshop.brain_context.resolve_repo_digest", return_value=digest):
        result = build_brain_context("coder", "owner/repo")

    assert "## Brain: Repo Digest" in result
    assert "### Standards/Conventions" in result
    assert "### Architecture" in result
    assert "### Decisions" in result
    # coder should NOT include Product or Recent PRs
    assert "### Product" not in result
    assert "### Recent PRs" not in result


def test_build_brain_context_reviewer_qa_with_test_command():
    """reviewer:qa stage prepends test_command when provided."""
    digest = _mock_digest(ALL_7_SECTIONS)
    with patch("workshop.brain_context.resolve_repo_digest", return_value=digest):
        result = build_brain_context("reviewer:qa", "owner/repo", test_command="pytest -x")

    assert "Test command: pytest -x" in result
    assert "## Brain: Repo Digest" in result


def test_build_brain_context_reviewer_qa_without_test_command():
    """reviewer:qa without test_command does not include 'Test command:' prefix."""
    digest = _mock_digest(ALL_7_SECTIONS)
    with patch("workshop.brain_context.resolve_repo_digest", return_value=digest):
        result = build_brain_context("reviewer:qa", "owner/repo")

    assert "Test command:" not in result


def test_build_brain_context_missing_sections_returns_present_only():
    """If digest is missing some sections, only present ones are returned."""
    partial_digest = {"Architecture": "Microservices only."}
    with patch("workshop.brain_context.resolve_repo_digest", return_value=partial_digest):
        result = build_brain_context("coder", "owner/repo")

    # coder wants Standards/Conventions + Architecture + Decisions;
    # only Architecture is present
    assert "### Architecture" in result
    assert "### Standards/Conventions" not in result
    assert "### Decisions" not in result


def test_build_brain_context_empty_digest_returns_empty_string():
    with patch("workshop.brain_context.resolve_repo_digest", return_value={}):
        result = build_brain_context("coder", "owner/repo")
    assert result == ""


def test_build_brain_context_exception_during_resolve_returns_empty():
    """If resolve_repo_digest raises, build_brain_context returns '' (fail-open)."""
    with patch("workshop.brain_context.resolve_repo_digest", side_effect=RuntimeError("boom")):
        result = build_brain_context("coder", "owner/repo")
    assert result == ""


def test_build_brain_context_unknown_stage_returns_empty():
    """Unknown stage has no section mapping → empty result."""
    digest = _mock_digest(ALL_7_SECTIONS)
    with patch("workshop.brain_context.resolve_repo_digest", return_value=digest):
        result = build_brain_context("totally-unknown-stage", "owner/repo")
    assert result == ""
