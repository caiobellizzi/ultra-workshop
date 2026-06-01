"""
link_orphans — Orphan-vault notification skill.

Reads a queue entry JSON from stdin, extracts the orphan list from
entry['orphans'], formats a plain-text message, and posts to Telegram via
telegram_alert.send_alert(). Called by cron_standard_poll via
_run_skill('link_orphans', entry).

ACK is NOT performed here — marking the queue entry dispatched is the caller's
responsibility (cron_standard_poll._dispatch_entry handles it after dispatch).

The orphan list comes from the queue entry payload (field: `orphans` — a list
of vault note paths). If the field is absent or empty, a fallback message is
posted and the script still exits 0.

Deploy location: /opt/ultra-workshop/hermes-skills/link_orphans.py
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Allow running from the hermes-skills directory with siblings on sys.path.
_HERE = Path(__file__).parent
_REPO_ROOT = _HERE.parent
for _p in (str(_HERE), str(_REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import telegram_alert  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [link_orphans] %(message)s",
)
logger = logging.getLogger(__name__)

_FALLBACK_MESSAGE = "link_orphans: no orphans in payload — nothing to link."


def main() -> None:
    """Read a queue entry from stdin and post an orphan-notification to Telegram."""
    raw = sys.stdin.read()
    try:
        entry = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON on stdin: %s", exc)
        sys.exit(1)

    chat_id = entry.get("chat_id", telegram_alert.DEFAULT_CHAT_ID)
    orphans = entry.get("orphans")

    if not orphans:
        message = _FALLBACK_MESSAGE
    else:
        lines = ["⚠️ Orphan vault notes:"] + [f"- {p}" for p in orphans]
        message = "\n".join(lines)

    try:
        telegram_alert.send_alert(message, chat_id=chat_id)
    except Exception as exc:
        logger.error("send_alert failed: %s", exc)

    logger.info("link_orphans: posted %d orphans", len(orphans) if orphans else 0)


if __name__ == "__main__":
    main()
