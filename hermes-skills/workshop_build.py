# Deploy location: /opt/ultra-workshop/hermes-skills/workshop_build.py
from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # adds /opt/ultra-workshop to sys.path


def _usage_with_repos() -> str:
    try:
        from workshop.repo_registry import list_active_repos

        repos = list_active_repos()
        if repos:
            active = "\n".join(f"  - {r['full_name']}" for r in repos)
        else:
            active = "  (none)"
    except Exception as exc:
        active = f"  (active repo list unavailable: {exc})"
    return "Usage: /build --repo <repo> <task>\n\nActive repos:\n" + active


def _stringify_clarification(item: object) -> str:
    if isinstance(item, dict):
        question = str(item.get("question") or item.get("prompt") or "").strip()
        answer = str(item.get("answer") or item.get("response") or item.get("value") or "").strip()
        if question and answer:
            return f"{question}: {answer}"
        return json.dumps(item, sort_keys=True)
    return str(item).strip()


def _load_clarifications(path: str) -> list[str]:
    if not path:
        return []
    try:
        text = Path(path).read_text(encoding="utf-8").strip()
    except OSError as exc:
        print(f"[workshop] clarification file error: {exc}", flush=True)
        sys.exit(1)

    if not text:
        return []

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return [text]

    if isinstance(payload, list):
        return [_stringify_clarification(item) for item in payload if _stringify_clarification(item)]
    if isinstance(payload, dict) and "answers" in payload:
        answers = payload.get("answers") or []
        return [_stringify_clarification(item) for item in answers if _stringify_clarification(item)]
    normalized = _stringify_clarification(payload)
    return [normalized] if normalized else []


def main() -> None:
    parser = argparse.ArgumentParser(description="Workshop build pipeline entry point")
    parser.add_argument("--repo", type=str, default="", help="Target repo, shorthand allowed (e.g. my-app)")
    parser.add_argument("--task", type=str, default="", help="Task description")
    parser.add_argument("--task-file", type=str, default="", help="Path containing the task description")
    parser.add_argument("--task-id", type=str, default="", help="Existing task ID to resume after clarification")
    parser.add_argument("--clarifications-file", type=str, default="", help="Path containing human clarification answers")
    parser.add_argument("--session-id", type=str, default="", help="Hermes session ID")
    parser.add_argument("--chat-id", type=str, default="7113965359", help="Telegram chat ID")
    parser.add_argument("--dry-run", action="store_true", help="Print dry-run message and exit 0")
    args = parser.parse_args()

    task = args.task
    if args.task_file:
        try:
            task = Path(args.task_file).read_text(encoding="utf-8").rstrip("\n")
        except OSError as exc:
            print(f"[workshop] task file error: {exc}", flush=True)
            sys.exit(1)

    if args.dry_run:
        if not args.repo:
            print(_usage_with_repos(), flush=True)
        print("[dry-run] would run workshop pipeline", flush=True)
        print(f"[dry-run] repo: {args.repo!r}", flush=True)
        print(f"[dry-run] task: {task!r}", flush=True)
        print(f"[dry-run] task_id: {args.task_id!r}", flush=True)
        sys.exit(0)

    # Import workshop modules AFTER dry-run check so --dry-run works even without workshop/
    from pydantic import BaseModel

    from workshop.cost import BudgetExhausted, check_circuit_breaker
    from workshop.ledger import append_progress, write_task_ledger
    from workshop.orchestrator import ClarificationNeeded, run_specialist
    from workshop.requirements_gate import RequirementsDecision, build_planning_context
    from workshop.repo_registry import RepoRegistryError, mark_last_used, validate_active_repo
    from workshop.types import Diff, Plan, Review

    class TriageResult(BaseModel):
        task_type: str
        summary: str
        complexity: str

    task_id = args.task_id or f"ws-{secrets.token_hex(3)}"
    goal = task
    clarifications = _load_clarifications(args.clarifications_file)

    if not args.repo:
        print(_usage_with_repos(), flush=True)
        sys.exit(1)

    try:
        repo_entry = mark_last_used(args.repo)
    except RepoRegistryError as exc:
        print(f"[workshop] repo rejected: {exc}", flush=True)
        sys.exit(1)
    except OSError:
        try:
            repo_entry = validate_active_repo(args.repo)
        except RepoRegistryError as exc:
            print(f"[workshop] repo rejected: {exc}", flush=True)
            sys.exit(1)

    repo_full_name = repo_entry["full_name"]
    default_branch = repo_entry.get("default_branch", "main")

    try:
        check_circuit_breaker()
    except BudgetExhausted as exc:
        print(f"[workshop] budget exhausted: {exc}", flush=True)
        sys.exit(1)

    write_task_ledger(task_id, goal=goal, status="running")
    if clarifications:
        append_progress(task_id, "clarification_received", {"count": len(clarifications)})

    try:
        # Stage 1: triage
        repo_context = f"Target repo: {repo_full_name}; base branch: {default_branch}"
        triage_query = json.dumps({"task_id": task_id, "goal": goal, "context": repo_context})
        triage_raw = run_specialist("triage-specialist", triage_query, TriageResult)
        append_progress(task_id, "triage_complete", {"task_type": triage_raw.task_type, "repo": repo_full_name})
        print("[workshop] triage_complete done", flush=True)

        # Stage 2: requirements gate
        requirements_query = json.dumps(
            {
                "task_id": task_id,
                "goal": goal,
                "context": repo_context,
                "repo": repo_entry,
                "clarifications": clarifications,
            }
        )
        requirements = run_specialist("requirements-specialist", requirements_query, RequirementsDecision)
        append_progress(task_id, "requirements_complete", {"ready": requirements.ready})
        print("[workshop] requirements_complete done", flush=True)

        # Stage 3: planner
        planning_context = build_planning_context(repo_context, requirements.clarifications)
        planner_query = json.dumps({
            "task_id": task_id,
            "goal": goal,
            "triage_result": triage_raw.model_dump(),
            "context": planning_context,
            "repo": repo_entry,
            "requirements_result": requirements.model_dump(),
            "clarifications": requirements.clarifications,
        })
        plan = run_specialist("planner-specialist", planner_query, Plan)
        append_progress(task_id, "plan_complete", {"steps": len(plan.steps)})
        print("[workshop] plan_complete done", flush=True)

        # Stage 4+5: coder + reviewer with retry (max 2 retries = 3 attempts)
        diff: Diff | None = None
        review: Review | None = None
        for attempt in range(3):
            coder_payload = {
                "task_id": task_id,
                "plan": plan.model_dump(),
                "workspace_dir": diff.workspace_dir if diff else "",
                "repo": repo_entry,
                "clarifications": requirements.clarifications,
            }
            if attempt > 0 and review is not None and not review.passed:
                coder_payload["previous_review"] = review.model_dump()
            coder_query = json.dumps(coder_payload)
            diff = run_specialist("coder-specialist", coder_query, Diff)
            append_progress(task_id, "coder_complete", {"branch": diff.branch, "attempt": attempt})
            print("[workshop] coder_complete done", flush=True)

            reviewer_query = json.dumps({
                "task_id": task_id,
                "plan": plan.model_dump(),
                "diff": diff.model_dump(),
                "context": planning_context,
                "repo": repo_entry,
                "clarifications": requirements.clarifications,
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
    except ClarificationNeeded as clarification:
        request = clarification.request
        write_task_ledger(task_id, goal, status="needs_clarification")
        append_progress(task_id, "clarification_requested", {"source_stage": request.source_stage})
        payload = {
            "needs_approval": True,
            "hitl_type": "clarification",
            "task_id": task_id,
            "source_stage": request.source_stage,
            "reason": request.reason,
            "questions": [question.model_dump() for question in request.questions],
            "options": request.options,
            "allow_free_text": request.allow_free_text,
            "evidence": request.evidence,
            "summary": request.summary or f"Clarification needed: {request.reason}",
        }
        print(json.dumps(payload), flush=True)
        sys.exit(2)

    # HITL gate — exit code 2: SKILL.md body catches this and calls clarify
    hitl_payload = {
        "needs_approval": True,
        "hitl_type": "approval",
        "task_id": task_id,
        "branch": diff.branch,
        "workspace_dir": diff.workspace_dir,
        "repo_full_name": repo_full_name,
        "default_branch": default_branch,
        "plan_goal": plan.goal,
        "diff_summary": diff.summary,
        "summary": (
            f"Review passed for {repo_full_name} ({default_branch}). "
            f"Push branch {diff.branch!r} and open PR for: {plan.goal}?"
        ),
    }
    print(json.dumps(hitl_payload), flush=True)
    sys.exit(2)


if __name__ == "__main__":
    main()
