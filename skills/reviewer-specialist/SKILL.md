---
name: reviewer-specialist
description: "Review a code diff against its Plan and return a pass/fail Review. Called by workshop_build.py via hermes-skill-run.sh."
version: 1.0.0
author: ultra-workshop (local impl)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [workshop, reviewer, review]
---

## Reviewer Specialist

Reviews a code diff against the implementation Plan and produces a structured pass/fail Review.

Production routing is deterministic: `scripts/hermes-skill-run.sh` calls
`/opt/ultra-workshop/hermes-skills/workshop_reviewer.py` directly instead of
asking Hermes chat to assemble the control JSON. This keeps the pipeline's
blocking review gate fast, bounded, and parseable.

## Behavior

1. Parse the `--query` argument (JSON string with keys: `task_id`, `plan`, `diff`, `context`)
2. Compare `diff.changes` (list of file changes) against `plan.steps` and `plan.affected_files`:
   - Were all plan steps addressed in the diff?
   - Are the changed files a subset of `plan.affected_files`?
   - Does the diff introduce any obvious regressions or security issues?
   - Is the code quality acceptable (no syntax errors, no hardcoded secrets)?
   - Do changed paths look like valid files rather than accidental shell command artifacts?
3. Determine outcome:
   - If all steps are addressed and no blocking issues exist → `passed=true`, `blocking_issues=[]`
   - If any blocking issue is found → `passed=false`, list each issue in `blocking_issues`
4. Write a `feedback` summary sentence (plain text, no markdown)
5. Emit the Review JSON object to stdout as the final output

## Output Schema

Emit exactly this JSON object to stdout (no surrounding text):

```json
{
  "passed": true,
  "feedback": "string — one sentence summary of the review outcome",
  "blocking_issues": []
}
```

Fields:
- `passed`: boolean — `true` if review passed, `false` if blocking issues were found
- `feedback`: one sentence, plain text
- `blocking_issues`: list of strings, each describing one blocking issue; empty list if `passed=true`

## Dry-run Behavior

If `--dry-run` appears in the trigger, emit the following hardcoded example and stop without further processing:

```json
{"passed": true, "feedback": "dry-run review passed", "blocking_issues": []}
```
