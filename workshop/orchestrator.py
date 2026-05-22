# Deploy location: /opt/ultra-workshop/workshop/orchestrator.py
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

HERMES_SKILL_RUN = Path("/opt/ultra-workshop/scripts/hermes-skill-run.sh")

T = TypeVar("T", bound=BaseModel)

_THINK_RE = re.compile(r"<think\b[^>]*>.*?</think>", re.DOTALL | re.IGNORECASE)


def _extract_json(text: str, *, skill_name: str | None = None) -> str:
    """Find and return the first complete JSON object in text.

    Strips ``<think>...</think>`` reasoning blocks (emitted by NIM DeepSeek
    thinking-mode models) before brace-matching, so JSON that follows the
    closing ``</think>`` tag is recovered cleanly.

    Raises ValueError if no JSON object found. The error message includes the
    skill name (when provided) and the head plus tail of the raw output, so
    Telegram surfaces an actionable diagnostic instead of a truncated narration
    fragment.
    """
    text = _THINK_RE.sub("", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        prefix = f"[{skill_name}] " if skill_name else ""
        head = text[:300].replace("\n", " ")
        tail = text[-300:].replace("\n", " ") if len(text) > 300 else ""
        raise ValueError(
            f"{prefix}No JSON object found. head={head!r}"
            + (f" tail={tail!r}" if tail else "")
        )
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

    raw_json = _extract_json(result.stdout, skill_name=skill_name)
    return output_schema.model_validate_json(raw_json)
