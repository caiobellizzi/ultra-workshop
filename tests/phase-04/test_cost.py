"""Tests for workshop/cost.py (Phase 4, Plan 1)."""
from __future__ import annotations

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Test C1: get_daily_spend() returns 0.0 when cost-ledger.md does not exist
# ---------------------------------------------------------------------------

def test_get_daily_spend_no_file(tmp_path, monkeypatch):
    import workshop.cost as cost_mod

    monkeypatch.setattr(cost_mod, "LEDGER_PATH", tmp_path / "nonexistent.md")

    assert cost_mod.get_daily_spend() == 0.0


# ---------------------------------------------------------------------------
# Test C2: check_circuit_breaker() raises BudgetExhausted at $20 spend
# ---------------------------------------------------------------------------

def test_check_circuit_breaker_raises_exhausted(monkeypatch):
    import workshop.cost as cost_mod

    monkeypatch.setattr(cost_mod, "get_daily_spend", lambda: 20.0)

    with pytest.raises(cost_mod.BudgetExhausted):
        cost_mod.check_circuit_breaker()


# ---------------------------------------------------------------------------
# Test C3: check_circuit_breaker(mode="cron") raises BudgetWarning at $18
# ---------------------------------------------------------------------------

def test_check_circuit_breaker_raises_warning_in_cron(monkeypatch):
    import workshop.cost as cost_mod

    monkeypatch.setattr(cost_mod, "get_daily_spend", lambda: 18.0)

    with pytest.raises(cost_mod.BudgetWarning):
        cost_mod.check_circuit_breaker(mode="cron")


# ---------------------------------------------------------------------------
# Test C4: check_circuit_breaker() does NOT raise when spend is $5
# ---------------------------------------------------------------------------

def test_check_circuit_breaker_no_raise_low_spend(monkeypatch):
    import workshop.cost as cost_mod

    monkeypatch.setattr(cost_mod, "get_daily_spend", lambda: 5.0)

    # Should not raise
    cost_mod.check_circuit_breaker()


# ---------------------------------------------------------------------------
# Test C5: check_circuit_breaker(mode="cron") does NOT raise below $18
# ---------------------------------------------------------------------------

def test_check_circuit_breaker_cron_no_raise_below_warn(monkeypatch):
    import workshop.cost as cost_mod

    monkeypatch.setattr(cost_mod, "get_daily_spend", lambda: 17.99)

    # Should not raise
    cost_mod.check_circuit_breaker(mode="cron")
