"""
telegram_alert — Direct Telegram Bot API caller.

Sends a text message to a Telegram chat via the Bot API.

Deploy location: /opt/ultra-workshop/hermes-skills/telegram_alert.py

No module-level state. Token is read at call time so import always succeeds.
"""
from __future__ import annotations

import os

import httpx

TELEGRAM_API_BASE = "https://api.telegram.org"
DEFAULT_CHAT_ID = "7113965359"


def send_alert(message: str, chat_id: str = DEFAULT_CHAT_ID) -> None:
    """Send a Telegram alert message via the Bot API.

    Reads TELEGRAM_BOT_TOKEN from the environment at call time.
    Raises RuntimeError if the token is not set.
    Raises httpx.HTTPStatusError on non-2xx responses.

    Args:
        message:  Text to send.
        chat_id:  Telegram chat ID to deliver the message to.
                  Defaults to the workshop owner's chat (7113965359).
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")

    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    resp = httpx.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
    resp.raise_for_status()


def main() -> None:
    """Read a queue entry JSON from stdin and dispatch it via send_alert().

    Thin subprocess wrapper so cron_standard_poll can dispatch the
    `post-to-telegram` verb via `_run_skill('telegram_alert', entry)`.
    Reads entry['text'] and optional entry['chat_id'] (defaults to
    DEFAULT_CHAT_ID). The send_alert() library function is left unchanged.
    """
    import json
    import sys

    raw = sys.stdin.read()
    try:
        entry = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"telegram_alert main(): invalid JSON: {exc}")

    send_alert(
        entry.get("text", "(no text)"),
        chat_id=entry.get("chat_id", DEFAULT_CHAT_ID),
    )


if __name__ == "__main__":
    main()
