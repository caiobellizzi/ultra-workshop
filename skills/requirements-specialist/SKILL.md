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
