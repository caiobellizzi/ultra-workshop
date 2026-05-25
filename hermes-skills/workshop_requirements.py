# Deploy location: /opt/ultra-workshop/hermes-skills/workshop_requirements.py
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from workshop.requirements_gate import evaluate_requirements


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic workshop requirements gate")
    parser.add_argument("--query", type=str, default="", help="Requirements gate query JSON")
    parser.add_argument("--dry-run", action="store_true", help="Emit hardcoded dry-run decision and exit 0")
    args = parser.parse_args()

    if args.dry_run:
        print(
            json.dumps(
                {
                    "ready": True,
                    "goal": "dry-run",
                    "planning_notes": [],
                    "clarifications": [],
                }
            ),
            flush=True,
        )
        sys.exit(0)

    if not args.query:
        print(
            "[workshop_requirements] ERROR: --query is required unless --dry-run is set",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)

    try:
        result = evaluate_requirements(args.query)
    except Exception as exc:
        print(f"[workshop_requirements] ERROR: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)

    print(result.model_dump_json(), flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
