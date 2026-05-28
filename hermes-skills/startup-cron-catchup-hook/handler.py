"""
startup-cron-catchup hook handler — gateway:startup event.

On each Hermes gateway start, checks whether daily-research and nightly-tests
ran today. If a routine was missed (marker absent or dated before today) and
the current local hour is past the routine's scheduled time, re-runs it
synchronously in a try/except so other hooks are not blocked.

Satisfies REQ-ws-022: "catch-up startup hook re-runs missed schedules after
service restart".

Deploy location (symlink or copy): /home/uws/.hermes/hooks/startup-cron-catchup/
                                   (auto-discovered by Hermes on startup)
Source:                            /opt/ultra-workshop/hermes-skills/startup-cron-catchup-hook/
"""
from __future__ import annotations

import datetime
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("startup-cron-catchup")

_SKILLS_DIR = Path("/opt/ultra-workshop/hermes-skills")
CRON_STATE_DIR = Path("/home/uws/.ultra-workshop/cron-state")

# Minimum local hour at which each routine should have run
DAILY_RESEARCH_HOUR = 7
NIGHTLY_TESTS_HOUR = 2


def _load_skill(module_name: str, filename: str):
    """Load a skill module from the skills directory via importlib."""
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = _SKILLS_DIR / filename
    if not path.exists():
        logger.error(
            "[startup-cron-catchup] Skill file not found: %s — skipping %s",
            path, module_name,
        )
        return None
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _should_catchup(marker_path: Path, threshold_hour: int) -> bool:
    """Return True if the routine should be re-run during startup.

    A catch-up is needed when:
    - The marker file does not exist, OR
    - The marker file's content is not today's ISO date
    AND the current local hour is at or past the scheduled threshold.
    """
    today = datetime.date.today().isoformat()
    now_hour = datetime.datetime.now().hour

    if now_hour < threshold_hour:
        return False

    if not marker_path.exists():
        return True

    try:
        last_run = marker_path.read_text(encoding="utf-8").strip()
        return last_run != today
    except Exception:
        return True


async def handle(event_type: str, context: Dict[str, Any]) -> None:
    """gateway:startup handler — catch up missed cron routines."""
    if event_type != "gateway:startup":
        return

    today = datetime.date.today().isoformat()
    print(
        f"[startup-cron-catchup] startup check on {today}",
        flush=True,
    )

    # --- daily-research ---
    daily_marker = CRON_STATE_DIR / "daily-research.last"
    if _should_catchup(daily_marker, DAILY_RESEARCH_HOUR):
        logger.info("[startup-cron-catchup] daily-research was missed — running catch-up")
        print("[startup-cron-catchup] running missed daily-research", flush=True)
        mod = _load_skill("cron_daily_research", "cron_daily_research.py")
        if mod is not None:
            try:
                mod.main()
                logger.info("[startup-cron-catchup] daily-research catch-up complete")
            except Exception as exc:
                # Log but do NOT re-raise — other hooks must not be blocked
                logger.error(
                    "[startup-cron-catchup] daily-research catch-up failed: %s", exc
                )
    else:
        logger.info("[startup-cron-catchup] daily-research already ran today — skipping")

    # --- nightly-tests ---
    nightly_marker = CRON_STATE_DIR / "nightly-tests.last"
    if _should_catchup(nightly_marker, NIGHTLY_TESTS_HOUR):
        logger.info("[startup-cron-catchup] nightly-tests was missed — running catch-up")
        print("[startup-cron-catchup] running missed nightly-tests", flush=True)
        mod = _load_skill("cron_nightly_tests", "cron_nightly_tests.py")
        if mod is not None:
            try:
                mod.main()
                logger.info("[startup-cron-catchup] nightly-tests catch-up complete")
            except Exception as exc:
                logger.error(
                    "[startup-cron-catchup] nightly-tests catch-up failed: %s", exc
                )
    else:
        logger.info("[startup-cron-catchup] nightly-tests already ran today — skipping")

    print("[startup-cron-catchup] startup check complete", flush=True)
