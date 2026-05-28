# Plan — async /build & /fix via background terminal

## Context

Hermes' foreground `terminal()` tool hard-caps at **600 seconds**. The workshop pipeline (triage → planner → coder → reviewer + HITL) typically runs 12–20 minutes on a cold NIM cache. Today's `skills/workshop-build/SKILL.md` calls `terminal(..., timeout=1800)`, which Hermes now actively refuses:

> "the specified timeout (1800 seconds) exceeds the hard limit set by the terminal tool's foreground timeout capability (maximum of 600 seconds). To allow for a longer-running process like this, we must change the execution pattern from a synchronous, foreground call to an asynchronous background job using `background=true` and `notify_on_complete=true`."

The fix is to run `workshop_build.py` and `workshop_fix.py` as background jobs. When the subprocess finishes, Hermes fires a completion notification → a fresh agent turn opens in the same chat session with the captured stdout + exit code, and the SKILL.md branches accordingly to drive the HITL clarify gate and the push step.

**Intended outcome:** `/build <task>` and `/fix <issue-url>` complete end-to-end in Telegram, with no 600-second wall, no false-failure timeouts, and a per-stage progress trail.

---

## Design (Option A + Progress prints)

- **Minimal SKILL.md change** — `workshop_build.py` and `workshop_fix.py` stay as the brains. They already print the HITL JSON envelope and exit 2. The SKILL.md body just switches its single `terminal(...)` call to background mode and adds an explicit branch for "this turn is a notification result".
- **Belt-and-suspenders progress prints** in `workshop_build.py` and `workshop_fix.py` — one `print(f"[workshop] {stage} done", flush=True)` next to each existing `append_progress(task_id, "<stage>", ...)` call. Cost: ~6 lines per script. Benefit: the user sees concrete progress in Telegram even if Hermes' streamer drops out for background jobs.
- **Push step stays foreground** — `workshop_push.py` is normally <30s; no need to background it.

---

## Files to modify

| File | Change |
|------|--------|
| `skills/workshop-build/SKILL.md` | Replace step 4's `terminal(..., timeout=1800)` with `terminal(..., background=true, notify_on_complete=true)`. Add an explicit "first turn vs notification turn" branch in the Behavior section. Send a one-line acknowledgment after firing background job. |
| `skills/workshop-fix/SKILL.md` | Same shape of change as `workshop-build`. |
| `hermes-skills/workshop_build.py` | Insert `print(f"[workshop] {stage} done", flush=True)` next to each `append_progress(...)` line (lines 50, 60, 73, 80 in current file). |
| `hermes-skills/workshop_fix.py` | Same as `workshop_build.py` — one progress print per ledger checkpoint. |
| `tests/phase-04/build-smoke.bats` / `fix-smoke.bats` | If they assert on stdout shape, update assertions to allow the new `[workshop] <stage> done` lines (likely a non-issue since dry-run path is unaffected). |
| `workshop/orchestrator.py` | **No change** — per-specialist timeout already bumped to 600s in the previous commit. |

---

## SKILL.md instruction shape (single body, branches on turn type)

```
1. If the current trigger is `/build <task>`:
   - Extract task from trigger
   - Run: terminal(command="python3 /opt/ultra-workshop/hermes-skills/workshop_build.py --task \"<task>\" ...",
                   background=true, notify_on_complete=true)
   - Reply: "🔧 Workshop pipeline started in background. I'll ping you when it's ready for approval."
   - End turn.

2. If the current turn is a notification of background job completion:
   - Read the terminal result's exit code + stdout (last line is JSON if exit 2).
   - exit 0 → unexpected; log and report stdout.
   - exit 1 → report failure with last 500 chars of stderr.
   - exit 2 → parse JSON; call `clarify` with `summary`. On approve, run
     `terminal(command="python3 /opt/ultra-workshop/hermes-skills/workshop_push.py ...")`
     in FOREGROUND (no background flag — push is fast).
     On reject, reply "PR creation rejected for task `<task_id>`."
```

Same shape for `workshop-fix/SKILL.md` (different command path).

---

## Reused existing code (no new helpers needed)

- `workshop_build.py:88-94` (HITL exit-2 JSON envelope) — unchanged contract.
- `workshop_build.py: append_progress(task_id, "<stage>", ...)` calls — already exist; we just print alongside.
- `hermes-skills/workshop_push.py` — unchanged.
- `workshop/orchestrator.run_specialist` — unchanged (600s per specialist already in place).

---

## Deploy

```bash
# After local commit
scp skills/workshop-build/SKILL.md root@31.97.130.253:/home/uws/.hermes/skills/workshop-build/SKILL.md
scp skills/workshop-fix/SKILL.md   root@31.97.130.253:/home/uws/.hermes/skills/workshop-fix/SKILL.md
scp hermes-skills/workshop_build.py root@31.97.130.253:/opt/ultra-workshop/hermes-skills/workshop_build.py
scp hermes-skills/workshop_fix.py   root@31.97.130.253:/opt/ultra-workshop/hermes-skills/workshop_fix.py
ssh root@31.97.130.253 'chown uws:uws /home/uws/.hermes/skills/workshop-{build,fix}/SKILL.md /opt/ultra-workshop/hermes-skills/workshop_{build,fix}.py'
```

No gateway restart needed (SKILL.md is re-read per invocation; Python scripts are subprocess-loaded).

---

## Verification

### Local
- `python3 -m pytest tests/phase-04/ -q` — 21 tests should still pass.
- `bats tests/phase-04/model-matrix-smoke.bats tests/phase-04/build-smoke.bats tests/phase-04/fix-smoke.bats` — all green.

### Live in Telegram (the actual proof)
1. Send `/build add a fibonacci(n) function to utils.py with a docstring and a basic test` to `@ultra_workshop_bot`.
2. Within a few seconds: expect `"🔧 Workshop pipeline started in background. I'll ping you when it's ready for approval."`
3. Over the next 10–20 min: expect progress lines `[workshop] triage_complete done`, `[workshop] plan_complete done`, `[workshop] coder_complete done`, `[workshop] review_complete done` (visible if Hermes streamer carries through; otherwise silent until completion).
4. When the pipeline reaches HITL: expect a Telegram clarify prompt `"Review passed. Push branch 'workshop/ws-XXXX' and open PR for: ..."` with yes/no inline buttons.
5. Reply yes → expect within ~30s a PR URL in the chat.
6. Repeat with `/fix https://github.com/caiobellizzi/test-workshop-sandbox/issues/2`.

### Forensic checks if something stalls
- `ssh root@31.97.130.253 'docker logs --since 10m ad801e889f7d | grep -E "ERROR|chat/completions" | tail -50'`
- `ssh root@31.97.130.253 'ls -ltr /opt/ultra-workshop/specialist-home-*/sessions | tail -10'`

---

## Out of scope (deferred)

- A `/status <task_id>` command to inspect mid-run state. Useful but additive — file when the basic flow proves out.
- Concurrent-run isolation (multiple /build at once). Already works because Hermes binds clarify to specific messages and `task_id` is generated per run, but not validated under load.
- workshop_build.py talking to Telegram directly (Option B from grilling) — explicitly rejected as scope creep.
