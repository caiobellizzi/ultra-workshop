# Fix: Autonomous one-submission builds of complex production PRDs

## Context

A task (`ws-ai-briefing-0526a`) reached `needs_timeout_recovery`: the planner produced **8 steps**, but the coder **ignored the steps**, fired a **single Aider `--architect` invocation** over all `affected_files`, routed it to a **~4B local model (`gemma-4-e4b`)** with `--no-stream`, and sat blind inside the model call until the **900s wall-clock** hard-killed it — producing zero edits.

The goal is to build complex, production-ready PRDs from **one submission, walking away** while the system builds autonomously. Three things currently fight that goal:

1. The plan's step decomposition is discarded at execution time (one giant coder run instead of a loop).
2. The coder model is a zero-cost v1 placeholder (`gemma-4-e4b`) far too weak for production work, with no per-stage routing.
3. The timeout is a blind wall clock — it cannot tell a hung model from a working one.

### Decisions (from grilling)

| # | Decision |
|---|----------|
| 1 | **"One shot" = one submission, many internal autonomous steps.** No literal single-call constraint. |
| 2 | **Per-stage model map. NVIDIA NIM primary; Anthropic/OpenAI fallback only.** Stop hardcoding the model in `aider_runner.py`. |
| 3 | **Step-by-step execution loop:** one `PlanStep` = one coder run = one commit, in plan order. |
| 4 | **Verify cadence:** build/test gate **per step** (retry on fail); full **LLM review once at the end** (+ on build failure), with a fix loop. |
| 5 | **Auto-recovery:** per step → bounded retry w/ feedback → **one** auto-decompose into sub-steps → HITL. Hard caps preserve boundedness. |
| 6 | **Timeout:** idle watchdog (streaming; kill on no-output-for-N) + tight per-model litellm `request_timeout` with fast cloud fallback. Drop `--no-stream`. |
| 7 | **Coder runs a single model per step** (drop `--architect` for execution; planner already did the reasoning). |
| 8 | **Planner contract:** many small, ordered, independently-testable slices. Remove the 2–5 / 6-file caps. One global cap (≤~20 steps + total wall-clock budget) → HITL if exceeded. |

---

## Implementation

### A. Per-stage model map + NVIDIA NIM provider

**`deploy/litellm/config.yaml`** — add NIM as primary provider and define per-stage aliases with cloud fallbacks:
- Provider: `api_base: https://integrate.api.nvidia.com/v1`, key from env `NVIDIA_API_KEY`.
- Aliases (NIM primary → Anthropic/OpenAI fallback):
  - `planner-reasoner` → NIM frontier reasoner (DeepSeek-R1-class) → fallback `cloud-sonnet`.
  - `coder-worker` → NIM strong coder (Qwen-Coder / DeepSeek-V3-class) → fallback `cloud-sonnet`.
  - `reviewer-model` → NIM strong model → fallback `cloud-sonnet`.
  - `cheap-fast` → small NIM model for triage/requirements → fallback existing cheap alias.
- Set **tight per-model `request_timeout`** (e.g. 90–120s) and `max_retries: 1` so a hung NIM call fails over to the cloud fallback quickly (the prior 300s×2 budget was a root cause).
- **Confirm exact NIM model IDs against the live build.nvidia.com catalog at implementation time** (version-sensitive — do not guess). Verify each chosen model is reliable at Aider's edit/diff format before locking it in.

**`hermes-skills/aider_runner.py`** (`_build_aider_argv`) — stop hardcoding `--model openai/orchestrator --editor-model openai/private-worker --architect`. Accept the model alias as a parameter and emit a **single `--model <alias>`** (no `--editor-model`, no `--architect`). Remove `--no-stream` (see C).

**`workshop/stage_policy.py`** / coder payload — carry the per-stage model alias so each stage's specialist passes the right alias down to Aider. Triage/requirements → `cheap-fast`; planner → `planner-reasoner`; coder → `coder-worker`; reviewer → `reviewer-model`.

### B. Step-by-step execution loop

**`hermes-skills/workshop_coder.py`** — replace the single-invocation body (the current `affected = plan["affected_files"]` → one `_run_aider_runner` call) with a **loop over `plan["steps"]`**:
- For each `PlanStep` in order: build the Aider `--message` from that step's `description`, pass **only that step's `files`** as targets, run one single-model Aider call.
- After each step: run the **build/test gate** (reuse the existing build/test command logic already invoked for the coder). On failure → retry the step with the failure output fed back into the message (bounded, e.g. 2x), mirroring the existing reviewer-feedback injection in `_build_aider_task`.
- On success → **commit the step** (one commit per step) on the `workshop/<task_id>` branch. Do **not** force-reset the branch between steps (current retry logic resets to `default_branch`; that must only happen at task start, not per step — preserve prior steps' commits).
- Persist a **step cursor** to state after each commit (see D) for mid-plan resume.

**End-of-plan review:** after all steps commit, `workshop_build.py` runs the reviewer once over the whole diff (existing reviewer call). Blocking issues → a **fix run** (single-model coder run targeting the reviewer-named files), then re-review, bounded by the existing `max_review_attempts` (`workshop_build.py`). This reuses the current review→coder loop, just moved to run *after* the step loop instead of around a single coder call.

### C. Idle watchdog timeout

**`hermes-skills/workshop_coder.py`** (`_run_aider_runner`) — replace `process.communicate(timeout=...)` with incremental reads:
- Drop `--no-stream` in `aider_runner.py` so Aider emits tokens as they arrive.
- Read stdout/stderr in a loop; track `last_output_at`. Kill the process group if `now - last_output_at > IDLE_TIMEOUT` (e.g. 120s, env-configurable) — **not** a fixed wall clock.
- Keep a generous absolute ceiling as a backstop and a **total per-task wall-clock budget** (decision 5/8) checked in the `workshop_build.py` loop.
- Keep the existing SIGTERM→SIGKILL process-group teardown (`_terminate_process_group`).

### D. Auto-recovery + bounded HITL

**`hermes-skills/workshop_build.py`** — the per-step failure ladder (after B's in-step retries are exhausted):
1. **Auto-decompose once:** ask the planner (`planner-reasoner`) to split the failing step into smaller sub-steps; run them through the same loop. Track a `decompose_depth` (max 1) per step in state.
2. If still failing, or any **hard cap** trips (global step count ≤~20, total wall-clock budget, decompose depth) → escalate via the existing `StageTimeoutForHITL` / Telegram path. Update the recovery payload options to reflect step-level context.

**`workshop/stage_policy.py`** — coder keeps `hitl_on_timeout` semantics, but a single in-step timeout now triggers **in-loop recovery first**, not immediate HITL. Adjust so the immediate-escalate behavior only fires after the recovery ladder is exhausted.

### E. Planner contract

**`skills/planner-specialist/SKILL.md`** — replace "2–5 steps" with: emit **as many small, ordered, independently build/testable steps as the PRD needs**, each touching a minimal coherent file set, ordered by dependency. State the global cap (≤~20 steps) and that exceeding it should surface a "PRD too large — split it" signal.

**`workshop/planner.py`** — remove the `[:6]` `affected_files` cap (`infer_affected_files` / `build_plan`); per-step `files` are the unit now. Keep `affected_files` as the union for sanitization/gating only.

**`workshop/types.py`** — `PlanStep` (`id`, `description`, `files`) is sufficient for ordered execution; no schema change required. (Steps execute in list order — no explicit dependency graph needed for v1.)

### F. State + resume

**`workshop/state.py`** — add a `current_step` cursor (and `decompose_depth` per step) to `new_task_state()`. Save after each committed step so `--resume` continues mid-plan from the next uncommitted step rather than restarting the coder.

**`workshop/orchestrator.py`** — `run_specialist` wall-clock (`timeout=960` for coder) must accommodate the multi-step loop; let per-step idle timeout + total-task budget govern instead of a single coarse coder timeout.

---

## Verification

1. **Unit / existing suites:** `pytest` (45) + bats (14) stay green; update coder tests in `tests/phase-06/test_aider_runner.py` for the new single-model argv and step loop.
2. **Model routing (local):** dry-run the pipeline (`hermes-skill-run.sh ... [dry-run]`) and assert each stage emits its correct litellm alias; assert `aider_runner.py` argv has a single `--model`, no `--architect`, no `--no-stream`.
3. **Idle watchdog (local):** point the coder at a deliberately hung/slow mock model endpoint; confirm it kills on the idle window (~120s) and fails over to cloud, not the old 900s wall clock.
4. **Step loop (local):** feed a 3-step plan; confirm 3 commits on `workshop/<task_id>`, build/test gate runs per step, prior steps survive a later step's retry (no branch reset mid-plan).
5. **Auto-recovery (local):** force a step's build to fail; confirm bounded retry → one auto-decompose → HITL escalation, and that global caps trip correctly.
6. **Live VPS smoke (NIM):** re-run `ws-ai-briefing`-style complex PRD end-to-end with NIM primary; confirm it builds multiple commits unattended, end-review passes, and Telegram is only hit on genuine cap/exhaustion.

## Open items to confirm at implementation
- Exact NVIDIA NIM model IDs (reasoner / coder / small) from the live catalog + their Aider edit-format reliability — verify via Context7/NIM docs, do not guess into config.
- `NVIDIA_API_KEY` provisioning on the VPS env.
- Concrete numeric caps (idle window, max steps, total wall-clock budget) — start with the suggested defaults, tune after the first live run.
