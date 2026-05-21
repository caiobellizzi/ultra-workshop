# Phase 3: Skill Toolkit — Research

**Researched:** 2026-05-21 (force re-research after Phase 2 execution)
**Domain:** Hermes Agent skill authoring, Python subprocess (Aider), Brain HTTP integration, Claude skill translation
**Confidence:** HIGH for skill format, Brain API, and VPS package state; MEDIUM for Aider cost-ledger emission; LOW for bats installation path on VPS

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
- How `hermes skill run <name> --dry-run` maps to actual Hermes CLI (RESOLVED — wrapper script)
- Smoke-test invocation pattern (RESOLVED — `scripts/hermes-skill-run.sh` wrapper)
- How Aider subprocess returns diff (stdout capture via `subprocess.run`)
- TRANSLATION_NOTES.md per-skill content format

### Deferred Ideas (OUT OF SCOPE for Phase 3)
- workshop-build / workshop-fix skills (Phase 4)
- Pydantic schemas in workshop/types.py (Phase 4)
- Cost circuit breaker in workshop/cost.py (Phase 4)
- MCP registration for 5 servers (deferred from Phase 2 — future phase)
- Cron routines: daily-research, nightly-tests, bug-scan (Phase 5)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-ws-003 | `scripts/audit-claude-skills.py` walks `~/.claude/skills/`, tags 4 categories, auto-translates `requires-translation` skills to `~/.hermes/skills/translated/`, emits `skill-audit.json` + `TRANSLATION_NOTES.md` per skill; `--dry-run` default; idempotent; never writes to `~/.hermes/skills/<name>/` directly | Tool Translation Map confirmed in PLAN.md Appendix E; 4 categories: `agent_agnostic`, `auto_translated`, `requires_manual_port`, `claude_specific_skip`; output JSON schema defined in PLAN.md |
| REQ-ws-004 | ~10 agent-agnostic skills copied to `~/.hermes/skills/` with Hermes frontmatter; each passes `hermes skill run <name> --dry-run` | Hermes SKILL.md format confirmed from live VPS; invocation via `hermes chat --skills` confirmed; `--dry-run` handled at skill-body level via wrapper |
| REQ-ws-005 | `brain-query`, `brain-ingest`, `brain-research` wrapping Brain HTTP endpoints; `hermes skill run brain-query --question "what is PARA"` returns vault-grounded answer | Brain API confirmed multipart/form-data at `POST /agents/{id}/runs`; agent IDs `['chat', 'curator', 'ingest', 'query', 'research']` confirmed live; httpx 0.28.1 already in venv |
| REQ-ws-006 | `skills/aider/SKILL.md` — Aider subprocess with architect=`cloud-sonnet`, editor=`private-worker`; `hermes skill run aider --task "echo to file"` returns diff; cost log shows two LLM calls | Aider not yet installed on VPS; must be installed before REQ-ws-006 tasks; LiteLLM proxy confirmed alive at `127.0.0.1:4000` |
</phase_requirements>

---

## Summary

Phase 3 delivers the skill infrastructure that Phase 4's pipeline depends on. It has four workstreams: (1) the audit/translate script classifying ~114 Claude skills; (2) ~10 hand-selected agent-agnostic skills promoted to live Hermes; (3) three brain-bridge skills wrapping Brain's Agno HTTP API; and (4) the Aider skill implementing the coder subprocess role.

**Post-Phase-2 updates (what changed since original research):** The VPS is confirmed live with Hermes v0.14.0 running, Brain active, and LiteLLM alive. Key package state now confirmed via live probe: `httpx 0.28.1` and `PyYAML 6.0.3` are already in the Hermes venv — no install needed. `aider-chat` and `python-frontmatter` are NOT installed — must be added. `bats` is not on the VPS PATH and must be installed. The VPS `/opt/ultra-workshop/` directory contains only `deploy/`, `hermes/`, `hermes-config/`, `hermes-skills/` — no `scripts/` directory exists yet. The `hermes-skills/` VPS directory only has `startup-hitl-scan.py` and `__pycache__/`. The `startup-hitl-scan.py` `record_hitl_pause()` function is deployed and ready for Phase 3 HITL-issuing skills to call. All five Open Questions from the original research are RESOLVED (see Open Questions section).

**Critical discovery (Brain API — CONFIRMED):** Brain's `POST /agents/{id}/runs` endpoint uses `multipart/form-data`, NOT JSON. [VERIFIED: live Agno 2.6.7 source + live VPS probe]

**Critical discovery (`hermes skill run` — CONFIRMED):** Hermes CLI has no `skill run` subcommand. The accepted surface is `hermes chat --skills <name> --query <q> -Q --max-turns N --yolo`. A thin shell wrapper `scripts/hermes-skill-run.sh` implements the acceptance criteria interface. [VERIFIED: live VPS `hermes --help` + `hermes chat --help`]

**Primary recommendation:** Install missing packages (aider-chat, bats) in Wave 0 before any skill work. Write the audit script first (it classifies all 114 skills and tells you exactly which ~10 to port). Then port skills in dependency order: brain-query → brain-ingest → brain-research → aider → agent-agnostic Tier 1.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Skill audit / translation | Local Mac (runs against `~/.claude/skills/`) | VPS (output deployed) | `~/.claude/skills/` is Mac-local only; translations go to Mac `~/.hermes/skills/translated/`; only reviewed skills go to VPS |
| Skill YAML validation | VPS (Hermes reads skills at runtime) | Mac (pytest in pre-deploy) | Hermes discovers skills from `~/.hermes/skills/`; frontmatter parsed at load time |
| Brain HTTP calls | VPS Hermes skill body | — | `127.0.0.1:7000` is only reachable from VPS loopback |
| Aider subprocess | VPS (inside skill body) | — | Aider runs as subprocess of Hermes on VPS; outputs to workspace dir |
| Smoke tests | Mac (bats orchestrates) + VPS execution | — | bats tests SSH to VPS to verify skill invocation |
| Cost ledger writes | VPS skill body → Brain POST /agents/curator/runs | — | Per-delegate_task cost recorded via Brain's curator agent |

---

## Standard Stack

### Core (Phase 3 additions)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Hermes Agent | v0.14.0 (pinned) | Skill runtime; `hermes skills install`, `hermes chat -s` | L2 locked |
| aider-chat | latest stable | Coder subprocess in `aider` skill | L10 locked; routes through LiteLLM natively |
| httpx | 0.28.1 | Brain HTTP calls from Python skill bodies | **Already installed** in Hermes venv [VERIFIED: live probe] |
| bats | v1.x | Smoke tests for skill invocation | Phase 2 pattern; NOT yet on VPS — must install |
| pytest | ≥7 | Unit tests for audit script logic | Already in Hermes venv (pytest binary in `/opt/ultra-workshop/hermes/venv/bin/`) |
| Python stdlib: `re`, `pathlib`, `json`, `yaml`, `subprocess` | stdlib | Audit script + skill bodies | No new deps needed |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyYAML | 6.0.3 | Parse SKILL.md frontmatter in audit script | **Already installed** in Hermes venv [VERIFIED: live probe] |
| python-frontmatter | ≥1.0 | Combined YAML+body parsing | Optional — stdlib yaml split works; NOT installed on VPS |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `httpx` for Brain calls | `requests` | Both work; httpx already installed, preferred |
| `python-frontmatter` | manual `---` split + PyYAML | Manual split is sufficient for well-formed SKILL.md files; avoids new install |
| bats for smoke tests | pytest | bats matches Phase 2 pattern; pytest used for Python unit tests only |

**Installation (VPS, root → hermes venv):**
```bash
# aider-chat — required before REQ-ws-006 tasks
/opt/ultra-workshop/hermes/venv/bin/python3 -m pip install aider-chat

# bats — required for smoke tests (system package, not venv)
apt-get install -y bats

# python-frontmatter — optional; stdlib yaml.safe_load(text.split('---')[1]) works
# /opt/ultra-workshop/hermes/venv/bin/python3 -m pip install python-frontmatter
```

**Note:** There is no `pip` binary in the venv (only `python`, `python3`, `python3.11`, `pytest`, `uvicorn`, etc.). Use `python3 -m pip` instead of `pip` or `pip3` directly. [VERIFIED: live VPS `ls /opt/ultra-workshop/hermes/venv/bin/`]

---

## Package Legitimacy Audit

> slopcheck was not available at research time. All packages tagged [ASSUMED] for legitimacy. Planner must verify on PyPI before installing.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| aider-chat | PyPI | ~3 yrs | ~1M/mo | github.com/paul-gauthier/aider | Not run | [ASSUMED] Approved — widely known, 50k+ GitHub stars |
| python-frontmatter | PyPI | ~7 yrs | ~5M/mo | github.com/eyeseast/python-frontmatter | Not run | [ASSUMED] Approved — common YAML frontmatter parser |
| httpx | PyPI | ~5 yrs | ~30M/wk | github.com/encode/httpx | Not run | [ASSUMED] Approved — standard Python HTTP client; already installed |

**Packages removed due to [SLOP]:** none
**Packages flagged [SUS]:** none — but all are [ASSUMED] pending human verification

*Since slopcheck was unavailable, planner must gate each new install behind a `checkpoint:human-verify` task.*

---

## Stack & Tooling

### Hermes SKILL.md Format [VERIFIED: live VPS `/home/uws/.hermes/skills/software-development/plan/SKILL.md`]

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

# Skill Title
Body content (Markdown instructions for the agent)
```

**Minimum required fields:** `name`, `description` [VERIFIED: from live skill SKILL.md]
**Optional but recommended:** `version`, `platforms`, `metadata.hermes.tags`
**NOT present in Hermes format:** `tools:` frontmatter (Hermes does not use a tools allowlist in SKILL.md; tools are configured globally)

**Translation delta (SKILL.md frontmatter only):**
- ADD: `version`, `author`, `license`, `platforms`, `metadata.hermes.tags`
- REMOVE: `tools:` (if present), `mcpServers:` (if present), `hooks:` (if present)
- KEEP: `name`, `description`
- BODY: apply Tool Translation Map

### Hermes Skill Install Mechanism [VERIFIED: live VPS `hermes skills install --help`]

```
hermes skills install <identifier>
```

Where `identifier` can be:
- A direct HTTP(S) URL to a SKILL.md file
- A registry slug like `openai/skills/skill-creator`
- `--category CATEGORY` — folder to install into
- `--name NAME` — override skill name
- `--yes` — skip confirmation prompt

**Practical Phase 3 install approach:** Direct filesystem copy is safest for local dev:
```bash
# Install via hermes skills install from local path (URL form not supported directly)
# Use cp instead:
sudo -u uws mkdir -p /home/uws/.hermes/skills/<category>/<skill-name>
sudo -u uws cp skills/<name>/SKILL.md /home/uws/.hermes/skills/<category>/<skill-name>/SKILL.md
# Then verify:
sudo -u uws /opt/ultra-workshop/hermes/venv/bin/hermes skills list | grep <skill-name>
```

The `ReadWritePaths=/home/uws/.hermes` in `uws-hermes.service` confirms `~/.hermes/skills/` is writable by the service. [VERIFIED: live VPS systemd unit]

### Hermes CLI — Confirmed Subcommands [VERIFIED: live VPS]

```
hermes chat [-q QUERY] [-s SKILLS] [-Q] [--max-turns N] [--yolo] [--provider PROVIDER]
hermes skills {browse,search,install,inspect,list,check,update,audit,uninstall,...}
```

Key `hermes chat` flags confirmed:
- `-s` / `--skills` — preload one or more skills (repeat or comma-separate)
- `-q` / `--query` — single query (non-interactive)
- `-Q` / `--quiet` — suppress banner, spinner, tool previews; only output final response
- `--max-turns N` — max tool-calling iterations per turn (default: 90)
- `--yolo` — bypass all dangerous command approval prompts

### `hermes skill run` Wrapper [VERIFIED: no such subcommand in Hermes v0.14.0]

Hermes CLI has no `hermes skill run` subcommand. The acceptance criteria's `hermes skill run <name> --dry-run` is implemented via `scripts/hermes-skill-run.sh`:

```bash
#!/usr/bin/env bash
# scripts/hermes-skill-run.sh
# Implements "hermes skill run" interface by delegating to hermes chat.
# Usage: hermes-skill-run.sh <skill-name> [--dry-run] [--key value ...]
SKILL="$1"; shift
QUERY="$*"
exec sudo -u uws /opt/ultra-workshop/hermes/venv/bin/hermes chat \
  --skills "$SKILL" \
  --query "$QUERY" \
  -Q \
  --max-turns 3 \
  --yolo
```

The `--dry-run` flag is handled at the **skill body level** — each ported skill must detect `--dry-run` in the trigger query and output a plan rather than executing.

**VPS deployment:** `scripts/hermes-skill-run.sh` must be rsync'd to `/opt/ultra-workshop/scripts/hermes-skill-run.sh` and chmod +x. Note: `/opt/ultra-workshop/scripts/` does NOT exist yet — must be created. [VERIFIED: live VPS `ls /opt/ultra-workshop/`]

### Tool Translation Map [VERIFIED: PLAN.md Appendix E]

**Direct mappings (safe to auto-translate):**

| Claude Code tool | Hermes equivalent | Notes |
|------------------|-------------------|-------|
| `Read` | `read_file` | Path arg compatible |
| `Write` | `write_file` | Same semantics |
| `Edit` | `edit_file` (`replace_in_file`) | `old_string`/`new_string` syntax differs — emit code-comment warning |
| `Bash` / `Bash command` | `terminal` | `pty=false` default |
| `Grep` | `search` | `pattern`/`path`/`glob` args compatible |
| `Glob` | `find_files` | Pattern syntax identical |
| `WebFetch` | `http_request` (method=GET + extract_with_prompt) | 2-step pattern; emit comment warning |
| `WebSearch` | `web_search` | Direct rename |

**Tag-only (output to `~/.hermes/skills/translated/_manual/`):**

| Claude Code tool | Reason |
|------------------|--------|
| `TaskCreate` / `TaskUpdate` / `TaskList` | No Hermes equivalent |
| `AskUserQuestion` | Semantics differ |
| `Skill` (recursive invocation) | Hermes call syntax differs |
| `ExitPlanMode` | Claude Code-only construct |
| `Agent` (spawn subagent) | Requires manual review |

### Four Classification Categories [VERIFIED: PLAN.md Appendix E]

1. `agent_agnostic` — no tool references; copy as-is
2. `auto_translated` — contains only directly-mappable tools; apply Tool Translation Map
3. `requires_manual_port` — contains untranslatable tools; output to `_manual/` subdirectory with notes
4. `claude_specific_skip` — plugin skill clusters (`gsd-*`, `superpowers:*`, `dotnet-*`) — skip

**Confirmed skill count:** 114 skills in `~/.claude/skills/` (including symlinks). [VERIFIED: `ls ~/.claude/skills/ | wc -l`]

**Confirmed `claude_specific_skip`:** 38+ `gsd-*` skills, plus symlinked plugin packs (stitch-design, remotion, etc.). [VERIFIED: `ls ~/.claude/skills/`]

### Agent-Agnostic Skill Candidates [VERIFIED: live `ls` + frontmatter inspection]

Confirmed skills with no or translatable-only tool references:

| Skill slug | Body style | Tool references | Category |
|------------|-----------|-----------------|----------|
| `caveman` | Pure Markdown behavior instructions | None | `agent_agnostic` |
| `commit` | Markdown instructions + shell commands | `Bash` → `terminal` | `auto_translated` |
| `triage-issue` | Markdown instructions | `Bash`, `Grep`, `Read` | `auto_translated` |
| `diagnose` | Markdown debug instructions | `Bash`, `Read` | `auto_translated` |
| `qa` | Markdown instructions + GitHub | `Bash`, `Grep` | `auto_translated` |
| `edit-article` | Markdown writing instructions | `Read`, `Write` | `auto_translated` |
| `ubiquitous-language` | Markdown instructions | `Read`, `Grep` | `auto_translated` |
| `zoom-out` | Pure Markdown reflective instructions | None | `agent_agnostic` |
| `triage` | Markdown instructions | `Bash`, `Read` likely | `auto_translated` |
| `knowledge` | Markdown instructions | None confirmed | `agent_agnostic` |

**Note:** `zoom-out` has `disable-model-invocation: true` in frontmatter — this is a Claude Code-specific key. Remove it for Hermes port (Hermes ignores unknown frontmatter keys, but the key serves no purpose there).

### Brain HTTP API [VERIFIED: live VPS probe + Agno 2.6.7 source]

Brain runs at `http://127.0.0.1:7000` (Agno AgentOS, FastAPI/uvicorn).

**CRITICAL:** Endpoint uses `multipart/form-data`, NOT `application/json`. [VERIFIED: live source + live probe]

**Confirmed agent IDs:** `['chat', 'curator', 'ingest', 'query', 'research']` [VERIFIED: live `GET /agents`]

**POST /agents/{id}/runs — form-data fields:**
- `message: str` — required; the user query / task text
- `stream: bool` — optional (default True); set to `false` for synchronous response
- `session_id: str` — optional
- `user_id: str` — optional; use `"workshop"` for audit trail

**Python invocation pattern (httpx — already installed):**
```python
import httpx

def call_brain(agent_id: str, message: str, user_id: str = "workshop") -> dict:
    resp = httpx.post(
        f"http://127.0.0.1:7000/agents/{agent_id}/runs",
        data={"message": message, "stream": "false", "user_id": user_id},
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()
```

Note: Using synchronous `httpx.post` (not async). Hermes skill bodies run synchronously via the `terminal` tool → Python script invocation. No async/await needed. [VERIFIED: Phase 2 pattern in `startup-hitl-scan.py`]

**Confirmed response structure:**
```json
{
  "run_id": "<uuid>",
  "agent_id": "query",
  "content": "<LLM response text or error message>",
  "status": "success|ERROR",
  "metrics": {"duration": <float>}
}
```

**Live test caveat (RESOLVED):** `POST /agents/query/runs` returns `status: "ERROR"` due to Groq model + tool-calling incompatibility in LiteLLM config. HTTP shape is confirmed correct. Phase 3 brain-query smoke test only asserts HTTP 200 + `run_id` present (V4 relaxation per user decision). Citation-grounded answer test deferred.

### Aider Subprocess Integration [VERIFIED: aider.chat docs + CONSTRAINT-stack-coder-aider]

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
  /path/to/file.py
```

**VPS install status:** `aider-chat` is NOT installed in the Hermes venv. [VERIFIED: live probe — `import aider` fails]

**Install command (no `pip` binary in venv — use `python3 -m pip`):**
```bash
/opt/ultra-workshop/hermes/venv/bin/python3 -m pip install aider-chat
```

**Cost ledger:** Aider does not emit structured cost JSON by default. Cost is estimated from LiteLLM proxy logs or approximated as two LLM calls (architect + editor). Skill body posts approximate cost entries to Brain's curator agent before and after the subprocess call. [ASSUMED]

**Diff output:** Aider writes changes to files AND prints a summary to stdout. Skill body captures stdout via `subprocess.run(..., capture_output=True, text=True)`. [ASSUMED — verify at execute time]

**Aider requires git repo:** Aider always operates on a git repo (uses tree-sitter RepoMap). The aider skill must set a working directory with an initialized git repo. For smoke tests, create a minimal temp git repo. [ASSUMED]

---

## VPS State After Phase 2 [VERIFIED: live probe 2026-05-21]

This section documents the confirmed VPS state that Phase 3 inherits.

| Component | State | Evidence |
|-----------|-------|----------|
| `uws-hermes.service` | `active (running)` | `systemctl is-active uws-hermes` → `active` |
| Hermes version | v0.14.0 (2026.5.16) | `hermes --version` output |
| Brain (`uab-brain.service`) | `active` | `systemctl is-active uab-brain` |
| LiteLLM proxy | alive at 127.0.0.1:4000 | `curl /health/liveliness` → `"I'm alive!"` |
| `httpx` in Hermes venv | 0.28.1 | `python3 -c 'import httpx; print(httpx.__version__)'` |
| `PyYAML` in Hermes venv | 6.0.3 | `python3 -c 'import yaml; print(yaml.__version__)'` |
| `pytest` in Hermes venv | installed | `pytest` binary in venv bin/ |
| `aider-chat` in Hermes venv | **NOT installed** | `import aider` fails |
| `python-frontmatter` in Hermes venv | **NOT installed** | `import frontmatter` fails |
| `bats` on VPS | **NOT on PATH** | `find /` returned no bats binary |
| `/opt/ultra-workshop/scripts/` | **Does NOT exist** | `ls /opt/ultra-workshop/` shows no scripts/ |
| `/opt/ultra-workshop/hermes-skills/` | `startup-hitl-scan.py` + `__pycache__/` only | `ls /opt/ultra-workshop/hermes-skills/` |
| `/home/uws/.hermes/skills/` | Hermes builtin skills (23 categories) | `hermes skills list` output |
| `ReadWritePaths` (systemd) | `/home/uws/.hermes /home/uws/.local /home/uws/.cache /home/uws/.ultra-workshop /opt/ultra-workshop /tmp` | `grep ReadWritePaths /etc/systemd/system/uws-hermes.service` |
| `record_hitl_pause()` | Deployed, ready to call | Phase 2 SUMMARY: "helper is ready for Phase 3 integration" |

---

## Architecture Patterns

### System Architecture Diagram

```
Mac (local)                          VPS (31.97.130.253)
───────────────────────────────      ───────────────────────────────────────
                                     Hermes (uws-hermes.service)
~/.claude/skills/ (114 skills)          │
       │                                │── hermes chat --skills <name>
       ▼                                │       │
audit-claude-skills.py                  │       ├── skill body (SKILL.md)
  │ classifies → 4 categories           │       │     → terminal: python3
  │ translates → ~/.hermes/             │       │         brain_http.py
  │              skills/translated/     │       │     → terminal: python3
  │                                     │       │         aider_runner.py
  ▼ (committed to repo)                 │       │
skills/ dir (repo)                      │       ▼
  │                                     │   Brain API (127.0.0.1:7000)
  └─── rsync ──────────────────────────►│   LiteLLM proxy (127.0.0.1:4000)
                                        │
hermes-skills/brain_http.py ───────────►│ /opt/ultra-workshop/hermes-skills/
scripts/hermes-skill-run.sh ───────────►│ /opt/ultra-workshop/scripts/

Mac bats tests ──── SSH ────────────────► VPS: run skill, assert output
```

### Recommended Project Structure

```
ultra-workshop/
├── scripts/
│   ├── audit-claude-skills.py     # REQ-ws-003 — NEW
│   ├── test_audit.py              # Wave 0 test for audit script
│   └── hermes-skill-run.sh        # smoke wrapper — NEW
├── skills/                        # NEW directory
│   ├── brain-query/
│   │   └── SKILL.md               # REQ-ws-005
│   ├── brain-ingest/
│   │   └── SKILL.md               # REQ-ws-005
│   ├── brain-research/
│   │   └── SKILL.md               # REQ-ws-005
│   ├── aider/
│   │   └── SKILL.md               # REQ-ws-006
│   ├── caveman/
│   │   └── SKILL.md               # REQ-ws-004
│   ├── commit/
│   │   └── SKILL.md               # REQ-ws-004
│   ├── triage-issue/
│   │   └── SKILL.md               # REQ-ws-004
│   ├── diagnose/
│   │   └── SKILL.md               # REQ-ws-004
│   ├── qa/
│   │   └── SKILL.md               # REQ-ws-004
│   └── [4-5 more agent-agnostic picks]
├── hermes-skills/                 # existing from Phase 2
│   ├── startup-hitl-scan.py       # Phase 2 — deployed to VPS
│   ├── brain_http.py              # NEW — shared Brain HTTP helper
│   ├── aider_runner.py            # NEW — Aider subprocess helper
│   └── test_skill_frontmatter.py  # Wave 0 test
└── tests/
    └── phase-03/                  # NEW
        ├── helpers.bash
        ├── scaffold.bats
        ├── skills-smoke.bats
        ├── brain-bridge.bats
        └── aider-smoke.bats
```

**VPS deployment targets:**
- `skills/<name>/SKILL.md` → `sudo -u uws cp` to `/home/uws/.hermes/skills/<category>/<name>/SKILL.md`
- `hermes-skills/brain_http.py` → rsync to `/opt/ultra-workshop/hermes-skills/brain_http.py`
- `hermes-skills/aider_runner.py` → rsync to `/opt/ultra-workshop/hermes-skills/aider_runner.py`
- `scripts/hermes-skill-run.sh` → rsync to `/opt/ultra-workshop/scripts/hermes-skill-run.sh` (mkdir scripts/ first)
- `skill-audit.json` output → committed to repo root

### Pattern 1: Hermes SKILL.md with Python Helper

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

## Steps
1. Extract the question from the user message (look for `--question` flag or bare query)
2. Run: `terminal python3 /opt/ultra-workshop/hermes-skills/brain_http.py query "<question>"`
3. Return the response content
```

### Pattern 2: Agent-Agnostic Skill (copy as-is, update frontmatter)

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

**Key:** Remove `disable-model-invocation: true` or other Claude-specific keys. Keep `name` and `description` identical.

### Pattern 3: Aider Skill (subprocess wrapper)

```yaml
---
name: aider
description: "Run Aider coder on a task. Use for 'aider --task <description>', 'code with aider', 'coder run'. Invokes architect=cloud-sonnet + editor=private-worker."
version: 1.0.0
author: ultra-workshop
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [coder, aider, coding, git, diff]
---
# Aider Coder

Invoke Aider as a subprocess with architect/editor split against the LiteLLM proxy.

## Steps
1. Extract `--task` from the user message
2. Run: `terminal python3 /opt/ultra-workshop/hermes-skills/aider_runner.py --task "..."`
3. Return the diff summary
```

### Pattern 4: Audit Script Core Structure

```python
# scripts/audit-claude-skills.py
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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Write translated files (default: dry-run only)")
    args = parser.parse_args()
    dry_run = not args.apply
    # walk, classify, optionally write
```

**Idempotency:** Use `exist_ok=True` on mkdir, skip write if file hash matches. Never fail on re-run.

**Path safety:** `safe_name = pathlib.Path(skill_name).name` — strips path components, prevents traversal.

### Anti-Patterns to Avoid

- **Writing to `~/.hermes/skills/<name>/` from the audit script** — violates CONSTRAINT-skill-translation-safety. Always write to `translated/` subdirectory.
- **Using `pip` binary directly** — no `pip` binary in the Hermes venv; use `python3 -m pip`. [VERIFIED: live VPS]
- **JSON Content-Type for Brain HTTP calls** — Brain uses multipart/form-data; JSON POST returns 422.
- **Assuming `hermes skill run` exists** — it does not; use `hermes chat --skills <name>` or wrapper.
- **Missing `mkdir scripts/` on VPS** — `/opt/ultra-workshop/scripts/` does not exist; must be created before rsync.
- **`--yolo` in production skills** — use only in smoke tests; production skills should not bypass approvals.
- **Using `logging.info()` in VPS Python scripts** — Hermes gateway sets root logger to WARNING; use `print(..., flush=True)` for output visible in journalctl. [VERIFIED: Phase 2 deviation #3]
- **Calling `sudo -u uws pip`** — `sudo` resets PATH, drops venv; use full path `sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 -m pip`. [VERIFIED: Phase 2 VPS probe found `sudo pip` fails]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SKILL.md frontmatter parsing | custom `---` regex | `yaml.safe_load(text.split('---')[1])` (PyYAML already in venv) | Edge cases: multi-line values, escaped chars |
| HTTP calls to Brain | `urllib` | `httpx` (already installed 0.28.1) | Cleaner timeout handling; already in ecosystem |
| Aider subprocess management | custom process manager | `subprocess.run(...)` | Aider is a well-behaved CLI |
| LiteLLM proxy routing | direct Anthropic calls | `--openai-api-base http://127.0.0.1:4000/v1` | Honors model-agnostic constraint L9 |
| Skill classification | LLM-based classifier | regex-based tool name detection | Deterministic; reproducible; fast; idempotent |

---

## Common Pitfalls

### Pitfall 1: No `pip` binary in Hermes venv [VERIFIED: Phase 2 probe]
**What goes wrong:** `sudo -u uws pip install aider-chat` fails with "command not found".
**Why it happens:** The Hermes venv only installs `python`, `python3`, `python3.11` and app binaries — no standalone `pip`.
**How to avoid:** Always use `/opt/ultra-workshop/hermes/venv/bin/python3 -m pip install <pkg>`. Root can run this without `sudo -u uws` since it targets a path the root user can write.
**Warning signs:** `command not found: pip` or `sudo: pip: command not found`

### Pitfall 2: `/opt/ultra-workshop/scripts/` Does Not Exist [VERIFIED: live probe]
**What goes wrong:** `rsync scripts/hermes-skill-run.sh root@VPS:/opt/ultra-workshop/scripts/` fails because the target directory doesn't exist.
**Why it happens:** Phase 2 only deployed `hermes-skills/` and `deploy/` to VPS. The `scripts/` directory was never created on VPS.
**How to avoid:** Add `ssh root@VPS "mkdir -p /opt/ultra-workshop/scripts"` as the first VPS deploy step in Wave 0.
**Warning signs:** rsync error "No such file or directory"

### Pitfall 3: `hermes chat --yolo` Needed for Non-Interactive Smoke Tests [VERIFIED: live VPS]
**What goes wrong:** `hermes chat -s <skill> -q <query> -Q` hangs waiting for tool approval prompt.
**Why it happens:** Hermes default `approvals.mode: smart` asks for confirmation on destructive tools.
**How to avoid:** Add `--yolo` to skip all approval prompts in smoke tests.
**Warning signs:** Process hangs; no output after 30s

### Pitfall 4: Brain Returns `status: "ERROR"` for query Agent [VERIFIED: live probe]
**What goes wrong:** `POST /agents/query/runs` returns HTTP 200 but `status: "ERROR"` with Groq structured output error.
**Why it happens:** Brain's query agent + Groq model + tool-calling = incompatibility in LiteLLM config.
**How to avoid:** Skill body checks `data["status"] != "ERROR"` and surfaces error clearly. Smoke test asserts HTTP 200 + `run_id` only (not content quality).
**Warning signs:** HTTP 200 response, `status: "ERROR"` field

### Pitfall 5: `ProtectHome=read-only` + New Dirs [VERIFIED: Phase 2 deviation #2]
**What goes wrong:** New directories under `/home/uws/` fail with "Permission denied".
**Why it happens:** `ProtectHome=read-only` in `uws-hermes.service` blocks writes to home dirs not in `ReadWritePaths`.
**How to avoid:** Current `ReadWritePaths` already includes `/home/uws/.hermes` — skills in `~/.hermes/skills/` ARE writable. No change needed for Phase 3 skill install.
**Warning signs:** systemd journal "Permission denied"; skill install fails

### Pitfall 6: Aider Requires Git Repo Working Directory [ASSUMED]
**What goes wrong:** `aider --message "echo to file"` fails because it needs a git repo.
**Why it happens:** Aider always operates on a git repo; uses tree-sitter RepoMap for context.
**How to avoid:** `aider_runner.py` must create a temp git repo (`git init /tmp/uws-aider-<id>`) or operate on a pre-existing workspace. Smoke test uses a minimal temp git repo.
**Warning signs:** `fatal: not a git repository` in aider stderr

### Pitfall 7: `logging.info()` Not Visible in journald [VERIFIED: Phase 2 deviation #3]
**What goes wrong:** Python `logging.getLogger().info(...)` output disappears in `journalctl -u uws-hermes`.
**Why it happens:** Hermes gateway sets root logger to WARNING level; INFO is filtered out.
**How to avoid:** Use `print(..., flush=True)` for all diagnostic output in scripts running inside the Hermes process (hooks, skill body helpers). For standalone scripts (audit-claude-skills.py), logging works normally.
**Warning signs:** bats assertion `grep 'pattern'` in journal finds nothing

### Pitfall 8: Audit Script Runs on Mac, Not VPS
**What goes wrong:** Running `scripts/audit-claude-skills.py` on VPS finds 0 skills.
**Why it happens:** `~/.claude/skills/` exists ONLY on Mac. The VPS has no Claude Code installation.
**How to avoid:** Run audit script locally on Mac. Commit `skill-audit.json` to repo. Skills in `skills/` dir are the VPS deployment artifact.
**Warning signs:** `CLAUDE_SKILLS_ROOT` resolves to an empty or nonexistent directory on VPS

---

## Runtime State Inventory

> Phase 3 installs skills into live Hermes runtime and writes to VPS state dirs.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `~/.hermes/skills/` — 23 categories of Hermes builtin skills | No migration; new skills added alongside |
| Stored data | `/home/uws/.ultra-workshop/pending_hitl.db` — SQLite from Phase 2 (schema: hitl_pauses table) | No action; `record_hitl_pause()` ready for Phase 3 HITL-issuing skills |
| Live service config | `hermes-config/config.yaml` — `mcp_servers: {}` empty stub | No action in Phase 3 — skills don't require MCP |
| OS-registered state | `/home/uws/.hermes/hooks/startup-hitl-scan/` — Phase 2 hook deployed | No action; hook fires on startup; unaffected by Phase 3 |
| Secrets/env vars | `/etc/uws/env` — `TELEGRAM_BOT_TOKEN`, `LITELLM_API_KEY`, `LITELLM_API_URL` | Phase 3 skills read `LITELLM_API_KEY` and `LITELLM_API_URL`; already set |
| Build artifacts | `skill-audit.json` — does not exist yet | Created by audit script on Mac; committed to repo root |
| VPS directory gap | `/opt/ultra-workshop/scripts/` — does not exist | Must `mkdir -p` before rsync of hermes-skill-run.sh |

**Nothing requires data migration.** All Phase 3 work is additive.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Hermes Agent | Skill runtime | ✓ VPS | v0.14.0 | — |
| Python 3.11 | Hermes venv | ✓ VPS | 3.11.x in venv | — |
| httpx | Brain HTTP calls | ✓ VPS (in venv) | 0.28.1 | — |
| PyYAML | SKILL.md frontmatter parsing | ✓ VPS (in venv) | 6.0.3 | — |
| pytest | Unit tests | ✓ VPS (in venv) | ≥7 (binary present) | — |
| aider-chat | REQ-ws-006 | ✗ NOT in venv | — | Must install: `python3 -m pip install aider-chat` |
| python-frontmatter | SKILL.md parsing | ✗ NOT in venv | — | Use `yaml.safe_load(text.split('---')[1])` instead |
| bats | Smoke tests | ✗ NOT on VPS PATH | — | Must install: `apt-get install -y bats` |
| Brain Agno API | REQ-ws-005 | ✓ VPS | Agno 2.6.7 at 127.0.0.1:7000 | — |
| LiteLLM proxy | Aider + LLM calls | ✓ VPS | alive at 127.0.0.1:4000 | — |
| `~/.claude/skills/` | Audit script source | ✓ Mac only | 114 skills | Script must run on Mac, not VPS |
| `private-worker` (LM Studio) | REQ-ws-006 aider smoke | ✗ Mac-dependent | — | Smoke test uses `skip` if unreachable |
| `/opt/ultra-workshop/scripts/` | hermes-skill-run.sh deploy | ✗ Dir does not exist | — | Create with `mkdir -p` in Wave 0 |

**Missing dependencies blocking execution (must fix in Wave 0):**
- `aider-chat` — must install before REQ-ws-006 plan executes
- `bats` — must install before any smoke tests run
- `/opt/ultra-workshop/scripts/` — must create before rsync

**Missing dependencies with fallback:**
- `python-frontmatter` — use stdlib yaml.safe_load; no install needed
- `private-worker` — smoke test skips if unreachable (not FAIL)

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (unit) | pytest ≥7 (already in Hermes venv bin/) |
| Framework (smoke) | bats v1.x (must install on VPS) |
| Config file | `tests/phase-03/helpers.bash` |
| Quick run command | `pytest scripts/ hermes-skills/ -x -q` |
| Full suite command | `bats tests/phase-03/ && pytest scripts/ hermes-skills/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-ws-003 | audit script tags 4 categories | unit | `pytest scripts/test_audit.py::test_classification -x` | ❌ Wave 0 |
| REQ-ws-003 | audit script is idempotent | unit | `pytest scripts/test_audit.py::test_idempotent -x` | ❌ Wave 0 |
| REQ-ws-003 | `--dry-run` never writes files | unit | `pytest scripts/test_audit.py::test_dry_run_no_write -x` | ❌ Wave 0 |
| REQ-ws-003 | TRANSLATION_NOTES.md emitted per skill | unit | `pytest scripts/test_audit.py::test_translation_notes -x` | ❌ Wave 0 |
| REQ-ws-004 | each ported skill frontmatter valid | unit | `pytest hermes-skills/test_skill_frontmatter.py -x` | ❌ Wave 0 |
| REQ-ws-004 | each ported skill dry-run exits 0 | smoke (bats) | `bats tests/phase-03/skills-smoke.bats` | ❌ Wave 0 |
| REQ-ws-005 | brain-query HTTP 200 + run_id | smoke (bats) | `bats tests/phase-03/brain-bridge.bats` | ❌ Wave 0 |
| REQ-ws-006 | aider skill returns diff | smoke (bats) | `bats tests/phase-03/aider-smoke.bats` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest scripts/ hermes-skills/ -q --tb=short`
- **Per wave merge:** `bats tests/phase-03/ && pytest scripts/ hermes-skills/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `scripts/test_audit.py` — pytest stubs for REQ-ws-003
- [ ] `hermes-skills/test_skill_frontmatter.py` — frontmatter validator for all Phase 3 skills
- [ ] `tests/phase-03/helpers.bash` — shared bats helpers (SSH wrapper, VPS_HOST)
- [ ] `tests/phase-03/scaffold.bats` — smoke test for hermes-skill-run.sh wrapper
- [ ] `scripts/hermes-skill-run.sh` — wrapper script (Wave 0 artifact)
- [ ] bats install on VPS: `apt-get install -y bats`
- [ ] aider-chat install on VPS: `python3 -m pip install aider-chat`
- [ ] `mkdir -p /opt/ultra-workshop/scripts` on VPS

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Brain API has no auth (loopback only) |
| V3 Session Management | no | Skills are stateless |
| V4 Access Control | yes | Skills run as `uws` user; ReadWritePaths enforced by systemd |
| V5 Input Validation | yes | Audit script sanitizes skill names; skill body validates `--question`/`--task` args |
| V6 Cryptography | no | No new secrets |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal in skill name → write outside `translated/` | Tampering | `pathlib.Path(name).name` strips path components; assert no `..` |
| Aider `--message` with untrusted content → command injection | Tampering | Pass `--message` as list element to `subprocess.run([...], shell=False)` |
| Brain HTTP form-data with crafted payload | Tampering | All calls are trusted (same VPS, uws user); no extra validation needed |

---

## Open Questions (ALL RESOLVED)

1. **`hermes skill run` wrapper vs. acceptance criteria wording**
   **RESOLVED:** `scripts/hermes-skill-run.sh` is the canonical smoke command. All bats tests use it. ROADMAP acceptance criteria `hermes skill run <name> --dry-run` is implemented via this wrapper. [VERIFIED: live VPS `hermes --help` confirms no `skill run` subcommand]

2. **Aider `--model openai/cloud-sonnet` prefix convention**
   **RESOLVED:** Plans encode `openai/cloud-sonnet` and `openai/private-worker` (with prefix) as the standard. Executor confirms at install time; if bare alias works, prefix is harmless.

3. **Brain LiteLLM structured output error (live test failed)**
   **RESOLVED:** HTTP round-trip only (V4 relaxation per user decision 2026-05-21). Phase 3 asserts HTTP 200 + `run_id` + form-data shape. Citation-grounded answer test deferred.

4. **`~/.hermes/skills/translated/` on VPS**
   **RESOLVED:** Audit script writes to Mac-local `~/.hermes/skills/translated/` only. The `skills/` repo directory is the VPS deployment artifact. `translated/` is never rsynced to VPS.

5. **Brain-side LM Studio availability for `private-worker` during Aider smoke test**
   **RESOLVED:** V5 strict — no fallback to default-worker. Plan 05 includes a precheck task that pings `private-worker` via LiteLLM. If unreachable, bats smoke uses `skip "private-worker unavailable"` (SKIP, not FAIL, not silent PASS).

**New open question discovered during re-research:**

6. **`hermes skills install` from local path**
   - What we know: `hermes skills install <identifier>` takes a URL or registry slug. There is no documented "local path" mode in the help output.
   - What's unclear: Does `hermes skills install /path/to/SKILL.md` work, or must we use direct filesystem copy?
   - Recommendation: Use direct `cp`/`sudo -u uws cp` to `~/.hermes/skills/<category>/<name>/SKILL.md`. This is safe, simple, and avoids registry lookup. The planner should use cp, not `hermes skills install`.

**RESOLVED:** Plans use direct `cp`/rsync to `~/.hermes/skills/<category>/<name>/SKILL.md` as recommended. `hermes skills install` does not support local paths (confirmed via live `--help` output on VPS 2026-05-21). All skill deployment tasks in 03-03, 03-04, 03-05 use filesystem copy exclusively.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `hermes skill` CLI | `hermes skills` (plural) subcommand | Hermes v0.14.0 | Wrapper needed for "skill run" idiom |
| Agno REST JSON API | Agno multipart/form-data POST | Agno 2.6.7 | Brain HTTP calls must use form fields, not JSON body |
| `pip install` via pip binary | `python3 -m pip install` (no pip binary in venv) | Hermes venv structure | Install commands must use full path + `-m pip` |
| LiteLLM `--model litellm/proxy/alias` | `--model openai/<alias>` with `--openai-api-base` | aider ≥0.50 | LiteLLM proxy treated as OpenAI-compatible endpoint |

**Deprecated/outdated (from original research):**
- `A1` assumption "httpx may not be in venv" → RESOLVED: httpx 0.28.1 confirmed installed
- `A1` assumption "PyYAML may not be in venv" → RESOLVED: PyYAML 6.0.3 confirmed installed
- `A2` assumption "python-frontmatter may be in venv" → RESOLVED: not installed; use stdlib yaml.safe_load

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Aider stdout diff captured via `subprocess.run(..., capture_output=True)` | Stack & Tooling | If aider writes only to files (no stdout diff), skill body needs different diff extraction |
| A2 | `--model openai/cloud-sonnet` prefix required with LiteLLM proxy | Stack & Tooling | If bare alias works, no change needed. If prefix format is wrong, aider fails with model-not-found |
| A3 | Brain ingest agent has HITL on Brain side (vault write gated) | Pitfalls | If ingest is NOT HITL-gated, brain-ingest smoke test could accidentally write to vault |
| A4 | Aider subprocess needs git repo in working directory | Common Pitfalls | If aider can run without git context, temp git init step is unnecessary |
| A5 | `aider-chat` PyPI package name is correct (not `aider` alone) | Standard Stack | If package name differs, pip install fails; check PyPI before running |

**Resolved assumptions from original research (no longer uncertain):**
- ~~A1~~ httpx in venv: CONFIRMED 0.28.1
- ~~A3~~ aider diff stdout: still ASSUMED (A1 above)
- ~~A6~~ ReadWritePaths covers ~/.hermes: CONFIRMED

---

## Sources

### Primary (HIGH confidence)
- Live VPS probe 2026-05-21 — `hermes --version`, `hermes chat --help`, `hermes skills --help`, `hermes skills install --help`
- Live VPS python3 import probes — confirmed httpx 0.28.1, PyYAML 6.0.3, aider absent, python-frontmatter absent
- Live VPS `ls /opt/ultra-workshop/` — confirmed directory structure (no scripts/ dir)
- Live VPS `systemctl is-active` — confirmed Hermes, Brain, LiteLLM all active
- Live VPS `curl http://127.0.0.1:7000/agents` — confirmed agent IDs `['chat', 'curator', 'ingest', 'query', 'research']`
- Live VPS `grep ReadWritePaths /etc/systemd/system/uws-hermes.service` — confirmed writable paths
- Live VPS `ls /home/uws/.hermes/skills/software-development/plan/SKILL.md` — confirmed Hermes SKILL.md format
- Phase 2 SUMMARY files (02-02 through 02-05) — execution patterns, VPS decisions, deviations
- Phase 2 VERIFICATION.md — confirmed 4/5 Phase 2 criteria satisfied; REQ-ws-015 deferred
- `docs/ingest/PLAN.md` Appendix E — Tool Translation Map (canonical SPEC)
- `deploy/systemd/uws-hermes.service` — ProtectHome, ReadWritePaths configuration

### Secondary (MEDIUM confidence)
- [aider.chat/docs/config/options.html](https://aider.chat/docs/config/options.html) — `--architect`, `--editor-model`, `--openai-api-base` flags
- Mac `ls ~/.claude/skills/` + frontmatter inspection — 114 skills, confirmed slug list, caveman body verified

### Tertiary (LOW confidence — needs verification)
- Aider `openai/` prefix convention with LiteLLM proxy — from training data; verify at execute time
- Aider stdout diff capture pattern — from training data; verify at execute time
- bats install via `apt-get install -y bats` — [ASSUMED] Debian package; confirm on VPS Ubuntu version

---

## Metadata

**Confidence breakdown:**
- VPS package state (httpx, PyYAML, aider, python-frontmatter, bats): HIGH — confirmed via live probe
- Brain API shape: HIGH — confirmed via live VPS probe and Agno source code
- Hermes SKILL.md format: HIGH — confirmed from live VPS skill inspection
- `hermes skill run` absent from CLI: HIGH — confirmed from live VPS `hermes --help`
- Tool Translation Map: HIGH — verbatim from PLAN.md Appendix E
- Aider flags: MEDIUM — confirmed from aider.chat official docs
- Aider cost ledger / stdout diff: LOW — inferred from training knowledge
- bats install method on VPS: LOW — apt-get assumed; verify at execute time

**Research date:** 2026-05-21 (force re-research)
**Valid until:** 2026-06-21 (stable — Hermes v0.14.0 pinned; Brain Agno 2.6.7 stable)
**Changes from original:** Updated VPS package state (httpx/PyYAML confirmed, aider/bats missing confirmed), added `/opt/ultra-workshop/scripts/` gap, resolved all 5 original Open Questions, added new Open Question #6 on `hermes skills install` local path, updated pitfall list with Phase 2 VPS lessons.
