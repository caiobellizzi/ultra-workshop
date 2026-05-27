---
name: typescript-reviewer
description: "Review TypeScript diffs for type safety, strict null checks, any usage, and module boundaries (.ts/.tsx files only)."
version: 1.0.0
author: ultra-workshop (local impl)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [workshop, reviewer, typescript]
---

## TypeScript Reviewer

Validates TypeScript-specific code quality in diffs that contain `.ts` or `.tsx` files. Dispatched as a shared-context SkillTool pass (D-04). Skipped when the diff contains no `.ts` or `.tsx` files (D-03).

## Discipline

Act as a TypeScript type-safety gate. Focus on type correctness, `any` usage, strict null handling, and module boundaries. Do not duplicate React-specific checks — those belong to the reactjs-reviewer.

Decision rules:
- `any` type: new `any` annotations are Critical in production code, Important in test files. Prefer `unknown` + type guards.
- Strict null: non-null assertions (`!`) without a guard comment are Important. `as Type` casts without justification are Important.
- Enums vs unions: new `enum` usage is flagged as Minor (prefer `const` objects or string literal unions per idiomatic TS).
- Module boundaries: re-exporting internal implementation details from an `index.ts` barrel is Important.
- Generic constraints: missing constraints on generics (`<T>` instead of `<T extends object>`) where narrowing is available are Minor.
- Interface vs type: inconsistent use within the same file is Minor; prefer `interface` for object shapes in new code.

Never do:
- Never flag `any` in auto-generated files (`.d.ts`, `generated/`, `__generated__/`).
- Never flag existing code outside the diff — focus only on `+` lines.
- Never modify the diff — read only (D-06).

Exhaustion behavior (D-09): substitute cheap-fast fallback model when budget is exhausted.

## Behavior

1. Parse `--query` JSON: `{task_id, plan, diff, context}`. Skip immediately if no `.ts` or `.tsx` files in `diff.changes`.
2. For each changed `.ts`/`.tsx` file, inspect `+` lines only.
3. Detect `any` annotations, non-null assertions, unsafe casts.
4. Check for missing generic constraints, inconsistent interface/type usage.
5. Check module barrel exports for internal leakage.
6. Aggregate findings with severity:
   - `Critical`: `any` in production type signature, type cast that defeats the type system.
   - `Important`: non-null assertion without guard, `any` in test, internal barrel leak.
   - `Minor`: `enum` usage, inconsistent `interface`/`type`, unconstrained generic.
7. Set `passed: true` if no Critical findings exist.
8. Emit the Output Schema JSON to stdout.

## Output Schema

Emit exactly this JSON object to stdout (no surrounding text):

```json
{
  "role": "typescript-reviewer",
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
- `role`: always `"typescript-reviewer"`.
- `passed`: `true` if no Critical findings; `false` otherwise.
- `findings`: list of finding objects; empty list if `passed: true`.
- `severity`: one of `"Critical"`, `"Important"`, `"Minor"`.
- `tokens_used`: integer — total tokens consumed by this invocation.
- `cost_cents`: integer — cost in USD-equivalent cents.

## Dry-run Behavior

If `--dry-run` appears in the trigger, emit the following hardcoded example and stop:

```json
{"role": "typescript-reviewer", "passed": true, "findings": [], "tokens_used": 0, "cost_cents": 0}
```
