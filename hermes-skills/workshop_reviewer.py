# Deploy location: /opt/ultra-workshop/hermes-skills/workshop_reviewer.py
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _get_wave_fns() -> tuple:
    """Load wave_dispatch and _build_merge_report from workshop_build.py module-level.

    Uses exec-based loading to avoid circular imports (workshop_build imports
    from workshop.*, which imports from each other).
    """
    wb_path = Path(__file__).parent / "workshop_build.py"
    source = wb_path.read_text(encoding="utf-8")
    pre_main = source.split("\ndef main(")[0]
    ns: dict = {"__file__": str(wb_path), "__name__": "workshop_build"}
    exec(compile(pre_main, str(wb_path), "exec"), ns)  # noqa: S102
    return ns["wave_dispatch"], ns["_build_merge_report"], ns["load_review_roster"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Workshop wave reviewer")
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
        from workshop.types import Diff, Plan, Review, ReviewIssue, WaveReport

        query = json.loads(args.query)
        task_id = str(query.get("task_id") or "")
        diff = Diff.model_validate(query["diff"])
        plan = Plan.model_validate(query["plan"])

        wave_dispatch, _build_merge_report, load_review_roster = _get_wave_fns()

        roster = load_review_roster()
        wave_reports = wave_dispatch(diff, plan, task_id, roster)
        merge_report = _build_merge_report(wave_reports)

        # Emit as Review for backward compatibility
        review = Review(
            passed=not merge_report.block_push,
            feedback=merge_report.summary,
            blocking_issues=[
                ReviewIssue(file=f.file, problem=f.problem, required_fix=f.required_fix)
                for f in merge_report.critical_findings + merge_report.important_findings
            ],
        )
    except Exception as exc:
        print(f"[workshop_reviewer] ERROR: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)

    print(review.model_dump_json(), flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
