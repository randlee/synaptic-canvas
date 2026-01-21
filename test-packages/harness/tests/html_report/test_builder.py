"""Tests for html_report.builder module.

These tests verify the main HTMLReportBuilder orchestrator.
"""

import pytest
from datetime import datetime

from harness.models import (
    FixtureReport,
    FixtureMeta,
    FixtureSummary,
    TestResult,
    TestStatus,
    StatusIcon,
    TestMetadata,
    ReproduceSection,
    ExecutionSection,
    Expectation,
    ExpectationType,
    TimelineEntry,
    TimelineEntryType,
    SideEffects,
    ClaudeResponse,
    DebugInfo,
)
from harness.html_report import HTMLReportBuilder, BuilderConfig


def create_minimal_test_result(
    test_id: str = "test-001",
    test_name: str = "Minimal Test",
    status: TestStatus = TestStatus.PASS
) -> TestResult:
    """Create a minimal TestResult for testing."""
    return TestResult(
        test_id=test_id,
        test_name=test_name,
        tab_label="Minimal",
        description="A minimal test",
        timestamp=datetime(2024, 1, 15, 10, 30, 0),
        duration_ms=1000,
        status=status,
        status_icon=StatusIcon.PASS if status == TestStatus.PASS else StatusIcon.FAIL,
        pass_rate="1/1",
        metadata=TestMetadata(
            fixture="test_fixture",
            package="sc-startup",
            model="haiku",
            test_repo="/path/to/repo"
        ),
        reproduce=ReproduceSection(
            setup_commands=["cd /path"],
            test_command="claude 'test'"
        ),
        execution=ExecutionSection(
            prompt="Test prompt",
            model="haiku"
        ),
        expectations=[
            Expectation(
                id="exp-001",
                description="Should pass",
                type=ExpectationType.TOOL_CALL,
                status=TestStatus.PASS,
                expected={"tool": "Bash"}
            )
        ],
        timeline=[],
        side_effects=SideEffects(),
        claude_response=ClaudeResponse(
            preview="Response preview",
            full_text="Full response text",
            word_count=3
        ),
        debug=DebugInfo()
    )


def create_fixture_report(tests: list[TestResult] | None = None) -> FixtureReport:
    """Create a FixtureReport for testing."""
    if tests is None:
        tests = [create_minimal_test_result()]

    # Calculate summary
    passed = sum(1 for t in tests if t.status == TestStatus.PASS)
    failed = sum(1 for t in tests if t.status == TestStatus.FAIL)
    partial = sum(1 for t in tests if t.status == TestStatus.PARTIAL)
    skipped = sum(1 for t in tests if t.status == TestStatus.SKIPPED)

    return FixtureReport(
        fixture=FixtureMeta(
            fixture_id="test_fixture",
            fixture_name="Test Fixture",
            package="sc-startup",
            agent_or_skill="startup",
            report_path="/path/to/report.html",
            generated_at=datetime(2024, 1, 15, 10, 30, 0),
            summary=FixtureSummary(
                total_tests=len(tests),
                passed=passed,
                failed=failed,
                partial=partial,
                skipped=skipped
            )
        ),
        tests=tests
    )


class TestHTMLReportBuilder:
    """Tests for HTMLReportBuilder."""

    def test_builder_initialization(self):
        """Test builder initializes with default config."""
        builder = HTMLReportBuilder()
        assert builder.config is not None
        assert builder.config.default_editor == "vscode"

    def test_builder_with_custom_config(self):
        """Test builder with custom configuration."""
        config = BuilderConfig(default_editor="pycharm")
        builder = HTMLReportBuilder(config=config)
        assert builder.config.default_editor == "pycharm"

    def test_build_minimal_report(self):
        """Test building a minimal report."""
        builder = HTMLReportBuilder()
        report = create_fixture_report()
        html = builder.build(report)

        # Check basic structure
        assert "<!DOCTYPE html>" in html
        assert "<html lang=\"en\">" in html
        assert "<head>" in html
        assert "<body>" in html
        assert "</html>" in html

        # Check title
        assert "<title>Test Report: Test Fixture Test Suite</title>" in html

        # Check CSS is embedded
        assert "<style>" in html
        assert "--pass:" in html  # CSS variable

        # Check JavaScript is embedded
        assert "<script>" in html
        assert "switchTab" in html

    def test_build_includes_fixture_header(self):
        """Test that fixture header is generated."""
        builder = HTMLReportBuilder()
        report = create_fixture_report()
        html = builder.build(report)

        assert 'class="fixture-header"' in html
        assert "Test Fixture Test Suite" in html
        assert "sc-startup" in html

    def test_build_includes_tabs(self):
        """Test that tabs are generated for each test."""
        builder = HTMLReportBuilder()
        tests = [
            create_minimal_test_result("test-1", "Test One"),
            create_minimal_test_result("test-2", "Test Two"),
        ]
        report = create_fixture_report(tests)
        html = builder.build(report)

        assert 'class="tabs-container"' in html
        assert 'class="tabs-header"' in html
        assert 'id="test-1"' in html
        assert 'id="test-2"' in html

    def test_build_includes_status_banners(self):
        """Test that status banners are included."""
        builder = HTMLReportBuilder()
        report = create_fixture_report()
        html = builder.build(report)

        assert 'class="status-banner pass"' in html
        assert "PASS" in html

    def test_build_includes_expectations(self):
        """Test that expectations section is included."""
        builder = HTMLReportBuilder()
        report = create_fixture_report()
        html = builder.build(report)

        assert 'class="expectations-list"' in html
        assert "Should pass" in html

    def test_build_handles_failed_tests(self):
        """Test building report with failed tests."""
        builder = HTMLReportBuilder()
        test = create_minimal_test_result("test-1", "Failed Test", TestStatus.FAIL)
        test.status_icon = StatusIcon.FAIL
        test.expectations[0].status = TestStatus.FAIL
        test.expectations[0].failure_reason = "Did not match expected pattern"

        report = create_fixture_report([test])
        html = builder.build(report)

        assert 'class="status-banner fail"' in html
        assert "FAIL" in html

    def test_build_handles_partial_tests(self):
        """Test building report with partial pass tests."""
        builder = HTMLReportBuilder()
        test = create_minimal_test_result("test-1", "Partial Test", TestStatus.PARTIAL)
        test.status_icon = StatusIcon.WARNING
        test.expectations.append(
            Expectation(
                id="exp-002",
                description="Should fail",
                type=ExpectationType.TOOL_CALL,
                status=TestStatus.FAIL,
                expected={"tool": "Read"}
            )
        )
        test.pass_rate = "1/2"

        report = create_fixture_report([test])
        html = builder.build(report)

        assert 'class="status-banner partial"' in html

    def test_build_handles_skipped_tests(self):
        """Test building report with skipped tests."""
        builder = HTMLReportBuilder()
        test = create_minimal_test_result("test-1", "Skipped Test", TestStatus.SKIPPED)
        test.status_icon = StatusIcon.SKIPPED
        test.skip_reason = "Not applicable"

        report = create_fixture_report([test])
        html = builder.build(report)

        assert 'class="status-banner skipped"' in html

    def test_build_includes_timeline(self):
        """Test that timeline section is included."""
        builder = HTMLReportBuilder()
        test = create_minimal_test_result()
        test.timeline = [
            TimelineEntry(
                seq=1,
                type=TimelineEntryType.PROMPT,
                timestamp=datetime(2024, 1, 15, 10, 30, 0),
                elapsed_ms=0,
                content="Hello"
            ),
            TimelineEntry(
                seq=2,
                type=TimelineEntryType.TOOL_CALL,
                timestamp=datetime(2024, 1, 15, 10, 30, 1),
                elapsed_ms=1000,
                tool="Bash"
            ),
        ]

        report = create_fixture_report([test])
        html = builder.build(report)

        assert 'class="timeline"' in html
        assert "Timeline (1 tool calls)" in html

    def test_build_includes_reproduce_section(self):
        """Test that reproduce section is included."""
        builder = HTMLReportBuilder()
        report = create_fixture_report()
        html = builder.build(report)

        assert 'class="reproduce-section"' in html
        assert "Reproduce This Test" in html
        assert "cd /path" in html

    def test_build_includes_debug_section(self):
        """Test that debug section is included."""
        builder = HTMLReportBuilder()
        report = create_fixture_report()
        html = builder.build(report)

        assert "Debug Information" in html

    def test_build_includes_assessment_section(self):
        """Test that assessment section placeholder is included."""
        builder = HTMLReportBuilder()
        report = create_fixture_report()
        html = builder.build(report)

        assert 'class="agent-assessment-section"' in html
        assert "Agent Assessment" in html

    def test_html_escaping(self):
        """Test that special characters are escaped."""
        builder = HTMLReportBuilder()
        test = create_minimal_test_result()
        test.test_name = "<script>alert('xss')</script>"
        test.description = "Test with <dangerous> characters & symbols"

        report = create_fixture_report([test])
        html = builder.build(report)

        # Should be escaped
        assert "&lt;script&gt;" in html
        assert "&lt;dangerous&gt;" in html
        assert "alert('xss')" not in html or "&lt;script&gt;" in html

    def test_first_tab_is_active(self):
        """Test that first tab is marked as active."""
        builder = HTMLReportBuilder()
        tests = [
            create_minimal_test_result("test-1", "Test One"),
            create_minimal_test_result("test-2", "Test Two"),
        ]
        report = create_fixture_report(tests)
        html = builder.build(report)

        # Check first tab content is active
        assert 'id="test-1" class="tab-content active"' in html
        # Check second tab content is not active
        assert 'id="test-2" class="tab-content"' in html
        assert 'id="test-2" class="tab-content active"' not in html


class TestHTMLReportBuilderTransforms:
    """Tests for internal transform methods."""

    def test_transform_header(self):
        """Test _transform_header method."""
        builder = HTMLReportBuilder()
        report = create_fixture_report()
        header = builder._transform_header(report)

        assert header.fixture_name == "Test Fixture"
        assert header.package == "sc-startup"
        assert header.total_tests == 1
        assert "1 passed" in header.summary_text

    def test_transform_tabs(self):
        """Test _transform_tabs method."""
        builder = HTMLReportBuilder()
        tests = [
            create_minimal_test_result("test-1", "Test One"),
            create_minimal_test_result("test-2", "Test Two"),
        ]
        report = create_fixture_report(tests)
        tabs = builder._transform_tabs(report)

        assert len(tabs) == 2
        assert tabs[0].tab_id == "test-1"
        assert tabs[0].is_active is True
        assert tabs[1].tab_id == "test-2"
        assert tabs[1].is_active is False

    def test_transform_expectation(self):
        """Test _transform_expectation method."""
        builder = HTMLReportBuilder()
        exp = Expectation(
            id="exp-001",
            description="Should call Bash",
            type=ExpectationType.TOOL_CALL,
            status=TestStatus.PASS,
            expected={"tool": "Bash", "pattern": ".*"},
            actual={"tool": "Bash", "command": "ls -la"}
        )
        exp_display = builder._transform_expectation(exp)

        assert exp_display.exp_id == "exp-001"
        assert exp_display.description == "Should call Bash"
        assert exp_display.status == TestStatus.PASS
        assert exp_display.has_details is True

    def test_transform_timeline(self):
        """Test _transform_timeline method."""
        builder = HTMLReportBuilder()
        test = create_minimal_test_result()
        test.timeline = [
            TimelineEntry(
                seq=1,
                type=TimelineEntryType.TOOL_CALL,
                timestamp=datetime(2024, 1, 15, 10, 30, 0),
                elapsed_ms=0,
                tool="Bash"
            ),
            TimelineEntry(
                seq=2,
                type=TimelineEntryType.TOOL_CALL,
                timestamp=datetime(2024, 1, 15, 10, 30, 1),
                elapsed_ms=1000,
                tool="Read"
            ),
        ]

        timeline = builder._transform_timeline(test, 1)

        assert timeline.timeline_id == "timeline-1"
        assert len(timeline.entries) == 2
        assert timeline.tool_call_count == 2
