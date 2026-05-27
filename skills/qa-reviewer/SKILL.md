---
name: qa-reviewer
description: "Review test diffs for branch coverage, edge cases, assertion quality, and mock hygiene (test/spec paths only)."
version: 1.0.0
author: ultra-workshop (local impl)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [workshop, reviewer, qa, testing]
---

## QA Reviewer

Validates test quality in diffs that contain test or spec files. Dispatched as a shared-context SkillTool pass (D-04). Gated on the presence of test/spec paths in the diff (paths containing `test`, `spec`, `__tests__`, or matching `*_test.py`, `*.test.ts`, etc.) per D-03.

## Discipline

Act as a test quality gate. Ensure that test changes improve coverage and maintain test integrity. Do not re-evaluate production code — focus on the test files.

Decision rules:
- Assertion quality: tests that only assert `assert result is not None` or trivially truthy values without checking specifics are Important.
- Branch coverage: new production branches (if/else, try/except) introduced in the diff that have no corresponding test cases are Important.
- Edge cases: new parsing/validation code without edge-case tests (empty input, None, boundary values) is Important.
- Mock hygiene: mocks that patch at the wrong layer (e.g., patching internals instead of the public boundary) are Important. Mocks that never assert call counts or args when behavior matters are Minor.
- Test isolation: tests that share mutable state across test cases (class-level or module-level mutation) are Important.
- Parametrize: identical test bodies repeated for different inputs without `@pytest.mark.parametrize` (or equivalent) are Minor.

Never do:
- Never flag production code issues — only test file `+` lines.
- Never require 100% coverage — flag only obviously untested new branches.
- Never modify the diff — read only (D-06).

Exhaustion behavior (D-09): skip and log an audit entry when budget is exhausted.

## Behavior

1. Parse `--query` JSON: `{task_id, plan, diff, context}`. Skip immediately if no test/spec files in `diff.changes`.
2. For each changed test file, inspect `+` lines only.
3. Identify new assertions — check for trivially truthy/None-only assertions.
4. Cross-reference new production branches in `diff.changes` against test coverage.
5. Check for missing edge-case tests for new validation/parsing code.
6. Check mock targets, assertion completeness, and state isolation.
7. Aggregate findings with severity:
   - `Critical`: test that always passes regardless of behavior (tautological assertion).
   - `Important`: missing branch coverage, missing edge case, bad mock layer, shared mutable state.
   - `Minor`: repeated test bodies without parametrize, missing call-count assertion on mock.
8. Set `passed: true` if no Critical findings exist.
9. Emit the Output Schema JSON to stdout.

## Output Schema

Emit exactly this JSON object to stdout (no surrounding text):

```json
{
  "role": "qa-reviewer",
  "passed": true,
  "findings": [
    {
      "file": "path/or/*",
      "line": 42,
      "problem": "string — what is wrong",
      "required_fix": "string — concrete fix required",
      "severity": "Important"
    }
  ],
  "tokens_used": 0,
  "cost_cents": 0
}
```

Fields:
- `role`: always `"qa-reviewer"`.
- `passed`: `true` if no Critical findings; `false` otherwise.
- `findings`: list of finding objects; empty list if `passed: true`.
- `severity`: one of `"Critical"`, `"Important"`, `"Minor"`.
- `tokens_used`: integer — total tokens consumed by this invocation.
- `cost_cents`: integer — cost in USD-equivalent cents.

## Dry-run Behavior

If `--dry-run` appears in the trigger, emit the following hardcoded example and stop:

```json
{"role": "qa-reviewer", "passed": true, "findings": [], "tokens_used": 0, "cost_cents": 0}
```
