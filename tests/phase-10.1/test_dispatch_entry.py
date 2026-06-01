from __future__ import annotations

"""
Unit tests for hermes-skills/cron_standard_poll._dispatch_entry (Phase 10.1).

Covers the dispatch-interface fix (REQ-ws-020 / REQ-ws-021):
  - build verb dispatches via subprocess.run CLI flags (--repo/--task-b64/--chat-id)
  - fix verb dispatches via subprocess.run CLI flags (--issue-url/--chat-id)
  - build verb does NOT use the stdin-JSON _run_skill() path
  - link-orphans verb STILL uses _run_skill() (unchanged stdin-JSON path)

CLI-flag assertions are guarded on a feature probe (`base64` imported into
cron_standard_poll) so they skip cleanly before the Task-3 fix and go GREEN after.
The link-orphans path test runs in all states (behavior is unchanged by the fix).
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_HERMES_DIR = _PROJECT_ROOT / "hermes-skills"
for _p in (str(_PROJECT_ROOT), str(_HERMES_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import cron_standard_poll  # noqa: E402

# `import base64` is added to cron_standard_poll only by the Task-3 fix.
_DISPATCH_FIXED = hasattr(cron_standard_poll, "base64")
_needs_fix = pytest.mark.skipif(
    not _DISPATCH_FIXED,
    reason="cron_standard_poll._dispatch_entry CLI-flag fix not yet applied (Task 3)",
)

_BUILD_ENTRY = {
    "id": "e1",
    "action": "build",
    "repo": "my-app",
    "task": "add tests",
    "chat_id": "12345",
}
_FIX_ENTRY = {
    "id": "e2",
    "action": "fix",
    "issue_url": "https://github.com/x/y/issues/1",
    "chat_id": "12345",
}
_LINK_ENTRY = {"id": "e3", "action": "link-orphans", "orphans": ["a.md"]}


@_needs_fix
def test_build_verb_uses_subprocess_with_cli_flags():
    with patch.object(cron_standard_poll, "subprocess") as mock_sp, patch.object(
        cron_standard_poll.brain_http, "mark_queue_entry_dispatched"
    ):
        cron_standard_poll._dispatch_entry(dict(_BUILD_ENTRY))
    assert mock_sp.run.call_count == 1
    argv = mock_sp.run.call_args.args[0]
    assert "--repo" in argv
    assert "--task-b64" in argv
    assert "--chat-id" in argv
    # list form, never shell=True
    assert mock_sp.run.call_args.kwargs.get("shell") in (None, False)


@_needs_fix
def test_fix_verb_uses_subprocess_with_issue_url():
    with patch.object(cron_standard_poll, "subprocess") as mock_sp, patch.object(
        cron_standard_poll.brain_http, "mark_queue_entry_dispatched"
    ):
        cron_standard_poll._dispatch_entry(dict(_FIX_ENTRY))
    assert mock_sp.run.call_count == 1
    argv = mock_sp.run.call_args.args[0]
    assert "--issue-url" in argv
    assert "--chat-id" in argv
    assert mock_sp.run.call_args.kwargs.get("shell") in (None, False)


@_needs_fix
def test_build_verb_does_not_use_run_skill():
    with patch.object(cron_standard_poll, "_run_skill") as mock_run_skill, patch.object(
        cron_standard_poll, "subprocess"
    ), patch.object(cron_standard_poll.brain_http, "mark_queue_entry_dispatched"):
        cron_standard_poll._dispatch_entry(dict(_BUILD_ENTRY))
    for call in mock_run_skill.call_args_list:
        assert call.args[0] != "workshop_build"


def test_link_orphans_still_uses_run_skill():
    with patch.object(cron_standard_poll, "_run_skill") as mock_run_skill, patch.object(
        cron_standard_poll.brain_http, "mark_queue_entry_dispatched"
    ):
        cron_standard_poll._dispatch_entry(dict(_LINK_ENTRY))
    mock_run_skill.assert_called_once()
    assert mock_run_skill.call_args.args[0] == "link_orphans"
