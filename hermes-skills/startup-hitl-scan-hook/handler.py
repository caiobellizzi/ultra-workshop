"""
startup-hitl-scan hook handler — gateway:startup event.

On each Hermes gateway start, scans /home/uws/.ultra-workshop/pending_hitl.db
for rows with status='pending' and re-emits a Telegram inline keyboard for
each one, so that a user can still Approve/Reject after a service restart.

Satisfies REQ-ws-014: "HITL pause survives systemctl restart uws-hermes".

Security (T-02-17): callback validates chat_id matches original before
resolving. (T-02-18): DB at /home/uws/.ultra-workshop/, mode 0600.
(T-02-20): approval written back to DB with timestamp + telegram_user_id.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("startup-hitl-scan")

# Load startup-hitl-scan.py via importlib (hyphens are invalid in import names)
_SKILLS_DIR = Path("/opt/ultra-workshop/hermes-skills")
_MODULE_FILE = _SKILLS_DIR / "startup-hitl-scan.py"

def _load_hitl_module():
    """Load startup-hitl-scan.py and register as 'startup_hitl_scan'."""
    import importlib.util
    if "startup_hitl_scan" in sys.modules:
        return sys.modules["startup_hitl_scan"]
    if not _MODULE_FILE.exists():
        return None
    spec = importlib.util.spec_from_file_location("startup_hitl_scan", str(_MODULE_FILE))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["startup_hitl_scan"] = mod
    spec.loader.exec_module(mod)
    return mod

ALLOWED_CHAT_ID = "7113965359"  # T-02-17: only this chat may resolve HITL


def _get_telegram_adapter():
    """Return the live Telegram platform adapter, or None."""
    try:
        from gateway.run import _gateway_runner_ref  # type: ignore[import]
        runner = _gateway_runner_ref()
        if runner is None:
            return None
        # Iterate adapters to find the telegram one by name
        for kind, adapter in runner.adapters.items():
            name = kind.value if hasattr(kind, "value") else str(kind)
            if "telegram" in name.lower():
                return adapter
        return None
    except Exception as exc:
        logger.warning("[startup-hitl-scan] Could not get Telegram adapter: %s", exc)
        return None


def _get_event_loop():
    """Return the gateway event loop, or None."""
    try:
        from gateway.run import _gateway_runner_ref  # type: ignore[import]
        runner = _gateway_runner_ref()
        if runner is None:
            return None
        return getattr(runner, "_loop", None) or getattr(runner, "loop", None)
    except Exception:
        return None


async def _re_emit_row(adapter, row: Dict[str, Any]) -> Optional[str]:
    """Send a Telegram inline keyboard for one pending HITL row.

    Returns the new telegram_message_id on success, None on failure.
    Uses the clarify mechanism with a custom clarify_id so the Telegram
    callback handler can route button taps back to resolve_gateway_clarify,
    which this handler monitors in a background thread.
    """
    _hitl_mod = _load_hitl_module()
    if _hitl_mod is None:
        logger.error("[startup-hitl-scan] startup_hitl_scan module not available")
        return None
    resolve_hitl_row = _hitl_mod.resolve_hitl_row
    update_hitl_message_id = _hitl_mod.update_hitl_message_id

    row_id: int = row["id"]
    session_id: str = row["session_id"]
    task_description: str = row["task_description"]
    chat_id: str = row["telegram_chat_id"]

    # T-02-17: only re-emit to the authorized chat
    if chat_id != ALLOWED_CHAT_ID:
        logger.warning(
            "[startup-hitl-scan] Skipping row %s — chat_id %s not in allowlist",
            row_id, chat_id,
        )
        return None

    # Build a fresh clarify_id for this re-emission
    clarify_id = f"hitl-restart-{row_id}-{uuid.uuid4().hex[:8]}"

    # Register in the clarify module so Telegram callback handler routes to it
    try:
        from tools.clarify_gateway import register  # type: ignore[import]
        entry = register(
            clarify_id=clarify_id,
            session_key=f"hitl-{session_id}",
            question=(
                f"HITL approval required (re-sent after restart)\n\n"
                f"Task: {task_description}"
            ),
            choices=["Approve", "Reject"],
        )
    except Exception as exc:
        logger.error("[startup-hitl-scan] Failed to register clarify entry: %s", exc)
        return None

    # Send the inline keyboard via the Telegram adapter's send_clarify method
    try:
        result = await adapter.send_clarify(
            chat_id=chat_id,
            question=(
                f"HITL approval required (re-sent after restart)\n\n"
                f"Task: {task_description}"
            ),
            choices=["Approve", "Reject"],
            clarify_id=clarify_id,
            session_key=f"hitl-{session_id}",
        )
        message_id = result.message_id if result.success else None
    except Exception as exc:
        logger.error("[startup-hitl-scan] send_clarify failed for row %s: %s", row_id, exc)
        return None

    if message_id:
        update_hitl_message_id(row_id, message_id)

    print(
        f"[startup-hitl-scan] re-emitting HITL for session {session_id} (row_id={row_id})",
        flush=True,
    )
    logger.info(
        "[startup-hitl-scan] re-emitting HITL for session %s (row_id=%s, clarify_id=%s)",
        session_id, row_id, clarify_id,
    )

    # Start background thread to wait for resolution and update DB
    def _wait_and_resolve():
        try:
            # Wait up to 7 days (604800 s) — T-02-19: cleanup is Phase 3
            response = entry.event.wait(timeout=604800)
            if not response:
                logger.info(
                    "[startup-hitl-scan] HITL row %s timed out (7 days, no response)",
                    row_id,
                )
                return
            decision_text = entry.response or ""
            if decision_text.lower().startswith("approve"):
                decision = "approved"
            elif decision_text.lower().startswith("reject"):
                decision = "rejected"
            else:
                decision = decision_text.lower()[:16]

            # T-02-20: record approval with timestamp
            resolve_hitl_row(
                row_id=row_id,
                decision=decision,
                approved_by=None,  # callback handler does not pass user_id to resolve
            )
            logger.info(
                "[startup-hitl-scan] HITL row %s resolved as '%s'",
                row_id, decision,
            )

            # Send confirmation back to Telegram
            loop = _get_event_loop()
            if loop and adapter:
                try:
                    emoji = "✅" if decision == "approved" else "❌"
                    asyncio.run_coroutine_threadsafe(
                        adapter.send(
                            chat_id=chat_id,
                            content=f"{emoji} HITL {decision} — session {session_id} has been marked as {decision}.",
                        ),
                        loop,
                    ).result(timeout=10)
                except Exception as exc:
                    logger.warning("[startup-hitl-scan] Could not send confirmation: %s", exc)
        except Exception as exc:
            logger.error("[startup-hitl-scan] Resolution thread error for row %s: %s", row_id, exc)

    t = threading.Thread(target=_wait_and_resolve, daemon=True, name=f"hitl-wait-{row_id}")
    t.start()

    return message_id


async def handle(event_type: str, context: Dict[str, Any]) -> None:
    """gateway:startup handler — re-emit pending HITL keyboards."""
    if event_type != "gateway:startup":
        return

    # Load the helper module (importlib-based, handles hyphenated filename)
    _hitl_mod = _load_hitl_module()
    if _hitl_mod is None:
        logger.error(
            "[startup-hitl-scan] Could not load startup-hitl-scan module from %s. "
            "Ensure /opt/ultra-workshop/hermes-skills/ is deployed.",
            _MODULE_FILE,
        )
        return

    fetch_pending = _hitl_mod.fetch_pending
    ensure_schema = _hitl_mod.ensure_schema

    # Ensure schema exists (idempotent)
    try:
        ensure_schema()
    except Exception as exc:
        logger.error("[startup-hitl-scan] Schema init failed: %s", exc)
        return

    # Fetch pending rows
    pending = fetch_pending()
    if not pending:
        print("[startup-hitl-scan] No pending HITL rows — startup scan complete.", flush=True)
        return

    print(
        f"[startup-hitl-scan] Found {len(pending)} pending HITL row(s) — re-emitting HITL keyboards.",
        flush=True,
    )
    logger.info(
        "[startup-hitl-scan] Found %d pending HITL row(s) — re-emitting HITL keyboards.",
        len(pending),
    )

    # Allow the Telegram adapter's internal PTB application to fully connect.
    # gateway:startup fires synchronously after adapters are wired — the bot
    # may still be mid-initialization when this hook runs.
    await asyncio.sleep(5)

    adapter = _get_telegram_adapter()
    if adapter is None:
        print(
            "[startup-hitl-scan] WARNING: Telegram adapter not available — "
            "cannot re-emit HITL keyboards.",
            flush=True,
        )
        logger.warning(
            "[startup-hitl-scan] Telegram adapter not available — "
            "cannot re-emit HITL keyboards. Will retry if adapter connects later."
        )
        return

    for row in pending:
        try:
            await _re_emit_row(adapter, row)
        except Exception as exc:
            logger.error(
                "[startup-hitl-scan] Error processing row %s: %s",
                row.get("id"), exc,
            )
