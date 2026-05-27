from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

# SC-3: audit log tests
# These tests are RED until workshop/ledger.py gains append_audit.
from workshop.ledger import append_audit


def test_append_audit_calls_ingest():
    with patch("workshop.ledger._brain_http") as mock_brain:
        mock_brain.call_agent = MagicMock(return_value={"ok": True})
        append_audit("ws-abc123", "wave_start", {"role": "correctness"})
        # Give the daemon thread a moment to fire
        time.sleep(0.1)
        mock_brain.call_agent.assert_called_once()
        call_args = mock_brain.call_agent.call_args
        assert call_args[0][0] == "ingest"


def test_append_audit_message_contains_task_id():
    with patch("workshop.ledger._brain_http") as mock_brain:
        mock_brain.call_agent = MagicMock(return_value={"ok": True})
        append_audit("ws-abc123", "wave_start", {"role": "correctness"})
        time.sleep(0.1)
        call_args = mock_brain.call_agent.call_args
        assert "workshop-audit/ws-abc123" in call_args[0][1]


def test_append_audit_is_nonblocking():
    event = threading.Event()

    def slow_call_agent(agent_id, message):
        event.wait(timeout=5.0)
        return {"ok": True}

    with patch("workshop.ledger._brain_http") as mock_brain:
        mock_brain.call_agent = slow_call_agent
        start = time.monotonic()
        append_audit("ws-abc123", "wave_start", {"role": "correctness"})
        elapsed = time.monotonic() - start
        # Should return well before the slow mock completes
        assert elapsed < 0.5, f"append_audit blocked for {elapsed:.2f}s (expected < 0.5s)"
        event.set()  # unblock the daemon thread
