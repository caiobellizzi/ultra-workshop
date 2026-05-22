---
name: pr-opener
description: "Post-approval: git push + gh pr create + ADR write-back via workshop_push.py. Called by workshop-build SKILL.md body after HITL approval."
version: 1.0.0
author: ultra-workshop (local impl)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [workshop, pr, git, push]
---

## PR Opener

Executes the post-approval pipeline: pushes the task branch to GitHub, creates a Pull Request, and writes an ADR to Brain. This skill is called after the user has explicitly approved the diff via the HITL gate in the calling skill.

## Behavior

1. Parse the `--query` argument (JSON string with keys: `task_id`, `branch`, `workspace_dir`, `plan_goal`, `diff_summary`)
2. Run workshop_push.py with the extracted values:
   ```
   terminal python3 /opt/ultra-workshop/hermes-skills/workshop_push.py --task-id "{task_id}" --branch "{branch}" --workspace-dir "{workspace_dir}" --plan-goal "{plan_goal}" --diff-summary "{diff_summary}"
   ```
3. Capture stdout from the subprocess — the last line will contain `pr_url=<url>`
4. Extract the PR URL from the last `pr_url=` line in the output
5. Emit the result JSON object to stdout as the final output

## ADR Frontmatter Note

`workshop_push.py` writes the ADR with these exact dotted-namespace frontmatter keys:

```yaml
workshop.task_id: <task_id>
workshop.status: done
workshop.pr_url: <pr_url>
system.created_by: workshop
date: <YYYY-MM-DD>
```

## Output Schema

Emit exactly this JSON object to stdout (no surrounding text):

```json
{
  "pr_url": "https://github.com/caiobellizzi/test-workshop-sandbox/pull/N",
  "status": "opened"
}
```

Fields:
- `pr_url`: the full GitHub PR URL returned by `gh pr create`
- `status`: `"opened"` on success

## Dry-run Behavior

If `--dry-run` appears in the trigger, emit the following hardcoded example and stop without further processing:

```json
{"pr_url": "https://github.com/caiobellizzi/test-workshop-sandbox/pull/0", "status": "dry-run"}
```
