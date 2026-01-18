"""
Unit tests for plugin installation functionality.

Tests the plugin installation features in pytest_plugin.py and runner.py:
- Plugin manifest parsing
- Artifact copying to .claude directory
- Cleanup of installed plugins
- Error handling for missing plugins

Run with:
    pytest test-packages/harness/tests/test_plugin_installation.py -v
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml


# =============================================================================
# Mock Classes for Testing
# =============================================================================


class MockSession:
    """Mock session object for testing plugin installation."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.env = {}


# =============================================================================
# Fixture Setup
# =============================================================================


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with packages."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        packages_dir = project_path / "packages"
        packages_dir.mkdir()

        # Create a test plugin package
        plugin_dir = packages_dir / "test-plugin"
        plugin_dir.mkdir()

        # Create manifest.yaml
        manifest = {
            "name": "test-plugin",
            "version": "1.0.0",
            "description": "Test plugin for testing",
            "artifacts": {
                "commands": ["commands/test-command.md"],
                "skills": ["skills/test-skill/SKILL.md"],
                "agents": ["agents/test-agent.md"],
            },
        }
        with open(plugin_dir / "manifest.yaml", "w") as f:
            yaml.dump(manifest, f)

        # Create artifact directories and files
        (plugin_dir / "commands").mkdir()
        (plugin_dir / "commands" / "test-command.md").write_text("# Test Command")

        (plugin_dir / "skills" / "test-skill").mkdir(parents=True)
        (plugin_dir / "skills" / "test-skill" / "SKILL.md").write_text("# Test Skill")

        (plugin_dir / "agents").mkdir()
        (plugin_dir / "agents" / "test-agent.md").write_text("# Test Agent")

        yield project_path


@pytest.fixture
def temp_session_dir():
    """Create a temporary session directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# YAMLTestItem Plugin Installation Tests
# =============================================================================


class TestYAMLTestItemPluginInstallation:
    """Tests for YAMLTestItem._install_plugins and _cleanup_plugins."""

    def test_install_plugins_copies_artifacts(
        self, temp_project_dir: Path, temp_session_dir: Path
    ):
        """Test that plugin artifacts are copied to session's .claude directory."""
        from harness.pytest_plugin import YAMLTestItem
        from harness.fixture_loader import FixtureConfig, TestConfig, SetupConfig

        # Create a minimal test item
        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)
            item._installed_plugin_files = []
            item._installed_plugin_dirs = []

        # Mock _find_project_path to return our temp project
        item._find_project_path = lambda: temp_project_dir

        # Create mock session
        session = MockSession(temp_session_dir)

        # Create setup config with plugins
        setup = SetupConfig(plugins=["test-plugin@synaptic-canvas"])

        # Install plugins
        item._install_plugins(session, setup)

        # Verify artifacts were copied
        claude_dir = temp_session_dir / ".claude"
        assert claude_dir.exists()
        assert (claude_dir / "commands" / "test-command.md").exists()
        assert (claude_dir / "skills" / "test-skill" / "SKILL.md").exists()
        assert (claude_dir / "agents" / "test-agent.md").exists()

        # Verify content is correct
        assert (claude_dir / "commands" / "test-command.md").read_text() == "# Test Command"

        # Verify tracking lists are populated
        assert len(item._installed_plugin_files) > 0

    def test_install_plugins_handles_missing_plugin(
        self, temp_project_dir: Path, temp_session_dir: Path
    ):
        """Test that missing plugins are handled gracefully."""
        from harness.pytest_plugin import YAMLTestItem
        from harness.fixture_loader import SetupConfig

        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)
            item._installed_plugin_files = []
            item._installed_plugin_dirs = []

        item._find_project_path = lambda: temp_project_dir

        session = MockSession(temp_session_dir)
        setup = SetupConfig(plugins=["nonexistent-plugin"])

        # Should not raise, just log warning
        item._install_plugins(session, setup)

        # Nothing should be installed
        assert len(item._installed_plugin_files) == 0

    def test_install_plugins_handles_empty_plugins_list(
        self, temp_project_dir: Path, temp_session_dir: Path
    ):
        """Test that empty plugins list is handled correctly."""
        from harness.pytest_plugin import YAMLTestItem
        from harness.fixture_loader import SetupConfig

        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)
            item._installed_plugin_files = []
            item._installed_plugin_dirs = []

        item._find_project_path = lambda: temp_project_dir

        session = MockSession(temp_session_dir)
        setup = SetupConfig(plugins=[])

        # Should return early without error
        item._install_plugins(session, setup)

        # .claude directory should not be created if no plugins
        assert len(item._installed_plugin_files) == 0

    def test_cleanup_plugins_removes_files(
        self, temp_project_dir: Path, temp_session_dir: Path
    ):
        """Test that cleanup removes installed plugin files."""
        from harness.pytest_plugin import YAMLTestItem
        from harness.fixture_loader import SetupConfig

        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)
            item._installed_plugin_files = []
            item._installed_plugin_dirs = []

        item._find_project_path = lambda: temp_project_dir

        session = MockSession(temp_session_dir)
        setup = SetupConfig(plugins=["test-plugin"])

        # Install plugins
        item._install_plugins(session, setup)

        # Verify files exist
        claude_dir = temp_session_dir / ".claude"
        assert (claude_dir / "commands" / "test-command.md").exists()

        # Cleanup
        item._cleanup_plugins()

        # Verify files are removed
        assert not (claude_dir / "commands" / "test-command.md").exists()
        assert not (claude_dir / "agents" / "test-agent.md").exists()

        # Tracking lists should be cleared
        assert len(item._installed_plugin_files) == 0
        assert len(item._installed_plugin_dirs) == 0

    def test_plugin_name_parsing(self):
        """Test that plugin names with @registry suffix are parsed correctly."""
        plugin_specs = [
            ("test-plugin@synaptic-canvas", "test-plugin"),
            ("test-plugin@other-registry", "test-plugin"),
            ("test-plugin", "test-plugin"),
            ("my-pkg@", "my-pkg"),
        ]

        for spec, expected in plugin_specs:
            parsed = spec.split("@")[0]
            assert parsed == expected


# =============================================================================
# TestRunner Plugin Installation Tests
# =============================================================================


class TestRunnerPluginInstallation:
    """Tests for TestRunner._install_plugins and _cleanup_plugins."""

    def test_install_plugins_returns_tracking_lists(
        self, temp_project_dir: Path, temp_session_dir: Path
    ):
        """Test that _install_plugins returns file and dir tracking lists."""
        from harness.runner import TestRunner

        runner = TestRunner(
            project_path=temp_project_dir,
            fixtures_path=temp_project_dir / "fixtures",
        )

        session = MockSession(temp_session_dir)

        files, dirs = runner._install_plugins(session, ["test-plugin"])

        # Should return non-empty lists
        assert len(files) > 0
        assert isinstance(files, list)
        assert isinstance(dirs, list)

    def test_cleanup_plugins_removes_installed_files(
        self, temp_project_dir: Path, temp_session_dir: Path
    ):
        """Test that _cleanup_plugins removes files and directories."""
        from harness.runner import TestRunner

        runner = TestRunner(
            project_path=temp_project_dir,
            fixtures_path=temp_project_dir / "fixtures",
        )

        session = MockSession(temp_session_dir)

        # Install
        files, dirs = runner._install_plugins(session, ["test-plugin"])

        # Verify files exist
        claude_dir = temp_session_dir / ".claude"
        assert (claude_dir / "commands" / "test-command.md").exists()

        # Cleanup
        runner._cleanup_plugins(files, dirs)

        # Verify files are removed
        assert not (claude_dir / "commands" / "test-command.md").exists()

    def test_install_plugins_with_empty_list(self, temp_project_dir: Path, temp_session_dir: Path):
        """Test that empty plugins list returns empty tracking lists."""
        from harness.runner import TestRunner

        runner = TestRunner(
            project_path=temp_project_dir,
            fixtures_path=temp_project_dir / "fixtures",
        )

        session = MockSession(temp_session_dir)

        files, dirs = runner._install_plugins(session, [])

        assert files == []
        assert dirs == []

    def test_install_plugins_missing_packages_dir(self, temp_session_dir: Path):
        """Test handling when packages directory doesn't exist."""
        from harness.runner import TestRunner

        # Use a project without packages directory
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

            runner = TestRunner(
                project_path=project_path,
                fixtures_path=project_path / "fixtures",
            )

            session = MockSession(temp_session_dir)

            # Should not raise, just return empty lists
            files, dirs = runner._install_plugins(session, ["some-plugin"])

            assert files == []
            assert dirs == []


# =============================================================================
# Integration Tests
# =============================================================================


class TestPluginInstallationIntegration:
    """Integration tests for plugin installation during test execution."""

    def test_plugin_artifacts_structure(self, temp_project_dir: Path, temp_session_dir: Path):
        """Test that plugin artifacts maintain their directory structure."""
        from harness.pytest_plugin import YAMLTestItem
        from harness.fixture_loader import SetupConfig

        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)
            item._installed_plugin_files = []
            item._installed_plugin_dirs = []

        item._find_project_path = lambda: temp_project_dir

        session = MockSession(temp_session_dir)
        setup = SetupConfig(plugins=["test-plugin"])

        item._install_plugins(session, setup)

        claude_dir = temp_session_dir / ".claude"

        # Verify directory structure is preserved
        assert (claude_dir / "commands").is_dir()
        assert (claude_dir / "skills" / "test-skill").is_dir()
        assert (claude_dir / "agents").is_dir()

        # Verify files are in correct locations
        assert (claude_dir / "commands" / "test-command.md").is_file()
        assert (claude_dir / "skills" / "test-skill" / "SKILL.md").is_file()
        assert (claude_dir / "agents" / "test-agent.md").is_file()

    def test_multiple_plugins_installation(self, temp_project_dir: Path, temp_session_dir: Path):
        """Test installing multiple plugins."""
        from harness.pytest_plugin import YAMLTestItem
        from harness.fixture_loader import SetupConfig

        # Create a second test plugin
        packages_dir = temp_project_dir / "packages"
        plugin2_dir = packages_dir / "test-plugin-2"
        plugin2_dir.mkdir()

        manifest = {
            "name": "test-plugin-2",
            "version": "1.0.0",
            "artifacts": {
                "commands": ["commands/another-command.md"],
            },
        }
        with open(plugin2_dir / "manifest.yaml", "w") as f:
            yaml.dump(manifest, f)

        (plugin2_dir / "commands").mkdir()
        (plugin2_dir / "commands" / "another-command.md").write_text("# Another Command")

        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)
            item._installed_plugin_files = []
            item._installed_plugin_dirs = []

        item._find_project_path = lambda: temp_project_dir

        session = MockSession(temp_session_dir)
        setup = SetupConfig(plugins=["test-plugin", "test-plugin-2"])

        item._install_plugins(session, setup)

        claude_dir = temp_session_dir / ".claude"

        # Both plugins' artifacts should be installed
        assert (claude_dir / "commands" / "test-command.md").exists()
        assert (claude_dir / "commands" / "another-command.md").exists()
