# Deploy location: /opt/ultra-workshop/hermes-skills/workshop_merge_agent.py
from __future__ import annotations

"""
Merge agent CLI shim.

Accepts --query JSON with wave_reports array, calls _build_merge_report,
emits MergeReport JSON to stdout. Handles --dry-run.

Following the pattern established by workshop_requirements.py.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> None:
    parser = argparse.ArgumentParser(description="Workshop merge agent — consolidates wave review reports")
    parser.add_argument("--query", type=str, default="", help="Merge agent query JSON with wave_reports array")
    parser.add_argument("--dry-run", action="store_true", help="Emit hardcoded dry-run MergeReport and exit 0")
    args = parser.parse_args()

    if args.dry_run:
        print(
            json.dumps(
                {
                    "block_push": False,
                    "critical_findings": [],
                    "important_findings": [],
                    "auto_fixed": [],
                    "summary": "dry-run: 0 critical, 0 important, 0 auto-fixed",
                }
            ),
            flush=True,
        )
        sys.exit(0)

    if not args.query:
        print(
            "[workshop_merge_agent] ERROR: --query is required unless --dry-run is set",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)

    try:
        import importlib.util
        _WB_PATH = Path(__file__).parent / "workshop_build.py"
        source = _WB_PATH.read_text(encoding="utf-8")
        pre_main = source.split("\ndef main(")[0]
        ns: dict = {"__file__": str(_WB_PATH), "__name__": "workshop_build"}
        exec(compile(pre_main, str(_WB_PATH), "exec"), ns)  # noqa: S102
        _build_merge_report = ns["_build_merge_report"]

        from workshop.types import WaveReport

        query = json.loads(args.query)
        raw_reports = query.get("wave_reports") or []
        wave_reports = [WaveReport.model_validate(r) for r in raw_reports]

        merge_report = _build_merge_report(wave_reports)
    except Exception as exc:
        print(f"[workshop_merge_agent] ERROR: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)

    print(merge_report.model_dump_json(), flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
