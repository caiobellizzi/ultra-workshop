"""
Brain context injection helper.
Provides deterministic vault digest reads and per-stage section slices.
Fail-open: all public functions return empty on any error.
"""

from __future__ import annotations

import logging
import sys
import os

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stage → section mapping
# ---------------------------------------------------------------------------

STAGE_SECTIONS: dict[str, list[str]] = {
    "brainstorm": ["Product", "Prior Clarifications", "Decisions"],
    "triage": ["Product", "Decisions", "Recent PRs"],
    "requirements": ["Product", "Prior Clarifications", "Standards/Conventions"],
    "planner": ["Architecture", "Standards/Conventions", "Decisions", "Recent PRs"],
    "coder": ["Standards/Conventions", "Architecture", "Decisions"],
    "reviewer:security": ["Incidents", "Standards/Conventions"],
    "reviewer:python": ["Standards/Conventions"],
    "reviewer:typescript": ["Standards/Conventions"],
    "reviewer:reactjs": ["Standards/Conventions"],
    "reviewer:docs": ["Standards/Conventions"],
    "reviewer:qa": ["Standards/Conventions", "Incidents"],
    "reviewer:correctness": ["Decisions", "Incidents"],
    "reviewer:config": ["Standards/Conventions", "Decisions"],
    "merge": ["Decisions", "Incidents"],
}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sanitize_repo_name(repo: str) -> str:
    """Convert 'owner/repo' to 'owner-repo' (lowercase) with safety checks."""
    if "\x00" in repo:
        raise ValueError("repo name contains null bytes")
    if repo.startswith("/"):
        raise ValueError("repo name must not start with '/'")
    if ".." in repo:
        raise ValueError("repo name must not contain '..'")
    return repo.replace("/", "-").lower()


def parse_digest_sections(md: str) -> dict[str, str]:
    """Split markdown on '## ' headers, return {section_name: section_body}."""
    if not md:
        return {}

    sections: dict[str, str] = {}
    current_name: str | None = None
    current_lines: list[str] = []

    for line in md.splitlines(keepends=True):
        if line.startswith("## "):
            if current_name is not None:
                sections[current_name] = "".join(current_lines).strip()
            current_name = line[3:].strip()
            current_lines = []
        else:
            if current_name is not None:
                current_lines.append(line)

    if current_name is not None:
        sections[current_name] = "".join(current_lines).strip()

    return sections


def resolve_repo_digest(repo: str, vault_dir: str | None = None) -> dict[str, str]:
    """Read and parse the vault digest for a repo. Returns {} on any error."""
    try:
        base = vault_dir or "/srv/second-brain"
        slug = _sanitize_repo_name(repo)
        path = os.path.join(base, "repos", slug + ".md")
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()
        return parse_digest_sections(content)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_brain_context(
    stage: str,
    repo: str,
    vault_dir: str | None = None,
    test_command: str = "",
) -> str:
    """
    Build a '## Brain: Repo Digest' block with only the sections relevant to
    the given stage. Returns '' if the digest is missing or no sections match.
    Fail-open: returns '' on any exception.
    """
    try:
        digest = resolve_repo_digest(repo, vault_dir)
        if not digest:
            return ""

        wanted = STAGE_SECTIONS.get(stage, [])
        parts: list[str] = []

        # reviewer:qa gets test_command prepended
        if stage == "reviewer:qa" and test_command:
            parts.append(f"Test command: {test_command}")

        for section in wanted:
            if section in digest:
                body = digest[section]
                parts.append(f"### {section}\n{body}")

        if not parts:
            return ""

        header = "## Brain: Repo Digest"
        return header + "\n\n" + "\n\n".join(parts)
    except Exception:
        return ""


def _append_digest_section(repo: str, section: str, content: str) -> None:
    """
    Append content to a named section in the vault digest via the brain ingest
    agent. Fail-open: logs a warning and returns on any exception.
    """
    try:
        # Import here to avoid circular import issues and allow the module to
        # load even when brain_http is unavailable.
        _hermes = os.path.join(
            os.path.dirname(__file__), "..", "hermes-skills"
        )
        if _hermes not in sys.path:
            sys.path.insert(0, os.path.abspath(_hermes))

        import brain_http  # type: ignore[import]

        slug = _sanitize_repo_name(repo)
        message = f"file: repos/{slug}.md\nsection: {section}\nappend:\n{content}"
        brain_http.call_agent("ingest", message)
    except Exception as exc:  # noqa: BLE001
        logger.warning("_append_digest_section failed: %s", exc)
