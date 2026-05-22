---
phase: "04-build-fix-pipeline"
plan: "04-04"
status: "complete"
date: "2026-05-22"
---

# 04-04 — Workshop specialist model matrix (NIM upgrade) — SUMMARY

## What shipped

Per-specialist model routing matrix is now wired end-to-end in the repo:

| Specialist            | Slot                  | Model alias                            | Resolution mechanism                |
|-----------------------|-----------------------|----------------------------------------|-------------------------------------|
| triage-specialist     | Hermes skill          | `private-worker` (no change)           | `specialist-home-private/config.yaml` |
| planner-specialist    | Hermes skill          | **`orchestrator`** (NIM DSv4 Pro)      | `specialist-home-orchestrator/config.yaml` |
| coder-specialist (orchestration) | Hermes skill | `private-worker` (no change)         | `specialist-home-private/config.yaml` |
| coder/architect       | Aider `--model`       | **`openai/orchestrator`** (NIM DSv4 Pro)| `hermes-skills/aider_runner.py:97`  |
| coder/editor          | Aider `--editor-model`| `openai/private-worker` (no change)    | `hermes-skills/aider_runner.py:98`  |
| reviewer-specialist   | Hermes skill          | **`research-worker`** (NIM DSv4 Flash) | `specialist-home-research/config.yaml` |

`workshop/orchestrator.py:_extract_json` now strips `<think>...</think>`
reasoning prologues defensively, so NIM thinking-mode brace leaks no
longer fool the brace-matcher.

## Commits

- `feat(04-04): route aider architect to openai/orchestrator (NIM DeepSeek V4 Pro)` — Task 1
- `feat(04-04): strip <think>…</think> blocks in _extract_json` — Task 2
- `feat(04-04): per-skill HERMES_HOME routing for model matrix` — Tasks 4 + 6

## Verification

### Unit tests (pytest)

```
$ python3 -m pytest tests/phase-04/test_orchestrator.py -q
............                                                             [100%]
12 passed in 0.06s
```

New tests added:
- `test_extract_json_strips_think_block` (single-line)
- `test_extract_json_strips_multiline_think_block`
- `test_extract_json_strips_think_block_case_insensitive`

### Smoke tests (bats — local, no VPS needed)

```
$ bats tests/phase-04/model-matrix-smoke.bats
1..6
ok 1 triage-specialist resolves to MAX_TURNS=3 and specialist-home-private
ok 2 planner-specialist resolves to MAX_TURNS=8 and specialist-home-orchestrator
ok 3 reviewer-specialist resolves to MAX_TURNS=10 and specialist-home-research
ok 4 coder-specialist resolves to MAX_TURNS=15 and specialist-home-private
ok 5 unknown specialist falls back to MAX_TURNS=8 and specialist-home-private
ok 6 MAX_TURNS env override still resolves correct HERMES_HOME
```

### Static checks

- `grep -n "cloud-sonnet" hermes-skills/aider_runner.py` → no architect references remain (only mentions are docstring/log strings referring to the proxy failover path; the active `--model` arg is `openai/orchestrator`).
- `bash -n scripts/hermes-skill-run.sh` → clean.
- `.planning/PROJECT.md` L25 and V17 already rewritten in commit `90b74fb` (this plan's import commit); confirmed in-place.

## Tasks completed in-tree

- **Task 1** — `hermes-skills/aider_runner.py` architect model swapped to `openai/orchestrator`; doc/log strings updated.
- **Task 2** — `workshop/orchestrator.py:_extract_json` strips `<think>…</think>`; 3 unit tests added.
- **Task 4** — `scripts/hermes-skill-run.sh` per-skill `MAX_TURNS` *and* `HOME_DIR` case implemented; dry-run output now reports `HERMES_HOME`; `SPECIALIST_HOME_OVERRIDE` env hook for ad-hoc overrides.
- **Task 5** — PROJECT.md L25/V17 already updated in the plan import commit.
- **Task 6** — `tests/phase-04/model-matrix-smoke.bats` (6 tests).

## Deferred to operator (out-of-band, side-effects on live VPS / Brain)

### Task 3 — Create per-specialist `HERMES_HOME` directories on VPS

Three home dirs need to exist on `31.97.130.253` with model-default
overrides:

```bash
ssh root@31.97.130.253 bash <<'EOF'
set -euxo pipefail
SRC=/opt/ultra-workshop/specialist-home
for tier in private orchestrator research; do
  DST="/opt/ultra-workshop/specialist-home-${tier}"
  if [ ! -d "$DST" ]; then
    cp -a "$SRC" "$DST"
    chown -R uws:uws "$DST"
  fi
done

# Patch each config.yaml default model alias.
python3 - <<'PY'
import re, pathlib
matrix = {
    "specialist-home-private":      "private-worker",
    "specialist-home-orchestrator": "orchestrator",
    "specialist-home-research":     "research-worker",
}
for home, model in matrix.items():
    cfg = pathlib.Path(f"/opt/ultra-workshop/{home}/config.yaml")
    text = cfg.read_text()
    # Replace the first `default:` line under a `model:` block.
    new = re.sub(r"(^\s*default:\s*).*$", rf"\1{model}", text, count=1, flags=re.MULTILINE)
    if new == text:
        # Append a model block if missing.
        new = text + f"\nmodel:\n  default: {model}\n"
    cfg.write_text(new)
    print(f"{cfg} → default: {model}")
PY

# Verify.
cat /opt/ultra-workshop/specialist-home-*/config.yaml | grep -E "default:"
EOF
```

Then re-deploy the updated `hermes-skill-run.sh`:

```bash
rsync -avz scripts/hermes-skill-run.sh root@31.97.130.253:/opt/ultra-workshop/scripts/
```

### Task 7 — Live VPS build verification

Run from Telegram against `test-workshop-sandbox`:

```
/build add /tmp/marker.txt
```

Tail Hermes gateway logs and confirm:

1. Planner call resolves to `orchestrator` (NIM DSv4 Pro).
2. Reviewer call resolves to `research-worker` (NIM DSv4 Flash).
3. Aider architect hits `openai/orchestrator`; editor hits `openai/private-worker`.
4. Latencies fit inside the LiteLLM proxy `timeout: 300`.
5. All `Plan` / `Review` blobs `model_validate_json()` cleanly (no `_extract_json` retries — the `<think>` strip should make this a no-op).

### Task 8 — ADR write-back via Brain

Use Brain's `manage_adr` to record:

```yaml
title: "Workshop specialist model matrix — NIM upgrade"
status: Accepted
context: |
  Brain now exposes a 5-tier LiteLLM proxy with NIM DeepSeek V4 Pro
  (`orchestrator`) and Flash (`research-worker`) aliases. Workshop's
  planner, reviewer, and Aider architect were reasoning-bound; lifting
  them to NIM thinking-mode is the clear quality lever. Editor slot
  (highest token volume) must stay on `private-worker` to honor V17
  (≥80% local token volume).
decision: |
  Per-specialist routing:
    - triage / coder-orchestration / coder-editor → private-worker (local)
    - planner / coder-architect                   → orchestrator (NIM DSv4 Pro, thinking on)
    - reviewer                                    → research-worker (NIM DSv4 Flash, thinking on, 1M ctx)
  Hermes v0.14.0 has no `--model` flag for `chat`, so per-skill routing is
  implemented as separate HERMES_HOME directories (one per alias) selected
  by hermes-skill-run.sh.
consequences:
  - Per-build cost ceiling ~$2 (validate via Brain cost-ledger after 5 builds).
  - L25 rewritten in PROJECT.md; V17 retained with empirical-verification clause.
  - First-build cost spike acceptable: NIM cold/throttle path falls back to
    cloud-sonnet (architect) and cloud-groq (default-worker) via the proxy.
  - DeepSeek thinking-mode cold-start latency 30–60s observed; 90s+ harness
    timeout already in place.
related_obs:
  - 21811  # 90s timeout adopted
  - 21824  # token volume / cost constraints
```

## Cost validation (operator, after first 5 builds)

```
ssh root@31.97.130.253 'grep "source: workshop" /srv/second-brain/_system/cost-ledger.md | tail -20'
```

Confirm per-build cost ≤ $2 and editor token share ≥ 80%. If editor share
drops, file follow-up to move editor to `default-worker` (Gemma → Llama 3.3
70B fallback) or hold the line.

## Risks acknowledged (carried from plan)

- NIM rate limit (40 RPM) — interactive traffic nowhere near.
- DeepSeek thinking-mode cold-start latency — 90s+ timeout already adopted.
- `<think>` JSON leak — defensive strip in place.
- Per-home disk usage — 3× config-only homes, negligible.
- First-build cost spike — automatic proxy fallback within $2 ceiling.

## Rollback

- `aider_runner.py:97` → `openai/cloud-sonnet`
- `hermes-skill-run.sh` → reset all `HOME_DIR` to `specialist-home-private`
- `_extract_json` `<think>` strip stays (defensive, no downside)
- `PROJECT.md` L25 reverts to "interactive → private-worker"

No data migration, no proxy-config changes.
