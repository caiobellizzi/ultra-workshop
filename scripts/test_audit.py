"""
pytest tests for audit-claude-skills.py helper module.

Tests use tmp_path fixtures that create minimal fake skill trees
so they never touch ~/.claude/skills/ or ~/.hermes/skills/.

Run: cd /path/to/ultra-workshop && python -m pytest scripts/test_audit.py -v
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module load (importlib — handles hyphenated filename)
# ---------------------------------------------------------------------------

_MODULE_PATH = Path(__file__).parent / "audit-claude-skills.py"


def _load_audit():
    """Load audit-claude-skills.py module via importlib."""
    if "audit_claude_skills" in sys.modules:
        return sys.modules["audit_claude_skills"]
    if not _MODULE_PATH.exists():
        pytest.skip(reason=f"audit-claude-skills.py not found at {_MODULE_PATH}")
    spec = importlib.util.spec_from_file_location("audit_claude_skills", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules["audit_claude_skills"] = mod
    return mod


@pytest.fixture(autouse=True)
def audit():
    """Load the audit module, skipping all tests if not yet implemented."""
    return _load_audit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_skill(skills_root: Path, name: str, body: str = "") -> Path:
    """Create a minimal fake skill directory with SKILL.md."""
    skill_dir = skills_root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    frontmatter = f"---\nname: {name}\ndescription: \"A test skill\"\n---\n"
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(frontmatter + "# Body\n" + body, encoding="utf-8")
    return skill_dir


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_skills_dir(tmp_path) -> Path:
    """Return a temp dir that mimics ~/.claude/skills/ layout."""
    skills = tmp_path / "skills"
    skills.mkdir()
    return skills


@pytest.fixture
def tmp_translated_dir(tmp_path) -> Path:
    """Return the target translated root (does not exist yet)."""
    return tmp_path / "translated"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_dry_run_no_write(audit, tmp_skills_dir, tmp_translated_dir):
    """--dry-run must never create files under hermes_root."""
    make_skill(tmp_skills_dir, "my-skill", body="Use Bash to run commands and Read files.")
    audit.main_with_roots(
        claude_root=tmp_skills_dir,
        hermes_root=tmp_translated_dir,
        dry_run=True,
    )
    # translated dir must not exist or be completely empty
    assert not tmp_translated_dir.exists() or not any(tmp_translated_dir.iterdir())


def test_apply_writes_translated_skill(audit, tmp_skills_dir, tmp_translated_dir):
    """--apply must write TRANSLATION_NOTES.md under hermes_root/<name>/."""
    make_skill(tmp_skills_dir, "auto-skill", body="Use Bash to run commands.")
    result = audit.main_with_roots(
        claude_root=tmp_skills_dir,
        hermes_root=tmp_translated_dir,
        dry_run=False,
    )
    # At least one skill should be auto_translated (has Bash which maps to terminal)
    categories = {s["name"]: s["category"] for s in result["skills"]}
    assert "auto-skill" in categories
    assert categories["auto-skill"] == "auto_translated"
    # TRANSLATION_NOTES.md must appear
    notes_file = tmp_translated_dir / "auto-skill" / "TRANSLATION_NOTES.md"
    assert notes_file.exists(), f"Expected {notes_file} to exist"
    content = notes_file.read_text()
    assert "terminal" in content  # Bash → terminal substitution noted


def test_idempotent(audit, tmp_skills_dir, tmp_translated_dir):
    """Running main_with_roots twice produces identical output dicts."""
    make_skill(tmp_skills_dir, "my-skill", body="Use Bash to run commands.")
    out1 = audit.main_with_roots(
        claude_root=tmp_skills_dir,
        hermes_root=tmp_translated_dir,
        dry_run=False,
    )
    out2 = audit.main_with_roots(
        claude_root=tmp_skills_dir,
        hermes_root=tmp_translated_dir,
        dry_run=False,
    )
    # Skills lists must be equal (generated_at timestamps may differ)
    assert out1["skills"] == out2["skills"]


def test_skip_gsd_prefix(audit, tmp_skills_dir, tmp_translated_dir):
    """Skills with 'gsd-' prefix must be classified as claude_specific_skip."""
    make_skill(tmp_skills_dir, "gsd-test", body="Use Bash to run.")
    result = audit.main_with_roots(
        claude_root=tmp_skills_dir,
        hermes_root=tmp_translated_dir,
        dry_run=False,
    )
    categories = {s["name"]: s["category"] for s in result["skills"]}
    assert "gsd-test" in categories
    assert categories["gsd-test"] == "claude_specific_skip"
    # Must NOT appear in translated dir
    assert not (tmp_translated_dir / "gsd-test").exists()


def test_safety_no_direct_hermes_write(audit, tmp_skills_dir, tmp_translated_dir, monkeypatch):
    """All write paths must be under hermes_root (translated subtree)."""
    written_paths: list[Path] = []
    original_write_file = audit._write_file

    def capturing_write(path: Path, content: str, dry_run: bool) -> None:
        if not dry_run:
            written_paths.append(path)
        original_write_file(path, content, dry_run)

    monkeypatch.setattr(audit, "_write_file", capturing_write)

    make_skill(tmp_skills_dir, "auto-skill", body="Use Bash to run commands.")
    audit.main_with_roots(
        claude_root=tmp_skills_dir,
        hermes_root=tmp_translated_dir,
        dry_run=False,
    )

    for written_path in written_paths:
        # All write paths must be inside hermes_root (the translated subtree)
        assert str(written_path).startswith(str(tmp_translated_dir)), (
            f"Unsafe write outside hermes_root: {written_path}"
        )


def test_audit_json_schema(audit, tmp_skills_dir, tmp_translated_dir):
    """Returned dict must have 'generated_at' and 'skills'; each skill must have required keys."""
    make_skill(tmp_skills_dir, "my-skill", body="Use Bash to run commands.")
    result = audit.main_with_roots(
        claude_root=tmp_skills_dir,
        hermes_root=tmp_translated_dir,
        dry_run=True,
    )
    assert "generated_at" in result, "Missing 'generated_at' key"
    assert "skills" in result, "Missing 'skills' key"
    assert isinstance(result["skills"], list)
    for skill in result["skills"]:
        assert "name" in skill, f"Skill missing 'name': {skill}"
        assert "category" in skill, f"Skill missing 'category': {skill}"
        assert "path" in skill, f"Skill missing 'path': {skill}"


def test_translation_notes_md_content(audit, tmp_skills_dir, tmp_translated_dir):
    """TRANSLATION_NOTES.md for auto_translated skill must contain required content."""
    make_skill(tmp_skills_dir, "translate-me", body="Use Bash to run commands and Read files.")
    audit.main_with_roots(
        claude_root=tmp_skills_dir,
        hermes_root=tmp_translated_dir,
        dry_run=False,
    )
    notes_file = tmp_translated_dir / "translate-me" / "TRANSLATION_NOTES.md"
    assert notes_file.exists()
    content = notes_file.read_text()
    assert "Tool Substitutions Applied" in content
    assert "translate-me" in content


def test_classify_agent_agnostic(audit, tmp_skills_dir, tmp_translated_dir):
    """A skill with no tool references must be classified as agent_agnostic."""
    make_skill(tmp_skills_dir, "pure-prose", body="This is pure prose with no tool references.")
    result = audit.main_with_roots(
        claude_root=tmp_skills_dir,
        hermes_root=tmp_translated_dir,
        dry_run=True,
    )
    categories = {s["name"]: s["category"] for s in result["skills"]}
    assert categories.get("pure-prose") == "agent_agnostic"


def test_classify_requires_manual_port(audit, tmp_skills_dir, tmp_translated_dir):
    """A skill with manual-port tools (Agent, TaskCreate) must be requires_manual_port."""
    make_skill(tmp_skills_dir, "needs-port", body="Use Agent and TaskCreate to orchestrate tasks.")
    result = audit.main_with_roots(
        claude_root=tmp_skills_dir,
        hermes_root=tmp_translated_dir,
        dry_run=True,
    )
    categories = {s["name"]: s["category"] for s in result["skills"]}
    assert categories.get("needs-port") == "requires_manual_port"
