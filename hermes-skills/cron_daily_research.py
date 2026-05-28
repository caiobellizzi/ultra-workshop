"""
cron_daily_research — Daily research cron skill.

Reads the next unprocessed item from vault/_system/research-queue.md,
delegates to Brain's research agent, and ingests the result into vault Inbox.

Deploy location: /opt/ultra-workshop/hermes-skills/cron_daily_research.py
Schedule: 07:00 daily (via Hermes cron config — see Plan 05-04)

Catch-up: startup-cron-catchup-hook will call main() after a restart if the
daily marker has not been written today.
"""
from __future__ import annotations

import datetime
import importlib.util
import os
import sys
import uuid
from pathlib import Path

# Add /opt/ultra-workshop to sys.path so workshop.* modules are importable when
# running on the VPS. When running locally (tests), PYTHONPATH already covers it.
_WORKSHOP_ROOT = Path("/opt/ultra-workshop")
if str(_WORKSHOP_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSHOP_ROOT))

from workshop.cost import BudgetExhausted, BudgetWarning, check_circuit_breaker  # noqa: E402

# Import brain_http and telegram_alert from the same skills directory, handling
# both local-dev (relative path) and deployed (/opt/ultra-workshop/hermes-skills/)
# scenarios.
_SKILLS_DIR = Path(__file__).parent


def _load_module(name: str, filename: str):
    """Load a module from the skills directory by filename."""
    path = _SKILLS_DIR / filename
    if not path.exists():
        path = Path("/opt/ultra-workshop/hermes-skills") / filename
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _get_brain_http():
    if "brain_http" in sys.modules:
        return sys.modules["brain_http"]
    return _load_module("brain_http", "brain_http.py")


def _get_telegram_alert():
    if "telegram_alert" in sys.modules:
        return sys.modules["telegram_alert"]
    return _load_module("telegram_alert", "telegram_alert.py")


CRON_STATE_DIR = Path("/home/uws/.ultra-workshop/cron-state")
DAILY_MARKER = CRON_STATE_DIR / "daily-research.last"
QUEUE_MARKER = "- [ ] "


def _find_next_queue_item(queue_text: str) -> tuple[int, str] | None:
    """Return (line_index, title) for the first uncompleted research queue entry.

    A line is considered completed if the checkbox is `[x]` or if the line
    immediately following it contains `workshop.status: done`.
    Returns None if no pending item is found.
    """
    lines = queue_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith(QUEUE_MARKER):
            # Check if the next line indicates already-done
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            if "workshop.status: done" not in next_line:
                title = line.lstrip()[len(QUEUE_MARKER):].strip()
                return i, title
        i += 1
    return None


def _mark_queue_done(queue_text: str, line_index: int) -> str:
    """Return updated queue text with the item at line_index marked [x] and annotated."""
    lines = queue_text.splitlines(keepends=True)
    original = lines[line_index]
    # Replace the leading `- [ ] ` with `- [x] `
    lines[line_index] = original.replace("- [ ] ", "- [x] ", 1)
    # Insert status annotation after this line (or replace existing annotation)
    lines.insert(line_index + 1, "<!-- workshop.status: done -->\n")
    return "".join(lines)


def main() -> None:
    """Run the daily research routine.

    1. Check circuit breaker — skip with Telegram alert if budget exhausted/warned.
    2. Pick the next unprocessed item from research-queue.md.
    3. Delegate to Brain's research agent.
    4. Ingest result into vault Inbox via Brain's ingest agent.
    5. Mark item done in research-queue.md.
    6. Write daily marker file.
    7. Send Telegram success alert.
    """
    brain_http = _get_brain_http()
    send_alert = _get_telegram_alert().send_alert

    # Step 1: Circuit breaker
    try:
        check_circuit_breaker(mode="cron")
    except (BudgetExhausted, BudgetWarning) as e:
        send_alert(f"[daily-research] skipped: {e}")
        return

    try:
        # Step 2: Read research queue
        vault_root = Path(os.environ.get("VAULT_VPS_PATH", "/srv/second-brain"))
        queue_path = vault_root / "_system" / "research-queue.md"
        queue_text = queue_path.read_text(encoding="utf-8")

        result = _find_next_queue_item(queue_text)
        if result is None:
            send_alert("[daily-research] no pending items in research-queue.md")
            return
        line_index, title = result

        # Step 3: Call Brain's research agent
        response = brain_http.call_agent("research", title)
        content = response.get("content", "")

        # Step 4: Derive filename and ingest into vault Inbox
        today = datetime.date.today().isoformat()
        uuid_short = str(uuid.uuid4())[:8]
        filename = f"{today}-research-{uuid_short}.md"
        inbox_path = f"vault/Inbox/{filename}"

        ingest_payload = (
            f"---\n"
            f"title: {title}\n"
            f"workshop.created_by: daily-research\n"
            f"---\n\n"
            f"{content}"
        )
        brain_http.call_agent("ingest", ingest_payload)

        # Step 5: Mark item done and write back atomically
        updated_queue = _mark_queue_done(queue_text, line_index)
        queue_path.write_text(updated_queue, encoding="utf-8")

        # Step 6: Write daily marker
        CRON_STATE_DIR.mkdir(parents=True, exist_ok=True)
        DAILY_MARKER.write_text(today, encoding="utf-8")

        # Step 7: Telegram success alert
        send_alert(f"Daily research: {title}. {inbox_path}")

    except Exception as e:
        send_alert(f"[daily-research] failed: {e}")
        raise


if __name__ == "__main__":
    main()
