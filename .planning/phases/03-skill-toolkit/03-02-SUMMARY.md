---
phase: 03-skill-toolkit
plan: "02"
subsystem: scripts
tags: [audit, skill-classification, auto-translate, pytest, tdd]

# Dependency graph
requires:
  - phase: 03-skill-toolkit
    plan: "01"
    provides: pytest infrastructure (pyproject.toml, hermes-skills test patterns, importlib loader convention)
provides:
  - scripts/audit-claude-skills.py — classifies ~/.claude/skills/ into 4 categories, auto-translates to ~/.hermes/skills/translated/
  - scripts/test_audit.py — 9 pytest tests covering all acceptance criteria
  - skill-audit.json (generated at runtime, not committed — in .gitignore)
  - TRANSLATION_NOTES.md per auto_translated skill under ~/.hermes/skills/translated/<name>/
affects: [03-03, 03-04, 03-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "importlib spec_from_file_location for hyphenated module names in tests"
    - "idempotency via timestamp preservation (reuse generated_at when skills data unchanged)"
    - "path traversal mitigation: Path(name).name + assert '..' not in safe_name"
    - "argparse --apply flag (absence = dry-run) for safe-by-default CLI"
    - "stdlib-only Python (argparse, json, pathlib, re, datetime) — no PyYAML"

key-files:
  created:
    - scripts/test_audit.py
    - scripts/audit-claude-skills.py
  modified:
    - .gitignore (added skill-audit.json)

key-decisions:
  - "Idempotency implemented by preserving existing generated_at timestamp when skills data is byte-identical — avoids timestamp drift on repeated runs"
  - "autouse fixture for module load: tests skip (not error) when audit-claude-skills.py absent; allows --collect-only to succeed in RED state"
  - "skill-audit.json added to .gitignore (T-03-07: generated output, contains no secrets)"
  - "stdlib-only: no PyYAML required; frontmatter parsed via split('---') as specified in plan"

patterns-established:
  - "test_audit.py autouse fixture: _load_audit() with pytest.skip fallback for RED-state compatibility"
  - "main_with_roots(claude_root, hermes_root, dry_run, audit_json_path) — testable entry point with injected paths"
  - "_write_file(path, content, dry_run) — idempotent guard: skips write if content unchanged"

requirements-completed: [REQ-ws-003]

# Metrics
duration: 5min
completed: 2026-05-21
---

# Phase 3 Plan 02: Skill Audit + Auto-Translate Script Summary

**Stdlib-only Python audit script classifying 113 Claude skills into 4 categories with safe auto-translation to ~/.hermes/skills/translated/**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-21T18:29:50Z
- **Completed:** 2026-05-21T18:35:06Z
- **Tasks:** 2
- **Files modified:** 3 (2 new scripts + .gitignore)

## Accomplishments

- `scripts/test_audit.py`: 9 pytest tests covering all acceptance criteria (dry-run safety, apply writes, idempotency, gsd- skip, path safety, JSON schema, TRANSLATION_NOTES.md content, agent_agnostic, requires_manual_port)
- `scripts/audit-claude-skills.py`: classifies 113 Claude skills across 4 categories: 67 claude_specific_skip, 14 auto_translated, 14 agent_agnostic, 18 requires_manual_port
- Auto-translation: writes TRANSLATION_NOTES.md for 14 auto_translated skills under ~/.hermes/skills/translated/
- Safety: path traversal mitigation (Path.name + assert ".." check); no writes outside HERMES_TRANSLATED_ROOT
- Idempotency: consecutive --apply runs produce byte-for-byte identical skill-audit.json (timestamp preserved)
- All 9 tests pass GREEN

## Task Commits

1. **Task 1: test_audit.py (RED state)** — `d11b361`
2. **Task 2: audit-claude-skills.py (GREEN)** — `5e47a1c`

## Files Created/Modified

- `scripts/test_audit.py` — 9 pytest tests; autouse fixture with importlib hyphen-safe loader; tmp_path isolation
- `scripts/audit-claude-skills.py` — 200+ lines; classify(), main_with_roots(), _write_file(), main() CLI
- `.gitignore` — added skill-audit.json (generated output, T-03-07)

## Verification Results

```
pytest scripts/test_audit.py -v
9 passed in 0.02s

python scripts/audit-claude-skills.py          # dry-run exits 0, no writes
python scripts/audit-claude-skills.py --apply  # skill-audit.json written, 14 TRANSLATION_NOTES.md files

grep -rn "hermes/skills" scripts/audit-claude-skills.py | grep -v translated
# returns empty — PASS

Idempotency: md5(skill-audit.json) identical on second --apply run — PASS
```

## Decisions Made

- **Idempotency via timestamp preservation**: on second run, if `skills` data is byte-identical to existing skill-audit.json, the existing `generated_at` is reused. This gives true byte-for-byte idempotency without sacrificing meaningful timestamps.
- **autouse fixture instead of module-level exec**: avoids collection failure in RED state; tests skip cleanly when the implementation file is absent.
- **stdlib-only**: no PyYAML; frontmatter parsed by `raw.split("---")` as specified in plan.
- **audit_json_path injected**: `main_with_roots` accepts optional `audit_json_path` so tests can run in tmp_path without writing to the repo root.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Idempotency for skill-audit.json on disk**
- **Found during:** Task 2 acceptance criteria verification
- **Issue:** `generated_at` timestamp changed on every run, making skill-audit.json non-identical on consecutive --apply calls
- **Fix:** Added idempotency logic: read existing skill-audit.json; if skills data is identical, reuse existing `generated_at` timestamp
- **Files modified:** scripts/audit-claude-skills.py
- **Commit:** 5e47a1c

**2. [Rule 2 - Missing functionality] Add skill-audit.json to .gitignore**
- **Found during:** Task 2 commit — git status showed skill-audit.json as untracked
- **Issue:** Generated file would be accidentally committed
- **Fix:** Added skill-audit.json to .gitignore (T-03-07 threat disposition: accept, add to gitignore)
- **Files modified:** .gitignore
- **Commit:** 5e47a1c

## Known Stubs

None — all classification logic is implemented and verified against real ~/.claude/skills/ (113 skills).

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced. Files written are:
- skill-audit.json (repo root, generated, in .gitignore) — contains skill names/categories, no secrets
- TRANSLATION_NOTES.md under ~/.hermes/skills/translated/<name>/ (Mac-local, not VPS)

T-03-05 (path traversal) mitigated per plan. T-03-07 (skill-audit.json disclosure) mitigated via .gitignore.

---
*Phase: 03-skill-toolkit | Plan: 02 | REQ-ws-003*
*Completed: 2026-05-21*
