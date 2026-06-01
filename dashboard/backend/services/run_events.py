"""Run-events service — pipeline stage/reviewer telemetry.

Stores a `run_events` table inside the existing `spend.sqlite` (decision 1).
Written via POST /internal/run-event (mirrors /internal/spend-update); the
pipeline emits fire-and-forget so DB access stays in the dashboard backend.

Read helpers feed the Skills run-stats and Reviewers telemetry surfaces.
"""
from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from dashboard.backend.config import settings


# ---------------------------------------------------------------------------
# Schema bootstrap (shares the spend.sqlite file with cost_service)
# ---------------------------------------------------------------------------

_CREATE_RUN_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS run_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    stage TEXT,
    agent TEXT,
    model TEXT,
    started_at TEXT,
    ended_at TEXT,
    outcome TEXT,
    issues_found INTEGER,
    recorded_at TEXT DEFAULT (datetime('now'))
);
"""

_CREATE_IDX_AGENT = "CREATE INDEX IF NOT EXISTS idx_run_events_agent ON run_events(agent);"
_CREATE_IDX_TASK = "CREATE INDEX IF NOT EXISTS idx_run_events_task ON run_events(task_id);"


def _db() -> Path:
    return Path(settings.spend_db)


def _ensure_schema(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(_CREATE_RUN_EVENTS_TABLE)
        conn.execute(_CREATE_IDX_AGENT)
        conn.execute(_CREATE_IDX_TASK)
        conn.commit()


def _duration_seconds_expr() -> str:
    """SQL expression for event duration in seconds (NULL when timestamps absent)."""
    # ISO-8601 strings sort/parse via julianday; 86400 seconds per day.
    return (
        "(julianday(ended_at) - julianday(started_at)) * 86400.0"
    )


# ---------------------------------------------------------------------------
# Write (called by /internal/run-event)
# ---------------------------------------------------------------------------

def record_run_event(entry: dict[str, Any]) -> int:
    """Insert a single run-event. Returns 1 on success, 0 on no-op."""
    db_path = _db()
    _ensure_schema(db_path)
    issues = entry.get("issues_found")
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            INSERT INTO run_events
                (task_id, stage, agent, model, started_at, ended_at, outcome, issues_found)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.get("task_id") or None,
                entry.get("stage"),
                entry.get("agent"),
                entry.get("model"),
                entry.get("started_at"),
                entry.get("ended_at"),
                entry.get("outcome"),
                int(issues) if issues is not None else None,
            ),
        )
        conn.commit()
    return 1


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------

def skill_stats() -> list[dict[str, Any]]:
    """Per-agent run stats for today: runs_today, avg_duration_seconds, last_run."""
    db_path = _db()
    if not db_path.exists():
        return []
    today = date.today().isoformat()
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(
            f"""
            SELECT agent,
                   COUNT(*) AS runs,
                   AVG({_duration_seconds_expr()}) AS avg_dur,
                   MAX(ended_at) AS last_run
            FROM run_events
            WHERE agent IS NOT NULL
              AND substr(COALESCE(started_at, recorded_at), 1, 10) = ?
            GROUP BY agent
            ORDER BY runs DESC
            """,
            (today,),
        ).fetchall()
    return [
        {
            "agent": r[0],
            "runs_today": int(r[1]),
            "avg_duration_seconds": round(float(r[2]), 2) if r[2] is not None else None,
            "last_run": r[3],
        }
        for r in rows
    ]


def reviewer_stats() -> list[dict[str, Any]]:
    """Per-role reviewer telemetry: reviews_run, issues_found, avg_latency, last_run.

    Reviewer events use agent == "<role>-reviewer"; the role is the agent name
    with the trailing "-reviewer" stripped.
    """
    db_path = _db()
    if not db_path.exists():
        return []
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute(
            f"""
            SELECT agent,
                   COUNT(*) AS reviews,
                   COALESCE(SUM(issues_found), 0) AS issues,
                   AVG({_duration_seconds_expr()}) AS avg_lat,
                   MAX(ended_at) AS last_run
            FROM run_events
            WHERE agent LIKE '%-reviewer'
            GROUP BY agent
            ORDER BY reviews DESC
            """,
        ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        agent = r[0] or ""
        role = agent[: -len("-reviewer")] if agent.endswith("-reviewer") else agent
        out.append(
            {
                "role": role,
                "reviews_run": int(r[1]),
                "issues_found": int(r[2]),
                "avg_latency_seconds": round(float(r[3]), 2) if r[3] is not None else None,
                "last_run": r[4],
            }
        )
    return out


def latest_for_task(task_id: str) -> dict[str, Any] | None:
    """Most recent run-event for a task (used to enrich HITL cost strip)."""
    db_path = _db()
    if not db_path.exists():
        return None
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute(
            """
            SELECT task_id, stage, agent, model, started_at, ended_at, outcome, issues_found
            FROM run_events
            WHERE task_id = ?
            ORDER BY COALESCE(ended_at, started_at, recorded_at) DESC
            LIMIT 1
            """,
            (task_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "task_id": row[0],
        "stage": row[1],
        "agent": row[2],
        "model": row[3],
        "started_at": row[4],
        "ended_at": row[5],
        "outcome": row[6],
        "issues_found": row[7],
    }
