---
phase: "04-build-fix-pipeline"
plan: "04-06"
status: completed
completed_at: 2026-05-22
---

# Plan 04-06 — Coder-specialist envelope made deterministic — SUMMARY

## What changed

The 04-05 live UAT exposed that coder-specialist was returning a Python code block instead of the expected Diff JSON envelope, tripping `_extract_json("No JSON object found")`. Root cause: the SKILL.md instructed the LLM to assemble JSON, and the model produced raw code instead.

Fix is structural — moved envelope assembly from the LLM into a deterministic script.

## Files changed

| File | Change |
|------|--------|
| `hermes-skills/workshop_coder.py` | NEW (~125 lines). Parses `--query`, clones sandbox if needed, creates `workshop/{task_id}` branch, runs `aider_runner.py`, emits Diff JSON to stdout. `shell=False` throughout. |
| `skills/coder-specialist/SKILL.md` | Behavior section rewritten — thin invocation of `workshop_coder.py`, forwards stdout verbatim. LLM no longer touches JSON assembly. Output schema doc retained for reference. |
| `workshop/orchestrator.py` | Added `_FENCE_RE` to strip ```json / ``` fenced blocks in `_extract_json` before brace-matching. Defensive insurance for the other specialists. |
| `tests/phase-04/test_extract_json.py` | NEW. 9 unit tests covering bare JSON, json-fenced, plain-fenced, post-think, fenced+think, no-JSON-raises with/without skill_name, fence-with-code-falls-through. |
| `tests/phase-04/coder-smoke.bats` | NEW. SSH-based dry-run test asserting envelope keys (summary/changes/branch/workspace_dir) present. |

## Verification

- `python3 -m pytest tests/phase-04/ -q` → **30 passed** (was 21 + 9 new).
- `bats tests/phase-04/build-smoke.bats` → **3 ok**.
- `bats tests/phase-04/fix-smoke.bats` → **2 ok**.
- `bats tests/phase-04/coder-smoke.bats` → **1 ok**.
- `bats tests/phase-04/model-matrix-smoke.bats` → **6 ok**.
- VPS deploy verified: `workshop_coder.py --dry-run` over SSH returns valid Diff JSON.

## Remaining (human UAT)

Re-run the live `/build` task that originally exposed the bug:

```
/build add a fibonacci(n) function to utils.py with a docstring and a basic test
```

Expected flow:
1. Background-ack within seconds.
2. Progress lines `[workshop] triage_complete done`, `plan_complete done`, `coder_complete done`, `review_complete done` over 10–20 min.
3. HITL clarify with yes/no buttons.
4. Approve → PR URL within ~30s.

Forensic command if coder fails again:
```bash
ssh root@31.97.130.253 "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 /opt/ultra-workshop/hermes-skills/workshop_coder.py --query '{\"task_id\":\"smoke\",\"plan\":{\"goal\":\"noop\"},\"workspace_dir\":\"\"}' --dry-run"
```

## Out of scope (still deferred)

- Refactoring planner-specialist / reviewer-specialist to use the same deterministic-envelope pattern. They have not failed yet.
- Replacing `_extract_json` with a real balanced-brace JSON parser. Fence-strip + brace-match suffices for current specialists.
- aider model swap or prompt tuning — bug was envelope assembly, not aider's code output.
