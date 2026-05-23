"""Unit tests for workshop.orchestrator._extract_json fence/think/bare recovery."""
from __future__ import annotations

import pytest

from workshop.orchestrator import _extract_json


def test_extract_bare_json() -> None:
    assert _extract_json('{"a": 1}') == '{"a": 1}'


def test_extract_json_after_prose() -> None:
    text = 'Some chatter before.\n{"a": 1, "b": 2}\nTrailing words.'
    assert _extract_json(text) == '{"a": 1, "b": 2}'


def test_extract_json_inside_json_fenced_block() -> None:
    text = 'Sure, here is the result:\n```json\n{"branch": "workshop/foo"}\n```\nDone.'
    assert _extract_json(text) == '{"branch": "workshop/foo"}'


def test_extract_json_inside_plain_fenced_block() -> None:
    text = '```\n{"x": 42}\n```'
    assert _extract_json(text) == '{"x": 42}'


def test_extract_json_after_think_block() -> None:
    text = "<think>plotting...</think>\n{\"answer\": true}"
    assert _extract_json(text) == '{"answer": true}'


def test_extract_json_fenced_after_think() -> None:
    text = "<think>reasoning</think>\n```json\n{\"k\": \"v\"}\n```"
    assert _extract_json(text) == '{"k": "v"}'


def test_no_json_raises_with_skill_name() -> None:
    with pytest.raises(ValueError, match=r"\[coder-specialist\] No JSON object found"):
        _extract_json("def fibonacci(n):\n    return n", skill_name="coder-specialist")


def test_no_json_raises_without_skill_name() -> None:
    with pytest.raises(ValueError, match="No JSON object found"):
        _extract_json("plain prose, no braces here")


def test_fence_with_only_code_falls_through_to_brace_scan() -> None:
    # If fenced block has no JSON but braces exist outside the fence, still recover.
    text = '```python\ndef f(): pass\n```\n{"after": "fence"}'
    assert _extract_json(text) == '{"after": "fence"}'
