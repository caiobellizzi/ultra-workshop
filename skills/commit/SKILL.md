---
name: commit
description: Commit and push git changes. Use when the user asks to commit, push, "commit and push", "save my changes", "push to remote", "git commit", "send changes", "sync my code", or any variation of committing/pushing code to the remote branch using conventional commits.
version: 1.0.0
author: ultra-workshop (ported from Claude Code skill)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [git, commit, workflow]
---

# Commit & Push

Commit and push changes on the current branch using Conventional Commits.

## Workflow

Execute the steps below without spending time on unnecessary exploration:

1. **Status**: `terminal git status` to see modified/untracked files
2. **Diff**: `terminal git diff --stat` + `terminal git diff --cached --stat` to understand the scope of changes
3. **Stage**: `terminal git add` on relevant files (prefer specific files; avoid `git add .` if there are sensitive files)
4. **Commit**: write a Conventional Commit message and commit
5. **Push**: `terminal git push` to the current branch (use `git push -u origin HEAD` if the branch has no upstream)

## Conventional Commits

Format: `<type>(<scope>): <short description>`

Types:
- `feat` — new feature
- `fix` — bug fix
- `refactor` — restructuring without behavior change
- `docs` — documentation
- `chore` — maintenance tasks, deps, configs
- `test` — add or fix tests
- `style` — formatting, lint (no logic change)
- `perf` — performance improvement
- `ci` — CI/CD changes

Scope is optional but recommended (e.g. `feat(gateway): add health endpoint`).

## Rules

- **Do not group unrelated changes** in the same commit. If the diff has distinct changes, make separate commits.
- **BLUF message** (Bottom Line Up Front): the first line must explain WHAT changed, not HOW.
- **Do not commit secrets** (.env, credentials, tokens). If detected, warn the user.
- **Use heredoc** for multi-line messages:
  ```bash
  git commit -m "$(cat <<'EOF'
  feat(api): add user authentication endpoint

  - JWT-based auth with refresh tokens
  - Rate limiting on login attempts
  EOF
  )"
  ```
- If push fails due to divergence, do `git pull --rebase` and try again.
- If pre-commit hooks fail, fix the problem and make a NEW commit (never `--amend` automatically).

## Dry-run behavior
If the trigger contains `--dry-run`, print the steps that would execute and the arguments extracted, then stop without taking any action.
