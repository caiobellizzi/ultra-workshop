---
name: brain-query
description: "Query the vault: answer a question using Brain's knowledge base. Use for 'brain-query --question <q>', 'ask brain', 'vault search', or similar."
version: 1.0.0
author: ultra-workshop
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [brain, vault, query, research]
---

# Brain Query

Query the Brain Agno endpoint for a vault-grounded answer.

## Usage

Parse the `--question` argument from the trigger, then delegate to the brain HTTP helper.

## Steps

1. Extract the `--question` argument from the user message.
2. Run: `terminal python3 /opt/ultra-workshop/hermes-skills/brain_http.py query "<question>"`
3. Parse the JSON response; surface the `content` field as the answer.

## V4 Acceptance Note

Brain's query agent currently returns `status: ERROR` due to a Groq structured-output
+ tool-calling conflict in the LiteLLM configuration. HTTP 200 and `run_id` are returned
correctly. The content field will contain the LiteLLM error message rather than a
vault-grounded answer until the upstream Groq issue is resolved.

## FOLLOW-UP BACKLOG

Once Brain's Groq structured-output issue is resolved: upgrade the brain-smoke.bats
HTTP live test to assert `content` is non-empty and contains vault document references.
The smoke test currently asserts HTTP 200 + `run_id` only (V4 relaxation, decided 2026-05-21).

## Dry-run behavior

If the trigger contains `--dry-run`, print the command that would execute and the
question extracted, then stop without calling `terminal`.

Example dry-run output:
```
[dry-run] would run: python3 /opt/ultra-workshop/hermes-skills/brain_http.py query "what is PARA"
```
