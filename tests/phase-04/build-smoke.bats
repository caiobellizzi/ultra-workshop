#!/usr/bin/env bats
# tests/phase-04/build-smoke.bats — workshop-build dry-run + importability smoke tests

load helpers

skip_if_workshop_down() {
  run ssh_cmd "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 -c 'import workshop.types' 2>/dev/null; echo exit:\$?"
  if echo "$output" | grep -q "exit:1"; then
    skip "workshop package not importable on VPS"
  fi
}

@test "workshop-build dry-run exits 0" {
  run ssh_cmd "bash /opt/ultra-workshop/scripts/hermes-skill-run.sh workshop-build --dry-run --task 'add hello endpoint'"
  [ "$status" -eq 0 ]
}

@test "workshop types are importable from Hermes venv" {
  skip_if_workshop_down
  run ssh_cmd "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 -c 'from workshop.types import Plan, Diff, Review; from workshop.orchestrator import run_specialist; print(\"ok\")'"
  [ "$status" -eq 0 ]
  [[ "$output" == *"ok"* ]]
}

@test "workshop_build.py --dry-run exits 0" {
  skip_if_workshop_down
  run ssh_cmd "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 /opt/ultra-workshop/hermes-skills/workshop_build.py --task 'add hello endpoint' --dry-run 2>/dev/null"
  [ "$status" -eq 0 ]
  [[ "$output" == *"dry-run"* ]]
}
