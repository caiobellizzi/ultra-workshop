#!/usr/bin/env bats
# tests/phase-02/pre-deploy.bats — automated pre-deploy gate checks
# Run: bats tests/phase-02/pre-deploy.bats
# Requires: bats-core, ssh access to VPS as root

load helpers

@test "VPS swap is active (2G swapfile)" {
  result="$(ssh_cmd 'swapon --show')"
  [ -n "$result" ]
  echo "$result" | grep -q "file"
}

@test "uab-telegram.service is masked" {
  assert_service_masked "uab-telegram"
}

@test "Node.js v24 installed for uws user" {
  result="$(ssh_cmd 'su - uws -c "export NVM_DIR=\$HOME/.nvm && [ -s \"\$NVM_DIR/nvm.sh\" ] && . \"\$NVM_DIR/nvm.sh\" && node --version"')"
  echo "$result" | grep -q "^v24\."
}

@test "/etc/uws/env exists on VPS" {
  ssh_cmd "stat /etc/uws/env" > /dev/null
}

@test "/etc/uws/env has correct permissions (0640)" {
  perms="$(ssh_cmd "stat -c '%a' /etc/uws/env")"
  [ "$perms" = "640" ]
}

@test "LiteLLM config has private-worker timeout 30" {
  result="$(ssh_cmd "grep -v '^#' /opt/ultra-agents-brain/deploy/litellm/config.yaml | grep timeout")"
  echo "$result" | grep -q "30"
}
