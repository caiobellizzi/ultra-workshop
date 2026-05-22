"""Tests for workshop/types.py and workshop/orchestrator.py (Phase 4, Plan 1)."""
from __future__ import annotations

import json
import subprocess
import sys
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_completed_process(stdout: str = "", stderr: str = "", returncode: int = 0):
    """Return a mock subprocess.CompletedProcess."""
    mock = MagicMock(spec=subprocess.CompletedProcess)
    mock.stdout = stdout
    mock.stderr = stderr
    mock.returncode = returncode
    return mock


# ---------------------------------------------------------------------------
# Test 1: Plan.model_validate_json succeeds
# ---------------------------------------------------------------------------

def test_plan_model_validate_json():
    from workshop.types import Plan

    result = Plan.model_validate_json('{"goal":"g","steps":[{"id":"1","description":"d"}]}')
    assert result.goal == "g"
    assert len(result.steps) == 1
    assert result.steps[0].id == "1"


# ---------------------------------------------------------------------------
# Test 2: Diff includes workspace_dir field
# ---------------------------------------------------------------------------

def test_diff_workspace_dir():
    from workshop.types import Diff

    raw = '{"summary":"s","changes":[],"branch":"workshop/x","workspace_dir":"/tmp/uws-sandbox-x"}'
    diff = Diff.model_validate_json(raw)
    assert diff.workspace_dir == "/tmp/uws-sandbox-x"


# ---------------------------------------------------------------------------
# Test 3: run_specialist calls subprocess.run with shell=False
# ---------------------------------------------------------------------------

def test_run_specialist_subprocess_shell_false(monkeypatch):
    from workshop import orchestrator
    from workshop.types import Plan

    captured = {}

    def fake_run(argv, capture_output, text, shell, timeout):
        captured["argv"] = argv
        captured["shell"] = shell
        return _make_completed_process(
            stdout=json.dumps({"goal": "test", "steps": []}),
            returncode=0,
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    orchestrator.run_specialist("planner-specialist", '{"task":"x"}', Plan)

    assert captured["shell"] is False
    assert any("hermes-skill-run.sh" in str(a) for a in captured["argv"])


# ---------------------------------------------------------------------------
# Test 4: run_specialist parses JSON and returns validated Pydantic model
# ---------------------------------------------------------------------------

def test_run_specialist_returns_pydantic_model(monkeypatch):
    from workshop import orchestrator
    from workshop.types import Plan

    plan_json = json.dumps({"goal": "build it", "steps": [{"id": "1", "description": "do stuff"}]})

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **kw: _make_completed_process(stdout=plan_json, returncode=0),
    )

    result = orchestrator.run_specialist("planner-specialist", "{}", Plan)
    assert isinstance(result, Plan)
    assert result.goal == "build it"


# ---------------------------------------------------------------------------
# Test 5: run_specialist raises RuntimeError on non-zero exit
# ---------------------------------------------------------------------------

def test_run_specialist_raises_on_nonzero(monkeypatch):
    from workshop import orchestrator
    from workshop.types import Plan

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **kw: _make_completed_process(
            stdout="", stderr="specialist error", returncode=1
        ),
    )

    with pytest.raises(RuntimeError, match="exited 1"):
        orchestrator.run_specialist("planner-specialist", "{}", Plan)


# ---------------------------------------------------------------------------
# Test 6: _extract_json with clean JSON
# ---------------------------------------------------------------------------

def test_extract_json_clean():
    from workshop.orchestrator import _extract_json

    result = _extract_json('{"key": "value"}')
    assert result == '{"key": "value"}'


# ---------------------------------------------------------------------------
# Test 7: _extract_json with surrounding text
# ---------------------------------------------------------------------------

def test_extract_json_with_prefix_suffix():
    from workshop.orchestrator import _extract_json

    result = _extract_json('prefix {"a":1} suffix')
    assert result == '{"a":1}'


# ---------------------------------------------------------------------------
# Test 8: _extract_json raises ValueError when no JSON
# ---------------------------------------------------------------------------

def test_extract_json_raises_on_no_json():
    from workshop.orchestrator import _extract_json

    with pytest.raises(ValueError):
        _extract_json("no json here")


# ---------------------------------------------------------------------------
# Test 8b: _extract_json strips <think>...</think> reasoning blocks (NIM
# DeepSeek thinking-mode leak guard) before brace-matching.
# ---------------------------------------------------------------------------

def test_extract_json_strips_think_block():
    from workshop.orchestrator import _extract_json

    raw = '<think>reasoning {with braces}</think>{"k":"v"}'
    assert _extract_json(raw) == '{"k":"v"}'


def test_extract_json_strips_multiline_think_block():
    from workshop.orchestrator import _extract_json

    raw = '<think>\nline1\n{nested:braces}\nline2\n</think>\n{"ok": true}'
    assert _extract_json(raw) == '{"ok": true}'


def test_extract_json_strips_think_block_case_insensitive():
    from workshop.orchestrator import _extract_json

    raw = '<THINK>x</Think>{"a":1}'
    assert _extract_json(raw) == '{"a":1}'


# ---------------------------------------------------------------------------
# Test 9: All seven types export model_json_schema() without error
# ---------------------------------------------------------------------------

def test_all_types_export_schema():
    from workshop.types import (
        Diff,
        FileChange,
        IngestResult,
        Issue,
        Plan,
        PlanStep,
        Review,
    )

    for model_cls in (Plan, PlanStep, Diff, FileChange, Review, Issue, IngestResult):
        schema = model_cls.model_json_schema()
        assert isinstance(schema, dict), f"{model_cls.__name__}.model_json_schema() did not return a dict"
