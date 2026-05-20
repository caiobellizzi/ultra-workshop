# Phase 2 Discussion Log

**Date:** 2026-05-20
**Phase:** 02 — Hermes Deploy

---

## Gray Areas Presented

1. Service hardening posture (dedicated `uws` user, ProtectSystem, MemoryMax, NoNewPrivileges)
2. MCP credential storage & rotation (EnvironmentFile vs per-MCP vs systemd-creds)
3. google-workspace OAuth bootstrap (ssh tunnel, pre-auth copy, or defer)
4. Restart-resilience smoke test (V14) — exact scripted scenario

## User Selection

**"none"** — User declined to discuss any open gray areas, deferring all four to downstream agents (researcher + planner).

## Outcome

CONTEXT.md captures:
- All locked architectural decisions (L1–L30, D1–D10) carried forward
- All 5 Phase 2 requirements and their acceptance criteria
- Pre-deploy gates (token rotation, `uab-telegram` stopped, RAM check, Phase 1 done)
- Four open gray areas explicitly flagged for planner discretion with recommended defaults

## Deferred Ideas

None.
