# Deploy location: /opt/ultra-workshop/hermes-skills/workshop_reviewer.py
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from workshop.reviewer import review_query  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic workshop reviewer")
    parser.add_argument("--query", type=str, default="", help="Reviewer query JSON")
    parser.add_argument("--dry-run", action="store_true", help="Emit hardcoded dry-run review and exit 0")
    args = parser.parse_args()

    if args.dry_run:
        print(
            json.dumps(
                {
                    "passed": True,
                    "feedback": "dry-run review passed",
                    "blocking_issues": [],
                }
            ),
            flush=True,
        )
        sys.exit(0)

    if not args.query:
        print("[workshop_reviewer] ERROR: --query is required unless --dry-run is set", file=sys.stderr, flush=True)
        sys.exit(1)

    try:
        review = review_query(args.query)
    except Exception as exc:
        print(f"[workshop_reviewer] ERROR: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)

    print(review.model_dump_json(), flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
