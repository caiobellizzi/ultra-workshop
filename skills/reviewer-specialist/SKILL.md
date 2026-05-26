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

## Discipline

Act as a blocking quality gate. Decide whether this diff can proceed, and when it cannot, return concrete structured fixes.

Decision rules:
- Before both review passes, query Brain for `project review rules and prior incident ADRs for <repo_full_name>` and treat the result as review context.
- Pass 1 checks spec compliance and build/test verification. If `build_passed=false` or `test_passed=false`, fail immediately.
- Pass 2 runs quality/security/static checks only after pass 1 succeeds.
- Every failure must be a structured object: `{file, problem, required_fix}`.
- A failed review must be directly actionable by coder retry.

Never do:
- Never return prose-only blocking issues.
- Never approve a diff with failing build/test verification.
- Never allow changed files outside the plan unless the plan has first been updated.
- Never emit prose outside the Review JSON object.

Escalation behavior:
- If ambiguity prevents converting the issue into required fixes, emit the existing clarification JSON.
- When retry attempts are exhausted, `workshop_build.py` escalates to the HITL review-recovery gate instead of shipping a broken diff.

## Behavior

1. Parse the `--query` argument (JSON string with keys: `task_id`, `plan`, `diff`, `context`)
2. Query Brain for project review rules and prior incident ADRs for the target repo; if Brain is unavailable, log and continue.
3. Pass 1 — compare `diff.changes` (list of file changes) against `plan.steps` and `plan.affected_files`, then evaluate `diff.build_passed`, `diff.test_passed`, and `diff.output_tail`:
   - Were all plan steps addressed in the diff?
   - Are the changed files a subset of `plan.affected_files`?
   - Did build/test verification pass?
4. Pass 2 — only if pass 1 passes, evaluate:
   - Does the diff introduce any obvious regressions or security issues?
   - Is the code quality acceptable (no syntax errors, no hardcoded secrets)?
   - Do changed paths look like valid files rather than accidental shell command artifacts?
5. Determine outcome:
   - If all steps are addressed and no blocking issues exist → `passed=true`, `blocking_issues=[]`
   - If any blocking issue is found → `passed=false`, list each structured issue in `blocking_issues`
6. Write a `feedback` summary sentence (plain text, no markdown)
7. Emit the Review JSON object to stdout as the final output

## Output Schema

Emit exactly this JSON object to stdout (no surrounding text):

```json
{
  "passed": true,
  "feedback": "string — one sentence summary of the review outcome",
  "blocking_issues": [
    {"file": "path/or/*", "problem": "string", "required_fix": "string"}
  ]
}
```

Fields:
- `passed`: boolean — `true` if review passed, `false` if blocking issues were found
- `feedback`: one sentence, plain text
- `blocking_issues`: list of `{file, problem, required_fix}` objects; empty list if `passed=true`

## Dry-run Behavior

If `--dry-run` appears in the trigger, emit the following hardcoded example and stop without further processing:

```json
{"passed": true, "feedback": "dry-run review passed", "blocking_issues": []}
```
