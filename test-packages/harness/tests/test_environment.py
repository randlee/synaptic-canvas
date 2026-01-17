"""
Unit tests for harness.environment module.

Tests the environment isolation functionality including:
- Isolated HOME creation and cleanup
- Marketplace data copying
- Transcript path computation
- Context manager behavior
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from harness.environment import (
    DEFAULT_TEST_HOME_PREFIX,
    cleanup_test_environment,
    copy_marketplace_data,
    create_isolated_home,
    get_git_state,
    get_transcript_path,
    isolated_claude_session,
    setup_test_environment,
)


class TestCreateIsolatedHome:
    """Tests for create_isolated_home function."""

    def test_creates_directory(self):
        """Test that isolated home is created."""
        home = create_isolated_home()
        try:
            assert home.exists()
            assert home.is_dir()
        finally:
            cleanup_test_environment(home, force=True)

    def test_creates_claude_subdirectory(self):
        """Test that .claude subdirectory is created."""
        home = create_isolated_home()
        try:
            claude_dir = home / ".claude"
            assert claude_dir.exists()
            assert claude_dir.is_dir()
        finally:
            cleanup_test_environment(home, force=True)

    def test_unique_directories(self):
        """Test that each call creates a unique directory."""
        home1 = create_isolated_home()
        home2 = create_isolated_home()
        try:
            assert home1 != home2
            assert home1.name != home2.name
        finally:
            cleanup_test_environment(home1, force=True)
            cleanup_test_environment(home2, force=True)

    def test_custom_prefix(self):
        """Test creating home with custom prefix."""
        home = create_isolated_home(prefix="my-test-")
        try:
            assert "my-test-" in home.name
        finally:
            cleanup_test_environment(home, force=True)

    def test_custom_base_dir(self):
        """Test creating home in custom base directory."""
        with tempfile.TemporaryDirectory() as base:
            home = create_isolated_home(base_dir=base)
            assert str(home).startswith(base)
            # Note: home will be cleaned up when base is deleted


class TestCopyMarketplaceData:
    """Tests for copy_marketplace_data function."""

    def test_copies_marketplace_file(self):
        """Test copying marketplace file."""
        with tempfile.TemporaryDirectory() as source_dir:
            with tempfile.TemporaryDirectory() as dest_dir:
                source_home = Path(source_dir)
                dest_home = Path(dest_dir)

                # Create source structure
                source_plugins = source_home / ".claude" / "plugins"
                source_plugins.mkdir(parents=True)
                (source_plugins / "known_marketplaces.json").write_text("{}")

                # Copy
                result = copy_marketplace_data(dest_home, source_home)

                # Verify
                assert result is True
                dest_file = dest_home / ".claude" / "plugins" / "known_marketplaces.json"
                assert dest_file.exists()

    def test_copies_marketplace_directory(self):
        """Test copying marketplace directory."""
        with tempfile.TemporaryDirectory() as source_dir:
            with tempfile.TemporaryDirectory() as dest_dir:
                source_home = Path(source_dir)
                dest_home = Path(dest_dir)

                # Create source structure with directory
                source_plugins = source_home / ".claude" / "plugins"
                source_mkt = source_plugins / "marketplaces"
                source_mkt.mkdir(parents=True)
                (source_mkt / "registry.json").write_text("{}")

                # Copy
                result = copy_marketplace_data(dest_home, source_home)

                # Verify
                assert result is True
                dest_mkt = dest_home / ".claude" / "plugins" / "marketplaces"
                assert dest_mkt.exists()
                assert (dest_mkt / "registry.json").exists()

    def test_returns_false_if_no_source(self):
        """Test returns False if source doesn't exist."""
        with tempfile.TemporaryDirectory() as dest_dir:
            dest_home = Path(dest_dir)
            nonexistent = Path("/nonexistent/path")

            result = copy_marketplace_data(dest_home, nonexistent)
            assert result is False


class TestSetupTestEnvironment:
    """Tests for setup_test_environment function."""

    def test_sets_home_env(self):
        """Test that HOME is set in environment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            isolated_home = Path(temp_dir)
            project_path = Path("/fake/project")

            env = setup_test_environment(isolated_home, project_path)

            assert env["HOME"] == str(isolated_home)

    def test_sets_project_path(self):
        """Test that project path is set."""
        with tempfile.TemporaryDirectory() as temp_dir:
            isolated_home = Path(temp_dir)
            project_path = Path("/fake/project")

            env = setup_test_environment(isolated_home, project_path)

            assert "SC_TEST_PROJECT" in env

    def test_inherits_current_env(self):
        """Test that current environment is inherited."""
        with tempfile.TemporaryDirectory() as temp_dir:
            isolated_home = Path(temp_dir)
            project_path = Path("/fake/project")

            # Set a test env var
            os.environ["TEST_HARNESS_VAR"] = "test_value"
            try:
                env = setup_test_environment(isolated_home, project_path)
                assert env.get("TEST_HARNESS_VAR") == "test_value"
            finally:
                del os.environ["TEST_HARNESS_VAR"]


class TestCleanupTestEnvironment:
    """Tests for cleanup_test_environment function."""

    def test_removes_directory(self):
        """Test that directory is removed."""
        home = create_isolated_home()
        assert home.exists()

        result = cleanup_test_environment(home)

        assert result is True
        assert not home.exists()

    def test_handles_nonexistent(self):
        """Test handling of nonexistent directory."""
        nonexistent = Path("/tmp/nonexistent-test-dir-12345")
        result = cleanup_test_environment(nonexistent)
        assert result is True

    def test_refuses_real_home(self):
        """Test that real HOME cannot be deleted."""
        real_home = Path.home()
        with pytest.raises(ValueError, match="real HOME"):
            cleanup_test_environment(real_home)

    def test_refuses_non_test_directory(self):
        """Test that non-test directories not in temp require force."""
        # Create a directory outside temp dir without test prefix
        # Use a subdirectory of the current test location
        import os
        non_temp_dir = Path(os.getcwd()) / "test-cleanup-temp-dir"
        non_temp_dir.mkdir(exist_ok=True)
        try:
            # This directory is not in temp and doesn't have the prefix
            with pytest.raises(ValueError, match="non-test directory"):
                cleanup_test_environment(non_temp_dir)
        finally:
            # Clean up manually
            if non_temp_dir.exists():
                non_temp_dir.rmdir()

    def test_force_deletes_any_directory(self):
        """Test that force=True deletes any directory."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Use a temporary directory created manually
            temp_dir = Path(f.name).parent / "force-test-dir"
            temp_dir.mkdir(exist_ok=True)
            (temp_dir / "file.txt").write_text("test")

            result = cleanup_test_environment(temp_dir, force=True)
            assert result is True
            assert not temp_dir.exists()


class TestGetTranscriptPath:
    """Tests for get_transcript_path function."""

    def test_encodes_path_correctly(self):
        """Test that project path is encoded correctly."""
        isolated_home = Path("/tmp/claude-test-123")
        project_path = Path("/Users/test/project")
        session_id = "abc-123"

        result = get_transcript_path(isolated_home, project_path, session_id)

        assert str(result).startswith("/tmp/claude-test-123/.claude/projects/")
        assert "-Users-test-project" in str(result)
        assert result.name == "abc-123.jsonl"

    def test_handles_leading_slash(self):
        """Test handling of leading slash in path."""
        isolated_home = Path("/tmp/test")
        project_path = Path("/absolute/path")
        session_id = "session"

        result = get_transcript_path(isolated_home, project_path, session_id)

        # Should have single dash prefix, not double
        assert "-absolute-path" in str(result)


class TestIsolatedClaudeSession:
    """Tests for isolated_claude_session context manager."""

    def test_creates_session_with_paths(self):
        """Test that session is created with correct paths."""
        with tempfile.TemporaryDirectory() as project_dir:
            project_path = Path(project_dir)
            (project_path / ".claude").mkdir()
            (project_path / "reports").mkdir()

            with isolated_claude_session(project_path) as session:
                assert session.isolated_home.exists()
                assert session.project_path == project_path
                assert session.trace_path.parent.exists()

    def test_cleans_up_on_exit(self):
        """Test that isolated home is cleaned up."""
        with tempfile.TemporaryDirectory() as project_dir:
            project_path = Path(project_dir)
            (project_path / ".claude").mkdir()
            (project_path / "reports").mkdir()

            with isolated_claude_session(project_path) as session:
                home = session.isolated_home
                assert home.exists()

            # After context exit, should be cleaned up
            assert not home.exists()

    def test_skip_cleanup_option(self):
        """Test that cleanup can be skipped."""
        with tempfile.TemporaryDirectory() as project_dir:
            project_path = Path(project_dir)
            (project_path / ".claude").mkdir()
            (project_path / "reports").mkdir()

            with isolated_claude_session(project_path, cleanup=False) as session:
                home = session.isolated_home

            # Should still exist after context exit
            assert home.exists()

            # Manual cleanup
            cleanup_test_environment(home, force=True)

    def test_env_has_home_override(self):
        """Test that env dict has HOME override."""
        with tempfile.TemporaryDirectory() as project_dir:
            project_path = Path(project_dir)
            (project_path / ".claude").mkdir()
            (project_path / "reports").mkdir()

            with isolated_claude_session(project_path) as session:
                assert session.env["HOME"] == str(session.isolated_home)

    def test_clears_existing_trace(self):
        """Test that existing trace file is cleared."""
        with tempfile.TemporaryDirectory() as project_dir:
            project_path = Path(project_dir)
            (project_path / ".claude").mkdir()
            reports_dir = project_path / "reports"
            reports_dir.mkdir()

            # Create existing trace file
            trace_path = reports_dir / "trace.jsonl"
            trace_path.write_text('{"old": "data"}')

            with isolated_claude_session(project_path) as session:
                # Trace should be cleared
                assert not session.trace_path.exists()


class TestGetGitState:
    """Tests for get_git_state function."""

    def test_returns_dict_structure(self):
        """Test that correct dict structure is returned."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = get_git_state(Path(temp_dir))

            assert "branch" in result
            assert "commit" in result
            assert "modified_files" in result
            assert isinstance(result["modified_files"], list)

    def test_handles_non_git_directory(self):
        """Test handling of non-git directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = get_git_state(Path(temp_dir))

            # Should return empty values, not crash
            assert result["branch"] == ""
            assert result["commit"] == ""

    @patch("subprocess.run")
    def test_parses_git_output(self, mock_run):
        """Test parsing of git command output."""
        # Mock git branch output
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="develop\n"),  # branch
            MagicMock(returncode=0, stdout="abc123\n"),  # commit
            MagicMock(returncode=0, stdout=" M file1.py\n?? file2.py\n"),  # status
        ]

        result = get_git_state(Path("/fake/path"))

        assert result["branch"] == "develop"
        assert result["commit"] == "abc123"
        assert "file1.py" in result["modified_files"]


class TestIsolatedSessionMethods:
    """Tests for IsolatedSession methods."""

    def test_find_transcript_returns_none_if_no_projects(self):
        """Test find_transcript returns None if no projects directory."""
        with tempfile.TemporaryDirectory() as project_dir:
            project_path = Path(project_dir)
            (project_path / ".claude").mkdir()
            (project_path / "reports").mkdir()

            with isolated_claude_session(project_path) as session:
                result = session.find_transcript()
                assert result is None

    def test_find_transcript_finds_most_recent(self):
        """Test find_transcript returns most recent transcript."""
        with tempfile.TemporaryDirectory() as project_dir:
            project_path = Path(project_dir)
            (project_path / ".claude").mkdir()
            (project_path / "reports").mkdir()

            with isolated_claude_session(project_path) as session:
                # Create projects directory with transcripts
                projects_dir = session.isolated_home / ".claude" / "projects" / "test"
                projects_dir.mkdir(parents=True)

                # Create older transcript
                old_transcript = projects_dir / "old-session.jsonl"
                old_transcript.write_text('{"type": "old"}')

                import time
                time.sleep(0.1)

                # Create newer transcript
                new_transcript = projects_dir / "new-session.jsonl"
                new_transcript.write_text('{"type": "new"}')

                result = session.find_transcript()

                assert result == new_transcript
                assert session.transcript_path == new_transcript
                assert session.session_id == "new-session"
