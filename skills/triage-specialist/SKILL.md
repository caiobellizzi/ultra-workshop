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
