"""Tests for brain_http.mark_queue_entry_dispatched local-file ACK.

The Brain does not serve PUT /workshop/queue/{id}/dispatched (404), so the ACK
is performed in-place on the local JSONL. These tests verify the entry is
flipped, others are preserved, and missing/empty queues are handled gracefully.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

_HERMES = Path(__file__).resolve().parents[2] / "hermes-skills"
if str(_HERMES) not in sys.path:
    sys.path.insert(0, str(_HERMES))

brain_http = importlib.import_module("brain_http")


def _write_queue(path: Path, entries: list[dict]) -> None:
    path.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")


def _read_queue(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


@pytest.fixture
def queue(tmp_path, monkeypatch):
    vault = tmp_path
    (vault / "_system").mkdir()
    monkeypatch.setenv("VAULT_VPS_PATH", str(vault))
    return vault / "_system" / ".workshop-queue.jsonl"


def test_flips_matching_entry_and_preserves_others(queue):
    _write_queue(queue, [
        {"id": "a", "action": "post-to-telegram", "confirmed": True, "dispatched": False, "text": "x"},
        {"id": "b", "action": "link-orphans", "confirmed": True, "dispatched": False, "orphans": ["n"]},
    ])
    result = brain_http.mark_queue_entry_dispatched("a")
    assert result == {"id": "a", "dispatched": True, "found": True}
    rows = {e["id"]: e for e in _read_queue(queue)}
    assert rows["a"]["dispatched"] is True
    assert rows["b"]["dispatched"] is False  # untouched
    assert rows["a"]["text"] == "x"          # other fields preserved


def test_missing_queue_returns_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("VAULT_VPS_PATH", str(tmp_path))  # no _system/queue file
    assert brain_http.mark_queue_entry_dispatched("nope") == {
        "id": "nope", "dispatched": False, "found": False,
    }


def test_unknown_id_leaves_file_intact(queue):
    _write_queue(queue, [{"id": "a", "dispatched": False}])
    result = brain_http.mark_queue_entry_dispatched("zzz")
    assert result["found"] is False
    assert _read_queue(queue) == [{"id": "a", "dispatched": False}]


def test_idempotent_second_ack_is_noop(queue):
    _write_queue(queue, [{"id": "a", "dispatched": False}])
    brain_http.mark_queue_entry_dispatched("a")
    second = brain_http.mark_queue_entry_dispatched("a")
    assert second["dispatched"] is True
    assert _read_queue(queue) == [{"id": "a", "dispatched": True}]
