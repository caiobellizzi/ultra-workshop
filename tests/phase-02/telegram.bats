#!/usr/bin/env bats
# tests/phase-02/telegram.bats — Telegram gateway gate tests for Phase 02-03

load helpers

@test "uab-telegram.service is masked" {
  assert_service_masked "uab-telegram.service"
}

@test "uab-telegram.service is not active" {
  run ssh_cmd "systemctl is-active uab-telegram.service"
  [[ "$output" != "active" ]]
}

@test "/etc/uws/env contains TELEGRAM_BOT_TOKEN (not placeholder)" {
  run ssh_cmd "grep -c '^TELEGRAM_BOT_TOKEN=' /etc/uws/env"
  [ "$status" -eq 0 ]
  [ "$output" -ge 1 ]
  # Ensure it's not still the placeholder
  run ssh_cmd "grep '^TELEGRAM_BOT_TOKEN=PLACEHOLDER' /etc/uws/env"
  [ "$status" -ne 0 ]
}

@test "uws-hermes.service is active after token injection" {
  assert_service_active "uws-hermes.service"
}

@test "uws-hermes current run shows no placeholder token error" {
  # Get PID of current running uws-hermes process
  run ssh_cmd "systemctl show uws-hermes --property=MainPID --value 2>&1"
  local pid="$output"
  [ -n "$pid" ] && [ "$pid" != "0" ]
  # Check logs only for this PID (current run)
  run ssh_cmd "journalctl -u uws-hermes _PID=$pid --no-pager 2>&1"
  ! echo "$output" | grep -q "ERROR.*TELEGRAM_BOT_TOKEN.*placeholder"
}

@test "uws-hermes journal does not show 'No messaging platforms enabled' after last start" {
  run ssh_cmd "journalctl -u uws-hermes --no-pager --since '5 minutes ago' 2>&1"
  ! echo "$output" | grep -q "No messaging platforms enabled"
}

@test "TELEGRAM_BOT_TOKEN is not in any git-tracked file" {
  run bash -c "cd /Users/caiobellizzi/Documents/Projects/ultra-workshop && git grep -l 'TELEGRAM_BOT_TOKEN=[^P$]' -- '*.yaml' '*.yml' '*.json' '*.env' '*.sh' 2>/dev/null | grep -v 'PLACEHOLDER'"
  [ "$status" -ne 0 ] || [ -z "$output" ]
}
