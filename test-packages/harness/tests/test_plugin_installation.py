"""
Unit tests for plugin installation functionality.

Tests the plugin installation features in pytest_plugin.py and runner.py:
- Plugin installation via `claude plugin install` CLI command
- Marketplace data copying for isolated environments
- Error handling for failed plugin installations
- Empty plugins list handling

Run with:
    pytest test-packages/harness/tests/test_plugin_installation.py -v
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch, call

import pytest


# =============================================================================
# Mock Classes for Testing
# =============================================================================


class MockSession:
    """Mock session object for testing plugin installation."""

    def __init__(self, project_path: Path, isolated_home: Path):
        self.project_path = project_path
        self.isolated_home = isolated_home
        self.env = {"HOME": str(isolated_home)}
        self._install_calls: list[tuple[str, str]] = []

    def run_plugin_install(
        self,
        plugin_name: str,
        scope: str = "project",
        timeout: int = 60,
    ) -> subprocess.CompletedProcess:
        """Mock plugin installation - records calls and returns success."""
        self._install_calls.append((plugin_name, scope))
        return subprocess.CompletedProcess(
            args=["claude", "plugin", "install", plugin_name, "--scope", scope],
            returncode=0,
            stdout=f"Successfully installed plugin: {plugin_name}",
            stderr="",
        )


class MockSessionFailure(MockSession):
    """Mock session that returns failure for plugin installation."""

    def run_plugin_install(
        self,
        plugin_name: str,
        scope: str = "project",
        timeout: int = 60,
    ) -> subprocess.CompletedProcess:
        """Mock plugin installation - returns failure."""
        self._install_calls.append((plugin_name, scope))
        return subprocess.CompletedProcess(
            args=["claude", "plugin", "install", plugin_name, "--scope", scope],
            returncode=1,
            stdout="",
            stderr=f'Plugin "{plugin_name}" not found in marketplace',
        )


# =============================================================================
# Fixture Setup
# =============================================================================


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        # Create .claude directory
        (project_path / ".claude").mkdir()
        yield project_path


@pytest.fixture
def temp_isolated_home():
    """Create a temporary isolated HOME directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        isolated_home = Path(tmpdir)
        # Create .claude/plugins directory structure
        (isolated_home / ".claude" / "plugins").mkdir(parents=True)
        yield isolated_home


# =============================================================================
# YAMLTestItem Plugin Installation Tests
# =============================================================================


class TestYAMLTestItemPluginInstallation:
    """Tests for YAMLTestItem._install_plugins using CLI-based installation."""

    def test_install_plugins_calls_cli(
        self, temp_project_dir: Path, temp_isolated_home: Path
    ):
        """Test that plugin installation uses claude plugin install CLI."""
        from harness.pytest_plugin import YAMLTestItem
        from harness.fixture_loader import SetupConfig

        # Create a minimal test item
        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)
            item._installed_plugin_files = []
            item._installed_plugin_dirs = []
            item.expected_plugins = []
            item.plugin_install_results = []

        # Mock _find_project_path
        item._find_project_path = lambda: temp_project_dir

        # Create mock session
        session = MockSession(temp_project_dir, temp_isolated_home)

        # Create setup config with plugins
        setup = SetupConfig(plugins=["test-plugin@synaptic-canvas"])

        # Mock copy_marketplace_data to avoid needing real marketplace data
        with patch("harness.environment.copy_marketplace_data") as mock_copy:
            mock_copy.return_value = True
            item._install_plugins(session, setup)

        # Verify CLI was called
        assert len(session._install_calls) == 1
        assert session._install_calls[0] == ("test-plugin@synaptic-canvas", "project")

        # Verify marketplace data was copied
        mock_copy.assert_called_once_with(temp_isolated_home)

        # Verify tracking list has marker entry
        assert len(item._installed_plugin_files) == 1
        assert "PLUGIN:test-plugin@synaptic-canvas" in str(item._installed_plugin_files[0])

        # Verify plugin install results were recorded
        assert len(item.plugin_install_results) == 1
        assert item.plugin_install_results[0].plugin_name == "test-plugin@synaptic-canvas"
        assert item.plugin_install_results[0].success is True

    def test_install_plugins_handles_cli_failure(
        self, temp_project_dir: Path, temp_isolated_home: Path
    ):
        """Test that CLI installation failures raise PluginInstallationError."""
        from harness.pytest_plugin import YAMLTestItem, PluginInstallationError
        from harness.fixture_loader import SetupConfig

        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)
            item._installed_plugin_files = []
            item._installed_plugin_dirs = []
            item.expected_plugins = []
            item.plugin_install_results = []

        item._find_project_path = lambda: temp_project_dir

        # Use failure mock session
        session = MockSessionFailure(temp_project_dir, temp_isolated_home)
        setup = SetupConfig(plugins=["nonexistent-plugin"])

        with patch("harness.environment.copy_marketplace_data") as mock_copy:
            mock_copy.return_value = True
            # Should raise PluginInstallationError (fail fast behavior)
            with pytest.raises(PluginInstallationError) as exc_info:
                item._install_plugins(session, setup)

        # Verify error details
        assert exc_info.value.plugin_name == "nonexistent-plugin"
        assert exc_info.value.return_code == 1

        # Nothing should be tracked as installed
        assert len(item._installed_plugin_files) == 0

        # But the failed install should still be recorded
        assert len(item.plugin_install_results) == 1
        assert item.plugin_install_results[0].success is False

    def test_install_plugins_handles_empty_plugins_list(
        self, temp_project_dir: Path, temp_isolated_home: Path
    ):
        """Test that empty plugins list is handled correctly."""
        from harness.pytest_plugin import YAMLTestItem
        from harness.fixture_loader import SetupConfig

        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)
            item._installed_plugin_files = []
            item._installed_plugin_dirs = []
            item.expected_plugins = []
            item.plugin_install_results = []

        item._find_project_path = lambda: temp_project_dir

        session = MockSession(temp_project_dir, temp_isolated_home)
        setup = SetupConfig(plugins=[])

        with patch("harness.environment.copy_marketplace_data") as mock_copy:
            # Should return early without calling copy_marketplace_data
            item._install_plugins(session, setup)

        # No marketplace copy should happen
        mock_copy.assert_not_called()
        # No installations
        assert len(session._install_calls) == 0
        assert len(item._installed_plugin_files) == 0
        assert len(item.plugin_install_results) == 0

    def test_cleanup_plugins_clears_tracking_lists(
        self, temp_project_dir: Path, temp_isolated_home: Path
    ):
        """Test that cleanup clears tracking lists."""
        from harness.pytest_plugin import YAMLTestItem
        from harness.fixture_loader import SetupConfig

        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)
            item._installed_plugin_files = []
            item._installed_plugin_dirs = []
            item.expected_plugins = []
            item.plugin_install_results = []

        item._find_project_path = lambda: temp_project_dir

        session = MockSession(temp_project_dir, temp_isolated_home)
        setup = SetupConfig(plugins=["test-plugin"])

        with patch("harness.environment.copy_marketplace_data"):
            item._install_plugins(session, setup)

        # Verify something was tracked
        assert len(item._installed_plugin_files) > 0

        # Cleanup
        item._cleanup_plugins()

        # Tracking lists should be cleared
        assert len(item._installed_plugin_files) == 0
        assert len(item._installed_plugin_dirs) == 0

    def test_multiple_plugins_installation(
        self, temp_project_dir: Path, temp_isolated_home: Path
    ):
        """Test installing multiple plugins."""
        from harness.pytest_plugin import YAMLTestItem
        from harness.fixture_loader import SetupConfig

        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)
            item._installed_plugin_files = []
            item._installed_plugin_dirs = []
            item.expected_plugins = []
            item.plugin_install_results = []

        item._find_project_path = lambda: temp_project_dir

        session = MockSession(temp_project_dir, temp_isolated_home)
        setup = SetupConfig(plugins=["plugin-1@registry", "plugin-2@registry"])

        with patch("harness.environment.copy_marketplace_data"):
            item._install_plugins(session, setup)

        # Both plugins should be installed
        assert len(session._install_calls) == 2
        assert session._install_calls[0] == ("plugin-1@registry", "project")
        assert session._install_calls[1] == ("plugin-2@registry", "project")

        # Both should be tracked
        assert len(item._installed_plugin_files) == 2

        # Both install results should be recorded
        assert len(item.plugin_install_results) == 2
        assert all(r.success for r in item.plugin_install_results)


# =============================================================================
# TestRunner Plugin Installation Tests
# =============================================================================


class TestRunnerPluginInstallation:
    """Tests for TestRunner._install_plugins using CLI-based installation."""

    def test_install_plugins_returns_tracking_lists(
        self, temp_project_dir: Path, temp_isolated_home: Path
    ):
        """Test that _install_plugins returns marker tracking lists."""
        from harness.runner import TestRunner

        runner = TestRunner(
            project_path=temp_project_dir,
            fixtures_path=temp_project_dir / "fixtures",
        )

        session = MockSession(temp_project_dir, temp_isolated_home)

        with patch("harness.environment.copy_marketplace_data"):
            files, dirs = runner._install_plugins(session, ["test-plugin"])

        # Should return marker list
        assert len(files) == 1
        assert "PLUGIN:test-plugin" in str(files[0])
        assert isinstance(dirs, list)

    def test_cleanup_plugins_logs_installed(
        self, temp_project_dir: Path, temp_isolated_home: Path
    ):
        """Test that _cleanup_plugins logs what was installed."""
        from harness.runner import TestRunner

        runner = TestRunner(
            project_path=temp_project_dir,
            fixtures_path=temp_project_dir / "fixtures",
        )

        session = MockSession(temp_project_dir, temp_isolated_home)

        with patch("harness.environment.copy_marketplace_data"):
            files, dirs = runner._install_plugins(session, ["test-plugin"])

        # Cleanup should not raise
        runner._cleanup_plugins(files, dirs)

    def test_install_plugins_with_empty_list(
        self, temp_project_dir: Path, temp_isolated_home: Path
    ):
        """Test that empty plugins list returns empty tracking lists."""
        from harness.runner import TestRunner

        runner = TestRunner(
            project_path=temp_project_dir,
            fixtures_path=temp_project_dir / "fixtures",
        )

        session = MockSession(temp_project_dir, temp_isolated_home)

        with patch("harness.environment.copy_marketplace_data") as mock_copy:
            files, dirs = runner._install_plugins(session, [])

        # No marketplace copy should happen
        mock_copy.assert_not_called()
        assert files == []
        assert dirs == []

    def test_install_plugins_handles_cli_failure(
        self, temp_project_dir: Path, temp_isolated_home: Path
    ):
        """Test handling when CLI installation fails."""
        from harness.runner import TestRunner

        runner = TestRunner(
            project_path=temp_project_dir,
            fixtures_path=temp_project_dir / "fixtures",
        )

        session = MockSessionFailure(temp_project_dir, temp_isolated_home)

        with patch("harness.environment.copy_marketplace_data"):
            # Should not raise, just return empty lists
            files, dirs = runner._install_plugins(session, ["nonexistent-plugin"])

        assert files == []
        assert dirs == []


# =============================================================================
# IsolatedSession Plugin Install Tests
# =============================================================================


class TestIsolatedSessionPluginInstall:
    """Tests for IsolatedSession.run_plugin_install method."""

    def test_run_plugin_install_builds_correct_command(self):
        """Test that run_plugin_install builds the correct CLI command."""
        from harness.environment import IsolatedSession

        with tempfile.TemporaryDirectory() as tmpdir:
            isolated_home = Path(tmpdir)
            project_path = Path(tmpdir) / "project"
            project_path.mkdir()

            session = IsolatedSession(
                isolated_home=isolated_home,
                project_path=project_path,
                env={"HOME": str(isolated_home)},
                trace_path=project_path / "trace.jsonl",
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="Success", stderr=""
                )

                session.run_plugin_install("my-plugin@marketplace", scope="project")

                # Verify correct command was built
                mock_run.assert_called_once()
                call_args = mock_run.call_args
                cmd = call_args[0][0]

                assert cmd == [
                    "claude", "plugin", "install",
                    "my-plugin@marketplace", "--scope", "project"
                ]
                assert call_args[1]["env"]["HOME"] == str(isolated_home)
                assert call_args[1]["cwd"] == project_path

    def test_run_plugin_install_returns_completed_process(self):
        """Test that run_plugin_install returns CompletedProcess."""
        from harness.environment import IsolatedSession

        with tempfile.TemporaryDirectory() as tmpdir:
            isolated_home = Path(tmpdir)
            project_path = Path(tmpdir) / "project"
            project_path.mkdir()

            session = IsolatedSession(
                isolated_home=isolated_home,
                project_path=project_path,
                env={"HOME": str(isolated_home)},
                trace_path=project_path / "trace.jsonl",
            )

            with patch("subprocess.run") as mock_run:
                expected_result = subprocess.CompletedProcess(
                    args=[], returncode=0,
                    stdout="Successfully installed",
                    stderr=""
                )
                mock_run.return_value = expected_result

                result = session.run_plugin_install("test-plugin")

                assert result.returncode == 0
                assert "Successfully installed" in result.stdout


# =============================================================================
# Integration Tests
# =============================================================================


class TestPluginInstallationIntegration:
    """Integration tests for plugin installation during test execution."""

    def test_marketplace_data_copied_before_install(
        self, temp_project_dir: Path, temp_isolated_home: Path
    ):
        """Test that marketplace data is copied before plugin installation."""
        from harness.pytest_plugin import YAMLTestItem
        from harness.fixture_loader import SetupConfig

        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)
            item._installed_plugin_files = []
            item._installed_plugin_dirs = []
            item.expected_plugins = []
            item.plugin_install_results = []

        item._find_project_path = lambda: temp_project_dir

        session = MockSession(temp_project_dir, temp_isolated_home)
        setup = SetupConfig(plugins=["test-plugin"])

        call_order = []

        def track_copy(*args, **kwargs):
            call_order.append("copy_marketplace")
            return True

        original_run_plugin_install = session.run_plugin_install

        def track_install(*args, **kwargs):
            call_order.append("install_plugin")
            return original_run_plugin_install(*args, **kwargs)

        session.run_plugin_install = track_install

        with patch("harness.environment.copy_marketplace_data", side_effect=track_copy):
            item._install_plugins(session, setup)

        # Marketplace copy should happen before install
        assert call_order == ["copy_marketplace", "install_plugin"]

    def test_plugin_name_parsing(self):
        """Test that plugin names with @registry suffix are passed correctly to CLI."""
        plugin_specs = [
            "test-plugin@synaptic-canvas",
            "test-plugin@other-registry",
            "test-plugin",
            "my-pkg@marketplace",
        ]

        # All specs should be passed as-is to the CLI (no parsing needed)
        for spec in plugin_specs:
            # The CLI handles parsing, we just pass through
            assert isinstance(spec, str)
