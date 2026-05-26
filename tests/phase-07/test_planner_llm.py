from __future__ import annotations

import pytest

try:
    from workshop.types import Plan  # type: ignore[import]
except ImportError:
    Plan = None  # type: ignore[assignment]


@pytest.mark.xfail(reason="workshop.types.Plan not yet updated with doc_refs field for LLM planner", strict=False)
def test_plan_schema_valid() -> None:
    """A minimal plan dict with LLM planner fields validates against Plan.model_validate().

    Phase 7 will add doc_refs (list of resolved doc names injected into planner context)
    to the Plan schema. This test verifies the updated schema is present.
    """
    if Plan is None:
        pytest.xfail("workshop.types.Plan not yet present")

    # This will xfail until Plan gains the doc_refs field (added in Plan 07-02)
    plan = Plan.model_validate(
        {
            "goal": "test",
            "steps": [],
            "affected_files": [],
            "doc_refs": [],
        }
    )
    assert plan.goal == "test"
    assert plan.steps == []
    assert plan.affected_files == []
    assert plan.doc_refs == []
