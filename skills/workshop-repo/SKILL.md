---
name: workshop-repo
description: "Manage workshop target repos: /repo list, add, create, remove."
version: 1.0.0
author: ultra-workshop (local impl)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [workshop, repo, registry, github]
---

## Workshop Repo

Manages the active repo registry used by `/build --repo` and `/fix`.

## Behavior

### A. `/repo list`

Run:

```
terminal(command="python3 /opt/ultra-workshop/hermes-skills/workshop_repo.py list")
```

Return stdout to the chat.

### B. `/repo add <repo>`

1. Run:
   ```
   terminal(command="python3 /opt/ultra-workshop/hermes-skills/workshop_repo.py add \"<repo>\"")
   ```
2. If exit code is `2`, parse the last stdout line as JSON and call `clarify` with `summary`.
3. On approval, run:
   ```
   terminal(command="python3 /opt/ultra-workshop/hermes-skills/workshop_repo.py add \"<repo>\" --approved")
   ```
4. On rejection, reply `Repo registration rejected for <repo>.`

### C. `/repo create <repo>`

Same approval pattern as add, then:

```
terminal(command="python3 /opt/ultra-workshop/hermes-skills/workshop_repo.py create \"<repo>\" --approved")
```

The backend creates a private repo with README using `gh repo create <owner/name> --private --add-readme`, then registers the repo.

### D. `/repo remove <repo>`

Same approval pattern as add, then:

```
terminal(command="python3 /opt/ultra-workshop/hermes-skills/workshop_repo.py remove \"<repo>\" --approved")
```

Removal only marks the registry entry inactive. It never deletes a GitHub repository.

## Approval token

The canonical approval flag is `--approved`. Do **not** use `workshop_continue.py`
here — that script belongs to the build/fix pipeline. If you instead pass the
HITL button selection as `--choice <token>`, `workshop_repo.py` tolerates it:
`1`/`yes`/`approved` count as approval, `2`/`no`/`rejected` cleanly cancel. Prefer
`--approved` for clarity.

## Dry-run

If `--dry-run` appears in the trigger, pass it through to `workshop_repo.py`. No registry or GitHub mutation occurs.
