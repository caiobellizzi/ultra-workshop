"""Tests for run_events service: write + read-helper round-trip (Workstream A)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def tmp_spend_db(tmp_path, monkeypatch):
    """Point settings.spend_db at a throwaway SQLite file."""
    db = tmp_path / "spend.sqlite"
    from dashboard.backend import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "spend_db", str(db))
    return db


def _iso(t: datetime) -> str:
    return t.isoformat()


def test_record_and_skill_stats(tmp_spend_db):
    from dashboard.backend.services import run_events

    t0 = datetime.now(timezone.utc)
    run_events.record_run_event({
        "task_id": "ws-abc", "stage": "coder", "agent": "coder-specialist",
        "model": "coder-model", "started_at": _iso(t0),
        "ended_at": _iso(t0 + timedelta(seconds=10)), "outcome": "completed",
    })
    stats = run_events.skill_stats()
    assert len(stats) == 1
    assert stats[0]["agent"] == "coder-specialist"
    assert stats[0]["runs_today"] == 1
    assert stats[0]["avg_duration_seconds"] == pytest.approx(10.0, abs=0.5)


def test_reviewer_stats_aggregates_issues(tmp_spend_db):
    from dashboard.backend.services import run_events

    t0 = datetime.now(timezone.utc)
    for secs, issues in ((5, 3), (7, 1)):
        run_events.record_run_event({
            "task_id": "ws-abc", "stage": "reviewer", "agent": "security-reviewer",
            "model": "reviewer-model", "started_at": _iso(t0),
            "ended_at": _iso(t0 + timedelta(seconds=secs)),
            "outcome": "completed", "issues_found": issues,
        })
    rstats = run_events.reviewer_stats()
    assert len(rstats) == 1
    row = rstats[0]
    assert row["role"] == "security"          # "-reviewer" suffix stripped
    assert row["reviews_run"] == 2
    assert row["issues_found"] == 4           # 3 + 1 summed
    assert row["avg_latency_seconds"] == pytest.approx(6.0, abs=0.5)


def test_latest_for_task_returns_most_recent(tmp_spend_db):
    from dashboard.backend.services import run_events

    t0 = datetime.now(timezone.utc)
    run_events.record_run_event({
        "task_id": "ws-z", "stage": "planner", "agent": "planner-specialist",
        "started_at": _iso(t0), "ended_at": _iso(t0 + timedelta(seconds=3)),
        "outcome": "completed",
    })
    run_events.record_run_event({
        "task_id": "ws-z", "stage": "coder", "agent": "coder-specialist",
        "started_at": _iso(t0 + timedelta(seconds=10)),
        "ended_at": _iso(t0 + timedelta(seconds=20)), "outcome": "completed",
    })
    latest = run_events.latest_for_task("ws-z")
    assert latest is not None
    assert latest["stage"] == "coder"


def test_empty_db_returns_empty(tmp_spend_db):
    from dashboard.backend.services import run_events

    assert run_events.skill_stats() == []
    assert run_events.reviewer_stats() == []
    assert run_events.latest_for_task("nope") is None
