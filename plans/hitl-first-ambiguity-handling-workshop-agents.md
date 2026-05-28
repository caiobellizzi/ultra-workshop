# HITL-First Ambiguity Handling For Workshop Agents

## Summary
Add a first-class clarification path so agents never resolve uncertain product intent themselves. Coder must not ask reviewer for clarification. Reviewer may only return concrete defects for retry; ambiguity routes to HITL, then the same task resumes from planning with the human answer.

## Key Changes
- Remove task-specific prompting and checks:
  - Delete the OpenHarness/"12-factor" assumptions from `workshop_coder.py`.
  - Delete hardcoded HKUDS/OpenHarness semantic checks from `workshop/reviewer.py`.
  - Keep only generic batch safety, timeouts, path/syntax/test/secret checks, and plan-sourced semantic checks.

- Add a dedicated requirements gate before planner:
  - New gate returns either `ready` or `needs_clarification`.
  - It may use LLM reasoning to detect ambiguity and draft options, but it must not choose an interpretation.
  - Ambiguous product/domain phrases like "12 factory practices" always produce HITL clarification.

- Add a generic `ClarificationRequest` control type:
  - Fields: `task_id`, `source_stage`, `reason`, `questions[]`, `options[]`, `allow_free_text=true`, and evidence/context.
  - `run_specialist()` detects `needs_clarification: true` before validating normal stage output and raises a typed control exception.
  - Any stage may emit it: requirements gate, planner, coder wrapper, or reviewer.

- Update orchestration/HITL flow:
  - `workshop_build.py` catches `ClarificationRequest`, writes task state, exits with a HITL payload using `hitl_type="clarification"`.
  - `workshop-build` skill asks Telegram with batched questions, options, and free-text support.
  - On answer, it relaunches `workshop_build.py` with the same `task_id` plus a clarifications file.
  - Resume always restarts from requirements gate/planner so the human answer becomes part of the plan, not a private coder/reviewer message.
  - Final PR approval remains a separate `hitl_type="approval"` gate.

- Clarify retry policy:
  - Reviewer concrete defects retry coder up to the existing 3 total attempts.
  - Reviewer ambiguity emits `ClarificationRequest`, not retry feedback.
  - Coder/Aider no-diff or clarification-like output emits `ClarificationRequest`, unless logs show infrastructure failure.
  - Coder receives reviewer defect feedback only; it never asks reviewer questions.

## Interface Changes
- Add Pydantic models for `ClarificationRequest` and `ClarificationQuestion`.
- Add `--task-id` and `--clarifications-file` to `workshop_build.py` for same-task resume.
- Extend HITL JSON payload with `hitl_type`, using:
  - `clarification` for ambiguity questions.
  - `approval` for push/PR approval.

## Test Plan
- Requirements gate returns `needs_clarification` for "12 factory practices" with multiple options plus free-text enabled.
- Requirements gate passes through clear tasks without changing their meaning.
- `run_specialist()` routes `needs_clarification` JSON before normal schema validation.
- `workshop_build.py` preserves the same `task_id` across clarification resume.
- Coder no-diff/clarification output becomes HITL, not a hang or reviewer retry.
- Reviewer returns retryable defects for path/syntax/test issues, but clarification requests for ambiguous intent.
- Regression: final approval flow still exits with HITL approval payload and push remains approval-gated.

## Assumptions
- HITL is the only authority for ambiguous product intent.
- Agents may use repo facts and trivial operational defaults, but not infer domain meaning.
- Ambiguity questions should be batched when independent.
- Reviewer semantic enforcement must come from the human-approved plan, not hardcoded domain rules.
