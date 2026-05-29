"""Cost service — reads from spend.sqlite (LiteLLM spend logs) with fallback
to cost-ledger.md for daily totals.
"""
from __future__ import annotations

import json
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


def _usd_to_cents(usd: float) -> int:
    return int(round(usd * 100))


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


def _load_task_data(task_id: str) -> dict[str, Any]:
    """Load state.json for a task_id; returns {} on any error."""
    state_file = Path(settings.tasks_base) / task_id / "state.json"
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_task_spend(task_id: str) -> dict[str, Any]:
    """Return per-task cost in the TaskCostRowResponse shape (cents)."""
    db_path = _spend_db()

    task_data = _load_task_data(task_id)
    goal = str(task_data.get("goal", ""))
    repo = str(task_data.get("repo", ""))
    status = str(task_data.get("status", "unknown"))
    created_at = str(task_data.get("created_at", ""))
    date_str = created_at[:10] if created_at else ""

    if not db_path.exists():
        return {
            "task_id": task_id,
            "goal": goal,
            "repo": repo,
            "date": date_str,
            "status": status,
            "stage_costs": {},
            "total_cents": 0,
            "wave_breakdown": [],
        }

    with sqlite3.connect(str(db_path)) as conn:
        total_row = conn.execute(
            "SELECT COALESCE(SUM(response_cost), 0) FROM spend_logs WHERE task_id = ?",
            (task_id,),
        ).fetchone()

        # wave_breakdown: group by model (used as role), sum tokens + cost
        wave_rows = conn.execute(
            """
            SELECT model,
                   COALESCE(SUM(total_tokens), 0) AS tokens,
                   COALESCE(SUM(response_cost), 0) AS cost
            FROM spend_logs
            WHERE task_id = ?
            GROUP BY model
            ORDER BY cost DESC
            """,
            (task_id,),
        ).fetchall()

        # stage_costs: group by call_type
        stage_rows = conn.execute(
            """
            SELECT call_type,
                   COALESCE(SUM(response_cost), 0) AS cost
            FROM spend_logs
            WHERE task_id = ?
            GROUP BY call_type
            """,
            (task_id,),
        ).fetchall()

    total_usd = float(total_row[0]) if total_row else 0.0
    wave_breakdown = [
        {
            "role": r[0] or "unknown",
            "tokens_used": int(r[1]),
            "cost_cents": _usd_to_cents(float(r[2])),
        }
        for r in wave_rows
    ]
    stage_costs = {
        (r[0] or "unknown"): _usd_to_cents(float(r[1]))
        for r in stage_rows
    }

    return {
        "task_id": task_id,
        "goal": goal,
        "repo": repo,
        "date": date_str,
        "status": status,
        "stage_costs": stage_costs,
        "total_cents": _usd_to_cents(total_usd),
        "wave_breakdown": wave_breakdown,
    }


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
    month = datetime.now().strftime("%Y-%m")
    try:
        from workshop.cost import ROLE_MONTHLY_CAPS, get_role_monthly_spend

        results = []
        for role, cap in ROLE_MONTHLY_CAPS.items():
            try:
                spend = get_role_monthly_spend(role)
            except Exception:
                spend = 0
            results.append(
                {"role": role, "spend_cents": int(spend), "cap_cents": int(cap), "month": month}
            )
        return results
    except ImportError:
        return []


# ---------------------------------------------------------------------------
# New aggregated endpoints
# ---------------------------------------------------------------------------

def get_summary() -> dict[str, Any]:
    """Return CostSummaryResponse data."""
    today = date.today().isoformat()
    month_prefix = today[:7]  # "YYYY-MM"

    db_path = _spend_db()
    daily_limit_cents = 0  # no setting defined; default to 0

    if not db_path.exists():
        return {
            "today_cents": 0,
            "daily_limit_cents": daily_limit_cents,
            "this_month_cents": 0,
            "per_task_avg_cents": 0,
            "most_expensive_alias": "",
        }

    with sqlite3.connect(str(db_path)) as conn:
        today_usd = float(
            conn.execute(
                "SELECT COALESCE(SUM(response_cost), 0) FROM spend_logs WHERE start_time LIKE ?",
                (f"{today}%",),
            ).fetchone()[0]
        )
        month_usd = float(
            conn.execute(
                "SELECT COALESCE(SUM(response_cost), 0) FROM spend_logs WHERE start_time LIKE ?",
                (f"{month_prefix}%",),
            ).fetchone()[0]
        )
        # average per distinct task_id (exclude NULLs)
        avg_row = conn.execute(
            """
            SELECT COALESCE(AVG(task_total), 0)
            FROM (
                SELECT task_id, SUM(response_cost) AS task_total
                FROM spend_logs
                WHERE task_id IS NOT NULL AND task_id != ''
                GROUP BY task_id
            )
            """
        ).fetchone()
        per_task_avg_usd = float(avg_row[0]) if avg_row else 0.0

        # most expensive model this month
        alias_row = conn.execute(
            """
            SELECT model
            FROM spend_logs
            WHERE start_time LIKE ?
            GROUP BY model
            ORDER BY SUM(response_cost) DESC
            LIMIT 1
            """,
            (f"{month_prefix}%",),
        ).fetchone()
        most_expensive_alias = alias_row[0] or "" if alias_row else ""

    return {
        "today_cents": _usd_to_cents(today_usd),
        "daily_limit_cents": daily_limit_cents,
        "this_month_cents": _usd_to_cents(month_usd),
        "per_task_avg_cents": _usd_to_cents(per_task_avg_usd),
        "most_expensive_alias": most_expensive_alias,
    }


def get_tasks_spend(from_date: str | None = None, to_date: str | None = None) -> list[dict[str, Any]]:
    """Return TaskCostRowResponse data for all tasks with spend."""
    db_path = _spend_db()
    if not db_path.exists():
        return []

    # Build date filter clause
    clauses: list[str] = []
    params: list[str] = []
    if from_date:
        clauses.append("start_time >= ?")
        params.append(from_date)
    if to_date:
        clauses.append("start_time <= ?")
        params.append(to_date + "T23:59:59")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    with sqlite3.connect(str(db_path)) as conn:
        task_rows = conn.execute(
            f"""
            SELECT task_id,
                   COALESCE(SUM(response_cost), 0) AS total_cost
            FROM spend_logs
            {where}
            GROUP BY task_id
            ORDER BY total_cost DESC
            """,
            params,
        ).fetchall()

        wave_rows = conn.execute(
            f"""
            SELECT task_id, model,
                   COALESCE(SUM(total_tokens), 0) AS tokens,
                   COALESCE(SUM(response_cost), 0) AS cost
            FROM spend_logs
            {where}
            GROUP BY task_id, model
            """,
            params,
        ).fetchall()

        stage_rows = conn.execute(
            f"""
            SELECT task_id, call_type,
                   COALESCE(SUM(response_cost), 0) AS cost
            FROM spend_logs
            {where}
            GROUP BY task_id, call_type
            """,
            params,
        ).fetchall()

    # Index wave and stage data by task_id
    wave_by_task: dict[str, list[dict[str, Any]]] = {}
    for task_id, model, tokens, cost in wave_rows:
        wave_by_task.setdefault(task_id or "", []).append({
            "role": model or "unknown",
            "tokens_used": int(tokens),
            "cost_cents": _usd_to_cents(float(cost)),
        })

    stage_by_task: dict[str, dict[str, int]] = {}
    for task_id, call_type, cost in stage_rows:
        key = task_id or ""
        stage_by_task.setdefault(key, {})[call_type or "unknown"] = _usd_to_cents(float(cost))

    results = []
    for task_id, total_usd in task_rows:
        task_id = task_id or ""
        task_data = _load_task_data(task_id) if task_id else {}
        created_at = str(task_data.get("created_at", ""))
        results.append({
            "task_id": task_id,
            "goal": str(task_data.get("goal", "")),
            "repo": str(task_data.get("repo", "")),
            "date": created_at[:10] if created_at else "",
            "status": str(task_data.get("status", "unknown")),
            "stage_costs": stage_by_task.get(task_id, {}),
            "total_cents": _usd_to_cents(float(total_usd)),
            "wave_breakdown": wave_by_task.get(task_id, []),
        })
    return results


def get_trends(from_date: str | None = None, to_date: str | None = None) -> dict[str, Any]:
    """Return CostTrendsResponse data."""
    month = datetime.now().strftime("%Y-%m")

    daily_raw = get_daily_totals(days=90)
    model_raw = get_model_totals()
    roles_raw = get_roles_spend()

    daily = [{"date": r["date"], "cents": _usd_to_cents(r["total_usd"])} for r in daily_raw]
    by_model = [{"alias": r["model"], "cents": _usd_to_cents(r["total_usd"])} for r in model_raw]
    by_role = [
        {
            "role": r["role"],
            "spend_cents": r["spend_cents"],
            "cap_cents": r["cap_cents"],
            "month": r["month"],
        }
        for r in roles_raw
    ]

    return {"daily": daily, "by_model": by_model, "by_role": by_role}
