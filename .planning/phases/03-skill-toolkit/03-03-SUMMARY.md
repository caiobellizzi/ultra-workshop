---
phase: 03-skill-toolkit
plan: "03"
subsystem: skills
tags: [hermes, skills, porting, vps, bats, pytest]

# Dependency graph
requires:
  - phase: 03-skill-toolkit
    plan: "01"
    provides: hermes-skill-run.sh on VPS, bats helpers, pytest test_skill_frontmatter.py
provides:
  - skills/caveman/SKILL.md — Hermes-formatted caveman brevity skill
  - skills/diagnose/SKILL.md — Hermes-formatted debugging diagnosis methodology
  - skills/knowledge/SKILL.md — Hermes-formatted knowledge lookup hierarchy
  - skills/write-a-prd/SKILL.md — Hermes-formatted PRD creation workflow
  - skills/zoom-out/SKILL.md — Hermes-formatted abstraction/perspective skill
  - skills/grill-me/SKILL.md — Hermes-formatted interview/requirements skill
  - skills/triage/SKILL.md — Hermes-formatted issue triage state machine
  - skills/commit/SKILL.md — Hermes-formatted git commit workflow (README-sync removed)
  - skills/triage-issue/SKILL.md — Hermes-formatted bug triage with TRANSLATION NOTE
  - skills/qa/SKILL.md — Hermes-formatted QA session skill with TRANSLATION NOTE
  - tests/phase-03/skills-smoke.bats — 10 dry-run smoke tests, 10/10 passing
  - VPS /home/uws/.hermes/skills/ — all 10 skills deployed via rsync
affects: [03-04, 03-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Hermes SKILL.md frontmatter canonical pattern (name/description/version/author/license/platforms/metadata.hermes.tags)
    - TRANSLATION NOTE inline comment replacing Agent/Explore subagent references
    - Dry-run body section in every skill
    - rsync to VPS for skill deployment (NOT hermes skills install — no local-path mode)

key-files:
  created:
    - skills/caveman/SKILL.md
    - skills/diagnose/SKILL.md
    - skills/knowledge/SKILL.md
    - skills/write-a-prd/SKILL.md
    - skills/zoom-out/SKILL.md
    - skills/grill-me/SKILL.md
    - skills/triage/SKILL.md
    - skills/commit/SKILL.md
    - skills/triage-issue/SKILL.md
    - skills/qa/SKILL.md
    - tests/phase-03/skills-smoke.bats
  modified: []

key-decisions:
  - "knowledge skill body simplified to generic tier hierarchy (source was Portuguese/CLI-specific; rewritten in English as Hermes-portable methodology)"
  - "TRANSLATION NOTE placed as # comment above replacement prose (not as YAML block) — inline comment allows original text traceability"
  - "subagent_type=Explore preserved inside TRANSLATION NOTE comment lines only — not as active instruction"
  - "commit skill readme-sync step removed; replaced with generic project docs note"
  - "rsync -avz used for batch deploy to /home/uws/.hermes/skills/ — all 10 in single command"

requirements-completed: [REQ-ws-004]

# Metrics
duration: 25min
completed: 2026-05-21
---

# Phase 3 Plan 03: Tier 1 Skill Porting Summary

**10 Claude Code skills ported to Hermes format with valid frontmatter, TRANSLATION NOTEs where required, and deployed to VPS via rsync — REQ-ws-004 satisfied**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-21T18:30:00Z
- **Completed:** 2026-05-21T18:55:00Z
- **Tasks:** 2
- **Files created:** 11

## Accomplishments

- 10 Hermes-formatted SKILL.md files created under skills/
- All frontmatter validated: name, description, version, author, license, platforms, metadata.hermes.tags
- No forbidden keys (tools:, mcpServers:, hooks:, disable-model-invocation) in any skill
- triage-issue and qa: Agent/Explore replaced with TRANSLATION NOTE + direct tool instructions
- commit: README-sync checkpoint removed (Claude ecosystem only)
- All 10 skills deployed to VPS /home/uws/.hermes/skills/ via rsync
- tests/phase-03/skills-smoke.bats: 10/10 dry-run smoke tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Port 7 agent-agnostic skills** — `e6d627d` (feat)
2. **Task 2: Port remaining 3 skills, deploy all 10, create bats smoke** — `081d327` (feat)

## Verification Results

| Check | Result |
|-------|--------|
| `pytest hermes-skills/test_skill_frontmatter.py` | 20/20 PASSED |
| `bats tests/phase-03/skills-smoke.bats` | 10/10 PASSED |
| `grep -rl "tools:" skills/` | EMPTY (clean) |
| `grep -rl "disable-model-invocation" skills/` | EMPTY (clean) |
| `grep -i "readme-sync" skills/commit/SKILL.md` | EMPTY (clean) |
| `grep "TRANSLATION NOTE" skills/triage-issue/SKILL.md` | FOUND |
| `grep "TRANSLATION NOTE" skills/qa/SKILL.md` | FOUND |
| VPS `ls /home/uws/.hermes/skills/` | All 10 dirs present |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] knowledge skill rewritten for Hermes portability**
- **Found during:** Task 1
- **Issue:** Source skill at ~/.claude/skills/knowledge/SKILL.md was heavily customized with Portuguese text, references to a local KnowledgeBase CLI tool (`npx tsx /Users/arrigoni/Repository/KnowledgeBaseForDeveloper/...`), NotebookLM MCP tool names, and Mac-specific paths — none of which exist on the VPS
- **Fix:** Rewrote the skill body as a generic, Hermes-portable knowledge consultation methodology using the same tiered hierarchy principle but with portable tool references (search, read_file, http_request)
- **Files modified:** skills/knowledge/SKILL.md
- **Commit:** e6d627d

## Known Stubs

None — all 10 skills are complete implementations with functional body content.

## Threat Flags

None — all files are SKILL.md markdown (prose instructions). No executable code, no new network endpoints, no auth paths introduced. T-03-09 through T-03-12 from the plan's threat register are addressed as documented.
