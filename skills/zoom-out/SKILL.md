---
name: zoom-out
description: Tell the agent to zoom out and give broader context or a higher-level perspective. Use when you're unfamiliar with a section of code or need to understand how it fits into the bigger picture.
version: 1.0.0
author: ultra-workshop (ported from Claude Code skill)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [reflection, metacognition, planning]
---

I don't know this area of code well. Go up a layer of abstraction. Give me a map of all the relevant modules and callers, using the project's domain glossary vocabulary.

## Dry-run behavior
If the trigger contains `--dry-run`, print the steps that would execute and the arguments extracted, then stop without taking any action.
