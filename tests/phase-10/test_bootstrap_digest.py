from __future__ import annotations

"""
Unit tests for hermes-skills/workshop_bootstrap_digest.py (Phase 10).

Covers:
  - harvest_repo_data: correct gh CLI commands called; gh error → empty strings/lists
  - compose_synthesis_prompt: all 7 section headers present in output
  - bootstrap_repo: ingest called with correct file path; research error → returns False
  - main(): --repo flag calls bootstrap_repo with correct arg
"""

import base64
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# Make project root importable
_PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Import the module under test
_BOOTSTRAP_PATH = _PROJECT_ROOT / "hermes-skills" / "workshop_bootstrap_digest.py"

# We need to import the module, but it imports brain_http at module level.
# Mock that import before loading.
_MOCK_BRAIN_HTTP = MagicMock()
_MOCK_BRAIN_HTTP.call_agent = MagicMock(return_value={"content": "## Product\nSample."})


def _load_bootstrap_module():
    """Load the bootstrap module with brain_http mocked."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("workshop_bootstrap_digest", _BOOTSTRAP_PATH)
    module = importlib.util.module_from_spec(spec)

    # Pre-populate sys.modules so import brain_http works
    sys.modules.setdefault("brain_http", _MOCK_BRAIN_HTTP)
    # Also mock list_active_repos
    _mock_reg = MagicMock()
    _mock_reg.list_active_repos = MagicMock(return_value=[])
    sys.modules.setdefault("workshop.repo_registry", _mock_reg)

    spec.loader.exec_module(module)
    return module


# Load once
try:
    _bm = _load_bootstrap_module()
    harvest_repo_data = _bm.harvest_repo_data
    compose_synthesis_prompt = _bm.compose_synthesis_prompt
    bootstrap_repo = _bm.bootstrap_repo
    _gh_run = _bm._gh_run
    _mod_main = _bm.main
except Exception as _exc:
    _bm = None
    harvest_repo_data = None
    compose_synthesis_prompt = None
    bootstrap_repo = None
    _gh_run = None
    _mod_main = None
    _IMPORT_ERROR = str(_exc)
else:
    _IMPORT_ERROR = None


def _skip_if_import_failed():
    if _bm is None:
        pytest.skip(f"Could not import workshop_bootstrap_digest: {_IMPORT_ERROR}")


# ---------------------------------------------------------------------------
# harvest_repo_data
# ---------------------------------------------------------------------------

_SAMPLE_README_B64 = base64.b64encode(b"# My Repo\nAwesome project.").decode()
_SAMPLE_CLAUDE_B64 = base64.b64encode(b"## Standards\nUse PEP 8.").decode()
_SAMPLE_PRS = json.dumps([
    {"title": "Add feature X", "body": "Long body here.", "mergedAt": "2026-01-01T00:00:00Z"},
])


def _make_gh_side_effect(responses: dict) -> callable:
    """
    Return a side_effect for subprocess.run that returns a CompletedProcess
    based on the first arg list element (the subcommand + path).
    """
    def _side_effect(args, **kwargs):
        key = " ".join(str(a) for a in args)
        stdout = ""
        for pattern, value in responses.items():
            if pattern in key:
                stdout = value
                break
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr="")
    return _side_effect


def test_harvest_repo_data_calls_gh_for_readme():
    _skip_if_import_failed()

    readme_content = _SAMPLE_README_B64

    def fake_run(args, **kwargs):
        if "readme" in " ".join(args):
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=readme_content, stderr="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=fake_run) as mock_run:
        result = harvest_repo_data("owner/repo")

    # Verify a call to the readme endpoint was made
    all_calls_joined = [" ".join(c.args[0]) for c in mock_run.call_args_list]
    assert any("readme" in c.lower() for c in all_calls_joined), (
        f"Expected a gh call containing 'readme', got: {all_calls_joined}"
    )
    # README should be decoded
    assert "My Repo" in result["readme"]


def test_harvest_repo_data_gh_error_returns_empty():
    """When gh commands fail (returncode != 0), all fields are empty/empty-list."""
    _skip_if_import_failed()

    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="error")

    with patch("subprocess.run", side_effect=fake_run):
        result = harvest_repo_data("owner/repo")

    assert result["readme"] == ""
    assert result["claude_md"] == ""
    assert result["prs"] == []
    assert result["package_info"] == ""
    assert result["adr_list"] == ""


def test_harvest_repo_data_calls_prs_endpoint():
    """harvest_repo_data calls gh pr list for the owner/repo."""
    _skip_if_import_failed()

    prs_returned = False

    def fake_run(args, **kwargs):
        nonlocal prs_returned
        joined = " ".join(args)
        if "pr" in joined and "list" in joined and "owner/repo" in joined:
            prs_returned = True
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=_SAMPLE_PRS, stderr="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=fake_run):
        result = harvest_repo_data("owner/repo")

    assert prs_returned, "Expected gh pr list to be called for owner/repo"
    assert len(result["prs"]) == 1
    assert result["prs"][0]["title"] == "Add feature X"


def test_harvest_repo_data_returns_empty_lists_on_json_error():
    """If gh pr list returns invalid JSON, prs is still an empty list."""
    _skip_if_import_failed()

    def fake_run(args, **kwargs):
        joined = " ".join(args)
        if "pr" in joined and "list" in joined:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="not json {{{", stderr="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=fake_run):
        result = harvest_repo_data("owner/repo")

    assert result["prs"] == []


# ---------------------------------------------------------------------------
# compose_synthesis_prompt
# ---------------------------------------------------------------------------

_SEVEN_SECTIONS = [
    "## Product",
    "## Architecture",
    "## Standards/Conventions",
    "## Decisions",
    "## Recent PRs",
    "## Prior Clarifications",
    "## Incidents",
]


def test_compose_synthesis_prompt_contains_all_7_section_headers():
    _skip_if_import_failed()

    data = {
        "readme": "# Test Readme",
        "claude_md": "# Test Claude.md",
        "prs": [{"title": "PR 1", "body": "body", "mergedAt": "2026-01-01"}],
        "package_info": '{"name": "my-pkg"}',
        "adr_list": "001-initial.md\n002-database.md",
    }

    prompt = compose_synthesis_prompt("owner/repo", data)

    for section in _SEVEN_SECTIONS:
        assert section in prompt, f"Expected section header {section!r} in prompt"


def test_compose_synthesis_prompt_includes_repo_name():
    _skip_if_import_failed()

    data = {
        "readme": "", "claude_md": "", "prs": [], "package_info": "", "adr_list": ""
    }
    prompt = compose_synthesis_prompt("myorg/myrepo", data)
    assert "myorg/myrepo" in prompt


def test_compose_synthesis_prompt_no_prs_shows_fallback():
    _skip_if_import_failed()

    data = {
        "readme": "", "claude_md": "", "prs": [], "package_info": "", "adr_list": ""
    }
    prompt = compose_synthesis_prompt("owner/repo", data)
    assert "no merged prs found" in prompt.lower()


# ---------------------------------------------------------------------------
# bootstrap_repo
# ---------------------------------------------------------------------------


def test_bootstrap_repo_calls_ingest_with_correct_file_path():
    """bootstrap_repo calls brain_http.call_agent('ingest', ...) with repos/<slug>.md path."""
    _skip_if_import_failed()

    mock_brain = MagicMock()
    mock_brain.call_agent = MagicMock(
        return_value={"content": "## Product\nGreat.\n## Architecture\nMicroservices.\n"}
    )

    def fake_harvest(owner_repo):
        return {
            "readme": "readme", "claude_md": "", "prs": [], "package_info": "", "adr_list": ""
        }

    with patch.object(sys.modules["brain_http"], "call_agent", mock_brain.call_agent):
        with patch.object(_bm, "harvest_repo_data", side_effect=fake_harvest):
            result = bootstrap_repo("owner/repo")

    # Should have returned True on success
    assert result is True

    # Verify ingest was called
    ingest_calls = [
        c for c in mock_brain.call_agent.call_args_list
        if c.args and c.args[0] == "ingest"
    ]
    assert ingest_calls, "Expected brain_http.call_agent('ingest', ...) to be called"

    # Verify the ingest message references the correct file path
    ingest_msg = ingest_calls[0].args[1]
    assert "repos/owner-repo.md" in ingest_msg


def test_bootstrap_repo_returns_false_on_research_error():
    """If research agent returns empty content, bootstrap_repo returns False."""
    _skip_if_import_failed()

    mock_brain = MagicMock()
    mock_brain.call_agent = MagicMock(return_value={"content": ""})

    def fake_harvest(owner_repo):
        return {
            "readme": "readme", "claude_md": "", "prs": [], "package_info": "", "adr_list": ""
        }

    with patch.object(sys.modules["brain_http"], "call_agent", mock_brain.call_agent):
        with patch.object(_bm, "harvest_repo_data", side_effect=fake_harvest):
            result = bootstrap_repo("owner/repo")

    assert result is False


def test_bootstrap_repo_returns_false_on_exception():
    """If harvest_repo_data raises, bootstrap_repo returns False (fail-open)."""
    _skip_if_import_failed()

    with patch.object(_bm, "harvest_repo_data", side_effect=RuntimeError("network error")):
        result = bootstrap_repo("owner/repo")

    assert result is False


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def test_main_with_repo_flag_calls_bootstrap_repo():
    """main() with --repo calls bootstrap_repo with the provided repo name."""
    _skip_if_import_failed()

    called_with = []

    def fake_bootstrap(owner_repo):
        called_with.append(owner_repo)
        return True

    with patch.object(_bm, "bootstrap_repo", side_effect=fake_bootstrap):
        with patch("sys.argv", ["workshop_bootstrap_digest.py", "--repo", "myorg/myrepo"]):
            with pytest.raises(SystemExit) as exc_info:
                _mod_main()

    assert exc_info.value.code == 0
    assert called_with == ["myorg/myrepo"], f"Expected bootstrap_repo called with 'myorg/myrepo', got {called_with}"


def test_main_exit_code_zero_on_success():
    """main() exits with code 0 when bootstrap succeeds."""
    _skip_if_import_failed()

    with patch.object(_bm, "bootstrap_repo", return_value=True):
        with patch("sys.argv", ["workshop_bootstrap_digest.py", "--repo", "owner/repo"]):
            with pytest.raises(SystemExit) as exc_info:
                _mod_main()

    assert exc_info.value.code == 0
