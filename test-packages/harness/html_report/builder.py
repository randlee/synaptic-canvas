"""
Main HTML Report Builder orchestrator.

This module provides the HTMLReportBuilder class that orchestrates all
component builders to generate a complete, self-contained HTML report
from a FixtureReport model.

The design follows the Builder pattern as specified in the design document,
with modular component builders that transform Pydantic models into HTML.
"""

from __future__ import annotations

from datetime import datetime
import json
import re
from typing import TYPE_CHECKING

from .models import (
    BuilderConfig,
    HeaderDisplayModel,
    StatusBannerDisplayModel,
    TestMetadataDisplayModel,
    ReproduceDisplayModel,
    ExpectationDisplayModel,
    ExpectationsDisplayModel,
    TimelineItemDisplayModel,
    TimelineDisplayModel,
    ResponseDisplayModel,
    DebugDisplayModel,
    AssessmentDisplayModel,
    TabDisplayModel,
    TestCaseDisplayModel,
    PluginVerificationDisplayModel,
    PluginInstallResultDisplayModel,
    LogIssuesDisplayModel,
    LogIssueDisplayModel,
)
from .components import (
    HeaderBuilder,
    TabsBuilder,
    TestCaseBuilder,
)
from .assets import get_all_css, get_all_scripts

if TYPE_CHECKING:
    from ..models import (
        FixtureReport,
        TestResult,
        Expectation,
    )


class HTMLReportBuilder:
    """Main orchestrator for building complete HTML reports.

    This builder transforms a FixtureReport Pydantic model into a
    self-contained HTML document with embedded CSS and JavaScript.

    The generated HTML matches the target format from the design document,
    with:
    - Dark gradient fixture header
    - Tab navigation with status icons
    - Status banners with pass/fail counts
    - Reproduce sections with copy buttons
    - Expectations with expandable details
    - Timeline with vertical line and colored dots
    - Collapsible response and debug sections
    - Agent assessment with lazy-loading support

    Example:
        from harness.models import FixtureReport
        from harness.html_report import HTMLReportBuilder

        report = FixtureReport(...)
        builder = HTMLReportBuilder()
        html = builder.build(report)

        with open("report.html", "w") as f:
            f.write(html)
    """

    def __init__(self, config: BuilderConfig | None = None):
        """Initialize the HTML report builder.

        Args:
            config: Optional configuration for customizing output
        """
        self.config = config or BuilderConfig()

        # Initialize component builders
        self.header_builder = HeaderBuilder(self.config)
        self.tabs_builder = TabsBuilder(self.config)
        self.test_case_builder = TestCaseBuilder(self.config)

    def build(self, report: "FixtureReport") -> str:
        """Build complete HTML report from a FixtureReport.

        Args:
            report: FixtureReport Pydantic model

        Returns:
            Complete HTML document as string
        """
        from ..models import TestStatus

        # Transform report data to display models
        header_data = self._transform_header(report)
        tab_data = self._transform_tabs(report)
        test_case_data = [
            self._transform_test_case(test, i)
            for i, test in enumerate(report.tests, 1)
        ]

        # Build components
        header_html = self.header_builder.build(header_data)
        tabs_header_html = self.tabs_builder.build(tab_data)

        # Build tab contents
        tab_contents = []
        for i, (tab, test_data) in enumerate(zip(tab_data, test_case_data)):
            content_html = self.test_case_builder.build(test_data)
            wrapped = self.tabs_builder.build_tab_content_wrapper(
                tab.tab_id,
                content_html,
                is_active=tab.is_active
            )
            tab_contents.append(wrapped)

        # Get assets
        css = get_all_css()
        js = get_all_scripts()

        # Assemble final document
        return self._assemble_document(
            fixture_name=report.fixture.fixture_name,
            css=css,
            header_html=header_html,
            tabs_header_html=tabs_header_html,
            tab_contents=tab_contents,
            js=js
        )

    def _transform_header(self, report: "FixtureReport") -> HeaderDisplayModel:
        """Transform FixtureReport to HeaderDisplayModel.

        Args:
            report: FixtureReport to transform

        Returns:
            HeaderDisplayModel for header builder
        """
        fixture = report.fixture
        summary = fixture.summary

        # Build summary text
        parts = []
        if summary.passed > 0:
            parts.append(f"{summary.passed} passed")
        if summary.failed > 0:
            parts.append(f"{summary.failed} failed")
        if summary.partial > 0:
            parts.append(f"{summary.partial} partial")
        if summary.skipped > 0:
            parts.append(f"{summary.skipped} skipped")
        summary_text = ", ".join(parts) if parts else "no tests"

        return HeaderDisplayModel(
            fixture_name=fixture.fixture_name,
            package=fixture.package,
            agent_or_skill=fixture.agent_or_skill,
            agent_or_skill_path=fixture.agent_or_skill_path,
            fixture_path=fixture.fixture_path,
            total_tests=summary.total_tests,
            summary_text=summary_text,
            generated_at=fixture.generated_at,
            report_path=fixture.report_path,
        )

    def _transform_tabs(self, report: "FixtureReport") -> list[TabDisplayModel]:
        """Transform FixtureReport tests to TabDisplayModels.

        Args:
            report: FixtureReport to transform

        Returns:
            List of TabDisplayModel for tabs builder
        """
        tabs = []
        for i, test in enumerate(report.tests, 1):
            tabs.append(TabDisplayModel(
                tab_id=f"test-{i}",
                tab_label=test.tab_label,
                status=test.status,
                is_active=(i == 1)
            ))
        return tabs

    def _transform_test_case(
        self,
        test: "TestResult",
        index: int
    ) -> TestCaseDisplayModel:
        """Transform TestResult to TestCaseDisplayModel.

        Args:
            test: TestResult to transform
            index: 1-based index of the test

        Returns:
            TestCaseDisplayModel for test case builder
        """
        from ..models import TestStatus, TimelineEntryType

        # Calculate passed/failed counts
        passed_count = sum(
            1 for e in test.expectations if e.status == TestStatus.PASS
        )
        total_count = len(test.expectations)

        # Extract token usage from timeline_tree.stats if available
        # Agent 7A is adding stats.token_usage - handle None gracefully
        token_kwargs = {}
        if test.timeline_tree is not None:
            # Check if timeline_tree has stats attribute (may be added by Agent 7A)
            stats = getattr(test.timeline_tree, 'stats', None)
            if stats is not None:
                token_usage = getattr(stats, 'token_usage', None)
                if token_usage is not None:
                    token_kwargs = {
                        'token_input': getattr(token_usage, 'input_tokens', 0),
                        'token_output': getattr(token_usage, 'output_tokens', 0),
                        'token_cache_creation': getattr(token_usage, 'cache_creation_tokens', 0),
                        'token_cache_read': getattr(token_usage, 'cache_read_tokens', 0),
                        'token_subagent': getattr(token_usage, 'subagent_tokens', 0),
                        'token_total_billable': getattr(token_usage, 'total_billable', 0),
                        'token_total_all': getattr(token_usage, 'total_all', 0),
                    }

        # Build status banner data
        status_banner = StatusBannerDisplayModel(
            status=test.status,
            passed_count=passed_count,
            total_count=total_count,
            duration_seconds=test.duration_ms / 1000.0,
            timestamp=test.timestamp,
            **token_kwargs,
        )

        # Build metadata data
        metadata = TestMetadataDisplayModel(
            test_id=test.test_id,
            test_name=test.test_name,
            fixture=test.metadata.fixture,
            package=test.metadata.package,
            model=test.metadata.model,
            session_id=test.metadata.session_id,
        )

        # Build reproduce data
        reproduce = ReproduceDisplayModel(
            test_index=index,
            setup_commands=test.reproduce.setup_commands,
            test_command=test.reproduce.test_command,
            cleanup_command=(
                test.reproduce.cleanup_commands[0]
                if test.reproduce.cleanup_commands
                else None
            ),
        )

        # Build plugin verification data
        plugin_verification = self._transform_plugin_verification(test, index)

        # Build expectations data
        expectations = ExpectationsDisplayModel(
            test_index=index,
            expectations=[
                self._transform_expectation(exp)
                for exp in test.expectations
            ]
        )

        # Build timeline data
        timeline = self._transform_timeline(test, index)

        # Build response data
        response = ResponseDisplayModel(
            test_index=index,
            full_text=test.claude_response.full_text,
        )

        # Build debug data
        side_effects = test.side_effects
        has_effects = (
            len(side_effects.files_created) > 0 or
            len(side_effects.files_modified) > 0 or
            len(side_effects.files_deleted) > 0
        )
        if has_effects:
            effects = []
            if side_effects.files_created:
                effects.append(f"Created: {', '.join(side_effects.files_created)}")
            if side_effects.files_modified:
                effects.append(f"Modified: {', '.join(side_effects.files_modified)}")
            if side_effects.files_deleted:
                effects.append(f"Deleted: {', '.join(side_effects.files_deleted)}")
            side_effects_text = "; ".join(effects)
        else:
            side_effects_text = "No files were created, modified, or deleted."

        debug = DebugDisplayModel(
            test_index=index,
            pytest_output=test.debug.pytest_output,
            test_script=None,  # Could be extracted from reproduce
            package=test.metadata.package,
            test_repo=test.metadata.test_repo,
            session_id=test.metadata.session_id,
            trace_file=test.debug.raw_trace_file,
            side_effects_text=side_effects_text,
            has_side_effects=has_effects,
        )

        # Build assessment data (placeholder for lazy-loading)
        assessment = AssessmentDisplayModel(
            test_index=index,
            test_id=test.test_id,
            is_embedded=False,
        )

        # Build log issues data
        log_issues = self._transform_log_issues(test, index)

        return TestCaseDisplayModel(
            test_index=index,
            test_id=test.test_id,
            test_name=test.test_name,
            description=test.description,
            status_banner=status_banner,
            metadata=metadata,
            reproduce=reproduce,
            plugin_verification=plugin_verification,
            expectations=expectations,
            timeline=timeline,
            response=response,
            debug=debug,
            log_issues=log_issues,
            assessment=assessment,
        )

    def _transform_plugin_verification(
        self,
        test: "TestResult",
        index: int
    ) -> PluginVerificationDisplayModel | None:
        """Transform plugin verification data to display model.

        Args:
            test: TestResult containing debug info with plugin verification
            index: 1-based test index

        Returns:
            PluginVerificationDisplayModel if plugins were configured, else None
        """
        # Check if plugin verification data exists
        if not test.debug.plugin_verification:
            return None

        pv = test.debug.plugin_verification
        if not pv.expected_plugins:
            return None

        # Transform install results to display models
        install_results = [
            PluginInstallResultDisplayModel(
                plugin_name=r.plugin_name,
                success=r.success,
                stdout=r.stdout,
                stderr=r.stderr,
                return_code=r.return_code,
            )
            for r in pv.install_results
        ]

        return PluginVerificationDisplayModel(
            test_index=index,
            expected_plugins=pv.expected_plugins,
            install_results=install_results,
            has_plugins=len(pv.expected_plugins) > 0,
        )

    def _transform_log_issues(
        self,
        test: "TestResult",
        index: int
    ) -> LogIssuesDisplayModel | None:
        """Transform log analysis data to display model.

        Args:
            test: TestResult containing log analysis data
            index: 1-based test index

        Returns:
            LogIssuesDisplayModel with warnings/errors, or None if no analysis data
        """
        # Check if log analysis data exists
        if not test.log_analysis:
            # Return empty model to show "no issues" section
            return LogIssuesDisplayModel(
                test_index=index,
                issues=[],
                allow_warnings=getattr(test, 'allow_warnings', False),
            )

        log_analysis = test.log_analysis
        raw_context = self._format_log_context(log_analysis.raw_content)

        # Transform log entries to display models
        issues = []

        # Add warnings
        for entry in log_analysis.warnings:
            issues.append(LogIssueDisplayModel(
                level="warning",
                message=entry.message,
                source=entry.logger_name if entry.logger_name else None,
                line_number=entry.line_number if entry.line_number > 0 else None,
                timestamp=entry.timestamp.strftime("%H:%M:%S.%f")[:-3] if entry.timestamp else None,
            ))

        # Add errors
        for entry in log_analysis.errors:
            issues.append(LogIssueDisplayModel(
                level="error",
                message=entry.message,
                source=entry.logger_name if entry.logger_name else None,
                line_number=entry.line_number if entry.line_number > 0 else None,
                timestamp=entry.timestamp.strftime("%H:%M:%S.%f")[:-3] if entry.timestamp else None,
            ))

        return LogIssuesDisplayModel(
            test_index=index,
            issues=issues,
            allow_warnings=getattr(test, 'allow_warnings', False),
            raw_context=raw_context,
        )

    @staticmethod
    def _format_log_context(raw_content: str) -> str | None:
        """Format raw log content for display."""
        if not raw_content:
            return None

        lines = []
        for line in raw_content.splitlines():
            stripped = line.rstrip()
            if not stripped:
                # Collapse multiple blank lines
                if lines and lines[-1] == "":
                    continue
                lines.append("")
                continue
            # Pretty-print JSON object lines when possible
            if stripped.startswith("{") and stripped.endswith("}"):
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    lines.append(stripped)
                else:
                    lines.append(json.dumps(parsed, indent=2, ensure_ascii=False))
                continue
            lines.append(stripped)

        formatted = "\n".join(lines).strip()
        return formatted or None

    def _transform_expectation(self, exp: "Expectation") -> ExpectationDisplayModel:
        """Transform Expectation to ExpectationDisplayModel.

        Args:
            exp: Expectation from TestResult

        Returns:
            ExpectationDisplayModel for expectations builder
        """
        from ..models import TestStatus

        # Build details text from expectation data
        details_text = exp.failure_reason or f"Type: {exp.type.value}"

        # Determine if details should be shown
        has_details = exp.has_details or bool(exp.expected) or bool(exp.actual)

        # Format expected/actual content
        expected_content = self._format_expectation_content(exp.expected)
        actual_content = self._format_expectation_content(exp.actual)

        return ExpectationDisplayModel(
            exp_id=exp.id,
            description=exp.description,
            status=exp.status,
            details_text=details_text,
            has_details=has_details,
            expected_content=expected_content,
            actual_content=actual_content,
        )

    def _format_expectation_content(self, value: object) -> str | None:
        if value is None:
            return None

        if isinstance(value, dict):
            value = self._format_expectation_dict(value)
            return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)

        if isinstance(value, list):
            return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)

        if isinstance(value, str):
            cleaned = self._format_command_json(value)
            if cleaned != value:
                return cleaned
            stripped = value.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError:
                    return value
                return json.dumps(parsed, indent=2, ensure_ascii=False)
            return value

        return str(value)

    def _format_expectation_dict(self, data: dict) -> dict:
        formatted = dict(data)
        command = formatted.get("command")
        if isinstance(command, str):
            formatted["command"] = self._format_command_json(command)
        return formatted

    def _format_command_json(self, command: str) -> str:
        """Pretty-print embedded JSON passed via --json in a command string."""
        pattern = re.compile(r"--json\\s+(?P<quote>['\"])(?P<payload>.*?)(?P=quote)")
        match = pattern.search(command)
        if not match:
            return command

        payload = match.group("payload")
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            return command

        pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
        replacement = f"--json {pretty}"
        return command[: match.start()] + replacement + command[match.end() :]

    def _transform_timeline(
        self,
        test: "TestResult",
        index: int
    ) -> TimelineDisplayModel:
        """Transform TestResult timeline to TimelineDisplayModel.

        Args:
            test: TestResult containing timeline
            index: 1-based test index

        Returns:
            TimelineDisplayModel for timeline builder
        """
        from ..models import TimelineEntryType

        entries = []
        tool_call_count = 0

        for entry in test.timeline:
            # Get content based on entry type
            content = entry.content or entry.content_preview
            command = entry.input.command if entry.input else None
            output = None
            if entry.output:
                output = entry.output.stdout or entry.output.content

            entries.append(TimelineItemDisplayModel(
                seq=entry.seq,
                entry_type=entry.type,
                tool_name=entry.tool,
                agent_id=entry.agent_id,
                agent_type=entry.agent_type,
                elapsed_ms=entry.elapsed_ms,
                content=content,
                intent=entry.intent,
                command=command,
                output=output,
                pid=entry.pid,
                tool_use_id=entry.tool_use_id,
            ))

            if entry.type == TimelineEntryType.TOOL_CALL:
                tool_call_count += 1

        return TimelineDisplayModel(
            timeline_id=f"timeline-{index}",
            entries=entries,
            tool_call_count=tool_call_count,
        )

    def _assemble_document(
        self,
        fixture_name: str,
        css: str,
        header_html: str,
        tabs_header_html: str,
        tab_contents: list[str],
        js: str,
    ) -> str:
        """Assemble the final HTML document.

        Args:
            fixture_name: Name for the title
            css: Complete CSS styles
            header_html: Fixture header HTML
            tabs_header_html: Tabs navigation HTML
            tab_contents: List of tab content HTML
            js: Complete JavaScript code

        Returns:
            Complete HTML document
        """
        from html import escape

        tabs_container = self.tabs_builder.build_container_start()
        tabs_container += tabs_header_html
        tabs_container += "\n".join(tab_contents)
        tabs_container += self.tabs_builder.build_container_end()

        return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Test Report: {escape(fixture_name)} Test Suite</title>
  <style>
{css}
  </style>
</head>
<body>
  {header_html}

  {tabs_container}

  <script>
{js}
  </script>
</body>
</html>'''
