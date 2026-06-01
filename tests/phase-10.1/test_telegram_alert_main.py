from __future__ import annotations

"""
Unit tests for hermes-skills/telegram_alert.py main() (Phase 10.1, REQ-ws-021).

Covers:
  - main() reads stdin JSON and calls send_alert(text, chat_id=...)
  - main() falls back to DEFAULT_CHAT_ID when "chat_id" absent
  - send_alert() signature is unchanged (message: str, chat_id: str = DEFAULT_CHAT_ID)
  - main() raises SystemExit on malformed JSON

The signature test runs immediately. The main() tests skip cleanly until main()
is added (Task 3), then go GREEN.
"""

import inspect
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_HERMES_DIR = _PROJECT_ROOT / "hermes-skills"
for _p in (str(_PROJECT_ROOT), str(_HERMES_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import telegram_alert  # noqa: E402

_HAS_MAIN = hasattr(telegram_alert, "main")
_needs_main = pytest.mark.skipif(_HAS_MAIN is False, reason="telegram_alert.main() not yet added (Task 3)")


def test_send_alert_signature_unchanged():
    sig = inspect.signature(telegram_alert.send_alert)
    params = list(sig.parameters.values())
    assert params[0].name == "message"
    assert params[1].name == "chat_id"
    assert params[1].default == telegram_alert.DEFAULT_CHAT_ID


@_needs_main
def test_main_reads_stdin_and_calls_send_alert(monkeypatch):
    monkeypatch.setattr(
        sys, "stdin", io.StringIO(json.dumps({"text": "hello", "chat_id": "999"}))
    )
    with patch.object(telegram_alert, "send_alert") as mock_send:
        telegram_alert.main()
    mock_send.assert_called_once_with("hello", chat_id="999")


@_needs_main
def test_main_uses_default_chat_id_when_absent(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"text": "hello"})))
    with patch.object(telegram_alert, "send_alert") as mock_send:
        telegram_alert.main()
    mock_send.assert_called_once_with("hello", chat_id=telegram_alert.DEFAULT_CHAT_ID)


@_needs_main
def test_main_invalid_json_raises_system_exit(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not-valid-json{"))
    with patch.object(telegram_alert, "send_alert"):
        with pytest.raises(SystemExit):
            telegram_alert.main()
