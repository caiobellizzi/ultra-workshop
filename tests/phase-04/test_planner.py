from __future__ import annotations

import json
import subprocess
import sys

from workshop.planner import build_plan


def test_build_plan_extracts_explicit_file_and_adds_requested_test() -> None:
    query = json.dumps(
        {
            "goal": "add a fibonacci(n) function to utils.py with a docstring and a basic test",
            "triage_result": {
                "task_type": "BUILD",
                "summary": "Add fibonacci utility",
                "complexity": "low",
            },
            "context": "",
        }
    )

    plan = build_plan(query)

    assert plan.affected_files == ["utils.py", "tests/test_utils.py"]
    assert 2 <= len(plan.steps) <= 5


def test_build_plan_infers_openharness_orchestration_files() -> None:
    query = json.dumps(
        {
            "goal": "create a multi agent orchestration using the best 12 factory practices and using https://github.com/HKUDS/OpenHarness",
            "triage_result": {
                "task_type": "BUILD",
                "summary": "Create OpenHarness multi-agent orchestration",
                "complexity": "high",
            },
            "context": "",
        }
    )

    plan = build_plan(query)

    assert "openharness_orchestration.py" in plan.affected_files
    assert "tests/test_openharness_orchestration.py" in plan.affected_files
    assert "README.md" in plan.affected_files


def test_workshop_planner_cli_outputs_plan_json() -> None:
    query = json.dumps(
        {
            "goal": "add an API endpoint in app.py",
            "triage_result": {"task_type": "BUILD", "summary": "Add API endpoint"},
            "context": "",
        }
    )

    result = subprocess.run(
        [sys.executable, "hermes-skills/workshop_planner.py", "--query", query],
        capture_output=True,
        text=True,
        shell=False,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["goal"] == "add an API endpoint in app.py"
    assert payload["affected_files"] == ["app.py"]
