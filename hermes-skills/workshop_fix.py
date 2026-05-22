# Deploy location: /opt/ultra-workshop/hermes-skills/workshop_fix.py
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Workshop fix pipeline entry point — fetches a GitHub issue and runs the build pipeline")
    parser.add_argument("--issue-url", type=str, required=True, help="GitHub issue URL")
    parser.add_argument("--session-id", type=str, default="", help="Hermes session ID")
    parser.add_argument("--chat-id", type=str, default="7113965359", help="Telegram chat ID")
    parser.add_argument("--dry-run", action="store_true", help="Print dry-run message and exit 0")
    args = parser.parse_args()

    if args.dry_run:
        print("[dry-run] would fetch issue and run workshop pipeline", flush=True)
        print(f"[dry-run] issue-url: {args.issue_url!r}", flush=True)
        sys.exit(0)

    # Fetch issue body via gh CLI
    import os

    result = subprocess.run(
        ["gh", "issue", "view", args.issue_url, "--json", "title,body,number"],
        capture_output=True,
        text=True,
        shell=False,
        env={**os.environ, "GH_TOKEN": os.environ.get("GITHUB_PAT", "")},
    )
    if result.returncode != 0:
        print(f"[workshop_fix] ERROR: gh issue view failed: {result.stderr}", flush=True)
        sys.exit(1)

    issue = json.loads(result.stdout)
    task = f"Fix issue #{issue['number']}: {issue['title']}\n\n{issue['body'][:500]}"

    # Delegate to workshop_build.py — inherit stdout/stderr so SKILL.md sees exit code 2
    build_result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parent / "workshop_build.py"),
            "--task", task,
            "--session-id", args.session_id,
            "--chat-id", args.chat_id,
        ],
        capture_output=False,
        shell=False,
    )
    sys.exit(build_result.returncode)  # propagate exit code 2 to SKILL.md


if __name__ == "__main__":
    main()
