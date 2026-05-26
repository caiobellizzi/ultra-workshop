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

@test "aider_runner argv has single --model, no --architect, no --no-stream" {
  RUNNER="$BATS_TEST_DIRNAME/../../hermes-skills/aider_runner.py"
  # Use python3 to call _build_aider_argv and check the argv flags
  run python3 -c "
import sys, pathlib
sys.path.insert(0, str(pathlib.Path('$RUNNER').parent.parent))
sys.path.insert(0, str(pathlib.Path('$RUNNER').parent))
import importlib.util, pathlib, tempfile
spec = importlib.util.spec_from_file_location('aider_runner', '$RUNNER')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as d:
    argv = m._build_aider_argv(aider_bin='aider', task='test', target_files=['f.py'], litellm_api_key='key', history_dir=pathlib.Path(d))
    assert '--model' in argv, f'--model missing from {argv}'
    model_idx = argv.index('--model')
    assert argv[model_idx+1] == 'openai/coder-worker', f'expected openai/coder-worker got {argv[model_idx+1]}'
    assert '--architect' not in argv, '--architect must not be in argv'
    assert '--no-stream' not in argv, '--no-stream must not be in argv'
    assert '--editor-model' not in argv, '--editor-model must not be in argv'
    print('ok')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"ok"* ]]
}

@test "aider_runner model_alias parameter is forwarded to --model flag" {
  RUNNER="$BATS_TEST_DIRNAME/../../hermes-skills/aider_runner.py"
  run python3 -c "
import sys, pathlib
sys.path.insert(0, str(pathlib.Path('$RUNNER').parent.parent))
sys.path.insert(0, str(pathlib.Path('$RUNNER').parent))
import importlib.util, pathlib, tempfile
spec = importlib.util.spec_from_file_location('aider_runner', '$RUNNER')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as d:
    argv = m._build_aider_argv(aider_bin='aider', task='plan', target_files=['p.py'], litellm_api_key='key', history_dir=pathlib.Path(d), model_alias='planner-reasoner')
    model_idx = argv.index('--model')
    assert argv[model_idx+1] == 'openai/planner-reasoner', f'expected openai/planner-reasoner got {argv[model_idx+1]}'
    print('ok')
"
  [ "$status" -eq 0 ]
  [[ "$output" == *"ok"* ]]
}
