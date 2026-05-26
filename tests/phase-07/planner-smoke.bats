#!/usr/bin/env bats
# tests/phase-07/planner-smoke.bats
#
# Plan 07-01 Task 1: smoke tests for post-Phase-7 planner routing.
# hermes-skill-run.sh has NOT been updated yet (that is Plan 03).
# These tests are skipped until the hermes-skill-run.sh changes land.

SCRIPT="$BATS_TEST_DIRNAME/../../scripts/hermes-skill-run.sh"

@test "planner-specialist routes through hermes chat after Phase 7" {
  skip "TODO: update hermes-skill-run.sh first (Plan 03)"
  run env -u MAX_TURNS bash "$SCRIPT" planner-specialist --dry-run "add hello.txt"
  [ "$status" -eq 0 ]
  [[ "$output" == *"hermes chat"* ]]
}

@test "planner-specialist dry-run shows specialist-home-orchestrator HERMES_HOME" {
  skip "TODO: update hermes-skill-run.sh first (Plan 03)"
  run env -u MAX_TURNS bash "$SCRIPT" planner-specialist --dry-run "add hello.txt"
  [ "$status" -eq 0 ]
  [[ "$output" == *"HERMES_HOME=/opt/ultra-workshop/specialist-home-orchestrator"* ]]
}
