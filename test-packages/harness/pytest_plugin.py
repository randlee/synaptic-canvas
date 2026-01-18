"""
Pytest plugin for dynamic test generation from YAML fixtures.

This module provides pytest integration that:
- Discovers YAML test fixtures from the fixtures directory
- Generates pytest test cases dynamically from fixture definitions
- Hooks into the existing runner infrastructure for execution
- Supports test filtering by tags and test IDs
- Generates HTML reports after test runs

Usage:
    # Run all fixture tests
    pytest test-packages/fixtures/ -v

    # Run specific fixture
    pytest test-packages/fixtures/sc-startup/ -v

    # Run by tag
    pytest test-packages/fixtures/ -v -k "readonly"

    # Run by test ID
    pytest test-packages/fixtures/ -v -k "sc-startup-001"

    # Generate and open HTML report
    pytest test-packages/fixtures/ -v --open-report

    # Open report only on failure
    pytest test-packages/fixtures/ -v --open-on-fail

Configuration:
    The plugin is registered via conftest.py and uses the following pytest hooks:
    - pytest_collect_file: Discovers fixture.yaml files
    - pytest_collection_modifyitems: Adds markers to test items
    - pytest_runtest_makereport: Captures test results for reporting
    - pytest_sessionfinish: Generates HTML reports

Based on the fixture design from:
- docs/requirements/test-harness-design-spec.md (Section 7)
"""

from __future__ import annotations

import logging
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

import pytest

from .fixture_loader import FixtureConfig, FixtureLoader, TestConfig
from .models import TestStatus

if TYPE_CHECKING:
    from _pytest.config import Config
    from _pytest.nodes import Collector
    from _pytest.reports import TestReport

logger = logging.getLogger(__name__)


# =============================================================================
# Report State Storage
# =============================================================================


class TestReportState:
    """Stores test execution data for HTML report generation.

    This class accumulates test results during a pytest session and provides
    them for HTML report generation in pytest_sessionfinish.
    """
    __test__ = False  # Prevent pytest collection

    def __init__(self):
        """Initialize empty state."""
        self.reset()

    def reset(self):
        """Reset all stored state."""
        # Map: fixture_name -> list of test results
        self._test_results: dict[str, list[dict]] = {}
        # Map: fixture_name -> FixtureConfig
        self._fixture_configs: dict[str, FixtureConfig] = {}
        # Track if any tests failed
        self._has_failures = False
        # Session start time
        self._session_start: datetime | None = None

    def record_fixture_config(self, fixture_name: str, config: FixtureConfig):
        """Record a fixture configuration.

        Args:
            fixture_name: Name of the fixture
            config: FixtureConfig for the fixture
        """
        if fixture_name not in self._fixture_configs:
            self._fixture_configs[fixture_name] = config

    def record_test_result(
        self,
        fixture_name: str,
        test_id: str,
        test_config: TestConfig,
        passed: bool,
        collected_data: Any | None = None,
        expectations: list | None = None,
        duration_ms: float = 0,
        error_message: str | None = None,
        pytest_output: str = "",
        expected_plugins: list[str] | None = None,
        plugin_install_results: list | None = None,
    ):
        """Record a test result.

        Args:
            fixture_name: Name of the parent fixture
            test_id: Test identifier
            test_config: Test configuration
            passed: Whether the test passed
            collected_data: CollectedData from DataCollector
            expectations: List of evaluated Expectation objects
            duration_ms: Test duration in milliseconds
            error_message: Optional error message
            pytest_output: Raw pytest output
            expected_plugins: List of expected plugin names from fixture setup
            plugin_install_results: List of PluginInstallResult objects
        """
        if fixture_name not in self._test_results:
            self._test_results[fixture_name] = []

        if not passed:
            self._has_failures = True

        self._test_results[fixture_name].append({
            "test_id": test_id,
            "test_config": test_config,
            "passed": passed,
            "collected_data": collected_data,
            "expectations": expectations or [],
            "duration_ms": duration_ms,
            "error_message": error_message,
            "pytest_output": pytest_output,
            "expected_plugins": expected_plugins or [],
            "plugin_install_results": plugin_install_results or [],
        })

    @property
    def has_failures(self) -> bool:
        """Return True if any tests failed."""
        return self._has_failures

    @property
    def fixture_names(self) -> list[str]:
        """Return list of fixture names with test results."""
        return list(self._test_results.keys())

    def get_fixture_config(self, fixture_name: str) -> FixtureConfig | None:
        """Get fixture configuration by name."""
        return self._fixture_configs.get(fixture_name)

    def get_test_results(self, fixture_name: str) -> list[dict]:
        """Get test results for a fixture."""
        return self._test_results.get(fixture_name, [])


# Global state instance (per pytest session)
_report_state = TestReportState()


# =============================================================================
# Pytest Custom Nodes
# =============================================================================


class YAMLFixtureFile(pytest.File):
    """Represents a fixture.yaml file for pytest collection.

    This collector discovers and creates test items from the fixture
    and its associated test files.
    """

    def collect(self) -> Iterator["YAMLTestItem"]:
        """Collect test items from the fixture.

        Yields:
            YAMLTestItem instances for each test in the fixture
        """
        try:
            fixture_config = FixtureConfig.from_yaml(self.path, load_tests=True)
        except Exception as e:
            logger.error(f"Failed to load fixture {self.path}: {e}")
            return

        for test_config in fixture_config.tests:
            yield YAMLTestItem.from_parent(
                self,
                name=test_config.test_id,
                fixture_config=fixture_config,
                test_config=test_config,
            )


class YAMLTestFile(pytest.File):
    """Represents a single test_*.yaml file for pytest collection.

    Used when running a specific test file directly.
    """

    def collect(self) -> Iterator["YAMLTestItem"]:
        """Collect the test item from this YAML file.

        Yields:
            Single YAMLTestItem for the test
        """
        # Find the parent fixture.yaml
        fixture_yaml = self.path.parent.parent / "fixture.yaml"
        if not fixture_yaml.exists():
            # Check if we're at the fixture level (test_*.yaml next to fixture.yaml)
            fixture_yaml = self.path.parent / "fixture.yaml"

        try:
            if fixture_yaml.exists():
                fixture_config = FixtureConfig.from_yaml(fixture_yaml, load_tests=False)
            else:
                # Create minimal fixture config
                fixture_config = FixtureConfig(
                    name=self.path.parent.name,
                    source_path=self.path.parent / "fixture.yaml",
                )

            test_config = TestConfig.from_yaml(self.path)

            yield YAMLTestItem.from_parent(
                self,
                name=test_config.test_id,
                fixture_config=fixture_config,
                test_config=test_config,
            )
        except Exception as e:
            logger.error(f"Failed to load test {self.path}: {e}")


class YAMLTestItem(pytest.Item):
    """Represents a single test case from YAML configuration.

    This is the actual test that gets executed by pytest.
    """

    def __init__(
        self,
        name: str,
        parent: pytest.Collector,
        fixture_config: FixtureConfig,
        test_config: TestConfig,
    ):
        """Initialize the test item.

        Args:
            name: Test name (usually test_id)
            parent: Parent collector
            fixture_config: Fixture configuration
            test_config: Test configuration
        """
        super().__init__(name, parent)
        self.fixture_config = fixture_config
        self.test_config = test_config

        # Execution result storage (populated during runtest)
        self.collected_data = None
        self.evaluated_expectations: list = []
        self.execution_start: datetime | None = None
        self.execution_duration_ms: float = 0
        self.execution_error: str | None = None

        # Claude CLI output capture (populated during runtest)
        self.claude_stdout: str = ""
        self.claude_stderr: str = ""

        # Track installed plugin files for cleanup
        self._installed_plugin_files: list[Path] = []
        self._installed_plugin_dirs: list[Path] = []

        # Plugin installation tracking
        self.expected_plugins: list[str] = []
        self.plugin_install_results: list = []  # List of PluginInstallResult

        # Deferred sc-manage installation (for self-testing sc-manage package)
        self._sc_manage_install_pending: list[str] = []

        # Add markers for tags
        for tag in test_config.tags:
            self.add_marker(pytest.mark.keyword(tag))

        # Add skip marker if test is marked as skip
        if test_config.skip:
            self.add_marker(pytest.mark.skip(reason=test_config.skip_reason or "Marked as skip in YAML"))

    def runtest(self) -> None:
        """Run the test using the harness infrastructure.

        This method executes the test using the isolated_claude_session
        and collects results via the DataCollector.

        Raises:
            YAMLTestFailure: If the test fails expectations
        """
        from .collector import DataCollector
        from .environment import isolated_claude_session
        from .reporter import ExpectationEvaluator

        # Get project path (assume it's a few levels up from the fixture)
        project_path = self._find_project_path()

        # Get merged setup from fixture and test
        merged_setup = self.fixture_config.get_merged_setup(self.test_config)

        # Track execution timing
        self.execution_start = datetime.now()
        start_time = time.time()

        # Register fixture config for report generation
        _report_state.record_fixture_config(
            self.fixture_config.name,
            self.fixture_config
        )

        try:
            with isolated_claude_session(
                project_path=project_path,
                trace_path=project_path / "reports" / "trace.jsonl",
            ) as session:
                # Install plugins before setup commands
                self._install_plugins(session, merged_setup)

                # Run setup commands
                self._run_setup_commands(session, merged_setup)

                # Build the prompt, prepending sc-manage install if needed
                prompt = self.test_config.execution.prompt
                if hasattr(self, "_sc_manage_install_pending") and self._sc_manage_install_pending:
                    # Prepend sc-manage install commands for each pending package
                    install_commands = []
                    for pkg_spec in self._sc_manage_install_pending:
                        pkg_name = self._extract_package_name(pkg_spec)
                        install_commands.append(f"/sc-manage --install {pkg_name} --local")
                    install_prefix = " ".join(install_commands) + " && "
                    prompt = install_prefix + prompt
                    logger.info(f"Prepending sc-manage install to prompt: {install_commands}")

                # Execute the test
                result = session.run_command(
                    prompt=prompt,
                    model=self.test_config.execution.model,
                    tools=self.test_config.execution.tools or None,
                    timeout=self.test_config.execution.timeout_ms // 1000,
                )

                # Capture Claude CLI output immediately after run_command
                self.claude_stdout = session.claude_stdout
                self.claude_stderr = session.claude_stderr

                # Find transcript
                session.find_transcript()

                # Collect data
                collector = DataCollector(
                    trace_path=session.trace_path,
                    transcript_path=session.transcript_path,
                )
                self.collected_data = collector.collect()

                # Propagate Claude CLI output to collected data for reports
                self.collected_data.claude_cli_stdout = self.claude_stdout
                self.collected_data.claude_cli_stderr = self.claude_stderr

                # Evaluate expectations
                evaluator = ExpectationEvaluator(self.collected_data)
                failures = []

                for exp_config in self.test_config.expectations:
                    from .models import ExpectationType

                    exp_type = ExpectationType(exp_config.type)
                    expectation = evaluator.evaluate(
                        expectation_id=exp_config.id,
                        expectation_type=exp_type,
                        description=exp_config.description,
                        expected=exp_config.expected,
                    )

                    self.evaluated_expectations.append(expectation)

                    if expectation.status != TestStatus.PASS:
                        failures.append(expectation)

                # Record duration
                self.execution_duration_ms = (time.time() - start_time) * 1000

                if failures:
                    raise YAMLTestFailure(self.test_config, failures)

        except YAMLTestFailure:
            self.execution_duration_ms = (time.time() - start_time) * 1000
            raise
        except Exception as e:
            self.execution_duration_ms = (time.time() - start_time) * 1000
            self.execution_error = str(e)
            raise YAMLTestFailure(
                self.test_config,
                [],
                error_message=str(e),
            ) from e
        finally:
            # Clean up installed plugins
            self._cleanup_plugins()
            # Run teardown commands
            self._run_teardown_commands(merged_setup)

    def _find_project_path(self) -> Path:
        """Find the test harness project path for isolated test execution.

        Tests should execute IN sc-test-harness to use its hooks configuration.
        The sc-test-harness contains:
        - .claude/settings.json with hook configuration
        - scripts/log-hook.py for event capture
        - reports/ directory for trace.jsonl

        Resolution order:
        1. SC_TEST_HARNESS_PATH environment variable (if set)
        2. ../sc-test-harness relative to synaptic-canvas root

        Returns:
            Path to sc-test-harness project root

        Raises:
            FileNotFoundError: If sc-test-harness cannot be located
        """
        import os

        # 1. Check environment variable override
        env_path = os.environ.get("SC_TEST_HARNESS_PATH")
        if env_path:
            harness_path = Path(env_path)
            if harness_path.exists() and (harness_path / ".claude").exists():
                logger.debug(f"Using SC_TEST_HARNESS_PATH: {harness_path}")
                return harness_path.absolute()
            else:
                logger.warning(
                    f"SC_TEST_HARNESS_PATH set but invalid: {env_path}"
                )

        # 2. Find synaptic-canvas root, then look for sibling sc-test-harness
        current = self.test_config.source_path or self.fspath
        if current is None:
            current = Path.cwd()
        else:
            current = Path(current)

        # Walk up to find synaptic-canvas root
        # Detection methods:
        # 1. pyproject.toml + test-packages (main repo)
        # 2. .claude + test-packages (worktrees)
        # 3. Name starts with 'synaptic-canvas' + test-packages
        synaptic_canvas_root = None
        for parent in [current] + list(current.parents):
            if (parent / "pyproject.toml").exists() and (parent / "test-packages").exists():
                synaptic_canvas_root = parent
                break
            # Check for worktree structure (no pyproject.toml but has .claude and test-packages)
            if (parent / ".claude").exists() and (parent / "test-packages").exists():
                synaptic_canvas_root = parent
                break
            # Also check for worktree by name pattern
            if parent.name.startswith("synaptic-canvas") and (parent / "test-packages").exists():
                synaptic_canvas_root = parent
                break

        if synaptic_canvas_root:
            # Look for sc-test-harness as sibling
            harness_path = synaptic_canvas_root.parent / "sc-test-harness"
            if harness_path.exists() and (harness_path / ".claude").exists():
                logger.debug(f"Found sc-test-harness at: {harness_path}")
                return harness_path.absolute()

            # Also check for worktrees structure: parent might be 'github' with sc-test-harness sibling
            # e.g., /github/synaptic-canvas-worktrees/feature/xyz -> /github/sc-test-harness
            for ancestor in synaptic_canvas_root.parents:
                harness_path = ancestor / "sc-test-harness"
                if harness_path.exists() and (harness_path / ".claude").exists():
                    logger.debug(f"Found sc-test-harness in ancestor: {harness_path}")
                    return harness_path.absolute()

        # Fallback: try common development layouts
        # Check if we're in a worktree and sc-test-harness is in the main github folder
        for parent in [current] + list(current.parents):
            if parent.name == "github":
                harness_path = parent / "sc-test-harness"
                if harness_path.exists() and (harness_path / ".claude").exists():
                    logger.debug(f"Found sc-test-harness in github folder: {harness_path}")
                    return harness_path.absolute()
                break

        # If still not found, raise an error with helpful message
        raise FileNotFoundError(
            "Could not locate sc-test-harness. Set SC_TEST_HARNESS_PATH environment "
            "variable or ensure sc-test-harness exists as a sibling to synaptic-canvas. "
            f"Searched from: {current}"
        )

    def _run_setup_commands(self, session: Any, setup: Any) -> None:
        """Run setup commands in the isolated session.

        Args:
            session: IsolatedSession instance
            setup: SetupConfig with commands to run
        """
        import subprocess

        for cmd in setup.commands:
            try:
                subprocess.run(
                    cmd,
                    shell=True,
                    cwd=session.project_path,
                    env=session.env,
                    check=False,
                    capture_output=True,
                )
            except Exception as e:
                logger.warning(f"Setup command failed: {cmd} - {e}")

    def _run_teardown_commands(self, setup: Any) -> None:
        """Run teardown commands.

        Args:
            setup: SetupConfig (used to access teardown if needed)
        """
        import subprocess

        for cmd in self.fixture_config.teardown.commands:
            try:
                subprocess.run(
                    cmd,
                    shell=True,
                    check=False,
                    capture_output=True,
                )
            except Exception as e:
                logger.warning(f"Teardown command failed: {cmd} - {e}")


    def _find_synaptic_canvas_path(self) -> Path | None:
        """Find the synaptic-canvas repository path for sc-install.py.

        Resolution order:
        1. SC_SYNAPTIC_CANVAS_PATH environment variable (if set)
        2. Find relative to the test fixture location (sibling or parent)

        Returns:
            Path to synaptic-canvas repo root, or None if not found
        """
        import os

        # 1. Check environment variable override
        env_path = os.environ.get("SC_SYNAPTIC_CANVAS_PATH")
        if env_path:
            sc_path = Path(env_path)
            if sc_path.exists() and (sc_path / "tools" / "sc-install.py").exists():
                logger.debug(f"Using SC_SYNAPTIC_CANVAS_PATH: {sc_path}")
                return sc_path.absolute()
            else:
                logger.warning(
                    f"SC_SYNAPTIC_CANVAS_PATH set but invalid or missing sc-install.py: {env_path}"
                )

        # 2. Find relative to fixture location
        current = self.test_config.source_path or self.fspath
        if current is None:
            current = Path.cwd()
        else:
            current = Path(current)

        # Walk up to find synaptic-canvas root with tools/sc-install.py
        for parent in [current] + list(current.parents):
            # Check for synaptic-canvas indicators with sc-install.py
            sc_install = parent / "tools" / "sc-install.py"
            if sc_install.exists() and (parent / "packages").exists():
                logger.debug(f"Found synaptic-canvas at: {parent}")
                return parent.absolute()

            # Also check for worktree or sibling patterns
            # e.g., synaptic-canvas-worktrees/feature/xyz -> look for tools/sc-install.py
            if parent.name.startswith("synaptic-canvas") or "synaptic-canvas" in str(parent):
                if sc_install.exists():
                    logger.debug(f"Found synaptic-canvas worktree at: {parent}")
                    return parent.absolute()

        # 3. Check if there's a sibling synaptic-canvas directory
        for parent in [current] + list(current.parents):
            sibling = parent / "synaptic-canvas"
            if sibling.exists() and (sibling / "tools" / "sc-install.py").exists():
                logger.debug(f"Found synaptic-canvas as sibling at: {sibling}")
                return sibling.absolute()

        logger.warning("Could not find synaptic-canvas repo with tools/sc-install.py")
        return None

    def _extract_package_name(self, plugin_spec: str) -> str:
        """Extract the package name from a plugin specification.

        Args:
            plugin_spec: Plugin spec like "sc-startup@synaptic-canvas" or "sc-startup"

        Returns:
            Package name (e.g., "sc-startup")
        """
        # Handle formats like "sc-startup@synaptic-canvas" or just "sc-startup"
        if "@" in plugin_spec:
            return plugin_spec.split("@")[0]
        return plugin_spec

    def _install_with_sc_install(
        self,
        package_name: str,
        project_path: Path,
        sc_path: Path,
    ) -> tuple[int, str, str]:
        """Install a plugin using sc-install.py directly via subprocess.

        Args:
            package_name: Name of the package to install (e.g., "sc-startup")
            project_path: Path to the test project (destination for .claude)
            sc_path: Path to the synaptic-canvas repo containing sc-install.py

        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        import subprocess

        sc_install_script = sc_path / "tools" / "sc-install.py"
        dest_claude = project_path / ".claude"

        cmd = [
            "python3",
            str(sc_install_script),
            "install",
            package_name,
            "--dest",
            str(dest_claude),
            "--force",  # Allow overwriting existing files
        ]

        logger.info(f"Installing plugin via sc-install.py: {package_name}")
        logger.debug(f"sc-install command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(sc_path),  # Run from synaptic-canvas repo for proper path resolution
            )

            if result.returncode == 0:
                logger.info(f"Successfully installed plugin via sc-install: {package_name}")
            else:
                logger.warning(
                    f"sc-install failed for {package_name}: "
                    f"returncode={result.returncode}, stderr={result.stderr}"
                )

            return result.returncode, result.stdout or "", result.stderr or ""

        except subprocess.TimeoutExpired:
            logger.error(f"sc-install timed out for {package_name}")
            return -1, "", "Installation timed out after 60 seconds"
        except Exception as e:
            logger.error(f"sc-install failed for {package_name}: {e}")
            return -1, "", str(e)

    def _install_plugins(self, session: Any, setup: Any) -> None:
        """Install plugins specified in setup configuration.

        For most packages: Uses sc-install.py directly via subprocess for
        reliable installation in isolated environments.

        For sc-manage package: Sets a flag to use Claude invocation with
        `/sc-manage --install <package> --local` for self-testing.

        Args:
            session: IsolatedSession instance
            setup: SetupConfig with plugins list

        Raises:
            PluginInstallationError: If any plugin fails to install
        """
        from .models import PluginInstallResult

        if not setup.plugins:
            return

        # Store expected plugins for reporting
        self.expected_plugins = list(setup.plugins)

        # Find synaptic-canvas repo for sc-install.py
        sc_path = self._find_synaptic_canvas_path()
        if sc_path is None:
            raise PluginInstallationError(
                plugin_name="(all)",
                return_code=-1,
                stdout="",
                stderr="Could not find synaptic-canvas repo with tools/sc-install.py. "
                       "Set SC_SYNAPTIC_CANVAS_PATH environment variable.",
            )

        # Track if sc-manage needs to be installed via Claude invocation
        self._sc_manage_install_pending: list[str] = []

        for plugin_spec in setup.plugins:
            package_name = self._extract_package_name(plugin_spec)
            stdout = ""
            stderr = ""
            return_code = -1

            try:
                if package_name == "sc-manage":
                    # For sc-manage, defer to Claude invocation for self-testing
                    # Store the package spec for later use in runtest()
                    self._sc_manage_install_pending.append(plugin_spec)
                    logger.info(
                        f"Deferring sc-manage installation to Claude invocation: {plugin_spec}"
                    )

                    # Create a successful install result (will actually install via Claude)
                    install_result = PluginInstallResult(
                        plugin_name=plugin_spec,
                        success=True,
                        stdout="Deferred to Claude /sc-manage --install invocation",
                        stderr="",
                        return_code=0,
                    )
                    self.plugin_install_results.append(install_result)
                    self._installed_plugin_files.append(
                        Path(f"PLUGIN:{plugin_spec}")
                    )
                    continue

                # For all other packages, use sc-install.py directly
                return_code, stdout, stderr = self._install_with_sc_install(
                    package_name=package_name,
                    project_path=session.project_path,
                    sc_path=sc_path,
                )

                # Create install result for reporting
                install_result = PluginInstallResult(
                    plugin_name=plugin_spec,
                    success=(return_code == 0),
                    stdout=stdout,
                    stderr=stderr,
                    return_code=return_code,
                )
                self.plugin_install_results.append(install_result)

                if return_code == 0:
                    logger.info(f"Installed plugin via sc-install: {plugin_spec}")
                    logger.debug(f"Plugin install stdout: {stdout}")
                    # Track that we installed this plugin (for observability)
                    self._installed_plugin_files.append(
                        Path(f"PLUGIN:{plugin_spec}")  # Marker for installed plugins
                    )
                else:
                    logger.error(
                        f"Failed to install plugin {plugin_spec}: "
                        f"returncode={return_code}, stderr={stderr}"
                    )
                    # Fail fast - raise immediately on plugin installation failure
                    raise PluginInstallationError(
                        plugin_name=plugin_spec,
                        return_code=return_code,
                        stdout=stdout,
                        stderr=stderr,
                    )

            except PluginInstallationError:
                # Re-raise plugin installation errors
                raise
            except Exception as e:
                # Create install result for reporting on unexpected errors
                install_result = PluginInstallResult(
                    plugin_name=plugin_spec,
                    success=False,
                    stdout=stdout,
                    stderr=str(e),
                    return_code=return_code,
                )
                self.plugin_install_results.append(install_result)

                logger.error(f"Failed to install plugin {plugin_spec}: {e}")
                # Fail fast on any plugin installation error
                raise PluginInstallationError(
                    plugin_name=plugin_spec,
                    return_code=return_code,
                    stdout=stdout,
                    stderr=str(e),
                ) from e

    def _cleanup_plugins(self) -> None:
        """Log installed plugins for observability.

        Since plugins are now installed via `claude plugin install` into the
        isolated HOME directory, cleanup happens automatically when the isolated
        session is cleaned up. This method now just logs what was installed.
        """
        # Log installed plugins for observability
        for entry in self._installed_plugin_files:
            entry_str = str(entry)
            if entry_str.startswith("PLUGIN:"):
                plugin_name = entry_str[7:]  # Strip "PLUGIN:" prefix
                logger.debug(f"Plugin was installed: {plugin_name}")

        # Clear the tracking lists
        self._installed_plugin_files.clear()
        self._installed_plugin_dirs.clear()

    def repr_failure(self, excinfo: pytest.ExceptionInfo[BaseException]) -> str:
        """Generate a failure representation.

        Args:
            excinfo: Exception info from pytest

        Returns:
            Formatted failure message
        """
        if isinstance(excinfo.value, YAMLTestFailure):
            return excinfo.value.format_failure()
        return super().repr_failure(excinfo)

    def reportinfo(self) -> tuple[Path, int | None, str]:
        """Report test information for pytest output.

        Returns:
            Tuple of (path, line, description)
        """
        source = self.test_config.source_path or Path(str(self.fspath))
        return source, None, f"{self.fixture_config.name}::{self.test_config.test_id}"


# =============================================================================
# Exception Classes
# =============================================================================


class YAMLTestFailure(Exception):
    """Exception raised when a YAML test fails expectations.

    Attributes:
        test_config: The test configuration
        failures: List of failed expectations
        error_message: Optional error message for execution failures
    """

    def __init__(
        self,
        test_config: TestConfig,
        failures: list[Any],
        error_message: str | None = None,
    ):
        """Initialize the failure.

        Args:
            test_config: Test configuration
            failures: List of failed Expectation objects
            error_message: Optional error message
        """
        self.test_config = test_config
        self.failures = failures
        self.error_message = error_message
        super().__init__(self.format_failure())

    def format_failure(self) -> str:
        """Format the failure message for display.

        Returns:
            Formatted failure string
        """
        lines = [
            f"Test: {self.test_config.test_id}",
            f"Name: {self.test_config.test_name}",
            "",
        ]

        if self.error_message:
            lines.extend([
                "Execution Error:",
                f"  {self.error_message}",
                "",
            ])

        if self.failures:
            lines.append(f"Failed Expectations ({len(self.failures)}):")
            for exp in self.failures:
                lines.append(f"  [{exp.id}] {exp.description}")
                if exp.failure_reason:
                    lines.append(f"      Reason: {exp.failure_reason}")
                lines.append(f"      Expected: {exp.expected}")
                if exp.actual:
                    lines.append(f"      Actual: {exp.actual}")
            lines.append("")

        return "\n".join(lines)


class PluginInstallationError(Exception):
    """Exception raised when plugin installation fails.

    This exception is raised immediately when a plugin fails to install,
    preventing test execution from proceeding.

    Attributes:
        plugin_name: Name of the plugin that failed to install
        return_code: Return code from the install command
        stdout: Standard output from the install command
        stderr: Standard error from the install command
    """

    def __init__(
        self,
        plugin_name: str,
        return_code: int,
        stdout: str = "",
        stderr: str = "",
    ):
        """Initialize the error.

        Args:
            plugin_name: Name of the plugin that failed
            return_code: Return code from install command
            stdout: Standard output from install command
            stderr: Standard error from install command
        """
        self.plugin_name = plugin_name
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(self.format_error())

    def format_error(self) -> str:
        """Format the error message for display.

        Returns:
            Formatted error string
        """
        lines = [
            f"Plugin Installation Failed: {self.plugin_name}",
            f"Return Code: {self.return_code}",
        ]

        if self.stdout:
            lines.extend(["", "STDOUT:", self.stdout])

        if self.stderr:
            lines.extend(["", "STDERR:", self.stderr])

        return "\n".join(lines)


# =============================================================================
# Pytest Hooks
# =============================================================================


def pytest_collect_file(
    parent: Collector,
    file_path: Path,
) -> YAMLFixtureFile | YAMLTestFile | None:
    """Pytest hook to collect YAML fixture and test files.

    This hook is called for each file pytest considers for collection.
    We intercept fixture.yaml files (which collect all tests in the fixture).

    To avoid duplicate test collection:
    - fixture.yaml collects all tests from its tests/ directory
    - Individual test_*.yaml files are only collected when they are the
      direct target of pytest (not discovered through directory traversal)

    Args:
        parent: Parent collector node
        file_path: Path to the file being considered

    Returns:
        Collector node or None if not a fixture file
    """
    if file_path.name == "fixture.yaml":
        return YAMLFixtureFile.from_parent(parent, path=file_path)

    # Only collect individual test_*.yaml files if:
    # 1. The file is a YAML test file
    # 2. There is NO fixture.yaml in the parent's parent (would cause duplication)
    # 3. OR we're running pytest directly on this specific file
    if file_path.name.startswith("test_") and file_path.suffix == ".yaml":
        # Check if there's a fixture.yaml that would collect this test
        fixture_yaml = file_path.parent.parent / "fixture.yaml"

        # If fixture.yaml exists at the fixture level, don't also collect individual files
        # The fixture.yaml already handles test discovery
        if fixture_yaml.exists():
            # Only collect if this specific file was targeted directly
            # (This happens when you run: pytest test-packages/fixtures/foo/tests/test_bar.yaml)
            # We detect this by checking if the parent is a Dir collector for the tests/ directory
            # and there's no YAMLFixtureFile sibling
            return None

        # Check for fixture.yaml in the same directory (alternative structure)
        fixture_yaml_same_dir = file_path.parent / "fixture.yaml"
        if fixture_yaml_same_dir.exists():
            return None

        # Standalone test file without fixture - still collect it
        return YAMLTestFile.from_parent(parent, path=file_path)

    return None


def pytest_configure(config: Config) -> None:
    """Pytest hook to configure the plugin.

    Registers custom markers for fixture testing.

    Args:
        config: Pytest configuration
    """
    config.addinivalue_line(
        "markers",
        "fixture_test: mark test as a YAML fixture test",
    )
    config.addinivalue_line(
        "markers",
        "keyword(name): mark test with a keyword for filtering",
    )


def pytest_sessionstart(session: pytest.Session) -> None:
    """Pytest hook called at session start.

    Initializes the report state for this session.

    Args:
        session: Pytest session
    """
    _report_state.reset()
    _report_state._session_start = datetime.now()


def pytest_collection_modifyitems(
    config: Config,
    items: list[pytest.Item],
) -> None:
    """Pytest hook to modify collected items.

    Adds the fixture_test marker to all YAML test items.

    Args:
        config: Pytest configuration
        items: List of collected test items
    """
    for item in items:
        if isinstance(item, YAMLTestItem):
            item.add_marker(pytest.mark.fixture_test)


def pytest_runtest_makereport(
    item: pytest.Item,
    call: pytest.CallInfo,
) -> None:
    """Pytest hook called after each test phase.

    Records test results for HTML report generation.

    Args:
        item: Test item
        call: Call info with execution details
    """
    # Only record results from the "call" phase (actual test execution)
    if call.when != "call":
        return

    # Only process YAML test items
    if not isinstance(item, YAMLTestItem):
        return

    # Build Claude session log from captured output
    claude_session_log = ""
    if item.claude_stdout:
        claude_session_log += f"=== Claude CLI stdout ===\n{item.claude_stdout}\n"
    if item.claude_stderr:
        claude_session_log += f"=== Claude CLI stderr ===\n{item.claude_stderr}\n"

    # Record the test result
    _report_state.record_test_result(
        fixture_name=item.fixture_config.name,
        test_id=item.test_config.test_id,
        test_config=item.test_config,
        passed=call.excinfo is None,
        collected_data=item.collected_data,
        expectations=item.evaluated_expectations,
        duration_ms=item.execution_duration_ms,
        error_message=item.execution_error,
        pytest_output=claude_session_log,
        expected_plugins=item.expected_plugins,
        plugin_install_results=item.plugin_install_results,
    )


def pytest_sessionfinish(
    session: pytest.Session,
    exitstatus: int,
) -> None:
    """Pytest hook called at session end.

    Generates HTML reports for all fixtures tested.

    Args:
        session: Pytest session
        exitstatus: Exit status code
    """
    config = session.config

    # Check if report generation is disabled
    if config.getoption("--no-report", default=False):
        return

    # Check if we should generate reports (default True)
    generate_report = config.getoption("--generate-report", default=True)
    if not generate_report:
        return

    # Skip if no YAML tests were run
    if not _report_state.fixture_names:
        return

    # Get report directory
    report_dir = config.getoption("--report-dir", default=None)
    if report_dir:
        report_path = Path(report_dir)
    else:
        # Default to test-packages/reports
        root_dir = Path(config.rootdir)
        report_path = root_dir / "test-packages" / "reports"

    report_path.mkdir(parents=True, exist_ok=True)

    # Generate report for each fixture
    generated_reports: list[Path] = []

    for fixture_name in _report_state.fixture_names:
        html_path = _generate_fixture_report(
            fixture_name=fixture_name,
            report_path=report_path,
            project_path=Path(config.rootdir),
        )
        if html_path:
            generated_reports.append(html_path)
            logger.info(f"Generated HTML report: {html_path}")

    # Handle browser opening
    if generated_reports:
        open_report = config.getoption("--open-report", default=False)
        open_on_fail = config.getoption("--open-on-fail", default=False)

        should_open = open_report or (open_on_fail and _report_state.has_failures)

        if should_open:
            # Open the first report (or most relevant one)
            report_to_open = generated_reports[0]
            logger.info(f"Opening report in browser: {report_to_open}")
            webbrowser.open(f"file://{report_to_open.absolute()}")


def _build_test_command(test_config: "TestConfig") -> str:
    """Build the complete Claude CLI command with all flags.

    Args:
        test_config: Test configuration containing execution settings

    Returns:
        Complete CLI command string
    """
    parts = ["claude"]

    # Add -p flag for prompt
    parts.append("-p")
    parts.append(f"'{test_config.execution.prompt}'")

    # Add model flag
    if test_config.execution.model:
        parts.append(f"--model {test_config.execution.model}")

    # Add tools flag (comma-separated)
    if test_config.execution.tools:
        tools_str = ",".join(test_config.execution.tools)
        parts.append(f"--tools {tools_str}")

    # Add standard test flags
    parts.append("--dangerously-skip-permissions")
    parts.append("--setting-sources project")

    return " ".join(parts)


def _build_setup_commands(
    fixture_config: "FixtureConfig | None",
    test_config: "TestConfig",
) -> list[str]:
    """Build setup commands including plugin installation.

    Args:
        fixture_config: Fixture configuration with plugins
        test_config: Test configuration with additional setup

    Returns:
        List of setup commands in order of execution
    """
    setup_commands: list[str] = []

    # Add plugin installation commands from fixture setup
    if fixture_config and fixture_config.setup and fixture_config.setup.plugins:
        for plugin in fixture_config.setup.plugins:
            setup_commands.append(f"claude plugin install {plugin} --scope project")

    # Add fixture-level setup commands
    if fixture_config and fixture_config.setup and fixture_config.setup.commands:
        setup_commands.extend(fixture_config.setup.commands)

    # Add test-specific setup commands
    if test_config.setup and test_config.setup.commands:
        setup_commands.extend(test_config.setup.commands)

    return setup_commands


def _find_agent_skill_path(
    fixture_config: "FixtureConfig | None",
    project_path: Path,
) -> str | None:
    """Find the skill/agent markdown file for the package.

    Searches in the following locations:
    1. Source synaptic-canvas repo: packages/<plugin-name>/skills|commands|agents/
    2. Installed location in test harness: .claude/skills|commands|agents/

    Args:
        fixture_config: Fixture configuration with package info
        project_path: Test harness project path

    Returns:
        Absolute path to markdown file, or None if not found
    """
    if not fixture_config or not fixture_config.package:
        return None

    # Package format is typically 'skill-name@repo' or just 'skill-name'
    skill_name = (
        fixture_config.package.split("@")[0]
        if "@" in fixture_config.package
        else fixture_config.package
    )

    # Try to find synaptic-canvas repo root (parent or sibling of test harness)
    sc_root = _find_synaptic_canvas_root(project_path)

    skill_locations: list[Path] = []

    # Priority 1: Look in synaptic-canvas packages directory (source files)
    if sc_root:
        package_path = sc_root / "packages" / skill_name
        if package_path.exists():
            for subdir in ["skills", "commands", "agents"]:
                dir_path = package_path / subdir
                if dir_path.exists():
                    # Find all markdown files recursively
                    for md_file in dir_path.glob("**/*.md"):
                        skill_locations.append(md_file)

    # Priority 2: Look in installed location in test harness
    for subdir in ["skills", "commands", "agents"]:
        installed_path = project_path / ".claude" / subdir / f"{skill_name}.md"
        skill_locations.append(installed_path)

    # Return the first existing path
    for skill_path in skill_locations:
        if skill_path.exists():
            return str(skill_path.absolute())

    return None


def _find_synaptic_canvas_root(project_path: Path) -> Path | None:
    """Find the synaptic-canvas repository root.

    Searches for a directory containing 'packages/' and 'docs/registries/'
    which indicates a synaptic-canvas repo.

    Args:
        project_path: Starting path (typically test harness root)

    Returns:
        Path to synaptic-canvas root, or None if not found
    """
    # Check if we're already in synaptic-canvas
    if (project_path / "packages").exists() and (project_path / "docs" / "registries").exists():
        return project_path

    # Check parent directory (if test harness is under synaptic-canvas)
    parent = project_path.parent
    if (parent / "packages").exists() and (parent / "docs" / "registries").exists():
        return parent

    # Check grandparent (e.g., test-packages/harness -> synaptic-canvas)
    grandparent = parent.parent
    if (grandparent / "packages").exists() and (grandparent / "docs" / "registries").exists():
        return grandparent

    # Check siblings (e.g., synaptic-canvas-worktrees/feature/agent-test-fixture)
    # In worktree setup, the harness is at <worktree>/test-packages/harness
    # and packages are at <worktree>/packages
    current = project_path
    for _ in range(5):  # Search up to 5 levels
        if (current / "packages").exists() and (current / "docs" / "registries").exists():
            return current
        if current.parent == current:
            break
        current = current.parent

    return None


def _generate_fixture_report(
    fixture_name: str,
    report_path: Path,
    project_path: Path,
) -> Path | None:
    """Generate HTML report for a fixture.

    Args:
        fixture_name: Name of the fixture
        report_path: Directory for reports
        project_path: Project root path

    Returns:
        Path to generated HTML report, or None on failure
    """
    try:
        from .html_report import HTMLReportBuilder, write_html_report
        from .models import (
            ClaudeResponse,
            DebugInfo,
            Expectation,
            FixtureMeta,
            FixtureReport,
            FixtureSummary,
            PluginInstallResult,
            PluginVerification,
            ReproduceSection,
            SideEffects,
            TestMetadata,
            TestResult,
        )
        from .reporter import ReportBuilder

        fixture_config = _report_state.get_fixture_config(fixture_name)
        test_results_data = _report_state.get_test_results(fixture_name)

        if not test_results_data:
            return None

        # Build TestResult objects from recorded data
        report_builder = ReportBuilder(project_path)
        test_results: list[TestResult] = []

        for result_data in test_results_data:
            test_config = result_data["test_config"]
            collected_data = result_data["collected_data"]
            expectations = result_data["expectations"]
            duration_ms = result_data["duration_ms"]

            # Build plugin verification data if plugins were configured
            plugin_verification = None
            expected_plugins = result_data.get("expected_plugins", [])
            plugin_install_results = result_data.get("plugin_install_results", [])
            if expected_plugins:
                plugin_verification = PluginVerification(
                    expected_plugins=expected_plugins,
                    install_results=plugin_install_results,
                )

            # Build complete CLI test command with all flags
            test_command = _build_test_command(test_config)

            # Build setup commands including plugin installation
            setup_commands = _build_setup_commands(fixture_config, test_config)

            # Build TestResult
            if collected_data:
                test_result = report_builder.build_test_result(
                    test_id=test_config.test_id,
                    test_name=test_config.test_name,
                    data=collected_data,
                    expectations=expectations,
                    description=test_config.description,
                    tags=test_config.tags,
                    model=test_config.execution.model,
                    tools_allowed=test_config.execution.tools,
                    fixture_id=fixture_name,
                    package=fixture_config.package if fixture_config else "",
                    test_command=test_command,
                    setup_commands=setup_commands,
                    plugin_verification=plugin_verification,
                )
            else:
                # Create minimal result for tests without collected data
                test_result = _create_minimal_test_result(
                    test_config=test_config,
                    fixture_name=fixture_name,
                    passed=result_data["passed"],
                    duration_ms=duration_ms,
                    error_message=result_data.get("error_message"),
                    plugin_verification=plugin_verification,
                )

            test_results.append(test_result)

        # Get fixture path from config
        fixture_yaml_path = None
        if fixture_config and fixture_config.source_path:
            fixture_yaml_path = str(fixture_config.source_path.absolute())

        # Try to find skill/agent markdown file based on package name
        agent_skill_path = _find_agent_skill_path(fixture_config, project_path)

        # Build FixtureReport
        fixture_report = report_builder.build_fixture_report(
            fixture_id=fixture_name,
            fixture_name=fixture_config.description if fixture_config else fixture_name,
            package=fixture_config.package if fixture_config else "",
            tests=test_results,
            agent_or_skill_path=agent_skill_path,
            fixture_path=fixture_yaml_path,
            report_path=str(report_path / f"{fixture_name}.html"),
        )

        # Write HTML report
        html_path = report_path / f"{fixture_name}.html"
        write_html_report(fixture_report, html_path)

        # Also write JSON report
        from .reporter import write_json_report
        json_path = report_path / f"{fixture_name}.json"
        write_json_report(fixture_report, json_path)

        # Preserve artifacts in folder next to HTML report
        _preserve_artifacts(
            fixture_name=fixture_name,
            report_path=report_path,
            test_results_data=test_results_data,
            fixture_config=fixture_config,
        )

        return html_path

    except Exception as e:
        logger.error(f"Failed to generate report for {fixture_name}: {e}")
        import traceback
        traceback.print_exc()
        return None


def _preserve_artifacts(
    fixture_name: str,
    report_path: Path,
    test_results_data: list[dict],
    fixture_config: FixtureConfig | None = None,
) -> None:
    """Preserve test artifacts in a folder next to the HTML report.

    Creates a folder with the same name as the report (without .html extension)
    and writes artifacts from collected_data. Also creates a timestamped copy
    in the history folder for retention.

    Artifacts preserved:
    - {test_id}-transcript.jsonl: Native Claude session transcript from raw_transcript_entries
    - {test_id}-trace.jsonl: Hook events from raw_hook_events
    - {test_id}-enriched.json: Enriched data with timeline tree structure
    - {test_id}-claude-cli.txt: Claude CLI stdout/stderr
    - {test_id}-pytest.txt: Pytest output

    Args:
        fixture_name: Name of the fixture (used for folder name)
        report_path: Directory where reports are stored
        test_results_data: List of test result dictionaries containing collected_data
        fixture_config: Optional FixtureConfig for enrichment metadata
    """
    import json
    import shutil

    # Create "latest" artifacts folder and clean it first
    latest_dir = report_path / fixture_name
    if latest_dir.exists():
        # Clean existing files in latest folder
        for item in latest_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        logger.info(f"Cleaned latest artifacts folder: {latest_dir}")
    latest_dir.mkdir(parents=True, exist_ok=True)

    # Create timestamped history folder
    # Use ISO format with hyphens instead of colons for filesystem safety: YYYY-MM-DDTHH-MM-SS
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    history_dir = report_path / "history" / fixture_name / timestamp
    history_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created history folder: {history_dir}")

    written_count = 0
    for i, result_data in enumerate(test_results_data, 1):
        collected_data = result_data.get("collected_data")
        test_id = result_data.get("test_id", f"test-{i}")

        # Write native Claude transcript (raw_transcript_entries) - preserved verbatim
        if collected_data and hasattr(collected_data, "raw_transcript_entries"):
            entries = collected_data.raw_transcript_entries
            if entries:
                dest_name = f"{test_id}-transcript.jsonl"
                for dest_dir in [latest_dir, history_dir]:
                    dest_path = dest_dir / dest_name
                    try:
                        with open(dest_path, "w") as f:
                            for entry in entries:
                                # Write native Claude transcript entries verbatim (no transformation)
                                f.write(json.dumps(entry) + "\n")
                        logger.debug(f"Preserved transcript: {dest_path}")
                    except Exception as e:
                        logger.warning(f"Failed to write transcript {dest_path}: {e}")
                written_count += 1
            else:
                logger.warning(f"Empty transcript for test {test_id}")

        # Write trace file (raw_hook_events)
        if collected_data and hasattr(collected_data, "raw_hook_events"):
            events = collected_data.raw_hook_events
            if events:
                dest_name = f"{test_id}-trace.jsonl"
                for dest_dir in [latest_dir, history_dir]:
                    dest_path = dest_dir / dest_name
                    try:
                        with open(dest_path, "w") as f:
                            for event in events:
                                f.write(json.dumps(event) + "\n")
                        logger.debug(f"Preserved trace file: {dest_path}")
                    except Exception as e:
                        logger.warning(f"Failed to write trace {dest_path}: {e}")
                written_count += 1
            else:
                logger.warning(f"Empty trace file for test {test_id}")

        # Write enriched.json with timeline tree structure
        try:
            from .enrichment import build_timeline_tree
            from .schemas import TestContext, TestContextPaths, ArtifactPaths

            # Get test_config for metadata
            test_config = result_data.get("test_config")

            # Get entries and events (may have been set in the transcript/trace blocks above)
            entries = []
            events = []
            if collected_data and hasattr(collected_data, "raw_transcript_entries"):
                entries = collected_data.raw_transcript_entries or []
            if collected_data and hasattr(collected_data, "raw_hook_events"):
                events = collected_data.raw_hook_events or []

            # Only proceed if we have data to enrich
            if entries or events:
                test_context = TestContext(
                    fixture_id=fixture_name,
                    test_id=test_id,
                    test_name=test_config.test_name if test_config else test_id,
                    package=fixture_config.package if fixture_config else "",
                    paths=TestContextPaths(
                        fixture_yaml=str(fixture_config.source_path) if fixture_config else "",
                        test_yaml=str(test_config.source_path) if test_config else "",
                    )
                )

                artifact_paths = ArtifactPaths(
                    transcript=f"{fixture_name}/{test_id}-transcript.jsonl",
                    trace=f"{fixture_name}/{test_id}-trace.jsonl",
                    enriched=f"{fixture_name}/{test_id}-enriched.json",
                )

                enriched_data = build_timeline_tree(
                    transcript_entries=entries,
                    trace_events=events,
                    test_context=test_context,
                    artifact_paths=artifact_paths,
                )

                # Write enriched.json
                dest_name = f"{test_id}-enriched.json"
                for dest_dir in [latest_dir, history_dir]:
                    dest_path = dest_dir / dest_name
                    with open(dest_path, "w") as f:
                        f.write(enriched_data.model_dump_json(indent=2))
                    logger.debug(f"Preserved enriched data: {dest_path}")
                written_count += 1

        except Exception as e:
            logger.warning(f"Failed to generate enriched data for {test_id}: {e}")

        # Write Claude CLI output (stdout + stderr)
        claude_stdout = ""
        claude_stderr = ""
        if collected_data:
            claude_stdout = getattr(collected_data, "claude_cli_stdout", "") or ""
            claude_stderr = getattr(collected_data, "claude_cli_stderr", "") or ""

        if claude_stdout or claude_stderr:
            dest_name = f"{test_id}-claude-cli.txt"
            cli_content = ""
            if claude_stdout:
                cli_content += "=== Claude CLI stdout ===\n" + claude_stdout + "\n"
            if claude_stderr:
                cli_content += "=== Claude CLI stderr ===\n" + claude_stderr + "\n"

            for dest_dir in [latest_dir, history_dir]:
                dest_path = dest_dir / dest_name
                try:
                    with open(dest_path, "w") as f:
                        f.write(cli_content)
                    logger.debug(f"Preserved Claude CLI output: {dest_path}")
                except Exception as e:
                    logger.warning(f"Failed to write CLI output {dest_path}: {e}")
            written_count += 1

        # Write pytest output
        pytest_output = result_data.get("pytest_output", "")
        if pytest_output:
            dest_name = f"{test_id}-pytest.txt"
            for dest_dir in [latest_dir, history_dir]:
                dest_path = dest_dir / dest_name
                try:
                    with open(dest_path, "w") as f:
                        f.write(pytest_output)
                    logger.debug(f"Preserved pytest output: {dest_path}")
                except Exception as e:
                    logger.warning(f"Failed to write pytest output {dest_path}: {e}")
            written_count += 1

    # Verify latest folder was created successfully
    assert latest_dir.exists(), f"Failed to create latest artifacts folder: {latest_dir}"

    if written_count > 0:
        logger.info(
            f"Preserved {written_count} artifact type(s) to: {latest_dir} and {history_dir}"
        )

    # Cleanup: keep only the last 10 history folders per fixture
    _cleanup_history_folders(report_path / "history" / fixture_name, max_folders=10)


def _cleanup_history_folders(history_fixture_dir: Path, max_folders: int = 10) -> None:
    """Clean up old history folders, keeping only the most recent ones.

    History folders are named with ISO timestamps (YYYY-MM-DDTHH-MM-SS), so
    sorting alphabetically also sorts chronologically.

    Args:
        history_fixture_dir: Path to the fixture's history directory
        max_folders: Maximum number of history folders to keep (default 10)
    """
    import shutil

    if not history_fixture_dir.exists():
        return

    # Get all subdirectories (history folders) sorted by name (chronologically)
    history_folders = sorted(
        [d for d in history_fixture_dir.iterdir() if d.is_dir()],
        key=lambda d: d.name
    )

    # If we have more than max_folders, delete the oldest ones
    folders_to_delete = len(history_folders) - max_folders
    if folders_to_delete > 0:
        for folder in history_folders[:folders_to_delete]:
            try:
                shutil.rmtree(folder)
                logger.info(f"Deleted old history folder: {folder}")
            except Exception as e:
                logger.warning(f"Failed to delete history folder {folder}: {e}")


def _create_minimal_test_result(
    test_config: TestConfig,
    fixture_name: str,
    passed: bool,
    duration_ms: float,
    error_message: str | None,
    plugin_verification: "PluginVerification | None" = None,
) -> "TestResult":
    """Create a minimal TestResult for tests without collected data.

    Args:
        test_config: Test configuration
        fixture_name: Parent fixture name
        passed: Whether test passed
        duration_ms: Test duration
        error_message: Optional error message
        plugin_verification: Plugin installation verification data

    Returns:
        Minimal TestResult
    """
    from .models import (
        ClaudeResponse,
        DebugInfo,
        Expectation,
        ExecutionSection,
        ExpectationType,
        PluginVerification,
        ReproduceSection,
        SideEffects,
        StatusIcon,
        TestMetadata,
        TestResult,
        TestStatus,
    )

    status = TestStatus.PASS if passed else TestStatus.FAIL
    status_icon = StatusIcon.PASS if passed else StatusIcon.FAIL

    # Create error expectation if there was an error
    expectations = []
    if error_message:
        expectations.append(
            Expectation(
                id="execution",
                type=ExpectationType.TOOL_CALL,
                description="Test execution",
                status=TestStatus.FAIL,
                expected={"success": True},
                actual={"error": error_message},
                failure_reason=error_message,
            )
        )

    # Calculate pass rate string
    if passed:
        pass_rate = "1/1" if not expectations else f"{len(expectations)}/{len(expectations)}"
    else:
        pass_rate = "0/1" if not expectations else f"0/{len(expectations)}"

    return TestResult(
        test_id=test_config.test_id,
        test_name=test_config.test_name,
        tab_label=test_config.test_id[:15],
        description=test_config.description,
        tags=test_config.tags,
        status=status,
        status_icon=status_icon,
        pass_rate=pass_rate,
        duration_ms=int(duration_ms),
        timestamp=datetime.now(),
        metadata=TestMetadata(
            fixture=fixture_name,
            package="",
            model=test_config.execution.model,
            session_id="",
            test_repo="",
        ),
        execution=ExecutionSection(
            prompt=test_config.execution.prompt,
            model=test_config.execution.model,
            tools_allowed=test_config.execution.tools or [],
        ),
        expectations=expectations,
        timeline=[],
        claude_response=ClaudeResponse(
            preview=error_message[:200] if error_message else "",
            full_text=error_message or "",
            word_count=len(error_message.split()) if error_message else 0,
        ),
        reproduce=ReproduceSection(
            setup_commands=[],
            test_command=f"claude '{test_config.execution.prompt}'",
            cleanup_commands=[],
        ),
        side_effects=SideEffects(),
        debug=DebugInfo(
            pytest_output=error_message or "",
            pytest_status=status,
            plugin_verification=plugin_verification,
        ),
    )


# =============================================================================
# Pytest Fixtures
# =============================================================================


@pytest.fixture
def fixture_loader(request: pytest.FixtureRequest) -> FixtureLoader:
    """Pytest fixture providing a FixtureLoader instance.

    The loader is configured to use the fixtures directory from
    the test-packages location.

    Args:
        request: Pytest fixture request

    Returns:
        Configured FixtureLoader instance
    """
    # Try to find fixtures path from config or default location
    fixtures_path = getattr(request.config, "_fixtures_path", None)
    if fixtures_path is None:
        # Default to test-packages/fixtures relative to repo root
        root_dir = Path(request.config.rootdir)
        fixtures_path = root_dir / "test-packages" / "fixtures"

    return FixtureLoader(fixtures_path)


@pytest.fixture
def isolated_session(request: pytest.FixtureRequest):
    """Pytest fixture providing an isolated Claude session.

    Creates a fresh isolated environment for each test.

    Args:
        request: Pytest fixture request

    Yields:
        IsolatedSession context manager
    """
    from .environment import isolated_claude_session

    # Find project path
    root_dir = Path(request.config.rootdir)
    project_path = root_dir

    # Look for test-harness specific project
    test_harness_project = root_dir / "test-packages"
    if test_harness_project.exists():
        project_path = test_harness_project

    with isolated_claude_session(
        project_path=project_path,
        cleanup=True,
    ) as session:
        yield session


@pytest.fixture
def data_collector():
    """Pytest fixture providing a DataCollector factory.

    Returns:
        Factory function to create DataCollector instances
    """
    from .collector import DataCollector

    def _create_collector(trace_path=None, transcript_path=None):
        return DataCollector(
            trace_path=trace_path,
            transcript_path=transcript_path,
        )

    return _create_collector
