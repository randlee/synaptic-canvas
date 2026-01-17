"""
Test runner for Claude Code test harness.

This module provides the main test orchestration functionality:
- Loading test fixtures from YAML configuration
- Executing tests in isolated environments
- Collecting results and generating reports

Example usage:
    from harness.runner import TestRunner

    runner = TestRunner(
        project_path="/path/to/test-harness",
        fixtures_path="/path/to/fixtures",
    )

    # Run all tests in a fixture
    report = runner.run_fixture("sc-startup")

    # Run specific test
    result = runner.run_test("sc-startup", "test_readonly.yaml")
"""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .collector import CollectedData, DataCollector
from .environment import get_git_state, isolated_claude_session
from .models import (
    ClaudeResponse,
    DebugInfo,
    ExecutionSection,
    Expectation,
    ExpectationType,
    FixtureMeta,
    FixtureReport,
    FixtureSummary,
    GitState,
    ReproduceSection,
    SideEffects,
    StatusIcon,
    TestMetadata,
    TestResult,
    TestStatus,
)
from .reporter import (
    ExpectationEvaluator,
    HTMLReportGenerator,
    ReportBuilder,
    write_html_report,
    write_json_report,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration Data Classes
# =============================================================================


@dataclass
class FixtureConfig:
    """Configuration for a test fixture loaded from fixture.yaml."""

    name: str
    description: str = ""
    package: str = ""

    # Setup/teardown
    setup_plugins: list[str] = field(default_factory=list)
    setup_files: list[dict[str, str]] = field(default_factory=list)
    setup_commands: list[str] = field(default_factory=list)
    teardown_commands: list[str] = field(default_factory=list)

    # Test discovery
    tests_dir: str = "tests"

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "FixtureConfig":
        """Load fixture configuration from YAML file.

        Args:
            yaml_path: Path to fixture.yaml

        Returns:
            FixtureConfig instance
        """
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        setup = data.get("setup", {})
        teardown = data.get("teardown", {})

        return cls(
            name=data.get("name", yaml_path.parent.name),
            description=data.get("description", ""),
            package=data.get("package", ""),
            setup_plugins=setup.get("plugins", []),
            setup_files=setup.get("files", []),
            setup_commands=setup.get("commands", []),
            teardown_commands=teardown.get("commands", []),
            tests_dir=data.get("tests_dir", "tests"),
        )


@dataclass
class TestConfig:
    """Configuration for an individual test loaded from test_*.yaml."""

    test_id: str
    test_name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)

    # Execution
    prompt: str = ""
    model: str = "haiku"
    tools: list[str] = field(default_factory=list)
    timeout_ms: int = 60000

    # Additional setup
    setup_files: list[dict[str, str]] = field(default_factory=list)
    setup_commands: list[str] = field(default_factory=list)

    # Expectations
    expectations: list[dict[str, Any]] = field(default_factory=list)

    # Skip conditions
    skip: bool = False
    skip_reason: str = ""

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "TestConfig":
        """Load test configuration from YAML file.

        Args:
            yaml_path: Path to test_*.yaml

        Returns:
            TestConfig instance
        """
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        execution = data.get("execution", {})
        setup = data.get("setup", {})

        return cls(
            test_id=data.get("test_id", yaml_path.stem),
            test_name=data.get("test_name", yaml_path.stem),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            prompt=execution.get("prompt", ""),
            model=execution.get("model", "haiku"),
            tools=execution.get("tools", []),
            timeout_ms=execution.get("timeout_ms", 60000),
            setup_files=setup.get("files", []),
            setup_commands=setup.get("commands", []),
            expectations=data.get("expectations", []),
            skip=data.get("skip", False),
            skip_reason=data.get("skip_reason", ""),
        )


# =============================================================================
# Test Runner
# =============================================================================


class TestRunner:
    """Orchestrates test execution for Claude Code skills and agents.

    The TestRunner loads fixture configurations, executes tests in isolated
    environments, collects results, and generates reports.

    Attributes:
        project_path: Path to the test project (with .claude/ directory)
        fixtures_path: Path to fixtures directory
        reports_path: Path for generated reports

    Example:
        runner = TestRunner(
            project_path="/path/to/sc-test-harness",
            fixtures_path="/path/to/fixtures",
        )
        report = runner.run_fixture("sc-startup")
    """

    def __init__(
        self,
        project_path: str | Path,
        fixtures_path: str | Path | None = None,
        reports_path: str | Path | None = None,
    ):
        """Initialize the TestRunner.

        Args:
            project_path: Path to the test project
            fixtures_path: Path to fixtures directory (default: project_path/fixtures)
            reports_path: Path for reports (default: project_path/reports)
        """
        self.project_path = Path(project_path).absolute()
        self.fixtures_path = (
            Path(fixtures_path).absolute()
            if fixtures_path
            else self.project_path / "fixtures"
        )
        self.reports_path = (
            Path(reports_path).absolute()
            if reports_path
            else self.project_path / "reports"
        )

        # Ensure directories exist
        self.reports_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"TestRunner initialized: project={self.project_path}")

    def discover_fixtures(self) -> list[str]:
        """Discover available fixtures.

        Returns:
            List of fixture names (directory names with fixture.yaml)
        """
        fixtures = []
        if not self.fixtures_path.exists():
            return fixtures

        for item in self.fixtures_path.iterdir():
            if item.is_dir() and (item / "fixture.yaml").exists():
                fixtures.append(item.name)

        logger.debug(f"Discovered fixtures: {fixtures}")
        return fixtures

    def discover_tests(self, fixture_name: str) -> list[Path]:
        """Discover tests in a fixture.

        Args:
            fixture_name: Name of the fixture

        Returns:
            List of paths to test YAML files
        """
        fixture_dir = self.fixtures_path / fixture_name
        config = FixtureConfig.from_yaml(fixture_dir / "fixture.yaml")

        tests_dir = fixture_dir / config.tests_dir
        if not tests_dir.exists():
            return []

        tests = sorted(tests_dir.glob("test_*.yaml"))
        logger.debug(f"Discovered {len(tests)} tests in {fixture_name}")
        return tests

    def run_fixture(
        self,
        fixture_name: str,
        test_filter: str | None = None,
        generate_html: bool = True,
    ) -> FixtureReport:
        """Run all tests in a fixture.

        Args:
            fixture_name: Name of the fixture to run
            test_filter: Optional filter for test names (substring match)
            generate_html: Whether to generate HTML report

        Returns:
            FixtureReport with all test results
        """
        fixture_dir = self.fixtures_path / fixture_name
        fixture_config = FixtureConfig.from_yaml(fixture_dir / "fixture.yaml")

        logger.info(f"Running fixture: {fixture_name}")

        # Discover and filter tests
        test_paths = self.discover_tests(fixture_name)
        if test_filter:
            test_paths = [p for p in test_paths if test_filter in p.stem]

        # Run tests
        results = []
        for test_path in test_paths:
            result = self.run_test(fixture_name, test_path.name, fixture_config)
            results.append(result)

        # Build fixture report
        builder = ReportBuilder(self.project_path)
        report = builder.build_fixture_report(
            fixture_id=fixture_name,
            fixture_name=fixture_config.description or fixture_name,
            package=fixture_config.package,
            tests=results,
            report_path=str(self.reports_path / f"{fixture_name}.json"),
        )

        # Write reports
        json_path = self.reports_path / f"{fixture_name}.json"
        write_json_report(report, json_path)

        if generate_html:
            html_path = self.reports_path / f"{fixture_name}.html"
            write_html_report(report, html_path)

        logger.info(
            f"Fixture complete: {report.fixture.summary.passed}/{report.fixture.summary.total_tests} passed"
        )
        return report

    def run_test(
        self,
        fixture_name: str,
        test_file: str,
        fixture_config: FixtureConfig | None = None,
    ) -> TestResult:
        """Run a single test.

        Args:
            fixture_name: Name of the fixture
            test_file: Name of the test YAML file
            fixture_config: Optional pre-loaded fixture config

        Returns:
            TestResult with test outcome
        """
        fixture_dir = self.fixtures_path / fixture_name

        # Load configs
        if fixture_config is None:
            fixture_config = FixtureConfig.from_yaml(fixture_dir / "fixture.yaml")

        test_path = fixture_dir / fixture_config.tests_dir / test_file
        test_config = TestConfig.from_yaml(test_path)

        logger.info(f"Running test: {test_config.test_id}")

        # Handle skipped tests
        if test_config.skip:
            return self._create_skipped_result(test_config, fixture_config)

        # Build CLI command
        test_command = self._build_test_command(test_config)

        # Combine setup commands
        setup_commands = [
            f"cd {self.project_path}",
            *fixture_config.setup_commands,
            *test_config.setup_commands,
        ]

        cleanup_commands = fixture_config.teardown_commands.copy()

        # Execute test
        start_time = time.time()
        start_timestamp = datetime.now()

        try:
            with isolated_claude_session(
                project_path=self.project_path,
                trace_path=self.reports_path / "trace.jsonl",
            ) as session:
                # Run the test
                result = session.run_command(
                    prompt=test_config.prompt,
                    model=test_config.model,
                    tools=test_config.tools if test_config.tools else None,
                    timeout=test_config.timeout_ms // 1000,
                )

                # Find transcript
                session.find_transcript()

                # Collect data
                collector = DataCollector(
                    trace_path=session.trace_path,
                    transcript_path=session.transcript_path,
                )
                collected_data = collector.collect()

                # Fill in missing data
                if not collected_data.start_timestamp:
                    collected_data.start_timestamp = start_timestamp
                if not collected_data.prompt:
                    collected_data.prompt = test_config.prompt

                # Evaluate expectations
                expectations = self._evaluate_expectations(
                    test_config.expectations, collected_data
                )

                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)

                # Build result
                builder = ReportBuilder(self.project_path)
                test_result = builder.build_test_result(
                    test_id=test_config.test_id,
                    test_name=test_config.test_name,
                    data=collected_data,
                    expectations=expectations,
                    description=test_config.description,
                    tags=test_config.tags,
                    model=test_config.model,
                    tools_allowed=test_config.tools,
                    fixture_id=fixture_name,
                    package=fixture_config.package,
                    test_repo=str(self.project_path),
                    test_command=test_command,
                    setup_commands=setup_commands,
                    cleanup_commands=cleanup_commands,
                )

                # Override duration with measured time
                test_result.duration_ms = duration_ms

                logger.info(f"Test complete: {test_config.test_id} - {test_result.status.value}")
                return test_result

        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            return self._create_timeout_result(
                test_config, fixture_config, duration_ms, test_command,
                setup_commands, cleanup_commands
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Test failed with exception: {e}")
            return self._create_error_result(
                test_config, fixture_config, duration_ms, str(e),
                test_command, setup_commands, cleanup_commands
            )

    def _build_test_command(self, test_config: TestConfig) -> str:
        """Build the Claude CLI command string."""
        cmd_parts = [
            "claude",
            "-p",
            f'"{test_config.prompt}"',
            "--model",
            test_config.model,
            "--setting-sources",
            "project",
            "--dangerously-skip-permissions",
        ]

        if test_config.tools:
            cmd_parts.extend(["--tools", ",".join(test_config.tools)])

        return " ".join(cmd_parts)

    def _evaluate_expectations(
        self,
        expectation_configs: list[dict[str, Any]],
        data: CollectedData,
    ) -> list[Expectation]:
        """Evaluate expectations against collected data."""
        evaluator = ExpectationEvaluator(data)
        results = []

        for exp_config in expectation_configs:
            exp_type = ExpectationType(exp_config.get("type", "tool_call"))
            result = evaluator.evaluate(
                expectation_id=exp_config.get("id", f"exp-{len(results)+1:03d}"),
                expectation_type=exp_type,
                description=exp_config.get("description", ""),
                expected=exp_config.get("expected", {}),
            )
            results.append(result)

        return results

    def _create_skipped_result(
        self,
        test_config: TestConfig,
        fixture_config: FixtureConfig,
    ) -> TestResult:
        """Create a result for a skipped test."""
        return TestResult(
            test_id=test_config.test_id,
            test_name=test_config.test_name,
            tab_label=test_config.test_name[:20],
            description=test_config.description,
            timestamp=datetime.now(),
            duration_ms=0,
            status=TestStatus.SKIPPED,
            status_icon=StatusIcon.SKIPPED,
            pass_rate="0/0",
            tags=test_config.tags,
            skip_reason=test_config.skip_reason,
            metadata=TestMetadata(
                fixture=fixture_config.name,
                package=fixture_config.package,
                model=test_config.model,
                session_id=None,
                test_repo=str(self.project_path),
            ),
            reproduce=ReproduceSection(
                test_command="",
            ),
            execution=ExecutionSection(
                prompt=test_config.prompt,
                model=test_config.model,
                tools_allowed=test_config.tools,
            ),
            expectations=[],
            timeline=[],
            side_effects=SideEffects(),
            claude_response=ClaudeResponse(
                preview="",
                full_text="",
                word_count=0,
            ),
            debug=DebugInfo(),
        )

    def _create_timeout_result(
        self,
        test_config: TestConfig,
        fixture_config: FixtureConfig,
        duration_ms: int,
        test_command: str,
        setup_commands: list[str],
        cleanup_commands: list[str],
    ) -> TestResult:
        """Create a result for a timed-out test."""
        return TestResult(
            test_id=test_config.test_id,
            test_name=test_config.test_name,
            tab_label=test_config.test_name[:20],
            description=test_config.description,
            timestamp=datetime.now(),
            duration_ms=duration_ms,
            status=TestStatus.FAIL,
            status_icon=StatusIcon.FAIL,
            pass_rate="0/0",
            tags=test_config.tags,
            metadata=TestMetadata(
                fixture=fixture_config.name,
                package=fixture_config.package,
                model=test_config.model,
                session_id=None,
                test_repo=str(self.project_path),
            ),
            reproduce=ReproduceSection(
                setup_commands=setup_commands,
                test_command=test_command,
                cleanup_commands=cleanup_commands,
            ),
            execution=ExecutionSection(
                prompt=test_config.prompt,
                model=test_config.model,
                tools_allowed=test_config.tools,
            ),
            expectations=[],
            timeline=[],
            side_effects=SideEffects(),
            claude_response=ClaudeResponse(
                preview="",
                full_text="",
                word_count=0,
            ),
            debug=DebugInfo(
                errors=[f"Test timed out after {test_config.timeout_ms}ms"],
            ),
        )

    def _create_error_result(
        self,
        test_config: TestConfig,
        fixture_config: FixtureConfig,
        duration_ms: int,
        error_msg: str,
        test_command: str,
        setup_commands: list[str],
        cleanup_commands: list[str],
    ) -> TestResult:
        """Create a result for a test that failed with an error."""
        return TestResult(
            test_id=test_config.test_id,
            test_name=test_config.test_name,
            tab_label=test_config.test_name[:20],
            description=test_config.description,
            timestamp=datetime.now(),
            duration_ms=duration_ms,
            status=TestStatus.FAIL,
            status_icon=StatusIcon.FAIL,
            pass_rate="0/0",
            tags=test_config.tags,
            metadata=TestMetadata(
                fixture=fixture_config.name,
                package=fixture_config.package,
                model=test_config.model,
                session_id=None,
                test_repo=str(self.project_path),
            ),
            reproduce=ReproduceSection(
                setup_commands=setup_commands,
                test_command=test_command,
                cleanup_commands=cleanup_commands,
            ),
            execution=ExecutionSection(
                prompt=test_config.prompt,
                model=test_config.model,
                tools_allowed=test_config.tools,
            ),
            expectations=[],
            timeline=[],
            side_effects=SideEffects(),
            claude_response=ClaudeResponse(
                preview="",
                full_text="",
                word_count=0,
            ),
            debug=DebugInfo(
                errors=[error_msg],
            ),
        )


# =============================================================================
# CLI Entry Point
# =============================================================================


def main():
    """CLI entry point for running tests."""
    import argparse

    parser = argparse.ArgumentParser(description="Claude Code Test Harness")
    parser.add_argument(
        "fixture",
        nargs="?",
        help="Fixture name to run (runs all fixtures if not specified)",
    )
    parser.add_argument(
        "--project",
        "-p",
        default=".",
        help="Path to test project",
    )
    parser.add_argument(
        "--fixtures",
        "-f",
        help="Path to fixtures directory",
    )
    parser.add_argument(
        "--filter",
        help="Filter tests by name substring",
    )
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="Skip HTML report generation",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create runner
    runner = TestRunner(
        project_path=args.project,
        fixtures_path=args.fixtures,
    )

    # Run tests
    if args.fixture:
        report = runner.run_fixture(
            args.fixture,
            test_filter=args.filter,
            generate_html=not args.no_html,
        )
        print(f"\nResults: {report.fixture.summary.passed}/{report.fixture.summary.total_tests} passed")
    else:
        # Run all fixtures
        fixtures = runner.discover_fixtures()
        for fixture in fixtures:
            report = runner.run_fixture(
                fixture,
                test_filter=args.filter,
                generate_html=not args.no_html,
            )
            print(f"{fixture}: {report.fixture.summary.passed}/{report.fixture.summary.total_tests} passed")


if __name__ == "__main__":
    main()
