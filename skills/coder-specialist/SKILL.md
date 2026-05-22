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

1. Parse the `--query` argument (JSON string with keys: `task_id`, `plan`, `workspace_dir`)
2. Determine workspace directory:
   - If `workspace_dir` is absent or empty, create `/tmp/uws-sandbox-{task_id}/`
3. Clone the sandbox repository if `.git` is not already present in `workspace_dir`:
   ```
   terminal git clone https://github.com/caiobellizzi/test-workshop-sandbox.git {workspace_dir}
   ```
4. Create the task branch:
   ```
   terminal git -C {workspace_dir} checkout -b workshop/{task_id}
   ```
5. Run aider_runner.py to implement the plan goal:
   ```
   terminal python3 /opt/ultra-workshop/hermes-skills/aider_runner.py --task "{plan.goal}" --workspace-file "{workspace_dir}/README.md"
   ```
6. Capture the aider stdout output (diff summary). Truncate to first 500 characters if longer.
7. Emit the Diff JSON object to stdout as the final output. The `changes` list may be empty — the reviewer uses the `summary` field for its assessment.

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
- `changes`: list of file-change objects; may be empty (`[]`)
- `branch`: the git branch name in format `workshop/{task_id}`
- `workspace_dir`: the absolute path to the cloned sandbox workspace — MUST be present and non-empty

## Dry-run Behavior

If `--dry-run` appears in the trigger, emit the following hardcoded example and stop without further processing:

```json
{"summary": "dry-run coder", "changes": [], "branch": "workshop/dry-run", "workspace_dir": "/tmp/uws-sandbox-dry-run"}
```
