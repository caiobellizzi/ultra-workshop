# Deploy location: /opt/ultra-workshop/hermes-skills/workshop_continue.py
from __future__ import annotations

import argparse
import base64
import binascii
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from workshop.requirements_gate import normalize_clarifications  # noqa: E402
from workshop.stage_policy import stage_policy  # noqa: E402
from workshop.state import append_state_item, load_task_state, save_task_state, utc_now  # noqa: E402


def _read_response(path: str) -> Any:
    if not path:
        return ""
    text = Path(path).read_text(encoding="utf-8").strip()
    if not text:
        return ""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _read_response_b64(value: str) -> Any:
    if not value:
        return ""
    try:
        text = base64.b64decode(value.encode("ascii"), validate=True).decode("utf-8").strip()
    except (binascii.Error, UnicodeDecodeError) as exc:
        print(f"[workshop_continue] invalid --response-b64: {exc}", flush=True)
        sys.exit(1)
    if not text:
        return ""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _response_text(response: Any) -> str:
    if isinstance(response, str):
        return response.strip()
    if isinstance(response, dict):
        for key in ("answer", "response", "value", "text"):
            value = response.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        normalized = normalize_clarifications(response)
        if normalized:
            return "\n".join(normalized)
        return json.dumps(response, sort_keys=True)
    if isinstance(response, list):
        normalized = normalize_clarifications(response)
        if normalized:
            return "\n".join(normalized)
        return json.dumps(response, sort_keys=True)
    return str(response).strip()


def _merge_unique(existing: list[str], new_items: list[str]) -> list[str]:
    merged = list(existing)
    seen = set(merged)
    for item in new_items:
        if item and item not in seen:
            merged.append(item)
            seen.add(item)
    return merged


def _invalidate_from(state: dict[str, Any], stage: str) -> None:
    stage_order = ["requirements", "planner", "diff", "review"]
    starts = {
        "requirements": 0,
        "planner": 1,
        "coder": 2,
        "reviewer": 3,
    }
    start = starts.get(stage, 0)
    stages = state.setdefault("stages", {})
    for key in stage_order[start:]:
        stages.pop(key, None)
    if stage in {"requirements", "planner"}:
        state["approval_payload"] = {}
        state["timeout_payload"] = {}


def _is_approval(response: Any) -> bool:
    text = _response_text(response).lower()
    if isinstance(response, bool):
        return response
    if isinstance(response, dict):
        value = response.get("approved")
        if isinstance(value, bool):
            return value
    return text in {"1", "y", "yes", "true", "approve", "approved", "ok", "ship", "send"}


def _launch_build(task_id: str) -> int:
    build_script = Path(__file__).parent / "workshop_build.py"
    result = subprocess.run(
        [sys.executable, str(build_script), "--task-id", task_id, "--resume"],
        shell=False,
    )
    return int(result.returncode)


def _run_push(task_id: str, state: dict[str, Any]) -> int:
    payload = state.get("approval_payload") or {}
    required = ["branch", "workspace_dir", "repo_full_name", "default_branch", "plan_goal", "diff_summary"]
    missing = [key for key in required if not payload.get(key)]
    if missing:
        print(f"[workshop_continue] approval payload missing: {', '.join(missing)}", flush=True)
        return 1

    push_script = Path(__file__).parent / "workshop_push.py"
    result = subprocess.run(
        [
            sys.executable,
            str(push_script),
            "--task-id",
            task_id,
            "--branch",
            str(payload["branch"]),
            "--workspace-dir",
            str(payload["workspace_dir"]),
            "--repo-full-name",
            str(payload["repo_full_name"]),
            "--base",
            str(payload["default_branch"]),
            "--plan-goal",
            str(payload["plan_goal"]),
            "--diff-summary",
            str(payload["diff_summary"]),
        ],
        capture_output=True,
        text=True,
        shell=False,
    )
    if result.stdout:
        print(result.stdout, end="", flush=True)
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr, flush=True)
    return int(result.returncode)


def _apply_clarification(state: dict[str, Any], response: Any) -> None:
    clarifications = normalize_clarifications(response)
    if not clarifications:
        text = _response_text(response)
        clarifications = [text] if text else []
    state["clarifications"] = _merge_unique(list(state.get("clarifications") or []), clarifications)
    state["status"] = "running"
    state["next_stage"] = "requirements"
    _invalidate_from(state, "requirements")


def _apply_timeout_recovery(state: dict[str, Any], response: Any) -> None:
    text = _response_text(response)
    lowered = text.lower()
    if lowered in {"4", "stop", "abort", "cancel", "cancelled"}:
        state["status"] = "stopped"
        state["next_stage"] = "timeout_recovery"
        return

    if lowered.startswith("2") or "increase" in lowered or "timeout" in lowered:
        coder_policy = stage_policy("coder")
        overrides = state.setdefault("stage_overrides", {}).setdefault("coder", {})
        overrides["timeout"] = max(int(overrides.get("timeout") or coder_policy.timeout), 1920)
        overrides["tool_timeout"] = max(int(overrides.get("tool_timeout") or coder_policy.tool_timeout or 900), 1800)
        state["status"] = "running"
        state["next_stage"] = "coder"
        _invalidate_from(state, "coder")
        return

    if lowered.startswith("3") or "simplif" in lowered:
        instruction = (
            "Human approved timeout recovery: simplify the original goal into the smallest "
            "reviewable implementation plan before coding. Planner must own the decomposition."
        )
    elif lowered and not lowered.startswith("1"):
        instruction = (
            "Human approved timeout recovery with this decomposition guidance: "
            f"{text}. Planner must produce the next bounded coding slice before coder runs."
        )
    else:
        instruction = (
            "Human approved timeout recovery: re-plan into the smallest first vertical slice. "
            "Only the first reviewable slice should be sent to coder in this pass; sequence the "
            "remaining work explicitly for later resumable stages."
        )

    state["scope_instruction"] = instruction
    state["status"] = "running"
    state["next_stage"] = "planner"
    _invalidate_from(state, "planner")


def main() -> None:
    parser = argparse.ArgumentParser(description="Resume a workshop task after HITL input")
    parser.add_argument("--task-id", required=True, help="Original workshop task ID")
    parser.add_argument(
        "--hitl-type",
        required=True,
        choices=["clarification", "timeout_recovery", "approval"],
        help="Type of human input being applied",
    )
    parser.add_argument("--response-file", default="", help="Path containing the human response")
    parser.add_argument("--response-b64", default="", help="Base64-encoded UTF-8 human response")
    parser.add_argument(
        "--choice",
        default="",
        help="Shell-safe HITL button choice or approval token; avoids temp files for simple selections",
    )
    args = parser.parse_args()

    try:
        state = load_task_state(args.task_id)
    except FileNotFoundError as exc:
        print(f"[workshop_continue] {exc}", flush=True)
        sys.exit(1)

    if args.choice:
        response = args.choice.strip()
    elif args.response_b64:
        response = _read_response_b64(args.response_b64)
    else:
        response = _read_response(args.response_file)
    append_state_item(
        state,
        "hitl_responses",
        {
            "type": args.hitl_type,
            "response": response,
            "received_at": utc_now(),
        },
    )

    if args.hitl_type == "clarification":
        _apply_clarification(state, response)
        save_task_state(state)
        sys.exit(_launch_build(args.task_id))

    if args.hitl_type == "timeout_recovery":
        append_state_item(
            state,
            "recovery_decisions",
            {
                "response": response,
                "received_at": utc_now(),
            },
        )
        _apply_timeout_recovery(state, response)
        save_task_state(state)
        if state.get("status") == "stopped":
            print(f"[workshop_continue] workflow stopped for task {args.task_id}", flush=True)
            sys.exit(0)
        sys.exit(_launch_build(args.task_id))

    if args.hitl_type == "approval":
        if not _is_approval(response):
            state["status"] = "approval_rejected"
            save_task_state(state)
            print(f"PR creation rejected for task {args.task_id}.", flush=True)
            sys.exit(0)
        state["status"] = "pushing"
        save_task_state(state)
        code = _run_push(args.task_id, state)
        state["status"] = "pushed" if code == 0 else "push_failed"
        save_task_state(state)
        sys.exit(code)


if __name__ == "__main__":
    main()
