---
name: planner-specialist
description: "Generate a step-by-step implementation Plan for a workshop task. Called by workshop_build.py via hermes-skill-run.sh."
version: 1.0.0
author: ultra-workshop (local impl)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [workshop, planner, plan]
---

## Planner Specialist

Generates a structured implementation Plan from a task goal and triage result.

## Behavior

1. Parse the `--query` argument (JSON string with keys: `task_id`, `goal`, `triage_result`, `context`)
2. If `context` does not already contain relevant code patterns for the goal, query Brain using the brain-query toolset to find related patterns
3. Break the goal into 2–5 concrete, sequential implementation steps; each step identifies the files it touches
4. Identify all `affected_files` that the implementation will create or modify, based on the goal and any Brain query results
5. Emit the Plan JSON object to stdout as the final output

## Output Schema

Emit exactly this JSON object to stdout (no surrounding text):

```json
{
  "goal": "string — the original task goal",
  "steps": [
    {"id": "1", "description": "string — concrete action", "files": ["path/to/file.py"]}
  ],
  "affected_files": ["path/to/file.py"]
}
```

Fields:
- `goal`: the original task goal string (pass through from query)
- `steps`: list of 2–5 steps; each step has `id` (string integer), `description` (plain text), `files` (list of strings, may be empty)
- `affected_files`: flat list of all file paths that will be touched across all steps

## Dry-run Behavior

If `--dry-run` appears in the trigger, emit the following hardcoded example and stop without further processing:

```json
{"goal": "dry-run", "steps": [{"id": "1", "description": "dry-run step", "files": []}], "affected_files": []}
```
