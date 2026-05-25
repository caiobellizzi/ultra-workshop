# Deploy location: /opt/ultra-workshop/hermes-skills/workshop_build.py
from __future__ import annotations

import argparse
import base64
import binascii
import json
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, TypeVar

sys.path.insert(0, str(Path(__file__).parent.parent))  # adds /opt/ultra-workshop to sys.path

T = TypeVar("T")

_STAGE_INDEX = {
    "triage": 0,
    "requirements": 1,
    "planner": 2,
    "coder": 3,
    "reviewer": 4,
    "approval": 5,
}


class StageTimeoutForHITL(RuntimeError):
    def __init__(self, stage: str, attempt: int, reason: str):
        self.stage = stage
        self.attempt = attempt
        self.reason = reason
        super().__init__(reason)


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
    if isinstance(payload, dict) and "user_responses" in payload:
        answers = payload.get("user_responses") or []
        return [_stringify_clarification(item) for item in answers if _stringify_clarification(item)]
    normalized = _stringify_clarification(payload)
    return [normalized] if normalized else []


def _decode_b64_arg(value: str, label: str) -> str:
    try:
        return base64.b64decode(value.encode("ascii"), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        print(f"[workshop] invalid {label}: {exc}", flush=True)
        sys.exit(1)


def _merge_unique(existing: list[str], new_items: list[str]) -> list[str]:
    merged = list(existing)
    seen = set(merged)
    for item in new_items:
        if item and item not in seen:
            merged.append(item)
            seen.add(item)
    return merged


def _stage_should_run(state: dict[str, Any], stage: str) -> bool:
    next_stage = str(state.get("next_stage") or "triage")
    return _STAGE_INDEX[stage] >= _STAGE_INDEX.get(next_stage, 0)


def _stage_policy_payload(state: dict[str, Any], stage: str, stage_policy: Callable[[str], Any]) -> dict[str, Any]:
    policy = stage_policy(stage)
    overrides = (state.get("stage_overrides") or {}).get(stage) or {}
    timeout = int(overrides.get("timeout") or policy.timeout)
    tool_timeout = overrides.get("tool_timeout")
    if tool_timeout is None:
        tool_timeout = policy.tool_timeout

    payload: dict[str, Any] = {
        "timeout": timeout,
        "auto_retries": policy.auto_retries,
        "hitl_on_timeout": policy.hitl_on_timeout,
    }
    if tool_timeout is not None:
        payload["tool_timeout"] = int(tool_timeout)
    return payload


def _is_timeout_failure(exc: Exception) -> bool:
    return (
        getattr(exc, "returncode", None) == 124
        or "timed out" in str(getattr(exc, "stderr", "")).lower()
        or "timeout" in str(getattr(exc, "stderr", "")).lower()
    )


def _timeout_recovery_payload(task_id: str, stage: str, attempt: int, reason: str) -> dict[str, Any]:
    return {
        "needs_approval": True,
        "hitl_type": "timeout_recovery",
        "task_id": task_id,
        "stage": stage,
        "attempt": attempt,
        "reason": reason,
        "summary": (
            f"The {stage} stage timed out on attempt {attempt}. "
            "Choose a human-approved recovery path before more expensive coding work runs."
        ),
        "options": [
            "1. Re-enter planning with a smaller first vertical slice",
            "2. Increase the bounded coder timeout for this task and retry coder",
            "3. Re-enter planning with a simplified goal",
            "4. Stop this workflow",
        ],
        "allow_free_text": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Workshop build pipeline entry point")
    parser.add_argument("--repo", type=str, default="", help="Target repo, shorthand allowed (e.g. my-app)")
    parser.add_argument("--task", type=str, default="", help="Task description")
    parser.add_argument("--task-file", type=str, default="", help="Path containing the task description")
    parser.add_argument("--task-b64", type=str, default="", help="Base64-encoded UTF-8 task description")
    parser.add_argument("--task-id", type=str, default="", help="Existing task ID to resume")
    parser.add_argument("--clarifications-file", type=str, default="", help="Path containing human clarification answers")
    parser.add_argument("--resume", action="store_true", help="Resume an existing task from state.json")
    parser.add_argument("--session-id", type=str, default="", help="Hermes session ID")
    parser.add_argument("--chat-id", type=str, default="7113965359", help="Telegram chat ID")
    parser.add_argument("--dry-run", action="store_true", help="Print dry-run message and exit 0")
    args = parser.parse_args()

    if args.task_file:
        try:
            task = Path(args.task_file).read_text(encoding="utf-8").rstrip("\n")
        except OSError as exc:
            print(f"[workshop] task file error: {exc}", flush=True)
            sys.exit(1)
    elif args.task_b64:
        task = _decode_b64_arg(args.task_b64, "--task-b64").rstrip("\n")
    else:
        task = args.task

    if args.dry_run:
        if not args.repo:
            print(_usage_with_repos(), flush=True)
        print("[dry-run] would run workshop pipeline", flush=True)
        print(f"[dry-run] repo: {args.repo!r}", flush=True)
        print(f"[dry-run] task: {task!r}", flush=True)
        print(f"[dry-run] task_id: {args.task_id!r}", flush=True)
        print(f"[dry-run] resume: {args.resume!r}", flush=True)
        sys.exit(0)

    # Import workshop modules AFTER dry-run check so --dry-run works even without workshop/
    from pydantic import BaseModel

    from workshop.cost import BudgetExhausted, check_circuit_breaker
    from workshop.ledger import append_progress, write_task_ledger
    from workshop.orchestrator import ClarificationNeeded, SpecialistFailed, run_specialist
    from workshop.requirements_gate import RequirementsDecision, build_planning_context
    from workshop.repo_registry import RepoRegistryError, mark_last_used, validate_active_repo
    from workshop.stage_policy import stage_policy
    from workshop.state import load_task_state, new_task_state, save_task_state, state_exists
    from workshop.types import Diff, Plan, Review

    class TriageResult(BaseModel):
        task_type: str
        summary: str
        complexity: str

    def run_stage(stage: str, skill_name: str, query_json: str, output_schema: type[T]) -> T:
        policy_data = _stage_policy_payload(state, stage, stage_policy)
        auto_retries = int(policy_data["auto_retries"])
        for retry_index in range(auto_retries + 1):
            attempts = state.setdefault("attempts", {})
            attempt = int(attempts.get(stage, 0)) + 1
            attempts[stage] = attempt
            save_task_state(state)
            try:
                return run_specialist(
                    skill_name,
                    query_json,
                    output_schema,
                    timeout=int(policy_data["timeout"]),
                )
            except subprocess.TimeoutExpired as exc:
                reason = f"Specialist {skill_name!r} timed out after {policy_data['timeout']}s"
                if policy_data["hitl_on_timeout"]:
                    raise StageTimeoutForHITL(stage, attempt, reason) from exc
                if retry_index >= auto_retries:
                    raise
                append_progress(task_id, "stage_retry", {"stage": stage, "attempt": attempt, "reason": reason})
            except SpecialistFailed as exc:
                if policy_data["hitl_on_timeout"] and _is_timeout_failure(exc):
                    reason = f"Specialist {skill_name!r} timed out or exited 124: {exc.stderr[:500]}"
                    raise StageTimeoutForHITL(stage, attempt, reason) from exc
                raise
        raise RuntimeError(f"stage {stage!r} exhausted without result")

    if args.resume and not args.task_id:
        print("[workshop] --resume requires --task-id", flush=True)
        sys.exit(1)

    task_id = args.task_id or f"ws-{secrets.token_hex(3)}"
    should_load_state = bool(args.resume or (args.task_id and state_exists(task_id)))
    if should_load_state:
        try:
            state = load_task_state(task_id)
        except FileNotFoundError as exc:
            print(f"[workshop] {exc}", flush=True)
            sys.exit(1)
        goal = str(state.get("goal") or task)
        if not goal:
            print(f"[workshop] state for {task_id} is missing goal", flush=True)
            sys.exit(1)
    else:
        goal = task
        state = new_task_state(
            task_id,
            goal=goal,
            repo=args.repo,
            session_id=args.session_id,
            chat_id=args.chat_id,
        )

    if not goal:
        print("[workshop] task description is required", flush=True)
        sys.exit(1)

    clarifications = _load_clarifications(args.clarifications_file)
    if clarifications:
        state["clarifications"] = _merge_unique(list(state.get("clarifications") or []), clarifications)
        state["status"] = "running"
        state["next_stage"] = "requirements"
        append_progress(task_id, "clarification_received", {"count": len(clarifications)})

    repo_arg = args.repo or str(state.get("repo") or "")
    repo_entry = state.get("repo_entry") if isinstance(state.get("repo_entry"), dict) else {}
    if not repo_arg and repo_entry:
        repo_arg = str(repo_entry.get("full_name") or "")
    if not repo_arg:
        print(_usage_with_repos(), flush=True)
        sys.exit(1)

    if not repo_entry or args.repo:
        try:
            repo_entry = mark_last_used(repo_arg)
        except RepoRegistryError as exc:
            print(f"[workshop] repo rejected: {exc}", flush=True)
            sys.exit(1)
        except OSError:
            try:
                repo_entry = validate_active_repo(repo_arg)
            except RepoRegistryError as exc:
                print(f"[workshop] repo rejected: {exc}", flush=True)
                sys.exit(1)

    repo_full_name = str(repo_entry["full_name"])
    default_branch = str(repo_entry.get("default_branch", "main"))
    state["repo"] = repo_arg
    state["repo_entry"] = repo_entry
    state["repo_full_name"] = repo_full_name
    state["default_branch"] = default_branch

    if state.get("next_stage") == "approval" and state.get("approval_payload"):
        state["status"] = "needs_approval"
        save_task_state(state)
        print(json.dumps(state["approval_payload"]), flush=True)
        sys.exit(2)

    state["status"] = "running"
    save_task_state(state)

    try:
        check_circuit_breaker()
    except BudgetExhausted as exc:
        print(f"[workshop] budget exhausted: {exc}", flush=True)
        sys.exit(1)

    write_task_ledger(task_id, goal=goal, status="running")

    try:
        stages = state.setdefault("stages", {})
        repo_context = f"Target repo: {repo_full_name}; base branch: {default_branch}"

        if _stage_should_run(state, "triage") or "triage" not in stages:
            triage_query = json.dumps({"task_id": task_id, "goal": goal, "context": repo_context})
            triage_raw = run_stage("triage", "triage-specialist", triage_query, TriageResult)
            stages["triage"] = triage_raw.model_dump()
            state["next_stage"] = "requirements"
            save_task_state(state)
            append_progress(task_id, "triage_complete", {"task_type": triage_raw.task_type, "repo": repo_full_name})
            print("[workshop] triage_complete done", flush=True)
        else:
            triage_raw = TriageResult.model_validate(stages["triage"])

        if _stage_should_run(state, "requirements") or "requirements" not in stages:
            requirements_query = json.dumps(
                {
                    "task_id": task_id,
                    "goal": goal,
                    "context": repo_context,
                    "repo": repo_entry,
                    "clarifications": state.get("clarifications") or [],
                }
            )
            requirements = run_stage("requirements", "requirements-specialist", requirements_query, RequirementsDecision)
            stages["requirements"] = requirements.model_dump()
            state["clarifications"] = _merge_unique(
                list(state.get("clarifications") or []),
                list(requirements.clarifications or []),
            )
            state["next_stage"] = "planner"
            save_task_state(state)
            append_progress(task_id, "requirements_complete", {"ready": requirements.ready})
            print("[workshop] requirements_complete done", flush=True)
        else:
            requirements = RequirementsDecision.model_validate(stages["requirements"])

        scope_instruction = str(state.get("scope_instruction") or "").strip()
        planner_goal = goal
        if scope_instruction:
            planner_goal = f"{goal}\n\nScope for this pass: {scope_instruction}"

        planning_context = build_planning_context(repo_context, requirements.clarifications)
        if _stage_should_run(state, "planner") or "planner" not in stages:
            planner_query = json.dumps({
                "task_id": task_id,
                "goal": planner_goal,
                "triage_result": triage_raw.model_dump(),
                "context": planning_context,
                "repo": repo_entry,
                "requirements_result": requirements.model_dump(),
                "clarifications": requirements.clarifications,
                "scope_instruction": scope_instruction,
            })
            plan = run_stage("planner", "planner-specialist", planner_query, Plan)
            stages["planner"] = plan.model_dump()
            state["next_stage"] = "coder"
            save_task_state(state)
            append_progress(task_id, "plan_complete", {"steps": len(plan.steps)})
            print("[workshop] plan_complete done", flush=True)
        else:
            plan = Plan.model_validate(stages["planner"])

        diff: Diff | None = None
        review: Review | None = None
        if "diff" in stages and not _stage_should_run(state, "coder"):
            diff = Diff.model_validate(stages["diff"])
        if "review" in stages and not _stage_should_run(state, "reviewer"):
            review = Review.model_validate(stages["review"])

        max_review_attempts = 3
        while True:
            current_review_attempts = int(state.setdefault("attempts", {}).get("reviewer", 0))
            if current_review_attempts >= max_review_attempts and review is not None and not review.passed:
                state["status"] = "review_failed"
                state["next_stage"] = "reviewer"
                save_task_state(state)
                write_task_ledger(task_id, goal, status="review_failed")
                print(f"[workshop] review failed after {max_review_attempts} attempts: {review.feedback}", flush=True)
                sys.exit(1)

            if _stage_should_run(state, "coder") or diff is None:
                coder_policy = _stage_policy_payload(state, "coder", stage_policy)
                coder_payload = {
                    "task_id": task_id,
                    "plan": plan.model_dump(),
                    "workspace_dir": diff.workspace_dir if diff else "",
                    "repo": repo_entry,
                    "clarifications": requirements.clarifications,
                    "stage_policy": coder_policy,
                }
                if review is not None and not review.passed:
                    coder_payload["previous_review"] = review.model_dump()
                coder_query = json.dumps(coder_payload)
                diff = run_stage("coder", "coder-specialist", coder_query, Diff)
                stages["diff"] = diff.model_dump()
                state["next_stage"] = "reviewer"
                save_task_state(state)
                append_progress(task_id, "coder_complete", {"branch": diff.branch, "attempt": state["attempts"]["coder"]})
                print("[workshop] coder_complete done", flush=True)

            if _stage_should_run(state, "reviewer") or review is None:
                reviewer_query = json.dumps({
                    "task_id": task_id,
                    "plan": plan.model_dump(),
                    "diff": diff.model_dump(),
                    "context": planning_context,
                    "repo": repo_entry,
                    "clarifications": requirements.clarifications,
                })
                review = run_stage("reviewer", "reviewer-specialist", reviewer_query, Review)
                stages["review"] = review.model_dump()
                save_task_state(state)
                append_progress(task_id, "review_complete", {"passed": review.passed, "attempt": state["attempts"]["reviewer"]})
                print("[workshop] review_complete done", flush=True)

            if review.passed:
                break

            stages.pop("diff", None)
            diff = None
            state["next_stage"] = "coder"
            save_task_state(state)

    except ClarificationNeeded as clarification:
        request = clarification.request
        state["status"] = "needs_clarification"
        state["next_stage"] = "requirements"
        state["clarification_request"] = request.model_dump()
        save_task_state(state)
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
    except StageTimeoutForHITL as timeout:
        payload = _timeout_recovery_payload(task_id, timeout.stage, timeout.attempt, timeout.reason)
        state["status"] = "needs_timeout_recovery"
        state["next_stage"] = timeout.stage
        state["timeout_payload"] = payload
        save_task_state(state)
        write_task_ledger(task_id, goal, status="needs_timeout_recovery")
        append_progress(task_id, "timeout_recovery_requested", {"stage": timeout.stage, "attempt": timeout.attempt})
        print(json.dumps(payload), flush=True)
        sys.exit(2)

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
    state["status"] = "needs_approval"
    state["next_stage"] = "approval"
    state["approval_payload"] = hitl_payload
    save_task_state(state)
    write_task_ledger(task_id, goal, status="needs_approval")
    print(json.dumps(hitl_payload), flush=True)
    sys.exit(2)


if __name__ == "__main__":
    main()
