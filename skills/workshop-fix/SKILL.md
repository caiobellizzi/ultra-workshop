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

1. Extract the issue URL from the user trigger (everything after `/fix`)
2. Extract `session_id` and `chat_id` from context if available (defaults: session_id="", chat_id="7113965359")
3. If `--dry-run` appears in the trigger: print dry-run message and stop without calling terminal
4. Run. **You MUST pass `timeout=1800` to the terminal tool** — the pipeline runs 4 specialist subprocess calls and easily exceeds the default 60s timeout.
   ```
   terminal(command="python3 /opt/ultra-workshop/hermes-skills/workshop_fix.py --issue-url \"<url>\" --session-id \"<session_id>\" --chat-id \"<chat_id>\"", timeout=1800)
   ```
5. `workshop_fix.py` internally:
   - Fetches the issue title, body, and number via `gh issue view`
   - Composes a task string: `"Fix issue #<N>: <title>\n\n<body[:500]>"`
   - Delegates to `workshop_build.py` with that task string
   - Propagates the exit code from `workshop_build.py` to the skill body
6. Capture exit code (same pattern as workshop-build):
   - If exit_code == 2 (needs_approval):
     - Parse the JSON from the last stdout line
     - Call `clarify` with the value of `summary` from the JSON
     - If approved:
       ```
       terminal python3 /opt/ultra-workshop/hermes-skills/workshop_push.py --task-id "<task_id>" --branch "<branch>" --workspace-dir "<workspace_dir>" --plan-goal "<plan_goal>" --diff-summary "<diff_summary>"
       ```
     - If rejected:
       Reply: "PR creation rejected for task `<task_id>`."
   - If exit_code == 1: return error output to user
7. Return the final stdout (PR URL or rejection message)

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
