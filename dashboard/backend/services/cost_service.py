"""Cost service — reads from spend.sqlite (LiteLLM spend logs) with fallback
to cost-ledger.md for daily totals.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

from dashboard.backend.config import settings


# ---------------------------------------------------------------------------
# SQLite schema bootstrap
# ---------------------------------------------------------------------------

_CREATE_SPEND_TABLE = """
CREATE TABLE IF NOT EXISTS spend_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT,
    call_type TEXT,
    model TEXT,
    total_tokens INTEGER,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    response_cost REAL,
    task_id TEXT,
    metadata TEXT,
    start_time TEXT,
    end_time TEXT,
    recorded_at TEXT DEFAULT (datetime('now'))
);
"""

_CREATE_IDX_DATE = "CREATE INDEX IF NOT EXISTS idx_spend_date ON spend_logs(start_time);"
_CREATE_IDX_TASK = "CREATE INDEX IF NOT EXISTS idx_spend_task ON spend_logs(task_id);"


def _ensure_schema(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(_CREATE_SPEND_TABLE)
        conn.execute(_CREATE_IDX_DATE)
        conn.execute(_CREATE_IDX_TASK)
        conn.commit()


def _spend_db() -> Path:
    return Path(settings.spend_db)


# ---------------------------------------------------------------------------
# Write (called by /internal/spend-update)
# ---------------------------------------------------------------------------

def record_spend_batch(entries: list[dict[str, Any]]) -> int:
    """Insert a batch of LiteLLM spend log entries. Returns count inserted."""
    db_path = _spend_db()
    _ensure_schema(db_path)
    inserted = 0
    with sqlite3.connect(str(db_path)) as conn:
        for entry in entries:
            import json
            task_id = (
                entry.get("user")
                or (entry.get("metadata") or {}).get("task_id")
                or ""
            )
            meta = entry.get("metadata")
            conn.execute(
                """
                INSERT INTO spend_logs
                    (request_id, call_type, model, total_tokens, prompt_tokens,
                     completion_tokens, response_cost, task_id, metadata, start_time, end_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.get("request_id"),
                    entry.get("call_type"),
                    entry.get("model"),
                    entry.get("total_tokens"),
                    entry.get("prompt_tokens"),
                    entry.get("completion_tokens"),
                    entry.get("response_cost"),
                    task_id or None,
                    json.dumps(meta) if meta else None,
                    entry.get("start_time"),
                    entry.get("end_time"),
                ),
            )
            inserted += 1
        conn.commit()
    return inserted


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

def get_daily_spend_db(target_date: str | None = None) -> float:
    """Return total spend (USD) for a date from spend.sqlite."""
    db_path = _spend_db()
    if not db_path.exists():
        return 0.0
    d = target_date or date.today().isoformat()
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(response_cost), 0) FROM spend_logs WHERE start_time LIKE ?",
            (f"{d}%",),
        ).fetchone()
    return float(row[0]) if row else 0.0


def get_daily_totals(days: int = 30) -> list[dict[str, Any]]:
    """Return daily spend totals for the last *days* days."""
    db_path = _spend_db()
    if not db_path.exists():
        return _daily_totals_from_ledger(days)

    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(
            """
            SELECT substr(start_time, 1, 10) AS day,
                   COALESCE(SUM(response_cost), 0) AS total
            FROM spend_logs
            WHERE start_time IS NOT NULL
            GROUP BY day
            ORDER BY day DESC
            LIMIT ?
            """,
            (days,),
        ).fetchall()

    if not rows:
        return _daily_totals_from_ledger(days)
    return [{"date": r[0], "total_usd": round(float(r[1]), 6)} for r in rows]


def _daily_totals_from_ledger(days: int = 30) -> list[dict[str, Any]]:
    """Fallback: parse cost-ledger.md for daily totals."""
    import re

    path = Path(settings.cost_ledger_md)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    daily: dict[str, float] = {}
    for line in text.splitlines():
        m_date = re.search(r"(\d{4}-\d{2}-\d{2})", line)
        m_amount = re.search(r"amount:\s*([\d.]+)", line)
        if m_date and m_amount:
            d = m_date.group(1)
            daily[d] = daily.get(d, 0.0) + float(m_amount.group(1))
    results = sorted(daily.items(), reverse=True)[:days]
    return [{"date": d, "total_usd": round(v, 6)} for d, v in results]


def get_task_spend(task_id: str) -> dict[str, Any]:
    """Return total spend and per-model breakdown for a task_id."""
    db_path = _spend_db()
    if not db_path.exists():
        return {"task_id": task_id, "total_usd": 0.0, "breakdown": []}

    with sqlite3.connect(str(db_path)) as conn:
        total_row = conn.execute(
            "SELECT COALESCE(SUM(response_cost), 0) FROM spend_logs WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        breakdown_rows = conn.execute(
            """
            SELECT model,
                   COALESCE(SUM(response_cost), 0) AS cost,
                   COUNT(*) AS reqs
            FROM spend_logs
            WHERE task_id = ?
            GROUP BY model
            ORDER BY cost DESC
            """,
            (task_id,),
        ).fetchall()

    total = float(total_row[0]) if total_row else 0.0
    breakdown = [
        {"model": r[0] or "unknown", "total_usd": round(float(r[1]), 6), "request_count": int(r[2])}
        for r in breakdown_rows
    ]
    return {"task_id": task_id, "total_usd": round(total, 6), "breakdown": breakdown}


def get_model_totals() -> list[dict[str, Any]]:
    """Return per-model spend totals."""
    db_path = _spend_db()
    if not db_path.exists():
        return []
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(
            """
            SELECT model,
                   COALESCE(SUM(response_cost), 0) AS cost,
                   COUNT(*) AS reqs
            FROM spend_logs
            GROUP BY model
            ORDER BY cost DESC
            """,
        ).fetchall()
    return [
        {"model": r[0] or "unknown", "total_usd": round(float(r[1]), 6), "request_count": int(r[2])}
        for r in rows
    ]


def get_roles_spend() -> list[dict[str, Any]]:
    """Return per-role monthly spend using workshop.cost module + caps."""
    try:
        from workshop.cost import ROLE_MONTHLY_CAPS, get_role_monthly_spend

        results = []
        for role, cap in ROLE_MONTHLY_CAPS.items():
            try:
                spend = get_role_monthly_spend(role)
            except Exception:
                spend = 0.0
            pct = round(spend / cap * 100, 1) if cap > 0 else 0.0
            results.append(
                {"role": role, "monthly_cents": spend, "cap_cents": cap, "pct": pct}
            )
        return results
    except ImportError:
        return []
