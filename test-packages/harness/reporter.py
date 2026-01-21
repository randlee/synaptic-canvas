"""
Report generation for Claude Code test harness.

This module provides functionality to generate JSON reports and evaluate
expectations from collected test data. Reports follow the v3.0 schema.

For HTML report generation, use the html_report module:
    from harness.html_report import HTMLReportBuilder, write_html_report

Example usage:
    from harness.reporter import ReportBuilder, ExpectationEvaluator
    from harness.collector import DataCollector

    # Build JSON report
    builder = ReportBuilder()
    report = builder.build_test_result(
        test_id="sc-startup-001",
        test_name="Startup readonly mode",
        data=collected_data,
        expectations=expectations,
    )

    # For HTML reports, use the new html_report module:
    from harness.html_report import HTMLReportBuilder, write_html_report
    builder = HTMLReportBuilder()
    html = builder.build(fixture_report)
    write_html_report(fixture_report, "output/report.html")
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .collector import CollectedData, DataCollector
from .environment import get_git_state
from .response_filters import OutputFilterConfig, compile_output_pattern, filter_response_texts
from .schemas import ArtifactPaths, EnrichedData, TimelineTree
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
    PluginVerification,
    ReproduceSection,
    SideEffects,
    StatusIcon,
    TestMetadata,
    TestResult,
    TestStatus,
    TimelineEntry,
    TokenUsage,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Report Builder
# =============================================================================


class ReportBuilder:
    """Builds test reports from collected data.

    The ReportBuilder transforms raw collected data into structured
    report models following the v3.0 schema.

    Example:
        builder = ReportBuilder()
        test_result = builder.build_test_result(
            test_id="test-001",
            test_name="My Test",
            data=collected_data,
            expectations=expectations,
        )
    """

    def __init__(self, project_path: Path | str | None = None):
        """Initialize the ReportBuilder.

        Args:
            project_path: Path to the test project (for git state, etc.)
        """
        self.project_path = Path(project_path) if project_path else None

    def build_test_result(
        self,
        test_id: str,
        test_name: str,
        data: CollectedData,
        expectations: list[Expectation] | None = None,
        description: str = "",
        tab_label: str | None = None,
        tags: list[str] | None = None,
        model: str = "haiku",
        tools_allowed: list[str] | None = None,
        fixture_id: str = "",
        package: str = "",
        test_repo: str = "",
        test_command: str = "",
        setup_commands: list[str] | None = None,
        cleanup_commands: list[str] | None = None,
        pytest_output: str = "",
        pytest_status: TestStatus | None = None,
        plugin_verification: "PluginVerification | None" = None,
        reports_dir: Path | str | None = None,
        fixture_name: str | None = None,
        allow_warnings: bool = False,
    ) -> TestResult:
        """Build a complete TestResult from collected data.

        Args:
            test_id: Unique test identifier
            test_name: Human-readable test name
            data: CollectedData from DataCollector
            expectations: List of evaluated expectations
            description: Test description
            tab_label: Short label for tab display
            tags: Test tags for filtering
            model: Claude model used
            tools_allowed: Tools allowed in the test
            fixture_id: Parent fixture ID
            package: Package being tested
            test_repo: Path to test repository
            test_command: The Claude CLI command
            setup_commands: Setup commands for reproduction
            cleanup_commands: Cleanup commands for reproduction
            pytest_output: Raw pytest output
            pytest_status: Pytest result status
            plugin_verification: Plugin installation verification data
            reports_dir: Directory containing report artifacts (for enriched data loading)
            fixture_name: Name of the fixture (for enriched data file path)

        Returns:
            Complete TestResult model
        """
        expectations = expectations or []
        tags = tags or []
        tools_allowed = tools_allowed or []
        setup_commands = setup_commands or []
        cleanup_commands = cleanup_commands or []

        # Compute status from expectations
        status = self._compute_status(expectations)
        status_icon = self._status_to_icon(status)
        pass_rate = self._compute_pass_rate(expectations)

        # Build timeline
        collector = DataCollector()
        timeline = collector.build_timeline(data, data.start_timestamp)

        # Build git state if project path available
        git_state = None
        if self.project_path:
            gs = get_git_state(self.project_path)
            git_state = GitState(
                branch=gs.get("branch", ""),
                commit=gs.get("commit", ""),
                modified_files=gs.get("modified_files", []),
            )

        # Build Claude response
        claude_response = ClaudeResponse(
            preview=data.final_response[:200] if data.final_response else "",
            full_text=data.final_response,
            word_count=len(data.final_response.split()) if data.final_response else 0,
        )

        # Load enriched data if available (timeline tree integration)
        timeline_tree: TimelineTree | None = None
        artifacts: ArtifactPaths | None = None
        if reports_dir and fixture_name:
            enriched_path = Path(reports_dir) / fixture_name / f"{test_id}-enriched.json"
            if enriched_path.exists():
                try:
                    with open(enriched_path) as f:
                        enriched_data = EnrichedData.model_validate(json.load(f))
                    # Build TimelineTree with stats included for token display
                    timeline_tree = TimelineTree(
                        root_uuid=enriched_data.tree.root_uuid,
                        nodes=enriched_data.tree.nodes,
                        stats=enriched_data.stats,
                    )
                    artifacts = enriched_data.artifacts
                    logger.debug(f"Loaded enriched data from {enriched_path}")
                except Exception as e:
                    logger.warning(f"Failed to load enriched data from {enriched_path}: {e}")

        # Build the TestResult
        raw_trace_file = None
        if artifacts and reports_dir:
            trace_path = Path(reports_dir) / artifacts.trace
            if trace_path.exists():
                raw_trace_file = str(trace_path)

        result = TestResult(
            test_id=test_id,
            test_name=test_name,
            tab_label=tab_label or test_name[:20],
            description=description,
            timestamp=data.start_timestamp or datetime.now(),
            duration_ms=data.duration_ms or 0,
            status=status,
            status_icon=status_icon,
            pass_rate=pass_rate,
            tags=tags,
            metadata=TestMetadata(
                fixture=fixture_id,
                package=package,
                model=model,
                session_id=data.session_id,
                test_repo=test_repo,
            ),
            reproduce=ReproduceSection(
                setup_commands=setup_commands,
                test_command=test_command,
                cleanup_commands=cleanup_commands,
                environment={
                    "ANTHROPIC_API_KEY": "(required)",
                },
                git_state=git_state,
            ),
            execution=ExecutionSection(
                prompt=data.prompt or "",
                model=model,
                tools_allowed=tools_allowed,
                token_usage=None,  # TODO: Extract from transcript if available
            ),
            expectations=expectations,
            timeline=timeline,
            side_effects=SideEffects(),  # TODO: Implement side effects tracking
            claude_response=claude_response,
            debug=DebugInfo(
                pytest_output=pytest_output or None,
                pytest_status=pytest_status,
                raw_trace_file=raw_trace_file,
                errors=[e.error_content for e in data.errors],
                plugin_verification=plugin_verification,
            ),
            timeline_tree=timeline_tree,
            artifacts=artifacts,
            allow_warnings=allow_warnings,
        )

        return result

    def build_fixture_report(
        self,
        fixture_id: str,
        fixture_name: str,
        package: str,
        tests: list[TestResult],
        agent_or_skill: str = "",
        agent_or_skill_path: str | None = None,
        fixture_path: str | None = None,
        report_path: str = "",
        tags: list[str] | None = None,
    ) -> FixtureReport:
        """Build a complete FixtureReport from test results.

        Args:
            fixture_id: Unique fixture identifier
            fixture_name: Human-readable fixture name
            package: Package being tested
            tests: List of TestResult objects
            agent_or_skill: Agent or skill being tested
            agent_or_skill_path: Path to skill/agent markdown file (opens in VS Code)
            fixture_path: Path to fixture.yaml file (opens in PyCharm)
            report_path: Path where report will be saved
            tags: Tags for filtering

        Returns:
            Complete FixtureReport model
        """
        tags = tags or []

        # Compute summary
        summary = FixtureSummary(
            total_tests=len(tests),
            passed=sum(1 for t in tests if t.status == TestStatus.PASS),
            failed=sum(1 for t in tests if t.status == TestStatus.FAIL),
            partial=sum(1 for t in tests if t.status == TestStatus.PARTIAL),
            skipped=sum(1 for t in tests if t.status == TestStatus.SKIPPED),
        )

        fixture_meta = FixtureMeta(
            fixture_id=fixture_id,
            fixture_name=fixture_name,
            package=package,
            agent_or_skill=agent_or_skill or package,
            agent_or_skill_path=agent_or_skill_path,
            fixture_path=fixture_path,
            report_path=report_path,
            generated_at=datetime.now(),
            summary=summary,
            tags=tags,
        )

        return FixtureReport(
            fixture=fixture_meta,
            tests=tests,
        )

    def _compute_status(self, expectations: list[Expectation]) -> TestStatus:
        """Compute overall status from expectations."""
        if not expectations:
            return TestStatus.PASS

        passed = sum(1 for e in expectations if e.status == TestStatus.PASS)
        total = len(expectations)

        if passed == total:
            return TestStatus.PASS
        elif passed == 0:
            return TestStatus.FAIL
        else:
            return TestStatus.PARTIAL

    def _compute_pass_rate(self, expectations: list[Expectation]) -> str:
        """Compute pass rate string."""
        if not expectations:
            return "0/0"

        passed = sum(1 for e in expectations if e.status == TestStatus.PASS)
        return f"{passed}/{len(expectations)}"

    def _status_to_icon(self, status: TestStatus) -> StatusIcon:
        """Convert status to icon."""
        mapping = {
            TestStatus.PASS: StatusIcon.PASS,
            TestStatus.FAIL: StatusIcon.FAIL,
            TestStatus.PARTIAL: StatusIcon.WARNING,
            TestStatus.SKIPPED: StatusIcon.SKIPPED,
        }
        return mapping.get(status, StatusIcon.WARNING)


# =============================================================================
# Expectation Evaluator
# =============================================================================


class ExpectationEvaluator:
    """Evaluates expectations against collected data.

    Takes expectation definitions and checks them against the actual
    data collected during test execution.
    """

    def __init__(self, data: CollectedData):
        """Initialize the evaluator.

        Args:
            data: CollectedData to evaluate expectations against
        """
        self.data = data

    def evaluate(
        self,
        expectation_id: str,
        expectation_type: ExpectationType,
        description: str,
        expected: dict[str, Any],
    ) -> Expectation:
        """Evaluate a single expectation.

        Args:
            expectation_id: Unique expectation ID
            expectation_type: Type of expectation
            description: Human-readable description
            expected: Expected values (type-specific)

        Returns:
            Expectation with status and actual values
        """
        if expectation_type == ExpectationType.TOOL_CALL:
            return self._evaluate_tool_call(
                expectation_id, description, expected
            )
        elif expectation_type == ExpectationType.HOOK_EVENT:
            return self._evaluate_hook_event(
                expectation_id, description, expected
            )
        elif expectation_type == ExpectationType.SUBAGENT_EVENT:
            return self._evaluate_subagent_event(
                expectation_id, description, expected
            )
        elif expectation_type == ExpectationType.OUTPUT_CONTAINS:
            return self._evaluate_output_contains(
                expectation_id, description, expected
            )
        else:
            return Expectation(
                id=expectation_id,
                description=description,
                type=expectation_type,
                status=TestStatus.FAIL,
                expected=expected,
                actual=None,
                failure_reason=f"Unsupported expectation type: {expectation_type}",
            )

    def _evaluate_tool_call(
        self,
        expectation_id: str,
        description: str,
        expected: dict[str, Any],
    ) -> Expectation:
        """Evaluate a tool_call expectation."""
        tool_name = expected.get("tool", "")
        pattern = expected.get("pattern", "")

        # Search for matching tool call
        for i, tc in enumerate(self.data.tool_calls, 1):
            if tc.tool_name != tool_name:
                continue

            # Check pattern against tool input
            input_str = json.dumps(tc.tool_input)
            if re.search(pattern, input_str):
                # Match found
                output_preview = ""
                if tc.tool_response:
                    stdout = tc.tool_response.get("stdout", "")
                    if stdout:
                        output_preview = stdout[:100] + "..." if len(stdout) > 100 else stdout

                return Expectation(
                    id=expectation_id,
                    description=description,
                    type=ExpectationType.TOOL_CALL,
                    status=TestStatus.PASS,
                    has_details=True,
                    expected=expected,
                    actual={
                        "tool": tc.tool_name,
                        "command": tc.tool_input.get("command", str(tc.tool_input)),
                        "output_preview": output_preview,
                    },
                    matched_at={
                        "sequence": i,
                        "timestamp": (
                            tc.pre_timestamp.isoformat() if tc.pre_timestamp else ""
                        ),
                    },
                )

        # No match found
        return Expectation(
            id=expectation_id,
            description=description,
            type=ExpectationType.TOOL_CALL,
            status=TestStatus.FAIL,
            expected=expected,
            actual=None,
            failure_reason=f"No {tool_name} call matching pattern: {pattern}",
        )

    def _evaluate_hook_event(
        self,
        expectation_id: str,
        description: str,
        expected: dict[str, Any],
    ) -> Expectation:
        """Evaluate a hook_event expectation."""
        event_type = expected.get("event", "")
        filters = expected.get("filters", {})

        # Search for matching event
        for event in self.data.raw_hook_events:
            evt = event.get("event") or event.get("hook_event_name")
            if evt != event_type:
                continue

            # Check filters
            if filters:
                match = all(
                    event.get(k) == v for k, v in filters.items()
                )
                if not match:
                    continue

            # Match found
            return Expectation(
                id=expectation_id,
                description=description,
                type=ExpectationType.HOOK_EVENT,
                status=TestStatus.PASS,
                expected=expected,
                actual=event,
            )

        # No match found
        return Expectation(
            id=expectation_id,
            description=description,
            type=ExpectationType.HOOK_EVENT,
            status=TestStatus.FAIL,
            expected=expected,
            actual=None,
            failure_reason=f"No {event_type} event found matching filters",
        )

    def _evaluate_subagent_event(
        self,
        expectation_id: str,
        description: str,
        expected: dict[str, Any],
    ) -> Expectation:
        """Evaluate a subagent_event expectation."""
        event_type = expected.get("event", "")
        agent_id = expected.get("agent_id")
        agent_type = expected.get("agent_type")

        # Search for matching subagent
        for subagent in self.data.subagents:
            if event_type == "SubagentStart" and not subagent.start_timestamp:
                continue
            if event_type == "SubagentStop" and not subagent.stop_timestamp:
                continue

            if agent_id and subagent.agent_id != agent_id:
                continue
            if agent_type and subagent.agent_type != agent_type:
                continue

            # Match found
            return Expectation(
                id=expectation_id,
                description=description,
                type=ExpectationType.SUBAGENT_EVENT,
                status=TestStatus.PASS,
                expected=expected,
                actual={
                    "agent_id": subagent.agent_id,
                    "agent_type": subagent.agent_type,
                },
            )

        # No match found
        return Expectation(
            id=expectation_id,
            description=description,
            type=ExpectationType.SUBAGENT_EVENT,
            status=TestStatus.FAIL,
            expected=expected,
            actual=None,
            failure_reason=f"No {event_type} event found for agent",
        )

    def _evaluate_output_contains(
        self,
        expectation_id: str,
        description: str,
        expected: dict[str, Any],
    ) -> Expectation:
        """Evaluate an output_contains expectation."""
        pattern = expected.get("pattern", "")
        flags_str = expected.get("flags", "")
        case_sensitive = expected.get("case_sensitive", False)
        response_filter = expected.get("response_filter", "assistant_all")
        exclude_prompt = expected.get("exclude_prompt", True)

        compiled = compile_output_pattern(
            pattern=pattern,
            flags=flags_str,
            case_sensitive=case_sensitive,
        )
        response_texts = filter_response_texts(
            self.data,
            OutputFilterConfig(
                response_filter=response_filter,
                exclude_prompt=exclude_prompt,
            ),
        )

        # Search in Claude responses
        for response_text in response_texts:
            match = compiled.search(response_text)
            if match:
                # Get context around match
                start = max(0, match.start() - 50)
                end = min(len(response_text), match.end() + 50)
                context = response_text[start:end]

                return Expectation(
                    id=expectation_id,
                    description=description,
                    type=ExpectationType.OUTPUT_CONTAINS,
                    status=TestStatus.PASS,
                    expected=expected,
                    actual={
                        "matched_text": match.group(),
                        "context": context,
                    },
                )

        # No match found
        return Expectation(
            id=expectation_id,
            description=description,
            type=ExpectationType.OUTPUT_CONTAINS,
            status=TestStatus.FAIL,
            expected=expected,
            actual=None,
            failure_reason=f"Pattern not found in output: {pattern}",
        )


# =============================================================================
# JSON Report Writer
# =============================================================================


def write_json_report(
    report: FixtureReport,
    output_path: Path | str,
    indent: int = 2,
) -> Path:
    """Write a fixture report to JSON file.

    Args:
        report: FixtureReport to write
        output_path: Path for output file
        indent: JSON indentation level

    Returns:
        Path to written file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write(report.model_dump_json(indent=indent))

    logger.info(f"Wrote JSON report to: {output_path}")
    return output_path


# =============================================================================
# HTML Report Generation (DEPRECATED - use harness.html_report instead)
# =============================================================================

# For backward compatibility, re-export from the new html_report module
# These are deprecated and will emit warnings when used directly from reporter
from .html_report import HTMLReportGenerator, write_html_report

__all__ = [
    "ReportBuilder",
    "ExpectationEvaluator",
    "write_json_report",
    # Deprecated - use harness.html_report instead
    "HTMLReportGenerator",
    "write_html_report",
]
