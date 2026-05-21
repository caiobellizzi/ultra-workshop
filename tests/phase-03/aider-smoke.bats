#!/usr/bin/env bats
# tests/phase-03/aider-smoke.bats — Aider skill smoke tests
#
# Test coverage:
#   - aider skill dry-run exits 0 (unconditional — no aider subprocess invoked)
#   - Brain curator endpoint reachable (OPTION B cost-ledger check)
#   - aider_runner.py invocation exits 0 when private-worker is available
#
# V5 STRICT precheck: private-worker availability is tested via LiteLLM /v1/models.
# If private-worker is unreachable, live tests are SKIPPED (not FAILED).
# This prevents false failures when LM Studio is not running on Mac.

load helpers

# ---------------------------------------------------------------------------
# Precheck: skip live tests if private-worker is unavailable.
# V5 strict — SKIP not FAIL if LM Studio not running.
# ---------------------------------------------------------------------------
skip_if_private_worker_down() {
  # LiteLLM requires auth — source /etc/uws/env to get LITELLM_API_KEY
  # V5 strict: checks both private-worker availability AND cloud-sonnet auth.
  # Both architect (cloud-sonnet) and editor (private-worker) must be functional
  # for the full aider invocation to succeed.
  run ssh_cmd "source /etc/uws/env && \
    curl -sf --connect-timeout 5 -H \"Authorization: Bearer \$LITELLM_API_KEY\" \
    http://127.0.0.1:4000/v1/models | \
    python3 -c \"import sys,json; ids=[m['id'] for m in json.load(sys.stdin)['data']]; sys.exit(0 if 'private-worker' in ids else 1)\""
  if [ "$status" -ne 0 ]; then
    skip "private-worker unavailable — ensure LM Studio is running on Mac with LM Link active"
  fi
}

skip_if_cloud_sonnet_auth_down() {
  # Skip if Anthropic API key is not configured in LiteLLM (cloud-sonnet fails auth).
  # Full aider runs require cloud-sonnet as architect; skip gracefully if unconfigured.
  run ssh_cmd "source /etc/uws/env && \
    curl -sf --connect-timeout 5 -X POST \
    -H \"Authorization: Bearer \$LITELLM_API_KEY\" \
    -H 'Content-Type: application/json' \
    -d '{\"model\":\"cloud-sonnet\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"max_tokens\":1}' \
    http://127.0.0.1:4000/v1/chat/completions | \
    python3 -c \"import sys,json; d=json.load(sys.stdin); sys.exit(0 if 'choices' in d else 1)\""
  if [ "$status" -ne 0 ]; then
    skip "cloud-sonnet unavailable — ANTHROPIC_API_KEY not configured in LiteLLM"
  fi
}

setup() {
  # Create minimal git repo for aider workspace on VPS
  ssh_cmd "mkdir -p /tmp/uws-aider-test && cd /tmp/uws-aider-test && git init && git commit --allow-empty -m 'init' 2>/dev/null || true"
}

teardown() {
  ssh_cmd "rm -rf /tmp/uws-aider-test"
}

@test "aider skill dry-run exits 0" {
  run ssh_cmd "bash /opt/ultra-workshop/scripts/hermes-skill-run.sh aider --dry-run --task 'echo test'"
  [ "$status" -eq 0 ]
}

# OPTION B cost-ledger: asserts curator endpoint is reachable and returns run_id.
# Does NOT assert 2 LLM-call entries were recorded. See skills/aider/SKILL.md BACKLOG note.
@test "Brain curator endpoint reachable (OPTION B cost-ledger check)" {
  skip_if_private_worker_down
  run ssh_cmd "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 /opt/ultra-workshop/hermes-skills/brain_http.py curator 'aider smoke test cost marker' 2>/dev/null"
  [ "$status" -eq 0 ]
  echo "$output" | python3 -c "import sys, json; d=json.load(sys.stdin); assert 'run_id' in d, 'curator run_id missing'"
}

@test "aider_runner.py exits 0 when private-worker and cloud-sonnet available" {
  skip_if_private_worker_down
  skip_if_cloud_sonnet_auth_down
  run ssh_cmd "source /etc/uws/env && export LITELLM_API_KEY && sudo -E -u uws env HOME=/home/uws /opt/ultra-workshop/hermes/venv/bin/python3 /opt/ultra-workshop/hermes-skills/aider_runner.py --task 'echo hello to /tmp/uws-aider-test/hello.txt'"
  # If both private-worker and cloud-sonnet are available: aider runs and returns diff or output; exit 0
  # The test asserts skill can be invoked without shell errors
  [ "$status" -eq 0 ]
}
