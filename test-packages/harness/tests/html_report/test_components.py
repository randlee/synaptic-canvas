"""Tests for html_report.components module.

These tests verify the HTML component builders generate correct output.
"""

import pytest
from datetime import datetime

from harness.models import TestStatus, TimelineEntryType
from harness.html_report.models import (
    BuilderConfig,
    HeaderDisplayModel,
    StatusBannerDisplayModel,
    ExpectationDisplayModel,
    ExpectationsDisplayModel,
    TimelineItemDisplayModel,
    TimelineDisplayModel,
    ReproduceDisplayModel,
    DebugDisplayModel,
    AssessmentDisplayModel,
    TabDisplayModel,
)
from harness.html_report.components import (
    BaseBuilder,
    CopyButtonBuilder,
    HeaderBuilder,
    TabsBuilder,
    StatusBannerBuilder,
    ExpectationsBuilder,
    TimelineBuilder,
    ReproduceBuilder,
    DebugBuilder,
    AssessmentBuilder,
)
from harness.html_report.components.base import FileLinkBuilder


class TestCopyButtonBuilder:
    """Tests for CopyButtonBuilder utility."""

    def test_basic_copy_button(self):
        """Test basic copy button generation."""
        html = CopyButtonBuilder.build(
            tooltip="Copy content",
            onclick="copyElement('test')"
        )
        assert 'class="copy-icon-btn"' in html
        assert 'data-tooltip="Copy content"' in html
        assert "copyElement('test')" in html
        assert "clipboard" in html  # SVG class
        assert "checkmark" in html  # SVG class

    def test_copy_button_with_stop_propagation(self):
        """Test copy button with event.stopPropagation()."""
        html = CopyButtonBuilder.build(
            tooltip="Copy",
            onclick="copyElement('test')",
            stop_propagation=True
        )
        assert "event.stopPropagation();" in html


class TestFileLinkBuilder:
    """Tests for FileLinkBuilder utility."""

    def test_vscode_link(self):
        """Test VS Code file link generation."""
        html = FileLinkBuilder.build("/path/to/file.js")
        assert 'href="vscode://file//path/to/file.js"' in html
        assert 'class="file-link vscode"' in html
        assert 'title="Open in VS Code"' in html

    def test_pycharm_link(self):
        """Test PyCharm file link generation."""
        html = FileLinkBuilder.build("/path/to/file.py")
        assert 'href="pycharm://open?file=' in html
        assert 'class="file-link pycharm"' in html
        assert 'title="Open in PyCharm"' in html

    def test_link_with_line_number(self):
        """Test file link with line number."""
        html = FileLinkBuilder.build("/path/to/file.py", line_number=42)
        assert "&line=42" in html

    def test_html_escaping(self):
        """Test that file names are HTML escaped."""
        html = FileLinkBuilder.build("/path/to/<file>.py", display_text="<file>.py")
        assert "&lt;file&gt;.py" in html


class TestHeaderBuilder:
    """Tests for HeaderBuilder component."""

    def test_header_structure(self):
        """Test header HTML structure."""
        builder = HeaderBuilder()
        data = HeaderDisplayModel(
            fixture_name="Test Fixture",
            package="sc-startup",
            agent_or_skill="startup",
            total_tests=5,
            summary_text="3 passed, 2 failed",
            generated_at=datetime(2024, 1, 15, 10, 30, 0),
            report_path="/path/to/report.html"
        )
        html = builder.build(data)

        assert 'class="fixture-header"' in html
        assert "Test Fixture Test Suite" in html
        assert "sc-startup" in html
        assert "startup" in html
        assert "5 tests" in html
        assert "3 passed, 2 failed" in html

    def test_header_with_file_links(self):
        """Test header with file path links."""
        builder = HeaderBuilder()
        data = HeaderDisplayModel(
            fixture_name="Test Fixture",
            package="sc-startup",
            agent_or_skill="startup",
            agent_or_skill_path="/path/to/agent.py",
            total_tests=3,
            summary_text="3 passed",
            generated_at=datetime(2024, 1, 15, 10, 30, 0),
            report_path="/path/to/report.html"
        )
        html = builder.build(data)
        assert "pycharm://open" in html  # Should have PyCharm link for .py


class TestTabsBuilder:
    """Tests for TabsBuilder component."""

    def test_tabs_header(self):
        """Test tabs header generation."""
        builder = TabsBuilder()
        tabs = [
            TabDisplayModel(tab_id="test-1", tab_label="Test 1", status=TestStatus.PASS, is_active=True),
            TabDisplayModel(tab_id="test-2", tab_label="Test 2", status=TestStatus.FAIL, is_active=False),
        ]
        html = builder.build(tabs)

        assert 'class="tabs-header"' in html
        assert 'onclick="switchTab(\'test-1\')"' in html
        assert 'onclick="switchTab(\'test-2\')"' in html
        assert "active" in html
        assert "Test 1" in html
        assert "Test 2" in html

    def test_tab_content_wrapper(self):
        """Test tab content wrapper generation."""
        builder = TabsBuilder()
        html = builder.build_tab_content_wrapper(
            "test-1",
            "<p>Content</p>",
            is_active=True
        )
        assert 'id="test-1"' in html
        assert 'class="tab-content active"' in html
        assert "<p>Content</p>" in html


class TestStatusBannerBuilder:
    """Tests for StatusBannerBuilder component."""

    def test_pass_banner(self):
        """Test PASS status banner."""
        builder = StatusBannerBuilder()
        data = StatusBannerDisplayModel(
            status=TestStatus.PASS,
            passed_count=5,
            total_count=5,
            duration_seconds=1.5,
            timestamp=datetime(2024, 1, 15, 10, 30, 0)
        )
        html = builder.build(data)

        assert 'class="status-banner pass"' in html
        assert "PASS" in html
        assert "5 of 5 expectations passed" in html
        assert "1.50s" in html

    def test_fail_banner(self):
        """Test FAIL status banner."""
        builder = StatusBannerBuilder()
        data = StatusBannerDisplayModel(
            status=TestStatus.FAIL,
            passed_count=0,
            total_count=3,
            duration_seconds=0.5,
            timestamp=datetime(2024, 1, 15, 10, 30, 0)
        )
        html = builder.build(data)

        assert 'class="status-banner fail"' in html
        assert "FAIL" in html


class TestExpectationsBuilder:
    """Tests for ExpectationsBuilder component."""

    def test_expectations_list(self):
        """Test expectations list generation."""
        builder = ExpectationsBuilder()
        data = ExpectationsDisplayModel(
            test_index=1,
            expectations=[
                ExpectationDisplayModel(
                    exp_id="exp-1",
                    description="Should call Bash",
                    status=TestStatus.PASS,
                    details_text="Type: tool_call"
                ),
                ExpectationDisplayModel(
                    exp_id="exp-2",
                    description="Should not fail",
                    status=TestStatus.FAIL,
                    details_text="Expected true, got false",
                    has_details=True,
                    expected_content="true",
                    actual_content="false"
                ),
            ]
        )
        html = builder.build(data)

        assert 'class="expectations-list"' in html
        assert "1 passed" in html
        assert "1 failed" in html
        assert "Should call Bash" in html
        assert "Should not fail" in html
        assert 'data-exp-id="exp-1"' in html
        assert 'data-exp-id="exp-2"' in html

    def test_expectation_with_details(self):
        """Test expectation with expandable details."""
        builder = ExpectationsBuilder()
        data = ExpectationsDisplayModel(
            test_index=1,
            expectations=[
                ExpectationDisplayModel(
                    exp_id="exp-1",
                    description="Test",
                    status=TestStatus.FAIL,
                    details_text="Details",
                    has_details=True,
                    expected_content="expected value",
                    actual_content="actual value"
                ),
            ]
        )
        html = builder.build(data)

        assert 'class="expectation-expanded"' in html
        assert "Expected" in html
        assert "Actual" in html
        assert "expected value" in html
        assert "actual value" in html


class TestTimelineBuilder:
    """Tests for TimelineBuilder component."""

    def test_timeline_structure(self):
        """Test timeline HTML structure."""
        builder = TimelineBuilder()
        data = TimelineDisplayModel(
            timeline_id="timeline-1",
            entries=[
                TimelineItemDisplayModel(
                    seq=1,
                    entry_type=TimelineEntryType.PROMPT,
                    elapsed_ms=0,
                    content="Hello"
                ),
                TimelineItemDisplayModel(
                    seq=2,
                    entry_type=TimelineEntryType.TOOL_CALL,
                    tool_name="Bash",
                    elapsed_ms=100,
                    command="echo hello",
                    output="hello"
                ),
            ],
            tool_call_count=1
        )
        html = builder.build(data)

        assert '<details>' in html
        assert "Timeline (1 tool calls)" in html
        assert 'id="timeline-1"' in html
        assert 'class="timeline-item prompt"' in html
        assert 'class="timeline-item tool_call"' in html
        assert "#1" in html
        assert "#2" in html

    def test_timeline_tool_call_content(self):
        """Test tool call entry content."""
        builder = TimelineBuilder()
        data = TimelineDisplayModel(
            timeline_id="timeline-1",
            entries=[
                TimelineItemDisplayModel(
                    seq=1,
                    entry_type=TimelineEntryType.TOOL_CALL,
                    tool_name="Bash",
                    elapsed_ms=100,
                    command="ls -la",
                    output="file1.txt\nfile2.txt"
                ),
            ],
            tool_call_count=1
        )
        html = builder.build(data)

        assert "$ ls -la" in html
        assert "file1.txt" in html


class TestReproduceBuilder:
    """Tests for ReproduceBuilder component."""

    def test_reproduce_section(self):
        """Test reproduce section generation."""
        builder = ReproduceBuilder()
        data = ReproduceDisplayModel(
            test_index=1,
            setup_commands=["cd /path/to/test", "git checkout main"],
            test_command="claude --model haiku 'Run the test'"
        )
        html = builder.build(data)

        assert 'class="reproduce-section"' in html
        assert "Reproduce This Test" in html
        assert "1. Setup" in html
        assert "2. Run Test" in html
        assert "cd /path/to/test" in html
        assert "claude --model haiku" in html


class TestDebugBuilder:
    """Tests for DebugBuilder component."""

    def test_debug_section(self):
        """Test debug section generation."""
        builder = DebugBuilder()
        data = DebugDisplayModel(
            test_index=1,
            pytest_output="PASSED",
            package="sc-startup",
            test_repo="/path/to/repo",
            side_effects_text="No files were created, modified, or deleted."
        )
        html = builder.build(data)

        assert '<details>' in html
        assert "Debug Information" in html
        assert "PASSED" in html
        assert "Side Effects" in html
        assert "No files were created" in html


class TestAssessmentBuilder:
    """Tests for AssessmentBuilder component."""

    def test_lazy_loading_assessment(self):
        """Test assessment with lazy loading placeholder."""
        builder = AssessmentBuilder()
        data = AssessmentDisplayModel(
            test_index=1,
            test_id="test-001",
            is_embedded=False
        )
        html = builder.build(data)

        assert 'class="agent-assessment-section"' in html
        assert 'data-test-id="test-001"' in html
        assert "Loading assessment..." in html
        assert 'open' not in html  # Should not be open by default

    def test_embedded_assessment(self):
        """Test assessment with embedded content."""
        builder = AssessmentBuilder()
        data = AssessmentDisplayModel(
            test_index=1,
            test_id="test-001",
            content_html="<p>Assessment content</p>",
            model="claude-3-opus",
            timestamp="2024-01-15 10:30:00",
            is_embedded=True
        )
        html = builder.build(data)

        assert 'class="agent-assessment-section visible"' in html
        assert "Assessment content" in html
        assert "Generated by claude-3-opus" in html
        assert "2024-01-15 10:30:00" in html
        assert "open" in html  # Should be open for embedded
