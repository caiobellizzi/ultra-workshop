#!/usr/bin/env bats
# tests/phase-04/coder-smoke.bats — workshop_coder.py dry-run + envelope shape

load helpers

skip_if_workshop_down() {
  run ssh_cmd "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 -c 'import workshop.types' 2>/dev/null; echo exit:\$?"
  if echo "$output" | grep -q "exit:1"; then
    skip "workshop package not importable on VPS"
  fi
}

@test "workshop_coder.py --dry-run exits 0 and emits Diff envelope with all required keys" {
  skip_if_workshop_down
  run ssh_cmd "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 /opt/ultra-workshop/hermes-skills/workshop_coder.py --query '{\"task_id\":\"smoke\",\"plan\":{\"goal\":\"noop\"},\"workspace_dir\":\"\"}' --dry-run 2>/dev/null"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"summary"'* ]]
  [[ "$output" == *'"changes"'* ]]
  [[ "$output" == *'"branch"'* ]]
  [[ "$output" == *'"workspace_dir"'* ]]
  [[ "$output" == *"workshop/dry-run"* ]]
}
