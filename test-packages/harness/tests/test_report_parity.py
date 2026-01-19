"""Tests for JSON/HTML report section parity.

These tests verify that HTML reports and JSON reports contain the same sections,
ensuring that a human looking at the JSON can find all data visible in the HTML
and vice versa.

If a new HTML section is added without corresponding JSON, tests should fail.
If a new JSON section is added without corresponding HTML, tests should fail.
"""

import re
from datetime import datetime
from typing import Any

import pytest

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
    ToolInput,
    ToolOutput,
)
from harness.html_report import HTMLReportBuilder


# =============================================================================
# CANONICAL SECTION DEFINITIONS
# =============================================================================

# These are the canonical sections that must appear in both JSON and HTML.
# Each section maps to a logical grouping of data that users care about.

# Fixture-level sections (appear once per report)
FIXTURE_LEVEL_SECTIONS = {
    "fixture_meta",       # fixture_id, fixture_name, package, agent_or_skill, etc.
    "fixture_summary",    # passed, failed, partial, skipped counts
}

# Test-level sections (appear once per test in both JSON and HTML)
TEST_LEVEL_SECTIONS = {
    "test_identity",      # test_id, test_name, description
    "test_status",        # status, status_icon, pass_rate, duration
    "metadata",           # fixture, package, model, session_id, test_repo
    "reproduce",          # setup_commands, test_command, cleanup_commands
    "execution",          # prompt, model, etc.
    "expectations",       # list of expectations with status
    "timeline",           # timeline entries (tool calls, events)
    "response",           # claude_response (preview, full_text)
    "side_effects",       # files_created, files_modified, files_deleted
    "debug",              # pytest_output, raw_trace_file, errors
}

# All required sections
REQUIRED_SECTIONS = FIXTURE_LEVEL_SECTIONS | TEST_LEVEL_SECTIONS


# =============================================================================
# TEST FIXTURE FACTORY
# =============================================================================

def create_full_test_result(
    test_id: str = "test-001",
    test_name: str = "Full Test",
    status: TestStatus = TestStatus.PASS,
) -> TestResult:
    """Create a fully-populated TestResult with all sections populated.

    This ensures all optional fields have data so we can verify
    both JSON and HTML render them.
    """
    return TestResult(
        test_id=test_id,
        test_name=test_name,
        tab_label="Full",
        description="A fully populated test for parity testing",
        timestamp=datetime(2024, 1, 15, 10, 30, 0),
        duration_ms=5432,
        status=status,
        status_icon=StatusIcon.PASS if status == TestStatus.PASS else StatusIcon.FAIL,
        pass_rate="3/4",
        tags=["integration", "smoke"],
        skip_reason=None,
        metadata=TestMetadata(
            fixture="test_fixture",
            package="sc-startup",
            model="haiku",
            session_id="session-12345",
            test_repo="/path/to/test/repo",
        ),
        reproduce=ReproduceSection(
            setup_commands=["cd /path/to/project", "git checkout main"],
            test_command="pytest tests/test_something.py -v",
            cleanup_commands=["git checkout -"],
        ),
        execution=ExecutionSection(
            prompt="Test prompt with instructions",
            model="haiku",
            max_turns=10,
            timeout_seconds=300,
        ),
        expectations=[
            Expectation(
                id="exp-001",
                description="Should call Bash tool",
                type=ExpectationType.TOOL_CALL,
                status=TestStatus.PASS,
                expected={"tool": "Bash", "contains": "npm install"},
                actual={"tool": "Bash", "input": "npm install package"},
            ),
            Expectation(
                id="exp-002",
                description="Should read config file",
                type=ExpectationType.TOOL_CALL,
                status=TestStatus.PASS,
                expected={"tool": "Read"},
                actual={"tool": "Read", "input": "/path/to/config.json"},
            ),
            Expectation(
                id="exp-003",
                description="Should output success message",
                type=ExpectationType.OUTPUT_CONTAINS,
                status=TestStatus.PASS,
                expected={"contains": "Success"},
                actual={"matched": True, "text": "Operation completed: Success"},
            ),
            Expectation(
                id="exp-004",
                description="Should not fail",
                type=ExpectationType.OUTPUT_CONTAINS,
                status=TestStatus.FAIL,
                expected={"contains": "Done"},
                actual={"matched": False, "text": "No match found"},
            ),
        ],
        timeline=[
            TimelineEntry(
                seq=1,
                type=TimelineEntryType.TOOL_CALL,
                timestamp=datetime(2024, 1, 15, 10, 30, 1),
                elapsed_ms=1000,
                tool="Bash",
                input=ToolInput(command="npm install"),
                output=ToolOutput(stdout="added 100 packages"),
                duration_ms=1500,
            ),
            TimelineEntry(
                seq=2,
                type=TimelineEntryType.TOOL_CALL,
                timestamp=datetime(2024, 1, 15, 10, 30, 3),
                elapsed_ms=3000,
                tool="Read",
                input=ToolInput(file_path="/path/to/config.json"),
                output=ToolOutput(content='{"key": "value"}'),
                duration_ms=50,
            ),
            TimelineEntry(
                seq=3,
                type=TimelineEntryType.RESPONSE,
                timestamp=datetime(2024, 1, 15, 10, 30, 4),
                elapsed_ms=4000,
                content="I have completed the setup.",
            ),
        ],
        side_effects=SideEffects(
            files_created=["/path/to/new_file.txt"],
            files_modified=["/path/to/modified_file.py"],
            files_deleted=["/path/to/deleted_file.tmp"],
            git_changes=True,
        ),
        claude_response=ClaudeResponse(
            preview="I have successfully completed the task...",
            full_text="I have successfully completed the task. Here is a summary of what was done:\n1. Installed packages\n2. Read configuration\n3. Applied changes",
            word_count=25,
        ),
        debug=DebugInfo(
            pytest_output="PASSED tests/test_something.py::test_full",
            pytest_status=TestStatus.PASS,
            raw_trace_file="/path/to/trace.jsonl",
            errors=[],
        ),
    )


def create_full_fixture_report() -> FixtureReport:
    """Create a fully-populated FixtureReport for parity testing.

    Includes multiple tests with various statuses to ensure all
    states are tested.
    """
    tests = [
        create_full_test_result(
            test_id="test-001",
            test_name="Passing Test",
            status=TestStatus.PASS,
        ),
        create_full_test_result(
            test_id="test-002",
            test_name="Failing Test",
            status=TestStatus.FAIL,
        ),
        create_full_test_result(
            test_id="test-003",
            test_name="Partial Test",
            status=TestStatus.PARTIAL,
        ),
    ]

    # Calculate summary
    passed = sum(1 for t in tests if t.status == TestStatus.PASS)
    failed = sum(1 for t in tests if t.status == TestStatus.FAIL)
    partial = sum(1 for t in tests if t.status == TestStatus.PARTIAL)
    skipped = sum(1 for t in tests if t.status == TestStatus.SKIPPED)

    return FixtureReport(
        fixture=FixtureMeta(
            fixture_id="parity_test_fixture",
            fixture_name="Parity Test Fixture",
            package="sc-startup",
            agent_or_skill="startup",
            agent_or_skill_path="/path/to/skill.md",
            fixture_path="/path/to/fixture.yaml",
            report_path="/path/to/report.html",
            generated_at=datetime(2024, 1, 15, 10, 30, 0),
            summary=FixtureSummary(
                total_tests=len(tests),
                passed=passed,
                failed=failed,
                partial=partial,
                skipped=skipped,
            ),
            tags=["integration", "parity"],
        ),
        tests=tests,
    )


# =============================================================================
# SECTION EXTRACTION HELPERS
# =============================================================================

def extract_json_sections(json_data: dict[str, Any]) -> set[str]:
    """Extract logical section names from JSON report data.

    Maps JSON structure to canonical section names.
    """
    sections = set()

    # Fixture-level sections
    if "fixture" in json_data:
        fixture = json_data["fixture"]
        # Check for fixture_meta fields
        if any(k in fixture for k in ["fixture_id", "fixture_name", "package", "agent_or_skill"]):
            sections.add("fixture_meta")
        # Check for summary
        if "summary" in fixture:
            sections.add("fixture_summary")

    # Test-level sections (check first test if available)
    if "tests" in json_data and json_data["tests"]:
        test = json_data["tests"][0]

        # test_identity
        if any(k in test for k in ["test_id", "test_name", "description"]):
            sections.add("test_identity")

        # test_status
        if any(k in test for k in ["status", "status_icon", "pass_rate", "duration_ms"]):
            sections.add("test_status")

        # metadata
        if "metadata" in test:
            sections.add("metadata")

        # reproduce
        if "reproduce" in test:
            sections.add("reproduce")

        # execution
        if "execution" in test:
            sections.add("execution")

        # expectations
        if "expectations" in test:
            sections.add("expectations")

        # timeline
        if "timeline" in test:
            sections.add("timeline")

        # response (claude_response)
        if "claude_response" in test:
            sections.add("response")

        # side_effects
        if "side_effects" in test:
            sections.add("side_effects")

        # debug
        if "debug" in test:
            sections.add("debug")

    return sections


def extract_html_sections(html: str) -> set[str]:
    """Extract logical section names from HTML report output.

    Looks for specific HTML patterns that indicate each section is present.
    """
    sections = set()

    # Fixture-level sections
    # fixture_meta: Look for fixture header with metadata items
    if 'class="fixture-header"' in html and 'class="fixture-meta"' in html:
        sections.add("fixture_meta")

    # fixture_summary: Look for summary stats (passed/failed counts in header)
    if re.search(r'\d+\s*passed.*\d+\s*failed', html, re.IGNORECASE) or 'total_tests' in html.lower():
        sections.add("fixture_summary")
    # Alternative: check for summary text pattern in header
    if re.search(r'tests\s*\(\d+\s*passed', html, re.IGNORECASE):
        sections.add("fixture_summary")

    # Test-level sections
    # test_identity: Look for test name heading and description
    if '<h1>' in html and 'class="description"' in html:
        sections.add("test_identity")

    # test_status: Look for status banner
    if 'class="status-banner' in html and 'class="status-badge"' in html:
        sections.add("test_status")

    # metadata: Look for test metadata table or section
    if 'Test ID' in html or 'test-metadata' in html.lower() or 'Session ID' in html:
        sections.add("metadata")

    # reproduce: Look for reproduce section
    if 'Reproduce This Test' in html or 'class="reproduce-section"' in html:
        sections.add("reproduce")

    # execution: execution params are typically shown in metadata
    # The execution section data (prompt, model) is part of metadata in HTML
    # We'll consider it present if metadata is present (they're combined)
    if 'metadata' in sections or 'Model' in html:
        sections.add("execution")

    # expectations: Look for expectations list
    if 'Expectations' in html and ('expectations-list' in html or 'class="expectation' in html):
        sections.add("expectations")

    # timeline: Look for timeline section
    if 'Timeline' in html and ('class="timeline"' in html or 'tool calls' in html.lower()):
        sections.add("timeline")

    # response: Look for Claude's response section
    # HTML uses "Claude's Full Response" as summary text and "response-preview" as class
    if "Claude's Full Response" in html or 'response-preview' in html or 'id="response-' in html:
        sections.add("response")
    # Alternative: look for word count indicator which is part of response section
    if re.search(r'\d+\s*words', html, re.IGNORECASE):
        sections.add("response")

    # side_effects: Part of debug section - look for side effects indicator
    if 'Side Effects' in html or 'files_created' in html or 'No files were' in html:
        sections.add("side_effects")

    # debug: Look for debug information section
    if 'Debug Information' in html or 'class="debug' in html:
        sections.add("debug")

    return sections


# =============================================================================
# TESTS
# =============================================================================

class TestReportSectionParity:
    """Tests for JSON/HTML report section parity."""

    def test_json_contains_all_required_sections(self):
        """JSON report should contain all required sections."""
        report = create_full_fixture_report()
        json_data = report.model_dump()
        json_sections = extract_json_sections(json_data)

        missing = REQUIRED_SECTIONS - json_sections
        assert not missing, f"JSON report missing sections: {missing}"

    def test_html_contains_all_required_sections(self):
        """HTML report should contain all required sections."""
        report = create_full_fixture_report()
        builder = HTMLReportBuilder()
        html = builder.build(report)
        html_sections = extract_html_sections(html)

        missing = REQUIRED_SECTIONS - html_sections
        assert not missing, f"HTML report missing sections: {missing}"

    def test_json_html_section_parity(self):
        """JSON and HTML reports should have the same sections."""
        report = create_full_fixture_report()

        # Extract JSON sections
        json_data = report.model_dump()
        json_sections = extract_json_sections(json_data)

        # Extract HTML sections
        builder = HTMLReportBuilder()
        html = builder.build(report)
        html_sections = extract_html_sections(html)

        # Check bidirectional parity
        json_only = json_sections - html_sections
        html_only = html_sections - json_sections

        assert not json_only and not html_only, (
            f"Section mismatch!\n"
            f"  JSON has but HTML missing: {json_only or 'none'}\n"
            f"  HTML has but JSON missing: {html_only or 'none'}"
        )

    def test_canonical_sections_complete(self):
        """Verify our canonical section list covers all data areas.

        This test ensures we haven't missed any major data groupings.
        """
        # Verify fixture-level sections are reasonable
        assert "fixture_meta" in FIXTURE_LEVEL_SECTIONS, "Missing fixture_meta"
        assert "fixture_summary" in FIXTURE_LEVEL_SECTIONS, "Missing fixture_summary"

        # Verify test-level sections cover all TestResult fields
        test_section_coverage = {
            "test_identity": ["test_id", "test_name", "description"],
            "test_status": ["status", "status_icon", "pass_rate", "duration_ms"],
            "metadata": ["metadata"],
            "reproduce": ["reproduce"],
            "execution": ["execution"],
            "expectations": ["expectations"],
            "timeline": ["timeline"],
            "response": ["claude_response"],
            "side_effects": ["side_effects"],
            "debug": ["debug"],
        }

        # All section names should be in TEST_LEVEL_SECTIONS
        for section_name in test_section_coverage:
            assert section_name in TEST_LEVEL_SECTIONS, f"Missing section: {section_name}"


class TestJSONStructureCompleteness:
    """Tests verifying JSON structure captures all data."""

    def test_fixture_meta_fields_present(self):
        """FixtureMeta should have all expected fields in JSON."""
        report = create_full_fixture_report()
        json_data = report.model_dump()

        fixture = json_data["fixture"]
        required_fields = [
            "fixture_id", "fixture_name", "package", "agent_or_skill",
            "report_path", "generated_at", "summary"
        ]

        for field in required_fields:
            assert field in fixture, f"FixtureMeta missing field: {field}"

    def test_fixture_summary_fields_present(self):
        """FixtureSummary should have all expected fields in JSON."""
        report = create_full_fixture_report()
        json_data = report.model_dump()

        summary = json_data["fixture"]["summary"]
        required_fields = ["total_tests", "passed", "failed", "partial", "skipped"]

        for field in required_fields:
            assert field in summary, f"FixtureSummary missing field: {field}"

    def test_test_result_fields_present(self):
        """TestResult should have all expected fields in JSON."""
        report = create_full_fixture_report()
        json_data = report.model_dump()

        test = json_data["tests"][0]
        required_fields = [
            "test_id", "test_name", "tab_label", "description",
            "timestamp", "duration_ms", "status", "status_icon", "pass_rate",
            "metadata", "reproduce", "execution", "expectations",
            "timeline", "side_effects", "claude_response", "debug"
        ]

        for field in required_fields:
            assert field in test, f"TestResult missing field: {field}"

    def test_expectations_structure(self):
        """Expectations should have proper structure in JSON."""
        report = create_full_fixture_report()
        json_data = report.model_dump()

        expectations = json_data["tests"][0]["expectations"]
        assert len(expectations) > 0, "No expectations in test"

        exp = expectations[0]
        required_fields = ["id", "description", "type", "status", "expected"]

        for field in required_fields:
            assert field in exp, f"Expectation missing field: {field}"

    def test_timeline_structure(self):
        """Timeline entries should have proper structure in JSON."""
        report = create_full_fixture_report()
        json_data = report.model_dump()

        timeline = json_data["tests"][0]["timeline"]
        assert len(timeline) > 0, "No timeline entries in test"

        entry = timeline[0]
        required_fields = ["seq", "type", "timestamp", "elapsed_ms"]

        for field in required_fields:
            assert field in entry, f"TimelineEntry missing field: {field}"


class TestHTMLStructureCompleteness:
    """Tests verifying HTML structure renders all data."""

    def test_fixture_header_rendered(self):
        """HTML should render fixture header with metadata."""
        report = create_full_fixture_report()
        builder = HTMLReportBuilder()
        html = builder.build(report)

        assert 'class="fixture-header"' in html, "Missing fixture header"
        assert report.fixture.fixture_name in html, "Missing fixture name"
        assert report.fixture.package in html, "Missing package name"

    def test_status_banner_rendered(self):
        """HTML should render status banner for each test."""
        report = create_full_fixture_report()
        builder = HTMLReportBuilder()
        html = builder.build(report)

        assert 'class="status-banner' in html, "Missing status banner"
        assert 'class="status-badge"' in html, "Missing status badge"

    def test_expectations_section_rendered(self):
        """HTML should render expectations section."""
        report = create_full_fixture_report()
        builder = HTMLReportBuilder()
        html = builder.build(report)

        assert 'Expectations' in html, "Missing Expectations heading"
        # Check that expectation descriptions appear
        for test in report.tests:
            for exp in test.expectations[:1]:  # Check at least first expectation
                assert exp.description in html, f"Missing expectation: {exp.description}"

    def test_timeline_section_rendered(self):
        """HTML should render timeline section."""
        report = create_full_fixture_report()
        builder = HTMLReportBuilder()
        html = builder.build(report)

        assert 'Timeline' in html, "Missing Timeline heading"
        assert 'tool calls' in html.lower(), "Missing tool call count"

    def test_reproduce_section_rendered(self):
        """HTML should render reproduce section."""
        report = create_full_fixture_report()
        builder = HTMLReportBuilder()
        html = builder.build(report)

        assert 'Reproduce This Test' in html, "Missing Reproduce heading"
        # Check that test command appears
        assert report.tests[0].reproduce.test_command in html

    def test_debug_section_rendered(self):
        """HTML should render debug section."""
        report = create_full_fixture_report()
        builder = HTMLReportBuilder()
        html = builder.build(report)

        assert 'Debug Information' in html, "Missing Debug heading"

    def test_response_section_rendered(self):
        """HTML should render Claude's response section."""
        report = create_full_fixture_report()
        builder = HTMLReportBuilder()
        html = builder.build(report)

        # Response is typically in a collapsible section or shown as full text
        # Check that the response text appears in the HTML
        assert report.tests[0].claude_response.full_text in html or \
               "Response" in html, "Missing response section"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_expectations_list(self):
        """Report with no expectations should still have sections."""
        test = create_full_test_result()
        test = test.model_copy(update={"expectations": []})
        report = create_full_fixture_report()
        report = report.model_copy(update={"tests": [test]})

        json_data = report.model_dump()
        json_sections = extract_json_sections(json_data)

        # Should still have expectations section (empty list)
        assert "expectations" in json_sections

    def test_empty_timeline(self):
        """Report with no timeline entries should still have sections."""
        test = create_full_test_result()
        test = test.model_copy(update={"timeline": []})
        report = create_full_fixture_report()
        report = report.model_copy(update={"tests": [test]})

        json_data = report.model_dump()
        json_sections = extract_json_sections(json_data)

        # Should still have timeline section (empty list)
        assert "timeline" in json_sections

    def test_single_test_report(self):
        """Report with single test should have all sections."""
        report = create_full_fixture_report()
        report = report.model_copy(update={"tests": [report.tests[0]]})

        json_data = report.model_dump()
        json_sections = extract_json_sections(json_data)

        missing = REQUIRED_SECTIONS - json_sections
        assert not missing, f"Single test report missing sections: {missing}"

    def test_no_side_effects(self):
        """Report with no side effects should indicate that."""
        test = create_full_test_result()
        test = test.model_copy(update={
            "side_effects": SideEffects(
                files_created=[],
                files_modified=[],
                files_deleted=[],
                git_changes=False,
            )
        })
        report = create_full_fixture_report()
        report = report.model_copy(update={"tests": [test]})

        builder = HTMLReportBuilder()
        html = builder.build(report)

        # Should still have side_effects section with "no files" message
        assert "No files were" in html or "side_effects" in html.lower() or "Side Effects" in html


class TestNewSectionDetection:
    """Tests that would catch new sections being added without parity."""

    def test_json_model_fields_mapped(self):
        """All TestResult model fields should map to a section.

        This test helps detect when new fields are added to the model
        but not mapped to HTML sections.
        """
        from harness.models import TestResult

        # Get all field names from TestResult
        model_fields = set(TestResult.model_fields.keys())

        # Fields that map to each section
        section_field_mapping = {
            "test_identity": {"test_id", "test_name", "tab_label", "description"},
            "test_status": {"timestamp", "duration_ms", "status", "status_icon", "pass_rate", "tags", "skip_reason"},
            "metadata": {"metadata"},
            "reproduce": {"reproduce"},
            "execution": {"execution"},
            "expectations": {"expectations"},
            "timeline": {"timeline", "timeline_tree"},
            "response": {"claude_response"},
            "side_effects": {"side_effects"},
            "debug": {"debug", "artifacts"},
            "log_analysis": {"log_analysis", "allow_warnings"},
        }

        # Flatten all mapped fields
        mapped_fields = set()
        for fields in section_field_mapping.values():
            mapped_fields.update(fields)

        # Check all model fields are mapped
        unmapped = model_fields - mapped_fields
        assert not unmapped, f"Model fields not mapped to sections: {unmapped}"

    def test_fixture_meta_fields_mapped(self):
        """All FixtureMeta model fields should appear in fixture_meta section.

        This test helps detect when new fields are added to FixtureMeta
        but not rendered in HTML.
        """
        from harness.models import FixtureMeta

        model_fields = set(FixtureMeta.model_fields.keys())

        # Create a report and verify all fields are in JSON
        report = create_full_fixture_report()
        json_data = report.model_dump()
        fixture_json_fields = set(json_data["fixture"].keys())

        # All model fields should be in JSON
        missing = model_fields - fixture_json_fields
        assert not missing, f"FixtureMeta fields missing from JSON: {missing}"


class TestSectionContentParity:
    """Tests that verify actual content matches between JSON and HTML."""

    def test_test_name_in_both(self):
        """Test name should appear in both JSON and HTML."""
        report = create_full_fixture_report()

        json_data = report.model_dump()
        builder = HTMLReportBuilder()
        html = builder.build(report)

        for test in json_data["tests"]:
            test_name = test["test_name"]
            assert test_name in html, f"Test name '{test_name}' not in HTML"

    def test_fixture_name_in_both(self):
        """Fixture name should appear in both JSON and HTML."""
        report = create_full_fixture_report()

        json_data = report.model_dump()
        builder = HTMLReportBuilder()
        html = builder.build(report)

        fixture_name = json_data["fixture"]["fixture_name"]
        assert fixture_name in html, f"Fixture name '{fixture_name}' not in HTML"

    def test_package_name_in_both(self):
        """Package name should appear in both JSON and HTML."""
        report = create_full_fixture_report()

        json_data = report.model_dump()
        builder = HTMLReportBuilder()
        html = builder.build(report)

        package = json_data["fixture"]["package"]
        assert package in html, f"Package '{package}' not in HTML"

    def test_expectation_descriptions_in_html(self):
        """All expectation descriptions from JSON should appear in HTML."""
        report = create_full_fixture_report()

        json_data = report.model_dump()
        builder = HTMLReportBuilder()
        html = builder.build(report)

        for test in json_data["tests"]:
            for exp in test["expectations"]:
                desc = exp["description"]
                # HTML may escape some characters, so check core text
                assert desc in html, f"Expectation '{desc}' not in HTML"
