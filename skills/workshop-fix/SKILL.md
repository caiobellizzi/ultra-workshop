---
name: workshop-fix
description: "Fix a GitHub issue: /fix <issue-url> fetches the issue and runs the 5-role build pipeline ending in a PR on human approval."
version: 1.0.0
author: ultra-workshop (local impl)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [workshop, fix, issue, pipeline, pr]
---

## Workshop Fix

Fetches a GitHub issue and runs the full workshop build pipeline to produce a PR fix.

## Behavior

The skill body handles two kinds of turns: the initial `/fix` trigger turn, and the background-job notification turn that fires when the pipeline subprocess finishes.

### A. Initial `/fix <issue-url>` turn

1. Extract the issue URL from the user trigger (everything after `/fix`)
2. Extract `session_id` and `chat_id` from context if available (defaults: session_id="", chat_id="7113965359")
3. If `--dry-run` appears in the trigger: print dry-run message and stop without calling terminal
4. Fire the pipeline as a **background job** (the foreground `terminal` tool hard-caps at 600s; the pipeline runs 12–20 min):
   ```
   terminal(command="python3 /opt/ultra-workshop/hermes-skills/workshop_fix.py --issue-url \"<url>\" --session-id \"<session_id>\" --chat-id \"<chat_id>\"",
            background=true, notify_on_complete=true)
   ```
5. Reply: `"🔧 Workshop pipeline started in background. I'll ping you when it's ready for approval."` and end the turn.

`workshop_fix.py` internally fetches the issue title, body, and number via `gh issue view`, composes a task string `"Fix issue #<N>: <title>\n\n<body[:500]>"`, then delegates to `workshop_build.py` and propagates its exit code.

### B. Background-job completion notification turn

Branch on the exit code from the captured terminal result:

- `exit 0`: pipeline succeeded without HITL (unexpected — log and return last 500 chars of stdout).
- `exit 1`: pipeline failed — reply with the last 500 chars of stderr.
- `exit 2` (needs_approval):
  - Parse the JSON from the last stdout line emitted by `workshop_build.py` (forwarded through `workshop_fix.py`).
  - Call `clarify` with the value of `summary` from the JSON.
  - If approved, run the push step in **foreground** (no `background` flag — push is <30s):
    ```
    terminal(command="python3 /opt/ultra-workshop/hermes-skills/workshop_push.py --task-id \"<task_id>\" --branch \"<branch>\" --workspace-dir \"<workspace_dir>\" --plan-goal \"<plan_goal>\" --diff-summary \"<diff_summary>\"")
    ```
    Return the final stdout (PR URL line from `workshop_push.py`).
  - If rejected, reply: `"PR creation rejected for task <task_id>."`

## Pipeline Flow

```
gh issue view <url>     (fetch issue title + body)
  → workshop_build.py
    → triage-specialist
    → planner-specialist
    → coder-specialist
    → reviewer-specialist  (retry up to 2 times if review.passed is False)
    → [exit 2 + HITL clarify gate]
    → workshop_push.py   (on approval)
```

## Dry-run Behavior

If `--dry-run` appears in the trigger, `workshop_fix.py` exits 0 with:
```
[dry-run] would fetch issue and run workshop pipeline
[dry-run] issue-url: '<url>'
```
No `gh` API calls are made. No LLM calls are made.
