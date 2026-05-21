"""
pytest tests for startup-hitl-scan.py helper module.

Tests use an in-memory (or temp-file) SQLite database so they do not
touch the production /home/uws/.ultra-workshop/pending_hitl.db.

Run:  cd hermes-skills && python -m pytest test_startup_hitl_scan.py -x -q
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import threading
import time
import unittest.mock as mock
from pathlib import Path
from typing import Any, Dict

import importlib.util
import pytest

# Load startup-hitl-scan.py via importlib since hyphens are invalid in Python identifiers
_MODULE_PATH = Path(__file__).parent / "startup-hitl-scan.py"
_spec = importlib.util.spec_from_file_location("startup_hitl_scan", _MODULE_PATH)
hitl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hitl)
sys.modules["startup_hitl_scan"] = hitl  # register so handler.py can import it too


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_db(tmp_path) -> Path:
    """Return a fresh temporary DB path (file does not exist yet)."""
    return tmp_path / "pending_hitl.db"


# ---------------------------------------------------------------------------
# ensure_schema
# ---------------------------------------------------------------------------


def test_ensure_schema_creates_table(tmp_db):
    hitl.ensure_schema(tmp_db)
    with sqlite3.connect(str(tmp_db)) as conn:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='pending_hitl'"
        )
        assert cur.fetchone() is not None, "pending_hitl table was not created"


def test_ensure_schema_is_idempotent(tmp_db):
    hitl.ensure_schema(tmp_db)
    hitl.ensure_schema(tmp_db)  # second call must not raise


def test_ensure_schema_sets_permissions(tmp_db):
    hitl.ensure_schema(tmp_db)
    mode = oct(os.stat(str(tmp_db)).st_mode)[-3:]
    assert mode == "600", f"Expected 0600 permissions, got {mode}"


# ---------------------------------------------------------------------------
# record_hitl_pause
# ---------------------------------------------------------------------------


def test_record_hitl_pause_writes_pending_row(tmp_db):
    row_id = hitl.record_hitl_pause(
        session_id="sess-001",
        task_description="push to main",
        chat_id="7113965359",
        db_path=tmp_db,
    )
    assert isinstance(row_id, int) and row_id > 0

    with sqlite3.connect(str(tmp_db)) as conn:
        cur = conn.execute("SELECT * FROM pending_hitl WHERE id = ?", (row_id,))
        row = cur.fetchone()
    assert row is not None, "Row was not inserted"


def test_record_hitl_pause_status_is_pending(tmp_db):
    row_id = hitl.record_hitl_pause(
        session_id="sess-002",
        task_description="deploy artifact",
        chat_id="7113965359",
        db_path=tmp_db,
    )
    with sqlite3.connect(str(tmp_db)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT status FROM pending_hitl WHERE id = ?", (row_id,))
        row = cur.fetchone()
    assert row["status"] == "pending"


# ---------------------------------------------------------------------------
# fetch_pending
# ---------------------------------------------------------------------------


def test_fetch_pending_returns_empty_when_db_missing(tmp_db):
    assert hitl.fetch_pending(tmp_db) == []


def test_fetch_pending_returns_pending_rows(tmp_db):
    hitl.record_hitl_pause("s1", "task A", "7113965359", db_path=tmp_db)
    hitl.record_hitl_pause("s2", "task B", "7113965359", db_path=tmp_db)
    rows = hitl.fetch_pending(tmp_db)
    assert len(rows) == 2
    for r in rows:
        assert r["status"] == "pending"


def test_fetch_pending_excludes_resolved_rows(tmp_db):
    row_id = hitl.record_hitl_pause("s3", "task C", "7113965359", db_path=tmp_db)
    hitl.resolve_hitl_row(row_id, "approved", db_path=tmp_db)
    rows = hitl.fetch_pending(tmp_db)
    assert rows == []


# ---------------------------------------------------------------------------
# resolve_hitl_row
# ---------------------------------------------------------------------------


def test_resolve_hitl_row_updates_status(tmp_db):
    row_id = hitl.record_hitl_pause("s4", "task D", "7113965359", db_path=tmp_db)
    hitl.resolve_hitl_row(row_id, "approved", approved_by="Alice", db_path=tmp_db)
    with sqlite3.connect(str(tmp_db)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM pending_hitl WHERE id = ?", (row_id,))
        row = cur.fetchone()
    assert row["status"] == "approved"
    assert row["approved_by"] == "Alice"
    assert row["approved_at"] is not None


def test_resolve_hitl_row_rejected(tmp_db):
    row_id = hitl.record_hitl_pause("s5", "task E", "7113965359", db_path=tmp_db)
    hitl.resolve_hitl_row(row_id, "rejected", db_path=tmp_db)
    with sqlite3.connect(str(tmp_db)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT status FROM pending_hitl WHERE id = ?", (row_id,))
        row = cur.fetchone()
    assert row["status"] == "rejected"


# ---------------------------------------------------------------------------
# update_hitl_message_id
# ---------------------------------------------------------------------------


def test_update_hitl_message_id(tmp_db):
    row_id = hitl.record_hitl_pause("s6", "task F", "7113965359", db_path=tmp_db)
    hitl.update_hitl_message_id(row_id, "tg-msg-999", db_path=tmp_db)
    with sqlite3.connect(str(tmp_db)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT telegram_message_id FROM pending_hitl WHERE id = ?", (row_id,))
        row = cur.fetchone()
    assert row["telegram_message_id"] == "tg-msg-999"


# ---------------------------------------------------------------------------
# handler.handle — mock-based integration test
# ---------------------------------------------------------------------------


def _load_handler_module():
    """Load handler.py via importlib; return module or None if not importable."""
    import importlib.util as _ilu
    hook_dir = Path(__file__).parent / "startup-hitl-scan-hook"
    handler_path = hook_dir / "handler.py"
    if not handler_path.exists():
        return None
    sys.path.insert(0, str(hook_dir))
    spec = _ilu.spec_from_file_location("handler_module", handler_path)
    mod = _ilu.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        # Handler has optional Hermes imports at module level; failures here are expected
        pass
    return mod


@pytest.mark.asyncio
async def test_handle_calls_clarify_for_pending_row(tmp_db, monkeypatch):
    """
    Creates a pending row in tmp_db, mocks the Hermes internals,
    and asserts that send_clarify is called with the correct chat_id.
    """
    # Seed a pending row
    hitl.record_hitl_pause("sess-handle-01", "test approval", "7113965359", db_path=tmp_db)

    # Mock adapter
    mock_adapter = mock.AsyncMock()
    mock_adapter.send_clarify.return_value = mock.MagicMock(success=True, message_id="msg-123")
    mock_adapter.send = mock.AsyncMock(return_value=mock.MagicMock(success=True))

    # Patch DB_PATH in the hitl module so fetch_pending uses tmp_db
    monkeypatch.setattr(hitl, "DB_PATH", tmp_db)

    # Patch the clarify_gateway module to avoid Hermes import errors
    fake_clarify = mock.MagicMock()
    fake_entry = mock.MagicMock()
    fake_entry.event = threading.Event()
    fake_clarify.register.return_value = fake_entry
    sys.modules.setdefault("tools.clarify_gateway", fake_clarify)
    sys.modules.setdefault("tools", mock.MagicMock())

    handler_mod = _load_handler_module()
    if handler_mod is None:
        pytest.skip("handler module not found")

    # Patch internal helpers in handler module
    monkeypatch.setattr(handler_mod, "_get_telegram_adapter", lambda: mock_adapter)
    monkeypatch.setattr(handler_mod, "_get_event_loop", lambda: None)

    # Patch fetch_pending and ensure_schema inside startup_hitl_scan (already in sys.modules)
    with mock.patch.object(hitl, "fetch_pending", return_value=hitl.fetch_pending(tmp_db)), \
         mock.patch.object(hitl, "ensure_schema", return_value=None):
        await handler_mod.handle("gateway:startup", {"platforms": ["telegram"]})

    # Assert send_clarify was called with the correct chat_id
    assert mock_adapter.send_clarify.called, "send_clarify was not called"
    call_args = mock_adapter.send_clarify.call_args
    # chat_id can be positional or keyword
    chat_id_value = (
        call_args.kwargs.get("chat_id")
        if call_args.kwargs
        else (call_args.args[0] if call_args.args else None)
    )
    assert chat_id_value == "7113965359", f"Expected chat_id 7113965359, got {chat_id_value}"


@pytest.mark.asyncio
async def test_handle_does_nothing_when_no_pending(tmp_db, monkeypatch):
    """If DB is empty, handle() should not call send_clarify."""
    hitl.ensure_schema(tmp_db)
    monkeypatch.setattr(hitl, "DB_PATH", tmp_db)

    mock_adapter = mock.AsyncMock()

    sys.modules.setdefault("tools.clarify_gateway", mock.MagicMock())
    sys.modules.setdefault("tools", mock.MagicMock())

    handler_mod = _load_handler_module()
    if handler_mod is None:
        pytest.skip("handler module not found")

    monkeypatch.setattr(handler_mod, "_get_telegram_adapter", lambda: mock_adapter)

    with mock.patch.object(hitl, "fetch_pending", return_value=[]), \
         mock.patch.object(hitl, "ensure_schema", return_value=None):
        await handler_mod.handle("gateway:startup", {"platforms": ["telegram"]})

    mock_adapter.send_clarify.assert_not_called()
