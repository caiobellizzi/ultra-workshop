# Phase 4 Wave 0 Probe Results
Date: 2026-05-22T00:00:00Z

## Architecture Decision (FINAL — not probe-dependent)
Architecture B is used throughout Phase 4:
- workshop_build.py and workshop_fix.py are standalone Python scripts (no Hermes imports)
- Each specialist role = subprocess.run(["bash", "/opt/ultra-workshop/scripts/hermes-skill-run.sh", "<role>-specialist", ...])
- HITL gate = workshop_build.py exits with code 2 + JSON to stdout; SKILL.md body catches exit 2 and calls clarify

## Q1: Hermes Python body delegate_task support (informational only)
- Status: NOT_SUPPORTED
- Evidence: Probe attempt via `hermes chat --skills probe-delegate` failed with "Error: Error code: 400 - {'error': {'message': 'No connected db.', 'type': 'no_db_connection'}}". The Hermes gateway runs as a daemon (uws-hermes.service) but the LiteLLM private-worker database is not accessible for direct CLI invocations outside the gateway process. Additionally, attempting to run hermes as the uws user from root's cwd fails with PermissionError on /root/.git. The delegate_task API is not reliably callable from a standalone skill body in the current VPS configuration.
- Architecture impact: N/A — Architecture B decided regardless. Wave 1 uses subprocess.run per specialist, not delegate_task.

## Q3: gh CLI on VPS
- Status: INSTALLED_NOW
- Version: gh version 2.45.0 (2025-07-18 Ubuntu 2.45.0-1ubuntu0.3)
- Installation method: apt-get install -y gh (ubuntu noble-security/universe package)

## Test-workshop-sandbox
- Status: PENDING_PAT (create after PAT injected)
- URL: https://github.com/caiobellizzi/test-workshop-sandbox
- Note: GITHUB_PAT not yet present in /etc/uws/env — repo existence cannot be verified until PAT is injected (Task 2 checkpoint)
