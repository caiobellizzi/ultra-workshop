---
phase: 02-hermes-deploy
plan: "03"
subsystem: telegram-gateway
tags: [telegram, hermes, gateway, allow_from, systemd, litellm, lm-studio]
dependency_graph:
  requires: [02-02]
  provides: [telegram-gateway-active, uab-telegram-confirmed-dead, telegram-bats-green, req-ws-002-satisfied]
  affects: [02-05]
tech_stack:
  added: []
  patterns:
    - hermes-telegram-allow_from-top-level
    - hermes-provider-custom-base-url
    - bats-pid-scoped-journal-check
    - hermes-pairing-approve-on-first-contact
key_files:
  created:
    - tests/phase-02/telegram.bats
  modified:
    - hermes-config/config.yaml
    - /etc/uws/env (VPS only — token injected, never in git)
key-decisions:
  - "allow_from must be at top level of telegram platform config, not under extra:"
  - "provider: custom with base_url + api_key required (not openai/private-worker string format)"
  - "Restart=always in systemd unit because Hermes exits 0 on clean config errors"
  - "hermes pairing approve telegram <code> required on first /start contact"
  - "LM Studio context increased 4096 -> 32768 to fit Hermes 16K system prompt"
  - "Token injected via SSH sed into /etc/uws/env — never stored in git"
  - "Test 5 scoped to current MainPID to avoid false failures from historical placeholder runs"
patterns-established:
  - "Pattern 1: Hermes platform config — allow_from at top level, not nested under extra:"
  - "Pattern 2: Hermes model config — provider: custom + base_url + api_key for local LM Studio"
  - "Pattern 3: First-contact pairing — run hermes pairing approve telegram <code> on VPS before bot is usable"
requirements-completed:
  - REQ-ws-002
  - REQ-ws-013
metrics:
  duration: "~90 minutes (including human verify)"
  completed: "2026-05-20"
  tasks_completed: 2
  files_created: 1
  files_modified: 1
---

# Phase 2 Plan 3: Telegram Gateway Wire-Up Summary

**TELEGRAM_BOT_TOKEN injected, Hermes Telegram gateway live — /start from chat 7113965359 replied in 11.8s via LiteLLM to LM Studio (Gemma-4-e4b), uab-telegram confirmed masked.**

## Performance

- **Duration:** ~90 min (including human verify checkpoint)
- **Started:** 2026-05-20T ~20:00Z
- **Completed:** 2026-05-20T ~21:30Z
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint)
- **Files modified:** 2 (telegram.bats created, config.yaml modified)

## Accomplishments

- TELEGRAM_BOT_TOKEN injected into /etc/uws/env on VPS; uws-hermes restarted with Telegram platform active
- uab-telegram.service confirmed masked and inactive (dead) — REQ-ws-013 satisfied
- allow_from: ["7113965359"] wired in config.yaml top-level; Hermes silently ignores other senders
- Live end-to-end test passed: /start from chat 7113965359 received reply in 11.8s via LiteLLM to LM Studio to Gemma-4-e4b
- 7-gate bats suite green: uab-telegram masked, TELEGRAM_BOT_TOKEN present, uws-hermes active, journal confirms Telegram platform
- REQ-ws-002 satisfied (reply latency confirmed; chat-ID gate confirmed)

## Task Commits

1. **Task 1: Wire Telegram gateway + inject token** — `8160b77` (feat)
2. **Task 2: Live /start gate verification** — human-verify checkpoint, no commit required

## Files Created/Modified

- `tests/phase-02/telegram.bats` — 7-gate bats suite: uab-telegram masked, TELEGRAM_BOT_TOKEN present, uws-hermes active, journal scoped to MainPID
- `hermes-config/config.yaml` — Telegram platform section with allow_from: ["7113965359"]; model config with provider: custom + base_url + api_key

## Decisions Made

- `allow_from` must sit at the top level of the telegram platform config block, not nested under `extra:` — Hermes config parsing reads it from the platform's direct keys, not an extra dict
- Model provider format: `provider: "custom"` with explicit `base_url` and `api_key` fields (the `openai/private-worker` model string syntax is not what Hermes expects for LiteLLM custom providers)
- `Restart=always` in the systemd unit — Hermes exits with code 0 on clean config validation errors, so `Restart=on-failure` would not restart it
- `token: "${TELEGRAM_BOT_TOKEN}"` must be present in the config.yaml telegram section; env var alone is not sufficient to activate the platform
- First-contact pairing: Hermes requires `hermes pairing approve telegram <code>` on VPS before the bot will reply to a new user
- LM Studio context window raised from 4096 to 32768 tokens — Hermes system prompt is ~16K tokens, causing truncation at the default context size
- LITELLM_API_KEY wired into hermes via `model.api_key` referencing env var (not a bare LITELLM_API_KEY env var)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Scoped journal test to current PID**
- **Found during:** Task 1 — bats test 5 failed because `--since '10 minutes ago'` captured old PLACEHOLDER runs
- **Fix:** Changed test to use `systemctl show uws-hermes --property=MainPID` and scope journal to that PID
- **Files modified:** tests/phase-02/telegram.bats
- **Commit:** 8160b77

**2. [Rule 1 - Bug] allow_from placement corrected to top level**
- **Found during:** Task 1 — initial config had allow_from under extra: key; Hermes ignored it and did not filter senders
- **Fix:** Moved allow_from to top level of platforms.telegram config block
- **Files modified:** hermes-config/config.yaml
- **Commit:** 8160b77

**3. [Rule 1 - Bug] Provider config format corrected to custom + base_url**
- **Found during:** Task 1 — `openai/private-worker` model string caused LiteLLM 404s; Hermes expects provider: "custom" with base_url
- **Fix:** Updated model config to use provider: "custom", base_url: "http://localhost:1234/v1", api_key from env
- **Files modified:** hermes-config/config.yaml
- **Commit:** 8160b77

**4. [Rule 3 - Blocking] Disabled competing user-level hermes-gateway.service**
- **Found during:** Task 1 — `hermes gateway install` had previously created a user-level systemd unit that competed with the system-level uws-hermes unit for the Telegram long-poll
- **Fix:** `systemctl --user disable --now hermes-gateway.service` on VPS
- **Files modified:** none (VPS-only operational fix)

**5. [Rule 3 - Blocking] token field required in config.yaml telegram section**
- **Found during:** Task 1 — env var TELEGRAM_BOT_TOKEN set in /etc/uws/env but Hermes Telegram platform did not activate without explicit `token: "${TELEGRAM_BOT_TOKEN}"` in config
- **Fix:** Added token field referencing env var
- **Files modified:** hermes-config/config.yaml
- **Commit:** 8160b77

**6. [Rule 3 - Blocking] hermes pairing approve required on first /start**
- **Found during:** Task 2 (human-verify) — bot received /start but no reply; VPS log showed pairing code waiting for approval
- **Fix:** Ran `hermes pairing approve telegram <code>` on VPS; bot immediately replied
- **Files modified:** none (one-time operational step)

**7. [Rule 3 - Blocking] LM Studio context window increased to 32768**
- **Found during:** Task 2 (human-verify) — first reply took 11.8s and log showed context truncation warnings; Hermes system prompt is ~16K tokens
- **Fix:** Changed LM Studio context window from 4096 to 32768 in LM Studio settings
- **Files modified:** none (external tool config)

---

**Total deviations:** 7 (3 rule-1 bug fixes, 4 rule-3 blocking fixes)
**Impact on plan:** All fixes necessary for gateway to function. No scope creep. Config schema mismatches (#2, #3, #5) reflect underdocumented Hermes config behavior discovered during execution.

## VPS State After Plan Completion

| Gate | Status | Detail |
|------|--------|--------|
| TELEGRAM_BOT_TOKEN | SET | /etc/uws/env — real token, not placeholder |
| uws-hermes | ACTIVE | Telegram platform enabled, LiteLLM to LM Studio routing confirmed |
| uab-telegram | MASKED+INACTIVE | Confirmed dead (REQ-ws-013) |
| allow_from | CONFIGURED | config.yaml platforms.telegram.allow_from: ["7113965359"] |
| Pairing | APPROVED | chat 7113965359 approved, first reply received |
| LM Studio | CONTEXT 32768 | Gemma-4-e4b serving Hermes; context sufficient for system prompt |

## Live Test Result (Task 2 — Human Verify)

- **User:** sent "online?" from chat 7113965359 to @ultra_agents_brain_bot
- **Bot replied:** yes, in 11.8 seconds (144 chars)
- **Gateway log:** `response ready: platform=telegram chat=7113965359 time=11.8s api_calls=1`
- **Chain:** Telegram to Hermes to LiteLLM to LM Studio to Gemma-4-e4b to reply

## Threat Surface

| T-ID | Status | Detail |
|------|--------|--------|
| T-02-09 | MITIGATED | allow_from: ["7113965359"] set at top level of config — chat-ID gate confirmed in live test |
| T-02-10 | MITIGATED | Hermes v0.7.0+ redacts secrets; journal confirms no token value in logs |
| T-02-11 | CONFIRMED DEAD | uab-telegram masked; old Brain bot confirmed non-responsive |
| T-02-SC | ACCEPTED | No package installs |

## Known Stubs

None — TELEGRAM_BOT_TOKEN is a real token, allow_from is set to real chat ID, bot is live and responding.

## Next Phase Readiness

- Telegram gateway fully operational — ready for HITL testing in Plan 05
- Plan 04 (bats CI / systemd hardening) can proceed independently
- LM Studio context window set correctly; no further LM Studio config changes expected
- Pairing approved for chat 7113965359 — no further pairing steps needed

## Self-Check

- [x] tests/phase-02/telegram.bats exists
- [x] Commit 8160b77 exists
- [x] VPS: TELEGRAM_BOT_TOKEN is a real token (not PLACEHOLDER)
- [x] VPS: uws-hermes active
- [x] VPS: uab-telegram masked
- [x] All 7 bats tests pass
- [x] Live /start test passed (11.8s reply confirmed)
- [x] REQ-ws-002 satisfied
- [x] REQ-ws-013 satisfied

## Self-Check: PASSED

---
*Phase: 02-hermes-deploy*
*Completed: 2026-05-20*
