# Phase 4: Build/Fix Pipeline - Pattern Map

**Mapped:** 2026-05-21
**Files analyzed:** 10 (4 new + 6 supporting modules)
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `workshop/types.py` | model | transform | `hermes-skills/brain_http.py` (dict schemas) | partial — no Pydantic in codebase yet; RESEARCH.md §Pattern 2 is authoritative |
| `workshop/orchestrator.py` | service | request-response | `hermes-skills/aider_runner.py` | role-match — subprocess-to-result wrapper with retry |
| `workshop/ledger.py` | utility | file-I/O | `hermes-skills/startup-hitl-scan.py` | role-match — SQLite append writer; same VPS path conventions |
| `workshop/cost.py` | utility | file-I/O + request-response | `hermes-skills/aider_runner.py` (`_post_cost_ledger`) + `hermes-skills/brain_http.py` | role-match — file-read + Brain HTTP POST |
| `workshop/nodes/pr_open.py` | service | event-driven | `hermes-skills/startup-hitl-scan-hook/handler.py` | exact — `record_hitl_pause` + `clarify_gateway.register` + `adapter.send_clarify` |
| `workshop/nodes/triage.py` | service | request-response | `hermes-skills/aider_runner.py` | role-match — single-purpose delegate wrapper |
| `workshop/nodes/planner.py` | service | request-response | `hermes-skills/aider_runner.py` | role-match |
| `workshop/nodes/coder.py` | service | request-response | `hermes-skills/aider_runner.py` | exact — invokes `aider_runner.py` subprocess |
| `workshop/nodes/reviewer.py` | service | request-response | `hermes-skills/aider_runner.py` | role-match |
| `skills/workshop-build/SKILL.md` | config | request-response | `skills/aider/SKILL.md` | exact — same frontmatter schema, trigger format, dry-run guard, `terminal python3` body |
| `skills/workshop-fix/SKILL.md` | config | request-response | `skills/brain-query/SKILL.md` | exact — argument-parsing skill with `--dry-run` guard |
| `tests/phase-04/helpers.bash` | test | — | `tests/phase-03/helpers.bash` | exact — copy SSH helper pattern |
| `tests/phase-04/build-smoke.bats` | test | — | `tests/phase-03/brain-smoke.bats` | exact — dry-run + live smoke pattern |
| `tests/phase-04/fix-smoke.bats` | test | — | `tests/phase-03/brain-smoke.bats` | exact |

---

## Pattern Assignments

### `workshop/types.py` (model, transform)

**Analog:** No existing Pydantic model file in the codebase. The closest structural reference is the `dict` return shapes in `hermes-skills/brain_http.py` lines 202–235 (the `call_agent` return dict with `run_id`, `content`, `status`).

**Imports pattern** — copy from `hermes-skills/brain_http.py` lines 191–196, then add pydantic:
```python
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional
```

**Core schema pattern** — use RESEARCH.md §Pattern 2 exactly (no analog exists; this is the authoritative source):
```python
# workshop/types.py
class PlanStep(BaseModel):
    id: str
    description: str
    files: list[str] = Field(default_factory=list)

class Plan(BaseModel):
    goal: str
    steps: list[PlanStep]
    affected_files: list[str] = Field(default_factory=list)

class FileChange(BaseModel):
    path: str
    diff: str

class Diff(BaseModel):
    summary: str
    changes: list[FileChange]
    branch: str  # workshop/<id>-<slug>

class Review(BaseModel):
    passed: bool
    feedback: str
    blocking_issues: list[str] = Field(default_factory=list)

class Issue(BaseModel):
    url: str
    title: str
    body: str
    number: int

class IngestResult(BaseModel):
    run_id: str
    status: str
    adr_path: str
```

**Pydantic v2 API** — never use v1 methods. All call sites must use:
- `Model.model_json_schema()` (not `.schema()`)
- `Model.model_validate_json(raw)` (not `.parse_raw()`)
- `instance.model_dump_json()` (not `.json()`)

---

### `workshop/orchestrator.py` (service, request-response)

**Analog:** `hermes-skills/aider_runner.py`

**Imports pattern** (lines 22–31 of aider_runner.py):
```python
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional, Type, TypeVar

import importlib.util

from pydantic import BaseModel, ValidationError
```

**importlib loading pattern** — for sibling modules with hyphens in their names (lines 36–40 of aider_runner.py):
```python
_BRAIN_HTTP = Path(__file__).parent.parent / "hermes-skills" / "brain_http.py"
_spec = importlib.util.spec_from_file_location("brain_http", _BRAIN_HTTP)
_brain_http = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_brain_http)
```

**Core parse-retry pattern** — from RESEARCH.md §Pattern 1 (no direct codebase analog; this is authoritative):
```python
T = TypeVar("T", bound=BaseModel)

def delegate_typed(
    goal: str,
    context: str,
    output_schema: Type[T],
    toolsets: list[str],
    max_retries: int = 2,
) -> T:
    schema_str = json.dumps(output_schema.model_json_schema(), indent=2)
    for attempt in range(max_retries + 1):
        prompt = goal
        if attempt > 0:
            prompt += (
                f"\n\nIMPORTANT: Your previous response could not be parsed. "
                f"You MUST return ONLY valid JSON matching this schema:\n{schema_str}"
            )
        raw = _call_delegate_task(goal=prompt, context=context, toolsets=toolsets)
        try:
            return output_schema.model_validate_json(_extract_json(raw))
        except (ValidationError, ValueError):
            if attempt == max_retries:
                raise
    raise RuntimeError("unreachable")

def _extract_json(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in: {text[:200]}")
    return text[start:end]
```

**Error handling pattern** — copy exit-code pattern from aider_runner.py lines 124–128:
```python
if result.returncode != 0:
    print(result.stderr, file=sys.stderr, flush=True)
    _post_cost_ledger(task, success=False)   # non-blocking
    sys.exit(result.returncode)
```

**Non-blocking secondary call pattern** — copy `_post_cost_ledger` try/except from aider_runner.py lines 142–156:
```python
try:
    ledger_result = _brain_http.call_agent(
        "curator",
        f"record-cost&amount={amount:.6f}&task={task_id}&source=workshop&model={model}",
    )
    run_id = ledger_result.get("run_id", "unknown")
    print(f"[cost-ledger] curator run_id={run_id}", flush=True)
except Exception as exc:
    print(
        f"[cost-ledger] WARNING: curator call failed (non-blocking): {exc}",
        file=sys.stderr,
        flush=True,
    )
```

---

### `workshop/ledger.py` (utility, file-I/O)

**Analog:** `hermes-skills/startup-hitl-scan.py`

**Imports pattern** (lines 293–299 of startup-hitl-scan.py):
```python
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
```

**Path + mkdir pattern** — copy from startup-hitl-scan.py lines 320–323 (ensure_schema):
```python
db_path.parent.mkdir(parents=True, exist_ok=True)
```
Apply as:
```python
LEDGER_BASE = Path("/home/uws/.ultra-workshop/tasks")

def task_dir(task_id: str) -> Path:
    d = LEDGER_BASE / task_id
    d.mkdir(parents=True, exist_ok=True)
    return d
```

**JSONL append pattern** — from RESEARCH.md §Pattern 3 (no exact codebase analog):
```python
def append_progress(task_id: str, event: str, data: dict) -> None:
    p = task_dir(task_id) / "progress_log.jsonl"
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **data,
    }
    with p.open("a") as f:
        f.write(json.dumps(entry) + "\n")
```

**Permission enforcement** — copy from startup-hitl-scan.py line 325:
```python
os.chmod(str(db_path), 0o600)
```

---

### `workshop/cost.py` (utility, file-I/O + request-response)

**Analog:** `hermes-skills/aider_runner.py` (`_post_cost_ledger`, lines 134–156) + `hermes-skills/brain_http.py` (`call_agent`, lines 202–235)

**Imports pattern**:
```python
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
```

**File read + non-existence guard** — modeled on startup-hitl-scan.py `fetch_pending` lines 408–418:
```python
LEDGER_PATH = Path("/srv/second-brain/_system/cost-ledger.md")

def get_daily_spend() -> float:
    if not LEDGER_PATH.exists():
        return 0.0
    today = date.today().isoformat()
    total = 0.0
    for line in LEDGER_PATH.read_text().splitlines():
        if today in line:
            m = re.search(r"amount:\s*([\d.]+)", line)
            if m:
                total += float(m.group(1))
    return total
```

**Brain HTTP call pattern** — copy from aider_runner.py lines 143–148 (the `call_agent` invocation):
```python
def record_cost(task_id: str, amount: float, model: str) -> None:
    _brain_http.call_agent(
        "curator",
        f"record-cost&amount={amount:.6f}&task={task_id}&source=workshop&model={model}",
    )
```

**Circuit breaker exception classes** — use plain `Exception` subclasses (no framework needed):
```python
class BudgetExhausted(Exception):
    pass

class BudgetWarning(Exception):
    pass

def check_circuit_breaker(mode: str = "interactive") -> None:
    spend = get_daily_spend()
    if spend >= HARD_THRESHOLD:
        raise BudgetExhausted(f"Daily budget exhausted (${spend:.2f} >= ${HARD_THRESHOLD}). Try tomorrow.")
    if mode == "cron" and spend >= WARN_THRESHOLD:
        raise BudgetWarning(f"Cron self-cancelled: ${spend:.2f} >= ${WARN_THRESHOLD} warn threshold.")
```

---

### `workshop/nodes/pr_open.py` (service, event-driven)

**Analog:** `hermes-skills/startup-hitl-scan-hook/handler.py`

**Imports pattern** (lines 15–25 of handler.py):
```python
from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path
from typing import Optional
```

**Module loading pattern** — copy importlib pattern from handler.py lines 32–43:
```python
_SKILLS_DIR = Path("/opt/ultra-workshop/hermes-skills")
_MODULE_FILE = _SKILLS_DIR / "startup-hitl-scan.py"

import importlib.util
import sys

spec = importlib.util.spec_from_file_location("startup_hitl_scan", str(_MODULE_FILE))
mod = importlib.util.module_from_spec(spec)
sys.modules["startup_hitl_scan"] = mod
spec.loader.exec_module(mod)
record_hitl_pause = mod.record_hitl_pause
```

**HITL durable-first write pattern** — copy from handler.py lines 107–123 (CRITICAL: write DB row BEFORE clarify call):
```python
ALLOWED_CHAT_ID = "7113965359"  # T-02-17

def run_pr_opener(task_id: str, branch: str, plan: dict, diff: dict, session_id: str) -> str:
    # 1. Write durable row BEFORE calling clarify (restart-resilience)
    row_id = record_hitl_pause(
        session_id=session_id,
        task_description=f"[{task_id}] Push branch {branch!r} and open PR?",
        chat_id=ALLOWED_CHAT_ID,
    )
    # 2. Register in clarify_gateway
    clarify_id = f"hitl-pr-{task_id}-{uuid.uuid4().hex[:8]}"
    from tools.clarify_gateway import register  # type: ignore[import]
    entry = register(
        clarify_id=clarify_id,
        session_key=f"hitl-{session_id}",
        question=f"Push branch {branch!r} and open PR?\n\nTask: {task_id}",
        choices=["Approve", "Reject"],
    )
    # 3. send_clarify via adapter (async — called from skill body event loop)
    # 4. On Approve: gh pr create (see gh CLI pattern below)
    # 5. On Reject: return "REJECTED"
```

**gh CLI subprocess pattern** — from RESEARCH.md §Code Examples (security: shell=False, GH_TOKEN env):
```python
result = subprocess.run(
    [
        "gh", "pr", "create",
        "--repo", "caiobellizzi/test-workshop-sandbox",
        "--base", "main",
        "--head", branch,
        "--title", pr_title,
        "--body", pr_body,
    ],
    capture_output=True, text=True, shell=False,
    env={**os.environ, "GH_TOKEN": os.environ["GITHUB_PAT"]},
)
if result.returncode != 0:
    raise RuntimeError(f"gh pr create failed: {result.stderr}")
pr_url = result.stdout.strip()
```

---

### `workshop/nodes/coder.py` (service, request-response)

**Analog:** `hermes-skills/aider_runner.py` (exact match — coder node invokes aider_runner.py)

**Core invocation pattern** — copy subprocess argv construction from aider_runner.py lines 96–118:
```python
import subprocess
import sys
from pathlib import Path

def run_coder(task_id: str, plan: dict, workspace_dir: str) -> dict:
    _venv_aider = Path(sys.executable).parent / "aider"
    aider_bin = str(_venv_aider) if _venv_aider.exists() else "aider"
    # aider_runner.py --workspace-file points to a file inside the cloned sandbox repo
    result = subprocess.run(
        [
            sys.executable,
            "/opt/ultra-workshop/hermes-skills/aider_runner.py",
            "--task", plan["goal"],
            "--workspace-file", workspace_dir + "/README.md",
        ],
        capture_output=True, text=True, shell=False,
        cwd=workspace_dir,
    )
    if result.returncode != 0:
        raise RuntimeError(f"aider_runner failed (exit {result.returncode}): {result.stderr[:500]}")
    return {"stdout": result.stdout, "branch": f"workshop/{task_id}"}
```

**Temp workspace clone pattern** — unique to Phase 4 (no existing analog); follow aider_runner.py tempdir convention (line 57):
```python
import tempfile
workspace_dir = Path(tempfile.mkdtemp(prefix=f"uws-sandbox-{task_id}-"))
print(f"[coder] workspace: {workspace_dir}", flush=True)
```

---

### `skills/workshop-build/SKILL.md` (config, request-response)

**Analog:** `skills/aider/SKILL.md` (exact — same YAML frontmatter schema, trigger line, dry-run guard, `terminal python3` invocation body)

**YAML frontmatter pattern** (lines 1–11 of skills/aider/SKILL.md):
```yaml
---
name: workshop-build
description: "Build a coding task: run /build <task> to generate a PR via the 5-role pipeline."
version: 1.0.0
author: ultra-workshop (local impl)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [workshop, build, pipeline, pr, coding]
---
```

**Trigger + dry-run + terminal body pattern** (lines 19–36 of skills/aider/SKILL.md):
```markdown
## Behavior

1. Extract `--task` from the user trigger
2. If `--dry-run` in trigger: print what would run and stop (no subprocess)
3. Run: `terminal python3 /opt/ultra-workshop/hermes-skills/workshop_build.py --task "<task>" --session-id "<session_id>" --chat-id "<chat_id>"`
4. Capture stdout (progress + PR URL) and return it

## Dry-run behavior

If trigger contains `--dry-run`, print the command that would execute and the task extracted,
then stop without calling `terminal`.

Example dry-run output:
```
[dry-run] would run: python3 /opt/ultra-workshop/hermes-skills/workshop_build.py --task "add hello endpoint" --dry-run
```
```

**Note on Python body vs `terminal` subprocess:** RESEARCH.md §Open Question 1 flags that `delegate_task` / `clarify` availability inside a Python SKILL.md body is ASSUMED, not confirmed. Follow the proven `terminal python3 ...` pattern from all Phase 3 skills. If direct body access to `delegate_task` is confirmed on VPS, the body can be a single `run_build_pipeline(...)` call instead.

---

### `skills/workshop-fix/SKILL.md` (config, request-response)

**Analog:** `skills/brain-query/SKILL.md` (exact — argument-parsing skill with single `--question`/`--issue` flag and dry-run guard)

**Frontmatter pattern** (lines 1–11 of skills/brain-query/SKILL.md):
```yaml
---
name: workshop-fix
description: "Fix a GitHub issue: /fix <github-issue-url> fetches issue, then runs the 5-role build pipeline."
version: 1.0.0
author: ultra-workshop (local impl)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [workshop, fix, issue, pipeline, pr]
---
```

**Steps pattern** (lines 22–27 of skills/brain-query/SKILL.md):
```markdown
## Steps

1. Extract the `--issue` argument (GitHub issue URL) from the user message.
2. Run: `terminal gh issue view "<issue-url>" --json body,title,number`
3. Parse JSON response into Issue schema.
4. Run: `terminal python3 /opt/ultra-workshop/hermes-skills/workshop_build.py --issue-url "<url>" --session-id "<session_id>" --chat-id "<chat_id>"`
5. Capture stdout (progress + PR URL) and return it.
```

---

### `tests/phase-04/helpers.bash` (test, -)

**Analog:** `tests/phase-03/helpers.bash` (exact copy — same VPS_HOST, same `ssh_cmd` + `assert_service_active` functions)

**Full pattern** (lines 1–20 of tests/phase-03/helpers.bash):
```bash
#!/usr/bin/env bash
# tests/phase-04/helpers.bash — Phase 4 shared SSH helpers

VPS_HOST="31.97.130.253"
VPS_USER="root"
VPS_SSH="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10"

ssh_cmd() {
  $VPS_SSH ${VPS_USER}@${VPS_HOST} "$@"
}

assert_service_active() {
  local svc="$1"
  ssh_cmd "systemctl is-active $svc" | grep -q "^active$"
}
```

---

### `tests/phase-04/build-smoke.bats` (test, -)

**Analog:** `tests/phase-03/brain-smoke.bats` (exact — dry-run + live smoke structure, `load helpers`, `skip_if_*` guard)

**Structure pattern** (lines 1–44 of tests/phase-03/brain-smoke.bats):
```bash
#!/usr/bin/env bats
# tests/phase-04/build-smoke.bats — workshop-build dry-run + smoke tests

load helpers

skip_if_pipeline_down() {
  run ssh_cmd "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 -c 'import workshop.types' 2>/dev/null; echo exit:$?"
  if echo "$output" | grep -q "exit:1"; then
    skip "workshop package not importable on VPS"
  fi
}

@test "workshop-build dry-run exits 0" {
  run ssh_cmd "bash /opt/ultra-workshop/scripts/hermes-skill-run.sh workshop-build --dry-run --task 'add hello endpoint'"
  [ "$status" -eq 0 ]
}

@test "workshop-fix dry-run exits 0" {
  run ssh_cmd "bash /opt/ultra-workshop/scripts/hermes-skill-run.sh workshop-fix --dry-run --issue 'https://github.com/caiobellizzi/test-workshop-sandbox/issues/1'"
  [ "$status" -eq 0 ]
}

@test "workshop types are importable" {
  skip_if_pipeline_down
  run ssh_cmd "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 -c 'from workshop.types import Plan, Diff, Review; print(\"ok\")'"
  [ "$status" -eq 0 ]
  [[ "$output" == *"ok"* ]]
}
```

---

## Shared Patterns

### subprocess.run(shell=False) — Security invariant
**Source:** `hermes-skills/aider_runner.py` lines 111–118
**Apply to:** `workshop/nodes/coder.py`, `workshop/nodes/pr_open.py`, any file calling `gh` or `aider`
```python
result = subprocess.run(
    argv,                # list — never a shell string
    capture_output=True,
    text=True,
    shell=False,
    cwd=str(workspace_dir),
)
```

### importlib for hyphenated filenames
**Source:** `hermes-skills/aider_runner.py` lines 36–40; `hermes-skills/startup-hitl-scan-hook/handler.py` lines 32–43
**Apply to:** `workshop/orchestrator.py` (loading brain_http.py), `workshop/nodes/pr_open.py` (loading startup-hitl-scan.py)
```python
_spec = importlib.util.spec_from_file_location("module_name", str(path_to_file))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
```

### Brain HTTP — multipart/form-data (CRITICAL)
**Source:** `hermes-skills/brain_http.py` lines 221–227
**Apply to:** `workshop/cost.py` (via `_brain_http.call_agent`), `workshop/nodes/pr_open.py` (ADR write-back)
```python
# ALWAYS use data={} not json={} — Brain Agno 2.6.7 returns 422 on json={}
resp = httpx.post(
    f"{BRAIN_BASE_URL}/agents/{agent_id}/runs",
    data={"message": message, "stream": "false", "user_id": user_id},
    timeout=DEFAULT_TIMEOUT,
)
```

### Non-blocking secondary calls (fire-and-forget)
**Source:** `hermes-skills/aider_runner.py` lines 134–156 (`_post_cost_ledger`)
**Apply to:** `workshop/cost.py` (`record_cost`), `workshop/nodes/pr_open.py` (ADR write-back)
```python
try:
    result = _brain_http.call_agent("curator", message)
    print(f"[cost-ledger] run_id={result.get('run_id', 'unknown')}", flush=True)
except Exception as exc:
    print(f"WARNING: curator call failed (non-blocking): {exc}", file=sys.stderr, flush=True)
    # Do NOT re-raise — caller result is not affected
```

### HITL durable-first pattern
**Source:** `hermes-skills/startup-hitl-scan.py` `record_hitl_pause` (lines 328–361) + `handler.py` `_re_emit_row` (lines 78–204)
**Apply to:** `workshop/nodes/pr_open.py`
**Rule:** Write `pending_hitl.db` row BEFORE `clarify_gateway.register()`. Never call `clarify` inside a `delegate_task` subagent — it must be in the parent skill body.

### `from __future__ import annotations` + flush=True
**Source:** All hermes-skills/*.py files (lines 1–2 of each)
**Apply to:** All `workshop/` Python files
```python
from __future__ import annotations
# ...
print("[module] message", flush=True)  # always flush for subprocess stdout capture
```

### SKILL.md dry-run guard
**Source:** `skills/aider/SKILL.md` lines 34–36; `scripts/hermes-skill-run.sh` lines 19–23
**Apply to:** `skills/workshop-build/SKILL.md`, `skills/workshop-fix/SKILL.md`

The `hermes-skill-run.sh` wrapper intercepts `--dry-run` at the shell level and short-circuits before calling `hermes chat`. SKILL.md bodies must also check for `--dry-run` in the trigger to guard against direct invocation.

### Deploy location comments
**Source:** `hermes-skills/aider_runner.py` lines 12–13; `hermes-skills/brain_http.py` lines 9–10
**Apply to:** All `workshop/` and `hermes-skills/` Python files
```python
# Deploy location: /opt/ultra-workshop/workshop/<module>.py
# Run as: sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 ...
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `workshop/__init__.py` | config | — | Empty init; no analog needed |
| `workshop/nodes/__init__.py` | config | — | Empty init; no analog needed |
| `tests/phase-04/test_orchestrator.py` | test | — | No existing pytest unit tests for delegate-style services; write fresh based on pytest conventions |
| `tests/phase-04/test_ledger.py` | test | — | No existing pytest unit tests for ledger writers |
| `tests/phase-04/test_cost.py` | test | — | No existing pytest unit tests for circuit breakers |

---

## Metadata

**Analog search scope:** `hermes-skills/`, `skills/`, `scripts/`, `tests/`
**Files scanned:** 13
**Pattern extraction date:** 2026-05-21

**Key findings:**
1. All Phase 3 skills use `terminal python3 /opt/ultra-workshop/hermes-skills/<script>.py` — workshop-build/fix should follow this pattern until Hermes Python body skill support is confirmed on VPS (RESEARCH.md Open Question 1).
2. The importlib pattern for loading hyphenated Python filenames is used in two existing files (aider_runner.py, handler.py) — `workshop/orchestrator.py` must use the same pattern to load `brain_http.py`.
3. The HITL gate pattern in `handler.py` is the only async code in the project; `pr_open.py` must match its async + threading structure for the wait-for-decision loop.
4. Brain HTTP `data={}` vs `json={}` is a live production constraint (422 failure if wrong) — documented in `brain_http.py` docstring and must be carried into all new Brain callers.
5. No Pydantic models exist anywhere in the current codebase — `workshop/types.py` is the first. Use RESEARCH.md §Pattern 2 as the authoritative source; all v2 API rules apply.
