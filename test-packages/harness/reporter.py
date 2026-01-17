"""
Report generation for Claude Code test harness.

This module provides functionality to generate JSON and HTML reports
from collected test data. Reports follow the v3.0 schema and include:
- Fixture-level summaries
- Individual test results with expectations
- Execution timeline
- Debug information

Example usage:
    from harness.reporter import ReportBuilder, HTMLReportGenerator
    from harness.collector import DataCollector

    # Build JSON report
    builder = ReportBuilder()
    report = builder.build_test_result(
        test_id="sc-startup-001",
        test_name="Startup readonly mode",
        data=collected_data,
        expectations=expectations,
    )

    # Generate HTML
    generator = HTMLReportGenerator()
    html = generator.generate(fixture_report)
"""

from __future__ import annotations

import html
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .collector import CollectedData, DataCollector
from .environment import get_git_state
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

        # Build the TestResult
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
                raw_trace_file=str(data.transcript_path) if data.transcript_path else None,
                errors=[e.error_content for e in data.errors],
            ),
        )

        return result

    def build_fixture_report(
        self,
        fixture_id: str,
        fixture_name: str,
        package: str,
        tests: list[TestResult],
        agent_or_skill: str = "",
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

        # Build regex flags
        flags = 0
        if "i" in flags_str:
            flags |= re.IGNORECASE

        # Search in Claude responses
        for response in self.data.claude_responses:
            match = re.search(pattern, response.text, flags)
            if match:
                # Get context around match
                start = max(0, match.start() - 50)
                end = min(len(response.text), match.end() + 50)
                context = response.text[start:end]

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
# HTML Report Generator
# =============================================================================


class HTMLReportGenerator:
    """Generates HTML reports from fixture reports.

    Creates self-contained HTML files with interactive features
    for viewing test results.
    """

    def __init__(self):
        """Initialize the HTML generator."""
        pass

    def generate(self, report: FixtureReport) -> str:
        """Generate HTML report from fixture report.

        Args:
            report: FixtureReport to convert to HTML

        Returns:
            Complete HTML document as string
        """
        fixture = report.fixture
        tests = report.tests

        # Generate test tabs
        tabs_html = self._generate_tabs(tests)
        test_content_html = self._generate_test_content(tests)

        # Build full HTML
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(fixture.fixture_name)} - Test Report</title>
    {self._generate_styles()}
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>{html.escape(fixture.fixture_name)}</h1>
            <div class="header-meta">
                <span class="package">{html.escape(fixture.package)}</span>
                <span class="date">{fixture.generated_at.strftime('%Y-%m-%d %H:%M')}</span>
            </div>
        </header>

        <div class="summary-bar">
            <div class="summary-stat total">
                <span class="stat-value">{fixture.summary.total_tests}</span>
                <span class="stat-label">Total</span>
            </div>
            <div class="summary-stat passed">
                <span class="stat-value">{fixture.summary.passed}</span>
                <span class="stat-label">Passed</span>
            </div>
            <div class="summary-stat failed">
                <span class="stat-value">{fixture.summary.failed}</span>
                <span class="stat-label">Failed</span>
            </div>
            <div class="summary-stat partial">
                <span class="stat-value">{fixture.summary.partial}</span>
                <span class="stat-label">Partial</span>
            </div>
            <div class="summary-stat skipped">
                <span class="stat-value">{fixture.summary.skipped}</span>
                <span class="stat-label">Skipped</span>
            </div>
        </div>

        <nav class="test-tabs">
            {tabs_html}
        </nav>

        <main class="test-content">
            {test_content_html}
        </main>
    </div>

    {self._generate_scripts()}
</body>
</html>"""

        return html_content

    def _generate_tabs(self, tests: list[TestResult]) -> str:
        """Generate tab navigation HTML."""
        tabs = []
        for i, test in enumerate(tests):
            active = "active" if i == 0 else ""
            status_class = test.status.value
            tabs.append(
                f'<button class="tab-btn {active} {status_class}" '
                f'data-tab="test-{i}">{html.escape(test.tab_label)}</button>'
            )
        return "\n            ".join(tabs)

    def _generate_test_content(self, tests: list[TestResult]) -> str:
        """Generate test content sections."""
        sections = []
        for i, test in enumerate(tests):
            active = "active" if i == 0 else ""
            sections.append(
                f'<section id="test-{i}" class="test-section {active}">'
                f"{self._generate_test_html(test)}"
                f"</section>"
            )
        return "\n            ".join(sections)

    def _generate_test_html(self, test: TestResult) -> str:
        """Generate HTML for a single test."""
        status_class = test.status.value
        status_icon = self._get_status_icon(test.status)

        # Generate subsections
        summary_html = self._generate_summary_section(test)
        expectations_html = self._generate_expectations_section(test)
        timeline_html = self._generate_timeline_section(test)
        debug_html = self._generate_debug_section(test)

        return f"""
                <div class="test-header">
                    <div class="test-title">
                        <span class="status-icon {status_class}">{status_icon}</span>
                        <h2>{html.escape(test.test_name)}</h2>
                    </div>
                    <div class="test-meta">
                        <span class="pass-rate">{test.pass_rate}</span>
                        <span class="duration">{test.duration_ms}ms</span>
                    </div>
                </div>

                <div class="test-description">{html.escape(test.description)}</div>

                <div class="section-tabs">
                    <button class="section-tab active" data-section="summary">Summary</button>
                    <button class="section-tab" data-section="expectations">Expectations</button>
                    <button class="section-tab" data-section="timeline">Timeline</button>
                    <button class="section-tab" data-section="debug">Debug</button>
                </div>

                <div class="section-content">
                    <div id="summary" class="section active">{summary_html}</div>
                    <div id="expectations" class="section">{expectations_html}</div>
                    <div id="timeline" class="section">{timeline_html}</div>
                    <div id="debug" class="section">{debug_html}</div>
                </div>
        """

    def _generate_summary_section(self, test: TestResult) -> str:
        """Generate summary section HTML."""
        reproduce = test.reproduce

        setup_cmds = "\n".join(reproduce.setup_commands)
        cleanup_cmds = "\n".join(reproduce.cleanup_commands)

        git_info = ""
        if reproduce.git_state:
            git_info = f"""
                <div class="git-state">
                    <h4>Git State</h4>
                    <p><strong>Branch:</strong> {html.escape(reproduce.git_state.branch)}</p>
                    <p><strong>Commit:</strong> {html.escape(reproduce.git_state.commit)}</p>
                </div>
            """

        return f"""
            <div class="reproduce-section">
                <h3>Reproduce</h3>

                <div class="code-block">
                    <div class="code-header">
                        <span>Setup Commands</span>
                        <button class="copy-btn" data-copy="setup-{test.test_id}">Copy</button>
                    </div>
                    <pre id="setup-{test.test_id}">{html.escape(setup_cmds)}</pre>
                </div>

                <div class="code-block">
                    <div class="code-header">
                        <span>Test Command</span>
                        <button class="copy-btn" data-copy="test-{test.test_id}">Copy</button>
                    </div>
                    <pre id="test-{test.test_id}">{html.escape(reproduce.test_command)}</pre>
                </div>

                <div class="code-block">
                    <div class="code-header">
                        <span>Cleanup Commands</span>
                        <button class="copy-btn" data-copy="cleanup-{test.test_id}">Copy</button>
                    </div>
                    <pre id="cleanup-{test.test_id}">{html.escape(cleanup_cmds)}</pre>
                </div>

                {git_info}
            </div>

            <div class="execution-section">
                <h3>Execution</h3>
                <p><strong>Model:</strong> {html.escape(test.execution.model)}</p>
                <p><strong>Tools:</strong> {html.escape(', '.join(test.execution.tools_allowed))}</p>
                <div class="prompt-box">
                    <strong>Prompt:</strong>
                    <pre>{html.escape(test.execution.prompt)}</pre>
                </div>
            </div>
        """

    def _generate_expectations_section(self, test: TestResult) -> str:
        """Generate expectations section HTML."""
        if not test.expectations:
            return "<p>No expectations defined.</p>"

        items = []
        for exp in test.expectations:
            status_class = exp.status.value
            status_icon = self._get_status_icon(exp.status)

            actual_html = ""
            if exp.actual:
                actual_html = f"""
                    <div class="expectation-actual">
                        <strong>Actual:</strong>
                        <pre>{html.escape(json.dumps(exp.actual, indent=2))}</pre>
                    </div>
                """

            failure_html = ""
            if exp.failure_reason:
                failure_html = f"""
                    <div class="expectation-failure">
                        <strong>Failure Reason:</strong> {html.escape(exp.failure_reason)}
                    </div>
                """

            items.append(f"""
                <div class="expectation-item {status_class}">
                    <div class="expectation-header">
                        <span class="status-icon">{status_icon}</span>
                        <span class="expectation-id">{html.escape(exp.id)}</span>
                        <span class="expectation-desc">{html.escape(exp.description)}</span>
                        <span class="expectation-type">{exp.type.value}</span>
                    </div>
                    <div class="expectation-body">
                        <div class="expectation-expected">
                            <strong>Expected:</strong>
                            <pre>{html.escape(json.dumps(exp.expected, indent=2))}</pre>
                        </div>
                        {actual_html}
                        {failure_html}
                    </div>
                </div>
            """)

        return "\n".join(items)

    def _generate_timeline_section(self, test: TestResult) -> str:
        """Generate timeline section HTML."""
        if not test.timeline:
            return "<p>No timeline entries.</p>"

        items = []
        for entry in test.timeline:
            type_class = entry.type.value.replace("_", "-")

            content_html = ""
            if entry.type.value == "prompt":
                content_html = f"<pre>{html.escape(entry.content or '')}</pre>"
            elif entry.type.value == "tool_call":
                input_str = ""
                if entry.input:
                    if entry.input.command:
                        input_str = entry.input.command
                    else:
                        input_str = json.dumps(entry.input.model_dump(exclude_none=True), indent=2)

                output_str = ""
                if entry.output:
                    if entry.output.stdout:
                        output_str = entry.output.stdout[:500]
                        if len(entry.output.stdout) > 500:
                            output_str += "..."

                content_html = f"""
                    <div class="tool-call-content">
                        <div class="tool-input">
                            <strong>Input:</strong>
                            <pre>{html.escape(input_str)}</pre>
                        </div>
                        <div class="tool-output">
                            <strong>Output:</strong>
                            <pre>{html.escape(output_str)}</pre>
                        </div>
                    </div>
                """
            elif entry.type.value == "response":
                preview = entry.content_preview or (entry.content[:200] if entry.content else "")
                content_html = f"<pre>{html.escape(preview)}</pre>"

            items.append(f"""
                <div class="timeline-item {type_class}">
                    <div class="timeline-header">
                        <span class="timeline-seq">#{entry.seq}</span>
                        <span class="timeline-type">{entry.type.value}</span>
                        {f'<span class="timeline-tool">{html.escape(entry.tool or "")}</span>' if entry.tool else ''}
                        <span class="timeline-elapsed">{entry.elapsed_ms}ms</span>
                        {f'<span class="timeline-duration">({entry.duration_ms}ms)</span>' if entry.duration_ms else ''}
                    </div>
                    {f'<div class="timeline-intent">{html.escape(entry.intent or "")}</div>' if entry.intent else ''}
                    <div class="timeline-body">
                        {content_html}
                    </div>
                </div>
            """)

        return "\n".join(items)

    def _generate_debug_section(self, test: TestResult) -> str:
        """Generate debug section HTML."""
        debug = test.debug

        pytest_html = ""
        if debug.pytest_output:
            pytest_html = f"""
                <div class="debug-block">
                    <h4>Pytest Output</h4>
                    <pre>{html.escape(debug.pytest_output)}</pre>
                </div>
            """

        errors_html = ""
        if debug.errors:
            error_list = "\n".join(debug.errors)
            errors_html = f"""
                <div class="debug-block errors">
                    <h4>Errors</h4>
                    <pre>{html.escape(error_list)}</pre>
                </div>
            """

        response_html = ""
        if test.claude_response.full_text:
            response_html = f"""
                <div class="debug-block">
                    <h4>Claude Response</h4>
                    <div class="code-block">
                        <div class="code-header">
                            <span>Full Response ({test.claude_response.word_count} words)</span>
                            <button class="copy-btn" data-copy="response-{test.test_id}">Copy</button>
                        </div>
                        <pre id="response-{test.test_id}">{html.escape(test.claude_response.full_text)}</pre>
                    </div>
                </div>
            """

        return f"""
            {pytest_html}
            {errors_html}
            {response_html}
            <div class="debug-block">
                <h4>Trace File</h4>
                <p>{html.escape(debug.raw_trace_file or 'N/A')}</p>
            </div>
        """

    def _get_status_icon(self, status: TestStatus) -> str:
        """Get emoji icon for status."""
        icons = {
            TestStatus.PASS: "&#10004;",  # Checkmark
            TestStatus.FAIL: "&#10008;",  # X mark
            TestStatus.PARTIAL: "&#9888;",  # Warning
            TestStatus.SKIPPED: "&#8594;",  # Arrow
        }
        return icons.get(status, "?")

    def _generate_styles(self) -> str:
        """Generate CSS styles."""
        return """
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .header h1 {
            font-size: 1.8rem;
            margin-bottom: 8px;
        }

        .header-meta {
            color: #666;
        }

        .header-meta .package {
            background: #e0e0e0;
            padding: 2px 8px;
            border-radius: 4px;
            margin-right: 10px;
        }

        .summary-bar {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }

        .summary-stat {
            flex: 1;
            background: #fff;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .summary-stat .stat-value {
            display: block;
            font-size: 2rem;
            font-weight: bold;
        }

        .summary-stat .stat-label {
            color: #666;
            font-size: 0.9rem;
        }

        .summary-stat.passed .stat-value { color: #2e7d32; }
        .summary-stat.failed .stat-value { color: #c62828; }
        .summary-stat.partial .stat-value { color: #f57c00; }
        .summary-stat.skipped .stat-value { color: #757575; }

        .test-tabs {
            display: flex;
            gap: 5px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }

        .tab-btn {
            padding: 10px 20px;
            border: none;
            background: #fff;
            border-radius: 8px 8px 0 0;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.2s;
        }

        .tab-btn:hover {
            background: #e3f2fd;
        }

        .tab-btn.active {
            background: #1976d2;
            color: #fff;
        }

        .tab-btn.pass { border-top: 3px solid #2e7d32; }
        .tab-btn.fail { border-top: 3px solid #c62828; }
        .tab-btn.partial { border-top: 3px solid #f57c00; }
        .tab-btn.skipped { border-top: 3px solid #757575; }

        .test-section {
            display: none;
            background: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .test-section.active {
            display: block;
        }

        .test-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid #e0e0e0;
        }

        .test-title {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .status-icon {
            font-size: 1.5rem;
        }

        .status-icon.pass { color: #2e7d32; }
        .status-icon.fail { color: #c62828; }
        .status-icon.partial { color: #f57c00; }
        .status-icon.skipped { color: #757575; }

        .test-meta {
            display: flex;
            gap: 15px;
            color: #666;
        }

        .pass-rate {
            font-weight: bold;
        }

        .test-description {
            color: #666;
            margin-bottom: 20px;
        }

        .section-tabs {
            display: flex;
            gap: 5px;
            margin-bottom: 15px;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 10px;
        }

        .section-tab {
            padding: 8px 15px;
            border: none;
            background: transparent;
            cursor: pointer;
            font-size: 0.9rem;
            border-radius: 4px;
        }

        .section-tab:hover {
            background: #f5f5f5;
        }

        .section-tab.active {
            background: #e3f2fd;
            color: #1976d2;
        }

        .section {
            display: none;
        }

        .section.active {
            display: block;
        }

        .code-block {
            margin: 15px 0;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
        }

        .code-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: #f5f5f5;
            border-bottom: 1px solid #e0e0e0;
        }

        .copy-btn {
            padding: 4px 10px;
            border: 1px solid #ccc;
            background: #fff;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8rem;
        }

        .copy-btn:hover {
            background: #e3f2fd;
        }

        pre {
            padding: 12px;
            background: #fafafa;
            overflow-x: auto;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.85rem;
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        .expectation-item {
            margin: 10px 0;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
        }

        .expectation-item.pass { border-left: 4px solid #2e7d32; }
        .expectation-item.fail { border-left: 4px solid #c62828; }

        .expectation-header {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px;
            background: #fafafa;
            cursor: pointer;
        }

        .expectation-id {
            font-family: monospace;
            color: #666;
        }

        .expectation-desc {
            flex: 1;
        }

        .expectation-type {
            background: #e0e0e0;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
        }

        .expectation-body {
            padding: 10px;
            display: none;
        }

        .expectation-item.expanded .expectation-body {
            display: block;
        }

        .expectation-failure {
            color: #c62828;
            margin-top: 10px;
            padding: 10px;
            background: #ffebee;
            border-radius: 4px;
        }

        .timeline-item {
            margin: 10px 0;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
        }

        .timeline-header {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px;
            background: #fafafa;
        }

        .timeline-seq {
            font-weight: bold;
            color: #1976d2;
        }

        .timeline-type {
            background: #e0e0e0;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
        }

        .timeline-item.prompt .timeline-type { background: #e3f2fd; }
        .timeline-item.tool-call .timeline-type { background: #fff3e0; }
        .timeline-item.response .timeline-type { background: #e8f5e9; }

        .timeline-tool {
            font-family: monospace;
        }

        .timeline-elapsed {
            margin-left: auto;
            color: #666;
        }

        .timeline-duration {
            color: #999;
        }

        .timeline-intent {
            padding: 5px 10px;
            color: #666;
            font-style: italic;
            background: #fafafa;
        }

        .timeline-body {
            padding: 10px;
        }

        .tool-call-content {
            display: grid;
            gap: 10px;
        }

        .debug-block {
            margin: 15px 0;
        }

        .debug-block h4 {
            margin-bottom: 10px;
            color: #666;
        }

        .debug-block.errors pre {
            background: #ffebee;
            color: #c62828;
        }

        h3 {
            margin: 20px 0 15px;
            color: #333;
        }

        .prompt-box {
            margin-top: 10px;
        }

        .git-state {
            margin-top: 15px;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 4px;
        }

        .git-state h4 {
            margin-bottom: 5px;
        }

        @media print {
            .copy-btn { display: none; }
            .section { display: block !important; }
            .test-section { display: block !important; }
        }
    </style>
"""

    def _generate_scripts(self) -> str:
        """Generate JavaScript for interactivity."""
        return """
    <script>
        // Test tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                // Remove active from all tabs and sections
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.test-section').forEach(s => s.classList.remove('active'));

                // Add active to clicked tab and corresponding section
                btn.classList.add('active');
                const sectionId = btn.dataset.tab;
                document.getElementById(sectionId).classList.add('active');
            });
        });

        // Section tab switching (within each test)
        document.querySelectorAll('.section-tab').forEach(btn => {
            btn.addEventListener('click', () => {
                const container = btn.closest('.test-section');

                // Remove active from sibling tabs and sections
                container.querySelectorAll('.section-tab').forEach(b => b.classList.remove('active'));
                container.querySelectorAll('.section').forEach(s => s.classList.remove('active'));

                // Add active
                btn.classList.add('active');
                const sectionId = btn.dataset.section;
                container.querySelector('#' + sectionId).classList.add('active');
            });
        });

        // Expectation expand/collapse
        document.querySelectorAll('.expectation-header').forEach(header => {
            header.addEventListener('click', () => {
                header.closest('.expectation-item').classList.toggle('expanded');
            });
        });

        // Copy buttons
        document.querySelectorAll('.copy-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const targetId = btn.dataset.copy;
                const target = document.getElementById(targetId);
                if (target) {
                    navigator.clipboard.writeText(target.textContent).then(() => {
                        const originalText = btn.textContent;
                        btn.textContent = 'Copied!';
                        setTimeout(() => btn.textContent = originalText, 1500);
                    });
                }
            });
        });
    </script>
"""


def write_html_report(
    report: FixtureReport,
    output_path: Path | str,
) -> Path:
    """Write a fixture report to HTML file.

    Args:
        report: FixtureReport to convert to HTML
        output_path: Path for output file

    Returns:
        Path to written file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    generator = HTMLReportGenerator()
    html_content = generator.generate(report)

    with open(output_path, "w") as f:
        f.write(html_content)

    logger.info(f"Wrote HTML report to: {output_path}")
    return output_path
