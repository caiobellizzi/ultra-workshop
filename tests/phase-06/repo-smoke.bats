#!/usr/bin/env bats
# tests/phase-06/repo-smoke.bats — repo registry and repo-targeted dry-run smoke tests

load ../phase-04/helpers

skip_if_workshop_down() {
  run ssh_cmd "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 -c 'import workshop.repo_registry' 2>/dev/null; echo exit:\$?"
  if echo "$output" | grep -q "exit:1"; then
    skip "workshop repo registry module not importable on VPS"
  fi
}

@test "workshop-repo list dry path exits 0 and shows sandbox seed" {
  skip_if_workshop_down
  run ssh_cmd "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 /opt/ultra-workshop/hermes-skills/workshop_repo.py list 2>/dev/null"
  [ "$status" -eq 0 ]
  [[ "$output" == *"caiobellizzi/test-workshop-sandbox"* ]]
}

@test "workshop-build requires --repo and dry-run accepts repo target" {
  skip_if_workshop_down
  run ssh_cmd "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 /opt/ultra-workshop/hermes-skills/workshop_build.py --repo test-workshop-sandbox --task 'add hello endpoint' --dry-run 2>/dev/null"
  [ "$status" -eq 0 ]
  [[ "$output" == *"dry-run"* ]]
  [[ "$output" == *"test-workshop-sandbox"* ]]
}

@test "workshop-fix dry-run derives repo from issue URL" {
  skip_if_workshop_down
  run ssh_cmd "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 /opt/ultra-workshop/hermes-skills/workshop_fix.py --issue-url 'https://github.com/caiobellizzi/test-workshop-sandbox/issues/1' --dry-run 2>/dev/null"
  [ "$status" -eq 0 ]
  [[ "$output" == *"caiobellizzi/test-workshop-sandbox"* ]]
  [[ "$output" == *"issue: 1"* ]]
}

@test "workshop_coder.py dry-run includes selected repo metadata" {
  skip_if_workshop_down
  run ssh_cmd "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 /opt/ultra-workshop/hermes-skills/workshop_coder.py --query '{\"task_id\":\"smoke\",\"plan\":{\"goal\":\"noop\"},\"repo\":{\"full_name\":\"caiobellizzi/test-workshop-sandbox\",\"default_branch\":\"main\"},\"workspace_dir\":\"\"}' --dry-run 2>/dev/null"
  [ "$status" -eq 0 ]
  [[ "$output" == *'"repo_full_name"'* ]]
  [[ "$output" == *'"default_branch"'* ]]
}

@test "workshop_push.py exposes repo and base branch args" {
  skip_if_workshop_down
  run ssh_cmd "sudo -u uws /opt/ultra-workshop/hermes/venv/bin/python3 /opt/ultra-workshop/hermes-skills/workshop_push.py --help 2>/dev/null"
  [ "$status" -eq 0 ]
  [[ "$output" == *"--repo-full-name"* ]]
  [[ "$output" == *"--base"* ]]
}
