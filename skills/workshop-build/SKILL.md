---
name: workshop-build
description: "Build a coding task: /build <task> runs the 5-role pipeline (triage→planner→coder→reviewer→HITL) and opens a PR after human approval."
version: 1.0.0
author: ultra-workshop (local impl)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [workshop, build, pipeline, pr, coding]
---

## Workshop Build

Runs the full 5-role workshop pipeline for a coding task and opens a PR on human approval.

## Behavior

The skill body handles two kinds of turns: the initial `/build` trigger turn, and the background-job notification turn that fires when the pipeline subprocess finishes.

### A. Initial `/build <task>` turn

1. Extract the task description from the user trigger (everything after `/build`)
2. Extract `session_id` and `chat_id` from context if available (defaults: session_id="", chat_id="7113965359")
3. If `--dry-run` appears in the trigger: print dry-run message and stop without calling terminal
4. Fire the pipeline as a **background job** (the foreground `terminal` tool hard-caps at 600s; the pipeline runs 12–20 min):
   ```
   terminal(command="python3 /opt/ultra-workshop/hermes-skills/workshop_build.py --task \"<task>\" --session-id \"<session_id>\" --chat-id \"<chat_id>\"",
            background=true, notify_on_complete=true)
   ```
5. Reply: `"🔧 Workshop pipeline started in background. I'll ping you when it's ready for approval."` and end the turn.

### B. Background-job completion notification turn

When the background job completes, Hermes opens a fresh agent turn carrying the terminal result (exit code + captured stdout/stderr). Branch on the exit code:

- `exit 0`: pipeline succeeded without HITL (unexpected — log and return last 500 chars of stdout).
- `exit 1`: pipeline failed — reply with the last 500 chars of stderr.
- `exit 2` (needs_approval):
  - Parse the JSON from the last stdout line emitted by `workshop_build.py`.
  - The JSON contains: `task_id`, `branch`, `workspace_dir`, `plan_goal`, `diff_summary`, `summary`.
  - Call `clarify` with the value of `summary` (e.g. "Review passed. Push branch 'workshop/abc-def' and open PR for: add hello endpoint?").
  - If approved, run the push step in **foreground** (no `background` flag — push is <30s):
    ```
    terminal(command="python3 /opt/ultra-workshop/hermes-skills/workshop_push.py --task-id \"<task_id>\" --branch \"<branch>\" --workspace-dir \"<workspace_dir>\" --plan-goal \"<plan_goal>\" --diff-summary \"<diff_summary>\"")
    ```
    Return the final stdout (PR URL line from `workshop_push.py`).
  - If rejected, reply: `"PR creation rejected for task <task_id>."`

## Pipeline Flow

```
triage-specialist
  → planner-specialist
  → coder-specialist
  → reviewer-specialist  (retry up to 2 times if review.passed is False)
  → [exit 2 + HITL clarify gate]
  → workshop_push.py     (on approval: git push + gh pr create + ADR write-back)
```

## HITL Gate

`workshop_build.py` exits with code 2 and emits a JSON object to stdout:

```json
{
  "needs_approval": true,
  "task_id": "<task-id>",
  "branch": "<branch>",
  "workspace_dir": "<path>",
  "plan_goal": "<goal>",
  "diff_summary": "<summary>",
  "summary": "Review passed. Push branch '<branch>' and open PR for: <goal>?"
}
```

The skill body catches exit code 2, issues a `clarify` with `summary`, and waits for the Telegram inline button response.

- On approval: `workshop_push.py` performs `git push` + `gh pr create` + ADR write-back.
- On rejection: no git operations are performed.

## Dry-run Behavior

If the trigger contains `--dry-run`, `workshop_build.py` prints `[dry-run] would run workshop pipeline` and exits 0. No LLM calls are made. No specialist subprocesses are launched.
