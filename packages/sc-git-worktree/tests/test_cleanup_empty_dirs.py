"""Tests for cleanup_empty_directories function.

These tests verify that empty directories are properly cleaned up
while preserving important files and handling edge cases.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from worktree_shared import cleanup_empty_directories


class TestCleanupEmptyDirectoriesBasic:
    """Basic functionality tests."""

    def test_nonexistent_base_returns_empty(self, tmp_path):
        """Test that non-existent base directory returns empty list."""
        nonexistent = tmp_path / "does_not_exist"
        result = cleanup_empty_directories(nonexistent)
        assert result == []

    def test_empty_base_not_removed(self, tmp_path):
        """Test that the base directory itself is never removed."""
        base = tmp_path / "worktrees"
        base.mkdir()

        result = cleanup_empty_directories(base)

        assert result == []
        assert base.exists()

    def test_single_empty_dir_removed(self, tmp_path):
        """Test that a single empty directory is removed."""
        base = tmp_path / "worktrees"
        empty_dir = base / "feature" / "old-branch"
        empty_dir.mkdir(parents=True)

        result = cleanup_empty_directories(base)

        assert not empty_dir.exists()
        assert not (base / "feature").exists()  # Parent also empty now
        assert str(empty_dir) in result
        assert str(base / "feature") in result

    def test_multiple_empty_dirs_removed(self, tmp_path):
        """Test that multiple empty directories are removed."""
        base = tmp_path / "worktrees"
        empty1 = base / "feature" / "branch1"
        empty2 = base / "feature" / "branch2"
        empty3 = base / "hotfix" / "fix1"
        empty1.mkdir(parents=True)
        empty2.mkdir(parents=True)
        empty3.mkdir(parents=True)

        result = cleanup_empty_directories(base)

        assert not empty1.exists()
        assert not empty2.exists()
        assert not empty3.exists()
        assert not (base / "feature").exists()
        assert not (base / "hotfix").exists()
        assert len(result) >= 5  # 3 leaves + 2 parents


class TestCleanupPreservesFiles:
    """Tests for file preservation behavior."""

    def test_dir_with_files_preserved(self, tmp_path):
        """Test that directories with files are not removed."""
        base = tmp_path / "worktrees"
        dir_with_file = base / "feature" / "active"
        dir_with_file.mkdir(parents=True)
        (dir_with_file / "some_file.txt").write_text("content")

        result = cleanup_empty_directories(base)

        assert dir_with_file.exists()
        assert str(dir_with_file) not in result

    def test_default_tracking_file_preserved(self, tmp_path):
        """Test that worktree-tracking.jsonl preserves its directory."""
        base = tmp_path / "worktrees"
        base.mkdir()
        (base / "worktree-tracking.jsonl").write_text("{}")

        result = cleanup_empty_directories(base)

        assert base.exists()
        assert (base / "worktree-tracking.jsonl").exists()
        assert result == []

    def test_legacy_tracking_file_preserved(self, tmp_path):
        """Test that worktree-tracking.md preserves its directory."""
        base = tmp_path / "worktrees"
        base.mkdir()
        (base / "worktree-tracking.md").write_text("# Tracking")

        result = cleanup_empty_directories(base)

        assert base.exists()
        assert (base / "worktree-tracking.md").exists()

    def test_custom_preserve_files(self, tmp_path):
        """Test custom preserve_files parameter."""
        base = tmp_path / "worktrees"
        subdir = base / "config"
        subdir.mkdir(parents=True)
        (subdir / "custom.cfg").write_text("config")

        # Without custom preserve - would check for .jsonl/.md
        # But this dir has custom.cfg so it won't be removed anyway
        result = cleanup_empty_directories(base, preserve_files=["custom.cfg"])

        assert subdir.exists()
        assert str(subdir) not in result

    def test_tracking_file_in_subdir_preserved(self, tmp_path):
        """Test tracking file in subdirectory preserves that dir."""
        base = tmp_path / "worktrees"
        subdir = base / "nested"
        subdir.mkdir(parents=True)
        (subdir / "worktree-tracking.jsonl").write_text("{}")

        result = cleanup_empty_directories(base)

        assert subdir.exists()


class TestCleanupNestedStructure:
    """Tests for nested directory structures."""

    def test_partial_cleanup_with_mixed_content(self, tmp_path):
        """Test cleanup with mix of empty and non-empty directories."""
        base = tmp_path / "worktrees"

        # Create structure:
        # worktrees/
        #   feature/
        #     active/
        #       file.txt
        #     empty/
        #   hotfix/
        #     empty1/
        #     empty2/

        active = base / "feature" / "active"
        empty_feature = base / "feature" / "empty"
        empty_hotfix1 = base / "hotfix" / "empty1"
        empty_hotfix2 = base / "hotfix" / "empty2"

        active.mkdir(parents=True)
        (active / "file.txt").write_text("content")
        empty_feature.mkdir(parents=True)
        empty_hotfix1.mkdir(parents=True)
        empty_hotfix2.mkdir(parents=True)

        result = cleanup_empty_directories(base)

        # Active should remain
        assert active.exists()
        assert (base / "feature").exists()

        # Empty dirs should be removed
        assert not empty_feature.exists()
        assert not empty_hotfix1.exists()
        assert not empty_hotfix2.exists()
        assert not (base / "hotfix").exists()

    def test_deeply_nested_empty_dirs(self, tmp_path):
        """Test cleanup of deeply nested empty directories."""
        base = tmp_path / "worktrees"
        deep = base / "a" / "b" / "c" / "d" / "e"
        deep.mkdir(parents=True)

        result = cleanup_empty_directories(base)

        # All nested empty dirs should be removed
        assert not (base / "a").exists()
        assert len(result) == 5  # a, b, c, d, e

    def test_sibling_dirs_one_empty_one_not(self, tmp_path):
        """Test that non-empty sibling prevents parent removal."""
        base = tmp_path / "worktrees"
        empty = base / "parent" / "empty"
        nonempty = base / "parent" / "nonempty"
        empty.mkdir(parents=True)
        nonempty.mkdir(parents=True)
        (nonempty / "file.txt").write_text("content")

        result = cleanup_empty_directories(base)

        assert not empty.exists()
        assert nonempty.exists()
        assert (base / "parent").exists()  # Parent preserved


class TestCleanupEdgeCases:
    """Edge cases and error handling."""

    def test_hidden_files_preserve_dir(self, tmp_path):
        """Test that hidden files preserve their directory."""
        base = tmp_path / "worktrees"
        dir_with_hidden = base / "feature" / "branch"
        dir_with_hidden.mkdir(parents=True)
        (dir_with_hidden / ".gitkeep").write_text("")

        result = cleanup_empty_directories(base)

        assert dir_with_hidden.exists()

    def test_symlink_handling(self, tmp_path):
        """Test handling of symbolic links."""
        base = tmp_path / "worktrees"
        target = tmp_path / "target"
        target.mkdir()
        link_parent = base / "feature"
        link_parent.mkdir(parents=True)

        link = link_parent / "symlink"
        link.symlink_to(target)

        result = cleanup_empty_directories(base)

        # Directory with symlink should be preserved (symlink counts as entry)
        assert link_parent.exists()

    def test_permission_error_handled(self, tmp_path):
        """Test that permission errors are handled gracefully."""
        base = tmp_path / "worktrees"
        protected = base / "protected"
        protected.mkdir(parents=True)

        with patch('pathlib.Path.rmdir') as mock_rmdir:
            mock_rmdir.side_effect = OSError("Permission denied")

            # Should not raise, just skip the directory
            result = cleanup_empty_directories(base)

            # Directory still exists (rmdir failed)
            assert protected.exists()
            assert str(protected) not in result

    def test_race_condition_dir_not_empty(self, tmp_path):
        """Test handling when directory becomes non-empty during cleanup."""
        base = tmp_path / "worktrees"
        racing = base / "racing"
        racing.mkdir(parents=True)

        original_rmdir = Path.rmdir

        def rmdir_with_race(self):
            if "racing" in str(self):
                raise OSError("Directory not empty")
            return original_rmdir(self)

        with patch.object(Path, 'rmdir', rmdir_with_race):
            result = cleanup_empty_directories(base)

            assert str(racing) not in result

    def test_returns_absolute_paths(self, tmp_path):
        """Test that returned paths are absolute."""
        base = tmp_path / "worktrees"
        empty = base / "empty"
        empty.mkdir(parents=True)

        result = cleanup_empty_directories(base)

        assert len(result) > 0
        for path in result:
            assert Path(path).is_absolute()

    def test_empty_preserve_files_list(self, tmp_path):
        """Test with empty preserve_files list."""
        base = tmp_path / "worktrees"
        with_tracking = base / "tracked"
        with_tracking.mkdir(parents=True)
        (with_tracking / "worktree-tracking.jsonl").write_text("{}")

        # With empty preserve list, tracking file won't protect directory
        # but directory has files so it won't be removed anyway
        result = cleanup_empty_directories(base, preserve_files=[])

        assert with_tracking.exists()


class TestCleanupRealWorldScenarios:
    """Tests simulating real-world worktree cleanup scenarios."""

    def test_after_single_branch_cleanup(self, tmp_path):
        """Simulate cleanup after a single branch worktree is removed."""
        base = tmp_path / "worktrees"

        # Structure after worktree removal:
        # worktrees/
        #   worktree-tracking.jsonl
        #   feature/
        #     other-branch/  (still active)
        #       .git
        #     cleaned-branch/  (empty - worktree was here)

        (base / "feature" / "other-branch").mkdir(parents=True)
        (base / "feature" / "other-branch" / ".git").write_text("gitdir: ...")
        (base / "feature" / "cleaned-branch").mkdir(parents=True)
        (base / "worktree-tracking.jsonl").write_text("{}")

        result = cleanup_empty_directories(base)

        assert not (base / "feature" / "cleaned-branch").exists()
        assert (base / "feature" / "other-branch").exists()
        assert (base / "feature").exists()

    def test_after_batch_cleanup(self, tmp_path):
        """Simulate cleanup after batch cleanup of all merged branches."""
        base = tmp_path / "worktrees"

        # All worktrees removed, only tracking file remains
        (base / "feature").mkdir(parents=True)
        (base / "hotfix").mkdir(parents=True)
        (base / "release").mkdir(parents=True)
        (base / "worktree-tracking.jsonl").write_text("{}")

        result = cleanup_empty_directories(base)

        # All empty category dirs removed
        assert not (base / "feature").exists()
        assert not (base / "hotfix").exists()
        assert not (base / "release").exists()

        # Base and tracking preserved
        assert base.exists()
        assert (base / "worktree-tracking.jsonl").exists()

    def test_mixed_branch_types(self, tmp_path):
        """Test cleanup with various branch naming conventions."""
        base = tmp_path / "worktrees"

        # Create various branch structures
        (base / "feature" / "JIRA-123-add-login").mkdir(parents=True)
        (base / "feature" / "JIRA-456-empty").mkdir(parents=True)
        (base / "bugfix" / "fix-typo").mkdir(parents=True)
        (base / "user" / "john" / "experiment").mkdir(parents=True)

        # Add content to some
        (base / "feature" / "JIRA-123-add-login" / ".git").write_text("gitdir")
        (base / "bugfix" / "fix-typo" / ".git").write_text("gitdir")

        result = cleanup_empty_directories(base)

        # Active branches preserved
        assert (base / "feature" / "JIRA-123-add-login").exists()
        assert (base / "bugfix" / "fix-typo").exists()

        # Empty branches and their parents removed
        assert not (base / "feature" / "JIRA-456-empty").exists()
        assert not (base / "user").exists()
