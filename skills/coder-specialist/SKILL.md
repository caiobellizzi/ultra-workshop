---
name: coder-specialist
description: "Clone test-workshop-sandbox, run aider_runner.py to implement a Plan, return Diff JSON with workspace_dir. Called by workshop_build.py via hermes-skill-run.sh."
version: 1.0.0
author: ultra-workshop (local impl)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [workshop, coder, aider, diff]
---

## Coder Specialist

Clones the test-workshop-sandbox repository into a temporary workspace, runs aider_runner.py to implement a Plan, and returns a Diff JSON containing the workspace directory for downstream steps.

## Behavior

Envelope assembly is performed by a deterministic script — the skill body just invokes it and forwards stdout verbatim. No JSON construction by the LLM.

1. If `--dry-run` appears in the trigger:
   ```
   terminal python3 /opt/ultra-workshop/hermes-skills/workshop_coder.py --query "<query>" --dry-run
   ```
   Forward stdout and stop.

2. Otherwise:
   ```
   terminal python3 /opt/ultra-workshop/hermes-skills/workshop_coder.py --query "<query>"
   ```
   Forward stdout verbatim — it is already the Diff JSON envelope. Do NOT wrap, prefix, or annotate.

The script internally clones the sandbox, creates `workshop/{task_id}`, runs `aider_runner.py`, and prints the Diff JSON envelope to stdout.

## Output Schema

Emit exactly this JSON object to stdout (no surrounding text):

```json
{
  "summary": "string — first 500 chars of aider stdout output",
  "changes": [],
  "branch": "workshop/{task_id}",
  "workspace_dir": "/tmp/uws-sandbox-{task_id}/"
}
```

Fields:
- `summary`: string containing the aider output (truncated to 500 chars)
- `changes`: list of file-change objects; **prefer empty (`[]`)** — the reviewer reads `summary`, not `changes`. If you do populate it, each entry MUST be `{"path": "<file-path>", "diff": "<unified-diff>"}`. Do **not** use the key `file` — the validator accepts it but `path` is canonical.
- `branch`: the git branch name in format `workshop/{task_id}`
- `workspace_dir`: the absolute path to the cloned sandbox workspace — MUST be present and non-empty

## Dry-run Behavior

If `--dry-run` appears in the trigger, emit the following hardcoded example and stop without further processing:

```json
{"summary": "dry-run coder", "changes": [], "branch": "workshop/dry-run", "workspace_dir": "/tmp/uws-sandbox-dry-run"}
```
