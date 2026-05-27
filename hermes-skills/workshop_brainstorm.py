# Deploy location: /opt/ultra-workshop/hermes-skills/workshop_brainstorm.py
from __future__ import annotations

"""
Brainstorm specialist CLI shim.

Thin wrapper that receives task context via --query JSON, calls the
brainstorm-specialist soul via run_specialist, and emits BrainstormResult JSON
to stdout. The multi-turn HITL loop lives in workshop_build.py — this shim
handles exactly one turn (one soul invocation).

D-17: Triggered by /brainstorm command; bypassed by /build.
B1-A / D-18: No turn cap — loop in workshop_build.py continues until approved.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> None:
    parser = argparse.ArgumentParser(description="Workshop brainstorm specialist shim")
    parser.add_argument("--query", type=str, default="", help="Brainstorm query JSON")
    parser.add_argument("--dry-run", action="store_true", help="Emit hardcoded dry-run result and exit 0")
    args = parser.parse_args()

    if args.dry_run:
        print(
            json.dumps(
                {
                    "approved": True,
                    "goal_statement": "dry-run goal statement",
                    "follow_up": None,
                }
            ),
            flush=True,
        )
        sys.exit(0)

    if not args.query:
        print(
            "[workshop_brainstorm] ERROR: --query is required unless --dry-run is set",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)

    try:
        from workshop.orchestrator import run_specialist
        from pydantic import BaseModel

        class BrainstormResult(BaseModel):
            approved: bool
            goal_statement: str
            follow_up: str | None = None

        result = run_specialist("brainstorm-specialist", args.query, BrainstormResult)
    except Exception as exc:
        print(f"[workshop_brainstorm] ERROR: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)

    print(result.model_dump_json(), flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
