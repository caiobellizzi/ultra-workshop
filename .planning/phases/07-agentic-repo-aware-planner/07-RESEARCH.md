# Phase 7: Agentic Repo-Aware Planner — Research

**Researched:** 2026-05-25
**Domain:** Python subprocess orchestration, LLM planner upgrade, git workspace management, doc resolution
**Confidence:** HIGH (all claims grounded in actual codebase files with line references)

---

## Summary

Phase 7 replaces the blind keyword-heuristic planner (`workshop/planner.py`) with an
LLM-driven planner that reads the cloned workspace before producing `Plan.affected_files`.
The pipeline already clones the repo inside `workshop_coder.py` during the coder stage;
Phase 7 moves that clone earlier — to before the planner stage — and gives the planner
read-only file tools scoped to `workspace_dir`.

The architecture is entirely brownfield. Every subsystem the phase touches already exists
and is working in production. The changes are surgical:

1. Clone into a deterministic path before the planner runs and persist `workspace_dir` in
   `state.json`.
2. Convert `workshop_planner.py` from a pure-Python deterministic script to a
   `hermes chat` LLM call (matching how triage/requirements are already invoked) with
   three read-only tools scoped to `workspace_dir`.
3. Add a doc-resolution helper (3-tier: repo-first, vault-grep, Brain HTTP) that injects
   the referenced design doc into the planner query.
4. Extend the reviewer's "changed files outside the plan" check — which already exists and
   is correct — to benefit from accurate `affected_files` rather than keyword guesses.

The coder's clone step (`workshop_coder.py:302–308`) must be removed or short-circuited
when `workspace_dir` is already present in the query. The `workspace_dir` key must be
added to `new_task_state()` in `workshop/state.py`.

**Primary recommendation:** Add `workspace_dir` to `state.json`, clone once in
`workshop_build.py` between registry validation and the planner stage, pass
`workspace_dir` to the planner query, and route `planner-specialist` through
`hermes chat` with `read_file`/`list_files`/`grep_files` allowed and all write/web/exec
forbidden — exactly mirroring how `triage-specialist` and `requirements-specialist` are
already routed.

---

## User Constraints

*(No CONTEXT.md exists for this phase — constraints come from ROADMAP.md locked decisions.)*

### Locked Decisions (from ROADMAP.md Phase 7 success criteria)

1. Repo cloned BEFORE the planner stage; single `workspace_dir` shared by planner (read),
   coder (write), reviewer (verify); persisted in `state.json`; resumable after restart.
2. `planner-specialist` runs as LLM on the `orchestrator` model (L25) via `hermes chat`,
   with read-only tools (`read_file`/`list_files`/`grep_files`) scoped to `workspace_dir`;
   write/web/code-exec forbidden.
3. `/build --repo <repo> "<task referencing prd.md>"` resolves the referenced doc
   deterministically — repo-first, vault-grep second, Brain HTTP semantic third (degraded
   while Brain's Groq issue is open) — and injects content into planner context.
4. `affected_files` must match what coder actually changes; reviewer "changed files outside
   plan" false-blocks eliminated.
5. Subprocess + `HERMES_HOME` isolation, `state.json` resumability, `exit(2)` HITL
   unchanged; no `delegate_task`; reviewer deterministic safety gates remain authoritative.
6. Phase-4 and Phase-6 bats + pytest suites stay green; planner timeout accommodates repo
   I/O without regressing latency.

### Claude's Discretion
- Exact clone directory path scheme (e.g. `/tmp/uws-workspace-{task_id}/`)
- Tool-call format for `read_file`/`list_files`/`grep_files` in the SKILL.md body
- Doc-resolution function name and module location
- Whether clone step lives in `workshop_build.py` or a new `workshop/workspace.py` module
- Timeout value for the LLM planner stage (must be >= current 300s)

### Deferred (OUT OF SCOPE for Phase 7)
- `delegate_task` — confirmed NOT_SUPPORTED (Phase 4 Wave 0 finding, LOCKED)
- LangGraph — reserved per L22 for a hypothetical Phase 2 upgrade
- Full 2-LLM-call cost verification in Brain curator

---

<phase_requirements>
## Phase Requirements

Phase 7 requirements will be minted during planning (per ROADMAP.md: "TBD — new REQ ids
assigned during planning"). Research maps the success criteria to implementation areas:

| Success Criterion | Implementation Area | Research Support |
|---|---|---|
| SC-1: Clone before planner, workspace_dir in state.json | workshop_build.py + state.py | §Clone Flow, §State Machine |
| SC-2: planner-specialist via hermes chat with read-only tools | hermes-skill-run.sh + SKILL.md | §Hermes Transport |
| SC-3: Doc resolution 3-tier | New workshop/doc_resolver.py | §Doc Resolution |
| SC-4: affected_files accuracy, reviewer false-blocks eliminated | workshop/planner.py replacement | §Planner Replacement |
| SC-5: No regressions to subprocess/HITL/state machine | All existing contracts | §Architecture Invariants |
| SC-6: Test suites stay green, timeout accommodates repo I/O | stage_policy.py | §Timeouts |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Repo clone before planner | workshop_build.py (orchestrator) | workshop/workspace.py (helper) | The build script owns stage sequencing; clone is a pre-planner orchestration step |
| workspace_dir persistence | workshop/state.py | workshop_build.py (writes) | State module owns all `state.json` fields; build script hydrates it |
| Planner LLM invocation | hermes-skill-run.sh (routing) | skills/planner-specialist/SKILL.md (prompt) | All LLM calls go through hermes-skill-run.sh; SKILL.md defines tools and prompt |
| Read-only repo tools for planner | Hermes tool allowlist in SKILL.md | HERMES_HOME specialist config | Hermes tool-permission model is per-skill via SKILL.md tool declarations |
| Doc resolution (prd.md) | workshop/doc_resolver.py (new) | brain_http.py (Brain tier) | Deterministic resolution logic belongs in the Python layer, not in the LLM prompt |
| Reviewer "outside plan" gate | workshop/reviewer.py (deterministic) | — | Already implemented; accuracy improves when affected_files are correct |
| Timeout policy | workshop/stage_policy.py | workshop_build.py | STAGE_POLICIES dict is the single source of timeout truth |

---

## Standard Stack

### Core (all already present in the repo — no new installs)

| Component | Location | Purpose | Notes |
|---|---|---|---|
| `workshop/planner.py` | Local | REPLACE: current keyword heuristic | Phase 7 replaces `infer_affected_files()` with LLM output |
| `hermes-skills/workshop_planner.py` | Local | CLI entry point for planner-specialist | Phase 7 converts from Python script to `hermes chat` passthrough |
| `scripts/hermes-skill-run.sh` | Local | Subprocess router for all specialists | Currently short-circuits planner to Python; Phase 7 removes that branch |
| `workshop/state.py` | Local | state.json schema + read/write | Add `workspace_dir` field to `new_task_state()` |
| `workshop/stage_policy.py` | Local | Timeout + retry policy per stage | Update planner timeout for LLM + repo I/O |
| `hermes-skills/brain_http.py` | Local | Brain HTTP client | Used for Brain tier in doc resolution |
| `hermes-skills/workshop_coder.py` | Local | Clone step to skip when workspace present | Already clones at line 302; short-circuit if workspace exists |

### New modules to create

| Module | Purpose |
|---|---|
| `workshop/doc_resolver.py` | 3-tier doc resolution: repo-first, vault-grep, Brain HTTP |
| `skills/planner-specialist/SKILL.md` | Updated with `read_file`/`list_files`/`grep_files` tools and LLM-planner prompt |

### No new packages needed

The entire phase uses existing Python stdlib, `subprocess`, `pathlib`, `pydantic`, and
the already-installed `httpx` (used in `brain_http.py`). [VERIFIED: codebase grep]

---

## Architecture Patterns

### Current Planner Architecture (to be replaced)

The current planner is a **deterministic keyword-heuristic** Python script:

**File:** `workshop/planner.py`
**Entry point:** `hermes-skills/workshop_planner.py` via `hermes-skill-run.sh`

The current `infer_affected_files()` (planner.py:95–111) works as follows:
1. Runs `_extract_file_paths(goal)` — a regex (`_FILE_RE`) matching extensions like
   `.py|.js|.ts|.md|.json` in the goal string.
2. If no paths found, calls `_default_files_for_goal(lower_goal)` — keyword matching:
   - "readme" → `["README.md"]`
   - "endpoint|api|route|server|fastapi|flask" → `["app.py"]`
   - "agent|orchestration|harness|workflow|pipeline" → `["agent_orchestration.py", "tests/test_agent_orchestration.py", "README.md"]`
   - "function|utility|utils|helper|fibonacci" → `["utils.py"]`
   - "cli|command" → `["cli.py"]`
   - default → `["README.md"]`
3. Adds test files for any Python source files if "test" appears in goal or task_type is "FIX".
4. Deduplicates and caps at 6 files.

**This is the exact mechanism** that causes `affected_files` to diverge from reality when
the task uses non-standard filenames or deeply nested paths. `[VERIFIED: workshop/planner.py:95–141]`

The `hermes-skill-run.sh` short-circuits planner to the Python script:

```bash
# hermes-skill-run.sh:80–96
if [ "$SKILL" = "requirements-specialist" ] || [ "$SKILL" = "planner-specialist" ] || ...; then
  case "$SKILL" in
    planner-specialist)  SCRIPT_PATH="/opt/ultra-workshop/hermes-skills/workshop_planner.py" ;;
    ...
  esac
  exec "$PYTHON_BIN" "$SCRIPT_PATH" "$@"
fi
```

`[VERIFIED: scripts/hermes-skill-run.sh:80–96]`

### Current State Machine + Clone Flow

**State file location:** `~/.ultra-workshop/tasks/<task_id>/state.json`
(via `workshop/ledger.py:task_dir(task_id)`)

**Current `state.json` schema** (`workshop/state.py:26–57`):
```python
{
    "schema_version": 1,
    "task_id": ...,
    "goal": ...,
    "repo": ...,           # repo shorthand arg
    "repo_entry": {},      # full registry entry dict
    "repo_full_name": "",  # "owner/name"
    "default_branch": "",
    "session_id": ...,
    "chat_id": ...,
    "status": "running",
    "next_stage": "triage",
    "attempts": {},
    "clarifications": [],
    "hitl_responses": [],
    "recovery_decisions": [],
    "scope_instruction": "",
    "stage_overrides": {},
    "stages": {},          # keyed by stage name, stores model_dump() output
    "approval_payload": {},
    "timeout_payload": {},
    "created_at": ...,
    "updated_at": ...,
}
```

**`workspace_dir` is NOT in `new_task_state()` today.** It only lives in `diff.workspace_dir`
(a field on the `Diff` Pydantic model) and is accessed from `stages["diff"]["workspace_dir"]`
after the coder runs. `[VERIFIED: workshop/state.py:26–57; workshop/types.py:Diff model]`

**Current clone location:** `workshop_coder.py:302–308` — clone happens inside the coder
stage, not before the planner:
```python
# workshop_coder.py:290–308
workspace_dir = query.get("workspace_dir") or f"/tmp/uws-sandbox-{task_id}/"
workspace = Path(workspace_dir)
workspace.mkdir(parents=True, exist_ok=True)
if not (workspace / ".git").exists():
    clone = subprocess.run(
        ["gh", "repo", "clone", repo_full_name, str(workspace)], ...
    )
```
`[VERIFIED: hermes-skills/workshop_coder.py:288–313]`

**What must change for SC-1:**
- `new_task_state()` in `workshop/state.py` must gain a `"workspace_dir": ""` field.
- `workshop_build.py` must clone the repo to a deterministic path AFTER registry
  validation (line ~300) but BEFORE the planner stage call (line ~361).
- The clone path must be saved to `state["workspace_dir"]` and `save_task_state()` called.
- The planner query JSON must include `"workspace_dir": state["workspace_dir"]`.
- `workshop_coder.py` must short-circuit its clone step when `workspace / ".git"` already
  exists (it already does — line 303: `if not (workspace / ".git").exists(): clone...`).
  No change needed there; passing the same `workspace_dir` is sufficient.

### The hermes-skill-run.sh Transport Pattern

All specialists are invoked via:
```bash
run_specialist(skill_name, query_json, output_schema, timeout=...) 
  → subprocess.run(["bash", HERMES_SKILL_RUN, skill_name, "--query", query_json], ...)
  → hermes-skill-run.sh <skill_name> --query <json>
```
`[VERIFIED: workshop/orchestrator.py:run_specialist(); scripts/hermes-skill-run.sh]`

For LLM-backed specialists (triage, requirements), `hermes-skill-run.sh` calls:
```bash
exec env HERMES_HOME="$SPECIALIST_HOME" ... \
  "$HERMES_BIN" chat --skills "$SKILL" --query "$QUERY" -Q --max-turns "$MAX_TURNS" --yolo
```
`[VERIFIED: hermes-skill-run.sh:103–110]`

**HERMES_HOME isolation per specialist:**
```bash
case "$SKILL" in
  triage-specialist)   HOME_DIR=specialist-home-private ;;
  requirements-specialist) HOME_DIR=specialist-home-orchestrator ;;
  planner-specialist)  HOME_DIR=specialist-home-orchestrator ;;
  reviewer-specialist) HOME_DIR=specialist-home-research ;;
  coder-specialist)    HOME_DIR=specialist-home-orchestrator ;;
esac
SPECIALIST_HOME="${SPECIALIST_HOME_OVERRIDE:-/opt/ultra-workshop/${HOME_DIR}}"
```
`[VERIFIED: hermes-skill-run.sh:27–45]`

**Tool scoping:** In Hermes, tools available to a skill are declared in the SKILL.md
frontmatter and/or `metadata.hermes.tools` section. The current
`planner-specialist/SKILL.md` **explicitly forbids** read-only tools:
```markdown
**Forbidden tools** (do NOT invoke any of these):
- `search_files`, `read_file`, `list_files`, `grep_files` — do NOT explore the codebase
- `code_execution`, `web_search`, `web_extract`, `web_fetch`, `browser_*`
```
`[VERIFIED: skills/planner-specialist/SKILL.md]`

**For Phase 7**, the SKILL.md body must:
1. Remove the `read_file`/`list_files`/`grep_files` prohibition.
2. Declare those three tools as allowed with `workspace_dir` as the root scope.
3. Keep write/code-exec/web tools forbidden.
4. Replace the `terminal(python3 workshop_planner.py ...)` pattern with direct LLM
   reasoning using the read tools.

The model used is `orchestrator` (LM Studio `google/gemma-4-e4b` primary, `cloud-sonnet`
fallback, 300s timeout). `[VERIFIED: deploy/litellm/config.yaml; hermes-skill-run.sh HOME_DIR]`

**Exact analog to mirror:** `requirements-specialist` already runs via `hermes chat` with
`HOME_DIR=specialist-home-orchestrator` and `MAX_TURNS=6`. Phase 7 planner should use
`MAX_TURNS=8` to `MAX_TURNS=12` (current value is already 8).
`[VERIFIED: hermes-skill-run.sh:30–34]`

### The Reviewer "Changed Files Outside Plan" Gate

**File:** `workshop/reviewer.py:110–117`

```python
if planned:
    extras = sorted(set(changed_paths) - planned)
    if extras:
        issues.append(
            "Changed files outside the plan: "
            + ", ".join(extras[:10])
            + (" ..." if len(extras) > 10 else "")
        )
```
`[VERIFIED: workshop/reviewer.py:110–117]`

`planned` is built from:
```python
def _planned_files(plan: Plan) -> set[str]:
    files = set(plan.affected_files)
    for step in plan.steps:
        files.update(step.files)
    return {path for path in files if path}
```
`[VERIFIED: workshop/reviewer.py:32–36]`

**How Phase 7 eliminates false-blocks:** When the LLM planner reads the actual repo and
produces `affected_files = ["src/workshop/orchestrator.py", "tests/test_orchestrator.py"]`
instead of the heuristic guess `["agent_orchestration.py", "README.md"]`, the set
subtraction `set(changed_paths) - planned` becomes empty for any coder that stays within
the plan. No code change needed to reviewer.py for SC-4.

The `_path_issue()` and `_SECRET_RE` gates are independent of plan accuracy and remain
authoritative. `[VERIFIED: workshop/reviewer.py:39–52, 141]`

### Doc Resolution Architecture (3-tier)

**Tier 1 — Repo-first:** Check `workspace_dir / referenced_doc_name` (e.g. `prd.md` at
workspace root or first-depth scan). Already available since workspace is cloned before
the planner runs.

**Tier 2 — Vault grep:** The vault lives at `/srv/second-brain` on VPS, accessible to the
`uws` user. The Mac vault path is `~/Documents/second-brain`. The registry path is
`DEFAULT_REGISTRY_PATH = Path("/srv/second-brain/_system/workshop-repos.json")`, confirming
vault access from the worker process. `[VERIFIED: workshop/repo_registry.py:8–9]`

Vault grep: `grep -r --include="*.md" -l "<doc_name>" /srv/second-brain/` — find the
note, read its content.

**Tier 3 — Brain HTTP semantic:** Uses `brain_http.call_agent("query", doc_name)`.
**Known degradation:** Brain's query agent returns `status: "ERROR"` due to a Groq
structured-output conflict in LiteLLM. `brain_http.py` already handles this gracefully:
```python
if data.get("status") == "ERROR":
    print(f"Brain error: {data.get('content', 'unknown')}", file=sys.stderr)
# does NOT sys.exit(1) — callers need run_id regardless
```
`[VERIFIED: hermes-skills/brain_http.py:call_agent()]`

Resolution should be **non-blocking** at each tier with graceful fallback to next tier.
Timeout for Brain call: 60s (same as `brain_http.DEFAULT_TIMEOUT`).

**Recommended doc_resolver.py design:**
```python
def resolve_doc(doc_name: str, workspace_dir: str, vault_path: str) -> str | None:
    # Tier 1: repo
    for candidate in Path(workspace_dir).rglob(doc_name):
        return candidate.read_text()
    # Tier 2: vault grep
    for f in Path(vault_path).rglob(doc_name):
        return f.read_text()
    # Tier 3: Brain HTTP (degraded — may return status:ERROR but content still present)
    try:
        result = call_agent("query", f"find document: {doc_name}")
        return result.get("content") or None
    except Exception:
        return None
```

### Recommended Project Structure (new files only)

```
workshop/
├── doc_resolver.py          # 3-tier doc resolution (new)
├── state.py                 # add workspace_dir field (modify)
├── stage_policy.py          # update planner timeout (modify)
hermes-skills/
├── workshop_build.py        # add clone-before-planner step (modify)
├── workshop_planner.py      # convert to hermes-chat passthrough (modify)
skills/
├── planner-specialist/
│   └── SKILL.md             # add read tools, LLM prompt (modify)
tests/
├── phase-07/
│   ├── __init__.py
│   ├── test_doc_resolver.py   # unit tests for 3-tier resolution
│   ├── test_planner_llm.py    # integration: planner with workspace tools
│   └── planner-smoke.bats     # dry-run smoke test on VPS
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Process isolation for LLM call | Custom process manager | `hermes chat` via `hermes-skill-run.sh` | Already handles HERMES_HOME isolation, `--yolo`, turn limits, timeout |
| JSON extraction from LLM output | Custom parser | `orchestrator._extract_json()` (already in prod) | Handles `<think>` blocks, fenced JSON, brace-matching; battle-tested |
| Schema validation of planner output | Manual dict checks | `Plan.model_validate(payload)` (Pydantic) | Already used for every specialist; ClarificationRequest detection built in |
| State persistence | Custom file format | `save_task_state(state)` with atomic tmp→replace | Already handles concurrent writes, corruption recovery |
| Per-file git diff | Custom diff parser | `git diff --name-only -z <ref>` + `git diff <ref> -- <file>` (used in `_changed_paths_since`) | Already in prod in `workshop_coder.py` |
| Brain HTTP client | Custom httpx wrapper | `brain_http.call_agent()` | Already handles multipart/form-data requirement and status:ERROR graceful handling |

---

## Common Pitfalls

### Pitfall 1: workspace_dir not in state.json → Resume breaks after planner
**What goes wrong:** If `workspace_dir` is computed in `workshop_build.py` but not saved
to `state.json`, a restart between clone and coder recomputes a new path, losing the
pre-cloned workspace and re-cloning into a different directory.
**How to avoid:** Add `"workspace_dir": ""` to `new_task_state()` in `state.py`. Write
`state["workspace_dir"] = workspace_dir` and call `save_task_state(state)` immediately
after clone succeeds. The coder query already passes `workspace_dir` from the state.
**Warning signs:** `tests/phase-07/planner-smoke.bats` resume test fails; planner stage
sees empty workspace on retry.

### Pitfall 2: Coder re-clones into same path and loses branch state
**What goes wrong:** The coder clones because `workspace_dir` arrives as `""` or wrong.
On retry the `checkout -B workshop/<task_id>` resets from `default_branch`, which is
correct — but only if the same workspace is used (branch tracking). A second clone breaks
branch continuity.
**How to avoid:** Pass `state["workspace_dir"]` from the build script's state to the
coder query at line 410 of `workshop_build.py` (currently uses `diff.workspace_dir if diff else ""`).
After Phase 7, use `state.get("workspace_dir") or ""` as the fallback when `diff` is None.
**Warning signs:** git clone error "destination path already exists" or reviewer seeing
an empty diff on retry.

### Pitfall 3: LLM planner times out because repo is large
**What goes wrong:** The planner LLM call uses read-tools to walk the repo.
A large repo with hundreds of files exhausts the 300s timeout.
**How to avoid:** In `SKILL.md`, instruct the planner to limit `list_files` to depth 2
and `grep_files` to specific subdirectories relevant to the task. Increase planner timeout
in `stage_policy.py` to 480s or 600s to accommodate I/O.
Current planner timeout: 300s (`STAGE_POLICIES["planner"] = StagePolicy(timeout=300)`).
`[VERIFIED: workshop/stage_policy.py]`
**Warning signs:** `subprocess.TimeoutExpired` at planner stage; `StageTimeoutForHITL`
raised if `hitl_on_timeout` is set for planner.

### Pitfall 4: hermes-skill-run.sh bats test breaks because short-circuit is removed
**What goes wrong:** `tests/phase-04/model-matrix-smoke.bats` asserts:
```bash
[[ "$output" == *"workshop_planner.py"* ]]
[[ "$output" == *"deterministic"* ]]
```
If the short-circuit is removed from `hermes-skill-run.sh`, these assertions fail.
**How to avoid:** Update `model-matrix-smoke.bats` in the same wave as the
`hermes-skill-run.sh` change. The new assertion should check that planner routes through
`hermes chat` with `--max-turns` and the `specialist-home-orchestrator` HERMES_HOME.
**Warning signs:** CI bats suite returns non-zero after hermes-skill-run.sh edit.

### Pitfall 5: Doc resolution vault path differs between VPS and Mac
**What goes wrong:** `VAULT_VPS_PATH` on VPS is `/srv/second-brain`; Mac vault path is
`~/Documents/second-brain`. If `doc_resolver.py` hardcodes either, it breaks on the other.
**How to avoid:** Read `VAULT_VPS_PATH` env var with fallback to `/srv/second-brain`.
`[VERIFIED: repo_registry.py:DEFAULT_REGISTRY_PATH]`
**Warning signs:** Tier-2 vault grep returns None on VPS despite the doc existing.

### Pitfall 6: Plan JSON schema not updated for workspace tools output
**What goes wrong:** The LLM planner, using read tools, may produce a richer
`affected_files` list with paths like `src/workshop/orchestrator.py`. The existing
`Plan` Pydantic schema accepts any `list[str]` — no change needed. But the SKILL.md
must still emit exactly the schema fields (`goal`, `steps`, `affected_files`).
**How to avoid:** Keep the output schema section in the updated SKILL.md identical to
the current one. No changes to `workshop/types.py:Plan`.

### Pitfall 7: `hermes-skill-run.sh` dry-run output changes break bats assertions
**What goes wrong:** The current dry-run output for planner is:
```
[dry-run] would run: python3 /opt/ultra-workshop/hermes-skills/workshop_planner.py ...
[dry-run] planner-specialist is deterministic; no HERMES_HOME
```
After Phase 7 it will route through `hermes chat` and emit:
```
[dry-run] would run: hermes chat --skills planner-specialist ...
[dry-run] HERMES_HOME=/opt/ultra-workshop/specialist-home-orchestrator
```
**How to avoid:** Update `model-matrix-smoke.bats` to assert the new output format.

---

## Timeouts

**Current planner timeout:** 300s with 1 auto-retry. `[VERIFIED: workshop/stage_policy.py:STAGE_POLICIES]`

**Required timeout for Phase 7:** The planner LLM call adds:
- Hermes subprocess startup: ~2s
- LM Studio cold-start for first tool call: ~5–8s
- `list_files` on a medium repo (~200 files): ~1–2s
- 2–3 `read_file` calls on key files: ~2–3s
- LLM reasoning + JSON generation: ~30–120s (orchestrator model, LM Studio)

Total estimated: 50–140s for the LLM + tool calls.
Adding repo clone (~10–30s for a typical small repo over gh CLI):

**Recommended new timeout:** 480s for planner stage (conservative 8 min).
The coder timeout remains 960s (tool_timeout=900s). Neither `hitl_on_timeout` nor
`auto_retries` for planner needs changing.

**The orchestrator model mapping:** `planner-specialist` uses `HOME_DIR=specialist-home-orchestrator`
which configures Hermes to use the `orchestrator` LiteLLM model alias.
`orchestrator` maps to `openai/google/gemma-4-e4b` on LM Studio with 300s timeout and
fallback to `cloud-sonnet` (120s). `[VERIFIED: deploy/litellm/config.yaml]`

The "orchestrator model (L25)" referenced in the ROADMAP success criteria aligns with
this `specialist-home-orchestrator` HERMES_HOME selection.

---

## State of the Art

| Old Approach | New Approach | Impact |
|---|---|---|
| `infer_affected_files()` regex + keyword heuristic | LLM reads repo, lists real paths | `affected_files` accurate; reviewer false-blocks eliminated |
| Clone inside coder stage only | Clone before planner stage, shared across all stages | Planner sees actual file tree; coder reuses workspace; reviewer uses same workspace for `py_compile` |
| `workspace_dir` only in `Diff` model | `workspace_dir` in `state.json` | Resumable after any restart including mid-planner restart |
| Planner: Python subprocess, no Hermes | Planner: `hermes chat` with read tools | Consistent with triage/requirements transport; HERMES_HOME isolation applies |

---

## Code Examples

### Pattern 1: Clone before planner in workshop_build.py (new section after registry validation)

```python
# After state["default_branch"] = default_branch (current line ~302)
# Before the planner stage block (current line ~361)

workspace_dir = state.get("workspace_dir") or f"/tmp/uws-workspace-{task_id}/"
if not workspace_dir or not Path(workspace_dir, ".git").exists():
    workspace = Path(workspace_dir)
    workspace.mkdir(parents=True, exist_ok=True)
    clone = subprocess.run(
        ["gh", "repo", "clone", repo_full_name, str(workspace)],
        capture_output=True, text=True, shell=False,
        env={**os.environ, "GH_TOKEN": os.environ.get("GITHUB_PAT", "")},
    )
    if clone.returncode != 0:
        print(f"[workshop] clone failed: {clone.stderr}", flush=True)
        sys.exit(1)
    state["workspace_dir"] = str(workspace)
    save_task_state(state)
    append_progress(task_id, "workspace_cloned", {"workspace_dir": str(workspace), "repo": repo_full_name})
```

This mirrors the existing clone in `workshop_coder.py:302–313`. `[ASSUMED: exact variable
names — verify against latest workshop_build.py before coding]`

### Pattern 2: Planner query with workspace_dir (update to existing planner_query)

```python
# Current planner_query (workshop_build.py ~362–372) gains workspace_dir key:
planner_query = json.dumps({
    "task_id": task_id,
    "goal": planner_goal,
    "triage_result": triage_raw.model_dump(),
    "context": planning_context,
    "repo": repo_entry,
    "requirements_result": requirements.model_dump(),
    "clarifications": requirements.clarifications,
    "scope_instruction": scope_instruction,
    "workspace_dir": state.get("workspace_dir") or "",  # NEW
    "reference_doc": resolved_doc_content or "",         # NEW (from doc_resolver)
})
```
`[ASSUMED: exact kwarg position — verify against current workshop_build.py before coding]`

### Pattern 3: hermes-skill-run.sh routing change for planner

Remove the `planner-specialist` branch from the Python short-circuit block (current
lines 80–96). After removal, planner falls through to the `hermes chat` production path
at lines 103–110. The `HOME_DIR=specialist-home-orchestrator` and `MAX_TURNS=8` routing
is already correct.

Before (remove):
```bash
if [ "$SKILL" = "requirements-specialist" ] || [ "$SKILL" = "planner-specialist" ] || ...
  case "$SKILL" in
    planner-specialist)  SCRIPT_PATH="...workshop_planner.py" ;;
    ...
  esac
  exec "$PYTHON_BIN" "$SCRIPT_PATH" "$@"
fi
```
`[VERIFIED: scripts/hermes-skill-run.sh:80–96]`

### Pattern 4: Reviewer "outside plan" check (no change needed — shown for reference)

```python
# workshop/reviewer.py:110–117
if planned:
    extras = sorted(set(changed_paths) - planned)
    if extras:
        issues.append("Changed files outside the plan: " + ...)
```
After Phase 7, `planned` will contain real paths like `src/workshop/orchestrator.py`
instead of `agent_orchestration.py`, so `extras` will be empty for compliant coders.
`[VERIFIED: workshop/reviewer.py:110–117]`

### Pattern 5: new_task_state() addition

```python
# workshop/state.py:new_task_state() — add workspace_dir
return {
    ...existing fields...,
    "workspace_dir": "",   # NEW: populated before planner stage, shared across stages
}
```
`[ASSUMED: exact dict key order — match alphabetical sort used by save_task_state()]`

### Pattern 6: stage_policy.py timeout update

```python
# workshop/stage_policy.py
STAGE_POLICIES: dict[str, StagePolicy] = {
    ...
    "planner": StagePolicy(timeout=480, auto_retries=1),  # was 300
    ...
}
```
`[VERIFIED: workshop/stage_policy.py — current is 300; 480 is recommended]`

---

## Package Legitimacy Audit

No new packages are installed in Phase 7. All code uses:
- Python stdlib: `subprocess`, `pathlib`, `json`, `os`, `re`
- Already-installed: `pydantic`, `httpx` (in hermes venv)
- Already-installed: `gh` CLI (Phase 4 Wave 0 prerequisite)

**No package legitimacy audit required.**

---

## Runtime State Inventory

Phase 7 modifies live state in the following ways (not a rename/refactor phase, but
state migration is relevant):

| Category | Items Found | Action Required |
|---|---|---|
| Stored data | `state.json` for running/paused tasks — missing `workspace_dir` key | Code adds the key; existing tasks resume without `workspace_dir` (treated as "" → re-clone) |
| Live service config | `uws-hermes.service` running on VPS — no config changes needed | None |
| OS-registered state | None relevant | None |
| Secrets/env vars | `GITHUB_PAT` used for clone (same as coder stage — already in `/etc/uws/env`) | None |
| Build artifacts | None — Python files only, no compiled artifacts | None |

**Backward compatibility of state.json:** Existing tasks with `workspace_dir: ""` will
trigger a re-clone when resumed. This is safe — `workspace_coder.py` already handles this
case (`if not (workspace / ".git").exists(): clone`). `[VERIFIED: workshop_coder.py:303–313]`

---

## Validation Architecture

`workflow.nyquist_validation` is absent from `.planning/config.json` → treated as enabled.
`[VERIFIED: .planning/config.json]`

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest (Python unit tests) + bats (bash smoke tests) |
| Config file | `pyproject.toml` or `pytest.ini` — run from project root |
| Quick run command | `python -m pytest tests/phase-07/ -x -q` |
| Full suite command | `python -m pytest tests/ -x -q && bats tests/phase-07/planner-smoke.bats` |

### Phase Requirements → Test Map

| Criterion | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| SC-1 | `workspace_dir` added to `new_task_state()` | unit | `pytest tests/phase-07/test_state.py::test_new_task_state_has_workspace_dir -x` | Wave 0 |
| SC-1 | Clone persists `workspace_dir` to `state.json` | unit | `pytest tests/phase-07/test_workspace.py::test_clone_saves_workspace_dir -x` | Wave 0 |
| SC-2 | `hermes-skill-run.sh` routes planner through hermes chat | bats | `bats tests/phase-07/planner-smoke.bats` | Wave 0 |
| SC-3 | Doc resolution tier 1 (repo-first) finds prd.md | unit | `pytest tests/phase-07/test_doc_resolver.py::test_tier1_repo_first -x` | Wave 0 |
| SC-3 | Doc resolution tier 2 (vault-grep) fallback | unit | `pytest tests/phase-07/test_doc_resolver.py::test_tier2_vault_grep -x` | Wave 0 |
| SC-3 | Doc resolution tier 3 (Brain) graceful degradation | unit (mock) | `pytest tests/phase-07/test_doc_resolver.py::test_tier3_brain_degraded -x` | Wave 0 |
| SC-4 | LLM planner output validates against `Plan` schema | unit | `pytest tests/phase-07/test_planner_llm.py::test_plan_schema_valid -x` | Wave 0 |
| SC-5 | Phase-4 bats suite stays green | smoke | `bats tests/phase-04/model-matrix-smoke.bats` | Exists (needs update) |
| SC-5 | Phase-6 pytest suite stays green | regression | `pytest tests/phase-06/ -x -q` | Exists |
| SC-6 | Pipeline latency: planner stage completes within 480s | integration | Manual on VPS | Manual only |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/phase-07/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q && bats tests/phase-04/model-matrix-smoke.bats && bats tests/phase-06/repo-smoke.bats`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/phase-07/__init__.py` — empty init for pytest discovery
- [ ] `tests/phase-07/test_doc_resolver.py` — covers SC-3 (all 3 tiers including Brain mock)
- [ ] `tests/phase-07/test_workspace.py` — covers SC-1 clone + state persistence
- [ ] `tests/phase-07/planner-smoke.bats` — covers SC-2 (dry-run routing assertion)
- [ ] Update `tests/phase-04/model-matrix-smoke.bats` to assert new planner routing output

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no | n/a |
| V3 Session Management | no | n/a |
| V4 Access Control | yes | Read-only tool scope in SKILL.md; workspace_dir path validation |
| V5 Input Validation | yes | `_valid_reviewable_path()` already validates all paths; doc_name must be validated before vault grep |
| V6 Cryptography | no | n/a |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| Path traversal in doc_name | Tampering | Validate `doc_name` with `_valid_reviewable_path()` before vault `rglob()` |
| LLM produces absolute paths in affected_files | Tampering | Reviewer `_path_issue()` already rejects absolute paths — no change needed |
| Clone into attacker-controlled path via `workspace_dir` in resume | Elevation | `workspace_dir` is written by our code only; validate it's under `/tmp/uws-workspace-*/` on load |
| Brain HTTP returns crafted content injected into planner context | Spoofing | Content is injected as reference context, not as trusted instructions; planner SKILL.md must label it as "reference doc" not "instructions" |

---

## Open Questions (RESOLVED)

1. **Hermes `read_file`/`list_files`/`grep_files` tool names**
   - What we know: These are the tool names referenced in the current planner SKILL.md as
     forbidden. They match standard Hermes terminal-based tool names.
   - What's unclear: Are these the exact Hermes tool identifiers, or do they differ in the
     installed Hermes version? The `specialist-home-orchestrator` config may restrict tools
     via a HERMES.md or config file.
   - Recommendation: Before writing the SKILL.md, run `hermes tools list` on the VPS
     with `HERMES_HOME=/opt/ultra-workshop/specialist-home-orchestrator` to confirm exact
     tool names.
   - **RESOLVED:** the exact tool IDs are confirmed by Plan 07-01 Task 2 (live-VPS `hermes tools list`), written to tests/phase-07/hermes-tool-notes.txt and consumed by Plan 07-03 before the SKILL.md tool declarations are written

2. **`specialist-home-orchestrator` existing tool allowlist**
   - What we know: `triage-specialist` uses `specialist-home-private`;
     `requirements-specialist` uses `specialist-home-orchestrator` and currently calls
     `terminal` for a deterministic Python script.
   - What's unclear: Does `specialist-home-orchestrator/HERMES.md` or config already
     allow `read_file`/`list_files`/`grep_files`? Or must they be added?
   - Recommendation: Read `/opt/ultra-workshop/specialist-home-orchestrator/HERMES.md`
     on VPS before writing the planner SKILL.md.
   - **RESOLVED:** gated by Plan 07-01 Task 2 (live-VPS checkpoint) which writes confirmed tool IDs to tests/phase-07/hermes-tool-notes.txt BEFORE Plan 07-03 writes the SKILL.md

3. **LLM planner output quality with small models**
   - What we know: `orchestrator` maps to `google/gemma-4-e4b` (LM Studio primary).
     The model must produce valid JSON with `affected_files` as real repo paths.
   - What's unclear: Will `gemma-4-e4b` reliably produce schema-valid JSON after reading
     files? `requirements-specialist` uses the same model for structured JSON.
   - Recommendation: Include explicit JSON schema as a fenced example in the SKILL.md
     body (same pattern as coder/reviewer SKILL.md) and rely on `_extract_json()` +
     `Plan.model_validate()` to validate; if validation fails, ClarificationNeeded is
     raised and HITL handles it.
   - **RESOLVED:** mitigated by including an explicit fenced JSON schema example in the SKILL.md (Plan 07-03 Task 2, mirroring the coder-specialist pattern); `_extract_json()` + `Plan.model_validate()` validate the output, and ClarificationNeeded → HITL is the recovery path on validation failure

4. **workshop_planner.py fate after Phase 7**
   - What we know: `hermes-skill-run.sh` currently execs `workshop_planner.py` for
     planner-specialist. After Phase 7 the script is no longer called by the main path.
   - What's unclear: Should `workshop_planner.py` be kept as a fallback (for tests,
     dry-run, and future use) or removed?
   - Recommendation: Keep `workshop_planner.py` for the `--dry-run` path and unit tests.
     Remove only the short-circuit in `hermes-skill-run.sh`.
   - **RESOLVED:** keep workshop_planner.py for the --dry-run path; remove only the short-circuit in hermes-skill-run.sh

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| `gh` CLI | Clone step | ✓ (Phase 4 prerequisite) | v2.45.0 on VPS | None — required |
| `GITHUB_PAT` env var | `gh repo clone` | ✓ (in `/etc/uws/env`) | `github_pat_...` format | None — required |
| `hermes` binary | planner-specialist via hermes chat | ✓ (Phase 2 prerequisite) | at `/opt/ultra-workshop/hermes/venv/bin/hermes` | None — required |
| `specialist-home-orchestrator` HERMES_HOME | planner model routing | ✓ (Phase 4 prerequisite) | at `/opt/ultra-workshop/specialist-home-orchestrator/` | None — required |
| LM Studio (`orchestrator` model) | planner LLM call | ✓ (Phase 4 prerequisite) | `google/gemma-4-e4b` with cloud-sonnet fallback | `cloud-sonnet` via LiteLLM fallback |
| `/srv/second-brain` vault | Tier-2 doc resolution | ✓ on VPS (Phase 1 prerequisite) | git-synced vault | Skip tier 2, try Brain |
| Brain HTTP (`127.0.0.1:7000`) | Tier-3 doc resolution | ✓ on VPS (Phase 2 prerequisite) | `status:ERROR` on query due to Groq issue | Return None from tier 3 — non-blocking |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** Brain HTTP (degraded — returns content even on `status:ERROR`).

---

## Sources

### Primary (HIGH confidence)

- `workshop/planner.py` — verified current keyword-heuristic mechanism line by line
- `workshop/orchestrator.py` — verified `run_specialist()` subprocess pattern
- `workshop/state.py` — verified `new_task_state()` schema fields
- `workshop/reviewer.py` — verified `_path_issue()` and "outside plan" gate
- `workshop/stage_policy.py` — verified current timeout values
- `hermes-skills/workshop_build.py` — verified full stage sequencing and state machine
- `hermes-skills/workshop_coder.py` — verified clone step location and workspace handling
- `hermes-skills/brain_http.py` — verified Brain HTTP transport and Groq degradation
- `scripts/hermes-skill-run.sh` — verified routing table, HERMES_HOME selection, short-circuit logic
- `skills/planner-specialist/SKILL.md` — verified current tool prohibitions
- `skills/coder-specialist/SKILL.md` — verified workspace_dir contract
- `skills/reviewer-specialist/SKILL.md` — verified routing pattern to mirror
- `deploy/litellm/config.yaml` — verified orchestrator model → LM Studio mapping
- `workshop/types.py` — verified Plan, Diff, Review schemas
- `.planning/ROADMAP.md` — verified Phase 7 success criteria (locked decisions)
- `tests/phase-04/model-matrix-smoke.bats` — verified current bats assertions to update
- `tests/phase-06/repo-smoke.bats` — verified phase-06 regression surface

### Secondary (MEDIUM confidence)

- `workshop/repo_registry.py` — vault path inference from `DEFAULT_REGISTRY_PATH`
- `hermes-skills/workshop_push.py` — vault write pattern (vault accessible from uws)

### Tertiary (LOW confidence)

None — all claims verified against actual files.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | Exact `new_task_state()` dict key order for `workspace_dir` insertion | Code Examples §5 | Minor — `save_task_state()` uses `sort_keys=True` so order is irrelevant |
| A2 | `hermes read_file`/`list_files`/`grep_files` are exact Hermes tool IDs in installed version | Open Questions §1 | Medium — SKILL.md tool declarations would be wrong; verify with `hermes tools list` |
| A3 | `specialist-home-orchestrator` HERMES_HOME does not already restrict `read_file` tool | Open Questions §2 | Medium — need to read HERMES.md in that home dir before writing SKILL.md |
| A4 | `gemma-4-e4b` produces schema-valid Plan JSON reliably with read tools | Open Questions §3 | Medium — may need prompt engineering; ClarificationNeeded handles failures gracefully |
| A5 | 480s is sufficient planner timeout for LM Studio + repo I/O | Timeouts section | Low — worst case HITL timeout recovery handles it; can be tuned |

**5 assumptions identified.** A2 and A3 are medium-risk and should be verified on VPS
before implementing the SKILL.md changes.

---

## Metadata

**Confidence breakdown:**
- Current planner mechanism: HIGH — read directly from source
- State machine + clone flow: HIGH — read directly from source
- hermes transport + HERMES_HOME: HIGH — read directly from source
- Reviewer gate: HIGH — read directly from source
- Doc resolution design: MEDIUM — Brain tier degradation behavior from comments in source
- Timeout estimates: MEDIUM — estimated from model characteristics, not measured
- Hermes tool names: LOW — referenced in SKILL.md comments, not confirmed against running Hermes binary

**Research date:** 2026-05-25
**Valid until:** 2026-06-25 (stable codebase; changes only if Phase 4/6 artifacts are modified)
