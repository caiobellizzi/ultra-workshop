from __future__ import annotations

import pytest

try:
    from workshop.types import Plan  # type: ignore[import]
    import pydantic
except ImportError:
    Plan = None  # type: ignore[assignment]


def test_plan_schema_valid() -> None:
    """A minimal plan dict validates against Plan.model_validate()."""
    if Plan is None:
        pytest.skip("workshop.types.Plan not importable")

    plan = Plan.model_validate(
        {
            "goal": "add hello world",
            "steps": [{"id": "1", "description": "create file", "files": ["hello.py"]}],
            "affected_files": ["hello.py"],
        }
    )
    assert plan.goal == "add hello world"
    assert len(plan.steps) == 1
    assert plan.steps[0].id == "1"
    assert plan.affected_files == ["hello.py"]


def test_plan_affected_files_real_paths() -> None:
    """A plan with workspace-style paths in affected_files validates without error."""
    if Plan is None:
        pytest.skip("workshop.types.Plan not importable")

    plan = Plan.model_validate(
        {
            "goal": "refactor auth",
            "steps": [
                {
                    "id": "1",
                    "description": "update auth module",
                    "files": [
                        "src/workshop/orchestrator.py",
                        "tests/test_orchestrator.py",
                    ],
                }
            ],
            "affected_files": [
                "src/workshop/orchestrator.py",
                "tests/test_orchestrator.py",
            ],
        }
    )
    assert "src/workshop/orchestrator.py" in plan.affected_files
    assert "tests/test_orchestrator.py" in plan.affected_files


def test_plan_empty_affected_files() -> None:
    """An LLM response with affected_files=[] is valid (empty list allowed)."""
    if Plan is None:
        pytest.skip("workshop.types.Plan not importable")

    plan = Plan.model_validate(
        {
            "goal": "scaffold hello.py",
            "steps": [{"id": "1", "description": "create scaffold", "files": []}],
            "affected_files": [],
        }
    )
    assert plan.affected_files == []


def test_clarification_needed_is_not_a_plan() -> None:
    """A ClarificationNeeded dict raises ValidationError when passed to Plan.model_validate().

    Confirms that the two response types are structurally distinct — a clarification
    request cannot accidentally be parsed as a Plan.
    """
    if Plan is None:
        pytest.skip("workshop.types.Plan not importable")

    with pytest.raises(Exception):
        Plan.model_validate({"clarification_needed": True, "question": "Which file?"})
