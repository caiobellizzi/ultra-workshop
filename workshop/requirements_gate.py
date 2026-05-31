from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field

from workshop.brain_context import _append_digest_section
from workshop.types import ClarificationQuestion, ClarificationRequest


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

    # B7: Extract prior clarifications from pre-injected brain context.
    # T-09-03-04: Result injected into planning_notes only — never overrides current task spec.
    repo = query.get("repo") or {}
    repo_full_name = str(repo.get("full_name") or query.get("repo_full_name") or "").strip()
    raw_context = query.get("context", "")
    prior_context = ""
    if "Prior Clarifications" in raw_context:
        parts = raw_context.split("## Prior Clarifications")
        if len(parts) > 1:
            section = parts[1].split("## ")[0].strip()
            prior_context = section

    clarifications = normalize_clarifications(query.get("clarifications"))
    clarification = maybe_clarification_request(
        task_id,
        goal,
        source_stage="requirements",
        clarifications=clarifications,
    )
    if clarification is not None:
        try:
            question = clarification.questions[0].question if clarification.questions else ""
            if repo_full_name and question:
                _append_digest_section(repo_full_name, "Prior Clarifications", question)
        except Exception:
            pass  # fail-open
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
