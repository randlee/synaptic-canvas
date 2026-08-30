"""Tests for gh-stack tracking interop.

CRITICAL: These tests verify that worktrees carrying gh-stack tracking state
(a per-worktree `gh-stack` marker under the worktree's git-dir) are not
silently touched by batch cleanup, and that scan/single-branch/abort
operations surface the tracked state so callers can require explicit
approval before acting on it.

1. `check_gh_stack_tracked()` correctly probes the worktree's git-dir
2. Batch cleanup skips gh-stack-tracked worktrees entirely (fail closed)
3. Batch cleanup is unaffected for worktrees without gh-stack tracking
4. Single-branch cleanup reports `gh_stack_tracked` but does not block on it
5. Scan reports `gh_stack_tracked` per worktree
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from worktree_shared import check_gh_stack_tracked
from worktree_cleanup import CleanupInput, cleanup_all_merged, cleanup_single_branch
from worktree_scan import scan_worktrees


# =============================================================================
# Real-git fixtures
# =============================================================================


def _run(args, cwd):
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )


def _init_repo(tmp_path: Path) -> Path:
    """Create a minimal real git repo with one commit on 'main'."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["init", "-b", "main"], cwd=repo)
    _run(["config", "user.email", "test@example.com"], cwd=repo)
    _run(["config", "user.name", "Test User"], cwd=repo)
    (repo / "README.md").write_text("init\n")
    _run(["add", "."], cwd=repo)
    _run(["commit", "-m", "init"], cwd=repo)
    return repo


def _add_worktree(repo: Path, wt_path: Path, branch: str) -> None:
    _run(["worktree", "add", "-b", branch, str(wt_path), "main"], cwd=repo)


def _mark_gh_stack(wt_path: Path) -> None:
    """Simulate gh-stack having written its per-worktree tracking marker."""
    result = _run(["rev-parse", "--git-dir"], cwd=wt_path)
    git_dir = Path(result.stdout.strip())
    if not git_dir.is_absolute():
        git_dir = (wt_path / git_dir).resolve()
    (git_dir / "gh-stack").touch()


# =============================================================================
# check_gh_stack_tracked()
# =============================================================================


class TestCheckGhStackTracked:
    """Unit tests for the gh-stack tracking probe."""

    @patch("worktree_shared.run_git")
    def test_marker_present_absolute_git_dir(self, mock_run_git, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "gh-stack").touch()
        mock_run_git.return_value = MagicMock(returncode=0, stdout=str(git_dir) + "\n")

        assert check_gh_stack_tracked(tmp_path) is True

    @patch("worktree_shared.run_git")
    def test_marker_absent(self, mock_run_git, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        mock_run_git.return_value = MagicMock(returncode=0, stdout=str(git_dir) + "\n")

        assert check_gh_stack_tracked(tmp_path) is False

    @patch("worktree_shared.run_git")
    def test_relative_git_dir_resolved_against_worktree(self, mock_run_git, tmp_path):
        # Linked worktrees report a relative --git-dir; it must be resolved
        # relative to the worktree path, not the process cwd.
        real_git_dir = tmp_path / ".git" / "worktrees" / "feature-x"
        real_git_dir.mkdir(parents=True)
        (real_git_dir / "gh-stack").touch()
        rel = ".git/worktrees/feature-x"
        mock_run_git.return_value = MagicMock(returncode=0, stdout=rel + "\n")

        assert check_gh_stack_tracked(tmp_path) is True

    @patch("worktree_shared.run_git")
    def test_git_error_fails_closed_to_false(self, mock_run_git, tmp_path):
        mock_run_git.return_value = MagicMock(returncode=128, stdout="")

        assert check_gh_stack_tracked(tmp_path) is False

    @patch("worktree_shared.run_git")
    def test_empty_git_dir_output_fails_closed_to_false(self, mock_run_git, tmp_path):
        mock_run_git.return_value = MagicMock(returncode=0, stdout="\n")

        assert check_gh_stack_tracked(tmp_path) is False


# =============================================================================
# Batch cleanup
# =============================================================================


class TestBatchCleanupGhStackGuard:
    """Batch cleanup must never touch a gh-stack-tracked worktree."""

    def test_gh_stack_tracked_worktree_is_skipped_not_removed(self, tmp_path):
        repo = _init_repo(tmp_path)
        wt_path = tmp_path / "wt-tracked"
        _add_worktree(repo, wt_path, "feature/tracked")
        _mark_gh_stack(wt_path)

        input_data = CleanupInput(
            repo_root=str(repo),
            protected_branches=["main"],
            cache_protected_branches=False,
            tracking_enabled=False,
        )
        envelope = cleanup_all_merged(input_data)

        assert envelope.success is True
        data = envelope.data
        skipped = data.get("gh_stack_skipped") or []
        assert any(e["branch"] == "feature/tracked" for e in skipped)
        skipped_entry = next(e for e in skipped if e["branch"] == "feature/tracked")
        assert skipped_entry["path"] == str(wt_path)
        assert "gh-stack tracking present" in skipped_entry["reason"]
        assert "single-branch cleanup" in skipped_entry["reason"]

        # Must not have been cleaned, and must not exist in cleaned list
        cleaned_branches = {e["branch"] for e in (data.get("cleaned") or [])}
        assert "feature/tracked" not in cleaned_branches

        # The worktree and branch must still exist on disk / in git
        assert wt_path.exists()
        branch_list = _run(["branch", "--list", "feature/tracked"], cwd=repo).stdout
        assert "feature/tracked" in branch_list

    def test_mixed_batch_only_skips_tracked_worktree(self, tmp_path):
        repo = _init_repo(tmp_path)

        tracked_path = tmp_path / "wt-tracked"
        _add_worktree(repo, tracked_path, "feature/tracked")
        _mark_gh_stack(tracked_path)

        plain_path = tmp_path / "wt-plain"
        _add_worktree(repo, plain_path, "feature/plain")

        input_data = CleanupInput(
            repo_root=str(repo),
            protected_branches=["main"],
            cache_protected_branches=False,
            tracking_enabled=False,
        )
        envelope = cleanup_all_merged(input_data)

        assert envelope.success is True
        data = envelope.data

        skipped_branches = {e["branch"] for e in (data.get("gh_stack_skipped") or [])}
        cleaned_branches = {e["branch"] for e in (data.get("cleaned") or [])}

        assert "feature/tracked" in skipped_branches
        assert "feature/plain" in cleaned_branches
        assert "feature/plain" not in skipped_branches
        assert "feature/tracked" not in cleaned_branches

        # Tracked worktree preserved; plain worktree actually removed
        assert tracked_path.exists()
        assert not plain_path.exists()

    def test_batch_cleanup_without_gh_stack_marker_behaves_as_before(self, tmp_path):
        """Regression: no gh-stack tracking anywhere -> normal clean+merged auto-cleanup."""
        repo = _init_repo(tmp_path)
        wt_path = tmp_path / "wt-plain"
        _add_worktree(repo, wt_path, "feature/plain")

        input_data = CleanupInput(
            repo_root=str(repo),
            protected_branches=["main"],
            cache_protected_branches=False,
            tracking_enabled=False,
        )
        envelope = cleanup_all_merged(input_data)

        assert envelope.success is True
        data = envelope.data
        assert data.get("gh_stack_skipped") is None
        cleaned_branches = {e["branch"] for e in (data.get("cleaned") or [])}
        assert "feature/plain" in cleaned_branches
        assert not wt_path.exists()
        assert data["summary"]["gh_stack_skipped"] == 0


# =============================================================================
# Single-branch cleanup
# =============================================================================


class TestSingleBranchCleanupReportsGhStackTracked:
    """Single-branch cleanup surfaces gh_stack_tracked but does not block."""

    def test_tracked_worktree_reports_true_and_still_cleans(self, tmp_path):
        repo = _init_repo(tmp_path)
        wt_path = tmp_path / "wt-tracked"
        _add_worktree(repo, wt_path, "feature/tracked")
        _mark_gh_stack(wt_path)

        input_data = CleanupInput(
            branch="feature/tracked",
            path=str(wt_path),
            repo_root=str(repo),
            protected_branches=["main"],
            cache_protected_branches=False,
            tracking_enabled=False,
            merged=True,
        )
        envelope = cleanup_single_branch(input_data)

        assert envelope.success is True
        assert envelope.data["gh_stack_tracked"] is True
        # Not a hard block: cleanup proceeds normally.
        assert envelope.data["worktree_removed"] is True
        assert not wt_path.exists()

    def test_untracked_worktree_reports_false(self, tmp_path):
        repo = _init_repo(tmp_path)
        wt_path = tmp_path / "wt-plain"
        _add_worktree(repo, wt_path, "feature/plain")

        input_data = CleanupInput(
            branch="feature/plain",
            path=str(wt_path),
            repo_root=str(repo),
            protected_branches=["main"],
            cache_protected_branches=False,
            tracking_enabled=False,
            merged=True,
        )
        envelope = cleanup_single_branch(input_data)

        assert envelope.success is True
        assert envelope.data["gh_stack_tracked"] is False
        assert envelope.data["worktree_removed"] is True


# =============================================================================
# Scan
# =============================================================================


class TestScanReportsGhStackTracked:
    """Scan reports gh_stack_tracked per worktree."""

    def test_scan_flags_tracked_and_untracked_worktrees(self, tmp_path, monkeypatch):
        repo = _init_repo(tmp_path)

        tracked_path = tmp_path / "wt-tracked"
        _add_worktree(repo, tracked_path, "feature/tracked")
        _mark_gh_stack(tracked_path)

        plain_path = tmp_path / "wt-plain"
        _add_worktree(repo, plain_path, "feature/plain")

        monkeypatch.chdir(repo)
        envelope = scan_worktrees(tracking_enabled=False, cache_protected_branches=False)

        assert envelope.success is True
        by_branch = {wt["branch"]: wt for wt in envelope.data["worktrees"]}

        assert by_branch["feature/tracked"]["gh_stack_tracked"] is True
        assert by_branch["feature/plain"]["gh_stack_tracked"] is False


class TestCheckGhStackTrackedMissingDirectory:
    """Non-mocked coverage for the OSError path: subprocess raises before git
    runs when the worktree directory itself is gone (prunable worktrees) —
    the fail-closed contract must swallow it, not crash the scan."""

    def test_nonexistent_directory_fails_closed(self):
        assert check_gh_stack_tracked(Path("/nonexistent/path/sc-gwt-xyz")) is False
