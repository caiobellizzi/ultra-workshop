# Fix: DeepSeek Thinking Tokens Corrupting Aider File Paths

## Context

Build `ws-ai-briefing-0527b` is stuck in a retry loop on Step 2 (`app/api/main.py`). The root cause: `coder-worker` resolves to `deepseek-ai/deepseek-v4-flash` on NVIDIA NIM, which outputs `<think>...</think>` reasoning blocks in its response. Aider receives this through LiteLLM as a generic `openai/coder-worker` model and doesn't know to strip those blocks. The thinking text bleeds into aider's filename parser, creating files at malformed paths like:

```
Let's produce the file listing.</think>app/services/ingestion_service.py
```

…instead of `app/services/ingestion_service.py`. The intended file stays at 0 bytes, the build/test gate fails, retries exhaust, and the pipeline stalls.

**Code quality is NOT affected by the fix.** The `reasoning_tag: think` approach tells aider how to *parse* DeepSeek's output — the model still reasons internally and produces the same quality code. Aider simply strips the `<think>` tag region from the content it uses for file editing (it still *displays* thinking blocks in the chat log). This is the documented, idiomatic aider solution for reasoning models.

## Root Cause Chain

1. LiteLLM alias `coder-worker` → `openai/deepseek-ai/deepseek-v4-flash` (NIM, 90s timeout)
2. DeepSeek-V4-Flash emits `<think>…</think>` in plain response text
3. `_build_aider_argv()` in `aider_runner.py` passes no model settings — aider treats response as plain text
4. Aider's file-listing parser picks up `</think>` as part of the filename
5. File written to wrong path; correct path stays 0 bytes → build/test gate fails

## Fix (one approach, two files)

### File 1 — Create model settings YAML

**Path:** `hermes-skills/.aider.model.settings.yml` (new file)

```yaml
- name: openai/coder-worker
  reasoning_tag: think
```

`reasoning_tag: think` is the aider v0.86.2 mechanism for reasoning models: aider displays the `<think>` block in the chat log but strips it from the text used for diff parsing and file editing. The model still reasons; aider just interprets the output correctly.

No other settings needed — `edit_format`, `use_repo_map`, etc. remain at aider's defaults which already work for this pipeline.

### File 2 — Pass `--model-settings-file` in aider invocation

**Path:** `hermes-skills/aider_runner.py`

In `_build_aider_argv()` (around line 212–238), add one entry to the `argv` list:

```python
# After the existing --no-* flags, before --message:
"--model-settings-file", str(Path(__file__).parent / ".aider.model.settings.yml"),
```

`Path(__file__).parent` resolves to `hermes-skills/` regardless of working directory, so the path is always found.

### Deploy to VPS

After committing locally:
```bash
rsync -av hermes-skills/aider_runner.py \
         hermes-skills/.aider.model.settings.yml \
    root@31.97.130.253:/opt/ultra-workshop/hermes-skills/
```

### Handle the stuck build

The current build (`ws-ai-briefing-0527b`) is in a stuck retry loop. After deploying:
1. Kill the active aider/coder processes for this task
2. Reset `state.json` `current_step` back to the original Step 2 (or restart the build entirely as `ws-ai-briefing-0527c`)

The simplest path is a fresh build — the workspace is polluted with malformed files.

## Verification

1. Launch a new build task targeting the same repo
2. Monitor `progress_log.jsonl` — expect `step_complete` events for each step
3. Check `git log` in the workspace — expect clean commit per step with correct file paths
4. Confirm no filenames containing `<think>` or `</think>` exist: `find /tmp/uws-workspace-* -name '*think*'`

## Files modified

| File | Change |
|------|--------|
| `hermes-skills/.aider.model.settings.yml` | New — defines `reasoning_tag: think` for `openai/coder-worker` |
| `hermes-skills/aider_runner.py` | Add `--model-settings-file` flag in `_build_aider_argv()` |
