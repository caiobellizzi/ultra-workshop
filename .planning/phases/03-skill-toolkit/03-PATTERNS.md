# Phase 3: Skill Toolkit — Pattern Map

**Mapped:** 2026-05-21
**Files analyzed:** 14 new/modified files
**Analogs found:** 12 / 14

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `scripts/audit-claude-skills.py` | utility (CLI) | batch + file-I/O | `hermes-skills/startup-hitl-scan.py` | role-match |
| `scripts/hermes-skill-run.sh` | utility (wrapper) | request-response | `scripts/install.sh` | role-match |
| `hermes-skills/brain_http.py` | service | request-response | `hermes-skills/startup-hitl-scan.py` | role-match |
| `skills/brain-query/SKILL.md` | skill (Hermes) | request-response | RESEARCH.md Pattern 1 (no repo analog) | research-only |
| `skills/brain-ingest/SKILL.md` | skill (Hermes) | request-response | `skills/brain-query/SKILL.md` (sibling) | exact (sibling) |
| `skills/brain-research/SKILL.md` | skill (Hermes) | request-response | `skills/brain-query/SKILL.md` (sibling) | exact (sibling) |
| `skills/aider/SKILL.md` | skill (Hermes) | request-response | RESEARCH.md Pattern 3 (no repo analog) | research-only |
| `skills/caveman/SKILL.md` | skill (Hermes) | transform | `~/.claude/skills/caveman/SKILL.md` | exact (source) |
| `skills/commit/SKILL.md` | skill (Hermes) | batch | `~/.claude/skills/commit/SKILL.md` | exact (source) |
| `skills/diagnose/SKILL.md` | skill (Hermes) | request-response | `~/.claude/skills/diagnose/SKILL.md` | exact (source) |
| `skills/triage-issue/SKILL.md` | skill (Hermes) | request-response | `~/.claude/skills/triage-issue/SKILL.md` | exact (source) |
| `skills/qa/SKILL.md` | skill (Hermes) | request-response | `~/.claude/skills/qa/SKILL.md` | exact (source) |
| `scripts/test_audit.py` | test (pytest) | batch | `hermes-skills/test_startup_hitl_scan.py` | exact |
| `tests/phase-03/*.bats` | test (bats) | request-response | `tests/phase-02/hitl-restart.bats` | exact |

---

## Pattern Assignments

### `scripts/audit-claude-skills.py` (utility, batch + file-I/O)

**Analog:** `hermes-skills/startup-hitl-scan.py`

**Module docstring pattern** (lines 1–24):
```python
"""
audit-claude-skills — Walk ~/.claude/skills/, classify, and optionally translate.

<functional description of what the module does>

Deploy location: scripts/audit-claude-skills.py
Run on: Mac only (reads ~/.claude/skills/ which is Mac-local)
"""
from __future__ import annotations
```

**Imports pattern** (adapt from lines 26–31 of startup-hitl-scan.py):
```python
from __future__ import annotations
import argparse, json, pathlib, re, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
```

**Module-level constants pattern** (RESEARCH.md Pattern 4):
```python
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
```

**`--dry-run` / `--apply` CLI pattern** (from `scripts/install.sh` lines 13–18):
```bash
# install.sh pattern — translate to argparse:
# for arg in "$@"; do
#   [[ "$arg" == "--dry-run" ]] && DRY_RUN=true
# done
```
Python equivalent:
```python
def main():
    parser = argparse.ArgumentParser(
        description="Classify and optionally translate Claude skills to Hermes format."
    )
    parser.add_argument("--apply", action="store_true",
                        help="Write translated files (default: dry-run only)")
    args = parser.parse_args()
    dry_run = not args.apply
```

**Dry-run guard pattern** (from `scripts/install.sh` lines 20–26 `rsh()` function):
```python
def _write_file(path: Path, content: str, dry_run: bool) -> None:
    """Write content to path, respecting dry_run flag."""
    if dry_run:
        print(f"[dry-run] would write {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
```

**Idempotent file-walk pattern** — derived from startup-hitl-scan.py `ensure_schema()` (lines 51–58):
```python
# The ensure_schema pattern uses mkdir(parents=True, exist_ok=True)
# and CREATE TABLE IF NOT EXISTS for idempotency.
# audit script equivalent: skip if output file is unchanged (compare hash):
def _is_identical(path: Path, content: str) -> bool:
    return path.exists() and path.read_text() == content
```

**Path traversal safety** (RESEARCH.md Security Domain):
```python
# Use pathlib.Path(name).name to strip path components
safe_name = pathlib.Path(skill_name).name
assert ".." not in safe_name
output_dir = HERMES_TRANSLATED_ROOT / safe_name
```

**Error handling pattern** (startup-hitl-scan.py `fetch_pending()` lines 141–150):
```python
# Graceful failure — return empty/default, never crash
try:
    ...
except Exception:
    return []
```

**JSON output** (emit to stdout, write to file):
```python
result = {"generated_at": datetime.now(timezone.utc).isoformat(), "skills": [...]}
print(json.dumps(result, indent=2))
if not dry_run:
    (Path("skill-audit.json")).write_text(json.dumps(result, indent=2))
```

**Differences to apply:** The audit script has no DB; replaces SQLite with filesystem writes. Uses `argparse` not bare `sys.argv`. Output must include `skill-audit.json` (repo root) + per-skill `TRANSLATION_NOTES.md`.

---

### `scripts/hermes-skill-run.sh` (utility wrapper, request-response)

**Analog:** `scripts/install.sh`

**Header pattern** (install.sh lines 1–6):
```bash
#!/usr/bin/env bash
# scripts/hermes-skill-run.sh
# Usage: hermes-skill-run.sh <skill-name> [--dry-run] [--key value ...]
# Wraps "hermes chat --skills" to implement the "hermes skill run" interface.
# Run from VPS as uws user or via: sudo -u uws hermes-skill-run.sh <name> [args...]

set -euo pipefail
```

**`--dry-run` guard pattern** (install.sh lines 13–18 + 20–26):
```bash
DRY_RUN=false
for arg in "$@"; do
  [[ "$arg" == "--dry-run" ]] && DRY_RUN=true
done
```

**Core delegation pattern** (RESEARCH.md lines 229–241):
```bash
SKILL="$1"; shift
QUERY="$*"

if $DRY_RUN; then
  echo "[dry-run] would run: hermes chat --skills ${SKILL} --query '${QUERY}' -Q --max-turns 3 --yolo"
  exit 0
fi

exec sudo -u uws /opt/ultra-workshop/hermes/venv/bin/hermes chat \
  --skills "$SKILL" \
  --query "$QUERY" \
  -Q \
  --max-turns 3 \
  --yolo
```

**SSH invocation pattern** (install.sh `rsh()` function lines 20–26):
```bash
# The wrapper itself runs ON the VPS. Bats tests call it via SSH:
# ssh_cmd "scripts/hermes-skill-run.sh brain-query --question 'what is PARA'"
```

**Differences to apply:** No rsync, no step-by-step output. This is a thin passthrough; `exec` replaces the process. Must handle empty `$QUERY` gracefully (print usage and exit 1).

---

### `hermes-skills/brain_http.py` (service, request-response)

**Analog:** `hermes-skills/startup-hitl-scan.py`

**Module docstring + imports pattern** (startup-hitl-scan.py lines 1–31):
```python
"""
brain_http — HTTP helper for Brain Agno endpoints.

Provides synchronous httpx wrappers for /agents/{id}/runs.
Uses multipart/form-data (NOT JSON) per Agno 2.6.7 API.

Deploy location: /opt/ultra-workshop/hermes-skills/brain_http.py
"""
from __future__ import annotations
import httpx, json, sys
from typing import Optional
```

**Core HTTP pattern** (RESEARCH.md lines 263–272):
```python
BRAIN_BASE_URL = "http://127.0.0.1:7000"
DEFAULT_TIMEOUT = 60.0

def call_agent(agent_id: str, message: str, user_id: str = "workshop") -> dict:
    """POST to /agents/{agent_id}/runs using multipart/form-data.

    CRITICAL: Brain uses form-data, NOT application/json.
    """
    resp = httpx.post(
        f"{BRAIN_BASE_URL}/agents/{agent_id}/runs",
        data={"message": message, "stream": "false", "user_id": user_id},
        timeout=DEFAULT_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()
```

**Error handling pattern** (RESEARCH.md lines 303–307 + startup-hitl-scan.py `fetch_pending()` lines 141–150):
```python
def call_agent(agent_id: str, message: str, user_id: str = "workshop") -> dict:
    ...
    data = resp.json()
    if data.get("status") == "ERROR":
        print(f"Brain error: {data['content']}", file=sys.stderr)
        sys.exit(1)
    return data
```

**CLI entrypoint pattern** (startup-hitl-scan.py module-level `DB_PATH` constant style):
```python
# Allow invocation as: python3 brain_http.py query "what is PARA"
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: brain_http.py <agent_id> <message>", file=sys.stderr)
        sys.exit(1)
    agent_id = sys.argv[1]
    message = " ".join(sys.argv[2:])
    result = call_agent(agent_id, message)
    print(result["content"])
```

**Differences to apply:** No SQLite. Pure HTTP. Must NOT use `async` (Hermes skill bodies call `terminal python3 brain_http.py ...` synchronously).

---

### `skills/brain-query/SKILL.md`, `skills/brain-ingest/SKILL.md`, `skills/brain-research/SKILL.md` (skill, request-response)

**No direct repo analog** — use RESEARCH.md Pattern 1 as canonical reference.

**Frontmatter pattern** (RESEARCH.md lines 518–530, confirmed from live VPS `plan` skill lines 365–381):
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
```

**Minimum required fields rule** (RESEARCH.md line 156): `name` + `description` are mandatory. `version`, `platforms`, `metadata.hermes.tags` are strongly recommended. `tools:` frontmatter must NOT appear (Hermes ignores/errors on Claude Code tool allowlists).

**Body pattern — Python helper delegation** (RESEARCH.md lines 535–539):
```markdown
# Brain Query

Query the Brain Agno endpoint for a vault-grounded answer.

## Usage
Parse the `--question` argument from the trigger, then call the brain HTTP helper.

## Steps
1. Extract the question from the user message
2. Run: `terminal python3 /opt/ultra-workshop/hermes-skills/brain_http.py query "<question>"`
3. Return the response content with citations
```

**Per-skill agent_id variants:**
- `brain-query` → agent_id `query`
- `brain-ingest` → agent_id `ingest` (note: HITL-gated on Brain side; smoke test checks HTTP 200 + run_id, not vault write)
- `brain-research` → agent_id `research`

**`--dry-run` body pattern** (RESEARCH.md line 243 — `plan` skill dry-run convention):
```markdown
## Dry-run
If the trigger contains `--dry-run`, output the command that would be executed
and the agent_id that would be called, then stop without running `terminal`.
```

---

### `skills/aider/SKILL.md` (skill, request-response)

**No direct repo analog** — use RESEARCH.md Pattern 3.

**Frontmatter pattern** (RESEARCH.md lines 565–577 — copy exactly):
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
```

**Body invocation pattern** (RESEARCH.md lines 578–590):
```markdown
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

**Aider subprocess flags** (RESEARCH.md lines 317–329 — VERIFIED):
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
  /path/to/workspace/file.py
```

**Subprocess safety** (RESEARCH.md Security Domain — `subprocess.run` not shell=True):
```python
import subprocess, os, sys
result = subprocess.run(
    ["aider", "--model", "openai/cloud-sonnet", "--editor-model", "openai/private-worker",
     "--architect", "--openai-api-base", "http://127.0.0.1:4000/v1",
     "--openai-api-key", os.environ["LITELLM_API_KEY"],
     "--yes-always", "--no-stream", "--message", task, workspace_file],
    capture_output=True, text=True, shell=False,
)
print(result.stdout)
if result.returncode != 0:
    print(result.stderr, file=sys.stderr)
    sys.exit(result.returncode)
```

**Working directory requirement** (RESEARCH.md Pitfall 4): Aider requires a git repo. The skill body must create `/tmp/uws-aider-workspace` and `git init` it before calling aider.

---

### `skills/caveman/SKILL.md` (skill, transform — agent_agnostic copy)

**Source:** `~/.claude/skills/caveman/SKILL.md`

**Translation delta** (frontmatter only — RESEARCH.md lines 171–175):
```yaml
# BEFORE (Claude Code — lines 1–7):
---
name: caveman
description: >
  Ultra-compressed communication mode. ...
---

# AFTER (Hermes — add required fields):
---
name: caveman
description: >
  Ultra-compressed communication mode. Cuts token usage ~75% by dropping
  filler, articles, and pleasantries while keeping full technical accuracy.
  Use when user says "caveman mode", "talk like caveman", "use caveman",
  "less tokens", "be brief", or invokes /caveman.
version: 1.0.0
author: ultra-workshop (ported from Claude Code skill)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [communication, brevity, tokens]
---
# (body unchanged — no tool references, pure Markdown instructions)
```

---

### `skills/commit/SKILL.md` (skill, batch — auto_translated)

**Source:** `~/.claude/skills/commit/SKILL.md`

**Frontmatter translation delta:**
- ADD: `version: 1.0.0`, `author: ultra-workshop (ported)`, `license: MIT`, `platforms: [linux, macos, windows]`, `metadata.hermes.tags: [git, commit, workflow]`
- REMOVE: none (Claude commit skill has no `tools:` frontmatter)

**Body translation required** — the `commit` skill references `Bash` implicitly via shell commands. In Hermes context, shell execution uses the `terminal` tool. Body instructions remain identical since they describe behavior in prose (the agent decides which tool to use). No tool name substitution needed in the body text itself.

**Claude Code README-sync checkpoint** (lines 17–18 of source) is Claude-ecosystem-specific — remove or rephrase as a general reminder to update project docs.

---

### `skills/diagnose/SKILL.md` (skill, request-response — agent_agnostic copy)

**Source:** `~/.claude/skills/diagnose/SKILL.md` (117 lines, full content read above)

**Frontmatter translation delta:**
- ADD: `version: 1.0.0`, `author: ultra-workshop (ported)`, `license: MIT`, `platforms: [linux, macos, windows]`, `metadata.hermes.tags: [debugging, diagnosis, bug-fix]`
- BODY: One reference to the `Agent` tool ("Use the Agent tool with subagent_type=Explore" appears in `triage-issue`, not `diagnose`). `diagnose` body is pure prose + methodology — no tool names. Copy body as-is.

---

### `skills/triage-issue/SKILL.md` (skill, request-response — requires_translation)

**Source:** `~/.claude/skills/triage-issue/SKILL.md`

**Frontmatter translation delta:** same ADD pattern as above; `tags: [triage, bug, github, issue]`

**Body translation required:** Line 21 uses `Agent` tool (`"Use the Agent tool with subagent_type=Explore"`). Translation:
```
# BEFORE:
Use the Agent tool with subagent_type=Explore to deeply investigate...

# AFTER (Hermes — delegate_task is the equivalent but requires manual review):
# [TRANSLATION NOTE: Agent/Explore → Hermes has no direct subagent tool.
#  Use terminal + search/read_file tools to investigate directly, or
#  use delegate_task if Hermes supports it in your version.]
Deeply investigate the codebase using search and read_file tools...
```

---

### `skills/qa/SKILL.md` (skill, request-response — requires_translation)

**Source:** `~/.claude/skills/qa/SKILL.md`

**Frontmatter translation delta:** `tags: [qa, bug-report, github, issue]`

**Body translation required:** References `Agent` tool (line 24: "kick off an Agent (subagent_type=Explore)"). Same translation pattern as `triage-issue`. Replace with direct tool invocation or add TRANSLATION NOTE comment.

---

### `scripts/test_audit.py` (test, batch)

**Analog:** `hermes-skills/test_startup_hitl_scan.py` (full file read above)

**importlib load pattern** (test_startup_hitl_scan.py lines 26–30 — CRITICAL for hyphenated filenames):
```python
import importlib.util, sys
from pathlib import Path

_MODULE_PATH = Path(__file__).parent.parent / "scripts" / "audit-claude-skills.py"
_spec = importlib.util.spec_from_file_location("audit_claude_skills", _MODULE_PATH)
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)
sys.modules["audit_claude_skills"] = audit
```

**Fixture pattern** (test_startup_hitl_scan.py lines 38–41):
```python
@pytest.fixture
def tmp_skills_dir(tmp_path) -> Path:
    """Return a temp dir that mimics ~/.claude/skills/ layout."""
    skills = tmp_path / "skills"
    skills.mkdir()
    return skills
```

**Dry-run safety test pattern** (test_startup_hitl_scan.py `test_ensure_schema_is_idempotent` lines 58–60):
```python
def test_dry_run_no_write(tmp_path, tmp_skills_dir):
    """--dry-run must never create files under HERMES_TRANSLATED_ROOT."""
    translated = tmp_path / "translated"
    audit.main_with_roots(
        claude_root=tmp_skills_dir, hermes_root=translated, dry_run=True
    )
    assert not translated.exists() or not any(translated.iterdir())
```

**Idempotency test pattern** (test_startup_hitl_scan.py style):
```python
def test_idempotent(tmp_skills_dir, tmp_path):
    """Running twice produces identical skill-audit.json output."""
    out1 = audit.run_audit(claude_root=tmp_skills_dir, dry_run=True)
    out2 = audit.run_audit(claude_root=tmp_skills_dir, dry_run=True)
    assert out1 == out2
```

**Assertion style** — use plain `assert` statements (not `unittest` methods), matching the Phase 2 test style throughout.

---

### `hermes-skills/test_skill_frontmatter.py` (test, batch)

**Analog:** `hermes-skills/test_startup_hitl_scan.py`

**Pattern:** Parametrize over all Phase 3 SKILL.md paths:
```python
import yaml
import pytest
from pathlib import Path

SKILL_DIRS = list((Path(__file__).parent.parent / "skills").glob("*/SKILL.md"))

@pytest.mark.parametrize("skill_path", SKILL_DIRS, ids=lambda p: p.parent.name)
def test_frontmatter_has_required_fields(skill_path):
    raw = skill_path.read_text()
    parts = raw.split("---")
    assert len(parts) >= 3, f"{skill_path}: no frontmatter block found"
    fm = yaml.safe_load(parts[1])
    assert "name" in fm, f"{skill_path}: missing 'name'"
    assert "description" in fm, f"{skill_path}: missing 'description'"
```

---

### `tests/phase-03/*.bats` (test, request-response)

**Analog:** `tests/phase-02/hitl-restart.bats` + `tests/phase-02/helpers.bash` (full files read above)

**helpers.bash pattern** (tests/phase-02/helpers.bash lines 1–20 — copy verbatim, update path):
```bash
#!/usr/bin/env bash
# tests/phase-03/helpers.bash — shared SSH assertion helpers

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

**Test structure pattern** (hitl-restart.bats lines 1–72):
```bash
#!/usr/bin/env bats
# tests/phase-03/skills-smoke.bats

load helpers

@test "skill <name> dry-run exits 0" {
  run ssh_cmd "bash /opt/ultra-workshop/scripts/hermes-skill-run.sh <name> --dry-run"
  [ "$status" -eq 0 ]
}
```

**setup/teardown pattern** (hitl-restart.bats lines 24–35 — use for bats that create state):
```bash
setup() {
  # create temp git repo for aider smoke test
  ssh_cmd "mkdir -p /tmp/uws-aider-test && cd /tmp/uws-aider-test && git init && git commit --allow-empty -m init"
}

teardown() {
  ssh_cmd "rm -rf /tmp/uws-aider-test"
}
```

**SSH command invocation** (hitl-restart.bats lines 37–42):
```bash
@test "brain-query returns non-empty content" {
  run ssh_cmd "bash /opt/ultra-workshop/scripts/hermes-skill-run.sh brain-query --question 'what is PARA'"
  [ "$status" -eq 0 ]
  [ -n "$output" ]
}
```

**journalctl check pattern** (hitl-restart.bats lines 52–58):
```bash
@test "aider skill run shows diff in output" {
  run ssh_cmd "bash /opt/ultra-workshop/scripts/hermes-skill-run.sh aider --task 'echo hello to /tmp/uws-aider-test/hello.txt'"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "hello.txt"
}
```

**`load helpers` path** — bats resolves relative to the test file directory. Place `helpers.bash` in `tests/phase-03/` to match Phase 2 convention.

---

## Shared Patterns

### importlib for hyphenated Python modules
**Source:** `hermes-skills/test_startup_hitl_scan.py` lines 26–30; `hermes-skills/startup-hitl-scan-hook/handler.py` `_load_hitl_module()` lines 32–43
**Apply to:** `scripts/test_audit.py` (loading `audit-claude-skills.py`); any future handler loading `brain_http.py` (no hyphen — direct import is fine)
```python
import importlib.util, sys
spec = importlib.util.spec_from_file_location("module_name", "/path/to/hyphen-file.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["module_name"] = mod
spec.loader.exec_module(mod)
```

### `--dry-run` flag convention
**Source:** `scripts/install.sh` lines 13–26
**Apply to:** `scripts/audit-claude-skills.py`, `scripts/hermes-skill-run.sh`
```bash
# Shell pattern:
DRY_RUN=false
for arg in "$@"; do [[ "$arg" == "--dry-run" ]] && DRY_RUN=true; done
if $DRY_RUN; then echo "[dry-run] would do: $ACTION"; exit 0; fi
```
```python
# Python pattern:
parser.add_argument("--apply", action="store_true")
dry_run = not args.apply
```

### Hermes SKILL.md frontmatter (canonical)
**Source:** RESEARCH.md lines 137–154 (confirmed from live VPS `plan` skill)
**Apply to:** All 10+ `skills/*/SKILL.md` files
```yaml
---
name: <slug>                    # Required. Matches directory name.
description: "<trigger phrase>" # Required. Used for skill matching.
version: 1.0.0                  # Recommended.
author: ultra-workshop          # Recommended.
license: MIT                    # Recommended.
platforms: [linux, macos, windows]  # Omit macos/windows if VPS-only
metadata:
  hermes:
    tags: [tag1, tag2]
---
```
**NEVER add:** `tools:`, `mcpServers:`, `hooks:` — these are Claude Code-only fields.

### `--dry-run` body handling in Hermes skills
**Source:** RESEARCH.md line 243 (`plan` skill convention)
**Apply to:** All `skills/*/SKILL.md` body sections
```markdown
## Dry-run behavior
If the trigger contains `--dry-run`, print the command that would execute
and the arguments extracted, then stop without calling `terminal`.
```

### Error output to stderr, success to stdout
**Source:** `hermes-skills/startup-hitl-scan.py` + handler.py throughout
**Apply to:** `hermes-skills/brain_http.py`, `hermes-skills/aider_runner.py` (if created)
```python
import sys
print(f"Error: {msg}", file=sys.stderr)
sys.exit(1)
# vs.
print(result_content)  # stdout — skill body captures this
```

### SSH smoke test via helpers.bash
**Source:** `tests/phase-02/helpers.bash` lines 1–20, `tests/phase-02/hitl-restart.bats`
**Apply to:** All `tests/phase-03/*.bats` files
```bash
load helpers   # resolves to tests/phase-03/helpers.bash
run ssh_cmd "..."
[ "$status" -eq 0 ]
```

### pytest tmp_path fixture for isolation
**Source:** `hermes-skills/test_startup_hitl_scan.py` `tmp_db` fixture lines 38–41
**Apply to:** `scripts/test_audit.py`, `hermes-skills/test_skill_frontmatter.py`
```python
@pytest.fixture
def tmp_skills_dir(tmp_path) -> Path:
    return tmp_path / "skills"
```

### subprocess.run with shell=False
**Source:** RESEARCH.md Security Domain (path injection mitigation)
**Apply to:** `hermes-skills/aider_runner.py` (companion to `skills/aider/SKILL.md`)
```python
result = subprocess.run([cmd, arg1, arg2, ...], capture_output=True, text=True, shell=False)
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `skills/brain-query/SKILL.md` | skill | request-response | No HTTP-calling Hermes skill exists in this repo yet; use RESEARCH.md Pattern 1 |
| `skills/aider/SKILL.md` | skill | request-response | No subprocess-wrapper Hermes skill exists in this repo yet; use RESEARCH.md Pattern 3 |

---

## Metadata

**Analog search scope:** `/Users/caiobellizzi/Documents/Projects/ultra-workshop/` (all directories), `~/.claude/skills/` (source Claude skills)
**Files scanned:** `hermes-skills/startup-hitl-scan.py`, `hermes-skills/test_startup_hitl_scan.py`, `hermes-skills/startup-hitl-scan-hook/handler.py`, `hermes-skills/startup-hitl-scan-hook/HOOK.yaml`, `scripts/install.sh`, `tests/phase-02/helpers.bash`, `tests/phase-02/hitl-restart.bats`, `tests/phase-02/service-up.bats`, `tests/phase-02/telegram.bats`, `~/.claude/skills/commit/SKILL.md`, `~/.claude/skills/caveman/SKILL.md`, `~/.claude/skills/diagnose/SKILL.md`, `~/.claude/skills/qa/SKILL.md`, `~/.claude/skills/triage-issue/SKILL.md`
**Pattern extraction date:** 2026-05-21
