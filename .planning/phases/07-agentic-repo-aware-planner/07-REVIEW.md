---
phase: 07-agentic-repo-aware-planner
reviewed: 2026-05-26T14:15:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - hermes-skills/aider_runner.py
  - hermes-skills/workshop_build.py
  - hermes-skills/workshop_push.py
  - scripts/hermes-skill-run.sh
  - workshop/doc_resolver.py
  - workshop/stage_policy.py
  - workshop/state.py
findings:
  critical: 3
  warning: 5
  info: 2
  total: 10
status: issues_found
---

# Phase 07: Code Review Report

**Reviewed:** 2026-05-26T14:15:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 07 adds clone-before-planner orchestration, 3-tier doc resolution, file-based arg
passing in `workshop_push.py`, and planner timeout bump. The core logic is structurally
sound and shell=False is consistently applied across all subprocess calls.

Three blockers were identified: path traversal via user-supplied `--task-id` into both
the ledger directory and the workspace clone directory; symlink escape from `rglob` in
`doc_resolver.py`; and YAML frontmatter injection in the ADR written back to Brain.
Five warnings cover unguarded resume behaviour, missing error boundary around
`_resolve_doc`, `GH_TOKEN` not checked before use, a bare `KeyError` from
`stage_policy()`, and an unquoted variable in the dry-run echo path of the shell script.

---

## Critical Issues

### CR-01: Path Traversal via `--task-id` into Ledger and Workspace Paths

**Files:**
- `workshop/ledger.py:13` (`task_dir` — used by `state.py`, `workshop_build.py`)
- `workshop/state.py:103` (`clone_repo_to_workspace`)

**Issue:** `task_id` is taken directly from the `--task-id` CLI argument
(`workshop_build.py:259`) and is embedded in filesystem paths without sanitization.
`ledger.task_dir` computes `LEDGER_BASE / task_id` (ledger.py:13), and
`clone_repo_to_workspace` computes
`Path("/tmp") / f"uws-workspace-{task_id}" / repo_name` (state.py:103).
A caller supplying `--task-id ../../../etc` resolves both paths outside their intended
roots:

```
LEDGER_BASE / "../../../etc"  =>  /home/uws/.ultra-workshop/tasks/../../../etc  =>  /etc
/tmp / "uws-workspace-../../../etc" / repo_name  =>  /etc/repo_name
```

`mkdir(parents=True, exist_ok=True)` would create directories under `/etc`; subsequent
writes (`state.json`, `progress_log.jsonl`, `task_ledger.md`) would land there too. The
`gh repo clone` call would clone into an attacker-chosen directory.

**Fix:** Validate `task_id` immediately after parsing — reject anything containing `/`,
`..`, or non-alphanumeric/hyphen/underscore characters. Apply the same check in
`ledger.task_dir` as a defence-in-depth guard:

```python
import re

_TASK_ID_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9\-_]{1,63}$')

def _validate_task_id(task_id: str) -> None:
    if not _TASK_ID_RE.match(task_id):
        raise ValueError(f"invalid task_id: {task_id!r}")
```

Call `_validate_task_id(task_id)` in `workshop_build.py` immediately after line 259,
and at the top of `ledger.task_dir`.

---

### CR-02: `rglob` Follows Symlinks — Doc Resolver Does Not Confine Results to Root

**File:** `workshop/doc_resolver.py:66-67`, `doc_resolver.py:73-74`

**Issue:** `Path.rglob()` follows symbolic links by default. A cloned repository (or the
vault) that contains a symlink named `prd.md` pointing to an arbitrary path outside the
workspace (e.g. `/etc/shadow`, `/home/uws/.ssh/id_rsa`) will cause `read_text()` to
return that file's contents. The `_validate_doc_name` guard only rejects path-traversal
in the *name* argument; it does not verify that the *resolved* candidate path stays inside
the search root. This is exploitable if an attacker can influence the contents of the
cloned repository.

**Fix:** After each candidate is found, verify it resolves inside the intended root before
reading:

```python
# Tier 1 — workspace (cloned repo)
if workspace_dir is not None:
    ws_path = Path(workspace_dir).resolve()
    if ws_path.exists():
        for candidate in ws_path.rglob(doc_name):
            resolved = candidate.resolve()
            try:
                resolved.relative_to(ws_path)
            except ValueError:
                continue          # symlink escapes root — skip
            return resolved.read_text(encoding="utf-8")
```

Apply the same pattern to Tier 2 vault resolution (lines 73-74).

---

### CR-03: YAML Frontmatter Injection in ADR Written to Brain

**File:** `hermes-skills/workshop_push.py:115-129`

**Issue:** `task_id`, `plan_goal`, and `diff_summary` are embedded directly into YAML
frontmatter and Markdown body via f-strings without escaping. A `task_id` or `plan_goal`
that contains newlines can inject arbitrary YAML keys into the frontmatter block, breaking
the document structure and potentially spoofing Brain metadata (e.g. injecting
`workshop.status: pwned` before the legitimate key). Demonstrated:

```
task_id = "real-id\nworkshop.status: pwned\nfoo"
# Produces:
# workshop.task_id: real-id
# workshop.status: pwned       <-- injected
# foo
# workshop.status: done        <-- real value, shadowed
```

`plan_goal` read from a file (`--plan-goal-file`) amplifies this: an attacker who
controls the file contents can inject a closing `---` line, ending the frontmatter block
early and corrupting the document.

**Fix:** Strip or reject newlines from fields embedded in frontmatter. At minimum, escape
the values:

```python
def _yaml_scalar(value: str) -> str:
    """Escape a string for safe embedding in a YAML block scalar."""
    # Simplest safe approach: replace newlines with spaces for single-line fields
    return value.replace("\n", " ").replace("\r", "")

# Then:
f"workshop.task_id: {_yaml_scalar(task_id)}\n"
f"workshop.status: done\n"
# etc.
```

For `diff_summary` (multi-line by nature), use a YAML literal block scalar (`|`) or
place it only in the Markdown body section below the closing `---`.

---

## Warnings

### WR-01: Stale `workspace_dir` on Resume — No Existence Check

**File:** `hermes-skills/workshop_build.py:322`

**Issue:** On resume (`--resume --task-id <id>`), `state["workspace_dir"]` is loaded from
`state.json`. The clone step is skipped because `state.get("workspace_dir")` is truthy
(line 322). If the workspace was under `/tmp` and was cleaned up between runs, all
downstream stages receive a `workspace_dir` that points to a nonexistent directory.
The coder and aider stages will fail with opaque errors rather than a clear "workspace
gone, re-clone required" message.

**Fix:** After loading state on resume, check that the workspace still exists and re-clone
if missing:

```python
if not state.get("workspace_dir") or not Path(state["workspace_dir"]).exists():
    clone_repo_to_workspace(state, repo=repo_full_name)
    save_task_state(state)
```

---

### WR-02: `_resolve_doc` Called Without Error Boundary — Can Abort Pipeline

**File:** `hermes-skills/workshop_build.py:394`

**Issue:** `_resolve_doc(_doc_name, ...)` is called without a `try/except`. The function
can raise:
- `ValueError` from `_validate_doc_name` (unlikely given the upstream regex, but possible
  if the guard logic changes).
- `PermissionError` from `rglob` in Tier 1 (only Tier 2 has an `OSError` catch).
- Any exception from `read_text()` if a matched file is unreadable.

An unhandled exception here aborts the entire pipeline before the planner stage runs.

**Fix:** Wrap the call:

```python
if _doc_name:
    try:
        _reference_doc = _resolve_doc(_doc_name, state.get("workspace_dir") or "", _vault_path) or ""
    except Exception as exc:
        print(f"[workshop] WARNING: doc resolve failed for {_doc_name!r}: {exc}", flush=True)
        _reference_doc = ""
```

Also add exception handling around the Tier 1 `rglob` loop in `doc_resolver.py` (lines 66-67)
to match the Tier 2 pattern.

---

### WR-03: `GH_TOKEN` Set to Empty String — No Early Validation

**File:** `hermes-skills/workshop_push.py:79`, `workshop_push.py:104`; `workshop/state.py:109`

**Issue:** `os.environ.get("GITHUB_PAT", "")` returns an empty string if the variable is
unset, and that empty string is passed as `GH_TOKEN` into both `git push` and `gh pr
create`. Both commands will fail with authentication errors, but the failure is reported
only after the subprocess exits, giving no actionable diagnostic at startup.
`clone_repo_to_workspace` in `state.py` has the same pattern.

**Fix:** Add an early check in `workshop_push.main()` and in `clone_repo_to_workspace`:

```python
github_pat = os.environ.get("GITHUB_PAT", "")
if not github_pat:
    print("[workshop_push] ERROR: GITHUB_PAT env var is not set", file=sys.stderr, flush=True)
    sys.exit(1)
```

---

### WR-04: `stage_policy()` Raises `KeyError` for Unknown Stage Names

**File:** `workshop/stage_policy.py:23-24`

**Issue:** `stage_policy(stage)` performs `STAGE_POLICIES[stage]` without a `.get()`
fallback. `STAGE_POLICIES` has five entries (`triage`, `requirements`, `planner`, `coder`,
`reviewer`). The `_STAGE_INDEX` in `workshop_build.py` has a sixth entry, `"approval"`.
Any future caller, state override, or test that passes an unlisted stage name gets an
unformatted `KeyError` with no context. The exception will surface deep in
`_stage_policy_payload`, making the root cause hard to diagnose.

**Fix:**

```python
def stage_policy(stage: str) -> StagePolicy:
    try:
        return STAGE_POLICIES[stage]
    except KeyError:
        raise KeyError(f"no policy defined for stage {stage!r}; known stages: {list(STAGE_POLICIES)}")
```

---

### WR-05: Unquoted `$QUERY` in Dry-Run `echo` Lines — Output Corruption

**File:** `scripts/hermes-skill-run.sh:54`, `57`, `60`

**Issue:** The dry-run diagnostic `echo` lines for `requirements-specialist`,
`reviewer-specialist`, and `coder-specialist` expand `${QUERY}` without quoting:

```bash
echo "[dry-run] would run: python3 ... ${QUERY}"
```

If `QUERY` contains shell globbing characters (`*`, `?`), backslashes, or special
sequences, the shell will expand them at `echo` time, producing misleading or corrupted
diagnostic output. The planner-specialist and catch-all dry-run lines (lines 51, 63) use
`'${QUERY}'` (single-quoted), which is consistent and safe.

**Fix:** Use the same single-quoting pattern:

```bash
echo "[dry-run] would run: python3 /opt/ultra-workshop/hermes-skills/workshop_requirements.py '${QUERY}'"
```

(This is diagnostic-only — the production `exec` paths at lines 91-93 use `"$@"` which
is correct.)

---

## Info

### IN-01: `_read_text_arg` Has No Path Restriction — Arbitrary File Read

**File:** `hermes-skills/workshop_push.py:39-46`

**Issue:** `_read_text_arg` reads any file path passed via `--plan-goal-file` or
`--diff-summary-file` without restricting it to a safe directory. Since `workshop_push.py`
is a CLI tool invoked by a SKILL.md body, the calling SKILL generates the paths and they
are not attacker-controlled in the current architecture. However, if the HITL payload or
state were ever to carry these paths from an external source, this would become an
arbitrary file read. The function provides no size cap either.

**Suggestion:** Document that these paths must be temp files under a trusted directory
(e.g. `/tmp/uws-*`), or add an assertion:

```python
def _read_text_arg(value: str, file_path: str, *, label: str) -> str:
    if not file_path:
        return value
    p = Path(file_path).resolve()
    # Assert file is under a trusted root (optional hardening)
    try:
        p.relative_to(Path("/tmp"))
    except ValueError:
        print(f"[workshop_push] ERROR: {label} file outside /tmp: {p}", flush=True)
        sys.exit(1)
    try:
        return p.read_text(encoding="utf-8").rstrip("\n")
    except OSError as exc:
        print(f"[workshop_push] ERROR: {label} file error: {exc}", flush=True)
        sys.exit(1)
```

---

### IN-02: `_extract_doc_reference` Returns First Match Only — Silent Ambiguity

**File:** `hermes-skills/workshop_build.py:162-165`

**Issue:** `_extract_doc_reference` returns the first `.md` filename found in the goal
string. Goals that mention multiple documents (e.g. "implement prd.md referencing
CHANGELOG.md") silently use only the first match. The planner receives only one
`reference_doc` but the goal text mentions others, creating a subtle mismatch with no
warning.

**Suggestion:** Either log a warning when more than one `.md` filename is found, or extend
`reference_doc` to a list of resolved documents and update the planner query schema
accordingly. At minimum, document the single-match behaviour in the function docstring.

---

_Reviewed: 2026-05-26T14:15:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
