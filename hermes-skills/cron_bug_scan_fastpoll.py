"""
cron_bug_scan_fastpoll.py — Bug-scan fast-poll dispatch loop (30s).

Polls the workshop queue every 30 seconds and dispatches entries that are:
  - confirmed: true
  - dispatched: false
  - have an action verb

Respects a quiet-hours window (22:00–07:00) for HITL-required verbs.
Zero-HITL verbs (post-to-telegram) are dispatched unconditionally.

Deploy location: /opt/ultra-workshop/hermes-skills/cron_bug_scan_fastpoll.py
Run as: uws user under systemd (uws-bug-scan-fastpoll.service)
"""
from __future__ import annotations

import atexit
import datetime
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ---------------------------------------------------------------------------
# Single-instance lock via PID file
# ---------------------------------------------------------------------------
PID_FILE = "/tmp/uws-fastpoll.pid"
_pid_path = Path(PID_FILE)

if _pid_path.exists():
    _existing_pid = _pid_path.read_text().strip()
    try:
        os.kill(int(_existing_pid), 0)  # signal 0 = existence check
        print(f"Already running (pid {_existing_pid}), exiting.", file=sys.stderr)
        sys.exit(1)
    except (ProcessLookupError, ValueError):
        pass  # stale PID file — continue

_pid_path.write_text(str(os.getpid()))

# ---------------------------------------------------------------------------
# Path setup — allow imports from hermes-skills directory
# ---------------------------------------------------------------------------
_HERMES_DIR = Path(__file__).parent
if str(_HERMES_DIR) not in sys.path:
    sys.path.insert(0, str(_HERMES_DIR))

import brain_http  # noqa: E402 — provided by Plan 05-01
import telegram_alert  # noqa: E402 — provided by Plan 05-02
from workshop.cost import BudgetExhausted, BudgetWarning, check_circuit_breaker  # noqa: E402

# ---------------------------------------------------------------------------
# PID file cleanup
# ---------------------------------------------------------------------------


def _remove_pid_file() -> None:
    try:
        _pid_path.unlink(missing_ok=True)
    except Exception:
        pass


atexit.register(_remove_pid_file)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _in_quiet_hours() -> bool:
    """Return True if the current local hour is in the 22:00–07:00 window."""
    h = datetime.datetime.now().hour
    return h >= 22 or h < 7


def _queue_path() -> Path:
    vault = os.environ.get("VAULT_VPS_PATH", "/srv/second-brain")
    return Path(vault) / "_system" / ".workshop-queue.jsonl"


def _read_eligible_entries(queue_file: Path) -> list[dict]:
    """Parse the JSONL queue and return entries pending dispatch."""
    if not queue_file.exists():
        return []

    eligible: list[dict] = []
    for line in queue_file.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            logging.warning("Malformed queue line, skipping: %.80s", line)
            continue
        if (
            entry.get("action")
            and entry.get("confirmed") is True
            and not entry.get("dispatched", False)
        ):
            eligible.append(entry)
    return eligible


# ---------------------------------------------------------------------------
# Core poll function
# ---------------------------------------------------------------------------

_ZERO_HITL_VERBS = {"post-to-telegram"}


def _poll_once() -> None:
    """Single poll iteration — read queue, dispatch eligible entries."""
    # Circuit-breaker check
    try:
        check_circuit_breaker(mode="cron")
    except (BudgetExhausted, BudgetWarning) as exc:
        logging.warning("poll_once skipped: %s", exc)
        return

    queue_file = _queue_path()
    eligible = _read_eligible_entries(queue_file)
    if not eligible:
        return

    # Partition by HITL requirement
    zero_hitl = [e for e in eligible if e.get("action") in _ZERO_HITL_VERBS]
    hitl_required = [e for e in eligible if e.get("action") not in _ZERO_HITL_VERBS]

    # Dispatch zero-HITL entries unconditionally
    for entry in zero_hitl:
        verb = entry.get("action", "")
        entry_id = entry["id"]
        if verb == "post-to-telegram":
            try:
                telegram_alert.send_alert(entry.get("text", "(no text)"))
            except Exception as exc:
                logging.error("telegram_alert.send_alert failed for %s: %s", entry_id, exc)
            brain_http.mark_queue_entry_dispatched(entry_id)

    # Apply quiet-hours deferral to HITL-required entries
    if _in_quiet_hours() and hitl_required:
        logging.info("quiet hours — deferring %d entries", len(hitl_required))
        return

    for entry in hitl_required:
        verb = entry.get("action", "")
        entry_id = entry["id"]

        if verb == "link-orphans":
            # Pre-approved zero-work verb — log and ACK only
            logging.info("link-orphans: marking dispatched (no-op dispatch), entry %s", entry_id)
            brain_http.mark_queue_entry_dispatched(entry_id)

        elif verb == "build":
            logging.info("Dispatching build for entry %s", entry_id)
            subprocess.run(
                [
                    sys.executable,
                    "/opt/ultra-workshop/hermes-skills/workshop_build.py",
                    entry.get("repo", ""),
                    entry.get("task", ""),
                ],
                check=False,
            )
            brain_http.mark_queue_entry_dispatched(entry_id)

        elif verb == "fix":
            logging.info("Dispatching fix for entry %s", entry_id)
            subprocess.run(
                [
                    sys.executable,
                    "/opt/ultra-workshop/hermes-skills/workshop_fix.py",
                    entry.get("issue_url", ""),
                ],
                check=False,
            )
            brain_http.mark_queue_entry_dispatched(entry_id)

        else:
            logging.warning(
                "Unknown verb '%s' for entry %s — marking dispatched to avoid re-processing",
                verb,
                entry_id,
            )
            brain_http.mark_queue_entry_dispatched(entry_id)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.info("uws-fastpoll starting (pid %d, poll interval 30s)", os.getpid())

    try:
        while True:
            try:
                _poll_once()
            except Exception as exc:
                logging.error("poll_once error: %s", exc)
            time.sleep(30)
    finally:
        _remove_pid_file()
