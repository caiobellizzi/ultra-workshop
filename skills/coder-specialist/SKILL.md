---
name: coder-specialist
description: "Clone the selected active repo, run aider_runner.py to implement a Plan, return Diff JSON with workspace_dir. Called by workshop_build.py via hermes-skill-run.sh."
version: 1.0.0
author: ultra-workshop (local impl)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [workshop, coder, aider, diff]
---

## Coder Specialist

Clones the selected active repository into a temporary workspace, runs aider_runner.py to implement a Plan, and returns a Diff JSON containing the workspace directory for downstream steps.

## Behavior

Envelope assembly is performed by a deterministic script — the skill body just invokes it and forwards stdout verbatim. No JSON construction by the LLM.
Production calls are handled directly by `hermes-skill-run.sh`, which executes
`workshop_coder.py` without starting a Hermes chat. This skill body is retained
as documentation and as a fallback if invoked directly.

**Call the `terminal` tool with `timeout=900`** — aider runs can take up to ~15 minutes; the Hermes terminal-tool default cap (180s) is far too short. The wrapper sets `TERMINAL_TIMEOUT=900` in the env as a backstop, but pass `timeout=900` explicitly so the per-call kwarg overrides any session default.

1. If `--dry-run` appears in the trigger:
   ```
   terminal(command="python3 /opt/ultra-workshop/hermes-skills/workshop_coder.py --query \"<query>\" --dry-run", timeout=900)
   ```
   Forward stdout and stop.

2. Otherwise:
   ```
   terminal(command="python3 /opt/ultra-workshop/hermes-skills/workshop_coder.py --query \"<query>\"", timeout=900)
   ```
   Forward stdout verbatim — it is already the Diff JSON envelope. Do NOT wrap, prefix, or annotate.

The script internally clones the selected repo from the query payload, creates `workshop/{task_id}`, runs `aider_runner.py`, and prints the Diff JSON envelope to stdout.

## Output Schema

Emit exactly this JSON object to stdout (no surrounding text):

```json
{
  "summary": "string — first 500 chars of aider stdout output",
  "changes": [
    {"path": "utils.py", "diff": "@@ ... unified diff ..."}
  ],
  "branch": "workshop/{task_id}",
  "workspace_dir": "/tmp/uws-sandbox-{task_id}/",
  "repo_full_name": "owner/name",
  "default_branch": "main"
}
```

Fields:
- `summary`: string containing the aider output (truncated to 500 chars)
- `changes`: list of file-change objects, one per modified file. The script computes this from `git diff` against the pre-aider HEAD. Each entry MUST be `{"path": "<file-path>", "diff": "<unified-diff>"}` (per-file diff capped at 4000 chars). The reviewer compares this list against `plan.steps` and `plan.affected_files`. Do **not** use the key `file` — the validator accepts it but `path` is canonical.
- `branch`: the git branch name in format `workshop/{task_id}`
- `workspace_dir`: the absolute path to the cloned target repo workspace — MUST be present and non-empty
- `repo_full_name`: selected GitHub repo in `owner/name` form
- `default_branch`: selected repo base branch

## Dry-run Behavior

If `--dry-run` appears in the trigger, emit the following hardcoded example and stop without further processing:

```json
{"summary": "dry-run coder", "changes": [], "branch": "workshop/dry-run", "workspace_dir": "/tmp/uws-sandbox-dry-run", "repo_full_name": "caiobellizzi/test-workshop-sandbox", "default_branch": "main"}
```
