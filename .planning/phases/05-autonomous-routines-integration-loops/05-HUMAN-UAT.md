---
status: partial
phase: 05-autonomous-routines-integration-loops
source: [05-VERIFICATION.md]
started: 2026-05-28T19:45:00Z
updated: 2026-05-28T19:45:00Z
---

## Current Test

[awaiting human testing — requires VPS access]

## Tests

### 1. Trust symlink on VPS
expected: `readlink /opt/ultra-workshop/workshop/trust_shared.py` returns `/opt/ultra-agents-brain/ultra_brain/trust.py` and `from workshop.trust_shared import classify_action; classify_action('git push')` executes without error
result: [pending]

### 2. 30s Telegram dispatch smoke test
expected: Inject synthetic queue entry with `action: post-to-telegram`, `confirmed: true`, `dispatched: false`; confirm Telegram message arrives within 30s and entry shows `"dispatched": true` in queue file
result: [pending]

### 3. Hermes cron registration
expected: After running `python hermes-skills/bootstrap_cron_jobs.py`, `hermes cron list | grep daily-research` shows `schedule: 0 7 * * *` and all 4 cron jobs appear
result: [pending]

### 4. systemd service active
expected: After `sudo systemctl start uws-bug-scan-fastpoll`, `systemctl is-active uws-bug-scan-fastpoll` returns `active` and journal shows polling loop running
result: [pending]

### 5. Catch-up hook fires on Hermes restart
expected: With a missed daily-research (last run >24h ago), `sudo systemctl restart hermes` triggers the startup-cron-catchup-hook and re-runs daily-research within 60s
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
