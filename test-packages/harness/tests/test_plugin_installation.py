"""
Unit tests for plugin installation functionality.

Tests the plugin installation features in pytest_plugin.py and runner.py:
- Plugin installation via sc-install.py subprocess (new method)
- sc-manage deferred installation via Claude invocation
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
    """Tests for YAMLTestItem._install_plugins using sc-install.py subprocess."""

    def test_install_plugins_calls_sc_install(
        self, temp_project_dir: Path, temp_isolated_home: Path
    ):
        """Test that plugin installation uses sc-install.py subprocess."""
        from harness.pytest_plugin import YAMLTestItem
        from harness.fixture_loader import SetupConfig

        # Create a minimal test item
        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)
            item._installed_plugin_files = []
            item._installed_plugin_dirs = []
            item.expected_plugins = []
            item.plugin_install_results = []
            item._sc_manage_install_pending = []
            item.test_config = MagicMock()
            item.test_config.source_path = temp_project_dir

        # Create mock session
        session = MockSession(temp_project_dir, temp_isolated_home)

        # Create setup config with plugins
        setup = SetupConfig(plugins=["test-plugin@synaptic-canvas"])

        # Mock _find_synaptic_canvas_path to return a valid path
        mock_sc_path = temp_project_dir / "synaptic-canvas"
        mock_sc_path.mkdir()
        (mock_sc_path / "tools").mkdir()
        (mock_sc_path / "tools" / "sc-install.py").touch()
        (mock_sc_path / "packages").mkdir()

        # Mock _install_with_sc_install to return success
        with patch.object(item, "_find_synaptic_canvas_path", return_value=mock_sc_path):
            with patch.object(item, "_install_with_sc_install") as mock_sc_install:
                mock_sc_install.return_value = (0, "Installed successfully", "")
                item._install_plugins(session, setup)

        # Verify sc-install was called with extracted package name
        mock_sc_install.assert_called_once_with(
            package_name="test-plugin",
            project_path=session.project_path,
            sc_path=mock_sc_path,
        )

        # Verify tracking list has marker entry
        assert len(item._installed_plugin_files) == 1
        assert "PLUGIN:test-plugin@synaptic-canvas" in str(item._installed_plugin_files[0])

        # Verify plugin install results were recorded
        assert len(item.plugin_install_results) == 1
        assert item.plugin_install_results[0].plugin_name == "test-plugin@synaptic-canvas"
        assert item.plugin_install_results[0].success is True

    def test_install_plugins_handles_sc_install_failure(
        self, temp_project_dir: Path, temp_isolated_home: Path
    ):
        """Test that sc-install.py failures raise PluginInstallationError."""
        from harness.pytest_plugin import YAMLTestItem, PluginInstallationError
        from harness.fixture_loader import SetupConfig

        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)
            item._installed_plugin_files = []
            item._installed_plugin_dirs = []
            item.expected_plugins = []
            item.plugin_install_results = []
            item._sc_manage_install_pending = []
            item.test_config = MagicMock()
            item.test_config.source_path = temp_project_dir

        session = MockSession(temp_project_dir, temp_isolated_home)
        setup = SetupConfig(plugins=["nonexistent-plugin"])

        mock_sc_path = temp_project_dir / "synaptic-canvas"
        mock_sc_path.mkdir()
        (mock_sc_path / "tools").mkdir()
        (mock_sc_path / "tools" / "sc-install.py").touch()
        (mock_sc_path / "packages").mkdir()

        with patch.object(item, "_find_synaptic_canvas_path", return_value=mock_sc_path):
            with patch.object(item, "_install_with_sc_install") as mock_sc_install:
                mock_sc_install.return_value = (1, "", "Package not found: nonexistent-plugin")
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
            item._sc_manage_install_pending = []

        session = MockSession(temp_project_dir, temp_isolated_home)
        setup = SetupConfig(plugins=[])

        # Should return early without calling sc-install
        item._install_plugins(session, setup)

        # No installations
        assert len(item._installed_plugin_files) == 0
        assert len(item.plugin_install_results) == 0

    def test_sc_manage_defers_to_claude_invocation(
        self, temp_project_dir: Path, temp_isolated_home: Path
    ):
        """Test that sc-manage installation is deferred to Claude invocation."""
        from harness.pytest_plugin import YAMLTestItem
        from harness.fixture_loader import SetupConfig

        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)
            item._installed_plugin_files = []
            item._installed_plugin_dirs = []
            item.expected_plugins = []
            item.plugin_install_results = []
            item._sc_manage_install_pending = []
            item.test_config = MagicMock()
            item.test_config.source_path = temp_project_dir

        session = MockSession(temp_project_dir, temp_isolated_home)
        setup = SetupConfig(plugins=["sc-manage@synaptic-canvas"])

        mock_sc_path = temp_project_dir / "synaptic-canvas"
        mock_sc_path.mkdir()
        (mock_sc_path / "tools").mkdir()
        (mock_sc_path / "tools" / "sc-install.py").touch()
        (mock_sc_path / "packages").mkdir()

        with patch.object(item, "_find_synaptic_canvas_path", return_value=mock_sc_path):
            with patch.object(item, "_install_with_sc_install") as mock_sc_install:
                # sc-manage should NOT call _install_with_sc_install
                item._install_plugins(session, setup)
                mock_sc_install.assert_not_called()

        # sc-manage should be in pending list
        assert len(item._sc_manage_install_pending) == 1
        assert item._sc_manage_install_pending[0] == "sc-manage@synaptic-canvas"

        # Should still have a success result (deferred)
        assert len(item.plugin_install_results) == 1
        assert item.plugin_install_results[0].success is True
        assert "Deferred" in item.plugin_install_results[0].stdout

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
            item._sc_manage_install_pending = []
            item.test_config = MagicMock()
            item.test_config.source_path = temp_project_dir

        session = MockSession(temp_project_dir, temp_isolated_home)
        setup = SetupConfig(plugins=["test-plugin"])

        mock_sc_path = temp_project_dir / "synaptic-canvas"
        mock_sc_path.mkdir()
        (mock_sc_path / "tools").mkdir()
        (mock_sc_path / "tools" / "sc-install.py").touch()
        (mock_sc_path / "packages").mkdir()

        with patch.object(item, "_find_synaptic_canvas_path", return_value=mock_sc_path):
            with patch.object(item, "_install_with_sc_install", return_value=(0, "", "")):
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
            item._sc_manage_install_pending = []
            item.test_config = MagicMock()
            item.test_config.source_path = temp_project_dir

        session = MockSession(temp_project_dir, temp_isolated_home)
        setup = SetupConfig(plugins=["plugin-1@registry", "plugin-2@registry"])

        mock_sc_path = temp_project_dir / "synaptic-canvas"
        mock_sc_path.mkdir()
        (mock_sc_path / "tools").mkdir()
        (mock_sc_path / "tools" / "sc-install.py").touch()
        (mock_sc_path / "packages").mkdir()

        sc_install_calls = []

        def mock_install(package_name, project_path, sc_path):
            sc_install_calls.append(package_name)
            return (0, f"Installed {package_name}", "")

        with patch.object(item, "_find_synaptic_canvas_path", return_value=mock_sc_path):
            with patch.object(item, "_install_with_sc_install", side_effect=mock_install):
                item._install_plugins(session, setup)

        # Both plugins should be installed via sc-install
        assert len(sc_install_calls) == 2
        assert sc_install_calls[0] == "plugin-1"
        assert sc_install_calls[1] == "plugin-2"

        # Both should be tracked
        assert len(item._installed_plugin_files) == 2

        # Both install results should be recorded
        assert len(item.plugin_install_results) == 2
        assert all(r.success for r in item.plugin_install_results)

    def test_extract_package_name(self, temp_project_dir: Path):
        """Test the package name extraction helper."""
        from harness.pytest_plugin import YAMLTestItem

        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)

        # Test various formats
        assert item._extract_package_name("sc-startup@synaptic-canvas") == "sc-startup"
        assert item._extract_package_name("sc-manage@registry") == "sc-manage"
        assert item._extract_package_name("plain-plugin") == "plain-plugin"
        assert item._extract_package_name("name@multi@at") == "name"

    def test_find_synaptic_canvas_path_from_env(self, temp_project_dir: Path):
        """Test finding synaptic-canvas path from environment variable."""
        from harness.pytest_plugin import YAMLTestItem
        import os

        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)
            item.test_config = MagicMock()
            item.test_config.source_path = temp_project_dir

        # Create mock synaptic-canvas structure
        mock_sc_path = temp_project_dir / "synaptic-canvas"
        mock_sc_path.mkdir()
        (mock_sc_path / "tools").mkdir()
        (mock_sc_path / "tools" / "sc-install.py").touch()
        (mock_sc_path / "packages").mkdir()

        # Test with environment variable
        with patch.dict(os.environ, {"SC_SYNAPTIC_CANVAS_PATH": str(mock_sc_path)}):
            result = item._find_synaptic_canvas_path()

        assert result is not None
        assert result == mock_sc_path.absolute()

    def test_missing_synaptic_canvas_raises_error(
        self, temp_project_dir: Path, temp_isolated_home: Path
    ):
        """Test that missing synaptic-canvas repo raises error."""
        from harness.pytest_plugin import YAMLTestItem, PluginInstallationError
        from harness.fixture_loader import SetupConfig

        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)
            item._installed_plugin_files = []
            item._installed_plugin_dirs = []
            item.expected_plugins = []
            item.plugin_install_results = []
            item._sc_manage_install_pending = []
            item.test_config = MagicMock()
            item.test_config.source_path = temp_project_dir

        session = MockSession(temp_project_dir, temp_isolated_home)
        setup = SetupConfig(plugins=["test-plugin"])

        # Mock _find_synaptic_canvas_path to return None (not found)
        with patch.object(item, "_find_synaptic_canvas_path", return_value=None):
            with pytest.raises(PluginInstallationError) as exc_info:
                item._install_plugins(session, setup)

        assert exc_info.value.plugin_name == "(all)"
        assert "Could not find synaptic-canvas" in exc_info.value.stderr


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

    def test_sc_install_subprocess_integration(
        self, temp_project_dir: Path, temp_isolated_home: Path
    ):
        """Test that _install_with_sc_install runs subprocess correctly."""
        from harness.pytest_plugin import YAMLTestItem

        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)
            item.test_config = MagicMock()
            item.test_config.source_path = temp_project_dir

        # Create mock synaptic-canvas structure
        mock_sc_path = temp_project_dir / "synaptic-canvas"
        mock_sc_path.mkdir()
        (mock_sc_path / "tools").mkdir()
        (mock_sc_path / "tools" / "sc-install.py").touch()

        # Mock subprocess.run to capture the command
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="Installed", stderr=""
            )

            return_code, stdout, stderr = item._install_with_sc_install(
                package_name="test-plugin",
                project_path=temp_project_dir,
                sc_path=mock_sc_path,
            )

            # Verify subprocess was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            cmd = call_args[0][0]

            # Verify command structure
            assert cmd[0] == "python3"
            assert "sc-install.py" in cmd[1]
            assert "install" in cmd
            assert "test-plugin" in cmd
            assert "--dest" in cmd
            assert "--force" in cmd

            # Verify return values
            assert return_code == 0
            assert stdout == "Installed"

    def test_plugin_name_extraction(self):
        """Test that package names are correctly extracted from plugin specs."""
        from harness.pytest_plugin import YAMLTestItem

        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)

        test_cases = [
            ("test-plugin@synaptic-canvas", "test-plugin"),
            ("test-plugin@other-registry", "test-plugin"),
            ("test-plugin", "test-plugin"),
            ("my-pkg@marketplace", "my-pkg"),
            ("sc-manage@synaptic-canvas", "sc-manage"),
        ]

        for spec, expected_name in test_cases:
            assert item._extract_package_name(spec) == expected_name

    def test_sc_manage_mixed_with_other_plugins(
        self, temp_project_dir: Path, temp_isolated_home: Path
    ):
        """Test that sc-manage is deferred while other plugins install normally."""
        from harness.pytest_plugin import YAMLTestItem
        from harness.fixture_loader import SetupConfig

        with patch.object(YAMLTestItem, "__init__", lambda self, *args, **kwargs: None):
            item = YAMLTestItem.__new__(YAMLTestItem)
            item._installed_plugin_files = []
            item._installed_plugin_dirs = []
            item.expected_plugins = []
            item.plugin_install_results = []
            item._sc_manage_install_pending = []
            item.test_config = MagicMock()
            item.test_config.source_path = temp_project_dir

        session = MockSession(temp_project_dir, temp_isolated_home)
        setup = SetupConfig(plugins=["sc-startup@synaptic-canvas", "sc-manage@synaptic-canvas"])

        mock_sc_path = temp_project_dir / "synaptic-canvas"
        mock_sc_path.mkdir()
        (mock_sc_path / "tools").mkdir()
        (mock_sc_path / "tools" / "sc-install.py").touch()
        (mock_sc_path / "packages").mkdir()

        sc_install_calls = []

        def mock_install(package_name, project_path, sc_path):
            sc_install_calls.append(package_name)
            return (0, f"Installed {package_name}", "")

        with patch.object(item, "_find_synaptic_canvas_path", return_value=mock_sc_path):
            with patch.object(item, "_install_with_sc_install", side_effect=mock_install):
                item._install_plugins(session, setup)

        # sc-startup should be installed via sc-install
        assert "sc-startup" in sc_install_calls
        # sc-manage should NOT be installed via sc-install
        assert "sc-manage" not in sc_install_calls

        # sc-manage should be in pending list
        assert "sc-manage@synaptic-canvas" in item._sc_manage_install_pending

        # Both should be tracked in results
        assert len(item.plugin_install_results) == 2
        assert all(r.success for r in item.plugin_install_results)
