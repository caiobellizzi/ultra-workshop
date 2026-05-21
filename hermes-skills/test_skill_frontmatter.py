"""
test_skill_frontmatter — Validate SKILL.md frontmatter for every skill in skills/.

Checks that each skills/<name>/SKILL.md:
  - Contains a valid YAML frontmatter block
  - Has required fields: name, description
  - Does NOT contain Hermes-incompatible CC fields: tools, mcpServers, hooks
  - Has name matching the directory name

Deploy location: hermes-skills/test_skill_frontmatter.py
Run on: VPS or Mac (reads skills/ relative to repo root)
"""
from __future__ import annotations

import yaml
import pytest
from pathlib import Path

SKILL_DIRS = list((Path(__file__).parent.parent / "skills").glob("*/SKILL.md"))


@pytest.mark.parametrize("skill_path", SKILL_DIRS, ids=lambda p: p.parent.name)
def test_frontmatter_has_required_fields(skill_path):
    raw = skill_path.read_text()
    parts = raw.split("---")
    assert len(parts) >= 3, f"{skill_path}: no frontmatter block found"
    fm = yaml.safe_load(parts[1])
    assert "name" in fm, f"{skill_path}: missing 'name'"
    assert "description" in fm, f"{skill_path}: missing 'description'"
    for forbidden in ("tools", "mcpServers", "hooks"):
        assert forbidden not in fm, f"{skill_path}: forbidden Hermes key '{forbidden}' present"


@pytest.mark.parametrize("skill_path", SKILL_DIRS, ids=lambda p: p.parent.name)
def test_name_matches_directory(skill_path):
    raw = skill_path.read_text()
    parts = raw.split("---")
    assert len(parts) >= 3
    fm = yaml.safe_load(parts[1])
    assert fm.get("name") == skill_path.parent.name, \
        f"name '{fm.get('name')}' does not match directory '{skill_path.parent.name}'"
