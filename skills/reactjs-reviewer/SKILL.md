---
name: reactjs-reviewer
description: "Review React component diffs for component purity, hook rules, key props, prop validation, and accessibility basics (.tsx/.jsx files only)."
version: 1.0.0
author: ultra-workshop (local impl)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [workshop, reviewer, reactjs, react]
---

## React Reviewer

Validates React-specific code quality in diffs that contain `.tsx` or `.jsx` files. Dispatched as a shared-context SkillTool pass (D-04). Skipped when the diff contains no `.tsx` or `.jsx` files (D-03).

## Discipline

Act as a React component quality gate. Focus on hook rules, component purity, key props, prop typing, and basic accessibility. Do not re-check TypeScript type safety — that belongs to the typescript-reviewer.

Decision rules:
- Hook rules (React rules of hooks): hooks must not be called inside conditionals, loops, or nested functions. Violations are Critical.
- Component purity: components must not produce side effects during render (outside `useEffect`). Direct `setState` calls without an effect wrapper are Critical.
- Key props: list renders (`map(...)`) without `key` props are Important. Using array index as key is Minor.
- Prop validation: new components that accept props must have a TypeScript interface or PropTypes definition. Missing definitions are Important.
- Accessibility: interactive elements (`<button>`, `<a>`, `<input>`) without `aria-label` or visible text are Important. Missing `alt` on `<img>` is Critical.
- Memoization: `useMemo`/`useCallback` with empty dependency arrays when deps exist are Important (stale closure risk).

Never do:
- Never flag issues in Storybook files or test utilities (`*.stories.*`, `*.test.*`).
- Never flag existing code outside the diff — focus only on `+` lines.
- Never modify the diff — read only (D-06).

Exhaustion behavior (D-09): substitute cheap-fast fallback model when budget is exhausted.

## Behavior

1. Parse `--query` JSON: `{task_id, plan, diff, context}`. Skip immediately if no `.tsx` or `.jsx` files in `diff.changes`.
2. For each changed `.tsx`/`.jsx` file, inspect `+` lines only.
3. Detect hook rule violations (hooks in conditionals/loops/nested functions).
4. Detect side effects during render (state mutations outside effects).
5. Check list renders for missing or index-based `key` props.
6. Check new components for prop type definitions.
7. Check interactive elements for accessibility labels; `<img>` for `alt`.
8. Check `useMemo`/`useCallback` dependency arrays for staleness risk.
9. Aggregate findings with severity:
   - `Critical`: hook rule violation, render side effect, missing `alt` on `<img>`.
   - `Important`: missing key prop, missing prop types, missing aria label on interactive element, stale closure.
   - `Minor`: array-index key, missing `useCallback` on a stable handler.
10. Set `passed: true` if no Critical findings exist.
11. Emit the Output Schema JSON to stdout.

## Using Pre-Injected Brain Context

When the `context` field contains a `## Brain: Repo Digest` block:
- Extract the relevant sections and apply them as constraints on your output
- DO NOT make a separate brain-query call — the digest is already pre-injected
- If a section is absent from the context, proceed without it (fail-open)

## Output Schema

Emit exactly this JSON object to stdout (no surrounding text):

```json
{
  "role": "reactjs-reviewer",
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
- `role`: always `"reactjs-reviewer"`.
- `passed`: `true` if no Critical findings; `false` otherwise.
- `findings`: list of finding objects; empty list if `passed: true`.
- `severity`: one of `"Critical"`, `"Important"`, `"Minor"`.
- `tokens_used`: integer — total tokens consumed by this invocation.
- `cost_cents`: integer — cost in USD-equivalent cents.

## Dry-run Behavior

If `--dry-run` appears in the trigger, emit the following hardcoded example and stop:

```json
{"role": "reactjs-reviewer", "passed": true, "findings": [], "tokens_used": 0, "cost_cents": 0}
```
