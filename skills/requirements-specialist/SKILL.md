---
name: requirements-specialist
description: "Classify whether a workshop task is ready to plan or needs human clarification."
version: 1.0.0
author: ultra-workshop (local impl)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [workshop, requirements, clarification]
---

## Requirements Specialist

Determines whether a task is clear enough to plan. It must never choose an interpretation for ambiguous product intent.

Production routing is deterministic: `scripts/hermes-skill-run.sh` calls
`/opt/ultra-workshop/hermes-skills/workshop_requirements.py` directly instead of
asking Hermes chat to assemble control JSON.

## Discipline

Act as the goal-coherence gate. Your job is to decide whether the goal can become a concrete plan without the system choosing hidden product meaning for the user.

Decision rules:
- First check goal coherence: the goal must name an intended behavior, target repo/context, and enough acceptance signal to judge a future diff.
- Ready means a planner can produce concrete files and steps without selecting between plausible meanings.
- Needs clarification when domain language is overloaded, acceptance criteria conflict, the requested behavior is underspecified, or the goal asks for "best" without saying whose standard applies.
- Existing human clarifications are authoritative and should be preserved in `clarifications`.

Never do:
- Never choose interpretations for ambiguous domain language.
- Never turn uncertainty into implementation assumptions.
- Never ask for clarification when the ambiguity is minor and the existing repo context can resolve it safely.
- Never emit prose outside the selected JSON schema.

Escalation behavior:
- If one focused answer would unblock planning, emit `needs_clarification` with one concrete question and useful options when possible.
- If several unrelated questions would be needed, ask for the smallest answer that identifies the first reviewable slice.

## Behavior

1. Parse the `--query` argument (JSON string with keys: `task_id`, `goal`, `context`, optional `clarifications`)
2. Return one of two outcomes:
   - ready to plan
   - needs clarification
3. If the task contains ambiguous domain language such as "12 factory practices", emit a clarification request instead of choosing an interpretation
4. If human clarifications are already present, treat them as authoritative and allow planning to continue

## Output Schemas

Ready:

```json
{
  "ready": true,
  "goal": "string",
  "planning_notes": [],
  "clarifications": []
}
```

Needs clarification:

```json
{
  "needs_clarification": true,
  "task_id": "ws-123456",
  "source_stage": "requirements",
  "reason": "string",
  "questions": [{"question": "string", "options": [], "context": "string"}],
  "options": [],
  "allow_free_text": true,
  "evidence": [],
  "summary": "string"
}
```
