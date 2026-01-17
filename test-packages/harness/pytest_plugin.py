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
                self.collected_data = collector.collect()

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
        pytest_output="",  # Could capture pytest output here if needed
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
                    test_command=f"claude '{test_config.execution.prompt}'",
                    setup_commands=test_config.setup.commands if test_config.setup else [],
                )
            else:
                # Create minimal result for tests without collected data
                test_result = _create_minimal_test_result(
                    test_config=test_config,
                    fixture_name=fixture_name,
                    passed=result_data["passed"],
                    duration_ms=duration_ms,
                    error_message=result_data.get("error_message"),
                )

            test_results.append(test_result)

        # Get fixture path from config
        fixture_yaml_path = None
        if fixture_config and fixture_config.source_path:
            fixture_yaml_path = str(fixture_config.source_path.absolute())

        # Try to find skill/agent markdown file based on package name
        agent_skill_path = None
        if fixture_config and fixture_config.package:
            # Package format is typically 'skill-name@repo' or just 'skill-name'
            skill_name = fixture_config.package.split("@")[0] if "@" in fixture_config.package else fixture_config.package
            # Look in common locations for skill markdown files
            skill_locations = [
                project_path / ".claude" / "skills" / f"{skill_name}.md",
                project_path / ".claude" / "commands" / f"{skill_name}.md",
                project_path / ".claude" / "agents" / f"{skill_name}.md",
            ]
            for skill_path in skill_locations:
                if skill_path.exists():
                    agent_skill_path = str(skill_path.absolute())
                    break

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

        return html_path

    except Exception as e:
        logger.error(f"Failed to generate report for {fixture_name}: {e}")
        import traceback
        traceback.print_exc()
        return None


def _create_minimal_test_result(
    test_config: TestConfig,
    fixture_name: str,
    passed: bool,
    duration_ms: float,
    error_message: str | None,
) -> "TestResult":
    """Create a minimal TestResult for tests without collected data.

    Args:
        test_config: Test configuration
        fixture_name: Parent fixture name
        passed: Whether test passed
        duration_ms: Test duration
        error_message: Optional error message

    Returns:
        Minimal TestResult
    """
    from .models import (
        ClaudeResponse,
        DebugInfo,
        Expectation,
        ExecutionSection,
        ExpectationType,
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
