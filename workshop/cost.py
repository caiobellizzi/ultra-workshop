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


# ---------------------------------------------------------------------------
# Per-role monthly budget layer (Phase 09)
# ---------------------------------------------------------------------------

ROLE_MONTHLY_CAPS: dict[str, int] = {
    "security": 4000,
    "correctness": 3000,
    "python": 2000,
    "typescript": 2000,
    "reactjs": 2000,
    "qa": 1000,
    "docs": 1000,
    "config": 1000,
    "merge": 1500,
    "brainstorm": 2000,
    "pipeline_pool": 3000,
}


class RoleBudgetExhausted(Exception):
    """Raised when a reviewer role has reached its monthly spending cap."""


class RoleBudgetWarning(Exception):
    """Raised when a reviewer role has reached 80% of its monthly spending cap."""


def get_role_monthly_spend(role: str) -> float:
    """Return total spend in cents for *role* in the current calendar month.

    Parses LEDGER_PATH looking for lines that contain both the role tag and
    the current month prefix (YYYY-MM). Returns 0.0 if the file is absent.
    """
    if not LEDGER_PATH.exists():
        return 0.0
    month_prefix = date.today().strftime("%Y-%m")
    text = LEDGER_PATH.read_text(encoding="utf-8")
    total = sum(
        float(m.group(1))
        for line in text.splitlines()
        if month_prefix in line and role in line
        for m in [re.search(r"amount:\s*([\d.]+)", line)]
        if m
    )
    return total


def record_role_cost(role: str, amount: float, model: str) -> None:
    """Post a per-role cost entry to Brain's curator agent (non-blocking on failure)."""
    if role not in ROLE_MONTHLY_CAPS:
        print(
            f"[cost-ledger] WARNING: unknown role {role!r} — skipping record_role_cost",
            file=sys.stderr,
            flush=True,
        )
        return
    try:
        if _brain_http:
            _brain_http.call_agent(
                "curator",
                f"record-cost&amount={amount:.6f}&role={role}&source=workshop&model={model}",
            )
    except Exception as exc:
        print(
            f"[cost-ledger] WARNING: failed to record role cost (non-blocking): {exc}",
            file=sys.stderr,
            flush=True,
        )


def check_role_budget(role: str) -> None:
    """Check per-role monthly cap and raise RoleBudgetExhausted or RoleBudgetWarning.

    Sends a Telegram notification (via brain notify agent) before raising.
    Notification failures are swallowed (fail-open) so budget enforcement
    is not blocked by Brain connectivity issues.
    """
    if role not in ROLE_MONTHLY_CAPS:
        print(
            f"[cost-ledger] INFO: no monthly cap configured for role {role!r} — skipping",
            file=sys.stderr,
            flush=True,
        )
        return
    cap = ROLE_MONTHLY_CAPS[role]
    spend = get_role_monthly_spend(role)

    if spend >= cap:
        try:
            if _brain_http:
                _brain_http.call_agent(
                    "notify",
                    f"[workshop-budget] AUTO-PAUSE: role={role} exhausted monthly cap "
                    f"({spend}/{cap} cents). Human resume required.",
                )
        except Exception:
            pass
        raise RoleBudgetExhausted(
            f"Role {role!r} monthly cap exhausted: {spend}/{cap} cents"
        )

    if spend >= cap * 0.8:
        try:
            if _brain_http:
                _brain_http.call_agent(
                    "notify",
                    f"[workshop-budget] WARNING: role={role} at {spend / cap * 100:.0f}% "
                    f"of monthly cap ({spend}/{cap} cents)",
                )
        except Exception:
            pass
        raise RoleBudgetWarning(
            f"Role {role!r} monthly spend at {spend / cap * 100:.0f}% of cap ({spend}/{cap} cents)"
        )
