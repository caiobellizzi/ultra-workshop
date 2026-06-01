"""Tests for spend_logs-derived reads (Workstream C): model-mix, estimate, deltas."""
from __future__ import annotations

import sqlite3

import pytest


@pytest.fixture()
def seeded_db(tmp_path, monkeypatch):
    db = tmp_path / "spend.sqlite"
    from dashboard.backend import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "spend_db", str(db))
    from dashboard.backend.services import cost_service as cs
    cs._ensure_schema(db)
    con = sqlite3.connect(str(db))
    rows = [
        ("m-fast", "t1", 0.10),
        ("m-fast", "t1", 0.20),
        ("m-slow", "t2", 0.50),
        ("m-slow", "t3", 0.30),
    ]
    for model, tid, cost in rows:
        con.execute(
            "INSERT INTO spend_logs(model, task_id, response_cost, total_tokens, start_time) VALUES(?,?,?,?,?)",
            (model, tid, cost, 100, "2026-06-01T10:00:00"),
        )
    con.commit()
    con.close()
    return db


def test_model_mix_all_and_filtered(seeded_db):
    from dashboard.backend.services import cost_service as cs

    by_alias = {r["alias"]: r["count"] for r in cs.get_model_mix()}
    assert by_alias == {"m-fast": 2, "m-slow": 2}
    filtered = {r["alias"]: r["count"] for r in cs.get_model_mix(["t1"])}
    assert filtered == {"m-fast": 2}


def test_estimate_global_fallback(seeded_db):
    from dashboard.backend.services import cost_service as cs

    est = cs.estimate_cost("owner/not-seen")  # repo has < 3 samples → global
    assert est["basis"] == "global"
    assert est["sample_size"] == 3            # t1, t2, t3 distinct
    assert est["p25_cents"] <= est["p50_cents"] <= est["p75_cents"]


def test_estimate_empty_db(tmp_path, monkeypatch):
    from dashboard.backend import config as cfg_module
    monkeypatch.setattr(cfg_module.settings, "spend_db", str(tmp_path / "none.sqlite"))
    from dashboard.backend.services import cost_service as cs
    est = cs.estimate_cost("any/repo")
    assert est == {"p25_cents": 0, "p50_cents": 0, "p75_cents": 0, "sample_size": 0, "basis": "none"}


def test_latest_spend_for_task(seeded_db):
    from dashboard.backend.services import cost_service as cs

    latest = cs.latest_spend_for_task("t1")
    assert latest == {"model": "m-fast", "tokens": 100}
    assert cs.latest_spend_for_task("nope") is None
