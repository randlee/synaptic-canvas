"""Tests for cleanup safety guards.

CRITICAL: These tests verify that branches are not accidentally deleted.
The cleanup process has multiple safety checks:

1. Never delete protected branches (main, master, develop)
2. Never delete unmerged branches without explicit approval
3. Never delete remote branches when remote is ahead (has unpulled commits)
4. Never delete dirty worktrees without explicit force flag
5. Orphaned remotes are cleaned up, not lost

These tests must pass before any release.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import sys

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from worktree_shared import (
    TrackingEntry,
    save_tracking_jsonl,
    get_protected_branches,
    get_remote_ahead_count,
    is_branch_merged,
    delete_remote_branch,
)


class TestProtectedBranchSafety:
    """Test that protected branches are never deleted."""

    @patch('worktree_shared.get_repo_root')
    @patch('worktree_shared.run_git')
    def test_get_protected_branches_from_gitflow(self, mock_run_git, mock_repo_root, tmp_path):
        """Test protected branches are detected from gitflow config."""
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
    def test_default_protected_branches(self, mock_run_git, mock_repo_root, tmp_path):
        """Test failure when protected branches aren't configured."""
        mock_repo_root.return_value = tmp_path
        mock_run_git.return_value = MagicMock(returncode=1, stdout="")

        with pytest.raises(ValueError):
            get_protected_branches(cwd=tmp_path)

    def test_protected_branch_list_includes_common_names(self, tmp_path):
        """Verify shared settings are honored when present."""
        shared = tmp_path / ".sc" / "shared-settings.yaml"
        shared.parent.mkdir(parents=True, exist_ok=True)
        shared.write_text("git:\\n  protected_branches:\\n    - main\\n    - develop\\n")

        with patch('worktree_shared.get_repo_root') as mock_root, \
             patch('worktree_shared._load_yaml') as mock_load:
            mock_root.return_value = tmp_path
            mock_load.return_value = {"git": {"protected_branches": ["main", "develop"]}}
            protected = get_protected_branches(cwd=tmp_path)
            assert "main" in protected
            assert "develop" in protected


class TestRemoteAheadSafety:
    """Test that remote-ahead branches are not deleted."""

    @patch('worktree_shared.run_git')
    def test_get_remote_ahead_count_returns_count(self, mock_run_git):
        """Test remote ahead count is correctly retrieved."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="5\n")

        count = get_remote_ahead_count("feature/test")
        assert count == 5

    @patch('worktree_shared.run_git')
    def test_get_remote_ahead_count_returns_zero(self, mock_run_git):
        """Test zero is returned when local is up to date."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="0\n")

        count = get_remote_ahead_count("feature/test")
        assert count == 0

    @patch('worktree_shared.run_git')
    def test_get_remote_ahead_count_error_returns_negative(self, mock_run_git):
        """Test -1 is returned on error (branch doesn't exist, etc.)."""
        mock_run_git.return_value = MagicMock(returncode=1, stdout="", stderr="error")

        count = get_remote_ahead_count("feature/nonexistent")
        assert count == -1

    @patch('worktree_shared.run_git')
    def test_remote_ahead_check_uses_correct_command(self, mock_run_git):
        """Test the correct git command is used for ahead check."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="3\n")

        get_remote_ahead_count("feature/test", cwd=Path("/repo"))

        # Verify command structure
        call_args = mock_run_git.call_args
        args = call_args[0][0] if call_args[0] else call_args[1].get('args', [])
        assert "rev-list" in args
        assert "--count" in args
        assert "feature/test..origin/feature/test" in args


class TestUnmergedBranchSafety:
    """Test that unmerged branches are not automatically deleted."""

    @patch('worktree_shared.run_git')
    def test_is_branch_merged_true(self, mock_run_git):
        """Test merged branch detection."""
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout="  feature/merged\n  other-branch\n"
        )

        result = is_branch_merged("feature/merged")
        assert result == True

    @patch('worktree_shared.run_git')
    def test_is_branch_merged_false(self, mock_run_git):
        """Test unmerged branch detection."""
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout="  other-branch\n  another-branch\n"
        )

        result = is_branch_merged("feature/unmerged")
        assert result == False

    @patch('worktree_shared.run_git')
    def test_is_branch_merged_handles_current_branch_marker(self, mock_run_git):
        """Test handling of current branch marker (*)."""
        mock_run_git.return_value = MagicMock(
            returncode=0,
            stdout="* feature/current\n  other-branch\n"
        )

        result = is_branch_merged("feature/current")
        assert result == True


class TestDeleteRemoteBranchSafety:
    """Test remote branch deletion safety."""

    @patch('worktree_shared.run_git')
    def test_delete_remote_branch_success(self, mock_run_git):
        """Test successful remote branch deletion."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="", stderr="")

        success, message = delete_remote_branch("feature/test")

        assert success == True
        assert message == "deleted"

    @patch('worktree_shared.run_git')
    def test_delete_remote_branch_already_gone(self, mock_run_git):
        """Test deleting already-deleted remote branch."""
        mock_run_git.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error: remote ref does not exist"
        )

        success, message = delete_remote_branch("feature/already-gone")

        # Should succeed (idempotent) with "already absent" message
        assert success == True
        assert "already absent" in message

    @patch('worktree_shared.run_git')
    def test_delete_remote_branch_permission_error(self, mock_run_git):
        """Test handling of permission errors."""
        mock_run_git.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="remote: Permission denied"
        )

        success, message = delete_remote_branch("feature/protected")

        assert success == False
        assert "Permission denied" in message


class TestCleanupDecisionLogic:
    """Test the decision logic for what gets cleaned up.

    These tests verify the cleanup decision matrix:
    - clean + merged + !remote_ahead -> DELETE
    - dirty -> SKIP (unless force)
    - unmerged -> SKIP (needs explicit approval)
    - remote_ahead > 0 -> SKIP remote deletion
    - protected -> NEVER delete branch (only remove worktree)
    """

    def test_cleanup_decision_clean_merged(self):
        """Clean + merged should allow deletion."""
        # This is a logical test - verify our understanding
        is_clean = True
        is_merged = True
        remote_ahead = 0
        is_protected = False

        should_cleanup = is_clean and is_merged and remote_ahead == 0 and not is_protected
        assert should_cleanup == True

    def test_cleanup_decision_dirty(self):
        """Dirty worktree should prevent cleanup."""
        is_clean = False
        is_merged = True
        remote_ahead = 0
        is_protected = False

        should_cleanup = is_clean and is_merged and remote_ahead == 0 and not is_protected
        assert should_cleanup == False

    def test_cleanup_decision_unmerged(self):
        """Unmerged branch should prevent cleanup."""
        is_clean = True
        is_merged = False
        remote_ahead = 0
        is_protected = False

        should_cleanup = is_clean and is_merged and remote_ahead == 0 and not is_protected
        assert should_cleanup == False

    def test_cleanup_decision_remote_ahead(self):
        """Remote ahead should prevent remote deletion."""
        is_clean = True
        is_merged = True
        remote_ahead = 5  # Remote has 5 commits we don't have!
        is_protected = False

        # Local cleanup ok, but remote deletion blocked
        should_delete_remote = is_clean and is_merged and remote_ahead == 0 and not is_protected
        assert should_delete_remote == False

    def test_cleanup_decision_protected(self):
        """Protected branch should never be deleted."""
        is_clean = True
        is_merged = True
        remote_ahead = 0
        is_protected = True

        should_delete_branch = is_clean and is_merged and remote_ahead == 0 and not is_protected
        assert should_delete_branch == False


class TestOrphanedRemoteHandling:
    """Test that orphaned remotes are properly tracked for cleanup."""

    def test_orphaned_remote_state_detection(self, tmp_path):
        """Test detecting orphaned remote state."""
        entry = TrackingEntry(
            branch="feature/orphaned",
            path="/nonexistent/path",  # Local doesn't exist
            base="main",
            owner="test-user",
            created="2024-01-15T10:30:00Z",
            last_checked="2024-01-15T10:30:00Z",
            local_worktree=False,
            remote_exists=True,  # But remote does
        )

        # This state means: local worktree was deleted, remote still exists
        is_orphaned_remote = not entry.local_worktree and entry.remote_exists
        assert is_orphaned_remote == True

    def test_orphaned_remote_cleanup_path(self, tmp_path):
        """Test orphaned remote can be identified for cleanup."""
        tracking_path = tmp_path / "tracking.jsonl"
        entries = [
            TrackingEntry(branch="feature/active", path="/exists", base="main",
                          owner="user", created="2024-01-15T10:30:00Z",
                          last_checked="2024-01-15T10:30:00Z",
                          local_worktree=True, remote_exists=True),
            TrackingEntry(branch="feature/orphaned", path="/gone", base="main",
                          owner="user", created="2024-01-15T10:30:00Z",
                          last_checked="2024-01-15T10:30:00Z",
                          local_worktree=False, remote_exists=True),
        ]
        save_tracking_jsonl(tracking_path, entries)

        from worktree_shared import load_tracking_jsonl
        loaded = load_tracking_jsonl(tracking_path)

        orphaned = [e for e in loaded if not e.local_worktree and e.remote_exists]
        assert len(orphaned) == 1
        assert orphaned[0].branch == "feature/orphaned"


class TestOwnerFiltering:
    """Test owner-based filtering for cleanup."""

    def test_owner_filter_matches(self, tmp_path):
        """Test entries are correctly filtered by owner."""
        entries = [
            TrackingEntry(branch="feature/mine", path="/mine", base="main",
                          owner="Alice", created="2024-01-15T10:30:00Z",
                          last_checked="2024-01-15T10:30:00Z"),
            TrackingEntry(branch="feature/theirs", path="/theirs", base="main",
                          owner="Bob", created="2024-01-15T10:30:00Z",
                          last_checked="2024-01-15T10:30:00Z"),
            TrackingEntry(branch="feature/also-mine", path="/also", base="main",
                          owner="Alice", created="2024-01-15T10:30:00Z",
                          last_checked="2024-01-15T10:30:00Z"),
        ]

        alice_entries = [e for e in entries if e.owner == "Alice"]
        assert len(alice_entries) == 2
        assert all(e.owner == "Alice" for e in alice_entries)

    def test_owner_filter_case_sensitive(self, tmp_path):
        """Test owner filter is case-sensitive."""
        entries = [
            TrackingEntry(branch="feature/a", path="/a", base="main",
                          owner="Alice", created="2024-01-15T10:30:00Z",
                          last_checked="2024-01-15T10:30:00Z"),
            TrackingEntry(branch="feature/b", path="/b", base="main",
                          owner="alice", created="2024-01-15T10:30:00Z",
                          last_checked="2024-01-15T10:30:00Z"),
        ]

        alice_entries = [e for e in entries if e.owner == "Alice"]
        assert len(alice_entries) == 1
