# Deploy location: /opt/ultra-workshop/hermes-skills/workshop_build.py
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # adds /opt/ultra-workshop to sys.path


def main() -> None:
    parser = argparse.ArgumentParser(description="Workshop build pipeline entry point")
    parser.add_argument("--task", type=str, default="", help="Task description")
    parser.add_argument("--session-id", type=str, default="", help="Hermes session ID")
    parser.add_argument("--chat-id", type=str, default="7113965359", help="Telegram chat ID")
    parser.add_argument("--dry-run", action="store_true", help="Print dry-run message and exit 0")
    args = parser.parse_args()

    if args.dry_run:
        print("[dry-run] would run workshop pipeline", flush=True)
        print(f"[dry-run] task: {args.task!r}", flush=True)
        sys.exit(0)

    # Import workshop modules AFTER dry-run check so --dry-run works even without workshop/
    from pydantic import BaseModel

    from workshop.cost import BudgetExhausted, check_circuit_breaker
    from workshop.ledger import append_progress, write_task_ledger
    from workshop.orchestrator import run_specialist
    from workshop.types import Diff, Plan, Review

    class TriageResult(BaseModel):
        task_type: str
        summary: str
        complexity: str

    task_id = f"ws-{secrets.token_hex(3)}"
    goal = args.task

    try:
        check_circuit_breaker()
    except BudgetExhausted as exc:
        print(f"[workshop] budget exhausted: {exc}", flush=True)
        sys.exit(1)

    write_task_ledger(task_id, goal=goal, status="running")

    # Stage 1: triage
    triage_query = json.dumps({"task_id": task_id, "goal": goal, "context": ""})
    triage_raw = run_specialist("triage-specialist", triage_query, TriageResult)
    append_progress(task_id, "triage_complete", {"task_type": triage_raw.task_type})
    print("[workshop] triage_complete done", flush=True)

    # Stage 2: planner
    planner_query = json.dumps({
        "task_id": task_id,
        "goal": goal,
        "triage_result": triage_raw.model_dump(),
        "context": "",
    })
    plan = run_specialist("planner-specialist", planner_query, Plan)
    append_progress(task_id, "plan_complete", {"steps": len(plan.steps)})
    print("[workshop] plan_complete done", flush=True)

    # Stage 3+4: coder + reviewer with retry (max 2 retries = 3 attempts)
    diff: Diff | None = None
    review: Review | None = None
    for attempt in range(3):
        coder_query = json.dumps({
            "task_id": task_id,
            "plan": plan.model_dump(),
            "workspace_dir": diff.workspace_dir if diff else "",
        })
        diff = run_specialist("coder-specialist", coder_query, Diff)
        append_progress(task_id, "coder_complete", {"branch": diff.branch, "attempt": attempt})
        print("[workshop] coder_complete done", flush=True)

        reviewer_query = json.dumps({
            "task_id": task_id,
            "plan": plan.model_dump(),
            "diff": diff.model_dump(),
            "context": "",
        })
        review = run_specialist("reviewer-specialist", reviewer_query, Review)
        append_progress(task_id, "review_complete", {"passed": review.passed, "attempt": attempt})
        print("[workshop] review_complete done", flush=True)

        if review.passed:
            break
        if attempt == 2:
            write_task_ledger(task_id, goal, status="review_failed")
            print(f"[workshop] review failed after 3 attempts: {review.feedback}", flush=True)
            sys.exit(1)

    # HITL gate — exit code 2: SKILL.md body catches this and calls clarify
    hitl_payload = {
        "needs_approval": True,
        "task_id": task_id,
        "branch": diff.branch,
        "workspace_dir": diff.workspace_dir,
        "plan_goal": plan.goal,
        "diff_summary": diff.summary,
        "summary": f"Review passed. Push branch {diff.branch!r} and open PR for: {plan.goal}?",
    }
    print(json.dumps(hitl_payload), flush=True)
    sys.exit(2)


if __name__ == "__main__":
    main()
