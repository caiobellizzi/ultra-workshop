from __future__ import annotations

import json
import re
from typing import Any

from workshop.types import Plan, PlanStep

_FILE_RE = re.compile(
    r"(?<![\w./-])(?:[\w.-]+/)*[\w.-]+\."
    r"(?:py|js|jsx|ts|tsx|md|json|yaml|yml|toml|sh|css|html|go|rs|java|rb|php)"
    r"(?![\w./-])",
    re.IGNORECASE,
)

_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "using",
    "use",
    "from",
    "into",
    "that",
    "this",
    "create",
    "build",
    "add",
    "fix",
    "best",
    "practices",
    "practice",
}


def build_plan(query_json: str) -> Plan:
    """Create a deterministic implementation plan from the planner query JSON."""
    query = json.loads(query_json)
    goal = str(query.get("goal") or "").strip()
    if not goal:
        raise ValueError("planner query missing non-empty goal")

    triage_result = query.get("triage_result") or {}
    affected_files = infer_affected_files(goal, triage_result)
    impl_files = [path for path in affected_files if not _is_test_file(path)]
    test_files = [path for path in affected_files if _is_test_file(path)]
    summary = str(triage_result.get("summary") or goal).strip()

    steps: list[PlanStep] = [
        PlanStep(
            id="1",
            description=f"Inspect the current code and confirm the intended behavior: {summary}",
            files=affected_files,
        )
    ]

    if impl_files:
        steps.append(
            PlanStep(
                id=str(len(steps) + 1),
                description="Implement the requested behavior in the focused source files.",
                files=impl_files,
            )
        )
    else:
        steps.append(
            PlanStep(
                id=str(len(steps) + 1),
                description="Update the focused documentation or configuration files.",
                files=affected_files,
            )
        )

    if test_files:
        steps.append(
            PlanStep(
                id=str(len(steps) + 1),
                description="Add or update focused regression tests for the requested behavior.",
                files=test_files,
            )
        )

    steps.append(
        PlanStep(
            id=str(len(steps) + 1),
            description="Run the smallest relevant validation and adjust the change if it fails.",
            files=affected_files,
        )
    )

    return Plan(goal=goal, steps=steps, affected_files=affected_files)


def infer_affected_files(goal: str, triage_result: dict[str, Any] | None = None) -> list[str]:
    lower_goal = goal.lower()
    files = _extract_file_paths(goal)
    triage_result = triage_result or {}
    task_type = str(triage_result.get("task_type") or "").upper()

    if not files:
        files = _default_files_for_goal(lower_goal)

    wants_tests = any(
        marker in lower_goal
        for marker in ("test", "tests", "pytest", "unit test", "basic test", "regression")
    ) or task_type == "FIX"
    if wants_tests:
        files.extend(_missing_test_files(files))

    return _dedupe_preserve(files)[:6]


def _extract_file_paths(text: str) -> list[str]:
    paths: list[str] = []
    for match in _FILE_RE.finditer(text):
        path = match.group(0).strip("`'\".,;:)]}>")
        if path.startswith(("http://", "https://")):
            continue
        if path.startswith("./"):
            path = path[2:]
        paths.append(path)
    return _dedupe_preserve(paths)


def _default_files_for_goal(lower_goal: str) -> list[str]:
    if any(marker in lower_goal for marker in ("readme", "documentation", "docs")):
        return ["README.md"]
    if any(marker in lower_goal for marker in ("endpoint", "api", "route", "server", "fastapi", "flask")):
        return ["app.py"]
    if any(
        marker in lower_goal
        for marker in ("agent", "orchestration", "harness", "openharness", "workflow", "pipeline")
    ):
        slug = _slug_from_goal(lower_goal)
        return [f"{slug}.py", f"tests/test_{slug}.py", "README.md"]
    if any(marker in lower_goal for marker in ("function", "utility", "utils", "helper", "fibonacci")):
        return ["utils.py"]
    if any(marker in lower_goal for marker in ("cli", "command")):
        return ["cli.py"]
    return ["README.md"]


def _missing_test_files(files: list[str]) -> list[str]:
    if any(_is_test_file(path) for path in files):
        return []

    tests: list[str] = []
    for path in files:
        if not path.endswith(".py") or _is_test_file(path):
            continue
        stem = path.rsplit("/", 1)[-1].removesuffix(".py")
        tests.append(f"tests/test_{stem}.py")
    return tests


def _is_test_file(path: str) -> bool:
    return path.startswith("tests/") or "/tests/" in path or path.rsplit("/", 1)[-1].startswith("test_")


def _slug_from_goal(lower_goal: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", lower_goal)
    if "openharness" in tokens:
        return "openharness_orchestration" if {"agent", "orchestration"} & set(tokens) else "openharness"
    if {"agent", "orchestration", "harness"} & set(tokens):
        return "agent_orchestration"

    meaningful = [token for token in tokens if len(token) > 2 and token not in _STOPWORDS]
    return "_".join(meaningful[:3]) or "workshop_task"


def _dedupe_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
