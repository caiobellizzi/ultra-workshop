"""Tests for workshop/ledger.py (Phase 4, Plan 1)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Test L1: append_progress creates progress_log.jsonl with valid JSON line
# ---------------------------------------------------------------------------

def test_append_progress_creates_jsonl(tmp_path, monkeypatch):
    import workshop.ledger as ledger_mod

    monkeypatch.setattr(ledger_mod, "LEDGER_BASE", tmp_path)

    ledger_mod.append_progress("abc123", "triage_complete", {"role": "triage"})

    log_file = tmp_path / "abc123" / "progress_log.jsonl"
    assert log_file.exists(), "progress_log.jsonl not created"

    line = log_file.read_text().strip()
    entry = json.loads(line)
    assert "ts" in entry
    assert entry["event"] == "triage_complete"
    assert entry["role"] == "triage"


# ---------------------------------------------------------------------------
# Test L2: multiple append_progress calls append separate lines
# ---------------------------------------------------------------------------

def test_append_progress_multiple_lines(tmp_path, monkeypatch):
    import workshop.ledger as ledger_mod

    monkeypatch.setattr(ledger_mod, "LEDGER_BASE", tmp_path)

    ledger_mod.append_progress("abc123", "step_1", {"x": 1})
    ledger_mod.append_progress("abc123", "step_2", {"x": 2})
    ledger_mod.append_progress("abc123", "step_3", {"x": 3})

    log_file = tmp_path / "abc123" / "progress_log.jsonl"
    lines = [l for l in log_file.read_text().splitlines() if l.strip()]
    assert len(lines) == 3

    for i, line in enumerate(lines, start=1):
        entry = json.loads(line)
        assert entry["event"] == f"step_{i}"


# ---------------------------------------------------------------------------
# Test L3: write_task_ledger writes task_ledger.md with goal and pr_url
# ---------------------------------------------------------------------------

def test_write_task_ledger_content(tmp_path, monkeypatch):
    import workshop.ledger as ledger_mod

    monkeypatch.setattr(ledger_mod, "LEDGER_BASE", tmp_path)

    ledger_mod.write_task_ledger(
        "abc123",
        "add hello endpoint",
        "completed",
        "https://github.com/.../pull/1",
    )

    ledger_file = tmp_path / "abc123" / "task_ledger.md"
    assert ledger_file.exists(), "task_ledger.md not created"

    content = ledger_file.read_text()
    assert "add hello endpoint" in content
    assert "https://github.com/.../pull/1" in content


# ---------------------------------------------------------------------------
# Test L4: task_dir() creates the directory with parents=True
# ---------------------------------------------------------------------------

def test_task_dir_creates_directory(tmp_path, monkeypatch):
    import workshop.ledger as ledger_mod

    monkeypatch.setattr(ledger_mod, "LEDGER_BASE", tmp_path)

    result = ledger_mod.task_dir("newid123")
    assert result.exists()
    assert result.is_dir()
    assert result == tmp_path / "newid123"
