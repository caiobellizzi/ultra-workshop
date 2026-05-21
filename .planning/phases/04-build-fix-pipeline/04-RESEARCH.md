# Phase 4: Build/Fix Pipeline - Research

**Researched:** 2026-05-21
**Domain:** Python orchestration, Hermes skill bodies, Pydantic v2, LiteLLM cost API, gh CLI, Brain HTTP, two-ledger pattern
**Confidence:** HIGH (primary findings from live codebase + Phase 2/3 summaries; no unknowns remain about core implementation)

---

## Summary

Phase 4 builds the first end-to-end coding pipeline: a `/build <task>` or `/fix <issue-url>` Telegram command that runs a 5-role specialist pipeline (triage → planner → coder → reviewer → pr_opener), pauses for HITL approval, and posts a PR URL back to the user. All supporting infrastructure (Hermes, aider_runner.py, brain_http.py, pending_hitl.db, startup-hitl-scan hook) was completed in Phases 2–3. Phase 4 creates only the `workshop/` Python package and two new Hermes skills.

The key architectural insight is that **all five specialists are Hermes `delegate_task` calls, not separate Python processes**. The workshop-build skill body is a single Python file that drives the pipeline with `for` loops and `delegate_task` — no LangGraph, no state machine. The `workshop/` module is pure Python: Pydantic schemas, a ledger writer, a circuit breaker, and thin node wrappers. Pydantic 2.12.5 is already in the Hermes venv as an aider-chat dependency — no new install needed.

The HITL gate reuses the proven pattern from Phase 2 (startup-hitl-scan hook, pending_hitl.db, `tools.clarify_gateway.register`). Cost tracking is done by reading the vault's `_system/cost-ledger.md` for circuit-breaking and POSTing entries via `brain_http.call_agent("curator", "record-cost&amount=X&task=Y")`. The `gh` CLI is available on the VPS (Node.js 24 via nvm was installed in Phase 2), and `GITHUB_PAT` must be provisioned as a Wave 0 prerequisite since it was deferred from Phase 2.

**Primary recommendation:** Three-wave plan — Wave 0 (prerequisites: GITHUB_PAT, test-workshop-sandbox repo, workshop/ package scaffold with types/ledger/cost), Wave 1 (5-role pipeline + two skills), Wave 2 (HITL gate + ADR write-back + bats smoke tests).

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-ws-028 | `workshop/types.py` Pydantic schemas (Plan, PlanStep, Diff, FileChange, Review, Issue, IngestResult); `delegate_typed()` in `workshop/orchestrator.py` with max 2 parse retries | Pydantic 2.12.5 already in venv; `model.model_json_schema()` for prompt injection; `model.model_validate_json()` for parse-retry loop |
| REQ-ws-007 | workshop-build Hermes skill with 5-role pipeline triage→planner→coder→reviewer→pr_opener; reviewer→coder retry max 2; end-to-end within ~5 min | `delegate_task(goal=..., context=..., toolsets=[...])` drives each role; skill body is a Python file; aider_runner.py already wired for coder role |
| REQ-ws-008 | workshop-fix skill: `/fix <github-issue-url>` path, fetches issue first, same pipeline | `gh issue view <url> --json body,title` to fetch; triage branch diverges at "is this from an issue URL?" check |
| REQ-ws-009 | Two-ledger task audit trail: `~/.ultra-workshop/tasks/<task-id>/task_ledger.md` + `progress_log.jsonl` | `workshop/ledger.py` writes both files; one JSONL event per node transition; task-id = 4-char hex + epoch |
| REQ-ws-010 | HITL gate before PR creation: Hermes `clarify` callback → Telegram inline buttons (Approve/Reject); Approve → git push + gh pr create; Reject → abort | `tools.clarify_gateway.register()` + `adapter.send_clarify()` already proven in startup-hitl-scan-hook; same pattern applies inside skill body |
| REQ-ws-011 | ADR write-back after PR: `brain_http.call_agent("ingest", ...)` to `_system/workshop-adrs/<task-id>.md` with correct frontmatter | brain_http.py already provides `call_agent("ingest", message)`; message contains markdown ADR text with required frontmatter fields |
| REQ-ws-012 | Cost ledger + circuit breaker: per-delegate_task cost → Brain curator; $18 self-cancel + warning; $20 refuse | `workshop/cost.py` reads `/srv/second-brain/_system/cost-ledger.md`, parses `amount:` lines with `source: workshop`; POSTs via `brain_http.call_agent("curator", "record-cost&amount=X&task=Y")` |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Pipeline orchestration | Hermes skill body (Python) | — | L11 LOCKED: delegate_task from skill body, no LangGraph |
| Specialist execution | Hermes delegate_task subagents | — | Each role runs in isolated subagent context |
| Code generation (coder role) | aider_runner.py subprocess | Hermes subagent | aider_runner.py already deployed; coder subagent invokes it via `terminal` |
| HITL approval gate | Hermes clarify_gateway + Telegram adapter | pending_hitl.db (durability) | Proven pattern from Phase 2; restart-resilience via existing startup-hitl-scan hook |
| PR creation | gh CLI subprocess on VPS | — | L18 LOCKED: fine-grained PAT; `gh pr create` is the only PR creation path |
| Cost tracking | workshop/cost.py (read vault file) | brain_http.py (write to curator) | D2 LOCKED: shared ledger at `/srv/second-brain/_system/cost-ledger.md` |
| ADR write-back | brain_http.py → Brain.ingest | — | D1 LOCKED: workshop writes to vault only via Brain.ingest |
| Task audit trail | workshop/ledger.py (local filesystem) | — | D9 LOCKED: `~/.ultra-workshop/tasks/<id>/` on VPS |
| Telegram UI | Hermes gateway (existing) | — | L4 LOCKED: Hermes owns Telegram gateway exclusively |

---

## Standard Stack

### Core — all already in Hermes venv (no new installs for workshop/ module)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 (pinned by aider-chat 0.86.2) | Specialist output schemas, JSON schema injection, parse-retry validation | L30 LOCKED; already in venv |
| httpx | 0.28.1 (already in venv) | Brain HTTP calls via brain_http.py | Proven in Phase 3; brain_http.py pattern reused |
| gh CLI | 2.x (installed via apt on VPS) | Branch push, PR creation, issue fetch | L18 LOCKED: fine-grained PAT; gh CLI is the standard tool |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlite3 (stdlib) | stdlib | pending_hitl.db reads for circuit-breaker restart | Already wired in startup_hitl_scan.py |
| json (stdlib) | stdlib | progress_log.jsonl writer | One line per node event |
| uuid / secrets (stdlib) | stdlib | 4-char hex task ID generation | `secrets.token_hex(2)` for short-id; full uuid for session_id |
| pathlib (stdlib) | stdlib | Ledger file path construction | Consistent with existing hermes-skills/ pattern |

### Installation

No new pip installs required for the `workshop/` module — pydantic 2.12.5 and httpx 0.28.1 are already present as aider-chat and hermes-agent transitive dependencies.

**Wave 0 install prerequisite (VPS only):**
```bash
# Verify pydantic is present in Hermes venv
sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 -c "import pydantic; print(pydantic.VERSION)"

# gh CLI (if not present — install via apt)
apt-get install -y gh
gh --version

# Test-workshop-sandbox repo must exist
gh repo view caiobellizzi/test-workshop-sandbox
```

**GITHUB_PAT provisioning (human gate — deferred from Phase 2):**
- Create at: github.com/settings/tokens → Fine-grained tokens → select `test-workshop-sandbox` repo → Contents read/write + Pull requests write
- Inject into `/etc/uws/env` as `GITHUB_PAT=ghp_...`
- Configure git credential: `git config --global credential.helper store` as uws user with the PAT

---

## Package Legitimacy Audit

> Phase 4 installs NO new external packages. All required libraries are already present in the Hermes venv from Phases 2–3. slopcheck not available at research time.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| pydantic | PyPI | ~9 yrs | ~150M/wk | github.com/pydantic/pydantic | Not run | Approved — industry standard, already in venv |
| httpx | PyPI | ~5 yrs | ~30M/wk | github.com/encode/httpx | Not run | Approved — proven in Phase 3 |
| gh CLI | GitHub releases (apt) | ~5 yrs | N/A | github.com/cli/cli | Not run | Approved — official GitHub tool |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*slopcheck was unavailable at research time. All packages above are [ASSUMED] on legitimacy grounds from official documentation; however, all are well-established ecosystem tools with no known impersonation risk.*

---

## Architecture Patterns

### System Architecture Diagram

```
Telegram → Hermes gateway → workshop-build/fix SKILL.md (Python body)
                               │
                               ├─ delegate_task(role=triage) ──────── [classify task]
                               │   └─ returns: Plan (Pydantic)
                               │
                               ├─ delegate_task(role=planner) ──────── [query Brain, write plan]
                               │   └─ returns: Plan (Pydantic)
                               │
                               ├─ [for attempt in range(3)]:
                               │   ├─ delegate_task(role=coder) ──────── [aider_runner.py subprocess → diff]
                               │   │   └─ returns: Diff (Pydantic)
                               │   └─ delegate_task(role=reviewer) ───── [lint + checks]
                               │       └─ returns: Review (Pydantic) → PASS/RETRY
                               │
                               ├─ workshop/ledger.py → task_ledger.md + progress_log.jsonl
                               │
                               ├─ clarify_gateway.register() → Telegram inline buttons (Approve/Reject)
                               │         pending_hitl.db (durability)
                               │
                               ├─ [on Approve]:
                               │   ├─ gh push workshop/<id>-<slug>
                               │   ├─ gh pr create → PR URL
                               │   └─ brain_http.call_agent("ingest", ADR text) → vault ADR
                               │
                               └─ workshop/cost.py → brain_http.call_agent("curator", "record-cost&...")
```

### Recommended Project Structure (new files for Phase 4)

```
workshop/
├── __init__.py                  # empty
├── types.py                     # Pydantic: Plan, PlanStep, Diff, FileChange, Review, Issue, IngestResult
├── orchestrator.py              # delegate_typed() with max-2 parse-retry loop
├── ledger.py                    # task_ledger.md writer + progress_log.jsonl appender
├── cost.py                      # circuit breaker: read vault file, check thresholds, POST to curator
└── nodes/
    ├── __init__.py
    ├── triage.py                # classify_task() → triage branch label
    ├── planner.py               # run_planner() → Plan
    ├── coder.py                 # run_coder() → Diff (calls aider_runner via terminal)
    ├── reviewer.py              # run_reviewer() → Review
    └── pr_open.py               # run_pr_opener() → PR URL (HITL gate here)
skills/
├── workshop-build/SKILL.md     # Hermes skill: Python body orchestrator
└── workshop-fix/SKILL.md       # Hermes skill: same but /fix path
tests/
└── phase-04/
    ├── helpers.bash              # inherit from tests/phase-03/helpers.bash
    ├── build-smoke.bats          # dry-run + VPS end-to-end smoke
    └── fix-smoke.bats            # dry-run only (issue URL path)
```

### Pattern 1: delegate_typed() — Pydantic parse-retry loop

**What:** Call `delegate_task` then parse the subagent's text output as JSON into a Pydantic schema. Retry up to 2 times with "must return valid JSON matching schema" in the retry prompt.

**When to use:** Every specialist call (triage, planner, coder, reviewer). Never call `delegate_task` without schema validation for these roles.

```python
# Source: docs/ingest/PLAN.md §WS-007 + L30 LOCKED decision
# workshop/orchestrator.py
import json
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

def delegate_typed(
    goal: str,
    context: str,
    output_schema: Type[T],
    toolsets: list[str],
    max_retries: int = 2,
) -> T:
    """Call delegate_task and parse result into Pydantic schema with retry."""
    schema_str = json.dumps(output_schema.model_json_schema(), indent=2)
    for attempt in range(max_retries + 1):
        prompt = goal
        if attempt > 0:
            prompt += (
                f"\n\nIMPORTANT: Your previous response could not be parsed. "
                f"You MUST return ONLY valid JSON matching this schema:\n{schema_str}"
            )
        # delegate_task is a Hermes tool — called as a tool in the skill body
        # The skill body uses: result = delegate_task(goal=prompt, context=context, toolsets=toolsets)
        # result is a string (subagent's final message)
        raw = _call_delegate_task(goal=prompt, context=context, toolsets=toolsets)
        try:
            return output_schema.model_validate_json(_extract_json(raw))
        except (ValidationError, ValueError):
            if attempt == max_retries:
                raise
    raise RuntimeError("unreachable")

def _extract_json(text: str) -> str:
    """Extract JSON from text that may have prose around it."""
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in: {text[:200]}")
    return text[start:end]
```

### Pattern 2: workshop/types.py — Pydantic schemas

```python
# Source: docs/ingest/PLAN.md §WS-007 + L30; pydantic 2.12.5 (aider-chat dep)
from pydantic import BaseModel, Field
from typing import Optional

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

### Pattern 3: workshop/ledger.py — Two-ledger writer

```python
# Source: docs/ingest/PLAN.md §WS-009 + D9; Magentic-One pattern
# [CITED: arxiv.org/abs/2511.03690 — Magentic-One multi-agent paper]
import json
from datetime import datetime, timezone
from pathlib import Path

LEDGER_BASE = Path("/home/uws/.ultra-workshop/tasks")

def task_dir(task_id: str) -> Path:
    d = LEDGER_BASE / task_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def write_task_ledger(task_id: str, goal: str, plan: dict) -> None:
    p = task_dir(task_id) / "task_ledger.md"
    p.write_text(
        f"# Task {task_id}\n\n"
        f"**Goal:** {goal}\n\n"
        f"## Plan\n\n"
        + "\n".join(f"- {s['id']}: {s['description']}" for s in plan.get("steps", []))
    )

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

### Pattern 4: workshop/cost.py — Circuit breaker

**What:** Read `/srv/second-brain/_system/cost-ledger.md`, sum `amount:` lines for today. POST cost entries to Brain curator. Two thresholds: $18 (cron self-cancel + Telegram warning, per day limit), $20 (LLM calls refused).

```python
# Source: docs/ingest/PLAN.md §WS-012 + D2 + CONSTRAINT-budget-circuit-breaker
# [CITED: .planning/intel/constraints.md CONSTRAINT-budget-circuit-breaker]
import re
from datetime import date
from pathlib import Path

LEDGER_PATH = Path("/srv/second-brain/_system/cost-ledger.md")
WARN_THRESHOLD = 18.0
HARD_THRESHOLD = 20.0

def get_daily_spend() -> float:
    """Parse today's total spend from the shared cost ledger (both Brain + Workshop)."""
    if not LEDGER_PATH.exists():
        return 0.0
    today = date.today().isoformat()
    total = 0.0
    for line in LEDGER_PATH.read_text().splitlines():
        # Entry format: "- date: 2026-05-21 amount: 0.047 source: workshop task: workshop-build-ab12"
        if today in line:
            m = re.search(r"amount:\s*([\d.]+)", line)
            if m:
                total += float(m.group(1))
    return total

def check_circuit_breaker(mode: str = "interactive") -> None:
    """Raise BudgetExhausted if over threshold. mode='cron' self-cancels at $18."""
    spend = get_daily_spend()
    if spend >= HARD_THRESHOLD:
        raise BudgetExhausted(f"Daily budget exhausted (${spend:.2f} >= ${HARD_THRESHOLD}). Try tomorrow.")
    if mode == "cron" and spend >= WARN_THRESHOLD:
        raise BudgetWarning(f"Cron self-cancelled: ${spend:.2f} >= ${WARN_THRESHOLD} warn threshold.")

class BudgetExhausted(Exception):
    pass

class BudgetWarning(Exception):
    pass

def record_cost(task_id: str, amount: float, model: str) -> None:
    """POST a cost entry to Brain's curator agent."""
    from hermes_skills import brain_http  # importlib path on VPS
    brain_http.call_agent(
        "curator",
        f"record-cost&amount={amount:.6f}&task={task_id}&source=workshop&model={model}",
    )
```

### Pattern 5: HITL gate in skill body

**What:** Before `gh pr create`, write to `pending_hitl.db`, then call `clarify_gateway.register()` + `adapter.send_clarify()`. The existing startup-hitl-scan hook re-emits the keyboard on restart.

**Critical constraint:** `clarify` is blocked inside `delegate_task` subagents (subagents cannot interact with users). The HITL gate MUST live in the parent skill body, not inside a specialist subagent. This is why `pr_opener` is a step in the skill body, not a fully delegated specialist.

```python
# Source: hermes-skills/startup-hitl-scan-hook/handler.py (proven Phase 2/3 pattern)
# workshop/nodes/pr_open.py — called from within the skill body (not inside delegate_task)
import uuid
from hermes_skills.startup_hitl_scan import record_hitl_pause  # importlib-loaded

ALLOWED_CHAT_ID = "7113965359"  # T-02-17

def run_pr_opener(task_id: str, branch: str, plan: dict, diff: dict, session_id: str) -> str:
    """Pause for HITL, then push branch + open PR. Returns PR URL."""
    # 1. Write durable row BEFORE calling clarify (restart-resilience)
    row_id = record_hitl_pause(
        session_id=session_id,
        task_description=f"[{task_id}] Push branch {branch!r} and open PR?",
        chat_id=ALLOWED_CHAT_ID,
    )
    # 2. Register clarify entry (in-process) and send Telegram inline keyboard
    clarify_id = f"hitl-pr-{task_id}-{uuid.uuid4().hex[:8]}"
    # In actual Hermes skill body: use `clarify` tool with buttons ["Approve", "Reject"]
    # The tool call: clarify(question=..., choices=["Approve", "Reject"])
    # On Approve: fall through to git push + gh pr create
    # On Reject: return "REJECTED"
    ...
```

### Pattern 6: workshop-build SKILL.md (Python body skill)

**What:** A Hermes SKILL.md with `## Body` Python section that drives the full pipeline. Hermes executes the Python body directly (unlike brain-query which calls `terminal python3 ...`). The skill body has direct access to `delegate_task`, `clarify`, and `terminal` as callable tools.

```markdown
---
name: workshop-build
description: "Build a coding task: run /build <task> to generate a PR via the 5-role pipeline."
version: 1.0.0
...
---
## Trigger
/build <task description>

## Body
```python
import sys
sys.path.insert(0, "/opt/ultra-workshop")
from workshop.orchestrator import run_build_pipeline
run_build_pipeline(task=trigger_args["task"], session_id=session_id, chat_id=chat_id)
```
```

> **Note on Hermes Python body vs terminal:** Phase 3 skills (brain-query, aider) used `terminal python3 /opt/ultra-workshop/hermes-skills/foo.py` in the SKILL.md body, which is a simpler pattern. For the workshop-build pipeline, the skill body needs direct access to `delegate_task` and `clarify` tools — these are only available inside the Hermes execution context, not in a subprocess. The planner must verify whether Hermes v0.14.0 supports Python-body skills or if the pipeline must be orchestrated via sequential `terminal` calls. **This is an open question requiring verification on VPS.** [ASSUMED]

### Anti-Patterns to Avoid

- **HITL inside delegate_task subagent:** `clarify` is blocked in subagents. The pr_opener MUST run in the parent skill body (confirmed by Hermes docs: "Subagents cannot call clarify, memory, send_message").
- **Using `delegate_task` for durable HITL state:** `delegate_task` is NOT restart-safe (confirmed Phase 2 research). Always write `pending_hitl.db` row BEFORE calling clarify.
- **Using `json={}` instead of `data={}` for Brain HTTP:** Brain Agno 2.6.7 returns 422 on JSON content-type. Use `data={}` (multipart/form-data). Pattern proven in brain_http.py.
- **Calling `gh pr create` before HITL approval:** blast radius constraint L17 — never push to test-workshop-sandbox without human approval.
- **Hardcoding cost amounts:** Never hardcode `private-worker` as $0.000 in ledger entries. Record token counts and model names; amount=0.0 for local models is correct.
- **Using `shell=True` for `gh` subprocess:** Security rule from Phase 3 — all subprocess calls use `shell=False` with list argv.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Telegram inline buttons for HITL | Custom Telegram Bot API calls | Hermes `clarify` + `tools.clarify_gateway.register()` | Already proven in startup-hitl-scan-hook; correct event loop integration |
| GitHub PR creation | Raw GitHub REST API via httpx | `gh pr create` subprocess | L18 LOCKED PAT auth; gh CLI handles all edge cases |
| GitHub issue fetch for /fix | PyGithub library | `gh issue view <url> --json body,title,number` | PAT already wired for gh CLI; no extra library needed |
| Specialist result parsing | Custom regex parser | `pydantic.model_validate_json()` | Schema validation + clear error messages for retry |
| Cost ledger format | Custom binary/DB | Append to markdown file + regex parse | D2 LOCKED: both systems share one markdown file; regex on `amount:` field is sufficient |
| HITL restart resilience | Re-implement | startup-hitl-scan hook (already deployed Phase 2) | Already live on VPS; just call `record_hitl_pause()` before clarify |
| task_id generation | UUID library | `secrets.token_hex(2)` (short-id) | L20 LOCKED: `workshop/<short-id>-<slug>` naming; 4-char hex suffices |

**Key insight:** Almost every "new" component reuses a proven Phase 2/3 primitive. The only truly new code is the Pydantic schemas, the pipeline for-loop, and the ledger writer.

---

## Common Pitfalls

### Pitfall 1: clarify blocked inside subagents (BLOCKS HITL gate)

**What goes wrong:** Developer puts HITL `clarify` call inside the pr_opener `delegate_task` call. Hermes silently ignores it or errors — subagents are `role="leaf"` and cannot call clarify.
**Why it happens:** The spec says "pr_opener role" — reads like a subagent. But it's actually a step executed in the parent skill body.
**How to avoid:** The HITL gate lives in the parent skill body. `delegate_task` is only used for planner, coder, reviewer. `pr_opener` is a local function called directly in the skill body after the pipeline completes.
**Warning signs:** HITL Telegram button never appears; `systemctl status uws-hermes` shows no clarify events.

### Pitfall 2: delegate_task context isolation (ALL specialists)

**What goes wrong:** `delegate_task(goal="Review the code we just generated")` — subagent has zero context about what "we just generated" means.
**Why it happens:** Hermes subagents start with a completely fresh conversation context.
**How to avoid:** Pass the full diff/plan JSON in the `context=` parameter. Use `output_schema.model_dump_json()` to serialize the previous specialist's output and pass it as context.
**Warning signs:** Reviewer produces generic feedback unrelated to the actual code changes.

### Pitfall 3: Pydantic v2 API differences from v1

**What goes wrong:** Using `.schema()` (v1) or `.json()` (v1) instead of `.model_json_schema()` and `.model_dump_json()` (v2).
**Why it happens:** Training data contains Pydantic v1 patterns; v2 renamed many methods.
**How to avoid:** Pydantic 2.12.5 is pinned. Use `model.model_json_schema()`, `model.model_validate_json()`, `model.model_dump_json()`. Never use deprecated v1 APIs.
**Warning signs:** `AttributeError: 'Plan' object has no attribute 'json'` or similar.

### Pitfall 4: GITHUB_PAT not provisioned (Wave 0 blocker)

**What goes wrong:** `gh pr create` returns 401 or gh CLI not authenticated.
**Why it happens:** GITHUB_PAT was deferred from Phase 2 (02-04 was deferred). It is NOT in `/etc/uws/env` yet.
**How to avoid:** Wave 0 MUST include a human-verify checkpoint: provision GITHUB_PAT → inject into `/etc/uws/env` → `gh auth login --with-token` as uws user → verify `gh repo view caiobellizzi/test-workshop-sandbox` returns 200.
**Warning signs:** Wave 0 gate fails; `gh auth status` as uws shows "not logged in".

### Pitfall 5: Cost ledger path not yet created

**What goes wrong:** `workshop/cost.py` tries to read `/srv/second-brain/_system/cost-ledger.md` but the file doesn't exist yet (no `/build` run has happened before).
**Why it happens:** The ledger is append-only and created on first write.
**How to avoid:** `get_daily_spend()` returns 0.0 if the file doesn't exist. `record_cost()` must create the file if absent (open with `"a"` mode or check existence first).
**Warning signs:** `FileNotFoundError` on first `/build` run.

### Pitfall 6: aider_runner.py creates a temp workspace, not the target repo

**What goes wrong:** Coder specialist produces a diff in `/tmp/uws-aider-workspace-<pid>/` — the diff doesn't apply to `caiobellizzi/test-workshop-sandbox`.
**Why it happens:** aider_runner.py was designed to create a fresh temp git workspace. For the pipeline, we need aider to work in a cloned sandbox repo.
**How to avoid:** The coder node must: (1) clone `test-workshop-sandbox` to `/tmp/uws-sandbox-<task-id>/`; (2) create branch `workshop/<id>-<slug>`; (3) run aider with `--workspace-file` pointing to a file in the cloned repo; (4) return the git diff. The `--workspace-file` parameter in aider_runner.py supports this. [ASSUMED — verify on VPS that aider can edit a real repo file, not just the temp workspace.py]
**Warning signs:** PR contains only `workspace.py` stub file, not actual sandbox repo changes.

### Pitfall 7: Brain ingest HITL on Brain side delays ADR write-back

**What goes wrong:** `brain_http.call_agent("ingest", adr_content)` hangs or returns an error because Brain's ingest agent has HITL gating on the Brain side.
**Why it happens:** From Phase 3 (03-04-SUMMARY): "brain-ingest/SKILL.md includes HITL Warning: Brain-side approval required before vault write commits."
**How to avoid:** The ADR write-back is fire-and-forget (non-blocking). Call `brain_http.call_agent("ingest", ...)` with a short timeout (e.g., 30s) and treat failure as a warning, not an error. The PR URL is already posted to Telegram before the ADR write.
**Warning signs:** `/build` takes >10 minutes; workshop-build skill hangs after PR creation.

### Pitfall 8: delegate_task max_spawn_depth constraint

**What goes wrong:** The skill body calls `delegate_task` for triage, then triage subagent tries to delegate further. Hermes silently ignores the nested delegation or errors.
**Why it happens:** L11 LOCKED: "Hermes Level 0 delegation (max depth 2, Level 0 only)". With default `max_spawn_depth: 1`, subagents cannot delegate.
**How to avoid:** All specialist subagents are `role="leaf"`. No specialist should call delegate_task itself. Retry loops live in the parent skill body.
**Warning signs:** Reviewer subagent tries to spawn a coder sub-subagent; result is empty or errored.

---

## Code Examples

### Verified patterns from existing codebase

**Brain HTTP call (multipart/form-data):**
```python
# Source: hermes-skills/brain_http.py (Phase 3 — production)
result = _brain_http.call_agent(
    "curator",
    f"record-cost&amount={amount:.6f}&task={task_id}&source=workshop&model={model}",
)
run_id = result.get("run_id", "unknown")
```

**HITL clarify_gateway registration:**
```python
# Source: hermes-skills/startup-hitl-scan-hook/handler.py (Phase 2 — production)
from tools.clarify_gateway import register  # type: ignore[import]
entry = register(
    clarify_id=clarify_id,
    session_key=f"hitl-{session_id}",
    question=f"Push branch {branch!r} and open PR?\n\nTask: {task_description}",
    choices=["Approve", "Reject"],
)
result = await adapter.send_clarify(
    chat_id=chat_id,
    question=...,
    choices=["Approve", "Reject"],
    clarify_id=clarify_id,
    session_key=f"hitl-{session_id}",
)
```

**pending_hitl.db write (durability before clarify):**
```python
# Source: hermes-skills/startup-hitl-scan.py (Phase 2 — production)
from hermes_skills.startup_hitl_scan import record_hitl_pause
row_id = record_hitl_pause(
    session_id=session_id,
    task_description=f"PR approval for task {task_id}: push {branch}",
    chat_id="7113965359",
)
```

**LiteLLM cost — OPTION B pattern (from aider_runner.py):**
```python
# Source: hermes-skills/aider_runner.py (Phase 3 — production)
# Cost tracking for aider calls is OPTION B (event marker only).
# For workshop/cost.py, the circuit breaker reads the shared vault markdown file,
# not LiteLLM's response_cost. LiteLLM proxy is Brain's responsibility; Workshop
# only reads and appends to the shared cost-ledger.md.
```

**gh CLI PR creation (subprocess, shell=False):**
```python
# Source: .planning/intel/constraints.md + L17/L18 LOCKED
import subprocess
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

**ADR frontmatter format (REQ-ws-011):**
```markdown
---
workshop.task_id: ab12
workshop.status: done
workshop.pr_url: https://github.com/caiobellizzi/test-workshop-sandbox/pull/42
system.created_by: workshop
date: 2026-05-21
---
# ADR: <task slug>
...
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `.schema()` / `.json()` | Pydantic v2 `.model_json_schema()` / `.model_validate_json()` | Pydantic 2.0 (2023) | v1 methods raise AttributeError in v2; aider-chat pins 2.12.5 so v2 API is mandatory |
| LangGraph StateGraph for pipeline | Hermes `delegate_task` + Python for-loops | v3 grill session (L22) | LangGraph removed entirely from Phase 1 scope |
| Brain HTTP `json={}` | Brain HTTP `data={}` (multipart/form-data) | Agno 2.6.7 | json= returns 422; data= is required (proven in Phase 3) |

**Deprecated/outdated:**
- `pydantic.BaseModel.schema()` — removed in v2; use `model_json_schema()`
- `pydantic.BaseModel.parse_raw()` — removed in v2; use `model_validate_json()`
- LangGraph in Phase 1 — LOCKED out by L22; reserved for Phase 2

---

## Open Questions

1. **Does Hermes v0.14.0 support Python skill body execution?**
   - What we know: All Phase 3 skills use `terminal python3 /path/to/script.py` from the SKILL.md body. The `delegate_task` and `clarify` tools are available in the Hermes execution context.
   - What's unclear: Whether the SKILL.md `## Body` section can contain Python code that calls `delegate_task` and `clarify` directly, or whether the pipeline must be invoked as a `terminal python3 workshop_build.py` subprocess that cannot access those tools.
   - Recommendation: **Wave 0 must include a VPS probe**: write a minimal test skill that calls `delegate_task` from its body and verify it works. If Python body skills are not supported, the pipeline orchestration moves to a separate `hermes-skills/workshop_build.py` that uses `hermes chat --skills` to drive each specialist sequentially. [ASSUMED]
   - Impact: If Python body is unsupported, `delegate_typed()` is not called in-process — instead, each specialist becomes a `hermes chat` subprocess call with `--skills <role>` and output captured.

2. **Does caiobellizzi/test-workshop-sandbox repo exist?**
   - What we know: L17 LOCKED as the Phase 1 blast-radius target. It was not verified to exist in any Phase 2/3 summary.
   - Recommendation: Wave 0 must check `gh repo view caiobellizzi/test-workshop-sandbox` and create it if absent: `gh repo create caiobellizzi/test-workshop-sandbox --public`.
   - Impact: Blocks all end-to-end testing if missing.

3. **Is gh CLI installed on VPS?**
   - What we know: Node.js 24 via nvm was installed in Phase 2 (02-01). The `gh` CLI (GitHub CLI) is a separate tool installed via apt or the GitHub releases page, not npm.
   - What's unclear: Whether `gh` was installed as part of Phase 2 or is still missing from the VPS.
   - Recommendation: Wave 0 must verify `which gh` and install via apt if missing: `apt-get install -y gh`.
   - Impact: Blocks PR creation if missing.

4. **Cost ledger markdown format — does Brain's curator accept `record-cost&amount=X&task=Y` message format?**
   - What we know: `POST /agents/curator/runs` with `message=record-cost&amount=X&task=Y` is documented in PROJECT.md Brain HTTP Contract and in PLAN.md. However, the curator was called in Phase 3 with a different message format (`aider task completed: cost_ledger_event status=success model=cloud-sonnet+private-worker task=...`).
   - What's unclear: Whether the `record-cost&amount=...` query-string format is how Brain's curator actually parses cost entries, or if it's a convention that Brain ignores.
   - Recommendation: Use the documented format from PROJECT.md. If the curator is an LLM agent, it will parse the message semantically regardless of format. Verify V11 after first `/build`.
   - Impact: Cost ledger entries may not be machine-parseable by the circuit breaker if Brain doesn't write them in the expected markdown format.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Hermes venv (Python 3.12) | workshop/ module | ✓ | Python 3.12.3 + venv at /opt/ultra-workshop/hermes/venv/ | — |
| pydantic | workshop/types.py | ✓ | 2.12.5 (aider-chat transitive dep, verified via PyPI JSON API) | — |
| httpx | brain_http.py | ✓ | 0.28.1 (already in venv, Phase 3) | — |
| aider-chat | coder role | ✓ | 0.86.2 (Phase 3) | — |
| bats | tests/phase-04/*.bats | ✓ | 1.10.0 (Phase 3, apt) | — |
| gh CLI | PR creation, issue fetch | ? | Unknown — not verified on VPS | apt-get install -y gh |
| GITHUB_PAT | gh auth, PR create | ? | Not provisioned (deferred from Phase 2 02-04) | Human-gate Wave 0 |
| test-workshop-sandbox | Target repo for PRs | ? | Existence not verified | gh repo create |
| 2GB swap | Aider subprocess RAM | ✓ | Active (Phase 2 02-01: /swapfile 2G in /etc/fstab) | — |
| Brain API at 127.0.0.1:7000 | cost ledger, ADR | ✓ | Agno 2.6.7 (Phase 3 verified) | — |
| /srv/second-brain (vault) | cost-ledger.md | ✓ | Phase 1 vault sync complete | — |

**Missing dependencies with no fallback:**
- GITHUB_PAT — must be provisioned by human in Wave 0 (no automation alternative)

**Missing dependencies with fallback:**
- gh CLI — Wave 0 installs via `apt-get install -y gh` if absent
- test-workshop-sandbox — Wave 0 creates via `gh repo create` if absent

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | bats 1.10.0 (system-wide on VPS) + pytest 7.x (in Hermes venv) |
| Config file | pyproject.toml (testpaths: hermes-skills, scripts) |
| Quick run command | `bats tests/phase-04/build-smoke.bats --dry-run-only` (VPS) |
| Full suite command | `bats tests/phase-04/*.bats` (VPS) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-ws-028 | delegate_typed() parses Pydantic schema and retries on failure | unit | `pytest tests/phase-04/test_orchestrator.py -x` | ❌ Wave 0 |
| REQ-ws-007 | workshop-build dry-run exits 0 | smoke | `bats tests/phase-04/build-smoke.bats` | ❌ Wave 0 |
| REQ-ws-007 | end-to-end /build → PR URL within ~5 min | e2e | manual / `bats tests/phase-04/build-e2e.bats` | ❌ Wave 2 |
| REQ-ws-008 | workshop-fix dry-run exits 0 | smoke | `bats tests/phase-04/fix-smoke.bats` | ❌ Wave 0 |
| REQ-ws-009 | task_ledger.md + progress_log.jsonl exist after build | unit | `pytest tests/phase-04/test_ledger.py -x` | ❌ Wave 0 |
| REQ-ws-010 | HITL gate appears; Approve creates PR; Reject aborts | e2e | manual (Telegram interaction required) | ❌ Wave 2 |
| REQ-ws-011 | ADR at vault/_system/workshop-adrs/<id>.md after PR | e2e | `ls /srv/second-brain/_system/workshop-adrs/` | ❌ Wave 2 |
| REQ-ws-012 | cost entry in ledger after /build | e2e | `grep "source: workshop" /srv/second-brain/_system/cost-ledger.md` | ❌ Wave 2 |
| REQ-ws-012 | circuit breaker refuses at $20 | unit | `pytest tests/phase-04/test_cost.py::test_hard_limit -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/phase-04/ -x` (unit tests only, ~5s)
- **Per wave merge:** `bats tests/phase-04/build-smoke.bats && pytest tests/phase-04/ -v`
- **Phase gate:** VPS e2e: `bats tests/phase-04/build-e2e.bats` + V7/V8/V10/V11/V12/V13 manual checks

### Wave 0 Gaps

- [ ] `tests/phase-04/test_orchestrator.py` — covers REQ-ws-028 delegate_typed retry logic
- [ ] `tests/phase-04/test_ledger.py` — covers REQ-ws-009 ledger file creation
- [ ] `tests/phase-04/test_cost.py` — covers REQ-ws-012 circuit breaker thresholds
- [ ] `tests/phase-04/build-smoke.bats` — covers REQ-ws-007 dry-run
- [ ] `tests/phase-04/fix-smoke.bats` — covers REQ-ws-008 dry-run
- [ ] `tests/phase-04/helpers.bash` — shared SSH helper (inherit from tests/phase-03/helpers.bash pattern)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | GITHUB_PAT in /etc/uws/env (EnvironmentFile, 0640 root:uws) — not in git |
| V3 Session Management | no | HITL uses pending_hitl.db row IDs, not user sessions |
| V4 Access Control | yes | allow_from: ["7113965359"] in Hermes config (already wired); ALLOWED_CHAT_ID check in pr_open.py |
| V5 Input Validation | yes | pydantic schema validation on all specialist outputs; `--task` passed as list element to subprocess (shell=False) |
| V6 Cryptography | no | No new crypto; GITHUB_PAT is plaintext env var (single-tenant VPS loopback) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Task prompt injection via `/build <crafted payload>` | Tampering | Passed as single list element to delegate_task goal (no shell expansion); pydantic validates output |
| GITHUB_PAT leak in git commit | Information Disclosure | EnvironmentFile /etc/uws/env (not in git); never printed to stdout in subprocess |
| PR creation without HITL approval | Elevation of Privilege | `record_hitl_pause()` + clarify gate before any `gh pr create`; Reject aborts and records in pending_hitl.db |
| Cost runaway from malicious /build loop | Denial of Service | Circuit breaker at $18/$20; hard retry caps (max 2 reviewer-coder, max 2 parse retries) |
| Unauthorized chat_id issuing /build | Spoofing | `allow_from: ["7113965359"]` in Hermes gateway config; `ALLOWED_CHAT_ID` check in pr_open.py |
| aider writing outside workspace | Tampering | aider_runner.py uses `cwd=workspace_dir`; shell=False; for pipeline, workspace = cloned sandbox repo |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Hermes v0.14.0 skill bodies can call `delegate_task` and `clarify` directly from Python body code | Architecture Patterns §Pattern 6 | Pipeline must be restructured as sequential `hermes chat --skills <role>` subprocess calls per specialist |
| A2 | `gh` CLI is available or can be installed on VPS via `apt-get install -y gh` | Environment Availability | Wave 0 must use alternative install method (snap, binary download) |
| A3 | `caiobellizzi/test-workshop-sandbox` repo exists or can be created by user | Open Questions #2 | Blocks all end-to-end tests |
| A4 | Brain curator agent accepts `record-cost&amount=X&task=Y` message format and writes a markdown entry with `source: workshop` | Code Examples (curator call) | Circuit breaker cannot read cost entries; V11/V21 fail |
| A5 | aider_runner.py can be invoked with `--workspace-file` pointing to a file inside a cloned repo (not just a temp workspace) | Pitfall 6 | Coder role produces diffs that don't apply to test-workshop-sandbox |
| A6 | Pydantic 2.12.5 is present in the Hermes venv as an aider-chat transitive dependency | Standard Stack | Need explicit `pip install pydantic==2.12.5` in Wave 0 |

---

## Sources

### Primary (HIGH confidence)

- `hermes-skills/aider_runner.py` — Phase 3 production code; subprocess wiring, cost-ledger OPTION B pattern, venv-relative binary path
- `hermes-skills/brain_http.py` — Phase 3 production code; `data={}` multipart/form-data pattern, `call_agent()` API
- `hermes-skills/startup-hitl-scan-hook/handler.py` — Phase 2 production code; `clarify_gateway.register()`, `adapter.send_clarify()`, `pending_hitl.db` pattern
- `hermes-skills/startup-hitl-scan.py` — Phase 2 production code; `record_hitl_pause()`, SQLite schema
- `.planning/PROJECT.md` — L1–L30 locked decisions, D1–D10 integration decisions, Brain HTTP contract
- `.planning/REQUIREMENTS.md` — REQ-ws-028, REQ-ws-007–012 acceptance criteria
- `.planning/phases/02-hermes-deploy/02-RESEARCH.md` — HITL durability analysis, clarify/delegate_task limitations
- `.planning/phases/03-skill-toolkit/03-05-SUMMARY.md` — aider_runner.py execution patterns, venv path resolution
- `.planning/phases/03-skill-toolkit/03-04-SUMMARY.md` — brain_http.py V4 relaxation, multipart/form-data pattern
- `pypi.org JSON API — aider-chat/0.86.2` — pydantic==2.12.5 pinned as direct dependency [VERIFIED]

### Secondary (MEDIUM confidence)

- `hermes-agent.nousresearch.com/docs/user-guide/features/delegation` — delegate_task API, subagent context isolation, clarify blocked in subagents [CITED]
- `hermes-agent.nousresearch.com/docs/user-guide/configuration` — delegation config (max_spawn_depth, max_concurrent_children) [CITED]
- `docs.litellm.ai/docs/completion/token_usage` — completion_cost() API, response._hidden_params["response_cost"] [CITED]
- `pypi.org/project/pydantic` — version 2.13.4 latest; 2.12.5 in venv [VERIFIED: PyPI registry]

### Tertiary (LOW confidence)

- `docs/ingest/PLAN.md §Day 4-5` — original implementation plan; used for structural guidance but pre-execution estimates
- `docs/ingest/PLAN.md §Brain HTTP Contract` — `record-cost&amount=X&task=Y` message format for curator [ASSUMED — not verified against live Brain curator behavior]

---

## Metadata

**Confidence breakdown:**
- Standard stack (Pydantic, httpx, gh): HIGH — all present in venv or well-known ecosystem tools
- Architecture (delegate_task, HITL, ledger): HIGH — derived from production Phase 2/3 code
- Pydantic v2 API: HIGH — verified from PyPI JSON API pinned version
- Hermes Python skill body API: LOW — delegate_task/clarify accessibility inside Python body is ASSUMED, not confirmed from live VPS test
- Cost ledger Brain curator format: LOW — message format is documented but not verified against live curator behavior

**Research date:** 2026-05-21
**Valid until:** 2026-06-21 (Hermes v0.14.0 is pinned; Brain Agno API is stable single-tenant)
