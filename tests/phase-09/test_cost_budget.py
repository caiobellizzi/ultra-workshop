from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# SC-2: per-role budget tests
# These tests are RED until workshop/cost.py gains the new symbols.
from workshop.cost import (
    ROLE_MONTHLY_CAPS,
    RoleBudgetExhausted,
    RoleBudgetWarning,
    check_role_budget,
    get_role_monthly_spend,
    record_role_cost,
)


def test_role_budget_caps_defined():
    assert ROLE_MONTHLY_CAPS["security"] == 4000
    assert ROLE_MONTHLY_CAPS["correctness"] == 3000


def test_check_role_budget_raises_exhausted():
    cap = ROLE_MONTHLY_CAPS["security"]
    with patch("workshop.cost.get_role_monthly_spend", return_value=float(cap)):
        with patch("workshop.cost._brain_http") as mock_brain:
            mock_brain.call_agent = MagicMock(return_value={"ok": True})
            with pytest.raises(RoleBudgetExhausted):
                check_role_budget("security")


def test_check_role_budget_raises_warning_at_80pct():
    cap = ROLE_MONTHLY_CAPS["security"]
    spend_80 = cap * 0.8
    with patch("workshop.cost.get_role_monthly_spend", return_value=spend_80):
        with patch("workshop.cost._brain_http") as mock_brain:
            mock_brain.call_agent = MagicMock(return_value={"ok": True})
            with pytest.raises(RoleBudgetWarning):
                check_role_budget("security")


def test_record_role_cost_calls_curator():
    with patch("workshop.cost._brain_http") as mock_brain:
        mock_brain.call_agent = MagicMock(return_value={"ok": True})
        record_role_cost("security", 0.05, "reviewer-model")
        mock_brain.call_agent.assert_called_once()
        call_args = mock_brain.call_agent.call_args
        assert call_args[0][0] == "curator"
        assert "role=security" in call_args[0][1]


def test_check_role_budget_sends_telegram_warn_at_80pct():
    cap = ROLE_MONTHLY_CAPS["security"]
    spend_80 = cap * 0.8
    with patch("workshop.cost.get_role_monthly_spend", return_value=spend_80):
        with patch("workshop.cost._brain_http") as mock_brain:
            mock_brain.call_agent = MagicMock(return_value={"ok": True})
            with pytest.raises(RoleBudgetWarning):
                check_role_budget("security")
            # Must have called notify with WARNING message
            notify_calls = [
                c for c in mock_brain.call_agent.call_args_list
                if c[0][0] == "notify"
            ]
            assert notify_calls, "Expected call_agent('notify', ...) at 80%"
            assert "WARNING" in notify_calls[0][0][1]


def test_check_role_budget_sends_telegram_alert_at_100pct():
    cap = ROLE_MONTHLY_CAPS["security"]
    with patch("workshop.cost.get_role_monthly_spend", return_value=float(cap)):
        with patch("workshop.cost._brain_http") as mock_brain:
            mock_brain.call_agent = MagicMock(return_value={"ok": True})
            with pytest.raises(RoleBudgetExhausted):
                check_role_budget("security")
            notify_calls = [
                c for c in mock_brain.call_agent.call_args_list
                if c[0][0] == "notify"
            ]
            assert notify_calls, "Expected call_agent('notify', ...) at 100%"
            assert "AUTO-PAUSE" in notify_calls[0][0][1]
