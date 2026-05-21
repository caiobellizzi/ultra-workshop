#!/usr/bin/env bats
# tests/phase-03/scaffold.bats — Phase 3 Wave 0 scaffold validation
# Validates that hermes-skill-run.sh is deployed and executable on VPS,
# and that the hermes binary is reachable as the uws user.

load helpers

@test "hermes-skill-run.sh dry-run exits 0 for dummy skill" {
  run ssh_cmd "bash /opt/ultra-workshop/scripts/hermes-skill-run.sh dummy-skill --dry-run"
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "\[dry-run\]"
}

@test "hermes binary is reachable as uws user" {
  run ssh_cmd "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/hermes --version"
  [ "$status" -eq 0 ]
}
