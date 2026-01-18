"""Tests for html_report.models module.

These tests verify the Pydantic display models used for HTML rendering.
"""

import pytest
from datetime import datetime

from harness.models import TestStatus, TimelineEntryType
from harness.html_report.models import (
    BuilderConfig,
    StatusDisplay,
    TimelineTypeDisplay,
    FileLinkDisplay,
    HeaderDisplayModel,
    StatusBannerDisplayModel,
    ExpectationDisplayModel,
    ExpectationsDisplayModel,
    TimelineItemDisplayModel,
    TimelineDisplayModel,
    TabDisplayModel,
)


class TestBuilderConfig:
    """Tests for BuilderConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BuilderConfig()
        assert config.default_editor == "vscode"
        assert config.pycharm_extensions == [".py"]
        assert config.include_source_attribution is True
        assert config.default_collapsed is True
        assert config.enable_lazy_loading is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = BuilderConfig(
            default_editor="pycharm",
            pycharm_extensions=[".py", ".pyi"],
            enable_lazy_loading=False
        )
        assert config.default_editor == "pycharm"
        assert config.pycharm_extensions == [".py", ".pyi"]
        assert config.enable_lazy_loading is False


class TestStatusDisplay:
    """Tests for StatusDisplay computed properties."""

    def test_pass_status(self):
        """Test PASS status display attributes."""
        display = StatusDisplay(status=TestStatus.PASS)
        assert display.css_class == "pass"
        assert display.label == "PASS"
        assert "10003" in display.icon_html  # Checkmark HTML entity

    def test_fail_status(self):
        """Test FAIL status display attributes."""
        display = StatusDisplay(status=TestStatus.FAIL)
        assert display.css_class == "fail"
        assert display.label == "FAIL"
        assert "10060" in display.icon_html  # X HTML entity

    def test_partial_status(self):
        """Test PARTIAL status display attributes."""
        display = StatusDisplay(status=TestStatus.PARTIAL)
        assert display.css_class == "partial"
        assert display.label == "PARTIAL"
        assert "9888" in display.icon_html  # Warning triangle

    def test_skipped_status(self):
        """Test SKIPPED status display attributes."""
        display = StatusDisplay(status=TestStatus.SKIPPED)
        assert display.css_class == "skipped"
        assert display.label == "SKIPPED"

    def test_expectation_icons(self):
        """Test expectation list icons are different from tab icons."""
        display = StatusDisplay(status=TestStatus.PASS)
        # Expectation icons use emoji versions
        assert display.expectation_icon_html != display.icon_html
        assert "9989" in display.expectation_icon_html  # Green checkmark emoji


class TestTimelineTypeDisplay:
    """Tests for TimelineTypeDisplay."""

    def test_prompt_type(self):
        """Test PROMPT type display."""
        display = TimelineTypeDisplay(entry_type=TimelineEntryType.PROMPT)
        assert display.css_class == "prompt"
        assert display.display_label == "Prompt"

    def test_tool_call_type(self):
        """Test TOOL_CALL type display."""
        display = TimelineTypeDisplay(entry_type=TimelineEntryType.TOOL_CALL)
        assert display.css_class == "tool_call"
        assert display.display_label == "Tool Call"

    def test_tool_call_with_name(self):
        """Test TOOL_CALL type with tool name."""
        display = TimelineTypeDisplay(
            entry_type=TimelineEntryType.TOOL_CALL,
            tool_name="Bash"
        )
        assert display.display_label == "Bash"

    def test_response_type(self):
        """Test RESPONSE type display."""
        display = TimelineTypeDisplay(entry_type=TimelineEntryType.RESPONSE)
        assert display.css_class == "response"
        assert display.display_label == "Response"


class TestFileLinkDisplay:
    """Tests for FileLinkDisplay."""

    def test_python_file_opens_in_pycharm(self):
        """Test that .py files are configured for PyCharm."""
        link = FileLinkDisplay(file_path="/path/to/file.py")
        assert link.editor_type == "pycharm"
        assert link.editor_name == "PyCharm"
        assert "pycharm://open" in link.editor_url
        assert "file=/path/to/file.py" in link.editor_url

    def test_other_file_opens_in_vscode(self):
        """Test that non-.py files are configured for VS Code."""
        link = FileLinkDisplay(file_path="/path/to/file.js")
        assert link.editor_type == "vscode"
        assert link.editor_name == "VS Code"
        assert "vscode://file/" in link.editor_url

    def test_line_number_in_url(self):
        """Test that line numbers are included in URL."""
        link = FileLinkDisplay(
            file_path="/path/to/file.py",
            line_number=42
        )
        assert "&line=42" in link.editor_url

    def test_display_text(self):
        """Test custom display text."""
        link = FileLinkDisplay(
            file_path="/path/to/file.py",
            display_text="file.py"
        )
        assert link.label == "file.py"

    def test_default_display_text(self):
        """Test default display text is file path."""
        link = FileLinkDisplay(file_path="/path/to/file.py")
        assert link.label == "/path/to/file.py"


class TestHeaderDisplayModel:
    """Tests for HeaderDisplayModel."""

    def test_header_creation(self):
        """Test creating a header display model."""
        header = HeaderDisplayModel(
            fixture_name="test_fixture",
            package="sc-startup",
            agent_or_skill="startup",
            total_tests=5,
            summary_text="3 passed, 2 failed",
            generated_at=datetime(2024, 1, 15, 10, 30, 0),
            report_path="/path/to/report.html"
        )
        assert header.fixture_name == "test_fixture"
        assert header.package == "sc-startup"
        assert header.total_tests == 5


class TestStatusBannerDisplayModel:
    """Tests for StatusBannerDisplayModel."""

    def test_status_banner_computed_fields(self):
        """Test computed fields on status banner."""
        banner = StatusBannerDisplayModel(
            status=TestStatus.PASS,
            passed_count=5,
            total_count=7,
            duration_seconds=2.5,
            timestamp=datetime(2024, 1, 15, 10, 30, 0)
        )
        assert banner.expectations_text == "5 of 7 expectations passed"
        assert banner.formatted_duration == "2.50s"
        assert banner.formatted_timestamp == "2024-01-15 10:30:00"
        assert banner.status_display.css_class == "pass"


class TestExpectationsDisplayModel:
    """Tests for ExpectationsDisplayModel."""

    def test_expectations_counts(self):
        """Test pass/fail count computation."""
        expectations = ExpectationsDisplayModel(
            test_index=1,
            expectations=[
                ExpectationDisplayModel(
                    exp_id="exp-1",
                    description="Test 1",
                    status=TestStatus.PASS,
                    details_text="Passed"
                ),
                ExpectationDisplayModel(
                    exp_id="exp-2",
                    description="Test 2",
                    status=TestStatus.PASS,
                    details_text="Passed"
                ),
                ExpectationDisplayModel(
                    exp_id="exp-3",
                    description="Test 3",
                    status=TestStatus.FAIL,
                    details_text="Failed"
                ),
            ]
        )
        assert expectations.passed_count == 2
        assert expectations.failed_count == 1


class TestTimelineItemDisplayModel:
    """Tests for TimelineItemDisplayModel."""

    def test_formatted_elapsed_ms(self):
        """Test elapsed time formatting under 1 second."""
        item = TimelineItemDisplayModel(
            seq=1,
            entry_type=TimelineEntryType.PROMPT,
            elapsed_ms=500
        )
        assert item.formatted_elapsed == "+500ms"

    def test_formatted_elapsed_seconds(self):
        """Test elapsed time formatting over 1 second."""
        item = TimelineItemDisplayModel(
            seq=1,
            entry_type=TimelineEntryType.PROMPT,
            elapsed_ms=2500
        )
        assert item.formatted_elapsed == "+2.50s"


class TestTabDisplayModel:
    """Tests for TabDisplayModel."""

    def test_tab_display(self):
        """Test tab display model creation."""
        tab = TabDisplayModel(
            tab_id="test-1",
            tab_label="Startup",
            status=TestStatus.PASS,
            is_active=True
        )
        assert tab.tab_id == "test-1"
        assert tab.tab_label == "Startup"
        assert tab.is_active is True
        assert tab.status_display.css_class == "pass"
