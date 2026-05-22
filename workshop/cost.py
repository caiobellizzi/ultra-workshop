# Deploy location: /opt/ultra-workshop/workshop/cost.py
from __future__ import annotations

import importlib.util
import re
import sys
from datetime import date
from pathlib import Path

# Load brain_http via importlib so the hyphenated filename is handled correctly.
# This mirrors the pattern used in hermes-skills/aider_runner.py.
_BRAIN_HTTP_FILE = Path("/opt/ultra-workshop/hermes-skills/brain_http.py")
try:
    _spec = importlib.util.spec_from_file_location("brain_http", _BRAIN_HTTP_FILE)
    _brain_http = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_brain_http)  # type: ignore[union-attr]
except Exception:
    _brain_http = None  # type: ignore[assignment]

LEDGER_PATH = Path("/srv/second-brain/_system/cost-ledger.md")
WARN_THRESHOLD = 18.0
HARD_THRESHOLD = 20.0


class BudgetExhausted(Exception):
    """Raised when daily spend reaches or exceeds the hard limit."""


class BudgetWarning(Exception):
    """Raised in cron mode when daily spend reaches the warning threshold."""


def get_daily_spend() -> float:
    """Parse today's spend total from cost-ledger.md. Returns 0.0 if file absent."""
    if not LEDGER_PATH.exists():
        return 0.0
    today = date.today().isoformat()
    text = LEDGER_PATH.read_text(encoding="utf-8")
    total = sum(
        float(m.group(1))
        for line in text.splitlines()
        if today in line
        for m in [re.search(r"amount:\s*([\d.]+)", line)]
        if m
    )
    return total


def record_cost(task_id: str, amount: float, model: str) -> None:
    """Post a cost entry to Brain's curator agent (non-blocking on failure)."""
    try:
        if _brain_http:
            _brain_http.call_agent(
                "curator",
                f"record-cost&amount={amount:.6f}&task={task_id}&source=workshop&model={model}",
            )
            print(f"[cost-ledger] recorded {amount:.6f} for {task_id}", flush=True)
    except Exception as exc:
        print(
            f"[cost-ledger] WARNING: failed to record cost (non-blocking): {exc}",
            file=sys.stderr,
            flush=True,
        )


def check_circuit_breaker(mode: str = "interactive") -> None:
    """Raise BudgetExhausted or BudgetWarning if daily spend limits are hit.

    Args:
        mode: "interactive" (default) checks only the hard limit;
              "cron" also checks the warn threshold.
    """
    spend = get_daily_spend()
    if spend >= HARD_THRESHOLD:
        raise BudgetExhausted(
            f"Daily spend ${spend:.2f} exceeds hard limit ${HARD_THRESHOLD:.2f} "
            "— refusing new LLM calls"
        )
    if mode == "cron" and spend >= WARN_THRESHOLD:
        raise BudgetWarning(
            f"Daily spend ${spend:.2f} at cron warning threshold — cancelling routine"
        )
