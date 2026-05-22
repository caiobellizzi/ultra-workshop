#!/usr/bin/env bats
# tests/phase-04/fix-smoke.bats — workshop-fix dry-run smoke tests

load helpers

skip_if_workshop_down() {
  run ssh_cmd "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 -c 'import workshop.types' 2>/dev/null; echo exit:\$?"
  if echo "$output" | grep -q "exit:1"; then
    skip "workshop package not importable on VPS"
  fi
}

@test "workshop-fix dry-run exits 0" {
  run ssh_cmd "bash /opt/ultra-workshop/scripts/hermes-skill-run.sh workshop-fix --dry-run --issue 'https://github.com/caiobellizzi/test-workshop-sandbox/issues/1'"
  [ "$status" -eq 0 ]
}

@test "workshop_fix.py --issue-url --dry-run exits 0" {
  skip_if_workshop_down
  run ssh_cmd "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 /opt/ultra-workshop/hermes-skills/workshop_fix.py --issue-url 'https://github.com/caiobellizzi/test-workshop-sandbox/issues/1' --dry-run 2>/dev/null"
  [ "$status" -eq 0 ]
  [[ "$output" == *"dry-run"* ]]
}
