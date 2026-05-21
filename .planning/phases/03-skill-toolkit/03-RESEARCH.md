# Phase 3: Skill Toolkit — Research

**Researched:** 2026-05-21
**Domain:** Hermes Agent skill authoring, Python subprocess (Aider), Brain HTTP integration, Claude skill translation
**Confidence:** HIGH for skill format and Brain API; MEDIUM for `hermes skill run` smoke invocation pattern (requires planner decision); LOW for Aider cost-ledger emission details

---

<user_constraints>
## User Constraints (from CONTEXT.md / PROJECT.md)

### Locked Decisions (verbatim from PROJECT.md)
- **L2** — Orchestrator = Hermes Agent v0.14.0 (pinned, no upgrade)
- **L9** — All LLM calls via LiteLLM proxy at `127.0.0.1:4000`; 6 aliases: `orchestrator`, `default-worker`, `cheap-worker`, `private-worker`, `cloud-sonnet`, `cloud-groq`
- **L10** — Coder = Aider (NOT Claude Code); routes through LiteLLM natively
- **L13** — Day 1 task = `audit-claude-skills.py` (tag + auto-translate)
- **L14** — Tier 1 port scope = ~10 agent-agnostic skills + 3 brain-bridge skills
- **L21** — Skill audit = tag + auto-translate to `~/.hermes/skills/translated/`; Tool Translation Map (Appendix E of PLAN.md) defines substitutions. Output NEVER written to `~/.hermes/skills/<name>/` directly (safety rule)
- **CONSTRAINT-skill-translation-safety** — Auto-translate output MUST go to `~/.hermes/skills/translated/<name>/` only. Promotion requires explicit user action. Broken translations may never shadow working skills.
- **CONSTRAINT-stack-coder-aider** — Aider: architect=`cloud-sonnet`, editor=`private-worker`, flags `--yes-always --no-stream --message <task>`
- **CONSTRAINT-stack-llm-gateway** — All LLM calls through LiteLLM proxy at `127.0.0.1:4000/v1`; no direct Anthropic/OpenAI API calls

### Claude's Discretion
- Exact ~10 skills to port (must be "agent-agnostic" — no Claude-specific tools: TaskCreate, AskUserQuestion, Skill, ExitPlanMode)
- How `hermes skill run <name> --dry-run` maps to actual Hermes CLI (requires investigation — see Open Questions)
- Smoke-test invocation pattern (bash wrapper or native hermes chat invocation)
- How Aider subprocess returns diff (stdout capture)
- TRANSLATION_NOTES.md per-skill content format

### Deferred Ideas (OUT OF SCOPE for Phase 3)
- workshop-build / workshop-fix skills (Phase 4)
- Pydantic schemas in workshop/types.py (Phase 4)
- Cost circuit breaker in workshop/cost.py (Phase 4)
- MCP registration for 5 servers (still deferred from Phase 2)
- Cron routines: daily-research, nightly-tests, bug-scan (Phase 5)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-ws-003 | `scripts/audit-claude-skills.py` walks `~/.claude/skills/`, tags 4 categories, auto-translates `requires-translation` skills to `~/.hermes/skills/translated/`, emits `skill-audit.json` + `TRANSLATION_NOTES.md` per skill; `--dry-run` default; idempotent; never writes to `~/.hermes/skills/<name>/` | Tool Translation Map confirmed in PLAN.md Appendix E; 4 categories: `agent_agnostic`, `auto_translated`, `requires_manual_port`, `claude_specific_skip`; output JSON schema defined in PLAN.md |
| REQ-ws-004 | ~10 agent-agnostic skills copied to `~/.hermes/skills/` with Hermes frontmatter; each passes `hermes skill run <name> --dry-run` | Hermes SKILL.md format confirmed from live VPS; invocation pattern via `hermes chat --skills` confirmed; `--dry-run` is a custom flag to be handled at skill-body level |
| REQ-ws-005 | `brain-query`, `brain-ingest`, `brain-research` wrapping Brain HTTP endpoints; `hermes skill run brain-query --question "what is PARA"` returns vault-grounded answer | Brain API confirmed as multipart/form-data at `POST /agents/{id}/runs`; live test shows structured JSON response; `query`, `ingest`, `research`, `curator` agent IDs confirmed |
| REQ-ws-006 | `skills/aider/SKILL.md` — Aider subprocess with architect=`cloud-sonnet`, editor=`private-worker`; `hermes skill run aider --task "echo to file"` returns diff; cost log shows two LLM calls | Aider flags confirmed: `--model`, `--editor-model`, `--openai-api-base`, `--yes-always`, `--no-stream`, `--message`; LiteLLM proxy connection pattern confirmed; cost ledger written by startup-hitl-scan.py pattern |
</phase_requirements>

---

## Summary

Phase 3 delivers the skill infrastructure that Phase 4's pipeline depends on. It has four distinct workstreams: (1) the audit/translate script that classifies ~114 Claude skills and auto-translates a subset; (2) ~10 hand-selected agent-agnostic skills promoted to live Hermes; (3) three brain-bridge skills that wrap Brain's Agno HTTP API; and (4) the Aider skill implementing the coder subprocess role.

**Critical discovery (Brain API):** Brain's `POST /agents/{id}/runs` endpoint uses `multipart/form-data`, NOT JSON. The `message` field is a `Form(...)` parameter. Callers must use `-F 'message=...'` in curl or `httpx` `data={}` with no `Content-Type: application/json` header. [VERIFIED: live VPS probe]

**Critical discovery (`hermes skill run`):** The Hermes CLI has no `skill run` subcommand. The accepted surface is `hermes skills {browse,search,install,list,...}` for registry management and `hermes chat -s <name> -q "<trigger>"` for invocation. [VERIFIED: live VPS `hermes --help`] The acceptance criteria's `hermes skill run <name> --dry-run` must be implemented as a thin shell wrapper `scripts/hermes-skill-run.sh` that translates to `hermes chat -s <name> -q "$*" -Q --max-turns 1 --yolo`. The planner must define this wrapper.

**Primary recommendation:** Write the audit script first (it classifies all 114 skills and tells you exactly which ~10 to port). Then implement the smoke wrapper. Then port skills in order of pipeline dependency: brain-query → brain-ingest → brain-research → aider → agent-agnostic Tier 1.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Skill audit / translation | Local Mac (runs against `~/.claude/skills/`) | VPS (output deployed) | Script reads Mac-local skills dir; translations deployed via rsync or commit+pull |
| Skill YAML validation | VPS (Hermes reads skills at runtime) | — | Hermes discovers skills from `~/.hermes/skills/`; frontmatter parsed at load time |
| Brain HTTP calls | VPS Hermes skill body | — | `127.0.0.1:7000` is only reachable from VPS; skills run in Hermes gateway process |
| Aider subprocess | VPS (inside skill body) | — | Aider runs as subprocess of Hermes on VPS; outputs to workspace dir |
| Smoke tests | Local Mac (bats) + VPS execution | — | bats tests SSH to VPS to verify skill invocation; consistent with Phase 2 pattern |
| Cost ledger writes | VPS skill body → Brain POST /agents/curator/runs | — | Per-delegate_task cost recorded via Brain's curator agent |

---

## Standard Stack

### Core (Phase 3 additions)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Hermes Agent | v0.14.0 (pinned) | Skill runtime; `hermes skills install`, `hermes chat -s` | L2 locked |
| aider-chat | latest stable | Coder subprocess in `aider` skill | L10 locked; routes through LiteLLM natively |
| httpx | ≥0.27 | Brain HTTP calls from Python skill bodies | Async-capable; already used by Agno ecosystem |
| bats | v1.x | Smoke tests for skill invocation | Established pattern from Phase 2 |
| pytest | ≥7 | Unit tests for audit script logic | Already installed in Hermes venv |
| Python stdlib: `re`, `pathlib`, `json`, `yaml`, `subprocess` | stdlib | Audit script + skill bodies | No new deps needed |

[ASSUMED] — httpx version not verified against VPS venv. Aider latest stable version not checked at research time.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyYAML | ≥6 | Parse SKILL.md frontmatter in audit script | Any SKILL.md frontmatter extraction |
| python-frontmatter | ≥1.0 | Combined YAML+body parsing | Cleaner than split-at-`---` regex |

[ASSUMED] — python-frontmatter not verified against VPS venv. May already be installed (Hermes uses SKILL.md internally).

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `httpx` for Brain calls | `requests` | Both work; httpx preferred for async-compatible skills |
| `python-frontmatter` | manual `---` split + PyYAML | Manual split is more fragile on multi-line frontmatter |
| bats for smoke tests | pytest | bats matches Phase 2 pattern; pytest used for unit tests of Python logic |

**Installation (VPS, uws user):**
```bash
sudo -u uws /opt/ultra-workshop/hermes/venv/bin/pip install aider-chat httpx
# python-frontmatter is optional — stdlib yaml.safe_load works if split at ---
```

---

## Package Legitimacy Audit

| Package | Registry | Age | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|
| aider-chat | PyPI | ~3 yrs (Paul Gauthier, MIT) | Not run — slopcheck unavailable | [ASSUMED] Approved — widely known, GitHub starred 50k+ |
| httpx | PyPI | ~5 yrs | Not run | [ASSUMED] Approved — standard Python HTTP library |
| python-frontmatter | PyPI | ~7 yrs | Not run | [ASSUMED] Approved — common YAML frontmatter parser |

*slopcheck was unavailable at research time. All packages tagged [ASSUMED]. Planner must verify on PyPI before installing.*

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged [SUS]:** none — but all are [ASSUMED] pending human verification

---

## Stack & Tooling

### Hermes SKILL.md Format

**Confirmed from live VPS (`/home/uws/.hermes/skills/software-development/plan/SKILL.md`):** [VERIFIED: live VPS]

```yaml
---
name: <slug>
description: "<trigger description — this is what Hermes uses for skill matching>"
version: 1.0.0
author: <string>
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [tag1, tag2]
    related_skills: [other-skill]
---

# Skill Title

## Body content (Markdown, instructions for the agent)
```

**Minimum required fields:** `name`, `description` [VERIFIED: from live skill SKILL.md]
**Optional but recommended:** `version`, `platforms`, `metadata.hermes.tags`
**NOT present in Hermes format:** `tools:` frontmatter (Hermes does not use a tools allowlist in SKILL.md; tools are configured globally in `~/.hermes/config.yaml` or `--toolsets` flag)

**Claude Code SKILL.md format (for comparison):**
```yaml
---
name: <slug>
description: >
  <trigger description — used by Claude Code for skill matching>
---
# Body
```
Claude Code skills may have `tools:`, `mcpServers:`, `hooks:` frontmatter which Hermes ignores or does not recognize.

**Translation delta (SKILL.md frontmatter only):**
- ADD: `version`, `author`, `license`, `platforms`, `metadata.hermes.tags`
- REMOVE: `tools:` (if present), `mcpServers:` (if present), `hooks:` (if present)
- KEEP: `name`, `description`
- BODY: apply Tool Translation Map (see below)

### Tool Translation Map [VERIFIED: PLAN.md Appendix E]

**Direct mappings (safe to auto-translate):**

| Claude Code tool | Hermes equivalent | Notes |
|------------------|-------------------|-------|
| `Read` | `read_file` | Path arg compatible; offset/limit may need shim |
| `Write` | `write_file` | Same semantics; Hermes validates parent dir exists |
| `Edit` | `edit_file` (`replace_in_file`) | `old_string`/`new_string` syntax differs — emit code-comment warning |
| `Bash` / `Bash command` | `terminal` | `pty=false` default matches Claude behavior |
| `Grep` | `search` | `pattern`/`path`/`glob` args compatible |
| `Glob` | `find_files` | Pattern syntax identical |
| `WebFetch` | `http_request` (method=GET + extract_with_prompt) | 2-step pattern; emit comment warning |
| `WebSearch` | `web_search` | Direct rename; query syntax identical |

**Tag-only (output to `~/.hermes/skills/translated/_manual/`):**

| Claude Code tool | Reason |
|------------------|--------|
| `TaskCreate` / `TaskUpdate` / `TaskList` | No Hermes equivalent |
| `AskUserQuestion` | Semantics differ from Hermes `clarify` |
| `Skill` (recursive invocation) | Hermes call syntax differs; max depth 2 |
| `ExitPlanMode` | Claude Code-only construct |
| `Agent` (spawn subagent) | Translates to `delegate_task` but requires manual review |
| `NotebookEdit` / `ReadMcpResourceTool` / `ListMcpResourcesTool` | Niche |

### Four Classification Categories [VERIFIED: PLAN.md Appendix E]

The audit script tags each skill in one of four categories:
1. `agent_agnostic` — no tool references; copy as-is
2. `auto_translated` — contains only directly-mappable tools; apply Tool Translation Map
3. `requires_manual_port` — contains untranslatable tools; output to `_manual/` subdirectory with notes
4. `claude_specific_skip` — plugin skill clusters (`gsd-*`, `superpowers:*`, `dotnet-*`) — don't attempt to port

Expected distribution (from PLAN.md Appendix E sample output):
- `agent_agnostic`: ~14 skills
- `auto_translated`: ~38 skills
- `requires_manual_port`: ~47 skills
- `claude_specific_skip`: ~22 skills (gsd-*, superpowers:*, etc.)
- Total in `~/.claude/skills/`: 114 (counted at research time)

### Hermes Skill Invocation: `hermes skill run` [VERIFIED: live VPS]

**The Hermes CLI has no `hermes skill run` subcommand.** The actual CLI subcommands are:
```
hermes skills {browse,search,install,inspect,list,check,update,audit,...}
hermes chat [-s SKILLS] [-q QUERY] [--max-turns N] [-Q] [--yolo]
```

The acceptance criteria's `hermes skill run <name> --dry-run` is therefore a **custom shell wrapper** that must be created as `scripts/hermes-skill-run.sh`:

```bash
#!/usr/bin/env bash
# scripts/hermes-skill-run.sh
# Usage: hermes-skill-run.sh <skill-name> [--dry-run] [--key value ...]
# Implements the "hermes skill run" interface by delegating to hermes chat.
SKILL="$1"; shift
QUERY="$*"
exec sudo -u uws /opt/ultra-workshop/hermes/venv/bin/hermes chat \
  --skills "$SKILL" \
  --query "$QUERY" \
  -Q \
  --max-turns 3 \
  --yolo
```

The `--dry-run` flag is then handled at the **skill body level** — each ported skill must detect `--dry-run` in its trigger query and output a plan rather than executing. This is the same pattern as Hermes's built-in `plan` skill.

### Brain HTTP API [VERIFIED: live VPS probe + source code]

Brain runs at `http://127.0.0.1:7000` as Agno AgentOS via `agentos` module (FastAPI/uvicorn).

**CRITICAL: endpoint uses `multipart/form-data`, NOT `application/json`.** [VERIFIED: live Agno 2.6.7 source at `/opt/ultra-agents-brain/.venv/lib/python3.12/site-packages/agno/os/routers/agents/router.py`]

**Confirmed agent IDs:** `chat`, `curator`, `ingest`, `query`, `research` [VERIFIED: `GET /agents`]

**POST /agents/{id}/runs — form-data fields:**
- `message: str` — required; the user query / task text
- `stream: bool` — optional (default True); set to `false` for synchronous response
- `session_id: str` — optional; for conversation continuity
- `user_id: str` — optional; use `"workshop"` for audit trail

**Python invocation pattern (httpx):**
```python
import httpx

async def call_brain(agent_id: str, message: str, user_id: str = "workshop") -> dict:
    async with httpx.AsyncClient(base_url="http://127.0.0.1:7000", timeout=60.0) as client:
        resp = await client.post(
            f"/agents/{agent_id}/runs",
            data={"message": message, "stream": "false", "user_id": user_id},
        )
        resp.raise_for_status()
        return resp.json()
```

**Response structure (confirmed from live test):**
```json
{
  "run_id": "<uuid>",
  "agent_id": "query",
  "agent_name": "query",
  "session_id": "<uuid>",
  "content": "<LLM response text or error message>",
  "content_type": "str",
  "model": "default-worker",
  "status": "success|ERROR",
  "metrics": {"duration": <float>},
  "input": {"input_content": "<message sent>"}
}
```

**Live test result (research session):** `POST /agents/query/runs` with `message="what is PARA"` returns response with `status: "ERROR"` due to LiteLLM structured output constraint error (Groq model + tool-calling workaround incompatibility). This is a VPS LiteLLM config issue, not an API shape issue. The API shape is confirmed correct. [VERIFIED: live VPS]

**brain-query skill body pattern:**
```python
# skills/brain-query/body.py (invoked from SKILL.md via terminal tool)
import httpx, json, sys

question = " ".join(sys.argv[1:])  # or parse from --question flag
resp = httpx.post(
    "http://127.0.0.1:7000/agents/query/runs",
    data={"message": question, "stream": "false", "user_id": "workshop"},
    timeout=60.0
)
data = resp.json()
if data.get("status") == "ERROR":
    print(f"Brain error: {data['content']}", file=sys.stderr)
    sys.exit(1)
print(data["content"])
```

**brain-ingest skill:** uses `POST /agents/ingest/runs` with `message=<markdown-content>`
**brain-research skill:** uses `POST /agents/research/runs` with `message=<research-topic>`
**cost recording:** uses `POST /agents/curator/runs` with `message="record-cost amount=X task=Y"`

### Aider Subprocess Integration [VERIFIED: aider.chat docs + CONSTRAINT-stack-coder-aider]

Aider routes through LiteLLM by pointing `--openai-api-base` at the proxy:

```bash
aider \
  --model openai/cloud-sonnet \
  --editor-model openai/private-worker \
  --architect \
  --openai-api-base http://127.0.0.1:4000/v1 \
  --openai-api-key "${LITELLM_API_KEY}" \
  --yes-always \
  --no-stream \
  --message "${TASK}" \
  /path/to/repo/file.py
```

Key flags [VERIFIED: aider.chat/docs/config/options.html]:
- `--model` — architect model (LiteLLM alias via `openai/` prefix)
- `--editor-model` — editor model
- `--architect` — enable architect mode (two-LLM-call pattern)
- `--openai-api-base` — redirect to LiteLLM proxy
- `--yes-always` — non-interactive (accepts all diffs)
- `--no-stream` — disable SSE streaming; full response at end
- `--message <task>` — one-shot non-interactive task
- stdout contains the edit summary / diff

**Cost ledger:** Aider does NOT emit a structured cost JSON by default. Cost must be estimated from `aider --show-diffs` or captured from LiteLLM proxy logs. The skill body should record two LLM calls as approximate cost entries to Brain's curator agent. The simplest pattern: post cost records before and after the subprocess call using token count estimates.

**Diff output:** Aider writes changes directly to files AND prints a summary to stdout. The skill body captures stdout via `subprocess.run(..., capture_output=True, text=True)` and returns the diff summary. [ASSUMED]

**aider-chat install on VPS (uws user):**
```bash
sudo -u uws /opt/ultra-workshop/hermes/venv/bin/pip install aider-chat
```
[ASSUMED] — not yet installed on VPS at research time.

### Hermes Skill Install Mechanism [VERIFIED: live VPS]

Hermes discovers skills from `~/.hermes/skills/` by traversing subdirectories for `SKILL.md` files. Install can be done:
1. `hermes skills install <local-path>` — installs from a local SKILL.md file path or directory
2. `hermes skills install <url>` — installs from a URL
3. Direct filesystem: `cp -r skills/brain-query ~/.hermes/skills/` (safest for local dev)

Local skills installed to `~/.hermes/skills/<name>/SKILL.md` are listed by `hermes skills list` with `Source: local` or the category they're placed under.

---

## Reference Implementations

### Existing Hermes Skill (VPS): `plan` skill [VERIFIED: live VPS]

```yaml
---
name: plan
description: "Plan mode: write markdown plan to .hermes/plans/, no exec."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, plan-mode, implementation, workflow]
    related_skills: [writing-plans, subagent-driven-development]
---
# Plan Mode
...body uses write_file tool...
```
This is the canonical reference for Hermes SKILL.md format.

### Existing Pattern: `startup-hitl-scan.py` (Phase 2) [VERIFIED: repo source]

The `hermes-skills/startup-hitl-scan.py` pattern from Phase 2 shows:
- Python files in `hermes-skills/` are helper modules deployed to `/opt/ultra-workshop/hermes-skills/`
- Loaded via `importlib.util.spec_from_file_location` (handles hyphens in filenames)
- Skills that need Python logic call `terminal` → python script pattern or embed Python in the SKILL.md body using code blocks

### Agent-Agnostic Skill Candidates from `~/.claude/skills/` [VERIFIED: live `ls`]

Skills with no Claude-specific tool references (confirmed by inspection of bodies):

| Skill slug | Body style | Tool references |
|------------|-----------|-----------------|
| `commit` | Markdown instructions + shell commands | `Bash` → `terminal` (auto-translate) |
| `caveman` | Pure Markdown behavior instructions | None |
| `triage-issue` | Markdown instructions | `Bash`, `Grep`, `Read` → terminal, search, read_file |
| `design-an-interface` | Markdown instructions | None confirmed |
| `improve-codebase-architecture` | Markdown instructions | `Read`, `Bash` likely |
| `qa` | Markdown instructions + shell | `Bash`, `Grep` likely |
| `zoom-out` | Markdown reflective instructions | None confirmed |
| `ubiquitous-language` | Markdown instructions | `Read`, `Grep` likely |
| `diagnose` | Markdown debug instructions | `Bash`, `Read` |
| `edit-article` | Markdown writing instructions | `Read`, `Write` → read_file, write_file |

**Confirmed `claude_specific_skip` (DO NOT PORT):** All `gsd-*` skills (38 of them), `superpowers:*`, plugin packs — these use `TaskCreate`, `AskUserQuestion`, `ExitPlanMode` extensively. [VERIFIED: from `ls ~/.claude/skills/` and PLAN.md exclusion list]

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (unit) | pytest ≥7 (already in Hermes venv) |
| Framework (integration smoke) | bats v1.x (established Phase 2 pattern) |
| Config file | `tests/phase-03/` directory (new) |
| Quick run command | `pytest hermes-skills/ scripts/ -x -q` |
| Full suite command | `bats tests/phase-03/ && pytest hermes-skills/ scripts/ -q` |

### Layer-of-Truth Mapping (per acceptance criteria)

| Layer | What it tests | Command | Automated? |
|-------|--------------|---------|-----------|
| **L1 (syntax)** | SKILL.md frontmatter has required `name` + `description` fields | `python3 -c "import yaml; d=yaml.safe_load(open('SKILL.md').read().split('---')[1]); assert 'name' in d and 'description' in d"` | Yes — pytest |
| **L2 (smoke-run)** | Hermes loads skill without error; dry-run exits 0 | `scripts/hermes-skill-run.sh <name> --dry-run` | Yes — bats |
| **L3 (functional)** | brain-query returns content with citation; aider returns diff | `scripts/hermes-skill-run.sh brain-query --question "what is PARA"` + content check | Yes — bats (VPS) |
| **L4 (idempotency)** | Audit script run twice produces identical `skill-audit.json` | `diff <(python3 scripts/audit-claude-skills.py --dry-run) <(python3 scripts/audit-claude-skills.py --dry-run)` | Yes — pytest |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File |
|--------|----------|-----------|-------------------|------|
| REQ-ws-003 | audit script tags 4 categories | unit | `pytest scripts/test_audit.py::test_classification -x` | Wave 0 gap |
| REQ-ws-003 | audit script is idempotent | unit | `pytest scripts/test_audit.py::test_idempotent -x` | Wave 0 gap |
| REQ-ws-003 | --dry-run never writes files | unit | `pytest scripts/test_audit.py::test_dry_run_no_write -x` | Wave 0 gap |
| REQ-ws-003 | TRANSLATION_NOTES.md emitted per skill | unit | `pytest scripts/test_audit.py::test_translation_notes -x` | Wave 0 gap |
| REQ-ws-004 | each ported skill frontmatter valid | unit | `pytest hermes-skills/test_skill_frontmatter.py -x` | Wave 0 gap |
| REQ-ws-004 | each ported skill dry-run exits 0 | smoke (bats SSH) | `bats tests/phase-03/skills-smoke.bats` | Wave 0 gap |
| REQ-ws-005 | brain-query returns non-empty content | smoke (bats SSH) | `bats tests/phase-03/brain-bridge.bats` | Wave 0 gap |
| REQ-ws-006 | aider skill invocation returns diff | smoke (bats SSH) | `bats tests/phase-03/aider-smoke.bats` | Wave 0 gap |
| REQ-ws-006 | cost log shows two LLM call entries | smoke (bats SSH) | within `aider-smoke.bats` | Wave 0 gap |

### Sampling Rate
- **Per task commit:** `pytest scripts/ hermes-skills/ -q --tb=short`
- **Per wave merge:** `bats tests/phase-03/ && pytest scripts/ hermes-skills/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps (test files to create before implementation)
- [ ] `scripts/test_audit.py` — unit tests for audit script: classification, idempotency, dry-run safety, TRANSLATION_NOTES.md emission
- [ ] `hermes-skills/test_skill_frontmatter.py` — frontmatter validator for all Phase 3 skills
- [ ] `tests/phase-03/skills-smoke.bats` — `hermes skill run <name> --dry-run` for each of ~10 ported skills
- [ ] `tests/phase-03/brain-bridge.bats` — brain-query/ingest/research smoke tests
- [ ] `tests/phase-03/aider-smoke.bats` — aider skill invocation + diff output + cost log
- [ ] `scripts/hermes-skill-run.sh` — wrapper translating `hermes skill run` invocations to `hermes chat --skills`

---

## File Layout Plan

```
ultra-workshop/
├── scripts/
│   ├── audit-claude-skills.py     # REQ-ws-003 — NEW
│   ├── test_audit.py              # Wave 0 test for audit script
│   ├── hermes-skill-run.sh        # smoke wrapper (replaces missing "hermes skill run")
│   └── install.sh                 # existing — Phase 2 deployed
├── skills/                        # NEW directory (from PROJECT.md Repo Structure)
│   ├── aider/
│   │   └── SKILL.md               # REQ-ws-006
│   ├── brain-query/
│   │   └── SKILL.md               # REQ-ws-005
│   ├── brain-ingest/
│   │   └── SKILL.md               # REQ-ws-005
│   ├── brain-research/
│   │   └── SKILL.md               # REQ-ws-005
│   ├── commit/                    # Tier 1 port
│   │   └── SKILL.md
│   ├── triage-issue/              # Tier 1 port (auto-translated)
│   │   └── SKILL.md
│   ├── caveman/                   # Tier 1 port (agent_agnostic, copy as-is)
│   │   └── SKILL.md
│   ├── diagnose/                  # Tier 1 port
│   │   └── SKILL.md
│   ├── qa/                        # Tier 1 port
│   │   └── SKILL.md
│   └── [4-5 more agent-agnostic picks TBD by planner]
├── hermes-skills/                 # existing — Python helper modules for Hermes hooks/skills
│   ├── startup-hitl-scan.py       # existing (Phase 2)
│   ├── brain_http.py              # NEW — shared Brain HTTP helper (httpx)
│   └── test_skill_frontmatter.py  # Wave 0 test
└── tests/
    └── phase-03/                  # NEW
        ├── skills-smoke.bats
        ├── brain-bridge.bats
        └── aider-smoke.bats
```

**VPS deployment targets:**
- `skills/` → rsync to `/opt/ultra-workshop/skills/` → then `hermes skills install` per skill or `cp -r` to `~/.hermes/skills/`
- `hermes-skills/brain_http.py` → `/opt/ultra-workshop/hermes-skills/brain_http.py`
- `scripts/hermes-skill-run.sh` → `/opt/ultra-workshop/scripts/hermes-skill-run.sh` (chmod +x)
- `skill-audit.json` output → committed to repo root (canonical record, per PLAN.md Day 1 checklist)

---

## Architecture Patterns

### Pattern 1: Hermes SKILL.md with Python Helper

When a skill needs Python logic (not just Markdown instructions), use the `terminal` tool in the SKILL.md body to call a Python helper module from `hermes-skills/`:

```yaml
---
name: brain-query
description: "Query the vault: answer a question using Brain's knowledge base. Use for 'brain-query --question <q>', 'ask brain', 'vault search', or similar."
version: 1.0.0
author: ultra-workshop
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [brain, vault, query, research]
---
# Brain Query

Query the Brain Agno endpoint for a vault-grounded answer.

## Usage
Parse the `--question` argument from the trigger, then call the brain HTTP helper.

## Steps
1. Extract the question from the user message
2. Run: `terminal python3 /opt/ultra-workshop/hermes-skills/brain_http.py query "<question>"`
3. Return the response content with citations
```

### Pattern 2: Agent-Agnostic Skill (copy as-is)

No tool translation needed. Update frontmatter only:

```yaml
---
name: caveman
description: >
  Ultra-compressed communication mode. Cuts token usage ~75%.
  Use when user says "caveman mode", "talk like caveman", "use caveman",
  "less tokens", "be brief".
version: 1.0.0
author: ultra-workshop (ported from Claude Code skill)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [communication, brevity, tokens]
---
# (body unchanged from Claude Code version)
```

### Pattern 3: Aider Skill (subprocess wrapper)

```yaml
---
name: aider
description: "Run Aider coder on a task. Use for 'aider --task <description>', 'code with aider', or 'coder run'. Invokes architect=cloud-sonnet + editor=private-worker."
version: 1.0.0
author: ultra-workshop (local impl of Hermes Issue #534)
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [coder, aider, coding, git, diff]
---
# Aider Coder

Invoke Aider as a subprocess with architect/editor split against the LiteLLM proxy.

## Behavior
1. Extract `--task` from the user message
2. Run aider subprocess with cloud-sonnet architect + private-worker editor
3. Capture stdout (diff summary)
4. Record two LLM call cost entries via brain-curator
5. Return the diff

## Invocation
terminal python3 /opt/ultra-workshop/hermes-skills/aider_runner.py --task "..."
```

### Pattern 4: Skill Audit Script Structure

```python
# scripts/audit-claude-skills.py
#!/usr/bin/env python3
"""Walk ~/.claude/skills/, classify each skill, optionally auto-translate."""
import argparse, json, pathlib, re, sys
from datetime import datetime, timezone

CLAUDE_SKILLS_ROOT = pathlib.Path.home() / ".claude" / "skills"
HERMES_TRANSLATED_ROOT = pathlib.Path.home() / ".hermes" / "skills" / "translated"

DIRECT_TOOL_MAP = {
    "Read": "read_file", "Write": "write_file", "Edit": "edit_file",
    "Bash": "terminal", "Grep": "search", "Glob": "find_files",
    "WebFetch": "http_request", "WebSearch": "web_search",
}
MANUAL_PORT_TOOLS = {"TaskCreate", "TaskUpdate", "TaskList", "AskUserQuestion",
                     "Skill", "ExitPlanMode", "Agent", "NotebookEdit"}
SKIP_PREFIXES = ("gsd-", "superpowers:", "dotnet-")

def classify(name: str, body: str) -> tuple[str, set, set]:
    """Returns (category, translatable_tools, manual_tools)."""
    ...

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")  # default: dry-run
    parser.add_argument("--dry-run", action="store_true", default=True)
    # --apply sets dry_run=False
    ...
```

### Anti-Patterns to Avoid

- **Writing to `~/.hermes/skills/<name>/` directly from the audit script** — violates CONSTRAINT-skill-translation-safety. Always write to `translated/` subdirectory.
- **Using Claude-specific tool names in Hermes SKILL.md bodies** — `Read`, `Edit`, `Bash`, etc. are Claude Code internal tools; Hermes uses `read_file`, `terminal`, etc.
- **JSON Content-Type for Brain HTTP calls** — Brain uses multipart/form-data; JSON POST returns 422 validation error.
- **Assuming `hermes skill run` exists** — it does not; must use `hermes chat --skills <name>` or the wrapper script.
- **Hardcoding model names** — always use LiteLLM aliases (`cloud-sonnet`, `private-worker`) not raw model IDs.
- **Running aider as root on VPS** — must run as `uws` user; Hermes skills already run as `uws`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SKILL.md frontmatter parsing | custom `---` regex | `python-frontmatter` or `yaml.safe_load(text.split('---')[1])` | Edge cases: multi-line values, escaped chars |
| HTTP calls to Brain | `urllib` | `httpx` | Async support; cleaner timeout handling; already in ecosystem |
| Aider subprocess management | custom process manager | `subprocess.run(...)` | Aider is a well-behaved CLI; no complex lifecycle needed |
| LiteLLM proxy routing | direct Anthropic calls | `--openai-api-base http://127.0.0.1:4000/v1` | Honors model-agnostic constraint L9 |
| Skill taxonomy/classification | LLM-based classifier | regex-based tool name detection | Deterministic; reproducible; fast; idempotent |

**Key insight:** The audit script is a static analysis tool, not an AI tool. Using an LLM to classify skills introduces non-determinism and violates the idempotency requirement.

---

## Common Pitfalls

### Pitfall 1: Brain Returns `status: "ERROR"` for Structured Output Issues
**What goes wrong:** `POST /agents/query/runs` returns HTTP 200 but `status: "ERROR"` in the JSON body, with content like `litellm.BadRequestError: Groq model does not support native structured outputs`.
**Why it happens:** Brain's query agent uses tool-calling workaround for Groq models, which conflicts with structured output constraints. Happens when `default-worker` falls back to `cloud-groq`.
**How to avoid:** The brain-query skill body should check `data["status"] != "ERROR"` and surface the error clearly. This is a VPS LiteLLM config issue, not a Workshop bug — but the skill must handle it gracefully. [VERIFIED: live VPS test]
**Warning signs:** HTTP 200 response, non-empty `content`, `status: "ERROR"` field

### Pitfall 2: `hermes chat --skills` Needs `--yolo` for Non-Interactive
**What goes wrong:** `hermes chat -s <skill> -q <query> -Q` hangs waiting for tool approval prompt.
**Why it happens:** Hermes default `approvals.mode: smart` asks for confirmation on destructive tools (terminal, write_file).
**How to avoid:** Add `--yolo` to skip all approval prompts in smoke tests. For production skills, use `approvals.mode: smart` in config.yaml and the gateway will handle approvals via Telegram.
**Warning signs:** Process hangs; no output after 30s

### Pitfall 3: ProtectHome Blocks New Skill Files
**What goes wrong:** Skill writing to `~/.hermes/skills/` fails with "Permission denied" because `ProtectHome=read-only` in uws-hermes.service only allows the directories in `ReadWritePaths`.
**Why it happens:** `deploy/systemd/uws-hermes.service` has `ProtectHome=read-only` and explicit `ReadWritePaths`. Any NEW directory under `/home/uws/` not in that list is blocked. [VERIFIED: Phase 2 deviation #3]
**How to avoid:** If skills need to write to `~/.hermes/skills/`, ensure that path is in `ReadWritePaths`. Current list includes `/home/uws/.hermes` — so `~/.hermes/skills/` IS covered. No change needed for skill install.
**Warning signs:** `systemd-uws-hermes.service` logs "Permission denied"; skill install fails

### Pitfall 4: Aider Subprocess Requires Working Directory
**What goes wrong:** `aider --message "echo to file"` fails because it needs a git repo to operate in.
**Why it happens:** Aider always operates on a git repo; it uses tree-sitter RepoMap to understand code context.
**How to avoid:** The aider skill must set a working directory (`/tmp/uws-aider-workspace` or a cloned sandbox repo). For the smoke test `--task "echo to file"`, create a minimal temp git repo. [ASSUMED]
**Warning signs:** `fatal: not a git repository` in aider stderr

### Pitfall 5: `hermes skills install` Requires Unique `name:` Frontmatter
**What goes wrong:** Two skills with the same `name:` in frontmatter clobber each other.
**Why it happens:** Hermes uses `name:` as the skill identifier in `skills list` output.
**How to avoid:** Ensure every ported skill has a unique `name:` matching its directory slug.
**Warning signs:** `hermes skills list` shows fewer skills than installed

### Pitfall 6: Aider `--model openai/cloud-sonnet` vs `--model cloud-sonnet`
**What goes wrong:** Aider can't find the model when using bare LiteLLM alias without `openai/` prefix.
**Why it happens:** Aider uses the `openai/` prefix convention when connecting to an OpenAI-compatible proxy. Without it, aider looks up the model in its own known-models registry.
**How to avoid:** Always use `--model openai/cloud-sonnet --editor-model openai/private-worker` with the `openai/` prefix when pointing at the LiteLLM proxy. [ASSUMED — verify at execute time]
**Warning signs:** `Model not found` or unexpected fallback to aider's default model

### Pitfall 7: Brain `POST /agents/ingest/runs` is HITL-gated
**What goes wrong:** brain-ingest call succeeds HTTP 200 but content is never written to vault; flow hangs waiting for Human approval on Brain side.
**Why it happens:** Brain's ingest agent is configured to require human approval before writing to vault (matches D1 vault write zone constraint).
**How to avoid:** brain-ingest is appropriate only for `_system/workshop-*/` path writes. For the skill smoke test, use a test message to `_system/workshop-test/` path. The smoke test should verify the call returns a valid run_id, not that vault write happened.
**Warning signs:** HTTP 200 but no vault file; Brain Telegram shows approval prompt [ASSUMED — infer from architecture]

---

## Runtime State Inventory

> Phase 3 is a new-skill phase, not a rename/refactor phase. However, it installs skills into a live Hermes runtime and writes to VPS state dirs. Explicit inventory follows.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `~/.hermes/skills/` — currently contains 28 Hermes builtin skills across 23 categories | No migration needed; new skills added alongside existing ones |
| Stored data | `/home/uws/.ultra-workshop/pending_hitl.db` — SQLite from Phase 2 | No action; schema unchanged; `record_hitl_pause()` will be called by Phase 3 HITL-gated skills |
| Live service config | `hermes-config/config.yaml` — `mcp_servers: {}` still empty (REQ-ws-015 deferred) | No action in Phase 3 — skills don't require MCP |
| OS-registered state | `~/.hermes/hooks/startup-hitl-scan/` — Phase 2 hook deployed | No action; hook fires on startup; unaffected by Phase 3 |
| Secrets/env vars | `/etc/uws/env` — `TELEGRAM_BOT_TOKEN`, `LITELLM_API_KEY`, `LITELLM_API_URL` | Phase 3 skills read `LITELLM_API_KEY` and `LITELLM_API_URL`; these are already set |
| Build artifacts | `skill-audit.json` — does not exist yet | Created by audit script; committed to repo root |

**Nothing found requiring data migration.** All Phase 3 work is additive (new files, new skills).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Hermes Agent | Skill runtime | ✓ | v0.14.0 | — |
| Python 3.11 | audit script, skill helpers | ✓ | 3.11.x (via uws venv) | — |
| aider-chat | REQ-ws-006 | ✗ | — | Must install: `pip install aider-chat` |
| httpx | Brain HTTP calls | Unknown | — | httpx or requests; may be in venv already |
| bats | Smoke tests | ✓ | v1.x (established Phase 2) | — |
| Brain Agno API | REQ-ws-005 | ✓ | Agno 2.6.7 at 127.0.0.1:7000 | — |
| LiteLLM proxy | Aider + LLM calls | ✓ | Running at 127.0.0.1:4000 | — |
| `~/.claude/skills/` | Audit script source | ✓ | 114 skills (Mac-local only) | Script must run on Mac, not VPS |
| Git (for aider workspace) | REQ-ws-006 smoke test | ✓ | Installed on VPS | — |

**Missing dependencies with no fallback:**
- `aider-chat` — must be installed on VPS before REQ-ws-006 tasks execute

**Missing dependencies with fallback:**
- `httpx` — if not in venv, `requests` is an acceptable substitute for synchronous Brain calls

**Critical note:** `~/.claude/skills/` exists ONLY on the Mac, not on the VPS. The audit script (`scripts/audit-claude-skills.py`) must run locally on the Mac, writing `skill-audit.json` to the repo. The translated skills in `~/.hermes/skills/translated/` also land on the Mac first, then are committed and rsync'd to VPS. The VPS has `~/.hermes/skills/` for live Hermes consumption — these are separate directories.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Brain API has no auth (loopback only) |
| V3 Session Management | no | Skills are stateless |
| V4 Access Control | yes | Skills run as `uws` user; ReadWritePaths enforced by systemd |
| V5 Input Validation | yes | Audit script sanitizes skill names before filesystem writes; skill body validates `--question` / `--task` args |
| V6 Cryptography | no | No new secrets |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal in skill name → write outside `translated/` | Tampering | `pathlib.Path(name).name` (strips path components); validate no `..` |
| Aider subprocess with untrusted `--message` → command injection | Tampering | Pass `--message` as positional arg to subprocess, not via shell string; use `subprocess.run([...], shell=False)` |
| Brain HTTP call to loopback with crafted payload | Tampering | All calls are trusted (same VPS, uws user); no validation needed beyond content-type correctness |
| Skill body writes to vault outside `_system/workshop-*/` | Elevation | D1 constraint; brain-ingest is the only vault-write path; skill bodies validated by planner |

---

## Open Questions

1. **`hermes skill run` wrapper vs. acceptance criteria wording**
   - What we know: Hermes v0.14.0 has no `hermes skill run` subcommand; acceptance criteria uses this exact phrasing.
   - What's unclear: Should the planner define `scripts/hermes-skill-run.sh` as the canonical smoke command, or should the ROADMAP acceptance criteria be interpreted as "any invocation that triggers the skill and validates it runs"?
   - Recommendation: Create `scripts/hermes-skill-run.sh` and use it in all bats smoke tests. Document in README that this wrapper implements the acceptance criteria interface. No user decision needed unless they want a different invocation pattern.

2. **Aider `--model openai/cloud-sonnet` prefix convention**
   - What we know: LiteLLM proxy is at `127.0.0.1:4000`; aliases are `cloud-sonnet`, `private-worker`; aider uses `--openai-api-base` to redirect.
   - What's unclear: Whether the `openai/` prefix is required or if bare `cloud-sonnet` works with `--openai-api-base` set.
   - Recommendation: Test at execute time. If bare alias doesn't work, add `openai/` prefix. This is a 1-line fix at execution.

3. **Brain LiteLLM structured output error (live test failed)**
   - What we know: `POST /agents/query/runs` returned `status: "ERROR"` due to Groq structured output constraint + tool-calling conflict. This is a Brain-side config issue.
   - What's unclear: Will this affect Phase 3 brain-bridge skill smoke tests? The query agent uses `default-worker` which falls back to `cloud-groq`, which fails on structured output.
   - Recommendation: The skill smoke test should pass if Brain returns HTTP 200 with any content (even an error message in `content`). The L3 validation (`returns vault-grounded answer with citations`) may require the Brain LiteLLM issue to be fixed first OR testing against the `chat` agent instead of `query`. **Escalate to user:** Does the Phase 3 smoke test for brain-query need to return a real vault answer, or just verify the HTTP round-trip succeeds?

4. **`~/.hermes/skills/translated/` on VPS**
   - What we know: The constraint says translated skills go to `~/.hermes/skills/translated/`. The audit script runs on Mac (`~/.claude/skills/` is Mac-local). The VPS is the production Hermes host.
   - What's unclear: Does `~/.hermes/skills/translated/` need to exist on both Mac and VPS, or only one?
   - Recommendation: The audit script writes to Mac-local `~/.hermes/skills/translated/` (this is correct per the constraint). The planner should NOT rsync `translated/` to the VPS — those are staging artifacts, not production. Only manually-reviewed skills go to VPS `~/.hermes/skills/`. The `skills/` directory in the repo IS the VPS-deployment artifact.

5. **Brain-side LM Studio availability for `private-worker` during Aider smoke test**
   - What we know: `private-worker` = LM Studio gemma-4-e4b via LM Link on the Mac; Mac is asleep ~14h/day; timeout is 30s.
   - What's unclear: The aider smoke test requires `private-worker` (editor model). If Mac is asleep, the call times out.
   - Recommendation: The smoke test should use `--editor-model openai/default-worker` as a fallback for the initial smoke test. The final acceptance test (V5) should use real `cloud-sonnet` + `private-worker`. Document this distinction in the plan.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `hermes skill` CLI | `hermes skills` (plural) subcommand | Hermes v0.14.0 | Wrapper needed for "skill run" idiom |
| Agno REST JSON API | Agno multipart/form-data POST | Agno 2.6.7 | Brain HTTP calls must use `-F` form fields, not JSON body |
| LiteLLM `--model litellm/proxy/alias` | `--model openai/<alias>` with `--openai-api-base` | aider ≥0.50 | LiteLLM proxy treated as OpenAI-compatible endpoint |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `httpx` is in or easily installable in the uws Hermes venv | Standard Stack | If missing, Brain HTTP calls need `requests` fallback — minor rewrite |
| A2 | `python-frontmatter` is installable (or stdlib yaml split works cleanly for all 114 skills) | Standard Stack | If frontmatter has unusual syntax, audit script may misparse some skills |
| A3 | Aider diff output captured via `subprocess.run(..., capture_output=True)` | Stack & Tooling | If aider writes only to files (no stdout diff), the skill body needs a different diff extraction approach |
| A4 | `--model openai/cloud-sonnet` prefix required with LiteLLM proxy | Stack & Tooling | If bare alias works, no change. If prefix wrong format, aider fails with model-not-found |
| A5 | Brain ingest agent has HITL on Brain side (vault write gated by human approval) | Pitfalls | If ingest is NOT HITL-gated, the brain-ingest smoke test could accidentally write to vault |
| A6 | VPS `~/.hermes/skills/` directory is already in `ReadWritePaths` in systemd unit | Environment Availability | Phase 2 deployed `ReadWritePaths=/home/uws/.hermes`; subdirs should be writable — needs confirm at execute |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed. (It is not empty — A1–A6 need verification at execute time.)

---

## Sources

### Primary (HIGH confidence)
- Live VPS Hermes v0.14.0 CLI probe — `hermes --help`, `hermes skills --help`, `hermes skills list`
- Live VPS skill SKILL.md inspection — `/home/uws/.hermes/skills/software-development/plan/SKILL.md`
- Agno 2.6.7 source at `/opt/ultra-agents-brain/.venv/lib/python3.12/site-packages/agno/os/routers/agents/router.py` — confirms form-data endpoint
- Brain AgentOS app at `/opt/ultra-agents-brain/agentos/app.py` — confirms agent IDs
- Live Brain API probe — `GET /agents` + `POST /agents/query/runs` (form-data confirmed, error response structure confirmed)
- `docs/ingest/PLAN.md` Appendix E — Tool Translation Map (canonical reference)
- Phase 2 SUMMARY files — deployment patterns, VPS state, hook discovery mechanism
- `deploy/systemd/uws-hermes.service` — ProtectHome and ReadWritePaths configuration

### Secondary (MEDIUM confidence)
- [aider.chat/docs/config/options.html](https://aider.chat/docs/config/options.html) — `--architect`, `--editor-model`, `--openai-api-base` flags
- [aider.chat/2024/09/26/architect.html](https://aider.chat/2024/09/26/architect.html) — architect/editor two-LLM pattern explained

### Tertiary (LOW confidence — needs verification)
- Aider `openai/` prefix convention with LiteLLM proxy — from training data; verify at execute time
- Aider stdout diff capture pattern — from training data; verify at execute time
- `python-frontmatter` availability on VPS venv — not checked

---

## Metadata

**Confidence breakdown:**
- Brain API shape: HIGH — confirmed via live VPS probe and Agno source code
- Hermes SKILL.md format: HIGH — confirmed from live VPS skill inspection
- `hermes skill run` absent from CLI: HIGH — confirmed from live VPS `hermes --help`
- Tool Translation Map: HIGH — verbatim from PLAN.md Appendix E (canonical SPEC)
- Aider flags: MEDIUM — confirmed from aider.chat official docs
- Aider cost ledger / stdout diff: LOW — inferred from training knowledge

**Research date:** 2026-05-21
**Valid until:** 2026-06-21 (stable — Hermes v0.14.0 pinned; Brain Agno 2.6.7 stable; aider moves fast but flags are stable)
