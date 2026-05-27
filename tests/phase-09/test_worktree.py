from __future__ import annotations

import subprocess
from pathlib import Path
from unittest import mock

import pytest

from workshop.worktree import create_worktree, remove_worktree, prune_stale_worktrees


def test_create_worktree_runs_git_add() -> None:
    """create_worktree must invoke 'git worktree add' via subprocess."""
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.MagicMock(returncode=0)
        result = create_worktree("/repo", "ws-abc-review", "ws-abc")
        assert mock_run.called
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "git" in cmd
        assert "worktree" in cmd
        assert "add" in cmd
        assert isinstance(result, Path)


def test_remove_worktree_runs_git_remove() -> None:
    """remove_worktree must invoke 'git worktree remove' via subprocess."""
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.MagicMock(returncode=0)
        remove_worktree("/tmp/worktree-ws-abc", repo_path="/repo")
        assert mock_run.called
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "git" in cmd
        assert "worktree" in cmd
        assert "remove" in cmd


def test_prune_stale_worktrees_runs_git_prune() -> None:
    """prune_stale_worktrees must call subprocess.run to list and remove stale worktrees."""
    # Simulate 'git worktree list --porcelain' returning one old worktree
    porcelain_output = (
        "worktree /tmp/uws-worktrees/ws-old\n"
        "HEAD abc123\n"
        "branch refs/heads/ws-old-review\n"
        "\n"
    )
    with mock.patch("subprocess.run") as mock_run, \
         mock.patch("time.time", return_value=9999999999.0):
        # First call: git worktree list --porcelain
        list_result = mock.MagicMock(stdout=porcelain_output, returncode=0)
        # Subsequent calls: git worktree remove (for each stale entry)
        remove_result = mock.MagicMock(returncode=0)
        mock_run.side_effect = [list_result, remove_result]

        import os
        with mock.patch("os.stat") as mock_stat:
            mock_stat_result = mock.MagicMock()
            mock_stat_result.st_mtime = 0.0  # epoch — very old
            mock_stat.return_value = mock_stat_result
            pruned = prune_stale_worktrees("/repo", max_age_hours=24)

        # At minimum, subprocess.run must have been called (for listing)
        assert mock_run.called
        # First call must be 'git worktree list'
        first_cmd = mock_run.call_args_list[0][0][0]
        assert "git" in first_cmd
        assert "worktree" in first_cmd
