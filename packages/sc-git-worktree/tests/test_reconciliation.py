"""Tests for tracking reconciliation logic.

CRITICAL: These tests verify the safety of branch management.
Mistakes here could lead to data loss through accidental branch deletion.

The reconciliation logic must ensure:
1. Entries are only removed when BOTH local worktree AND remote branch are gone
2. Orphaned remotes (local deleted, remote exists) are preserved for cleanup
3. Remote-ahead branches are flagged but not auto-deleted
4. Protected branches are never deleted
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from worktree_shared import (
    TrackingEntry,
    load_tracking_jsonl,
    save_tracking_jsonl,
    reconcile_tracking,
)


class TestEntryLifecycle:
    """Test the entry lifecycle states.

    Entry states:
    - Active: local_worktree=True, remote_exists=True -> KEEP
    - Local only: local_worktree=True, remote_exists=False -> KEEP
    - Orphaned remote: local_worktree=False, remote_exists=True -> KEEP
    - Fully cleaned: local_worktree=False, remote_exists=False -> REMOVE
    """

    def create_entry(self, branch, local_worktree=True, remote_exists=True):
        """Helper to create a test entry."""
        return TrackingEntry(
            branch=branch,
            path=f"/worktrees/{branch}",
            base="main",
            owner="test-user",
            created="2024-01-15T10:30:00Z",
            last_checked="2024-01-15T10:30:00Z",
            local_worktree=local_worktree,
            remote_exists=remote_exists,
        )

    @patch('worktree_shared.run_git')
    @patch('worktree_shared.check_remote_branch_exists')
    def test_active_entry_preserved(self, mock_remote_exists, mock_run_git, tmp_path):
        """Active entries (local + remote exist) are preserved."""
        tracking_path = tmp_path / "tracking.jsonl"
        worktree_path = tmp_path / "worktrees" / "feature" / "test"
        worktree_path.mkdir(parents=True)

        entry = TrackingEntry(
            branch="feature/test",
            path=str(worktree_path),
            base="main",
            owner="test-user",
            created="2024-01-15T10:30:00Z",
            last_checked="2024-01-15T10:30:00Z",
        )
        save_tracking_jsonl(tracking_path, [entry])

        mock_run_git.return_value = MagicMock(returncode=0, stdout="")
        mock_remote_exists.return_value = True

        result = reconcile_tracking(tracking_path, tmp_path)

        entries = load_tracking_jsonl(tracking_path)
        assert len(entries) == 1
        assert entries[0].branch == "feature/test"
        assert "feature/test" not in result.get("removed", [])

    @patch('worktree_shared.run_git')
    @patch('worktree_shared.check_remote_branch_exists')
    def test_local_only_entry_preserved(self, mock_remote_exists, mock_run_git, tmp_path):
        """Local-only entries (not pushed) are preserved."""
        tracking_path = tmp_path / "tracking.jsonl"
        worktree_path = tmp_path / "worktrees" / "feature" / "local"
        worktree_path.mkdir(parents=True)

        entry = TrackingEntry(
            branch="feature/local",
            path=str(worktree_path),
            base="main",
            owner="test-user",
            created="2024-01-15T10:30:00Z",
            last_checked="2024-01-15T10:30:00Z",
            remote_exists=False,  # not pushed yet
        )
        save_tracking_jsonl(tracking_path, [entry])

        mock_run_git.return_value = MagicMock(returncode=0, stdout="")
        mock_remote_exists.return_value = False  # remote doesn't exist

        result = reconcile_tracking(tracking_path, tmp_path)

        entries = load_tracking_jsonl(tracking_path)
        assert len(entries) == 1
        assert entries[0].branch == "feature/local"
        assert entries[0].local_worktree == True
        assert "feature/local" not in result.get("removed", [])

    @patch('worktree_shared.run_git')
    @patch('worktree_shared.check_remote_branch_exists')
    def test_orphaned_remote_preserved(self, mock_remote_exists, mock_run_git, tmp_path):
        """CRITICAL: Orphaned remotes (local deleted, remote exists) are PRESERVED."""
        tracking_path = tmp_path / "tracking.jsonl"

        # Entry with path that doesn't exist (local worktree deleted)
        entry = TrackingEntry(
            branch="feature/orphaned",
            path="/nonexistent/path",
            base="main",
            owner="test-user",
            created="2024-01-15T10:30:00Z",
            last_checked="2024-01-15T10:30:00Z",
        )
        save_tracking_jsonl(tracking_path, [entry])

        mock_run_git.return_value = MagicMock(returncode=0, stdout="")
        mock_remote_exists.return_value = True  # remote still exists!

        result = reconcile_tracking(tracking_path, tmp_path)

        # Entry MUST be preserved
        entries = load_tracking_jsonl(tracking_path)
        assert len(entries) == 1, "Orphaned remote entry must be preserved"
        assert entries[0].branch == "feature/orphaned"
        assert entries[0].local_worktree == False
        assert entries[0].remote_exists == True
        assert "feature/orphaned" not in result.get("removed", [])

    @patch('worktree_shared.run_git')
    @patch('worktree_shared.check_remote_branch_exists')
    def test_fully_cleaned_entry_removed(self, mock_remote_exists, mock_run_git, tmp_path):
        """Fully cleaned entries (no local, no remote) are removed."""
        tracking_path = tmp_path / "tracking.jsonl"

        entry = TrackingEntry(
            branch="feature/cleaned",
            path="/nonexistent/path",
            base="main",
            owner="test-user",
            created="2024-01-15T10:30:00Z",
            last_checked="2024-01-15T10:30:00Z",
        )
        save_tracking_jsonl(tracking_path, [entry])

        mock_run_git.return_value = MagicMock(returncode=0, stdout="")
        mock_remote_exists.return_value = False  # remote also gone

        result = reconcile_tracking(tracking_path, tmp_path)

        entries = load_tracking_jsonl(tracking_path)
        assert len(entries) == 0, "Fully cleaned entry should be removed"
        assert "feature/cleaned" in result.get("removed", [])


class TestRemoteAheadTracking:
    """Test remote_ahead tracking and safety."""

    @patch('worktree_shared.run_git')
    @patch('worktree_shared.check_remote_branch_exists')
    @patch('worktree_shared.get_remote_ahead_count')
    def test_remote_ahead_count_tracked(self, mock_ahead, mock_remote_exists, mock_run_git, tmp_path):
        """Remote ahead count is properly tracked."""
        tracking_path = tmp_path / "tracking.jsonl"
        worktree_path = tmp_path / "worktrees" / "feature" / "behind"
        worktree_path.mkdir(parents=True)

        entry = TrackingEntry(
            branch="feature/behind",
            path=str(worktree_path),
            base="main",
            owner="test-user",
            created="2024-01-15T10:30:00Z",
            last_checked="2024-01-15T10:30:00Z",
            remote_ahead=0,
        )
        save_tracking_jsonl(tracking_path, [entry])

        mock_run_git.return_value = MagicMock(returncode=0, stdout="")
        mock_remote_exists.return_value = True
        mock_ahead.return_value = 5  # Remote has 5 commits we don't have

        result = reconcile_tracking(tracking_path, tmp_path)

        entries = load_tracking_jsonl(tracking_path)
        assert entries[0].remote_ahead == 5

        # Should generate warning
        warnings = result.get("warnings", [])
        assert any(w.get("branch") == "feature/behind" for w in warnings)

    @patch('worktree_shared.run_git')
    @patch('worktree_shared.check_remote_branch_exists')
    @patch('worktree_shared.get_remote_ahead_count')
    def test_remote_ahead_prevents_deletion_info(self, mock_ahead, mock_remote_exists, mock_run_git, tmp_path):
        """Remote ahead count > 0 should trigger warning (deletion blocked in cleanup)."""
        tracking_path = tmp_path / "tracking.jsonl"
        worktree_path = tmp_path / "worktrees" / "feature" / "behind"
        worktree_path.mkdir(parents=True)

        entry = TrackingEntry(
            branch="feature/behind",
            path=str(worktree_path),
            base="main",
            owner="test-user",
            created="2024-01-15T10:30:00Z",
            last_checked="2024-01-15T10:30:00Z",
        )
        save_tracking_jsonl(tracking_path, [entry])

        mock_run_git.return_value = MagicMock(returncode=0, stdout="")
        mock_remote_exists.return_value = True
        mock_ahead.return_value = 3  # Remote has unpulled commits

        result = reconcile_tracking(tracking_path, tmp_path)

        # Warning must be generated for remote-ahead branches
        warnings = result.get("warnings", [])
        ahead_warnings = [w for w in warnings if w.get("branch") == "feature/behind"]
        assert len(ahead_warnings) == 1
        assert ahead_warnings[0]["remote_ahead"] == 3


class TestMixedEntries:
    """Test reconciliation with mixed entry states."""

    @patch('worktree_shared.run_git')
    @patch('worktree_shared.check_remote_branch_exists')
    def test_mixed_states_handled_correctly(self, mock_remote_exists, mock_run_git, tmp_path):
        """Test various entry states are handled correctly together."""
        tracking_path = tmp_path / "tracking.jsonl"

        # Create some worktree directories
        active_path = tmp_path / "worktrees" / "feature" / "active"
        active_path.mkdir(parents=True)
        local_only_path = tmp_path / "worktrees" / "feature" / "local-only"
        local_only_path.mkdir(parents=True)

        entries = [
            # Active - should keep
            TrackingEntry(branch="feature/active", path=str(active_path), base="main",
                          owner="user1", created="2024-01-15T10:30:00Z",
                          last_checked="2024-01-15T10:30:00Z"),
            # Local only - should keep
            TrackingEntry(branch="feature/local-only", path=str(local_only_path), base="main",
                          owner="user2", created="2024-01-15T10:30:00Z",
                          last_checked="2024-01-15T10:30:00Z"),
            # Orphaned remote - should keep
            TrackingEntry(branch="feature/orphaned", path="/nonexistent", base="main",
                          owner="user3", created="2024-01-15T10:30:00Z",
                          last_checked="2024-01-15T10:30:00Z"),
            # Fully cleaned - should remove
            TrackingEntry(branch="feature/cleaned", path="/also-nonexistent", base="main",
                          owner="user4", created="2024-01-15T10:30:00Z",
                          last_checked="2024-01-15T10:30:00Z"),
        ]
        save_tracking_jsonl(tracking_path, entries)

        # Mock remote existence
        def remote_exists_side_effect(branch, cwd=None):
            return branch in ["feature/active", "feature/orphaned"]

        mock_run_git.return_value = MagicMock(returncode=0, stdout="")
        mock_remote_exists.side_effect = remote_exists_side_effect

        result = reconcile_tracking(tracking_path, tmp_path)

        loaded = load_tracking_jsonl(tracking_path)
        branches = {e.branch for e in loaded}

        # Verify correct entries kept/removed
        assert "feature/active" in branches, "Active entry should be kept"
        assert "feature/local-only" in branches, "Local-only entry should be kept"
        assert "feature/orphaned" in branches, "Orphaned remote should be kept"
        assert "feature/cleaned" not in branches, "Fully cleaned should be removed"

        assert "feature/cleaned" in result["removed"]
        assert len(result["removed"]) == 1


class TestProtectedBranches:
    """Test that protected branches are never auto-processed dangerously."""

    @patch('worktree_shared.run_git')
    @patch('worktree_shared.check_remote_branch_exists')
    @patch('worktree_shared.get_branch_creator_info')
    @patch('worktree_shared.get_all_remote_branches')
    def test_protected_branches_not_discovered(self, mock_all_branches, mock_creator,
                                                mock_remote_exists, mock_run_git, tmp_path):
        """Protected branches should not be added during --all discovery."""
        tracking_path = tmp_path / "tracking.jsonl"
        save_tracking_jsonl(tracking_path, [])

        mock_run_git.return_value = MagicMock(returncode=0, stdout="")
        mock_remote_exists.return_value = True
        mock_all_branches.return_value = ["main", "develop", "feature/test"]
        mock_creator.return_value = {"author": "test", "date": "2024-01-15T10:30:00Z"}

        result = reconcile_tracking(
            tracking_path, tmp_path,
            discover_all=True,
            protected_branches=["main", "develop"],
        )

        discovered = [d["branch"] for d in result.get("discovered", [])]
        assert "main" not in discovered
        assert "develop" not in discovered
        assert "feature/test" in discovered


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @patch('worktree_shared.run_git')
    def test_empty_tracking_file(self, mock_run_git, tmp_path):
        """Test reconciliation with empty tracking file."""
        tracking_path = tmp_path / "tracking.jsonl"
        save_tracking_jsonl(tracking_path, [])

        mock_run_git.return_value = MagicMock(returncode=0, stdout="")

        result = reconcile_tracking(tracking_path, tmp_path)

        assert result["total"] == 0
        assert result["removed"] == []

    @patch('worktree_shared.run_git')
    def test_nonexistent_tracking_file(self, mock_run_git, tmp_path):
        """Test reconciliation with non-existent tracking file."""
        tracking_path = tmp_path / "nonexistent.jsonl"

        mock_run_git.return_value = MagicMock(returncode=0, stdout="")

        result = reconcile_tracking(tracking_path, tmp_path)

        assert result["total"] == 0

    @patch('worktree_shared.run_git')
    @patch('worktree_shared.check_remote_branch_exists')
    def test_duplicate_branches_in_tracking(self, mock_remote_exists, mock_run_git, tmp_path):
        """Test handling of duplicate branch entries (shouldn't happen, but be safe)."""
        tracking_path = tmp_path / "tracking.jsonl"
        worktree_path = tmp_path / "worktrees" / "feature" / "dup"
        worktree_path.mkdir(parents=True)

        # Write duplicate entries directly
        content = ""
        for i in range(2):
            entry = TrackingEntry(
                branch="feature/dup",
                path=str(worktree_path),
                base="main",
                owner=f"user{i}",
                created="2024-01-15T10:30:00Z",
                last_checked="2024-01-15T10:30:00Z",
            )
            content += json.dumps(entry.model_dump()) + "\n"
        tracking_path.write_text(content)

        mock_run_git.return_value = MagicMock(returncode=0, stdout="")
        mock_remote_exists.return_value = True

        # Should not crash
        result = reconcile_tracking(tracking_path, tmp_path)
        assert result["total"] >= 1
