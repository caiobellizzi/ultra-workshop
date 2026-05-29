"""Tests for hitl_service against a seeded SQLite database."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


def _seed_hitl_db(db_path: Path) -> None:
    """Create and seed a pending_hitl.db with test rows."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    create_sql = """
    CREATE TABLE IF NOT EXISTS pending_hitl (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        message_id TEXT,
        task_description TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending',
        telegram_chat_id TEXT NOT NULL,
        telegram_message_id TEXT,
        approved_at TIMESTAMP,
        approved_by TEXT
    );
    """
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(create_sql)
        conn.execute(
            "INSERT INTO pending_hitl (session_id, task_description, status, telegram_chat_id) VALUES (?, ?, ?, ?)",
            ("sess-001", "Approve PR merge for task-abc", "pending", "12345"),
        )
        conn.execute(
            "INSERT INTO pending_hitl (session_id, task_description, status, telegram_chat_id) VALUES (?, ?, ?, ?)",
            ("sess-002", "Timeout recovery for task-xyz", "approved", "12345"),
        )
        conn.commit()


@pytest.fixture()
def seeded_hitl_db(tmp_path):
    db_path = tmp_path / "pending_hitl.db"
    _seed_hitl_db(db_path)
    return db_path


class TestListPending:
    def test_returns_only_pending_rows(self, seeded_hitl_db, monkeypatch):
        from dashboard.backend import config as cfg_module
        monkeypatch.setattr(cfg_module.settings, "hitl_db", str(seeded_hitl_db))

        # Also patch the hitl_service to use the seeded db directly
        import importlib.util
        from pathlib import Path as _Path

        # We test fetch_pending directly since list_pending delegates to it
        spec = importlib.util.spec_from_file_location(
            "startup_hitl_scan",
            _Path(__file__).parent.parent.parent.parent / "hermes-skills" / "startup-hitl-scan.py",
        )
        if spec is None:
            pytest.skip("startup-hitl-scan.py not found (VPS-only path)")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        rows = mod.fetch_pending(db_path=seeded_hitl_db)
        assert len(rows) == 1
        assert rows[0]["status"] == "pending"
        assert rows[0]["session_id"] == "sess-001"

    def test_no_db_returns_empty(self, tmp_path, monkeypatch):
        nonexistent = tmp_path / "no-such.db"
        from dashboard.backend import config as cfg_module
        monkeypatch.setattr(cfg_module.settings, "hitl_db", str(nonexistent))

        from dashboard.backend.services.hitl_service import list_pending
        result = list_pending()
        assert result == []


class TestCostService:
    def test_record_and_read_spend(self, tmp_path, monkeypatch):
        """Test that spend batch writes and reads back correctly."""
        spend_db = tmp_path / "spend.sqlite"
        from dashboard.backend import config as cfg_module
        monkeypatch.setattr(cfg_module.settings, "spend_db", str(spend_db))

        from dashboard.backend.services.cost_service import get_task_spend, record_spend_batch

        entries = [
            {
                "request_id": "req-1",
                "model": "coder-worker",
                "response_cost": 0.0025,
                "user": "task-abc",
                "start_time": "2026-05-29T10:00:00",
            },
            {
                "request_id": "req-2",
                "model": "reviewer-model",
                "response_cost": 0.0010,
                "user": "task-abc",
                "start_time": "2026-05-29T10:01:00",
            },
        ]
        count = record_spend_batch(entries)
        assert count == 2

        result = get_task_spend("task-abc")
        assert result["task_id"] == "task-abc"
        assert abs(result["total_usd"] - 0.0035) < 1e-9
        assert len(result["breakdown"]) == 2

    def test_daily_totals_empty_db(self, tmp_path, monkeypatch):
        from dashboard.backend import config as cfg_module
        monkeypatch.setattr(cfg_module.settings, "spend_db", str(tmp_path / "nonexistent.sqlite"))
        monkeypatch.setattr(cfg_module.settings, "cost_ledger_md", str(tmp_path / "no-ledger.md"))

        from dashboard.backend.services.cost_service import get_daily_totals
        result = get_daily_totals()
        assert result == []

    def test_model_totals_empty_db(self, tmp_path, monkeypatch):
        from dashboard.backend import config as cfg_module
        monkeypatch.setattr(cfg_module.settings, "spend_db", str(tmp_path / "nonexistent.sqlite"))

        from dashboard.backend.services.cost_service import get_model_totals
        result = get_model_totals()
        assert result == []
