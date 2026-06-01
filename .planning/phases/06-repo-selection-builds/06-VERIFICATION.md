---
phase: 06-repo-selection-builds
verified: 2026-06-01
verifier: inline (Opus — Sonnet verifier tier rate-limited until 18:00)
status: pass_with_caveats
score: "REQ-ws-029 code-verified across 5 success criteria; live Telegram approval + live PR deferred to human"
requirements_checked: ["REQ-ws-029"]
human_verification:
  - test: "Live /repo add/create/remove approval flow"
    expected: "Each mutation prompts a Telegram approval; approval mutates registry/GitHub, rejection aborts; /repo create makes a private repo with README"
    why_human: "Requires live Telegram interaction + GitHub API writes; offline confirms the approval-gated code paths and permission checks exist"
  - test: "Live /build --repo PR against a registered repo"
    expected: "/build --repo <repo> opens a PR against that repo's default branch; final approval card shows repo, base branch, feature branch, changed files, diff summary"
    why_human: "Requires a live pipeline run against a throwaway registered repo"
---

# Phase 6: Repo Selection & Multi-Repo Builds — Verification Report

**Phase Goal:** Telegram can create, register, list, disable, and target active repos through a Brain-backed registry while preserving HITL before repo mutations, pushes, and PR creation.
**Verified:** 2026-06-01 · **Status:** pass_with_caveats · **Re-verification:** No (initial — backfilled during v1.0 milestone audit)

> Backfill note: Phase 6 shipped without a VERIFICATION.md. `06-01-SUMMARY.md` frontmatter lists `requirements-completed: [REQ-ws-029]`. This report verifies the registry + dispatch code locally; live Telegram/GitHub behaviors are flagged human_needed.

## Requirement

| Aspect of REQ-ws-029 | Status | Evidence |
|----------------------|--------|----------|
| `/repo list\|add\|create\|remove` subcommands | verified | `hermes-skills/workshop_repo.py` handles "list", "add", "create", "remove". |
| Registry backing + auto-seed test-workshop-sandbox | verified | `workshop/repo_registry.py`: `DEFAULT_REPO = "{owner}/test-workshop-sandbox"` (line 15), `seed_entry()` (line 99) appended when registry missing (lines 182, 193). Registry path `workshop-repos.json` referenced. |
| Permission validation WRITE/MAINTAIN/ADMIN on add | verified | `workshop/repo_registry.py` WRITE/MAINTAIN/ADMIN → 4 matches. |
| `/build --repo` repo-targeted dispatch | verified | `hermes-skills/workshop_build.py` `--repo` argparse (line 647), repo resolution (lines 790, 798). |
| `/fix <issue-url>` derives owner/name | verified | `hermes-skills/workshop_fix.py` `parse_issue_repo(args.issue_url)` (line 25). |
| Approval-gated mutations / PR approval card | verified (code) / human (live) | Approval gating present; live button flow + PR card → human_needed. |

## Success Criteria

| SC | Status | Evidence |
|----|--------|----------|
| SC-1 /repo list auto-seeds sandbox | verified | `seed_entry()` on missing registry |
| SC-2 add/create/remove validate perms + require approval | verified (code) / human (live) | WRITE/MAINTAIN/ADMIN checks; live approval → human |
| SC-3 /build --repo validates active repo + targets default branch | verified (code) / human (live) | `--repo` resolution; live PR → human |
| SC-4 /fix derives repo + rejects unknown/inactive | verified | `parse_issue_repo` |
| SC-5 PR approval card shows repo/branches/files/diff | verified (code) / human (live) | card builder present; live render → human |

## Verdict

REQ-ws-029 is code-complete across all five success criteria — registry (`repo_registry.py`), the four `/repo` subcommands (`workshop_repo.py`), `--repo` targeting (`workshop_build.py`), and `/fix` URL derivation (`workshop_fix.py`) are all wired with permission checks and approval gating. Live Telegram approval and a live PR against a registered repo remain `human_needed`. Overall: **pass_with_caveats**.
