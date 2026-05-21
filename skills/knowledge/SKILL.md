---
name: knowledge
description: >
  Intelligent knowledge lookup using curated sources before any web search.
  Use when the query involves development, infrastructure, security, debugging,
  or technical architecture. Triggers: "how to fix", "best practice for",
  "how to configure", "how did we solve", "what's the best way to",
  "debug this error", "architecture for", "como resolver", "best practice para".
version: 1.0.0
author: ultra-workshop (ported from Claude Code skill)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [knowledge, research, lookup]
---

# Knowledge Consultation

Consult curated knowledge sources in strict tier order before resorting to web search.

## Source Hierarchy (MANDATORY order)

1. **Curated notebooks / internal docs** (zero hallucination — highest trust)
2. **Official library documentation** (use search_file or http_request for docs sites)
3. **Session history / prior decisions** (what was solved before, what was decided)
4. **Web search** (last resort only)

Never jump straight to web search because it feels faster. The hierarchy exists because higher tiers are more trustworthy.

## Consultation Flow

### Step 1: Classify the query

Determine which tier is most likely to have the answer:

- Errors / bugs → curated debug solutions
- Architecture / patterns → architecture decisions
- Framework / library API → official docs
- "How did we do X" / "Did we already solve Y" → session history
- Novel / current events → web search

### Step 2: Execute in tier order

**Tier 1 — Curated notebooks:**
Use read_file or search tools to look in project docs, ADRs, and internal knowledge files.
If answer found: use it and stop.
If insufficient: proceed to Tier 2.

**Tier 2 — Official documentation:**
Use http_request or search to access official library/framework docs.
If answer found: use it and stop.
If insufficient: proceed to Tier 3.

**Tier 3 — Session history:**
Search conversation history and prior decisions for relevant context.
Especially useful for "how did we do X", "why did we decide Y", "did we solve this before".
If answer found: use it and stop.
If insufficient: proceed to Tier 4.

**Tier 4 — Web search:**
Last resort. Prefer official sources (vendor blogs, release notes) over aggregators.
If you reach here for a library question, check whether Tier 2 was really exhausted first.

### Step 3: Feedback loop

When a solution was found outside the curated internal docs and is worth preserving:
Note it in your response with "Knowledge captured: [summary]" so it can be added to internal docs.

## Quick Routing Reference

| Query type | Primary tier |
|------------|-------------|
| Error / exception | Curated docs |
| Architecture decision | Curated docs |
| Framework API | Official docs |
| Version migration | Official docs |
| "Did we solve X" | Session history |
| Breaking news / changelog | Web search |

## Rules

1. NEVER do web search without first checking curated internal docs
2. ALWAYS note the source of your answer
3. PREFER official docs for library API questions — training data may be stale
4. USE session history for context about prior decisions ("how did we", "why did we decide")
5. Only solutions you've confirmed — not speculation

## Dry-run behavior
If the trigger contains `--dry-run`, print the steps that would execute and the arguments extracted, then stop without taking any action.
