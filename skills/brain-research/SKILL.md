---
name: brain-research
description: "Run a multi-step research task via Brain. Use for 'brain-research --topic <topic>', 'research with brain', 'synthesize information about'. Invokes Brain's research agent for deep synthesis."
version: 1.0.0
author: ultra-workshop
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [brain, vault, research, synthesis]
---

# Brain Research

Invoke Brain's research agent for multi-step synthesis on a topic.

## Usage

Parse the `--topic` argument from the trigger, then delegate to the brain HTTP helper.

## Steps

1. Extract the `--topic` argument from the user message.
2. Run: `terminal python3 /opt/ultra-workshop/hermes-skills/brain_http.py research "<topic>"`
3. Parse the JSON response; surface the `content` field as the synthesized research output.

## Dry-run behavior

If the trigger contains `--dry-run`, print the command that would execute and the
topic extracted, then stop without calling `terminal`.

Example dry-run output:
```
[dry-run] would run: python3 /opt/ultra-workshop/hermes-skills/brain_http.py research "PARA"
```
