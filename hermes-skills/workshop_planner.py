# Deploy location: /opt/ultra-workshop/hermes-skills/workshop_planner.py
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # adds /opt/ultra-workshop to sys.path

from workshop.planner import build_plan

try:
    import brain_http as _brain_http  # type: ignore[import]
except ImportError:
    _brain_http = None  # type: ignore[assignment]


def _inject_brain_context(query_json: str) -> str:
    """Enrich planner query with brain context (repo conventions + ADRs). Fail-open."""
    if _brain_http is None:
        return query_json
    try:
        query = json.loads(query_json)
        repo_full_name = str((query.get("repo") or {}).get("full_name") or "")
        if not repo_full_name:
            return query_json
        result = _brain_http.call_agent("query", f"repo conventions and relevant ADRs for {repo_full_name}")
        brain_content = str(result.get("content") or "")
        if brain_content:
            query["context"] = (query.get("context") or "") + "\n\n" + brain_content
        return json.dumps(query)
    except Exception:
        return query_json


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
