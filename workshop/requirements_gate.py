from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

from pydantic import BaseModel, Field

from workshop.types import ClarificationQuestion, ClarificationRequest

# Load brain_http via importlib (mirrors pattern from workshop/reviewer.py and workshop/cost.py)
_BRAIN_HTTP_FILE = Path("/opt/ultra-workshop/hermes-skills/brain_http.py")
_brain_http = None
try:
    _spec = importlib.util.spec_from_file_location("brain_http", _BRAIN_HTTP_FILE)
    if _spec and _spec.loader:
        _brain_http = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_brain_http)  # type: ignore[union-attr]
except Exception:
    _brain_http = None  # type: ignore[assignment]


def _query_prior_clarifications(repo_full_name: str) -> str:
    """Query brain for prior clarifications on this repo. Fail-open: returns '' on any failure.

    B7: Injects prior context into requirements evaluation to avoid re-asking known questions.
    T-09-03-04: Result goes into planning_notes only, never overrides current task requirements.
    """
    if _brain_http is None or not repo_full_name:
        return ""
    try:
        result = _brain_http.call_agent(
            "query",
            f"prior clarifications for {repo_full_name}",
        )
        content = str(result.get("content") or result)
        if content and content != str(result):
            print(
                f"[requirements_gate] brain prior-clarification context loaded for {repo_full_name}",
                file=sys.stderr,
                flush=True,
            )
        return content
    except Exception as exc:
        print(
            f"[requirements_gate] brain query failed (non-blocking): {exc}",
            file=sys.stderr,
            flush=True,
        )
        return ""


_TWELVE_FACTORY_RE = re.compile(
    r"\b(?:12|twelve)[-\s]+factory\s+practices?\b",
    re.IGNORECASE,
)


class RequirementsDecision(BaseModel):
    ready: bool = True
    goal: str
    planning_notes: list[str] = Field(default_factory=list)
    clarifications: list[str] = Field(default_factory=list)


def normalize_clarifications(raw: object) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        text = raw.strip()
        return [text] if text else []
    if isinstance(raw, dict):
        if "answers" in raw:
            return normalize_clarifications(raw.get("answers"))
        if "user_responses" in raw:
            return normalize_clarifications(raw.get("user_responses"))
        question = str(raw.get("question") or raw.get("prompt") or "").strip()
        answer = str(raw.get("answer") or raw.get("response") or raw.get("value") or "").strip()
        if question and answer:
            return [f"{question}: {answer}"]
        text = json.dumps(raw, sort_keys=True)
        return [text] if text else []
    if isinstance(raw, list):
        result: list[str] = []
        for item in raw:
            result.extend(normalize_clarifications(item))
        return result
    return [str(raw)]


def build_planning_context(base_context: str, clarifications: list[str]) -> str:
    if not clarifications:
        return base_context
    clarification_block = "\n".join(f"- {item}" for item in clarifications)
    if base_context:
        return f"{base_context}\nHuman clarifications:\n{clarification_block}"
    return f"Human clarifications:\n{clarification_block}"


def maybe_clarification_request(
    task_id: str,
    goal: str,
    *,
    source_stage: str,
    clarifications: list[str] | None = None,
) -> ClarificationRequest | None:
    clarifications = clarifications or []
    if clarifications:
        return None

    match = _TWELVE_FACTORY_RE.search(goal)
    if not match:
        return None

    options = [
        "12-factor app methodology",
        "Factory or manufacturing workflow practices",
        "Something else; answer in free text",
    ]
    phrase = match.group(0)
    return ClarificationRequest(
        task_id=task_id,
        source_stage=source_stage,
        reason=f"The phrase {phrase!r} is ambiguous and should not be interpreted automatically.",
        questions=[
            ClarificationQuestion(
                question="What did you mean by '12 factory practices' in this task?",
                options=options,
                context=goal,
            )
        ],
        options=options,
        allow_free_text=True,
        evidence=[f"Ambiguous phrase detected in goal: {phrase!r}"],
        summary="Clarification needed before implementation can continue.",
    )


def evaluate_requirements(query_json: str) -> RequirementsDecision | ClarificationRequest:
    query = json.loads(query_json)
    task_id = str(query.get("task_id") or "").strip()
    goal = str(query.get("goal") or "").strip()
    if not task_id or not goal:
        raise ValueError("requirements query missing task_id or goal")

    # B7: Query brain for prior clarifications before ambiguity detection.
    # T-09-03-04: Result injected into planning_notes only — never overrides current task spec.
    repo = query.get("repo") or {}
    repo_full_name = str(repo.get("full_name") or query.get("repo_full_name") or "").strip()
    prior_context = _query_prior_clarifications(repo_full_name)

    clarifications = normalize_clarifications(query.get("clarifications"))
    clarification = maybe_clarification_request(
        task_id,
        goal,
        source_stage="requirements",
        clarifications=clarifications,
    )
    if clarification is not None:
        return clarification

    notes: list[str] = []
    if clarifications:
        notes.append("Human clarifications are authoritative and must shape the implementation plan.")
    if prior_context:
        notes.append(f"Prior context from brain (informational only): {prior_context}")
    return RequirementsDecision(
        goal=goal,
        planning_notes=notes,
        clarifications=clarifications,
    )
