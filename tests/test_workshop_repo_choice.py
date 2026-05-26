"""CLI tests for workshop_repo.py --choice approval-token handling.

The Telegram agent sometimes carries over the build pipeline's
`workshop_continue.py --choice <number>` continuation pattern and aims it at
workshop_repo.py, which historically only knew `--approved` and errored with
"unrecognized arguments: --choice". These tests lock in the tolerant behavior.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "hermes-skills" / "workshop_repo.py"


def _run(*args: str, registry: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--registry", str(registry)],
        capture_output=True,
        text=True,
    )


def test_choice_rejection_token_exits_clean_without_mutation(tmp_path):
    reg = tmp_path / "r.json"
    res = _run("add", "caiobellizzi/x", "--choice", "2", registry=reg)
    assert res.returncode == 0
    assert "rejected" in res.stdout.lower()


def test_choice_approval_token_bypasses_gate(tmp_path):
    # remove of an unknown repo: --choice approved must reach the mutation path
    # (UnknownRepo error) rather than the approval gate — proving it counted as
    # approval. Also proves --choice no longer triggers an argparse error.
    reg = tmp_path / "r.json"
    res = _run("remove", "caiobellizzi/notthere", "--choice", "approved", registry=reg)
    assert "unrecognized arguments" not in (res.stdout + res.stderr).lower()
    assert res.returncode == 1
    assert "unknown or inactive" in res.stderr.lower()


def test_choice_numeric_yes_is_approval(tmp_path):
    reg = tmp_path / "r.json"
    res = _run("remove", "caiobellizzi/notthere", "--choice", "1", registry=reg)
    assert res.returncode == 1
    assert "unknown or inactive" in res.stderr.lower()


def test_unrecognized_choice_falls_through_to_approval_gate(tmp_path):
    reg = tmp_path / "r.json"
    res = _run("remove", "caiobellizzi/notthere", "--choice", "bogus", registry=reg)
    assert res.returncode == 2
    assert '"needs_approval": true' in res.stdout


def test_choice_flag_no_longer_unrecognized_for_add(tmp_path):
    # Regression: the original bug was argparse rejecting --choice outright.
    reg = tmp_path / "r.json"
    res = _run("add", "caiobellizzi/x", "--choice", "no", registry=reg)
    assert "unrecognized arguments" not in (res.stdout + res.stderr).lower()
    assert res.returncode == 0  # 'no' -> rejection -> clean exit
