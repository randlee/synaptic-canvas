"""Tests for git operation error handling.

These tests verify that git operations handle errors gracefully
and return appropriate values for edge cases.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from worktree_shared import (
    check_branch_exists_local,
    check_branch_exists_remote,
    check_remote_branch_exists,
    count_unique_commits,
    create_tracking_branch,
    delete_local_branch,
    delete_remote_branch,
    get_all_remote_branches,
    get_branch_creator_info,
    get_protected_branches,
    get_remote_ahead_count,
    is_branch_merged,
    resolve_merge_base,
    run_git,
)


class TestRunGit:
    """Tests for the run_git helper function."""

    @patch('subprocess.run')
    def test_run_git_success(self, mock_run):
        """Test successful git command execution."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="output\n",
            stderr=""
        )

        result = run_git(["status"])

        assert result.returncode == 0
        assert result.stdout == "output\n"

    @patch('subprocess.run')
    def test_run_git_with_cwd(self, mock_run):
        """Test git command with custom working directory."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        run_git(["status"], cwd=Path("/custom/path"))

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cwd"] == Path("/custom/path")

    @patch('subprocess.run')
    def test_run_git_failure_no_check(self, mock_run):
        """Test git command failure with check=False."""
        mock_run.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository"
        )

        result = run_git(["status"], check=False)

        assert result.returncode == 128


class TestGetProtectedBranches:
    """Tests for protected branch detection."""

    @patch('worktree_shared.get_repo_root')
    @patch('worktree_shared.run_git')
    def test_gitflow_configured(self, mock_run_git, mock_repo_root, tmp_path):
        """Test protected branches from gitflow config."""
        mock_repo_root.return_value = tmp_path
        def config_side_effect(args, cwd=None, check=True):
            if "gitflow.branch.master" in args:
                return MagicMock(returncode=0, stdout="main\n")
            elif "gitflow.branch.develop" in args:
                return MagicMock(returncode=0, stdout="develop\n")
            return MagicMock(returncode=1, stdout="")

        mock_run_git.side_effect = config_side_effect

        protected = get_protected_branches(cwd=tmp_path)

        assert "main" in protected
        assert "develop" in protected

    @patch('worktree_shared.get_repo_root')
    @patch('worktree_shared.run_git')
    def test_gitflow_not_configured(self, mock_run_git, mock_repo_root, tmp_path):
        """Test fallback when gitflow not configured."""
        mock_repo_root.return_value = tmp_path
        mock_run_git.return_value = MagicMock(returncode=1, stdout="")

        with pytest.raises(ValueError):
            get_protected_branches(cwd=tmp_path)

    @patch('worktree_shared.get_repo_root')
    @patch('worktree_shared.run_git')
    def test_gitflow_empty_response(self, mock_run_git, mock_repo_root, tmp_path):
        """Test handling of empty gitflow config values."""
        mock_repo_root.return_value = tmp_path
        mock_run_git.return_value = MagicMock(returncode=0, stdout="\n")

        with pytest.raises(ValueError):
            get_protected_branches(cwd=tmp_path)


class TestGetRemoteAheadCount:
    """Tests for remote ahead detection."""

    @patch('worktree_shared.run_git')
    def test_remote_ahead_positive(self, mock_run_git):
        """Test when remote has commits we don't have."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="5\n")

        count = get_remote_ahead_count("feature/test")

        assert count == 5

    @patch('worktree_shared.run_git')
    def test_remote_ahead_zero(self, mock_run_git):
        """Test when we're up to date with remote."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="0\n")

        count = get_remote_ahead_count("feature/test")

        assert count == 0

    @patch('worktree_shared.run_git')
    def test_remote_not_found(self, mock_run_git):
        """Test when remote branch doesn't exist."""
        mock_run_git.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr="fatal: bad revision 'feature/nonexistent..origin/feature/nonexistent'"
        )

        count = get_remote_ahead_count("feature/nonexistent")

        assert count == -1

    @patch('worktree_shared.run_git')
    def test_network_error(self, mock_run_git):
        """Test handling of network errors."""
        mock_run_git.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="fatal: unable to access remote"
        )

        count = get_remote_ahead_count("feature/test")

        assert count == -1

    @patch('worktree_shared.run_git')
    def test_non_numeric_output(self, mock_run_git):
        """Test handling of unexpected output."""
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout="not a number\n"
        )

        count = get_remote_ahead_count("feature/test")

        # Should handle gracefully
        assert count == -1


class TestIsBranchMerged:
    """Tests for merged branch detection."""

    @patch('worktree_shared.run_git')
    def test_branch_is_merged(self, mock_run_git):
        """Test detection of merged branch."""
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout="  feature/merged\n  other-branch\n"
        )

        result = is_branch_merged("feature/merged")

        assert result == True

    @patch('worktree_shared.run_git')
    def test_branch_not_merged(self, mock_run_git):
        """Test detection of unmerged branch."""
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout="  other-branch\n  another-branch\n"
        )

        result = is_branch_merged("feature/unmerged")

        assert result == False

    @patch('worktree_shared.run_git')
    def test_current_branch_marker(self, mock_run_git):
        """Test handling of * marker for current branch."""
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout="* feature/current\n  other-branch\n"
        )

        result = is_branch_merged("feature/current")

        assert result == True

    @patch('worktree_shared.run_git')
    def test_git_error(self, mock_run_git):
        """Test handling of git errors."""
        mock_run_git.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error: malformed object name"
        )

        result = is_branch_merged("bad-branch")

        assert result == False


class TestDeleteRemoteBranch:
    """Tests for remote branch deletion."""

    @patch('worktree_shared.run_git')
    def test_delete_success(self, mock_run_git):
        """Test successful remote branch deletion."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

        success, message = delete_remote_branch("feature/test")

        assert success == True
        assert message == "deleted"

    @patch('worktree_shared.run_git')
    def test_already_deleted(self, mock_run_git):
        """Test deleting already-gone remote branch."""
        mock_run_git.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error: remote ref does not exist"
        )

        success, message = delete_remote_branch("feature/gone")

        assert success == True
        assert "already absent" in message

    @patch('worktree_shared.run_git')
    def test_permission_denied(self, mock_run_git):
        """Test handling of permission errors."""
        mock_run_git.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="remote: Permission denied to delete"
        )

        success, message = delete_remote_branch("feature/protected")

        assert success == False
        assert "Permission denied" in message or "Error" in message

    @patch('worktree_shared.run_git')
    def test_network_error(self, mock_run_git):
        """Test handling of network errors."""
        mock_run_git.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="fatal: unable to connect to remote"
        )

        success, message = delete_remote_branch("feature/test")

        assert success == False


class TestDeleteLocalBranch:
    """Tests for local branch deletion."""

    @patch('worktree_shared.run_git')
    def test_delete_merged_branch(self, mock_run_git):
        """Test deleting a merged branch with -d."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

        success = delete_local_branch("feature/merged", force=False)

        assert success == True
        call_args = mock_run_git.call_args[0][0]
        assert "-d" in call_args

    @patch('worktree_shared.run_git')
    def test_force_delete_branch(self, mock_run_git):
        """Test force deleting an unmerged branch with -D."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

        success = delete_local_branch("feature/unmerged", force=True)

        assert success == True
        call_args = mock_run_git.call_args[0][0]
        assert "-D" in call_args

    @patch('worktree_shared.run_git')
    def test_branch_not_merged_error(self, mock_run_git):
        """Test error when trying to delete unmerged branch without force."""
        mock_run_git.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error: The branch 'feature/test' is not fully merged"
        )

        success = delete_local_branch("feature/test", force=False)

        assert success == False


class TestCheckRemoteBranchExists:
    """Tests for remote branch existence check."""

    @patch('worktree_shared.run_git')
    def test_branch_exists(self, mock_run_git):
        """Test when remote branch exists."""
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout="refs/remotes/origin/feature/test\n"
        )

        exists = check_remote_branch_exists("feature/test")

        assert exists == True

    @patch('worktree_shared.run_git')
    def test_branch_not_exists(self, mock_run_git):
        """Test when remote branch doesn't exist."""
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout=""
        )

        exists = check_remote_branch_exists("feature/nonexistent")

        assert exists == False

    @patch('worktree_shared.run_git')
    def test_git_error(self, mock_run_git):
        """Test handling of git errors."""
        mock_run_git.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error"
        )

        exists = check_remote_branch_exists("feature/test")

        assert exists == False


class TestGetBranchCreatorInfo:
    """Tests for branch creator detection."""

    @patch('worktree_shared.run_git')
    def test_creator_found(self, mock_run_git):
        """Test successful creator detection."""
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout="John Doe|john@example.com|2024-01-15T10:30:00Z\n"
        )

        info = get_branch_creator_info("feature/test")

        assert info["author"] == "John Doe"
        assert info["email"] == "john@example.com"
        assert info["date"] == "2024-01-15T10:30:00Z"

    @patch('worktree_shared.run_git')
    def test_no_unique_commits(self, mock_run_git):
        """Test when branch has no unique commits."""
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout=""
        )

        info = get_branch_creator_info("feature/no-commits")

        assert info == {}

    @patch('worktree_shared.run_git')
    def test_branch_not_found(self, mock_run_git):
        """Test when branch doesn't exist."""
        mock_run_git.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr="fatal: bad revision"
        )

        info = get_branch_creator_info("feature/nonexistent")

        assert info == {}

    @patch('worktree_shared.run_git')
    def test_malformed_output(self, mock_run_git):
        """Test handling of malformed git output."""
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout="incomplete data"
        )

        info = get_branch_creator_info("feature/test")

        assert info == {}


class TestGetAllRemoteBranches:
    """Tests for listing all remote branches."""

    @patch('worktree_shared.run_git')
    def test_multiple_branches(self, mock_run_git):
        """Test listing multiple remote branches."""
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout="origin/main\norigin/develop\norigin/feature/test\n"
        )

        branches = get_all_remote_branches()

        assert "main" in branches
        assert "develop" in branches
        assert "feature/test" in branches

    @patch('worktree_shared.run_git')
    def test_no_branches(self, mock_run_git):
        """Test empty branch list."""
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout=""
        )

        branches = get_all_remote_branches()

        assert branches == []

    @patch('worktree_shared.run_git')
    def test_head_reference_filtered(self, mock_run_git):
        """Test that HEAD reference is filtered out."""
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout="origin/HEAD -> origin/main\norigin/main\norigin/feature/test\n"
        )

        branches = get_all_remote_branches()

        assert "HEAD" not in branches
        assert "HEAD -> origin/main" not in branches

    @patch('worktree_shared.run_git')
    def test_git_error(self, mock_run_git):
        """Test handling of git errors."""
        mock_run_git.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="fatal: not a git repository"
        )

        branches = get_all_remote_branches()

        assert branches == []


class TestCountUniqueCommits:
    """Tests for unique commit counting."""

    @patch('worktree_shared.run_git')
    def test_has_unique_commits(self, mock_run_git):
        """Test branch with unique commits."""
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout="5\n"
        )

        count = count_unique_commits("feature/test", "main")

        assert count == 5

    @patch('worktree_shared.run_git')
    def test_no_unique_commits(self, mock_run_git):
        """Test branch with no unique commits (fully merged)."""
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout="0\n"
        )

        count = count_unique_commits("feature/merged", "main")

        assert count == 0

    @patch('worktree_shared.run_git')
    def test_branch_not_found(self, mock_run_git):
        """Test when branch doesn't exist."""
        mock_run_git.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr="fatal: bad revision"
        )

        count = count_unique_commits("feature/nonexistent", "main")

        assert count == -1  # Returns -1 on git error

    @patch('worktree_shared.run_git')
    def test_non_numeric_output(self, mock_run_git):
        """Test handling of non-numeric output."""
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout="not a number\n"
        )

        count = count_unique_commits("feature/test", "main")

        assert count == -1  # Returns -1 on parse error


class TestResolveMergeBase:
    """Tests for resolve_merge_base helper."""

    @patch('worktree_shared.get_protected_branches')
    @patch('worktree_shared.run_git')
    def test_local_main_exists(self, mock_run_git, mock_get_protected):
        """Test resolving to local main branch."""
        mock_get_protected.return_value = ["main"]
        def side_effect(args, cwd=None, check=True):
            if args == ["branch", "--list", "main"]:
                return MagicMock(returncode=0, stdout="  main\n")
            return MagicMock(returncode=1, stdout="")

        mock_run_git.side_effect = side_effect

        base = resolve_merge_base()

        assert base == "main"

    @patch('worktree_shared.get_protected_branches')
    @patch('worktree_shared.run_git')
    def test_remote_main_fallback(self, mock_run_git, mock_get_protected):
        """Test falling back to remote main when local doesn't exist."""
        mock_get_protected.return_value = ["main"]
        def side_effect(args, cwd=None, check=True):
            if args == ["branch", "--list", "main"]:
                return MagicMock(returncode=0, stdout="")
            if args == ["branch", "-r", "--list", "origin/main"]:
                return MagicMock(returncode=0, stdout="  origin/main\n")
            return MagicMock(returncode=1, stdout="")

        mock_run_git.side_effect = side_effect

        base = resolve_merge_base()

        assert base == "origin/main"

    @patch('worktree_shared.get_protected_branches')
    @patch('worktree_shared.run_git')
    def test_no_protected_branch_found(self, mock_run_git, mock_get_protected):
        """Test when no protected branch exists."""
        mock_get_protected.return_value = ["main"]
        mock_run_git.return_value = MagicMock(returncode=0, stdout="")

        base = resolve_merge_base()

        assert base is None

    @patch('worktree_shared.get_protected_branches')
    @patch('worktree_shared.run_git')
    def test_develop_fallback(self, mock_run_git, mock_get_protected):
        """Test falling back to develop when main/master don't exist."""
        mock_get_protected.return_value = ["main", "master", "develop"]
        def side_effect(args, cwd=None, check=True):
            if args == ["branch", "--list", "develop"]:
                return MagicMock(returncode=0, stdout="  develop\n")
            if "develop" not in str(args):
                return MagicMock(returncode=0, stdout="")
            return MagicMock(returncode=1, stdout="")

        mock_run_git.side_effect = side_effect

        base = resolve_merge_base()

        assert base == "develop"


class TestCheckBranchExists:
    """Tests for branch existence helpers."""

    @patch('worktree_shared.run_git')
    def test_local_branch_exists(self, mock_run_git):
        """Test detecting existing local branch."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="  feature/test\n")

        exists = check_branch_exists_local("feature/test")

        assert exists == True

    @patch('worktree_shared.run_git')
    def test_local_branch_not_exists(self, mock_run_git):
        """Test detecting non-existent local branch."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="")

        exists = check_branch_exists_local("feature/nonexistent")

        assert exists == False

    @patch('worktree_shared.run_git')
    def test_remote_branch_exists(self, mock_run_git):
        """Test detecting existing remote branch."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="  origin/feature/test\n")

        exists = check_branch_exists_remote("feature/test")

        assert exists == True

    @patch('worktree_shared.run_git')
    def test_remote_branch_not_exists(self, mock_run_git):
        """Test detecting non-existent remote branch."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="")

        exists = check_branch_exists_remote("feature/nonexistent")

        assert exists == False


class TestCreateTrackingBranch:
    """Tests for creating tracking branches."""

    @patch('worktree_shared.run_git')
    def test_create_tracking_branch_success(self, mock_run_git):
        """Test successful tracking branch creation."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

        success = create_tracking_branch("feature/test")

        assert success == True
        call_args = mock_run_git.call_args[0][0]
        assert "branch" in call_args
        assert "--track" in call_args
        assert "feature/test" in call_args
        assert "origin/feature/test" in call_args

    @patch('worktree_shared.run_git')
    def test_create_tracking_branch_failure(self, mock_run_git):
        """Test tracking branch creation failure."""
        mock_run_git.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="fatal: not a valid ref"
        )

        success = create_tracking_branch("feature/nonexistent")

        assert success == False
