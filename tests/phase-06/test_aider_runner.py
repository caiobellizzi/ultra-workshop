from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from hermes_skills_import import load_module


aider_runner = load_module("aider_runner", "hermes-skills/aider_runner.py")


def test_build_aider_argv_uses_single_model_flag(tmp_path: Path) -> None:
    argv = aider_runner._build_aider_argv(
        aider_bin="aider",
        task="add hello",
        target_files=["hello.py"],
        litellm_api_key="test-key",
        history_dir=tmp_path,
    )

    # Single --model flag with default alias
    assert "--model" in argv
    model_idx = argv.index("--model")
    assert argv[model_idx + 1] == "openai/coder-worker"

    # No architect/editor-model/no-stream flags
    assert "--architect" not in argv
    assert "--editor-model" not in argv
    assert "--no-stream" not in argv


def test_build_aider_argv_uses_batch_terminal_flags(tmp_path: Path) -> None:
    argv = aider_runner._build_aider_argv(
        aider_bin="aider",
        task="add hello",
        target_files=["hello.py"],
        litellm_api_key="test-key",
        history_dir=tmp_path,
    )

    assert "--no-fancy-input" in argv
    assert "--no-pretty" in argv
    assert "--no-detect-urls" in argv
    assert "--no-check-update" in argv
    assert "--no-gitignore" in argv
    assert "--input-history-file" in argv
    assert "--chat-history-file" in argv
    assert "--llm-history-file" in argv
    assert argv[-1] == "hello.py"


def test_build_aider_argv_forwards_model_alias(tmp_path: Path) -> None:
    argv = aider_runner._build_aider_argv(
        aider_bin="aider",
        task="plan a feature",
        target_files=["plan.py"],
        litellm_api_key="test-key",
        history_dir=tmp_path,
        model_alias="planner-reasoner",
    )

    assert "--model" in argv
    model_idx = argv.index("--model")
    assert argv[model_idx + 1] == "openai/planner-reasoner"

    # Still no architect/editor-model/no-stream
    assert "--architect" not in argv
    assert "--editor-model" not in argv
    assert "--no-stream" not in argv


def test_resolve_workspace_uses_target_git_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    target = repo / "pkg" / "feature.py"
    target.parent.mkdir()
    target.write_text("", encoding="utf-8")

    workspace_dir, target_files = aider_runner._resolve_workspace([str(target)])

    assert workspace_dir == repo
    assert target_files == ["pkg/feature.py"]


def test_verify_workspace_runs_make_test(tmp_path: Path) -> None:
    (tmp_path / "Makefile").write_text(
        f"test:\n\t{sys.executable} -c \"print('verify-ok')\"\n",
        encoding="utf-8",
    )

    result = aider_runner.verify_workspace(tmp_path)

    assert result["build_passed"] is True
    assert result["test_passed"] is True
    assert "verify-ok" in result["output_tail"]
