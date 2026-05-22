---
phase: "04-build-fix-pipeline"
plan: "04-05"
status: completed
completed_at: 2026-05-22
---

# Plan 04-05 — Async /build & /fix via background terminal — SUMMARY

## What changed

Hermes' foreground `terminal()` tool hard-caps at 600s, but the workshop
pipeline (triage → planner → coder → reviewer + HITL) runs 12–20 min on
a cold NIM cache. Switched `/build` and `/fix` to async background jobs
so completion fires a fresh agent turn carrying the captured exit code +
stdout, which then drives the HITL clarify gate.

## Files modified

| File | Change |
|------|--------|
| `skills/workshop-build/SKILL.md` | Replaced `terminal(..., timeout=1800)` with `terminal(..., background=true, notify_on_complete=true)`. Restructured Behavior into "A. Initial /build turn" (fire-and-ack) and "B. Notification turn" (branch on exit code → HITL clarify → foreground push). |
| `skills/workshop-fix/SKILL.md` | Same shape of change; mirrors workshop-build. |
| `hermes-skills/workshop_build.py` | Added `print("[workshop] <stage> done", flush=True)` next to each `append_progress(...)` call (triage_complete, plan_complete, coder_complete, review_complete). |
| `hermes-skills/workshop_fix.py` | No change — has no `append_progress` calls (delegates to workshop_build.py and inherits stdout). |
| `tests/phase-04/build-smoke.bats` / `fix-smoke.bats` | No change — dry-run path is unaffected and tests don't pin stdout shape. |
| `workshop/orchestrator.py` | No change — 600s per-specialist timeout already in place from 04-04. |

## Verification

- `python3 -m pytest tests/phase-04/ -q` → **21 passed**
- `bats tests/phase-04/build-smoke.bats tests/phase-04/fix-smoke.bats` → **5/5 ok**
- Deployed to VPS `31.97.130.253`:
  - `/home/uws/.hermes/skills/workshop-{build,fix}/SKILL.md`
  - `/opt/ultra-workshop/hermes-skills/workshop_build.py`
  - chown'd to `uws:uws`, no gateway restart required (SKILL.md re-read per invocation; Python is subprocess-loaded)

## Remaining (human UAT)

Live Telegram verification per plan §Verification:

1. Send `/build add a fibonacci(n) function to utils.py with a docstring and a basic test` to `@ultra_workshop_bot`.
2. Expect within ~seconds: `"🔧 Workshop pipeline started in background. I'll ping you when it's ready for approval."`
3. Over the next 10–20 min: expect `[workshop] triage_complete done`, `plan_complete done`, `coder_complete done`, `review_complete done` progress lines.
4. On HITL: expect Telegram clarify with yes/no inline buttons.
5. Reply yes → PR URL within ~30s.
6. Repeat with `/fix https://github.com/caiobellizzi/test-workshop-sandbox/issues/2`.

Forensic checks if it stalls:
- `ssh root@31.97.130.253 'docker logs --since 10m ad801e889f7d | grep -E "ERROR|chat/completions" | tail -50'`
- `ssh root@31.97.130.253 'ls -ltr /opt/ultra-workshop/specialist-home-*/sessions | tail -10'`

## Out of scope (deferred, unchanged from plan)

- `/status <task_id>` mid-run inspection command.
- Concurrent-run isolation (multiple /build at once).
- workshop_build.py talking to Telegram directly (Option B from grilling).
