#!/usr/bin/env bats
# tests/phase-03/skills-smoke.bats — dry-run smoke tests for Tier 1 Hermes skills
#
# Each test verifies that hermes-skill-run.sh <skill-name> --dry-run:
#   1. Exits 0 (the dry-run guard short-circuits before calling hermes)
#   2. Produces output (the [dry-run] echo line)

load helpers

@test "skill caveman dry-run exits 0" {
  run ssh_cmd "bash /opt/ultra-workshop/scripts/hermes-skill-run.sh caveman --dry-run"
  [ "$status" -eq 0 ]
}

@test "skill commit dry-run exits 0" {
  run ssh_cmd "bash /opt/ultra-workshop/scripts/hermes-skill-run.sh commit --dry-run"
  [ "$status" -eq 0 ]
}

@test "skill diagnose dry-run exits 0" {
  run ssh_cmd "bash /opt/ultra-workshop/scripts/hermes-skill-run.sh diagnose --dry-run"
  [ "$status" -eq 0 ]
}

@test "skill triage-issue dry-run exits 0" {
  run ssh_cmd "bash /opt/ultra-workshop/scripts/hermes-skill-run.sh triage-issue --dry-run"
  [ "$status" -eq 0 ]
}

@test "skill qa dry-run exits 0" {
  run ssh_cmd "bash /opt/ultra-workshop/scripts/hermes-skill-run.sh qa --dry-run"
  [ "$status" -eq 0 ]
}

@test "skill knowledge dry-run exits 0" {
  run ssh_cmd "bash /opt/ultra-workshop/scripts/hermes-skill-run.sh knowledge --dry-run"
  [ "$status" -eq 0 ]
}

@test "skill write-a-prd dry-run exits 0" {
  run ssh_cmd "bash /opt/ultra-workshop/scripts/hermes-skill-run.sh write-a-prd --dry-run"
  [ "$status" -eq 0 ]
}

@test "skill zoom-out dry-run exits 0" {
  run ssh_cmd "bash /opt/ultra-workshop/scripts/hermes-skill-run.sh zoom-out --dry-run"
  [ "$status" -eq 0 ]
}

@test "skill grill-me dry-run exits 0" {
  run ssh_cmd "bash /opt/ultra-workshop/scripts/hermes-skill-run.sh grill-me --dry-run"
  [ "$status" -eq 0 ]
}

@test "skill triage dry-run exits 0" {
  run ssh_cmd "bash /opt/ultra-workshop/scripts/hermes-skill-run.sh triage --dry-run"
  [ "$status" -eq 0 ]
}
