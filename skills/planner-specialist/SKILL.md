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
Production calls are handled by the deterministic `workshop_planner.py` script
through `hermes-skill-run.sh`; this skill body is retained as documentation and
as a fallback if it is invoked directly.

## Behavior

You receive a single user message containing the `--query` argument (JSON with keys: `task_id`, `goal`, `triage_result`, `context`).

If the `terminal` tool is available, call the deterministic planner and forward stdout verbatim:

```
terminal(command="python3 /opt/ultra-workshop/hermes-skills/workshop_planner.py --query \"<query>\"", timeout=30)
```

If no tools are available, emit the Plan JSON as your FIRST response. No preamble. No explanation. No tool calls before the JSON.

**Forbidden tools** (do NOT invoke any of these — the planner has everything it needs in the prompt):
- `search_files`, `read_file`, `list_files`, `grep_files` — do NOT explore the codebase
- `code_execution` — no ad hoc code execution
- `web_search`, `web_extract`, `web_fetch` — no web access
- `browser_*` — no browsing

The only allowed `terminal` usage is the exact `workshop_planner.py` command above.

**Allowed (optional, use sparingly):**
- `brain-query` — only if `context` is empty AND the task explicitly requires knowledge of repo-specific conventions (e.g. "add a feature flag in the existing flag system"). Skip Brain for self-contained tasks like "add a fibonacci function with docstring and test".

**Steps (perform internally — do NOT call tools to do these):**
1. Read `--query` from the prompt
2. From `goal` + `triage_result`, identify 2–5 concrete sequential implementation steps; each step lists the files it will touch
3. Collect `affected_files` (flat list of all paths touched across steps)
4. Emit the Plan JSON to stdout. JSON only — nothing before, nothing after.

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
