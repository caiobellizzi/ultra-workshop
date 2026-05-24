# Deploy location: /opt/ultra-workshop/hermes-skills/workshop_repo.py
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from workshop.repo_registry import (  # noqa: E402
    DEFAULT_OWNER,
    RepoRegistryError,
    canonicalize_repo,
    deactivate_repo,
    entry_from_gh_metadata,
    list_active_repos,
    registry_path,
    upsert_repo,
)


def _gh_env() -> dict[str, str]:
    return {**os.environ, "GH_TOKEN": os.environ.get("GITHUB_PAT", "")}


def _run_gh(args: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        shell=False,
        env=_gh_env(),
    )
    if result.returncode != 0:
        print(f"[workshop_repo] ERROR: gh {' '.join(args)} failed: {result.stderr}", file=sys.stderr, flush=True)
        sys.exit(result.returncode)
    if not result.stdout.strip():
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        print(f"[workshop_repo] ERROR: gh returned non-JSON output: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)


def _repo_metadata(full_name: str) -> dict[str, Any]:
    return _run_gh([
        "repo",
        "view",
        full_name,
        "--json",
        "nameWithOwner,defaultBranchRef,visibility,viewerPermission",
    ])


def _approval(action: str, full_name: str, summary: str) -> None:
    print(
        json.dumps(
            {
                "needs_approval": True,
                "action": action,
                "repo": full_name,
                "summary": summary,
            }
        ),
        flush=True,
    )
    sys.exit(2)


def _print_active_repos(path: str | Path | None) -> None:
    repos = list_active_repos(path)
    if not repos:
        print("No active workshop repos.", flush=True)
        return
    for entry in repos:
        print(
            f"{entry['full_name']} "
            f"(branch={entry.get('default_branch', 'main')}, "
            f"permission={entry.get('viewer_permission', 'UNKNOWN')})",
            flush=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Workshop repo registry command backend")
    parser.add_argument("command", choices=["list", "add", "create", "remove"])
    parser.add_argument("repo", nargs="?", default="")
    parser.add_argument("--approved", action="store_true", help="Mutation already approved by Telegram HITL")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without mutating")
    parser.add_argument("--registry", default="", help="Override registry path for tests")
    args = parser.parse_args()

    path = registry_path(args.registry or None)

    try:
        if args.command == "list":
            _print_active_repos(path)
            return

        if not args.repo:
            print(f"[workshop_repo] ERROR: /repo {args.command} requires a repo argument", file=sys.stderr, flush=True)
            sys.exit(1)

        full_name = canonicalize_repo(args.repo, default_owner=DEFAULT_OWNER)

        if args.dry_run:
            print(f"[dry-run] would {args.command} {full_name}", flush=True)
            return

        if not args.approved:
            verbs = {
                "add": "Register existing GitHub repo",
                "create": "Create private GitHub repo and register it",
                "remove": "Disable repo in workshop registry",
            }
            _approval(args.command, full_name, f"{verbs[args.command]}: {full_name}?")

        if args.command == "add":
            entry = entry_from_gh_metadata(_repo_metadata(full_name), source="add")
            upsert_repo(entry, path)
            print(f"[workshop_repo] added {entry['full_name']}", flush=True)
            return

        if args.command == "create":
            create = subprocess.run(
                ["gh", "repo", "create", full_name, "--private", "--add-readme"],
                capture_output=True,
                text=True,
                shell=False,
                env=_gh_env(),
            )
            if create.returncode != 0:
                print(f"[workshop_repo] ERROR: gh repo create failed: {create.stderr}", file=sys.stderr, flush=True)
                sys.exit(create.returncode)
            entry = entry_from_gh_metadata(_repo_metadata(full_name), source="create")
            upsert_repo(entry, path)
            print(f"[workshop_repo] created {entry['full_name']}", flush=True)
            return

        if args.command == "remove":
            entry = deactivate_repo(full_name, path)
            print(f"[workshop_repo] disabled {entry['full_name']}", flush=True)
            return
    except RepoRegistryError as exc:
        print(f"[workshop_repo] ERROR: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
