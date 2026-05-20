## Conflict Detection Report

### BLOCKERS (0)

None.

### WARNINGS (1)

[WARNING] Classification JSON marks locked: false, but source document declares explicit Locked Decisions section
  Found: docs/ingest/PLAN.md contains §"Locked decisions (chosen during this discuss-phase session)" with 30 explicitly named locked decisions (L1–L30) established during /grill-me sessions on 2026-05-19
  Found: PLAN-d4e8f1a2.json has `locked: false` — the classifier could not read the file body (only line 1 was accessible via claude-mem at classification time); notes field confirms: "File content only partially readable via claude-mem observation (title only)"
  Impact: Synthesizer promoted L1–L30 to LOCKED status based on source document content. If the author intended these decisions to remain non-locked (i.e., still negotiable), the decisions.md file overstates their authority.
  source (classification): .planning/intel/classifications/PLAN-d4e8f1a2.json
  source (document): docs/ingest/PLAN.md §Locked decisions
  → Review decisions.md and confirm whether L1–L30 should be treated as LOCKED (cannot be auto-overridden downstream) or as proposed decisions. If locked status is correct, no action needed. If they should remain proposed, re-run classification with `locked: false` enforced and update decisions.md accordingly.

[WARNING] Repo tree in PLAN.md references workshop/graph.py (LangGraph) but L22 locks LangGraph out of Phase 1
  Found: docs/ingest/PLAN.md §Repo tree lists `workshop/graph.py (LangGraph StateGraph + SqliteSaver)` as a deliverable
  Found: docs/ingest/PLAN.md §Locked decisions L22 declares "LangGraph removed from Phase 1"
  Found: docs/ingest/PLAN.md §Key invariants confirms "No LangGraph in Phase 1"
  Impact: Repo tree is internally inconsistent with L22. The constraints.md and context.md synthesized intel notes this discrepancy. Downstream roadmapper may generate a LangGraph file as a deliverable if it reads the repo tree without L22 context.
  source: docs/ingest/PLAN.md §Repo tree vs §Locked decisions L22
  → Before execution phase: rename `workshop/graph.py` to `workshop/orchestrator.py` in the repo tree (already noted in context.md). The orchestrator.py implements Hermes `delegate_task` pattern, not LangGraph StateGraph. No LangGraph dep in pyproject.toml Phase 1.

### INFO (1)

[INFO] Single-source ingest — no cross-doc precedence resolution required
  Note: Only one document was classified in this ingest run (docs/ingest/PLAN.md, type=SPEC, precedence=0). No ADR-vs-SPEC, PRD-vs-PRD, or lower-vs-higher-precedence conflicts are possible with a single source. Cycle detection: no cross_refs declared in classification JSON; no cycles possible.
  source: .planning/intel/classifications/PLAN-d4e8f1a2.json (`cross_refs: []`)
  Note: Mode is `new` with no EXISTING_CONTEXT; no merge-mode LOCKED contradiction checks performed.
