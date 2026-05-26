#!/usr/bin/env bats
# tests/phase-07/planner-smoke.bats
#
# Plan 07-03 Task 1: activated smoke tests for post-Phase-7 planner routing.
# hermes-skill-run.sh planner-specialist now routes through hermes chat.

SCRIPT="$BATS_TEST_DIRNAME/../../scripts/hermes-skill-run.sh"

@test "planner-specialist routes through hermes chat after Phase 7" {
  run env -u MAX_TURNS bash "$SCRIPT" planner-specialist --dry-run "add hello.txt"
  [ "$status" -eq 0 ]
  [[ "$output" == *"hermes chat"* ]]
  [[ "$output" == *"--max-turns 8"* ]]
}

@test "planner-specialist dry-run shows specialist-home-orchestrator HERMES_HOME" {
  run env -u MAX_TURNS bash "$SCRIPT" planner-specialist --dry-run "add hello.txt"
  [ "$status" -eq 0 ]
  [[ "$output" == *"HERMES_HOME=/opt/ultra-workshop/specialist-home-orchestrator"* ]]
}
