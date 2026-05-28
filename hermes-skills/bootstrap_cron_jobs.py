"""
bootstrap_cron_jobs — One-shot Hermes skill that registers all ultra-workshop
cron jobs via the Hermes `cronjob` builtin (available in Hermes 0.14.0+).

Run once during installation via:
  hermes skill run /opt/ultra-workshop/hermes-skills/bootstrap_cron_jobs.py

Idempotent: the Hermes `cronjob(action="create", ...)` call is a no-op if the
job ID already exists (Hermes 0.14.0 behavior).

Deploy location: /opt/ultra-workshop/hermes-skills/bootstrap_cron_jobs.py
"""
from __future__ import annotations

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [bootstrap_cron_jobs] %(message)s",
)
logger = logging.getLogger(__name__)

_CRON_JOBS = [
    {
        "id": "daily-research",
        "schedule": "0 7 * * *",
        "prompt": "Run daily-research routine",
        "skills": ["cron_daily_research"],
    },
    {
        "id": "nightly-tests",
        "schedule": "0 2 * * *",
        "prompt": "Run nightly-tests routine",
        "skills": ["cron_nightly_tests"],
    },
    {
        "id": "standard-poll-4h",
        "schedule": "0 */4 * * *",
        "prompt": "Run standard queue poll",
        "skills": ["cron_standard_poll"],
    },
    {
        "id": "nightly-rescan",
        "schedule": "0 3 * * *",
        "prompt": "Run nightly queue rescan",
        "skills": ["cron_standard_poll"],
    },
]


def register_cron_jobs() -> None:
    """Register all cron jobs. Designed to be called from Hermes skill context."""
    for job in _CRON_JOBS:
        logger.info("Registering cron job: %s (schedule=%s)", job["id"], job["schedule"])
        cronjob(  # noqa: F821 — injected by Hermes skill runtime
            action="create",
            id=job["id"],
            schedule=job["schedule"],
            prompt=job["prompt"],
            skills=job["skills"],
        )
        logger.info("Registered: %s", job["id"])


# Hermes skill entrypoint — register_cron_jobs() is called when Hermes runs this skill.
register_cron_jobs()
