from __future__ import annotations

"""
Unit tests for hermes-skills/link_orphans.py (Phase 10.1, REQ-ws-020).

Covers:
  - main() with empty orphans → posts fallback message, exits 0
  - main() with orphans → formats "⚠️ Orphan vault notes:" message
  - main() with missing "orphans" key → posts fallback message
  - main() does NOT call brain_http.mark_queue_entry_dispatched (ACK is the caller's job)

Before link_orphans.py exists (Task 2), these tests skip cleanly so Task 1's
Wave-0 commit collects without import errors. They activate (GREEN) once the
module is created.
"""

import io
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Make hermes-skills importable for `import link_orphans` / `import telegram_alert`.
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_HERMES_DIR = _PROJECT_ROOT / "hermes-skills"
for _p in (str(_PROJECT_ROOT), str(_HERMES_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    import link_orphans  # noqa: E402

    _LINK_ORPHANS_AVAILABLE = True
except Exception as _exc:  # pragma: no cover - import guard
    link_orphans = None
    _LINK_ORPHANS_AVAILABLE = False
    _IMPORT_ERROR = str(_exc)

_needs_module = pytest.mark.skipif(
    not _LINK_ORPHANS_AVAILABLE,
    reason="link_orphans.py not yet created (Task 2)",
)


def _run_main_with_stdin(monkeypatch, payload: dict):
    """Inject `payload` as stdin JSON and run link_orphans.main()."""
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))


@_needs_module
def test_main_empty_orphans_posts_fallback_and_exits_0(monkeypatch):
    _run_main_with_stdin(monkeypatch, {"id": "t1", "orphans": []})
    with patch.object(link_orphans.telegram_alert, "send_alert") as mock_send:
        link_orphans.main()  # returns normally → exit 0
    assert mock_send.call_count == 1
    sent_message = mock_send.call_args.args[0]
    assert "no orphans" in sent_message.lower()


@_needs_module
def test_main_with_orphans_formats_message(monkeypatch):
    _run_main_with_stdin(
        monkeypatch,
        {"id": "t2", "orphans": ["notes/a.md", "notes/b.md"]},
    )
    with patch.object(link_orphans.telegram_alert, "send_alert") as mock_send:
        link_orphans.main()
    assert mock_send.call_count == 1
    sent_message = mock_send.call_args.args[0]
    assert sent_message.startswith(
        "⚠️ Orphan vault notes:\n- notes/a.md\n- notes/b.md"
    )


@_needs_module
def test_main_missing_orphans_key_posts_fallback(monkeypatch):
    _run_main_with_stdin(monkeypatch, {"id": "t3"})
    with patch.object(link_orphans.telegram_alert, "send_alert") as mock_send:
        link_orphans.main()
    assert mock_send.call_count == 1
    sent_message = mock_send.call_args.args[0]
    assert "no orphans" in sent_message.lower()


@_needs_module
def test_main_does_not_call_mark_queue_entry_dispatched(monkeypatch):
    # Inject a fake brain_http into sys.modules; if link_orphans wrongly imported
    # and called it, the mock would register the call.
    fake_brain = MagicMock()
    monkeypatch.setitem(sys.modules, "brain_http", fake_brain)
    _run_main_with_stdin(monkeypatch, {"id": "t4", "orphans": ["x.md"]})
    with patch.object(link_orphans.telegram_alert, "send_alert"):
        link_orphans.main()
    fake_brain.mark_queue_entry_dispatched.assert_not_called()
