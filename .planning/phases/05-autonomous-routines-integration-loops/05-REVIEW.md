---
phase: 05-autonomous-routines-integration-loops
reviewed: 2026-05-28T19:50:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - deploy/systemd/uws-bug-scan-fastpoll.service
  - hermes-skills/bootstrap_cron_jobs.py
  - hermes-skills/brain_http.py
  - hermes-skills/cron_bug_scan_fastpoll.py
  - hermes-skills/cron_daily_research.py
  - hermes-skills/cron_nightly_tests.py
  - hermes-skills/cron_standard_poll.py
  - hermes-skills/startup-cron-catchup-hook/handler.py
  - hermes-skills/startup-cron-catchup-hook/HOOK.yaml
  - hermes-skills/telegram_alert.py
  - scripts/install.sh
  - vault/_system/integration-contract.md
  - workshop/repo_registry.py
findings:
  critical: 5
  warning: 7
  info: 3
  total: 15
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-05-28T19:50:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Phase 05 introduces four autonomous routines (fast-poll dispatcher, standard-poll dispatcher, daily-research cron, nightly-tests cron), a startup catch-up hook, and the plumbing that ties them together (Brain HTTP helper, Telegram alert helper, bootstrap cron jobs, systemd unit, install script, integration contract, repo registry). The integration contract and repo registry are well-structured. The critical findings below are concentrated in two areas: a split-brain queue path used by the two pollers (they read different files) and a silently broken `post-to-telegram` path in `cron_standard_poll`. Several error-handling gaps and one stale-lock window complete the critical tier.

---

## Critical Issues

### CR-01: Split queue path — fastpoll and standard-poll read different files

**Files:** `hermes-skills/cron_bug_scan_fastpoll.py:83-84` and `hermes-skills/cron_standard_poll.py:40`

**Issue:** The two dispatchers resolve the queue file to different paths and use different environment variables:

- `cron_bug_scan_fastpoll.py` → `$VAULT_VPS_PATH/_system/.workshop-queue.jsonl` (default: `/srv/second-brain/_system/.workshop-queue.jsonl`)
- `cron_standard_poll.py` → `$WORKSHOP_QUEUE_PATH` (default: `/srv/second-brain/.workshop-queue.jsonl`)

These are different directories (`_system/` vs root). Both dispatchers run in production; whichever path Brain actually writes to is invisible to the other poller. Entries will appear in one dispatcher and never be seen by the other.

**Fix:**
```python
# cron_bug_scan_fastpoll.py — change _queue_path() to match standard_poll
def _queue_path() -> Path:
    return Path(os.environ.get("WORKSHOP_QUEUE_PATH", "/srv/second-brain/.workshop-queue.jsonl"))
```
Remove the `VAULT_VPS_PATH` usage and standardize both scripts on the single env var `WORKSHOP_QUEUE_PATH`. Update the integration contract to declare the canonical path.

---

### CR-02: `post-to-telegram` silently no-ops in `cron_standard_poll`

**File:** `hermes-skills/cron_standard_poll.py:72`, `hermes-skills/telegram_alert.py` (entire file)

**Issue:** `_dispatch_entry` handles `post-to-telegram` by calling `_run_skill("telegram_alert", entry)`, which executes `telegram_alert.py` as a subprocess. However, `telegram_alert.py` has no `__main__` block, no `main()` function, and reads nothing from stdin. When invoked as a subprocess it imports, defines `send_alert()`, then exits 0 without sending anything. The queue entry is then ACK'd as dispatched. Telegram messages intended for the standard-poll path are silently swallowed.

**Fix — Option A:** Add an entrypoint to `telegram_alert.py`:
```python
if __name__ == "__main__":
    import json, sys
    entry = json.loads(sys.stdin.read())
    send_alert(entry.get("text", "(no text)"))
```

**Fix — Option B:** In `_dispatch_entry`, call `send_alert` directly (as `cron_bug_scan_fastpoll` already does) instead of spawning a subprocess:
```python
from telegram_alert import send_alert as _send_alert

if action == "post-to-telegram":
    try:
        _send_alert(entry.get("text", "(no text)"))
    except Exception as exc:
        logger.error("telegram send_alert failed for %s: %s", entry_id, exc)
```

---

### CR-03: `cron_standard_poll` ACKs queue entries unconditionally even on skill failure

**File:** `hermes-skills/cron_standard_poll.py:65-82`

**Issue:** `_dispatch_entry` calls `_run_skill(...)` and then unconditionally calls `brain_http.mark_queue_entry_dispatched(entry_id)` regardless of whether the skill subprocess succeeded, timed out, or was not found. `_run_skill` only logs errors and returns `None` on failure. The result is that any failed dispatch (subprocess non-zero exit, timeout, missing skill file) is silently ACK'd and the entry is permanently lost from the queue.

```python
def _dispatch_entry(entry: dict) -> None:
    ...
    if action == "post-to-telegram":
        _run_skill("telegram_alert", entry)  # may fail silently
    ...
    brain_http.mark_queue_entry_dispatched(entry_id)  # ACK always happens
```

**Fix:** Return a success boolean from `_run_skill` and only ACK on success:
```python
def _run_skill(skill_name: str, entry: dict) -> bool:
    ...
    # return True on success, False on any error/timeout/non-zero exit

def _dispatch_entry(entry: dict) -> None:
    ...
    ok = True
    if action == "post-to-telegram":
        ok = _run_skill("telegram_alert", entry)
    ...
    if ok:
        brain_http.mark_queue_entry_dispatched(entry_id)
    else:
        logger.error("Skill failed — NOT ACKing entry %s; will retry next poll", entry_id)
```

---

### CR-04: PID file left behind on import failure (stale lock on next start)

**File:** `hermes-skills/cron_bug_scan_fastpoll.py:44, 53-55, 69`

**Issue:** The PID file is written at line 44. The risky module-level imports (`brain_http`, `telegram_alert`, `workshop.cost`) occur at lines 53–55. The `atexit` cleanup handler is registered only at line 69. If any import at lines 53–55 raises `ModuleNotFoundError` or any other exception, Python exits immediately without the `atexit` handler ever firing. The PID file remains on disk. The next invocation reads the stale PID, calls `os.kill(pid, 0)` — if the OS has recycled that PID to a different process, the check passes, the script prints "Already running" and exits. The fastpoll service never starts.

**Fix:** Register the atexit handler and define `_remove_pid_file` immediately after writing the PID file, before any imports that can fail:
```python
_pid_path.write_text(str(os.getpid()))

def _remove_pid_file() -> None:
    try:
        _pid_path.unlink(missing_ok=True)
    except Exception:
        pass

atexit.register(_remove_pid_file)

# Only now do the risky imports
import brain_http
import telegram_alert
...
```

---

### CR-05: `PermissionError` not caught in PID existence check — script crashes at module level

**File:** `hermes-skills/cron_bug_scan_fastpoll.py:38-42`

**Issue:** `os.kill(int(_existing_pid), 0)` raises `PermissionError` when the target process exists but is owned by a different user. The `except (ProcessLookupError, ValueError)` clause does not catch `PermissionError`, so it propagates to the top level. Because this code runs at module import time (before `try`/`except` wrappers), the entire script crashes with an unhandled exception. The stale PID file is also not cleaned up (see CR-04).

In practice the service runs as `uws` and PID reuse across users is rare, but it is a latent crash path that becomes real when deploying alongside other services or after OS PID recycling.

**Fix:**
```python
try:
    os.kill(int(_existing_pid), 0)
    print(f"Already running (pid {_existing_pid}), exiting.", file=sys.stderr)
    sys.exit(1)
except (ProcessLookupError, ValueError, PermissionError):
    pass  # stale PID file or not our process — continue
```

---

## Warnings

### WR-01: `cron_nightly_tests` clone directory never cleaned up — second nightly run always fails per repo

**File:** `hermes-skills/cron_nightly_tests.py:68-82`

**Issue:** Each run clones repos into `CLONE_BASE / full_name.replace("/", "_")` (e.g., `/tmp/uws-test/owner_repo`). There is no cleanup before or after cloning. On the second nightly run, `git clone` fails with "destination path already exists" (exit code non-zero). The failure is logged and the function returns early, skipping the test run. After the first nightly run, every subsequent run silently skips all repos.

**Fix:** Add cleanup before cloning:
```python
import shutil

clone_dir = CLONE_BASE / full_name.replace("/", "_")
if clone_dir.exists():
    shutil.rmtree(clone_dir)
```

---

### WR-02: `cron_standard_poll` applies quiet-hours gate to `post-to-telegram` (zero-HITL verb)

**File:** `hermes-skills/cron_standard_poll.py:121-123`

**Issue:** The standard-poll's quiet-hours check at line 121 fires before the dispatch loop and blocks ALL verbs, including `post-to-telegram`. The integration contract (Flow E) classifies this verb as zero-HITL and `cron_bug_scan_fastpoll` explicitly exempts it via `_ZERO_HITL_VERBS`. The two pollers disagree: during quiet hours, fast-poll sends Telegram messages but standard-poll does not. Any `post-to-telegram` entry that arrives when only standard-poll runs (e.g., between 4-hour intervals where fast-poll restart window applies) will be silently deferred.

**Fix:** Move the quiet-hours gate inside the dispatch loop and skip it for zero-HITL verbs:
```python
_ZERO_HITL_ACTIONS = {"post-to-telegram"}

for entry in eligible:
    if _is_quiet_hours() and entry.get("action") not in _ZERO_HITL_ACTIONS:
        logger.info("Quiet hours — deferring entry %s", entry.get("id"))
        continue
    try:
        _dispatch_entry(entry)
    except Exception as exc:
        ...
```

---

### WR-03: `brain_http.call_agent` docstring documents `SystemExit(1)` that the implementation no longer raises

**File:** `hermes-skills/brain_http.py:42-43`

**Issue:** The docstring states `Raises: SystemExit(1) if Brain returns status "ERROR"`. The implementation (lines 52–58) was deliberately relaxed (V4 comment) to only print to stderr and return data. Callers reading the docstring may defensively wrap call sites in `try/except SystemExit`, missing the real error path, or may assume the call is safe when `status == "ERROR"` is returned to them.

**Fix:** Update the docstring to reflect current behavior:
```python
"""
...
Returns:
    Parsed JSON response dict. If Brain returns status "ERROR", the error
    is printed to stderr and the response dict is still returned (callers
    must check response.get("status") == "ERROR" themselves).

Raises:
    httpx.HTTPError on network/HTTP transport failures.
"""
```

---

### WR-04: YAML frontmatter injection via unquoted `title` in `cron_daily_research`

**File:** `hermes-skills/cron_daily_research.py:140-146`

**Issue:** The ingest payload is built by string interpolation of `title` directly into YAML frontmatter:
```python
ingest_payload = (
    f"---\n"
    f"title: {title}\n"
    ...
)
```
If `title` contains a colon (e.g., `"HTTP: A Protocol Overview"`), the resulting YAML is `title: HTTP: A Protocol Overview`, which is invalid YAML and will confuse any YAML parser downstream. If `title` contains a newline, it can inject arbitrary YAML fields.

**Fix:** Quote the title:
```python
import re
safe_title = title.replace('"', '\\"')
ingest_payload = (
    f"---\n"
    f'title: "{safe_title}"\n'
    ...
)
```
Or use the `yaml` module to emit the frontmatter block.

---

### WR-05: `cron_nightly_tests` infrastructure: `test_command` runs arbitrary commands from registry

**File:** `hermes-skills/cron_nightly_tests.py:85-90`

**Issue:** `shlex.split(test_command)` is passed directly to `subprocess.run` with `cwd=clone_dir`. The `test_command` value comes from the registry JSON written by Brain. If the registry is tampered with (e.g., a compromised Brain, a malformed registry write via CR-06), any system command can be executed as the `uws` user. `shlex.split` prevents shell metacharacter injection but does not prevent arbitrary command execution (e.g., `"rm -rf /home/uws"` is still valid).

**Fix:** Enforce an allowlist of permitted test command prefixes, or validate `test_command` against a pattern (e.g., must start with `pytest`, `cargo test`, `go test`, `npm test`) before executing:
```python
ALLOWED_TEST_PREFIXES = ("pytest", "cargo test", "go test", "npm test", "npx vitest")
if not any(test_command.startswith(p) for p in ALLOWED_TEST_PREFIXES):
    print(f"[nightly-tests] REJECTED test_command for {full_name}: {test_command!r}", flush=True)
    return
```

---

### WR-06: `install.sh` Step N+5 fails silently when `VAULT_VPS_PATH` is unset and `rsync_files` caller is remote

**File:** `scripts/install.sh:112`

**Issue:** `rsync_files` is a local function that, in non-dry-run mode, runs `rsync -av src VPS:dst`. The destination `${VAULT_VPS_PATH:-/srv/second-brain}/_system/` expands locally. If `VAULT_VPS_PATH` is not set on the local machine, it falls back to `/srv/second-brain` which may not match the VPS layout. The step description implies the integration contract should land in the vault, but if the path is wrong the `rsync` succeeds to the wrong location (or fails if `VPS:/srv/second-brain` does not exist). `set -euo pipefail` will abort on rsync failure, but a wrong-path rsync succeeds silently.

**Fix:** Require the env var explicitly, or validate the path before deploying:
```bash
: "${VAULT_VPS_PATH:?VAULT_VPS_PATH must be set for Step N+5}"
rsync_files "vault/_system/integration-contract.md" "${VAULT_VPS_PATH}/_system/"
```

---

### WR-07: `bootstrap_cron_jobs.py` unconditionally calls `register_cron_jobs()` at module load — no Hermes context guard

**File:** `hermes-skills/bootstrap_cron_jobs.py:66`

**Issue:** `register_cron_jobs()` is called at module level (line 66), which means any `import bootstrap_cron_jobs` anywhere (tests, linter, other scripts) will attempt to call `cronjob()` — an undefined global injected only by the Hermes runtime. Outside Hermes, this raises `NameError: name 'cronjob' is not defined` immediately on import. The `noqa: F821` comment acknowledges the undefined name but there is no guard.

**Fix:**
```python
if __name__ == "__main__":
    register_cron_jobs()
```
This way, direct execution via `hermes skill run bootstrap_cron_jobs.py` still works (Hermes runs the file as `__main__`), but accidental imports in test environments do not crash.

---

## Info

### IN-01: Hardcoded VPS IP address in `install.sh`

**File:** `scripts/install.sh:8`

**Issue:** `VPS="root@31.97.130.253"` is hardcoded. A change of VPS IP requires a source code edit.

**Fix:** Accept it as an environment variable with the current value as default:
```bash
VPS="${UWS_VPS:-root@31.97.130.253}"
```

---

### IN-02: `_load_module` helper duplicated across three files

**Files:** `hermes-skills/cron_daily_research.py:36-45`, `hermes-skills/cron_nightly_tests.py:34-43`, `hermes-skills/startup-cron-catchup-hook/handler.py:35-50`

**Issue:** The same `_load_module(name, filename)` implementation is copy-pasted across three files. Any bug fix or behavior change must be applied in three places.

**Fix:** Extract into a shared `hermes_utils.py` module in the `hermes-skills/` directory and import from there.

---

### IN-03: `install.sh` uses `curl | bash` without integrity verification for Hermes installer

**File:** `scripts/install.sh:65`

**Issue:** The Hermes agent is installed via `curl -fsSL <url> | bash`. This pattern is common but fetches and executes arbitrary code at install time without checksum or signature verification. A compromised CDN, DNS hijack, or repository compromise delivers malicious code silently. The `-fsSL` flags follow redirects, increasing exposure.

**Fix:** Pin to a specific commit hash and verify a SHA-256 checksum, or vendor the install script:
```bash
HERMES_SHA256="<expected-sha256>"
curl -fsSL "$HERMES_INSTALL_URL" -o /tmp/hermes-install.sh
echo "$HERMES_SHA256  /tmp/hermes-install.sh" | sha256sum -c -
bash /tmp/hermes-install.sh
```

---

_Reviewed: 2026-05-28T19:50:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
