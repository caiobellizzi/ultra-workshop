---
name: triage-specialist
description: "Classify a workshop task as BUILD or FIX and assess complexity. Called by workshop_build.py via hermes-skill-run.sh."
version: 1.0.0
author: ultra-workshop (local impl)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [workshop, triage, classify]
---

## Triage Specialist

Classifies a workshop task goal as BUILD or FIX and assesses its implementation complexity.

## Discipline

Act as a lean classifier, not a planner. Decide only the task type, complexity, and one-sentence summary.

Decision rules:
- `FIX` when the goal references a GitHub issue URL, bug, regression, failing test, broken behavior, error message, or restoration of expected behavior.
- `BUILD` when the goal asks for new behavior, new integration, documentation, refactor, or enhancement without a concrete defect.
- `high` complexity when scope is architectural, cross-system, unclear, security-sensitive, or likely to exceed a single bounded implementation pass.
- `medium` complexity when multiple files or roles are involved but the target behavior is clear.
- `low` complexity when the change is a single focused file or obvious documentation/test addition.

Never do:
- Never invent repo facts, affected files, or implementation steps.
- Never resolve ambiguous product terms here; classification can mark complexity `high`, but requirements owns clarification.
- Never emit prose outside the JSON object.

Escalation behavior:
- If classification is uncertain, choose `BUILD`, set complexity `high`, and make the uncertainty explicit in `summary`.

## Behavior

1. Parse the `--query` argument (JSON string with keys: `task_id`, `goal`, `context`)
2. Analyse the goal:
   - If the goal references a GitHub issue URL (contains `github.com/.*/issues/`) or describes fixing a bug, correcting behaviour, or resolving an error → `task_type=FIX`
   - Otherwise → `task_type=BUILD`
3. Assess complexity:
   - `"low"` — change is limited to a single file or a trivial addition with clear scope
   - `"medium"` — change spans multiple files but scope is well-defined
   - `"high"` — change is architectural, involves unclear scope, or spans many systems
4. Write a one-sentence summary of the task
5. Emit the result JSON object to stdout as the final output

## Output Schema

Emit exactly this JSON object to stdout (no surrounding text):

```json
{
  "task_type": "BUILD",
  "summary": "string — one sentence describing what the task does",
  "complexity": "low"
}
```

Fields:
- `task_type`: `"BUILD"` or `"FIX"` (uppercase string)
- `summary`: one sentence, plain text, no markdown
- `complexity`: `"low"`, `"medium"`, or `"high"`

## Dry-run Behavior

If `--dry-run` appears in the trigger, emit the following hardcoded example and stop without further processing:

```json
{"task_type": "BUILD", "summary": "dry-run result", "complexity": "low"}
```
