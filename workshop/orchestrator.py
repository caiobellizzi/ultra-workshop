# Deploy location: /opt/ultra-workshop/workshop/orchestrator.py
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

HERMES_SKILL_RUN = Path("/opt/ultra-workshop/scripts/hermes-skill-run.sh")

T = TypeVar("T", bound=BaseModel)


def _extract_json(text: str) -> str:
    """Find and return the first complete JSON object in text.

    Raises ValueError if no JSON object found.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"No JSON object found in: {text[:200]!r}")
    return text[start : end + 1]


def run_specialist(
    skill_name: str,
    query_json: str,
    output_schema: Type[T],
    dry_run: bool = False,
    timeout: int = 300,
) -> T:
    """Call a Hermes specialist skill via hermes-skill-run.sh and parse JSON stdout.

    Raises RuntimeError if subprocess exits non-zero.
    Raises subprocess.TimeoutExpired if specialist exceeds timeout.
    Raises ValidationError if stdout is not valid schema JSON.
    """
    if dry_run:
        raise NotImplementedError(
            "dry_run in run_specialist is for tests only — use --dry-run flag in workshop_build.py"
        )

    result = subprocess.run(
        ["bash", str(HERMES_SKILL_RUN), skill_name, "--query", query_json],
        capture_output=True,
        text=True,
        shell=False,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Specialist {skill_name!r} exited {result.returncode}: {result.stderr[:500]}"
        )

    raw_json = _extract_json(result.stdout)
    return output_schema.model_validate_json(raw_json)
