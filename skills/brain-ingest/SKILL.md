---
name: brain-ingest
description: "Ingest content into the vault via Brain. Use for 'brain-ingest --content <text>', 'add to vault', 'ingest note'. Warning: Brain's ingest agent is HITL-gated — human approval required on Brain side before vault write completes."
version: 1.0.0
author: ultra-workshop
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [brain, vault, ingest, write]
---

# Brain Ingest

Send content to the Brain Agno ingest agent for vault storage.

## Usage

Parse the `--content` argument from the trigger, then delegate to the brain HTTP helper.

## Steps

1. Extract the `--content` argument from the user message.
2. Run: `terminal python3 /opt/ultra-workshop/hermes-skills/brain_http.py ingest "<content>"`
3. Parse the JSON response; surface the `run_id` to confirm the request was received.

## HITL Warning

Note: Brain's ingest agent requires human approval (HITL) before the vault write is
committed. The smoke test verifies HTTP 200 and `run_id` only — it does not verify that
content was written to the vault. Do not assume ingest is complete until Brain-side
HITL approval is confirmed.

## Dry-run behavior

If the trigger contains `--dry-run`, print the command that would execute and the
content that would be ingested, then stop without calling `terminal`.

Example dry-run output:
```
[dry-run] would run: python3 /opt/ultra-workshop/hermes-skills/brain_http.py ingest "test note"
```
