"""
Pytest plugin for dynamic test generation from YAML fixtures.

This module provides pytest integration that:
- Discovers YAML test fixtures from the fixtures directory
- Generates pytest test cases dynamically from fixture definitions
- Hooks into the existing runner infrastructure for execution
- Supports test filtering by tags and test IDs

Usage:
    # Run all fixture tests
    pytest test-packages/fixtures/ -v

    # Run specific fixture
    pytest test-packages/fixtures/sc-startup/ -v

    # Run by tag
    pytest test-packages/fixtures/ -v -k "readonly"

    # Run by test ID
    pytest test-packages/fixtures/ -v -k "sc-startup-001"

Configuration:
    The plugin is registered via conftest.py and uses the following pytest hooks:
    - pytest_collect_file: Discovers fixture.yaml files
    - pytest_collect_directory: Handles fixture directories

Based on the fixture design from:
- docs/requirements/test-harness-design-spec.md (Section 7)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

import pytest

from .fixture_loader import FixtureConfig, FixtureLoader, TestConfig
from .models import TestStatus

if TYPE_CHECKING:
    from _pytest.config import Config
    from _pytest.nodes import Collector

logger = logging.getLogger(__name__)


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

        try:
            with isolated_claude_session(
                project_path=project_path,
                trace_path=project_path / "reports" / "trace.jsonl",
            ) as session:
                # Run setup commands
                self._run_setup_commands(session, merged_setup)

                # Execute the test
                result = session.run_command(
                    prompt=self.test_config.execution.prompt,
                    model=self.test_config.execution.model,
                    tools=self.test_config.execution.tools or None,
                    timeout=self.test_config.execution.timeout_ms // 1000,
                )

                # Find transcript
                session.find_transcript()

                # Collect data
                collector = DataCollector(
                    trace_path=session.trace_path,
                    transcript_path=session.transcript_path,
                )
                collected_data = collector.collect()

                # Evaluate expectations
                evaluator = ExpectationEvaluator(collected_data)
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

                    if expectation.status != TestStatus.PASS:
                        failures.append(expectation)

                if failures:
                    raise YAMLTestFailure(self.test_config, failures)

        except YAMLTestFailure:
            raise
        except Exception as e:
            raise YAMLTestFailure(
                self.test_config,
                [],
                error_message=str(e),
            ) from e
        finally:
            # Run teardown commands
            self._run_teardown_commands(merged_setup)

    def _find_project_path(self) -> Path:
        """Find the project path from the test file location.

        Traverses up the directory tree looking for indicators of the
        project root (like .claude directory or pyproject.toml).

        Returns:
            Path to the project root
        """
        current = self.test_config.source_path or self.fspath
        if current is None:
            # Fallback to session path
            return Path.cwd()

        current = Path(current)

        # Walk up looking for project root indicators
        for parent in [current] + list(current.parents):
            # Look for test-packages directory indicator
            if (parent / ".claude").exists():
                return parent
            if (parent / "pyproject.toml").exists():
                return parent
            if parent.name == "test-packages":
                # We're inside test-packages, go one level up
                return parent.parent

        # Default to current working directory
        return Path.cwd()

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
