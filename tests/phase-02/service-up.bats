#!/usr/bin/env bats
# tests/phase-02/service-up.bats
# Verifies uws-hermes.service is active and correctly configured on the VPS.
# Run from repo root: bats tests/phase-02/service-up.bats
# Requires: SSH access to root@31.97.130.253

VPS="root@31.97.130.253"

@test "uws-hermes.service is active on VPS" {
  run ssh "$VPS" "systemctl is-active uws-hermes"
  [ "$status" -eq 0 ]
  [ "$output" = "active" ]
}

@test "unit file After= ordering includes uab-brain.service" {
  run ssh "$VPS" "grep -q 'uab-brain.service' /etc/systemd/system/uws-hermes.service"
  [ "$status" -eq 0 ]
}

@test "hermes binary is callable as uws user" {
  run ssh "$VPS" "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/hermes --version"
  [ "$status" -eq 0 ]
}

@test "config.yaml is accessible at deploy path or via symlink" {
  run ssh "$VPS" "test -f /opt/ultra-workshop/hermes-config/config.yaml"
  [ "$status" -eq 0 ]
}

@test "config.yaml contains no secrets (no bot tokens, API keys)" {
  run ssh "$VPS" "grep -qiE '(^|[[:space:]])(bot[0-9]+:|sk-|ghp_|password\s*=|token\s*=)' /opt/ultra-workshop/hermes-config/config.yaml"
  # grep should find NO matches — exit code 1 means no secrets found
  [ "$status" -eq 1 ]
}
