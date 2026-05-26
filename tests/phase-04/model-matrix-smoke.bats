#!/usr/bin/env bats
# tests/phase-04/model-matrix-smoke.bats
#
# Plan 04-04 Task 6: per-specialist MAX_TURNS and HERMES_HOME routing.
# Runs hermes-skill-run.sh with --dry-run (no VPS, no Hermes binary needed)
# and asserts the dry-run output reports the expected turn budget and home
# directory for each specialist alias.

SCRIPT="$BATS_TEST_DIRNAME/../../scripts/hermes-skill-run.sh"

@test "triage-specialist resolves to MAX_TURNS=3 and specialist-home-private" {
  run env -u MAX_TURNS bash "$SCRIPT" triage-specialist --dry-run "add hello.txt"
  [ "$status" -eq 0 ]
  [[ "$output" == *"--max-turns 3"* ]]
  [[ "$output" == *"HERMES_HOME=/opt/ultra-workshop/specialist-home-private"* ]]
}

@test "planner-specialist resolves to hermes chat with specialist-home-orchestrator" {
  run env -u MAX_TURNS bash "$SCRIPT" planner-specialist --dry-run "add hello.txt"
  [ "$status" -eq 0 ]
  [[ "$output" == *"--max-turns 8"* ]]
  [[ "$output" == *"HERMES_HOME=/opt/ultra-workshop/specialist-home-orchestrator"* ]]
}

@test "reviewer-specialist resolves to deterministic local reviewer" {
  run env -u MAX_TURNS bash "$SCRIPT" reviewer-specialist --dry-run "noop"
  [ "$status" -eq 0 ]
  [[ "$output" == *"workshop_reviewer.py"* ]]
  [[ "$output" == *"deterministic"* ]]
}

@test "coder-specialist resolves to deterministic local coder" {
  run env -u MAX_TURNS bash "$SCRIPT" coder-specialist --dry-run "add hello.txt"
  [ "$status" -eq 0 ]
  [[ "$output" == *"workshop_coder.py"* ]]
  [[ "$output" == *"deterministic"* ]]
}

@test "unknown specialist falls back to MAX_TURNS=8 and specialist-home-private" {
  run env -u MAX_TURNS bash "$SCRIPT" some-other-specialist --dry-run "noop"
  [ "$status" -eq 0 ]
  [[ "$output" == *"--max-turns 8"* ]]
  [[ "$output" == *"HERMES_HOME=/opt/ultra-workshop/specialist-home-private"* ]]
}

@test "MAX_TURNS env override still resolves correct HERMES_HOME" {
  run env MAX_TURNS=42 bash "$SCRIPT" triage-specialist --dry-run "noop"
  [ "$status" -eq 0 ]
  [[ "$output" == *"--max-turns 42"* ]]
  [[ "$output" == *"HERMES_HOME=/opt/ultra-workshop/specialist-home-private"* ]]
}
