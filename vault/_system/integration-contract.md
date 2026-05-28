---
title: Workshop Integration Contract
workshop.created_by: install-script
---

# Workshop Integration Contract

This document defines the shared vocabulary between ultra-agents-brain (Brain)
and ultra-workshop (Workshop). Both sides MUST treat this as authoritative.

## Frontmatter Field Vocabulary

| Field | Owner | Written by | Valid values | Notes |
|-------|-------|------------|--------------|-------|
| `workshop.suggested_action` | Workshop | Brain ingest agent | `fix-test-failure`, `review`, `security-scan` | Suggestion only; requires human confirmation |
| `workshop.action` | Workshop | Brain daily-digest | `build`, `fix`, `post-to-telegram`, `link-orphans` | Confirmed verb for dispatch |
| `workshop.confirmed` | Workshop | Human via Telegram HITL | `true`, `false` | Must be `true` before fast-poll dispatches |
| `workshop.status` | Brain+Workshop | Either side | `pending`, `in-progress`, `done`, `failed` | Lifecycle state |
| `workshop.task_id` | Workshop | workshop_build / workshop_fix | UUID string | Correlates ledger entries |
| `workshop.dispatched` | Workshop | fast-poll / standard-poll | `true` | Set after ACK to Brain; prevents double-dispatch |
| `workshop.pr_url` | Workshop | workshop_push | GitHub PR URL | Written after PR creation |
| `workshop.created_by` | Brain | Brain ingest agent | `daily-research`, `nightly-tests`, `install-script` | Source traceability |

## Dispatch Flows

### Flow A: Build task
Brain daily-digest writes queue entry (`action: build`, `confirmed: false`) →
Telegram HITL (`confirmed: true`) →
fast-poll dispatches `workshop_build.py` →
ACK (`dispatched: true`) →
PR URL written back to vault.

### Flow B: Fix task
Brain daily-digest writes queue entry (`action: fix`, `confirmed: false`) →
Telegram HITL (`confirmed: true`) →
fast-poll dispatches `workshop_fix.py` →
ACK (`dispatched: true`).

### Flow D: Test failure (suggested, not auto-dispatched)
nightly-tests writes vault note (`workshop.suggested_action: fix-test-failure`) →
Brain daily-digest surfaces in digest →
Human reviews → promotes to Flow B if desired.

### Flow E: Post to Telegram (zero-HITL)
Brain daily-digest writes queue entry (`action: post-to-telegram`, `confirmed: true`) →
fast-poll sends Telegram message →
ACK (`dispatched: true`).

## Write Rules
- Only Brain writes `workshop.action` and `workshop.confirmed`.
- Only Workshop writes `workshop.dispatched`, `workshop.task_id`, `workshop.pr_url`.
- Either side may write `workshop.status`.
- `workshop.confirmed: true` is irrevocable once written.
