"""
startup-hitl-scan — HITL restart-resilience helper for ultra-workshop.

This module provides:

  record_hitl_pause(session_id, task_description, chat_id)
      Called by any code that issues a clarify() before doing so.
      Writes a pending row to pending_hitl.db so the startup hook can
      re-emit the Telegram inline keyboard if Hermes restarts mid-flow.

  ensure_schema(db_path)
      Creates the pending_hitl table if it does not exist.

  DB_PATH
      Canonical location: /home/uws/.ultra-workshop/pending_hitl.db

Deploy location: /opt/ultra-workshop/hermes-skills/startup-hitl-scan.py

The actual gateway:startup hook lives in:
  /home/uws/.hermes/hooks/startup-hitl-scan/handler.py
  /home/uws/.hermes/hooks/startup-hitl-scan/HOOK.yaml

This module is imported by handler.py at runtime.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path("/home/uws/.ultra-workshop/pending_hitl.db")

CREATE_TABLE_SQL = """
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


def ensure_schema(db_path: Path = DB_PATH) -> None:
    """Create the pending_hitl table if it does not exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()
    # Enforce permissions: 0600 (owner rw only)
    os.chmod(str(db_path), 0o600)


def record_hitl_pause(
    session_id: str,
    task_description: str,
    chat_id: str,
    message_id: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> int:
    """Write a pending HITL row and return its row id.

    Call this BEFORE issuing clarify() so that a restart can re-emit
    the inline keyboard.

    Args:
        session_id: Hermes session identifier.
        task_description: Human-readable description of what needs approval.
        chat_id: Telegram chat_id to re-send the keyboard to.
        message_id: Optional Hermes message_id for cross-referencing.
        db_path: Override DB path (for testing).

    Returns:
        The inserted row id.
    """
    ensure_schema(db_path)
    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.execute(
            """
            INSERT INTO pending_hitl
                (session_id, message_id, task_description, status, telegram_chat_id)
            VALUES (?, ?, ?, 'pending', ?)
            """,
            (session_id, message_id, task_description, chat_id),
        )
        conn.commit()
        return cur.lastrowid


def update_hitl_message_id(row_id: int, telegram_message_id: str, db_path: Path = DB_PATH) -> None:
    """Update the telegram_message_id after re-emission."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "UPDATE pending_hitl SET telegram_message_id = ? WHERE id = ?",
            (str(telegram_message_id), row_id),
        )
        conn.commit()


def resolve_hitl_row(
    row_id: int,
    decision: str,
    approved_by: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> None:
    """Mark a row as approved or rejected with timestamp.

    Args:
        row_id: The pending_hitl.id to resolve.
        decision: 'approved' or 'rejected'.
        approved_by: Telegram user display name (for audit trail).
        db_path: Override DB path (for testing).
    """
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            UPDATE pending_hitl
            SET status = ?,
                approved_at = CURRENT_TIMESTAMP,
                approved_by = ?
            WHERE id = ?
            """,
            (decision, approved_by, row_id),
        )
        conn.commit()


def fetch_pending(db_path: Path = DB_PATH) -> list:
    """Return all rows with status='pending'.

    Each row is a dict with keys matching the pending_hitl columns.
    Returns [] if the DB does not exist or the table is empty.
    """
    if not db_path.exists():
        return []
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM pending_hitl WHERE status = 'pending' ORDER BY created_at"
            )
            return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error:
        return []
