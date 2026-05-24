---
phase: "06-repo-selection-builds"
plan: "06-01"
type: "feature"
wave: 1
depends_on: ["04-06"]
files_modified:
  - "workshop/repo_registry.py"
  - "hermes-skills/workshop_repo.py"
  - "hermes-skills/workshop_build.py"
  - "hermes-skills/workshop_fix.py"
  - "hermes-skills/workshop_coder.py"
  - "hermes-skills/workshop_push.py"
  - "skills/workshop-repo/SKILL.md"
  - "skills/workshop-build/SKILL.md"
  - "skills/workshop-fix/SKILL.md"
  - "tests/test_repo_registry.py"
  - "tests/phase-06/repo-smoke.bats"
autonomous: true
requirements:
  - REQ-ws-029
must_haves:
  truths:
    - "Repo registry lives at /srv/second-brain/_system/workshop-repos.json and auto-seeds caiobellizzi/test-workshop-sandbox when missing"
    - "/repo add, /repo create, and /repo remove require Telegram approval before mutating registry or GitHub state"
    - "/build requires --repo after Phase 6 ships; missing --repo shows usage plus active repos"
    - "/fix derives owner/name from the GitHub issue URL and rejects unknown or inactive repos with a /repo add hint"
    - "Final PR approval shows repo, base branch, feature branch, changed files, and diff summary"
  artifacts:
    - path: "workshop/repo_registry.py"
      provides: "Deterministic repo registry: canonicalization, atomic JSON read/write, bootstrap seeding, active repo validation, GitHub metadata mapping"
      contains: "def canonicalize_repo"
    - path: "hermes-skills/workshop_repo.py"
      provides: "Telegram /repo command backend for list/add/create/remove"
      contains: "def main"
    - path: "skills/workshop-repo/SKILL.md"
      provides: "Hermes skill wrapper for /repo commands with approval before mutations"
      contains: "/repo"
    - path: "hermes-skills/workshop_build.py"
      provides: "Repo-aware build parser and registry validation before background pipeline launch"
      contains: "--repo"
    - path: "hermes-skills/workshop_fix.py"
      provides: "Issue URL repo derivation and registry validation for /fix"
      contains: "issue_url"
    - path: "hermes-skills/workshop_coder.py"
      provides: "Clones the selected repo and returns Diff JSON with repo metadata"
      contains: "gh repo clone"
    - path: "hermes-skills/workshop_push.py"
      provides: "Pushes branches and opens PRs against the selected repo and default branch"
      contains: "--repo"
    - path: "tests/test_repo_registry.py"
      provides: "Unit tests for canonicalization, bootstrap, active/inactive handling, parser behavior, and permission checks"
    - path: "tests/phase-06/repo-smoke.bats"
      provides: "Dry-run smoke coverage for /repo, /build --repo, /fix repo derivation, coder clone payload, and push args"
  key_links:
    - from: "skills/workshop-repo/SKILL.md"
      to: "hermes-skills/workshop_repo.py"
      via: "terminal python3 /opt/ultra-workshop/hermes-skills/workshop_repo.py"
      pattern: "workshop_repo\\.py"
    - from: "hermes-skills/workshop_build.py"
      to: "workshop/repo_registry.py"
      via: "repo validation before pipeline launch"
      pattern: "validate_active_repo"
    - from: "hermes-skills/workshop_coder.py"
      to: "selected GitHub repo"
      via: "gh repo clone <owner/name> <workspace>"
      pattern: "gh repo clone"
    - from: "hermes-skills/workshop_push.py"
      to: "selected GitHub repo"
      via: "gh pr create --repo <owner/name> --base <default_branch>"
      pattern: "gh pr create"
---

# 06-01 — Telegram repo registry and repo-targeted builds

## Objective

Add Brain-backed repo selection so Telegram can create, register, list, disable, and target active repos instead of always using `caiobellizzi/test-workshop-sandbox`.

This plan is unlocked by owner amendments L17-A and L18-A, documented on 2026-05-24. It is a Phase 6 follow-up to the completed Phase 4 build/fix pipeline, not a reopening of Phase 4.

## UX Contract

Primary commands:

- `/repo list`
- `/repo add <repo>`
- `/repo create <repo>`
- `/repo remove <repo>`
- `/build --repo <repo> <task>`
- `/fix <issue-url>`

Repo shorthand is allowed: `my-app` means `caiobellizzi/my-app`.

After Phase 6 ships, `/build` requires `--repo`. If missing, it shows usage plus active repos. The sandbox flow remains available as `/build --repo test-workshop-sandbox <task>` because the registry auto-seeds `caiobellizzi/test-workshop-sandbox`.

## Interfaces And Data

- Store the canonical repo registry at `/srv/second-brain/_system/workshop-repos.json`.
- If the registry is missing, auto-seed it with `caiobellizzi/test-workshop-sandbox`.
- Registry entries include `full_name`, `active`, `default_branch`, `visibility`, `viewer_permission`, `source`, `created_at`, `updated_at`, and `last_used_at`.
- `/repo create` creates private repos with a README using `gh repo create <owner/name> --private --add-readme`.
- `/repo add` verifies the repo with `gh repo view` and requires `WRITE`, `MAINTAIN`, or `ADMIN`.
- `/repo remove` only marks the repo inactive; it never deletes GitHub repos.
- `/fix` derives `owner/name` from the GitHub issue URL and rejects unknown/inactive repos with a `/repo add` hint.

## Implementation

<tasks>

<task type="auto">
  <name>Task 1: Add deterministic repo registry module</name>
  <files>workshop/repo_registry.py, tests/test_repo_registry.py</files>
  <action>
Implement canonicalization, atomic JSON reads/writes, active repo validation, bootstrap seeding, and GitHub metadata mapping.

Rules:
- `my-app` canonicalizes to `caiobellizzi/my-app`.
- Registry writes are atomic via write-temp-then-rename.
- Missing registry auto-seeds `caiobellizzi/test-workshop-sandbox` as active.
- Unknown or inactive repos raise explicit validation errors that command handlers can render as Telegram usage hints.
- `remove` only flips `active` to false and updates `updated_at`.

Add unit tests for canonicalization, bootstrap, active/inactive handling, malformed registry handling, and permission mapping from mocked `gh repo view` JSON.
  </action>
</task>

<task type="auto">
  <name>Task 2: Add /repo command backend and Hermes skill</name>
  <files>hermes-skills/workshop_repo.py, skills/workshop-repo/SKILL.md</files>
  <action>
Create a Python backend for `list`, `add`, `create`, and `remove`. `list` is read-only. `add`, `create`, and `remove` must emit an approval envelope or use the established clarify pattern before mutating registry or GitHub state.

`/repo create` uses `gh repo create <owner/name> --private --add-readme`. `/repo add` uses `gh repo view` and accepts only WRITE, MAINTAIN, or ADMIN. The skill wrapper forwards command arguments to the Python backend and handles approval/rejection consistently with the existing HITL pattern.
  </action>
</task>

<task type="auto">
  <name>Task 3: Make /build repo-aware</name>
  <files>hermes-skills/workshop_build.py, skills/workshop-build/SKILL.md</files>
  <action>
Move command parsing into Python if any parsing remains in the skill wrapper. Require `/build --repo <repo> <task>` after Phase 6 ships. Missing `--repo` prints usage plus active repos and exits without launching the pipeline.

Before launching the background pipeline, validate the selected repo against the registry and attach `repo_full_name`, `default_branch`, and repo metadata to the pipeline payload. Include repo and base branch in the HITL approval payload.
  </action>
</task>

<task type="auto">
  <name>Task 4: Thread repo metadata through coder and push</name>
  <files>hermes-skills/workshop_coder.py, hermes-skills/workshop_push.py</files>
  <action>
Replace hardcoded sandbox constants with registry-provided repo and default branch.

Coder clones with `gh repo clone <owner/name> <workspace>` using `GH_TOKEN` from `GITHUB_PAT`. Push/PR creation uses `gh pr create --repo <owner/name> --base <default_branch>`. The final approval prompt shows repo, base branch, feature branch, changed files, and diff summary, not the full diff.
  </action>
</task>

<task type="auto">
  <name>Task 5: Make /fix derive and validate target repo</name>
  <files>hermes-skills/workshop_fix.py, skills/workshop-fix/SKILL.md</files>
  <action>
Parse `owner/name` from the GitHub issue URL. Reject unknown or inactive repos with a clear `/repo add <repo>` hint. For active repos, pass repo metadata through the same pipeline path used by `/build --repo`.
  </action>
</task>

<task type="auto">
  <name>Task 6: Add tests, dry-run smoke coverage, and live acceptance notes</name>
  <files>tests/test_repo_registry.py, tests/phase-06/repo-smoke.bats</files>
  <action>
Add dry-run smoke tests for `/repo`, `/build --repo`, `/fix` repo derivation, coder clone payload, and push args.

Live acceptance:
1. Deploy.
2. Run `/repo list`.
3. Create a private throwaway `caiobellizzi/uws-smoke-<date>` repo and approve it.
4. Run one real `/build --repo uws-smoke-<date> ...`.
5. Approve PR creation and confirm the PR targets the smoke repo.
6. Verify `/fix` with dry-run/tests only for this pass, not a second live full pipeline.
  </action>
</task>

</tasks>

## Assumptions

- Single allowed Telegram chat remains the trust boundary.
- GitHub auth uses `GITHUB_PAT` on the VPS with permissions expanded per L18-A.
- Default owner is `caiobellizzi`.
- No sticky active repo, no inline picker, no template repos, and no GitHub repo deletion in this version.
