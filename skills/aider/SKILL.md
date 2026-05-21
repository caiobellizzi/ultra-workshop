---
name: aider
description: "Run Aider coder on a task. Use for 'aider --task <description>', 'code with aider', or 'coder run'. Invokes architect=cloud-sonnet + editor=private-worker via LiteLLM proxy."
version: 1.0.0
author: ultra-workshop (local impl)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [coder, aider, coding, git, diff]
---

## Aider Coder

Invokes aider as a subprocess with architect/editor model split through the LiteLLM proxy.

## Behavior

1. Extract `--task` from the user trigger
2. Run: `terminal python3 /opt/ultra-workshop/hermes-skills/aider_runner.py --task "<task>"`
3. Capture stdout (diff summary) and return it

## Models

- Architect: openai/cloud-sonnet (via LiteLLM proxy at 127.0.0.1:4000)
- Editor: openai/private-worker (requires LM Studio running on Mac with LM Link active)

## Cost Ledger (OPTION B — BACKLOG)

After the aider run, aider_runner.py posts a completion event to Brain's curator agent (HTTP 200 + run_id).
Full 2-LLM-call cost verification is deferred until Brain exposes a queryable cost-history endpoint.
Current smoke test asserts curator endpoint is reachable only (decided 2026-05-21).

## Dry-run behavior

If trigger contains `--dry-run`, print the aider command that would execute and the task extracted, then stop without calling terminal.
