"""
audit-claude-skills — Walk ~/.claude/skills/, classify, and optionally translate.

Classifies all Claude Code skills into 4 categories:
  - claude_specific_skip: prefixed with gsd-, superpowers:, dotnet-
  - agent_agnostic: no tool references; copy as-is to Hermes
  - auto_translated: all tool refs have direct DIRECT_TOOL_MAP equivalents
  - requires_manual_port: contains manual-port tools (Agent, TaskCreate, etc.)

Writes:
  - skill-audit.json at repo root (when --apply)
  - TRANSLATION_NOTES.md per auto_translated skill under HERMES_TRANSLATED_ROOT

Deploy location: scripts/audit-claude-skills.py
Run on: Mac only (reads ~/.claude/skills/ which is Mac-local)

Usage:
  python scripts/audit-claude-skills.py            # dry-run (no writes)
  python scripts/audit-claude-skills.py --apply    # write translated files
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

CLAUDE_SKILLS_ROOT = pathlib.Path.home() / ".claude" / "skills"
HERMES_TRANSLATED_ROOT = pathlib.Path.home() / ".hermes" / "skills" / "translated"

DIRECT_TOOL_MAP: dict[str, str] = {
    "Read": "read_file",
    "Write": "write_file",
    "Edit": "edit_file",
    "Bash": "terminal",
    "Grep": "search",
    "Glob": "find_files",
    "WebFetch": "http_request",
    "WebSearch": "web_search",
}

MANUAL_PORT_TOOLS: set[str] = {
    "TaskCreate",
    "TaskUpdate",
    "TaskList",
    "AskUserQuestion",
    "Skill",
    "ExitPlanMode",
    "Agent",
    "NotebookEdit",
}

SKIP_PREFIXES = ("gsd-", "superpowers:", "dotnet-")

# Regex to detect tool name references in skill body
_TOOL_PATTERN = re.compile(
    r"\b(Read|Write|Edit|Bash|Grep|Glob|WebFetch|WebSearch"
    r"|TaskCreate|TaskUpdate|TaskList|AskUserQuestion"
    r"|Skill|ExitPlanMode|Agent|NotebookEdit)\b"
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _write_file(path: Path, content: str, dry_run: bool) -> None:
    """Write content to path, respecting dry_run flag.

    Idempotent: skips write if existing content is identical.
    """
    if dry_run:
        print(f"[dry-run] would write {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return  # already up-to-date
    path.write_text(content, encoding="utf-8")


def _read_skill_body(skill_path: Path) -> str:
    """Read the body of a SKILL.md (everything after first frontmatter block)."""
    try:
        raw = skill_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    # Split on --- to strip frontmatter; body is after second ---
    parts = raw.split("---")
    if len(parts) >= 3:
        return "---".join(parts[2:])
    return raw


def _is_identical(path: Path, content: str) -> bool:
    """Return True if path exists and its content matches exactly."""
    return path.exists() and path.read_text(encoding="utf-8") == content


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def classify(
    name: str, body: str
) -> tuple[str, list[str], list[str]]:
    """Classify a skill by name and body text.

    Returns:
        (category, translatable_tools_found, manual_tools_found)

    Categories (in priority order):
        1. claude_specific_skip — name starts with a SKIP_PREFIX
        2. agent_agnostic       — no tool references at all
        3. auto_translated      — all tool refs are in DIRECT_TOOL_MAP
        4. requires_manual_port — has at least one MANUAL_PORT_TOOL ref
    """
    # Priority 1: skip by prefix
    if name.startswith(SKIP_PREFIXES):
        return ("claude_specific_skip", [], [])

    # Find all tool references in the body
    found_tools = _TOOL_PATTERN.findall(body)
    unique_tools = list(dict.fromkeys(found_tools))  # deduplicate, preserve order

    translatable = [t for t in unique_tools if t in DIRECT_TOOL_MAP]
    manual = [t for t in unique_tools if t in MANUAL_PORT_TOOLS]

    # Priority 2: no tool refs → agent agnostic
    if not unique_tools:
        return ("agent_agnostic", [], [])

    # Priority 3: has manual tools → requires manual port
    if manual:
        return ("requires_manual_port", translatable, manual)

    # Priority 4: all tools translatable → auto_translated
    return ("auto_translated", translatable, [])


# ---------------------------------------------------------------------------
# Translation notes generator
# ---------------------------------------------------------------------------


def _build_translation_notes(
    skill_name: str,
    skill_path: Path,
    translatable_tools: list[str],
    generated_at: str,
) -> str:
    """Build TRANSLATION_NOTES.md content for an auto_translated skill."""
    substitutions = "\n".join(
        f"- `{tool}` → `{DIRECT_TOOL_MAP[tool]}`"
        for tool in translatable_tools
    )
    if not substitutions:
        substitutions = "None."

    return f"""# Translation Notes: {skill_name}

**Category:** auto_translated
**Source:** {skill_path}
**Generated:** {generated_at}

## Tool Substitutions Applied
{substitutions}

## Warnings
None.
"""


# ---------------------------------------------------------------------------
# Main entry points
# ---------------------------------------------------------------------------


def main_with_roots(
    claude_root: Path,
    hermes_root: Path,
    dry_run: bool,
    audit_json_path: Optional[Path] = None,
) -> dict:
    """Walk claude_root, classify skills, write translated files.

    Args:
        claude_root:       Directory that mimics ~/.claude/skills/ layout.
        hermes_root:       Target translated root (~/.hermes/skills/translated/).
        dry_run:           If True, print actions but write nothing.
        audit_json_path:   Where to write skill-audit.json (default: skill-audit.json
                           in cwd). Pass None to skip writing the JSON file.

    Returns:
        {"generated_at": ISO str, "skills": [{"name", "category", "path", ...}]}

    Idempotency: if the skills data is identical to what is already on disk,
    the existing generated_at timestamp is preserved so the output is byte-for-byte
    identical on repeated runs.
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    skills: list[dict] = []

    # Determine audit JSON path for idempotency read
    _audit_path = audit_json_path if audit_json_path is not None else Path("skill-audit.json")

    if not claude_root.exists():
        return {"generated_at": generated_at, "skills": skills}

    # Walk each subdirectory that contains a SKILL.md
    for skill_dir in sorted(claude_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        skill_name = skill_dir.name
        body = _read_skill_body(skill_file)
        category, translatable, manual = classify(skill_name, body)

        entry: dict = {
            "name": skill_name,
            "category": category,
            "path": str(skill_file),
            "translatable_tools": translatable,
            "manual_tools": manual,
        }
        skills.append(entry)

        # Write TRANSLATION_NOTES.md for auto_translated skills
        if category == "auto_translated":
            # Path safety: strip any path traversal from skill name
            safe_name = Path(skill_name).name
            assert ".." not in safe_name, f"Unsafe skill name: {skill_name!r}"
            output_dir = hermes_root / safe_name
            notes_path = output_dir / "TRANSLATION_NOTES.md"
            notes_content = _build_translation_notes(
                skill_name=skill_name,
                skill_path=skill_file,
                translatable_tools=translatable,
                generated_at=generated_at,
            )
            _write_file(notes_path, notes_content, dry_run)

    result: dict = {"generated_at": generated_at, "skills": skills}

    # Idempotency: if an existing audit file has the same skills data, reuse its timestamp
    # so repeated --apply runs produce byte-for-byte identical output.
    if not dry_run and _audit_path.exists():
        try:
            existing = json.loads(_audit_path.read_text(encoding="utf-8"))
            if existing.get("skills") == skills:
                result["generated_at"] = existing["generated_at"]
        except (json.JSONDecodeError, OSError):
            pass  # can't read existing — use fresh timestamp

    return result


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Classify and optionally translate Claude skills to Hermes format."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write translated files (default: dry-run only, no writes)",
    )
    args = parser.parse_args()
    dry_run = not args.apply

    audit_json_path = Path("skill-audit.json")

    result = main_with_roots(
        claude_root=CLAUDE_SKILLS_ROOT,
        hermes_root=HERMES_TRANSLATED_ROOT,
        dry_run=dry_run,
        audit_json_path=audit_json_path,
    )

    # Print summary
    categories: dict[str, int] = {}
    for skill in result["skills"]:
        cat = skill["category"]
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\nSkill audit — {len(result['skills'])} skills found")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")

    # Emit skill-audit.json to repo root
    json_content = json.dumps(result, indent=2)
    _write_file(audit_json_path, json_content, dry_run)

    if dry_run:
        print("\n[dry-run] No files written. Use --apply to write translations.")
    else:
        print(f"\nWrote {audit_json_path}")
        translated_count = sum(1 for s in result["skills"] if s["category"] == "auto_translated")
        print(f"Wrote TRANSLATION_NOTES.md for {translated_count} auto_translated skills")


if __name__ == "__main__":
    main()
