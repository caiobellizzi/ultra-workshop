from __future__ import annotations

import json
import py_compile
import re
import importlib.util
import sys
from pathlib import Path
from typing import Any

from workshop.requirements_gate import maybe_clarification_request, normalize_clarifications
from workshop.types import ClarificationQuestion, ClarificationRequest
from workshop.types import Diff, Plan, Review, ReviewIssue

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
_BRAIN_HTTP = Path(__file__).resolve().parent.parent / "hermes-skills" / "brain_http.py"
_brain_http = None
try:
    _spec = importlib.util.spec_from_file_location("brain_http", _BRAIN_HTTP)
    if _spec and _spec.loader:
        _brain_http = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_brain_http)
except Exception:
    _brain_http = None


def _issue(file: str, problem: str, required_fix: str) -> ReviewIssue:
    return ReviewIssue(file=file or "*", problem=problem, required_fix=required_fix)


def _query_review_memory(repo_full_name: str) -> str:
    if _brain_http is None or not repo_full_name:
        return ""
    try:
        result = _brain_http.call_agent(
            "query",
            f"project review rules and prior incident ADRs for {repo_full_name}",
        )
        content = str(result.get("content") or result)
        print(
            f"[workshop_reviewer] brain-query review context loaded for {repo_full_name}",
            file=sys.stderr,
            flush=True,
        )
        return content
    except Exception as exc:
        print(
            f"[workshop_reviewer] WARNING: brain-query failed: {exc}",
            file=sys.stderr,
            flush=True,
        )
        return ""


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


def _compile_changed_python(workspace_dir: str, changes: list[str]) -> list[ReviewIssue]:
    if not workspace_dir:
        return []
    workspace = Path(workspace_dir)
    if not workspace.exists():
        return []

    issues: list[ReviewIssue] = []
    for rel_path in changes:
        if not rel_path.endswith(".py"):
            continue
        path = workspace / rel_path
        if not path.exists():
            issues.append(
                _issue(
                    rel_path,
                    f"Changed Python file {rel_path!r} is missing from the workspace.",
                    "Create the file in the workspace or remove it from the reported diff.",
                )
            )
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            issues.append(
                _issue(
                    rel_path,
                    f"Changed Python file {rel_path!r} does not compile: {exc.msg}",
                    "Fix the Python syntax error and rerun the verification command.",
                )
            )
    return issues


def review_query(query_json: str) -> Review | ClarificationRequest:
    query: dict[str, Any] = json.loads(query_json)
    plan = Plan.model_validate(query.get("plan") or {})
    diff = Diff.model_validate(query.get("diff") or {})
    task_id = str(query.get("task_id") or "unknown-task")
    goal = str(plan.goal or query.get("goal") or "")
    clarifications = normalize_clarifications(query.get("clarifications"))
    repo = query.get("repo") if isinstance(query.get("repo"), dict) else {}
    repo_full_name = str(repo.get("full_name") or query.get("repo_full_name") or "").strip()
    _query_review_memory(repo_full_name)

    clarification = maybe_clarification_request(
        task_id,
        goal,
        source_stage="reviewer",
        clarifications=clarifications,
    )
    if clarification is not None:
        return clarification

    verification_issues: list[ReviewIssue] = []
    if not diff.build_passed:
        verification_issues.append(
            _issue(
                "*",
                "Build verification failed before static review.",
                "Fix the build failure shown in output_tail before retrying.",
            )
        )
    if not diff.test_passed:
        verification_issues.append(
            _issue(
                "*",
                "Test verification failed before static review.",
                "Fix the failing tests shown in output_tail before retrying.",
            )
        )
    if verification_issues:
        tail = (diff.output_tail or "").strip()
        if tail:
            verification_issues[0].problem = f"{verification_issues[0].problem} Output tail: {tail[:800]}"
        return Review(
            passed=False,
            feedback=f"Review blocked by verification failure with {len(verification_issues)} issue(s).",
            blocking_issues=verification_issues,
        )

    issues: list[ReviewIssue] = []
    changed_paths = [change.path for change in diff.changes]
    planned = _planned_files(plan)

    if not diff.changes:
        issues.append(
            _issue(
                "*",
                "No file changes were reported by the coder.",
                "Produce a concrete diff for the planned files or ask for clarification.",
            )
        )

    for path in changed_paths:
        path_problem = _path_issue(path)
        if path_problem:
            issues.append(
                _issue(
                    path,
                    path_problem,
                    "Report only workspace-relative file paths in diff.changes.",
                )
            )

    if planned:
        extras = sorted(set(changed_paths) - planned)
        if extras:
            issues.append(
                _issue(
                    ", ".join(extras[:10]),
                    "Changed files outside the plan: "
                    + ", ".join(extras[:10])
                    + (" ..." if len(extras) > 10 else ""),
                    "Restrict the change to plan.affected_files or re-plan before coding.",
                )
            )

    source_changes = [p for p in changed_paths if p.endswith(".py") and not p.startswith("tests/")]
    test_changes = [p for p in changed_paths if p.startswith("tests/") or p.endswith("_test.py")]
    if source_changes and not test_changes:
        issues.append(
            _issue(
                ", ".join(source_changes[:10]),
                "Python source changed without a focused test change.",
                "Add or update a focused test file covering the source change.",
            )
        )

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
        issues.append(
            _issue(
                "*",
                "Diff appears to introduce a hardcoded secret, token, password, or API key.",
                "Remove the secret and load sensitive values from approved runtime configuration.",
            )
        )

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
