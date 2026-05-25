# Deploy location: /opt/ultra-workshop/hermes-skills/workshop_planner.py
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # adds /opt/ultra-workshop to sys.path

from workshop.planner import build_plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic workshop planner")
    parser.add_argument("--query", type=str, default="", help="Planner query JSON")
    parser.add_argument("--dry-run", action="store_true", help="Emit hardcoded dry-run plan and exit 0")
    args = parser.parse_args()

    if args.dry_run:
        print(
            json.dumps(
                {
                    "goal": "dry-run",
                    "steps": [{"id": "1", "description": "dry-run step", "files": []}],
                    "affected_files": [],
                }
            ),
            flush=True,
        )
        sys.exit(0)

    if not args.query:
        print("[workshop_planner] ERROR: --query is required unless --dry-run is set", file=sys.stderr, flush=True)
        sys.exit(1)

    try:
        plan = build_plan(args.query)
    except Exception as exc:
        print(f"[workshop_planner] ERROR: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)

    print(plan.model_dump_json(), flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
