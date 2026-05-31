# Deploy location: /opt/ultra-workshop/hermes-skills/workshop_bootstrap_digest.py
"""Cold-start bootstrap — harvest a target repo via gh CLI and populate its second-brain digest."""

from __future__ import annotations

import argparse
import base64
import json
import logging
import subprocess
import sys
from pathlib import Path

# Allow running from the hermes-skills directory directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import brain_http  # noqa: E402
from workshop.repo_registry import list_active_repos  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def _gh_run(args: list[str]) -> str:
    """Run a gh CLI command and return stdout. Returns empty string on error."""
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        log.debug("gh command failed: %s\nstderr: %s", " ".join(args), result.stderr.strip())
        return ""
    return result.stdout.strip()


def harvest_repo_data(owner_repo: str) -> dict:
    """Gather repo data via gh CLI. Fail-open: empty string/list on any gh error."""
    data: dict = {
        "readme": "",
        "claude_md": "",
        "prs": [],
        "package_info": "",
        "adr_list": "",
    }

    # README
    raw_readme = _gh_run(["gh", "api", f"repos/{owner_repo}/readme", "--jq", ".content"])
    if raw_readme:
        try:
            data["readme"] = base64.b64decode(raw_readme).decode("utf-8", errors="replace")
        except Exception:
            data["readme"] = raw_readme

    # CLAUDE.md
    raw_claude = _gh_run(["gh", "api", f"repos/{owner_repo}/contents/CLAUDE.md", "--jq", ".content"])
    if raw_claude:
        try:
            data["claude_md"] = base64.b64decode(raw_claude).decode("utf-8", errors="replace")
        except Exception:
            data["claude_md"] = raw_claude

    # Last 5 merged PRs
    prs_json = _gh_run([
        "gh", "pr", "list",
        "--repo", owner_repo,
        "--state", "merged",
        "--limit", "5",
        "--json", "title,body,mergedAt",
    ])
    if prs_json:
        try:
            data["prs"] = json.loads(prs_json)
        except json.JSONDecodeError:
            data["prs"] = []

    # Package info (try package.json, then pyproject.toml)
    for pkg_file in ("package.json", "pyproject.toml"):
        pkg_raw = _gh_run(["gh", "api", f"repos/{owner_repo}/contents/{pkg_file}"])
        if pkg_raw:
            try:
                pkg_obj = json.loads(pkg_raw)
                content_b64 = pkg_obj.get("content", "")
                data["package_info"] = base64.b64decode(content_b64).decode("utf-8", errors="replace")
            except Exception:
                data["package_info"] = pkg_raw
            break

    # ADR files
    adr_raw = _gh_run(["gh", "api", f"repos/{owner_repo}/contents/docs/adr", "--jq", ".[].name"])
    data["adr_list"] = adr_raw  # newline-separated names or empty string

    return data


def compose_synthesis_prompt(owner_repo: str, data: dict) -> str:
    """Build a prompt asking the research agent to synthesize repo data into the 7-section digest."""
    prs_text = ""
    if data["prs"]:
        pr_lines = []
        for pr in data["prs"]:
            merged_at = pr.get("mergedAt", "unknown")
            title = pr.get("title", "(no title)")
            body = (pr.get("body") or "").strip()[:300]
            pr_lines.append(f"- [{merged_at}] {title}\n  {body}")
        prs_text = "\n".join(pr_lines)
    else:
        prs_text = "(no merged PRs found)"

    readme_section = data["readme"][:4000] if data["readme"] else "(not found)"
    claude_md_section = data["claude_md"][:2000] if data["claude_md"] else "(not found)"
    package_section = data["package_info"][:1000] if data["package_info"] else "(not found)"
    adr_section = data["adr_list"] if data["adr_list"] else "(none found)"

    return f"""You are synthesizing a second-brain digest for the GitHub repository: {owner_repo}

Below is harvested data from the repo. Produce a structured digest using EXACTLY these 7 sections in this order, each starting with '## ' followed by the section name:

## Product
## Architecture
## Standards/Conventions
## Decisions
## Recent PRs
## Prior Clarifications
## Incidents

Guidelines:
- Be concise and factual. Use bullet points where appropriate.
- If a section has no relevant data, write "(none documented)".
- Do NOT add extra sections or change section names.
- The output should be a standalone reference document for an AI agent resuming work on this repo.

--- README ---
{readme_section}

--- CLAUDE.md ---
{claude_md_section}

--- Package Info ({owner_repo}) ---
{package_section}

--- ADR Files ---
{adr_section}

--- Last 5 Merged PRs ---
{prs_text}

Now produce the 7-section digest for {owner_repo}:"""


def bootstrap_repo(owner_repo: str) -> bool:
    """Harvest repo data, synthesize via research agent, and ingest into the second brain."""
    try:
        log.info("Harvesting data for %s ...", owner_repo)
        data = harvest_repo_data(owner_repo)

        prompt = compose_synthesis_prompt(owner_repo, data)

        log.info("Calling research agent for %s ...", owner_repo)
        result = brain_http.call_agent("research", prompt)

        content = (result or {}).get("content", "")
        if not content or not content.strip():
            log.warning("Research agent returned empty content for %s", owner_repo)
            return False

        slug = owner_repo.lower().replace("/", "-")
        ingest_msg = f"file: repos/{slug}.md\n{content}"

        log.info("Ingesting digest for %s as repos/%s.md ...", owner_repo, slug)
        brain_http.call_agent("ingest", ingest_msg)

        log.info("Bootstrap complete for %s", owner_repo)
        return True

    except Exception as exc:
        log.error("Failed to bootstrap %s: %s", owner_repo, exc)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cold-start bootstrap: harvest a repo and populate its second-brain digest."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--repo",
        metavar="OWNER/REPO",
        help="Single repo to bootstrap (e.g. acme/my-service)",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Bootstrap all active repos in the workshop registry",
    )
    args = parser.parse_args()

    if args.repo:
        bootstrap_repo(args.repo)
    elif args.all:
        repos = list_active_repos()
        if not repos:
            log.warning("No active repos found in registry.")
        for entry in repos:
            owner_repo = entry["full_name"]
            bootstrap_repo(owner_repo)

    sys.exit(0)


if __name__ == "__main__":
    main()
