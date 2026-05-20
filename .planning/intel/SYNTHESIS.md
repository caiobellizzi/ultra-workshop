# Synthesis Entry Point

Generated: 2026-05-20
Mode: new
Precedence: ["ADR", "SPEC", "PRD", "DOC"]

---

## Doc counts by type

- SPEC: 1 (docs/ingest/PLAN.md — precedence 0, manifest_override: true)
- ADR: 0
- PRD: 0
- DOC: 0
- UNKNOWN: 0

Total docs synthesized: 1

---

## Decisions locked

Count: 30 (L1–L30 promoted from §"Locked decisions" section in source document)
Source: docs/ingest/PLAN.md

Key locked decisions:
- L2: Orchestrator = Hermes Agent v0.14.0
- L9: Model-agnostic via LiteLLM proxy at 127.0.0.1:4000
- L10: Coder = Aider (NOT Claude Code)
- L11: Coordination = Hermes delegate_task (NOT LangGraph)
- L22: LangGraph removed from Phase 1
- L24: Integration model = "one system, two tiers, vault as connective tissue"
- L28: Two-tier signaling vocabulary for vault frontmatter

See: .planning/intel/decisions.md

---

## Requirements extracted

Count: 28 (WS-001 through WS-028)

IDs: REQ-ws-001 through REQ-ws-028

Scope areas:
- Infrastructure: REQ-ws-001 (Hermes systemd), REQ-ws-005 (Hermes install), REQ-ws-013 (Telegram dedup), REQ-ws-015 (MCP registration)
- Core skills: REQ-ws-003 (skill audit), REQ-ws-004 (Tier 1 ports), REQ-ws-005 (brain-bridge), REQ-ws-006 (Aider skill)
- Pipeline: REQ-ws-007 (workshop-build), REQ-ws-008 (workshop-fix), REQ-ws-028 (Pydantic schemas)
- Observability: REQ-ws-009 (two-ledger), REQ-ws-010 (HITL), REQ-ws-011 (ADR write-back), REQ-ws-012 (cost ledger)
- Autonomous routines: REQ-ws-016 (daily-research), REQ-ws-017 (nightly-tests), REQ-ws-018 (bug-scan/polling)
- Integration flows: REQ-ws-020 (Flow B), REQ-ws-021 (Flow E), REQ-ws-022 (trust symlink), REQ-ws-023 (integration contract)
- Vault sync: REQ-ws-024 (GitHub remote), REQ-ws-025 (Mac Obsidian-Git), REQ-ws-026 (VPS cron), REQ-ws-027 (env vars)
- Safety: REQ-ws-014 (restart resilience), REQ-ws-019 (cron budget enforcement)

See: .planning/intel/requirements.md

---

## Constraints

Count: 18

Type breakdown:
- protocol: 11 (Hermes-only gateway, no LangGraph, HITL on push, no event bus, cron no-overlap, systemd dependency, skill translation safety, no excluded patterns, vault write zones, HTTP one-way, branch protection)
- nfr: 5 (model-agnostic, blast radius, budget circuit breaker, retry caps, Python 3.11)
- api-contract: 2 (LiteLLM proxy + 6 aliases, Brain HTTP one-way)

See: .planning/intel/constraints.md

---

## Context topics

Count: 9

Topics:
1. Project origin and timing
2. Plan revision history (v1→v2→v3)
3. Brain HTTP surface / workshop contract with Brain
4. Multi-agent patterns research summary (10 patterns, P1–P10)
5. Aider composition details and rejected alternatives
6. Real-world architecture primitives adopted (Magentic-One, OpenHands V1, Manus, Claude Agent SDK, mini-SWE-agent)
7. Cost envelope and model routing strategy
8. Verification matrix (V1–V24)
9. Risks and mitigations + Phase 1 execution timeline

See: .planning/intel/context.md

---

## Conflicts

Blockers: 0
Competing variants: 0 (single source; no competing PRDs)
Warnings: 2 (classification locked-field mismatch; repo-tree vs L22 internal inconsistency)
Auto-resolved: 0

See: .planning/INGEST-CONFLICTS.md

---

## Status

STATUS: AWAITING USER — 2 warnings need review before routing

The warnings do not block synthesis but should be confirmed before the roadmapper generates execution artifacts:
1. Confirm L1–L30 should be treated as LOCKED in decisions.md (likely yes — document is explicit)
2. Confirm workshop/graph.py in repo tree should be renamed to workshop/orchestrator.py (likely yes — L22 is unambiguous)

---

## Intel file index

- .planning/intel/decisions.md — 30 locked decisions (L1–L30) + 10 integration decisions (D1–D10)
- .planning/intel/requirements.md — 28 requirements (REQ-ws-001 through REQ-ws-028)
- .planning/intel/constraints.md — 18 constraints (protocol/nfr/api-contract)
- .planning/intel/context.md — 9 context topics with full source attribution
- .planning/INGEST-CONFLICTS.md — conflict detection report (0 blockers, 2 warnings, 1 info)
