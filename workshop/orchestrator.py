# Deploy location: /opt/ultra-workshop/workshop/orchestrator.py
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from workshop.types import ClarificationRequest

HERMES_SKILL_RUN = Path("/opt/ultra-workshop/scripts/hermes-skill-run.sh")

T = TypeVar("T", bound=BaseModel)

_THINK_RE = re.compile(r"<think\b[^>]*>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL | re.IGNORECASE)


class ClarificationNeeded(RuntimeError):
    def __init__(self, request: ClarificationRequest):
        self.request = request
        super().__init__(
            f"Specialist requested clarification at {request.source_stage}: {request.reason}"
        )


class SpecialistFailed(RuntimeError):
    def __init__(self, skill_name: str, returncode: int, stderr: str):
        self.skill_name = skill_name
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(
            f"Specialist {skill_name!r} exited {returncode}: {stderr[:500]}"
        )


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
    fenced = _FENCE_RE.search(text)
    if fenced and "{" in fenced.group(1):
        text = fenced.group(1)
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
    timeout: int = int(os.environ.get("UWS_CODER_MAX", "7200")),
) -> T:
    """Call a Hermes specialist skill via hermes-skill-run.sh and parse JSON stdout.

    Default timeout is UWS_CODER_MAX (default 7200s) as a backstop for the multi-step
    coder stage. Per-step idle timeout and total task budget govern per step — this is
    the outer wall-clock limit only. Override per-call as needed.

    Raises SpecialistFailed if subprocess exits non-zero.
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
        raise SpecialistFailed(skill_name, result.returncode, result.stderr)

    raw_json = _extract_json(result.stdout, skill_name=skill_name)
    payload = json.loads(raw_json)
    if isinstance(payload, dict) and payload.get("needs_clarification") is True:
        raise ClarificationNeeded(ClarificationRequest.model_validate(payload))
    return output_schema.model_validate(payload)
