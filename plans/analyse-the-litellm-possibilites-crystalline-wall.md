# LiteLLM model matrix — NVIDIA NIM upgrade for Workshop specialists

## Context

The ultra-agents-brain project just shipped a 5-tier LiteLLM proxy
(`/opt/ultra-agents-brain/deploy/litellm/config.yaml`) that exposes NVIDIA NIM
models alongside the existing local Gemma and cloud fallbacks:

- `orchestrator` → NIM DeepSeek V4 Pro (thinking on) → failover GLM-5.1 → cloud-sonnet
- `research-worker` → NIM DeepSeek V4 Flash (1M ctx, thinking on) → Qwen 3.5 397B → cloud-sonnet
- `default-worker` → local Gemma → NIM Llama 3.3 70B → Mistral Large → cloud-groq
- `cheap-worker` & `private-worker` → local Gemma (local-only by contract)

ultra-workshop is still routing 100% of interactive `/build` and `/fix`
specialist traffic through `private-worker` per L25/V17. The goal of this
change is to **lift reasoning quality on the planner, reviewer, and Aider
architect** by routing them to NIM thinking-mode models, while keeping the
high-token-volume Aider editor on `private-worker` so V17 (≥80% local token
volume) still holds in spirit. We accept up to ~$2/build cost ceiling
(decision (c) from the grilling session) — meaningful cloud fallback spend is
allowed when NIM throttles or fails.

This change overrides the locked decisions L25 ("interactive → private-worker")
and partially updates V17. Both get rewritten in `PROJECT.md`.

## Decision matrix (locked via grill session)

| Specialist | Slot | Model alias | Rationale |
|---|---|---|---|
| triage-specialist | Hermes skill | `private-worker` (no change) | Classification, max-turns 3, tiny token count. Thinking model adds latency without quality gain. |
| planner-specialist | Hermes skill | **`orchestrator`** (was `private-worker`) | Reasoning-bound; NIM DeepSeek V4 Pro thinking-mode is the clear quality lever. |
| coder-specialist (orchestration) | Hermes skill | `private-worker` (no change) | Just orchestrates aider_runner.py — doesn't need a smart model. |
| coder/architect | Aider `--model` | **`orchestrator`** (was `cloud-sonnet`) | Lifts architect from Sonnet to NIM DeepSeek V4 Pro thinking. Sonnet remains as proxy-level failover. |
| coder/editor | Aider `--editor-model` | `private-worker` (no change) | Highest token volume in system; staying local honors V17. Editor must NOT be a thinking model (would break SEARCH/REPLACE parsing). |
| reviewer-specialist | Hermes skill | **`research-worker`** (was `private-worker`) | Diff vs. Plan judgment; 1M ctx swallows large diffs, Flash thinking-mode is right-sized for verification. |

## Files to modify

### 1. `hermes-skills/aider_runner.py` (architect upgrade)

- Line 97: `"--model", "openai/cloud-sonnet"` → `"--model", "openai/orchestrator"`
- Line 5 docstring: update "Architect model: openai/cloud-sonnet" → "openai/orchestrator (NIM DeepSeek V4 Pro, thinking on; cloud-sonnet via proxy failover)"
- Lines 19, 138, 146: update model-name strings in comments / log line (`cloud-sonnet+private-worker` → `orchestrator+private-worker`)

Editor model and all other arguments stay unchanged.

### 2. `workshop/orchestrator.py` (defensive `<think>` stripping)

Augment `_extract_json` to strip `<think>...</think>` blocks before
brace-matching. Thinking-mode models emit reasoning blocks before final JSON;
brace-matching *should* survive but this is a 5-line defensive change that
eliminates a whole risk class.

```python
import re

_THINK_RE = re.compile(r"<think\b[^>]*>.*?</think>", re.DOTALL | re.IGNORECASE)

def _extract_json(text: str) -> str:
    text = _THINK_RE.sub("", text)
    # ...existing brace-matching logic
```

Add a unit test in `tests/` that feeds `<think>reasoning</think>{"k":"v"}` and
asserts `{"k":"v"}` is extracted cleanly.

### 3. Per-specialist `HERMES_HOME` directories (production wiring)

Hermes v0.14.0's `chat` subcommand has no `--model` flag. Model defaults live
in `~/.hermes/config.yaml`. We already use an isolated
`/opt/ultra-workshop/specialist-home/` for specialist subprocess calls. Expand
to three homes — one per default-model setting:

- `/opt/ultra-workshop/specialist-home-private/` — `model.default: private-worker` (used by triage, coder orchestration)
- `/opt/ultra-workshop/specialist-home-orchestrator/` — `model.default: orchestrator` (used by planner)
- `/opt/ultra-workshop/specialist-home-research/` — `model.default: research-worker` (used by reviewer)

Each home is a copy of the current `specialist-home/` with only `config.yaml`
differing. Deploy via the existing rsync pipeline.

### 4. `scripts/hermes-skill-run.sh` (per-specialist home selection)

Extend the existing per-skill `MAX_TURNS` case statement to also set
`SPECIALIST_HOME` per skill:

```bash
case "$SKILL" in
  triage-specialist)   MAX_TURNS=3;  HOME_DIR=specialist-home-private ;;
  planner-specialist)  MAX_TURNS=8;  HOME_DIR=specialist-home-orchestrator ;;
  reviewer-specialist) MAX_TURNS=10; HOME_DIR=specialist-home-research ;;
  coder-specialist)    MAX_TURNS=15; HOME_DIR=specialist-home-private ;;
  *)                   MAX_TURNS=8;  HOME_DIR=specialist-home-private ;;
esac
SPECIALIST_HOME="/opt/ultra-workshop/${HOME_DIR}"
```

Existing `HERMES_HOME="$SPECIALIST_HOME"` injection lines unchanged.

**Fallback if per-home approach hits problems:** investigate Hermes config
`${VAR}` interpolation. If `default: "${HERMES_DEFAULT_MODEL:-private-worker}"`
expands at startup, a single home with env-var override per invocation is
simpler. Treat as Phase-2 simplification, not Phase-1 blocker.

### 5. `.planning/PROJECT.md` (decision updates)

- **L25**: Rewrite from "Interactive `/build`/`/fix` → `private-worker`" to:
  "Interactive `/build`/`/fix` uses a per-specialist model matrix: triage +
  coder/editor on `private-worker`, planner + coder/architect on `orchestrator`
  (NIM DeepSeek V4 Pro thinking), reviewer on `research-worker` (NIM DeepSeek
  V4 Flash thinking). Cron remains `cloud-groq` directly."
- **V17**: Keep "Local model must handle ≥80% of token volume" — the editor
  (highest-volume slot) stays local, so this still holds. Add a note: "Verify
  empirically via cost-ledger entries after first 5 builds; tighten or relax
  the 80% target based on observed economics."
- **L26**: `private-worker` 30s timeout unchanged — only the per-specialist
  default-alias setting moves.

### 6. ADR write-back (after first successful build)

Use Brain's `manage_adr` to record this matrix change as ADR-0XXX with:
- Title: "Workshop specialist model matrix — NIM upgrade"
- Decision: per-specialist routing table from §Decision Matrix
- Consequences: cost ceiling raised to ~$2/build, V17 retained, L25 rewritten
- Status: Accepted (once smoke tests pass)

## Verification

### Smoke tests (run before declaring done)

1. **Unit**: new test in `tests/test_orchestrator.py` asserts `_extract_json`
   strips `<think>...</think>` and preserves the trailing JSON. Run with
   `pytest tests/test_orchestrator.py -v`.
2. **Dry-run pipeline**: invoke each specialist with `--dry-run`:
   ```
   hermes-skill-run.sh triage-specialist  --dry-run "add hello.txt"
   hermes-skill-run.sh planner-specialist --dry-run "add hello.txt"
   hermes-skill-run.sh reviewer-specialist --dry-run "noop"
   ```
   Each should report the matching `MAX_TURNS` and `HERMES_HOME` for its
   slot. Add this to bats smoke tests in `tests/smoke/`.
3. **Live VPS build** (the real proof): trigger `/build add /tmp/marker.txt`
   in Telegram against the test-workshop-sandbox repo.
   - Watch Hermes gateway logs: planner call should target NIM (`orchestrator`
     alias resolves to DeepSeek V4 Pro). Reviewer call should target NIM
     (`research-worker` alias resolves to DeepSeek V4 Flash). Aider architect
     call should hit `openai/orchestrator`, editor call should hit
     `openai/private-worker`.
   - Capture latencies — confirm DeepSeek thinking cold-start fits within
     `timeout: 300` set in the proxy config.
4. **JSON robustness**: review `state.db` events for the same build — every
   `Plan` and `Review` blob must `model_validate_json()` cleanly. No
   `_extract_json` retries, no validation errors.

### Cost validation (after first 5 builds)

- Query Brain cost ledger: `/srv/second-brain/_system/cost-ledger.md`,
  `source: workshop` entries.
- Confirm per-build cost ≤ $2 (ceiling (c)).
- Confirm editor token share ≥ 80% of build total (V17). If editor share
  drops below 80%, file follow-up to consider moving editor to
  `default-worker` (Gemma → Llama 3.3 70B fallback) or hold the line.

### Rollback path

If quality regresses or costs blow up, revert is one-line per file:
- `aider_runner.py:97` → `openai/cloud-sonnet`
- `hermes-skill-run.sh` → reset all `HOME_DIR` to `specialist-home-private`
- `_extract_json` `<think>` strip stays (defensive, no downside)
- `PROJECT.md` L25 reverts to "interactive → private-worker"

No data migration; no proxy-config changes (proxy stays as Brain shipped it).

## Risks acknowledged

- **NIM rate limit (40 RPM)**: interactive `/build`/`/fix` traffic is nowhere
  near this. Cron jobs already route via `cloud-groq` per L25. No mitigation
  needed.
- **DeepSeek thinking-mode latency**: 30–60s cold-start observed previously
  (claude-mem obs 21811). 90s+ harness timeout already adopted. Acceptable.
- **`<think>` token leak into JSON**: mitigated by (b) defensive strip in
  `_extract_json`. Falls back to brace-matching as before for non-leak case.
- **Per-home disk usage**: 3× the specialist-home directory. Marginal — these
  are config-only homes, no model weights.
- **First-build cost spike if NIM cold/throttled**: fallback to cloud-sonnet
  (architect) and cloud-groq (default-worker) is automatic via proxy. Ceiling
  (c) accepts this.

## Critical files (cheat sheet)

- `hermes-skills/aider_runner.py:97` — architect model
- `workshop/orchestrator.py:_extract_json` — JSON parse hardening
- `scripts/hermes-skill-run.sh` — per-skill `HERMES_HOME` routing
- `.planning/PROJECT.md` L25/V17 — locked-decision rewrites
- `/opt/ultra-workshop/specialist-home-*/config.yaml` (VPS) — per-home model defaults
- `/opt/ultra-agents-brain/deploy/litellm/config.yaml` (Brain VPS) — proxy aliases (no changes; Brain owns this)
