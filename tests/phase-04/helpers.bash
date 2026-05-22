#!/usr/bin/env bash
# tests/phase-04/helpers.bash — Phase 4 shared SSH helpers for bats test suite

VPS_HOST="31.97.130.253"
VPS_USER="root"
VPS_SSH="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10"

ssh_cmd() {
  $VPS_SSH ${VPS_USER}@${VPS_HOST} "$@"
}

assert_service_active() {
  local svc="$1"
  ssh_cmd "systemctl is-active $svc" | grep -q "^active$"
}
