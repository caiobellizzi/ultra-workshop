# Deploy location: /opt/ultra-workshop/hermes-skills/workshop_build.py
from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import re
import secrets
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, TypeVar

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))  # adds /opt/ultra-workshop to sys.path

# Phase 10 task-level budget caps
UWS_TASK_BUDGET = int(os.environ.get("UWS_TASK_BUDGET", "2400"))
MAX_STEPS = 20
DECOMPOSE_DEPTH_MAX = 1

T = TypeVar("T")

_STAGE_INDEX = {
    "brainstorm": 0,
    "triage": 1,
    "requirements": 2,
    "planner": 3,
    "coder": 4,
    "reviewer": 5,
    "approval": 6,
}

# Path to review roster config (T-09-03-01: fail-safe if missing)
_REVIEW_ROSTER_PATH = Path("/opt/ultra-workshop/hermes-config/review-roster.yaml")
# Fallback roster used when YAML is missing/malformed — security never silently skipped
_FALLBACK_ROSTER: list[dict] = [
    {"role": "correctness", "model_alias": "reviewer-model", "isolation": True, "file_patterns": [], "monthly_budget_cents": 3000, "fallback_model_alias": None},
    {"role": "security", "model_alias": "reviewer-model", "isolation": True, "file_patterns": [], "monthly_budget_cents": 4000, "fallback_model_alias": None},
]


def load_review_roster() -> list[dict]:
    """Load the review roster from hermes-config/review-roster.yaml.

    T-09-03-01: If the file is missing or malformed, returns the fallback roster
    which always contains correctness and security — security is never silently skipped.
    """
    roster_path = _REVIEW_ROSTER_PATH
    # Allow local override for testing
    local_path = Path(__file__).parent.parent / "hermes-config" / "review-roster.yaml"
    if local_path.exists():
        roster_path = local_path
    try:
        data = yaml.safe_load(roster_path.read_text(encoding="utf-8"))
        reviewers = data.get("reviewers") or []
        if not reviewers:
            raise ValueError("review-roster.yaml has no reviewers entries")
        # Ensure always-on roles (correctness, security) are present
        roles_present = {r["role"] for r in reviewers}
        for fallback_entry in _FALLBACK_ROSTER:
            if fallback_entry["role"] not in roles_present:
                reviewers.insert(0, fallback_entry)
        return reviewers
    except (OSError, yaml.YAMLError, KeyError, TypeError) as exc:
        print(f"[workshop] WARNING: could not load review roster ({exc}); using fallback", file=sys.stderr, flush=True)
        return list(_FALLBACK_ROSTER)


def _select_reviewers(roster: list[dict], diff_files: list[str]) -> list[dict]:
    """Select reviewers to run based on the diff file list.

    Always-on entries (file_patterns == []) are always included.
    Pattern-gated entries are included if any diff file matches any pattern
    (substring or suffix match per D-03).
    """
    selected = []
    for entry in roster:
        patterns = entry.get("file_patterns") or []
        if not patterns:
            # Always-on reviewer
            selected.append(entry)
            continue
        # Extension/path-gated: include if any diff file matches any pattern
        for diff_file in diff_files:
            if any(pat in diff_file for pat in patterns):
                selected.append(entry)
                break
    return selected


def _dedup_findings(findings: list) -> list:
    """Deduplicate findings by (file, line), keeping highest severity.

    Groups by (file, line). For each group, keeps one entry with:
    - highest severity (Critical > Important > Minor)
    - merged required_fix strings
    - first problem statement
    """
    _SEVERITY_ORDER = {"Critical": 3, "Important": 2, "Minor": 1}
    groups: dict[tuple, list] = {}
    for f in findings:
        key = (getattr(f, "file", ""), getattr(f, "line", None))
        groups.setdefault(key, []).append(f)

    result = []
    for group in groups.values():
        if len(group) == 1:
            result.append(group[0])
            continue
        # Pick highest severity
        best = max(group, key=lambda f: _SEVERITY_ORDER.get(f.severity, 0))
        # Merge required_fix strings if different
        fixes = list(dict.fromkeys(f.required_fix for f in group))
        if len(fixes) > 1:
            merged_fix = "; ".join(fixes)
            # Create a new finding with merged fix (Pydantic model_copy)
            if hasattr(best, "model_copy"):
                best = best.model_copy(update={"required_fix": merged_fix})
        result.append(best)
    return result


def _build_merge_report(wave_reports: list) -> Any:
    """Build a MergeReport from a list of WaveReports.

    Collects all findings, deduplicates, splits by severity.
    MergeReport.block_push = True when any Critical findings exist.
    Minor findings go to auto_fixed.
    """
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from workshop.types import MergeReport

    all_findings = []
    for report in wave_reports:
        all_findings.extend(getattr(report, "findings", []) or [])

    deduped = _dedup_findings(all_findings)

    critical = [f for f in deduped if f.severity == "Critical"]
    important = [f for f in deduped if f.severity == "Important"]
    minor = [f for f in deduped if f.severity == "Minor"]

    return MergeReport(
        block_push=len(critical) > 0,
        critical_findings=critical,
        important_findings=important,
        auto_fixed=minor,
        summary=f"{len(critical)} critical, {len(important)} important, {len(minor)} auto-fixed",
    )


def wave_dispatch(diff: Any, plan: Any, task_id: str, roster: list[dict]) -> list:
    """Dispatch parallel reviewer wave using ThreadPoolExecutor(max_workers=8).

    T-09-03-02: Each reviewer has a per-reviewer timeout; wave-level timeout is
    max(per-reviewer) + 60s buffer.

    D-09 budget fallback:
    - security exhausted → raise (block the pipeline)
    - fallback_model_alias present → use it
    - non-critical exhausted → skip + append_audit

    Raises ValueError if roster is empty.
    """
    if not roster:
        raise ValueError("Roster is empty — cannot dispatch review wave")

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from workshop.cost import RoleBudgetExhausted, RoleBudgetWarning, check_role_budget
    from workshop.ledger import append_audit
    from workshop.orchestrator import run_specialist
    from workshop.types import WaveReport

    diff_files = [getattr(c, "path", str(c)) for c in (getattr(diff, "changes", []) or [])]
    selected = _select_reviewers(roster, diff_files)

    if not selected:
        raise ValueError("No reviewers selected after file filtering")

    per_reviewer_timeout = 120  # seconds
    wave_timeout = per_reviewer_timeout + 60

    def _run_one(entry: dict) -> WaveReport:
        role = entry["role"]
        skill_name = f"{role}-reviewer"
        model_alias = entry.get("model_alias", "reviewer-model")

        # D-09 budget check before dispatch
        try:
            check_role_budget(role)
        except RoleBudgetExhausted:
            if role == "security":
                raise  # security exhaustion blocks pipeline
            fallback = entry.get("fallback_model_alias")
            if fallback:
                model_alias = fallback
                print(f"[workshop] role {role!r} exhausted; using fallback model {fallback!r}", file=sys.stderr, flush=True)
            else:
                # Non-critical exhausted, no fallback → skip
                try:
                    append_audit(task_id, "role_budget_skipped", {"role": role})
                except Exception:
                    pass
                return WaveReport(role=role, passed=True, findings=[], tokens_used=0, cost_cents=0.0)
        except RoleBudgetWarning:
            print(f"[workshop] WARNING: role {role!r} approaching budget cap", file=sys.stderr, flush=True)

        reviewer_query = json.dumps({
            "task_id": task_id,
            "role": role,
            "plan": plan.model_dump() if hasattr(plan, "model_dump") else {},
            "diff": diff.model_dump() if hasattr(diff, "model_dump") else {},
            "model_alias": model_alias,
        })

        try:
            result = run_specialist(skill_name, reviewer_query, WaveReport, timeout=per_reviewer_timeout)
            return result
        except Exception as exc:
            # Per-reviewer failure is non-blocking for non-critical roles
            print(f"[workshop] WARNING: {role} reviewer failed: {exc}", file=sys.stderr, flush=True)
            return WaveReport(role=role, passed=True, findings=[], tokens_used=0, cost_cents=0.0)

    results: list[WaveReport] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_run_one, entry): entry for entry in selected}
        for future in as_completed(futures, timeout=wave_timeout):
            try:
                results.append(future.result())
            except RoleBudgetExhausted:
                raise  # re-raise for security budget exhaustion
            except Exception as exc:
                entry = futures[future]
                print(f"[workshop] reviewer {entry['role']!r} future failed: {exc}", file=sys.stderr, flush=True)

    roles_run = [r.role for r in results]
    total_findings = sum(len(r.findings) for r in results)
    try:
        append_audit(task_id, "wave_complete", {"roles": roles_run, "total_findings": total_findings})
    except Exception:
        pass

    return results


class StageTimeoutForHITL(RuntimeError):
    def __init__(self, stage: str, attempt: int, reason: str, step_context: dict | None = None):
        self.stage = stage
        self.attempt = attempt
        self.reason = reason
        self.step_context = step_context or {}
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


def _step_exhausted_hitl_payload(
    task_id: str,
    *,
    step_idx: int,
    step_desc: str,
    decompose_attempted: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "needs_approval": True,
        "hitl_type": "step_retry_exhausted",
        "task_id": task_id,
        "step_idx": step_idx,
        "step_desc": step_desc,
        "decompose_attempted": decompose_attempted,
        "reason": reason,
        "summary": (
            f"Step {step_idx + 1} exhausted retries and auto-decompose on task {task_id}. "
            "Human intervention required to continue."
        ),
        "options": [
            "1. Provide a refined description and retry this step",
            "2. Skip this step and continue from the next",
            "3. Re-enter planning with a smaller goal",
            "4. Stop this workflow",
        ],
        "allow_free_text": True,
    }


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


def _review_retry_exhausted_payload(
    task_id: str,
    *,
    plan_goal: str,
    repo_full_name: str,
    default_branch: str,
    review: Any,
    diff: Any,
) -> dict[str, Any]:
    blocking_issues = []
    if review is not None:
        for item in getattr(review, "blocking_issues", []) or []:
            if hasattr(item, "model_dump"):
                blocking_issues.append(item.model_dump())
            else:
                blocking_issues.append(item)
    return {
        "needs_approval": True,
        "hitl_type": "review_retry_exhausted",
        "task_id": task_id,
        "branch": getattr(diff, "branch", ""),
        "workspace_dir": getattr(diff, "workspace_dir", ""),
        "repo_full_name": repo_full_name,
        "default_branch": default_branch,
        "plan_goal": plan_goal,
        "diff_summary": getattr(diff, "summary", ""),
        "blocking_issues": blocking_issues,
        "summary": (
            f"Review failed after the allowed retry attempts for {repo_full_name}. "
            "Choose whether to accept the current diff with notes, provide more guidance, or abort."
        ),
        "options": [
            "1. Accept current diff with notes and proceed to PR approval",
            "2. Provide guidance and retry from planner",
            "3. Abort this workflow",
        ],
        "allow_free_text": True,
    }


def _extract_doc_reference(text: str) -> str:
    """Return the first *.md filename found in *text*, or empty string."""
    m = re.search(r'\b([\w\-]+\.md)\b', text or "")
    return m.group(1) if m else ""


def _handle_step_retry_exhausted(
    exc: Any,
    state: dict[str, Any],
    task_id: str,
    plan: Any,
    planner_query_template: str,
    run_stage: Any,
    stage_model_alias: Any,
    append_progress: Any,
    save_task_state: Any,
    Diff: Any,
    Plan: Any,
    task_start: float,
) -> Any:
    """Handle StepRetryExhausted escalation from workshop_coder.

    Recovery ladder:
    1. Parse step context from exc.stderr to find step_idx and step_id
    2. If decompose_depth[step_id] < DECOMPOSE_DEPTH_MAX: auto-decompose via planner
    3. Otherwise: raise StageTimeoutForHITL with full context
    """
    from workshop.orchestrator import SpecialistFailed  # local import — only available after workshop/ is on path

    # Extract step context from stderr if available
    stderr_text = str(getattr(exc, "stderr", "") or "")
    step_idx = 0
    step_id = "unknown"
    step_desc = ""

    # Parse step context from StepRetryExhausted repr in stderr
    import re as _re
    _m_idx = _re.search(r"idx=(\d+)", stderr_text)
    if _m_idx:
        step_idx = int(_m_idx.group(1))
    _m_id = _re.search(r"Step\s+(\S+)\s+\(idx=", stderr_text)
    if _m_id:
        step_id = _m_id.group(1)

    # Get step description from plan
    plan_dict = plan.model_dump() if hasattr(plan, "model_dump") else (plan or {})
    steps = plan_dict.get("steps") or []
    if 0 <= step_idx < len(steps):
        step = steps[step_idx]
        step_desc = str(step.get("description") or "") if isinstance(step, dict) else str(getattr(step, "description", ""))
        step_id = str(step.get("id") or step_idx + 1) if isinstance(step, dict) else str(getattr(step, "id", step_idx + 1))

    decompose_depth = state.setdefault("decompose_depth", {})
    current_depth = int(decompose_depth.get(step_id, 0))

    append_progress(task_id, "step_retry_exhausted", {"step_id": step_id, "step_idx": step_idx, "decompose_depth": current_depth})

    # Check global caps before attempting decompose
    elapsed_total = time.monotonic() - task_start
    budget_exceeded = elapsed_total > UWS_TASK_BUDGET

    if current_depth >= DECOMPOSE_DEPTH_MAX or budget_exceeded:
        reason = (
            f"Step {step_id} retry exhausted; decompose_depth={current_depth}>={DECOMPOSE_DEPTH_MAX}"
            if current_depth >= DECOMPOSE_DEPTH_MAX
            else f"UWS_TASK_BUDGET={UWS_TASK_BUDGET}s exceeded before decompose attempt"
        )
        payload = _step_exhausted_hitl_payload(
            task_id,
            step_idx=step_idx,
            step_desc=step_desc,
            decompose_attempted=current_depth > 0,
            reason=reason,
        )
        state["status"] = "needs_step_recovery"
        state["step_recovery_payload"] = payload
        save_task_state(state)
        raise StageTimeoutForHITL(
            "coder",
            state.get("attempts", {}).get("coder", 0),
            reason,
            step_context={"step_idx": step_idx, "step_desc": step_desc, "decompose_attempted": current_depth > 0},
        ) from exc

    # Auto-decompose: call planner to split the failing step into 2-3 sub-steps
    print(f"[workshop] auto-decompose step {step_id} (depth={current_depth} → {current_depth + 1})", flush=True)
    decompose_depth[step_id] = current_depth + 1
    state["decompose_depth"] = decompose_depth
    save_task_state(state)

    goal = plan_dict.get("goal", "")
    decompose_goal = (
        f"{goal}\n\nSplit the following failing step into 2-3 smaller independently "
        f"buildable sub-steps:\n\nFailing step: {step_desc}\n\n"
        "Return a Plan with only the sub-steps for this failing step."
    )
    decompose_query = json.dumps({
        "task_id": task_id,
        "goal": decompose_goal,
        "model_alias": stage_model_alias("planner-specialist"),
        "triage_result": {},
        "context": f"auto-decompose of step {step_id}",
        "repo": state.get("repo_entry") or {},
        "requirements_result": {},
        "clarifications": [],
        "scope_instruction": f"decompose step {step_id} only",
        "workspace_dir": state.get("workspace_dir") or "",
        "reference_doc": "",
    })

    try:
        sub_plan = run_stage("planner", "planner-specialist", decompose_query, Plan)
    except Exception as decompose_exc:
        reason = f"Auto-decompose planner call failed: {decompose_exc}"
        raise StageTimeoutForHITL(
            "coder",
            state.get("attempts", {}).get("coder", 0),
            reason,
            step_context={"step_idx": step_idx, "step_desc": step_desc, "decompose_attempted": True},
        ) from decompose_exc

    # Merge sub-steps into the plan for the coder retry
    new_steps = list(steps[:step_idx]) + sub_plan.steps + list(steps[step_idx + 1:])
    if len(new_steps) > MAX_STEPS:
        reason = f"Decomposed plan has {len(new_steps)} steps > MAX_STEPS={MAX_STEPS}"
        raise StageTimeoutForHITL(
            "coder",
            state.get("attempts", {}).get("coder", 0),
            reason,
            step_context={"step_idx": step_idx, "step_desc": step_desc, "decompose_attempted": True},
        )

    # Build updated plan with sub-steps
    new_plan_dict = dict(plan_dict)
    new_plan_dict["steps"] = [s.model_dump() if hasattr(s, "model_dump") else s for s in new_steps]
    new_plan = Plan.model_validate(new_plan_dict)

    # Run the sub-steps via coder
    from workshop.stage_policy import stage_policy as _stage_policy
    coder_policy = _stage_policy_payload(state, "coder", _stage_policy)
    sub_coder_payload = {
        "task_id": task_id,
        "plan": new_plan.model_dump(),
        "workspace_dir": state.get("workspace_dir") or "",
        "repo": state.get("repo_entry") or {},
        "clarifications": [],
        "stage_policy": coder_policy,
        "model_alias": stage_model_alias("coder-specialist"),
        "current_step": step_idx,  # start from the failing step position
    }
    sub_coder_query = json.dumps(sub_coder_payload)
    try:
        return run_stage("coder", "coder-specialist", sub_coder_query, Diff)
    except SpecialistFailed as sub_exc:
        reason = f"Sub-steps also failed after decompose: {sub_exc}"
        raise StageTimeoutForHITL(
            "coder",
            state.get("attempts", {}).get("coder", 0),
            reason,
            step_context={"step_idx": step_idx, "step_desc": step_desc, "decompose_attempted": True},
        ) from sub_exc


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
    parser.add_argument("--brainstorm", action="store_true", help="Enable brainstorm stage before triage (D-17)")
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

    try:
        from workshop.doc_resolver import resolve_doc as _resolve_doc
    except ImportError:
        def _resolve_doc(*_a, **_kw):  # type: ignore[misc]
            return None

    from workshop.cost import BudgetExhausted, check_circuit_breaker
    from workshop.ledger import append_audit, append_progress, validate_task_id, write_task_ledger
    from workshop.orchestrator import ClarificationNeeded, SpecialistFailed, run_specialist
    from workshop.requirements_gate import RequirementsDecision, build_planning_context
    from workshop.repo_registry import RepoRegistryError, mark_last_used, validate_active_repo
    from workshop.stage_policy import stage_model_alias, stage_policy
    from workshop.state import clone_repo_to_workspace, load_task_state, new_task_state, save_task_state, state_exists
    from workshop.types import Diff, Plan, Review, ReviewIssue

    class TriageResult(BaseModel):
        task_type: str
        summary: str
        complexity: str

    class BrainstormResult(BaseModel):
        approved: bool
        goal_statement: str
        follow_up: str | None = None

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
    try:
        validate_task_id(task_id)
    except ValueError as exc:
        print(f"[workshop] {exc}", flush=True)
        sys.exit(1)
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

    # Clone the repo before any specialist stage so workspace_dir is available.
    # clone_repo_to_workspace skips re-clone if .git already exists (resume path).
    workspace_dir = str(state.get("workspace_dir") or "")
    workspace_missing = bool(workspace_dir) and not (Path(workspace_dir) / ".git").exists()
    if not workspace_dir or workspace_missing:
        clone_repo_to_workspace(state, repo=repo_full_name)
        save_task_state(state)
        from workshop.ledger import append_progress as _ap
        event = "workspace_recloned" if workspace_missing else "workspace_cloned"
        _ap(task_id, event, {"workspace_dir": state["workspace_dir"], "repo": repo_full_name})
        print(f"[workshop] workspace_cloned: {state['workspace_dir']}", flush=True)

    if state.get("next_stage") == "approval" and state.get("approval_payload"):
        state["status"] = "needs_approval"
        save_task_state(state)
        print(json.dumps(state["approval_payload"]), flush=True)
        sys.exit(2)

    state["status"] = "running"
    save_task_state(state)
    task_start = time.monotonic()

    try:
        check_circuit_breaker()
    except BudgetExhausted as exc:
        print(f"[workshop] budget exhausted: {exc}", flush=True)
        sys.exit(1)

    write_task_ledger(task_id, goal=goal, status="running")

    try:
        stages = state.setdefault("stages", {})
        repo_context = f"Target repo: {repo_full_name}; base branch: {default_branch}"

        # Brainstorm stage (D-17: only triggered when --brainstorm flag is set)
        if args.brainstorm and _stage_should_run(state, "brainstorm"):
            if not state.get("brainstorm_approved"):
                brainstorm_query = json.dumps({
                    "task_id": task_id,
                    "goal": goal,
                    "context": repo_context,
                    "clarifications": state.get("clarifications") or [],
                    "brainstorm_turn": state.get("brainstorm_turn", 0),
                    "model_alias": stage_model_alias("brainstorm-specialist"),
                })
                brainstorm_result = run_stage("brainstorm", "brainstorm-specialist", brainstorm_query, BrainstormResult)
                if not brainstorm_result.approved:
                    # B1-A / D-18: no turn cap — loop until approved
                    state["next_stage"] = "brainstorm"
                    state["brainstorm_turn"] = state.get("brainstorm_turn", 0) + 1
                    save_task_state(state)
                    hitl_brainstorm = {
                        "needs_approval": False,
                        "hitl_type": "brainstorm",
                        "task_id": task_id,
                        "turn": state["brainstorm_turn"],
                        "goal_statement": brainstorm_result.goal_statement,
                        "follow_up": brainstorm_result.follow_up,
                        "summary": (
                            f"Brainstorm turn {state['brainstorm_turn']}: "
                            + (brainstorm_result.follow_up or "Review and approve or provide feedback")
                        ),
                    }
                    print(json.dumps(hitl_brainstorm), flush=True)
                    sys.exit(2)
                else:
                    state["brainstorm_approved"] = True
                    state["brainstorm_goal"] = brainstorm_result.goal_statement
                    state["next_stage"] = "triage"
                    save_task_state(state)
                    append_audit(task_id, "brainstorm_approved", {
                        "goal": brainstorm_result.goal_statement,
                        "turns": state.get("brainstorm_turn", 0),
                    })
                    print("[workshop] brainstorm_approved done", flush=True)

        if _stage_should_run(state, "triage") or "triage" not in stages:
            triage_query = json.dumps({"task_id": task_id, "goal": goal, "context": repo_context, "model_alias": stage_model_alias("triage-specialist")})
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
                    "model_alias": stage_model_alias("requirements-specialist"),
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

        # Resolve any referenced doc (e.g. prd.md) into reference content for planner.
        _doc_name = _extract_doc_reference(planner_goal)
        _vault_path = os.environ.get("VAULT_VPS_PATH", "/srv/second-brain")
        _reference_doc = ""
        if _doc_name:
            try:
                _reference_doc = _resolve_doc(_doc_name, state.get("workspace_dir") or "", _vault_path) or ""
            except Exception as exc:
                print(f"[workshop] WARNING: doc resolve failed for {_doc_name!r}: {exc}", flush=True)
                _reference_doc = ""

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
                "workspace_dir": state.get("workspace_dir") or "",
                "reference_doc": _reference_doc,
                "model_alias": stage_model_alias("planner-specialist"),
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
                payload = _review_retry_exhausted_payload(
                    task_id,
                    plan_goal=plan.goal,
                    repo_full_name=repo_full_name,
                    default_branch=default_branch,
                    review=review,
                    diff=diff,
                )
                state["status"] = "needs_review_recovery"
                state["next_stage"] = "reviewer"
                state["review_recovery_payload"] = payload
                save_task_state(state)
                write_task_ledger(task_id, goal, status="needs_review_recovery")
                append_progress(
                    task_id,
                    "review_recovery_requested",
                    {"attempts": current_review_attempts, "issues": len(payload["blocking_issues"])},
                )
                print(json.dumps(payload), flush=True)
                sys.exit(2)

            if _stage_should_run(state, "coder") or diff is None:
                # Budget check before running coder
                elapsed_total = time.monotonic() - task_start
                if elapsed_total > UWS_TASK_BUDGET:
                    reason = f"UWS_TASK_BUDGET={UWS_TASK_BUDGET}s exceeded (elapsed={elapsed_total:.0f}s)"
                    raise StageTimeoutForHITL("coder", state.get("attempts", {}).get("coder", 0), reason)

                # Cap check: if plan has too many steps, escalate before running
                plan_steps = plan.steps if hasattr(plan, "steps") else (plan.model_dump().get("steps") or [])
                if len(plan_steps) > MAX_STEPS:
                    reason = f"Plan has {len(plan_steps)} steps > MAX_STEPS={MAX_STEPS}. PRD too large — split it."
                    raise StageTimeoutForHITL("coder", 0, reason)

                coder_policy = _stage_policy_payload(state, "coder", stage_policy)
                current_step = int(state.get("current_step") or 0)
                coder_payload = {
                    "task_id": task_id,
                    "plan": plan.model_dump(),
                    "workspace_dir": state.get("workspace_dir") or (diff.workspace_dir if diff else ""),
                    "repo": repo_entry,
                    "clarifications": requirements.clarifications,
                    "stage_policy": coder_policy,
                    "model_alias": stage_model_alias("coder-specialist"),
                    "current_step": current_step,
                }
                if review is not None and not review.passed:
                    coder_payload["previous_review"] = review.model_dump()
                coder_query = json.dumps(coder_payload)
                try:
                    diff = run_stage("coder", "coder-specialist", coder_query, Diff)
                except SpecialistFailed as exc:
                    # workshop_coder.py exits non-zero when StepRetryExhausted is raised.
                    # Run the auto-recovery ladder: decompose → HITL.
                    diff = _handle_step_retry_exhausted(
                        exc, state, task_id, plan, "",
                        run_stage, stage_model_alias, append_progress, save_task_state, Diff, Plan,
                        task_start,
                    )
                stages["diff"] = diff.model_dump()
                state["next_stage"] = "reviewer"
                save_task_state(state)
                append_progress(task_id, "coder_complete", {"branch": diff.branch, "attempt": state["attempts"]["coder"]})
                print("[workshop] coder_complete done", flush=True)

            if _stage_should_run(state, "reviewer") or review is None:
                # Track reviewer attempt (mirrors the run_stage increment pattern)
                reviewer_attempts = state.setdefault("attempts", {})
                reviewer_attempt = int(reviewer_attempts.get("reviewer", 0)) + 1
                reviewer_attempts["reviewer"] = reviewer_attempt
                save_task_state(state)

                roster = load_review_roster()
                wave_reports = wave_dispatch(diff, plan, task_id, roster)
                merge_report = _build_merge_report(wave_reports)
                append_audit(task_id, "merge_complete", {
                    "block_push": merge_report.block_push,
                    "critical": len(merge_report.critical_findings),
                })
                # Convert MergeReport to Review — block_push=True → passed=False → triggers retry loop
                compat_review = Review(
                    passed=not merge_report.block_push,
                    feedback=merge_report.summary,
                    blocking_issues=[
                        ReviewIssue(file=f.file, problem=f.problem, required_fix=f.required_fix)
                        for f in merge_report.critical_findings + merge_report.important_findings
                    ],
                )
                review = compat_review
                stages["review"] = review.model_dump()
                save_task_state(state)
                append_progress(task_id, "review_complete", {"passed": review.passed, "attempt": reviewer_attempt})
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
        if timeout.step_context:
            payload.update(timeout.step_context)
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
