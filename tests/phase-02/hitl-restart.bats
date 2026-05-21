#!/usr/bin/env bats
# tests/phase-02/hitl-restart.bats
# Scripted HITL restart-resilience smoke test — V14 scenario (REQ-ws-014)
#
# Verifies that:
#   1. A pending_hitl.db row written before restart persists after restart
#   2. uws-hermes restarts cleanly (systemctl is-active → active)
#   3. Journal shows startup-hitl-scan re-emitting the HITL keyboard
#   4. The DB row still has status='pending' (awaiting human tap)
#   5. DB permissions: 0600, owned by uws
#
# The human approval step (tapping [Approve] in Telegram) is NOT automated —
# it is covered by the checkpoint in Task 3 of plan 02-05.
#
# Run from repo root:
#   bats tests/phase-02/hitl-restart.bats
# Requires: SSH access to root@31.97.130.253, sqlite3 on VPS, bats >= 1.0

load helpers

VPS_DB="/home/uws/.ultra-workshop/pending_hitl.db"
SMOKE_SESSION="smoke-test-v14-$(date +%s)"

setup() {
  # Seed a synthetic pending HITL row directly on VPS
  ssh_cmd "sqlite3 '$VPS_DB' \
    \"INSERT INTO pending_hitl (session_id, task_description, status, telegram_chat_id) \
      VALUES ('${SMOKE_SESSION}', 'bats V14 synthetic HITL test', 'pending', '7113965359');\""
}

teardown() {
  # Remove the seeded row regardless of test outcome
  ssh_cmd "sqlite3 '$VPS_DB' \
    \"DELETE FROM pending_hitl WHERE session_id='${SMOKE_SESSION}';\""
}

@test "1: seed row is written to pending_hitl.db before restart" {
  run ssh_cmd "sqlite3 '$VPS_DB' \
    \"SELECT count(*) FROM pending_hitl WHERE session_id='${SMOKE_SESSION}' AND status='pending';\""
  [ "$status" -eq 0 ]
  [ "$output" = "1" ]
}

@test "2: uws-hermes restarts cleanly (active after 25s cold-start)" {
  ssh_cmd "systemctl restart uws-hermes"
  sleep 25
  run ssh_cmd "systemctl is-active uws-hermes"
  [ "$status" -eq 0 ]
  [ "$output" = "active" ]
}

@test "3: journal shows startup-hitl-scan re-emitting HITL after restart" {
  # Allow up to 10 extra seconds for the hook's asyncio.sleep(5) + processing
  sleep 10
  run ssh_cmd "journalctl -u uws-hermes -n 100 --no-pager \
    | grep 'startup-hitl-scan.*re-emitting'"
  [ "$status" -eq 0 ]
}

@test "4: pending_hitl.db row still has status=pending (awaiting human approval)" {
  run ssh_cmd "sqlite3 '$VPS_DB' \
    \"SELECT count(*) FROM pending_hitl \
      WHERE session_id='${SMOKE_SESSION}' AND status='pending';\""
  [ "$status" -eq 0 ]
  [ "$output" = "1" ]
}

@test "5: pending_hitl.db permissions are 0600 owned by uws" {
  run ssh_cmd "stat -c '%a %U' '$VPS_DB'"
  [ "$status" -eq 0 ]
  [ "$output" = "600 uws" ]
}
