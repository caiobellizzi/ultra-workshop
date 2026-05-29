<!-- generated-by: gsd-doc-writer -->
# Testing

## Test framework and setup

Ultra-workshop uses two complementary test frameworks:

- **pytest** — Python unit tests for all workshop modules, dashboard backend, and hermes-skills. Test configuration is in `pyproject.toml`.
- **bats** (Bash Automated Testing System) — shell smoke tests for CLI invocations that verify deployed services on the VPS.

Install dependencies before running pytest:

```bash
pip install -e ".[dev]"
# or, inside the VPS virtualenv:
/opt/ultra-workshop/hermes/venv/bin/pip install -e ".[dev]"
```

bats must be installed separately:

```bash
brew install bats-core   # macOS
apt-get install bats     # Debian/Ubuntu
```

## Test categories

The suite is divided into three categories with different runtime requirements:

| Category | Files | Requires |
|---|---|---|
| Unit tests (pytest) | `tests/*.py`, `tests/phase-*/test_*.py`, `dashboard/backend/tests/`, `hermes-skills/test_*.py` | Python only — no VPS, no LLM calls |
| Shell smoke tests (bats) | `tests/phase-*/**.bats` | VPS SSH access or partial VPS setup |
| Integration tests | Phase-02 and Phase-03 bats | Running Hermes + LiteLLM on VPS |

LLM calls are **always mocked** in unit tests. pytest tests must never make real LLM API calls.

## Running tests

### Full pytest suite

```bash
pytest
```

`pyproject.toml` configures `testpaths = ["hermes-skills", "scripts", "tests"]`, so this picks up all Python tests across those directories.

### Specific phase

```bash
pytest tests/phase-09/
pytest tests/phase-04/
```

### Dashboard backend tests only

```bash
pytest dashboard/backend/tests/
```

### With coverage

```bash
pytest --cov=workshop --cov=hermes-skills
```

### Single bats file

```bash
bats tests/phase-04/build-smoke.bats
bats tests/phase-04/fix-smoke.bats
```

### All bats files in a phase

```bash
bats tests/phase-04/
```

## Test suite structure

```
tests/
├── test_repo_registry.py          # Repo registry unit tests
├── test_workshop_repo_choice.py   # Repo selection logic
├── phase-02/                      # Hermes deploy smoke (bats — requires VPS SSH)
│   ├── helpers.bash
│   ├── hitl-restart.bats
│   ├── pre-deploy.bats
│   ├── service-up.bats
│   └── telegram.bats
├── phase-03/                      # Skill toolkit smoke (bats — requires VPS + LiteLLM)
│   ├── helpers.bash
│   ├── aider-smoke.bats
│   ├── brain-smoke.bats
│   ├── scaffold.bats
│   └── skills-smoke.bats
├── phase-04/                      # Build/fix pipeline (pytest + bats)
│   ├── test_cost.py
│   ├── test_extract_json.py
│   ├── test_ledger.py
│   ├── test_orchestrator.py
│   ├── test_planner.py
│   ├── test_requirements_gate.py
│   ├── test_reviewer.py
│   ├── test_workshop_build.py
│   ├── test_workshop_continue.py
│   ├── build-smoke.bats
│   ├── coder-smoke.bats
│   ├── fix-smoke.bats
│   └── model-matrix-smoke.bats
├── phase-06/                      # Repo selection smoke (bats)
│   └── repo-smoke.bats
├── phase-07/                      # Planner (pytest + bats)
│   ├── __init__.py
│   ├── test_doc_resolver.py
│   ├── test_planner_llm.py
│   ├── test_workspace.py
│   ├── hermes-tool-notes.txt
│   └── planner-smoke.bats
├── phase-08/                      # Quality uplift (pytest)
│   └── test_quality_uplift.py
└── phase-09/                      # Advanced architecture (pytest)
    ├── test_audit_log.py
    ├── test_brainstorm_hitl.py
    ├── test_cost_budget.py
    ├── test_merge_agent.py
    ├── test_requirements_brain.py
    ├── test_review_wave.py
    └── test_worktree.py

dashboard/backend/tests/           # Dashboard backend unit tests (pytest)
├── test_config_service.py
├── test_hitl_service.py
└── test_task_store.py

hermes-skills/                     # Skill-level unit tests (pytest)
├── test_skill_frontmatter.py
└── test_startup_hitl_scan.py
```

## Writing new tests

### File naming

- Python tests: `test_<module_name>.py`, placed in the phase directory that matches the feature or in `tests/` for cross-cutting concerns.
- Bats tests: `<feature>-smoke.bats`, placed in the appropriate `tests/phase-*/` directory.

### Mocking LLM calls

All LLM calls must be mocked. Use `unittest.mock.MagicMock` or `monkeypatch` — never make real API calls in pytest:

```python
from unittest.mock import MagicMock
import pytest

def test_something(monkeypatch):
    monkeypatch.setattr("workshop.orchestrator.run_specialist", MagicMock(return_value=...))
    # test logic here
```

### Bats shared helpers

Shell smoke tests load a shared `helpers.bash` from the same phase directory. The helpers define `ssh_cmd`, `assert_service_active`, and `assert_service_masked` for VPS assertions. Load them with:

```bash
load helpers
```

## Coverage requirements

No minimum coverage thresholds are configured. Run with `--cov` to inspect coverage during development:

```bash
pytest --cov=workshop --cov=hermes-skills --cov-report=term-missing
```

## CI integration

The repository has one GitHub Actions workflow (`.github/workflows/summary.yml`) which runs a scheduled brain summary job — it does not execute the test suite in CI.

pytest and bats tests are run manually or as part of VPS deployment validation. Bats smoke tests in Phase-02 and Phase-03 require SSH access to the VPS (`31.97.130.253`) and are treated as post-deploy verification steps rather than pre-merge gates.

## Environment variables for bats smoke tests

Bats tests that connect to the VPS or invoke LiteLLM require the following environment variables:

| Variable | Required by | Description |
|---|---|---|
| `HERMES_HOME` | Phase-04 bats | Path to the Hermes home directory on the VPS |
| `LITELLM_API_KEY` | Phase-03 bats | API key for the LiteLLM proxy |

On the VPS these are sourced from `/etc/uws/env`. For local execution, export them before running bats:

```bash
export HERMES_HOME=/opt/ultra-workshop/specialist-home-private
export LITELLM_API_KEY=<your-key>
bats tests/phase-03/aider-smoke.bats
```

Phase-02 and Phase-03 bats tests also require VPS SSH access with `StrictHostKeyChecking=no` accepted for `root@31.97.130.253`. <!-- VERIFY: VPS IP and user still current -->
