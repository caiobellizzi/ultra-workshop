"""
cron_nightly_tests — Nightly test runner cron skill.

For each active repo with a test_command, clones it and runs the tests.
Failed tests are ingested into vault as suggested-action notes.
Only infrastructure failures (not per-repo test failures) trigger Telegram alerts.

Deploy location: /opt/ultra-workshop/hermes-skills/cron_nightly_tests.py
Schedule: 02:00 daily (via Hermes cron config — see Plan 05-04)

Catch-up: startup-cron-catchup-hook will call main() after a restart if the
nightly marker has not been written today.
"""
from __future__ import annotations

import datetime
import importlib.util
import shlex
import subprocess
import sys
from pathlib import Path

# Add /opt/ultra-workshop to sys.path so workshop.* modules are importable on VPS.
_WORKSHOP_ROOT = Path("/opt/ultra-workshop")
if str(_WORKSHOP_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSHOP_ROOT))

from workshop.cost import BudgetExhausted, BudgetWarning, check_circuit_breaker  # noqa: E402
from workshop.repo_registry import list_active_repos  # noqa: E402

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
NIGHTLY_MARKER = CRON_STATE_DIR / "nightly-tests.last"
CLONE_BASE = Path("/tmp/uws-test")


def _run_repo_tests(repo: dict, brain_http) -> None:
    """Clone a single repo and run its test_command. Ingests failures into vault."""
    full_name: str = repo["full_name"]
    test_command: str = repo["test_command"]

    clone_dir = CLONE_BASE / full_name.replace("/", "_")

    # Clone (shallow)
    clone_result = subprocess.run(
        ["git", "clone", "--depth=1", f"https://github.com/{full_name}", str(clone_dir)],
        capture_output=True,
        timeout=120,
    )
    if clone_result.returncode != 0:
        print(
            f"[nightly-tests] clone failed for {full_name}: "
            f"{clone_result.stderr.decode()[-500:]}",
            flush=True,
        )
        return

    # Run tests
    proc = subprocess.run(
        shlex.split(test_command),
        cwd=str(clone_dir),
        capture_output=True,
        timeout=300,
    )

    result_summary = (
        f"repo: {full_name}\n"
        f"exit_code: {proc.returncode}\n\n"
        f"stdout (last 2000 chars):\n{proc.stdout.decode()[-2000:]}\n\n"
        f"stderr (last 2000 chars):\n{proc.stderr.decode()[-2000:]}"
    )

    if proc.returncode != 0:
        # Ingest failure note into vault — do NOT send per-repo Telegram alert (REQ-ws-017 / D-10)
        ingest_payload = (
            f"---\n"
            f"title: Test failure: {full_name}\n"
            f"workshop.suggested_action: fix-test-failure\n"
            f"workshop.created_by: nightly-tests\n"
            f"---\n\n"
            f"{result_summary}"
        )
        brain_http.call_agent("ingest", ingest_payload)
        # incremental brain digest append (fire-and-forget)
        try:
            from workshop.brain_context import _append_digest_section
            _append_digest_section(full_name, "Incidents", f"Test failure: {result_summary}")
        except Exception:
            pass  # fail-open
        print(
            f"[nightly-tests] {full_name} FAILED (exit {proc.returncode}) — ingested to vault",
            flush=True,
        )
    else:
        print(f"[nightly-tests] {full_name} passed", flush=True)


def main() -> None:
    """Run the nightly test routine.

    1. Check circuit breaker — skip if budget exhausted/warned.
    2. Filter active repos to those with a non-empty test_command.
    3. For each repo: clone + run tests; ingest failures into vault.
    4. Write nightly marker file.
    5. On infrastructure failure: send Telegram alert and re-raise.
    """
    brain_http = _get_brain_http()
    send_alert = _get_telegram_alert().send_alert

    # Step 1: Circuit breaker
    try:
        check_circuit_breaker(mode="cron")
    except (BudgetExhausted, BudgetWarning) as e:
        send_alert(f"[nightly-tests] skipped: {e}")
        return

    try:
        # Step 2: Filter repos with a test_command
        repos = [
            r for r in list_active_repos()
            if r.get("test_command", "").strip()
        ]

        today = datetime.date.today().isoformat()

        if not repos:
            print("[nightly-tests] no repos with test_command — writing marker and returning", flush=True)
            CRON_STATE_DIR.mkdir(parents=True, exist_ok=True)
            NIGHTLY_MARKER.write_text(today, encoding="utf-8")
            return

        # Step 3: Run tests for each repo
        for repo in repos:
            try:
                _run_repo_tests(repo, brain_http)
            except Exception as exc:
                print(
                    f"[nightly-tests] unexpected error for {repo.get('full_name')}: {exc}",
                    flush=True,
                )

        # Step 4: Write nightly marker
        CRON_STATE_DIR.mkdir(parents=True, exist_ok=True)
        NIGHTLY_MARKER.write_text(today, encoding="utf-8")
        print(f"[nightly-tests] complete for {len(repos)} repo(s)", flush=True)

    except Exception as e:
        # Step 5: Infrastructure failure alert
        send_alert(f"[nightly-tests] infra failure: {e}")
        raise


if __name__ == "__main__":
    main()
