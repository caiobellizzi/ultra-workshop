"""
cron_standard_poll — Standard-cadence queue dispatcher for ultra-workshop.

Runs once per invocation (no infinite loop). Registered as a Hermes cron skill
with two schedules:
  - standard-poll-4h: 0 */4 * * *  (every 4 hours)
  - nightly-rescan:   0 3 * * *    (03:00 rescan)

On each invocation, reads the shared queue, filters eligible entries, applies
quiet-hours check, dispatches each confirmed-and-undispatched verb, and ACKs
via Brain HTTP.

Deploy location: /opt/ultra-workshop/hermes-skills/cron_standard_poll.py
"""
from __future__ import annotations

import base64
import datetime
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

# Allow running from the hermes-skills directory with workshop on sys.path.
_HERE = Path(__file__).parent
_REPO_ROOT = _HERE.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from workshop.cost import BudgetExhausted, BudgetWarning, check_circuit_breaker
import brain_http

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [cron_standard_poll] %(message)s",
)
logger = logging.getLogger(__name__)

QUEUE_PATH = Path(os.environ.get("WORKSHOP_QUEUE_PATH", "/srv/second-brain/.workshop-queue.jsonl"))
SKILL_DIR = _HERE


def _is_quiet_hours() -> bool:
    """Return True during quiet hours (22:00–06:59 local time)."""
    h = datetime.datetime.now().hour
    return h >= 22 or h < 7


def _load_queue() -> list[dict]:
    if not QUEUE_PATH.exists():
        return []
    entries = []
    for line in QUEUE_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as exc:
            logger.warning("Malformed queue line (skipped): %s — %s", line[:80], exc)
    return entries


def _dispatch_entry(entry: dict) -> None:
    """Dispatch a single queue entry based on its action verb."""
    entry_id = entry.get("id", "<unknown>")
    action = entry.get("action", "")
    logger.info("Dispatching entry %s (action=%s)", entry_id, action)

    if action == "post-to-telegram":
        _run_skill("telegram_alert", entry)
    elif action == "link-orphans":
        _run_skill("link_orphans", entry)
    elif action == "build":
        # workshop_build.py parses argparse — pass CLI flags, not stdin JSON.
        skill_file = SKILL_DIR / "workshop_build.py"
        if not skill_file.exists():
            logger.error("Skill file not found: %s — skipping", skill_file)
        else:
            task_b64 = base64.b64encode(entry.get("task", "").encode()).decode()
            try:
                subprocess.run(
                    [
                        sys.executable,
                        str(skill_file),
                        "--repo", entry.get("repo", ""),
                        "--task-b64", task_b64,
                        "--chat-id", entry.get("chat_id", "7113965359"),
                    ],
                    timeout=1800,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                logger.error("workshop_build timed out after 1800s")
            except Exception as exc:
                logger.error("workshop_build dispatch raised: %s", exc)
    elif action == "fix":
        # workshop_fix.py parses argparse and requires --issue-url, not stdin JSON.
        skill_file = SKILL_DIR / "workshop_fix.py"
        if not skill_file.exists():
            logger.error("Skill file not found: %s — skipping", skill_file)
        else:
            try:
                subprocess.run(
                    [
                        sys.executable,
                        str(skill_file),
                        "--issue-url", entry.get("issue_url", ""),
                        "--chat-id", entry.get("chat_id", "7113965359"),
                    ],
                    timeout=1800,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                logger.error("workshop_fix timed out after 1800s")
            except Exception as exc:
                logger.error("workshop_fix dispatch raised: %s", exc)
    else:
        logger.warning("Unknown action %r for entry %s — ACKing without dispatch", action, entry_id)

    brain_http.mark_queue_entry_dispatched(entry_id)


def _run_skill(skill_name: str, entry: dict) -> None:
    """Invoke a Hermes skill as a subprocess, forwarding entry as JSON via stdin."""
    skill_file = SKILL_DIR / f"{skill_name}.py"
    if not skill_file.exists():
        logger.error("Skill file not found: %s — skipping", skill_file)
        return
    try:
        result = subprocess.run(
            [sys.executable, str(skill_file)],
            input=json.dumps(entry),
            capture_output=True,
            text=True,
            timeout=1800,
        )
        if result.returncode != 0:
            logger.error("Skill %s exited %d: %s", skill_name, result.returncode, result.stderr[:500])
        else:
            logger.info("Skill %s completed ok", skill_name)
    except subprocess.TimeoutExpired:
        logger.error("Skill %s timed out after 1800s", skill_name)
    except Exception as exc:
        logger.error("Skill %s raised: %s", skill_name, exc)


def main() -> None:
    """Entry point: run one poll cycle and return."""
    # Circuit-breaker check — quiet fail for cron context.
    try:
        check_circuit_breaker(mode="cron")
    except BudgetExhausted as exc:
        logger.warning("Budget exhausted — skipping standard-poll: %s", exc)
        return
    except BudgetWarning as exc:
        logger.warning("Budget warning — skipping standard-poll: %s", exc)
        return

    if _is_quiet_hours():
        logger.info("Quiet hours active — skipping standard-poll")
        return

    entries = _load_queue()
    if not entries:
        logger.info("Queue is empty — nothing to dispatch")
        return

    eligible = [
        e for e in entries
        if e.get("confirmed") is True and not e.get("dispatched")
    ]
    logger.info("Queue: %d total, %d eligible", len(entries), len(eligible))

    for entry in eligible:
        try:
            _dispatch_entry(entry)
        except Exception as exc:
            logger.error("Failed to dispatch entry %s: %s", entry.get("id", "?"), exc)


if __name__ == "__main__":
    main()
