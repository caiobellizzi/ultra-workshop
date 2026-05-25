from __future__ import annotations

import json
import py_compile
import re
from pathlib import Path
from typing import Any

from workshop.requirements_gate import maybe_clarification_request, normalize_clarifications
from workshop.types import ClarificationQuestion, ClarificationRequest
from workshop.types import Diff, Plan, Review

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")
_SECRET_RE = re.compile(
    r"(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}",
    re.IGNORECASE,
)
_AMBIGUITY_RE = re.compile(
    r"\b(?:need(?:s)? more (?:info|information)|please clarify|unclear|ambiguous|which one)\b",
    re.IGNORECASE,
)
_SHELL_COMMAND_PREFIXES = (
    "bash ",
    "curl ",
    "pip ",
    "pytest",
    "python ",
    "sh ",
)


def _planned_files(plan: Plan) -> set[str]:
    files = set(plan.affected_files)
    for step in plan.steps:
        files.update(step.files)
    return {path for path in files if path}


def _path_issue(path: str) -> str | None:
    if not path or path.strip() != path:
        return f"Invalid changed path {path!r}: path is empty or padded."
    if Path(path).is_absolute():
        return f"Invalid changed path {path!r}: absolute paths are not allowed."
    if ".." in Path(path).parts:
        return f"Invalid changed path {path!r}: parent traversal is not allowed."
    if _CONTROL_CHARS_RE.search(path) or any(ch in path for ch in {'"', "'", "`"}):
        return f"Invalid changed path {path!r}: quotes/control characters are not allowed."
    if any(ch.isspace() for ch in path):
        return f"Invalid changed path {path!r}: whitespace makes it look like a shell command, not a file."
    if path in {"pytest", "python", "pip"} or path.startswith(_SHELL_COMMAND_PREFIXES):
        return f"Invalid changed path {path!r}: path looks like an accidental shell command artifact."
    return None


def _diff_text(diff: Diff) -> str:
    return "\n".join([diff.summary, *(change.diff for change in diff.changes)])


def _compile_changed_python(workspace_dir: str, changes: list[str]) -> list[str]:
    if not workspace_dir:
        return []
    workspace = Path(workspace_dir)
    if not workspace.exists():
        return []

    issues: list[str] = []
    for rel_path in changes:
        if not rel_path.endswith(".py"):
            continue
        path = workspace / rel_path
        if not path.exists():
            issues.append(f"Changed Python file {rel_path!r} is missing from the workspace.")
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            issues.append(f"Changed Python file {rel_path!r} does not compile: {exc.msg}")
    return issues


def review_query(query_json: str) -> Review | ClarificationRequest:
    query: dict[str, Any] = json.loads(query_json)
    plan = Plan.model_validate(query.get("plan") or {})
    diff = Diff.model_validate(query.get("diff") or {})
    task_id = str(query.get("task_id") or "unknown-task")
    goal = str(plan.goal or query.get("goal") or "")
    clarifications = normalize_clarifications(query.get("clarifications"))

    clarification = maybe_clarification_request(
        task_id,
        goal,
        source_stage="reviewer",
        clarifications=clarifications,
    )
    if clarification is not None:
        return clarification

    issues: list[str] = []
    changed_paths = [change.path for change in diff.changes]
    planned = _planned_files(plan)

    if not diff.changes:
        issues.append("No file changes were reported by the coder.")

    for path in changed_paths:
        issue = _path_issue(path)
        if issue:
            issues.append(issue)

    if planned:
        extras = sorted(set(changed_paths) - planned)
        if extras:
            issues.append(
                "Changed files outside the plan: "
                + ", ".join(extras[:10])
                + (" ..." if len(extras) > 10 else "")
            )

    source_changes = [p for p in changed_paths if p.endswith(".py") and not p.startswith("tests/")]
    test_changes = [p for p in changed_paths if p.startswith("tests/") or p.endswith("_test.py")]
    if source_changes and not test_changes:
        issues.append("Python source changed without a focused test change.")

    text = _diff_text(diff)
    if _AMBIGUITY_RE.search(text):
        return ClarificationRequest(
            task_id=task_id,
            source_stage="reviewer",
            reason="Reviewer found ambiguity in the requested behavior and cannot turn it into a concrete defect list.",
            questions=[
                ClarificationQuestion(
                    question="What exact behavior should the implementation satisfy?",
                    options=[],
                    context=goal,
                )
            ],
            allow_free_text=True,
            evidence=[text[:200]],
            summary="Clarification needed because the reviewer could not determine the intended behavior.",
        )
    if _SECRET_RE.search(text):
        issues.append("Diff appears to introduce a hardcoded secret, token, password, or API key.")

    issues.extend(_compile_changed_python(diff.workspace_dir, changed_paths))

    if issues:
        return Review(
            passed=False,
            feedback=f"Review blocked with {len(issues)} issue(s); fix the blocking issues and retry.",
            blocking_issues=issues,
        )

    return Review(
        passed=True,
        feedback="Review passed: changed files match the plan and no blocking issues were found.",
        blocking_issues=[],
    )
