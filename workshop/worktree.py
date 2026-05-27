from __future__ import annotations

"""
Git worktree lifecycle management for ultra-workshop.

Used by the review-wave merge agent (B5) to create isolated worktrees
for the single file-editing agent in the wave, and pruned on task success
per D-20.
"""

import os
import shutil
import subprocess
import time
from pathlib import Path

WORKTREE_BASE = Path("/tmp/uws-worktrees")


def create_worktree(repo_path: str, branch_name: str, task_id: str) -> Path:
    """
    Create a git worktree for the given task.

    Runs: git -C {repo_path} worktree add {worktree_path} -b {branch_name}

    Args:
        repo_path: Absolute path to the repository root.
        branch_name: Name for the new branch in the worktree.
        task_id: Task identifier used to name the worktree directory.

    Returns:
        Path to the newly created worktree.

    Raises:
        subprocess.CalledProcessError: If the git command fails.
    """
    worktree_path = WORKTREE_BASE / task_id
    subprocess.run(
        ["git", "-C", repo_path, "worktree", "add", str(worktree_path), "-b", branch_name],
        check=True,
        capture_output=True,
        text=True,
    )
    return worktree_path


def remove_worktree(
    worktree_path: str | Path,
    repo_path: str | None = None,
    force: bool = False,
) -> None:
    """
    Remove a git worktree.

    Runs: git -C {repo_path} worktree remove [--force] {worktree_path}

    Falls back to shutil.rmtree if the git command fails (e.g., worktree
    already unlinked but directory still present).

    Args:
        worktree_path: Path to the worktree directory to remove.
        repo_path: Repository root for the git command. If None, uses the
                   parent of worktree_path.
        force: Pass --force to git worktree remove.
    """
    worktree_path = Path(worktree_path)
    if repo_path is None:
        repo_path = str(worktree_path.parent)

    cmd = ["git", "-C", repo_path, "worktree", "remove", str(worktree_path)]
    if force:
        cmd.insert(4, "--force")

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        # Fallback: forcibly remove the directory tree if git fails
        if worktree_path.exists():
            shutil.rmtree(str(worktree_path), ignore_errors=True)


def prune_stale_worktrees(repo_path: str, max_age_hours: int = 48) -> list[Path]:
    """
    Find and remove worktrees older than max_age_hours.

    Runs: git -C {repo_path} worktree list --porcelain
    Checks each worktree directory's mtime against max_age_hours.
    Calls remove_worktree on each stale entry.

    Per D-20: prune on task success; retain on failure. This function is
    called by the success path in workshop_build.py (09-03) and optionally
    by a scheduled sweep to handle orphaned failed worktrees after a
    configurable grace period.

    Args:
        repo_path: Absolute path to the repository root.
        max_age_hours: Worktrees older than this many hours are removed.

    Returns:
        List of worktree Paths that were pruned.
    """
    result = subprocess.run(
        ["git", "-C", repo_path, "worktree", "list", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    )

    worktrees = _parse_worktree_list(result.stdout)
    pruned: list[Path] = []
    now = time.time()
    max_age_seconds = max_age_hours * 3600

    for wt_path in worktrees:
        # Skip the main worktree (repo_path itself)
        if Path(wt_path).resolve() == Path(repo_path).resolve():
            continue
        try:
            stat = os.stat(wt_path)
            age_seconds = now - stat.st_mtime
            if age_seconds > max_age_seconds:
                remove_worktree(wt_path, repo_path=repo_path, force=True)
                pruned.append(Path(wt_path))
        except (FileNotFoundError, PermissionError):
            # Worktree directory already gone or inaccessible — skip
            continue

    return pruned


def _parse_worktree_list(porcelain_output: str) -> list[str]:
    """Parse 'git worktree list --porcelain' output into a list of worktree paths."""
    paths: list[str] = []
    for line in porcelain_output.splitlines():
        if line.startswith("worktree "):
            paths.append(line[len("worktree "):].strip())
    return paths
