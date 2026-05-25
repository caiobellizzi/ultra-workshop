---
name: workshop-build
description: "Build a coding task: /build --repo <repo> <task> runs the 5-role pipeline and opens a PR after human approval."
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

### A. Initial `/build --repo <repo> <task>` turn

1. Extract `--repo <repo>` and the task description from the user trigger. If `--repo` is missing, run the backend dry usage path and return its output.
2. Extract `session_id` and `chat_id` from context if available (defaults: session_id="", chat_id="7113965359")
3. If `--dry-run` appears in the trigger, run `workshop_build.py --dry-run` with any parsed `--repo` and `--task`, return stdout, and stop. No LLM calls are made.
4. Fire the pipeline as a **background job** (the foreground `terminal` tool hard-caps at 600s; the pipeline runs 12–20 min).
   Never put raw task text directly inside a shell argument. Telegram link previews can contain quotes and break bash parsing. Put the task in a temp file with a quoted heredoc and pass `--task-file`.
   ```
   terminal(command="TASK_FILE=\"$(mktemp /tmp/uws-build-task.XXXXXX)\"\ncat > \"$TASK_FILE\" <<'__UWS_TASK__'\n<task>\n__UWS_TASK__\npython3 /opt/ultra-workshop/hermes-skills/workshop_build.py --repo \"<repo>\" --task-file \"$TASK_FILE\" --session-id \"<session_id>\" --chat-id \"<chat_id>\"",
            background=true, notify_on_complete=true)
   ```
5. Reply: `"🔧 Workshop pipeline started in background. I'll ping you when it's ready for approval."` and end the turn.

### B. Background-job completion notification turn

When the background job completes, Hermes opens a fresh agent turn carrying the terminal result (exit code + captured stdout/stderr). Branch on the exit code:

- `exit 0`: pipeline succeeded without HITL (unexpected — log and return last 500 chars of stdout).
- `exit 1`: pipeline failed — reply with the last 500 chars of stderr.
- `exit 2` (HITL gate):
  - Parse the JSON from the last stdout line emitted by `workshop_build.py`.
  - Branch on `hitl_type`.
  - `hitl_type="clarification"`:
    - Ask the user the batched clarification questions from `questions[]`, show any `options[]`, and allow free text when `allow_free_text=true`.
    - Write the answers to a temp JSON file and re-launch `workshop_build.py` in the background with the same `--task-id` plus `--clarifications-file <path>`.
    - Resume always restarts from the requirements/planner path so the human answer becomes part of the plan context.
  - `hitl_type="approval"`:
    - The JSON contains: `task_id`, `branch`, `workspace_dir`, `repo_full_name`, `default_branch`, `plan_goal`, `diff_summary`, `summary`.
    - Call `clarify` with the value of `summary` (e.g. "Review passed. Push branch 'workshop/abc-def' and open PR for: add hello endpoint?").
    - If approved, run the push step in **foreground** (no `background` flag — push is <30s). Do not inline `plan_goal` or `diff_summary` in shell arguments; write them to files with quoted heredocs and pass the file paths.
    ```
    terminal(command="PLAN_FILE=\"$(mktemp /tmp/uws-plan-goal.XXXXXX)\"\nDIFF_FILE=\"$(mktemp /tmp/uws-diff-summary.XXXXXX)\"\ncat > \"$PLAN_FILE\" <<'__UWS_PLAN_GOAL__'\n<plan_goal>\n__UWS_PLAN_GOAL__\ncat > \"$DIFF_FILE\" <<'__UWS_DIFF_SUMMARY__'\n<diff_summary>\n__UWS_DIFF_SUMMARY__\npython3 /opt/ultra-workshop/hermes-skills/workshop_push.py --task-id \"<task_id>\" --branch \"<branch>\" --workspace-dir \"<workspace_dir>\" --repo-full-name \"<repo_full_name>\" --base \"<default_branch>\" --plan-goal-file \"$PLAN_FILE\" --diff-summary-file \"$DIFF_FILE\"")
    ```
    Return the final stdout (PR URL line from `workshop_push.py`).
    - If rejected, reply: `"PR creation rejected for task <task_id>."`

## Pipeline Flow

```
triage-specialist
  → planner-specialist
  → coder-specialist
  → reviewer-specialist  (retry up to 2 times if review.passed is False)
  → [exit 2 + clarification HITL if intent is ambiguous]
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
  "repo_full_name": "<owner/name>",
  "default_branch": "<branch>",
  "plan_goal": "<goal>",
  "diff_summary": "<summary>",
  "summary": "Review passed for <owner/name> (<base>). Push branch '<branch>' and open PR for: <goal>?"
}
```

The skill body catches exit code 2, issues a `clarify` with `summary`, and waits for the Telegram inline button response.

- On approval: `workshop_push.py` performs `git push` + `gh pr create` + ADR write-back.
- On rejection: no git operations are performed.

## Dry-run Behavior

If the trigger contains `--dry-run`, `workshop_build.py` prints `[dry-run] would run workshop pipeline` and exits 0. No LLM calls are made. No specialist subprocesses are launched.
