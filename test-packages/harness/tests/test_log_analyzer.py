"""
Unit tests for harness.log_analyzer module.

Tests the log analysis functionality including:
- Log entry parsing with various formats
- Warning and error detection
- LogAnalysisResult properties
- Filtering allowed warnings
"""

import pytest

from harness.log_analyzer import (
    LogAnalysisResult,
    LogEntry,
    LogLevel,
    analyze_logs,
    filter_allowed_warnings,
)


class TestLogLevel:
    """Tests for LogLevel enum."""

    def test_log_levels_are_strings(self):
        """Test that LogLevel values are strings."""
        assert LogLevel.DEBUG == "DEBUG"
        assert LogLevel.INFO == "INFO"
        assert LogLevel.WARNING == "WARNING"
        assert LogLevel.ERROR == "ERROR"
        assert LogLevel.CRITICAL == "CRITICAL"


class TestLogEntry:
    """Tests for LogEntry dataclass."""

    def test_creates_log_entry(self):
        """Test creating a LogEntry with all fields."""
        entry = LogEntry(
            level=LogLevel.WARNING,
            message="Test warning",
            logger_name="test.module",
            line_number=10,
            raw_line="WARNING:test.module:Test warning",
        )
        assert entry.level == LogLevel.WARNING
        assert entry.message == "Test warning"
        assert entry.logger_name == "test.module"
        assert entry.line_number == 10

    def test_default_values(self):
        """Test LogEntry default values."""
        entry = LogEntry(level=LogLevel.ERROR, message="Error")
        assert entry.logger_name == ""
        assert entry.timestamp is None
        assert entry.line_number == 0
        assert entry.raw_line == ""


class TestLogAnalysisResult:
    """Tests for LogAnalysisResult dataclass."""

    def test_empty_result_has_no_issues(self):
        """Test empty result has_issues is False."""
        result = LogAnalysisResult()
        assert result.has_issues is False
        assert result.has_warnings is False
        assert result.has_errors is False
        assert result.issue_count == 0

    def test_has_warnings_true(self):
        """Test has_warnings when warnings present."""
        result = LogAnalysisResult(
            warnings=[LogEntry(level=LogLevel.WARNING, message="warning")]
        )
        assert result.has_warnings is True
        assert result.has_issues is True
        assert result.has_errors is False

    def test_has_errors_true(self):
        """Test has_errors when errors present."""
        result = LogAnalysisResult(
            errors=[LogEntry(level=LogLevel.ERROR, message="error")]
        )
        assert result.has_errors is True
        assert result.has_issues is True
        assert result.has_warnings is False

    def test_issue_count(self):
        """Test issue_count includes both warnings and errors."""
        result = LogAnalysisResult(
            warnings=[
                LogEntry(level=LogLevel.WARNING, message="w1"),
                LogEntry(level=LogLevel.WARNING, message="w2"),
            ],
            errors=[LogEntry(level=LogLevel.ERROR, message="e1")],
        )
        assert result.issue_count == 3

    def test_summary_no_issues(self):
        """Test summary when no issues."""
        result = LogAnalysisResult()
        assert result.summary() == "No issues found in logs"

    def test_summary_with_warnings_and_errors(self):
        """Test summary with both warnings and errors."""
        result = LogAnalysisResult(
            warnings=[LogEntry(level=LogLevel.WARNING, message="w1")],
            errors=[
                LogEntry(level=LogLevel.ERROR, message="e1"),
                LogEntry(level=LogLevel.ERROR, message="e2"),
            ],
        )
        summary = result.summary()
        assert "1 warning(s)" in summary
        assert "2 error(s)" in summary


class TestAnalyzeLogs:
    """Tests for analyze_logs function."""

    def test_empty_content(self):
        """Test analyzing empty content."""
        result = analyze_logs("")
        assert result.has_issues is False
        assert len(result.all_entries) == 0

    def test_simple_format_warning(self):
        """Test parsing simple format: LEVEL:logger:message."""
        content = "WARNING:test.module:This is a warning"
        result = analyze_logs(content)
        assert len(result.warnings) == 1
        assert result.warnings[0].level == LogLevel.WARNING
        assert result.warnings[0].message == "This is a warning"
        assert result.warnings[0].logger_name == "test.module"

    def test_simple_format_error(self):
        """Test parsing simple format ERROR."""
        content = "ERROR:test.module:This is an error"
        result = analyze_logs(content)
        assert len(result.errors) == 1
        assert result.errors[0].level == LogLevel.ERROR
        assert result.errors[0].message == "This is an error"

    def test_simple_format_critical(self):
        """Test parsing CRITICAL level as error."""
        content = "CRITICAL:test.module:Critical error"
        result = analyze_logs(content)
        assert len(result.errors) == 1
        assert result.errors[0].level == LogLevel.CRITICAL

    def test_simple_format_with_dashes(self):
        """Test parsing format with dashes: LEVEL - logger - message."""
        content = "WARNING - test.module - This is a warning"
        result = analyze_logs(content)
        assert len(result.warnings) == 1
        assert result.warnings[0].message == "This is a warning"

    def test_timestamped_format(self):
        """Test parsing timestamped format."""
        content = "2024-01-15 10:30:45,123 - mylogger - WARNING - Some warning"
        result = analyze_logs(content)
        assert len(result.warnings) == 1
        assert result.warnings[0].logger_name == "mylogger"
        assert result.warnings[0].message == "Some warning"
        assert result.warnings[0].timestamp is not None
        assert result.warnings[0].timestamp.year == 2024

    def test_timestamped_format_with_dot(self):
        """Test parsing timestamped format with dot for milliseconds."""
        content = "2024-01-15 10:30:45.123 - mylogger - ERROR - Some error"
        result = analyze_logs(content)
        assert len(result.errors) == 1
        assert result.errors[0].timestamp is not None

    def test_bare_level_format(self):
        """Test parsing bare level: WARNING: message."""
        content = "WARNING: Something went wrong"
        result = analyze_logs(content)
        assert len(result.warnings) == 1
        assert result.warnings[0].message == "Something went wrong"
        assert result.warnings[0].logger_name == ""

    def test_info_and_debug_not_captured(self):
        """Test that INFO and DEBUG are in all_entries but not warnings/errors."""
        content = """INFO:mylogger:Info message
DEBUG:mylogger:Debug message
WARNING:mylogger:Warning message"""
        result = analyze_logs(content)
        assert len(result.warnings) == 1
        assert len(result.errors) == 0
        # INFO and DEBUG should still be parsed into all_entries
        assert len(result.all_entries) == 3

    def test_multiline_content(self):
        """Test analyzing multiline log content."""
        content = """INFO:app:Starting application
WARNING:app:Memory usage high
ERROR:app:Connection failed
INFO:app:Retrying connection
WARNING:app:Retry limit approaching"""
        result = analyze_logs(content)
        assert len(result.warnings) == 2
        assert len(result.errors) == 1
        assert len(result.all_entries) == 5

    def test_line_numbers_preserved(self):
        """Test that line numbers are preserved in entries."""
        content = """INFO:app:Line 1
WARNING:app:Line 2
ERROR:app:Line 3"""
        result = analyze_logs(content)
        assert result.warnings[0].line_number == 2
        assert result.errors[0].line_number == 3

    def test_non_log_lines_ignored(self):
        """Test that non-log lines are ignored."""
        content = """Some regular text
Not a log entry
WARNING:app:This is a warning
More regular text"""
        result = analyze_logs(content)
        assert len(result.warnings) == 1
        assert len(result.all_entries) == 1

    def test_raw_content_preserved(self):
        """Test that raw content is preserved in result."""
        content = "WARNING:test:A warning"
        result = analyze_logs(content)
        assert result.raw_content == content


class TestFilterAllowedWarnings:
    """Tests for filter_allowed_warnings function."""

    def test_no_patterns_returns_same(self):
        """Test with no patterns returns same result."""
        result = LogAnalysisResult(
            warnings=[LogEntry(level=LogLevel.WARNING, message="A warning")]
        )
        filtered = filter_allowed_warnings(result, None)
        assert len(filtered.warnings) == 1

    def test_empty_patterns_returns_same(self):
        """Test with empty patterns returns same result."""
        result = LogAnalysisResult(
            warnings=[LogEntry(level=LogLevel.WARNING, message="A warning")]
        )
        filtered = filter_allowed_warnings(result, [])
        assert len(filtered.warnings) == 1

    def test_filters_matching_warnings(self):
        """Test that matching warnings are filtered out."""
        result = LogAnalysisResult(
            warnings=[
                LogEntry(level=LogLevel.WARNING, message="Deprecation warning"),
                LogEntry(level=LogLevel.WARNING, message="Memory warning"),
                LogEntry(level=LogLevel.WARNING, message="Another deprecation"),
            ]
        )
        filtered = filter_allowed_warnings(result, ["[Dd]eprecation"])
        assert len(filtered.warnings) == 1
        assert "Memory" in filtered.warnings[0].message

    def test_errors_never_filtered(self):
        """Test that errors are never filtered regardless of patterns."""
        result = LogAnalysisResult(
            warnings=[LogEntry(level=LogLevel.WARNING, message="Deprecation warning")],
            errors=[LogEntry(level=LogLevel.ERROR, message="Deprecation error")],
        )
        filtered = filter_allowed_warnings(result, ["[Dd]eprecation"])
        assert len(filtered.warnings) == 0
        assert len(filtered.errors) == 1  # Error kept even though matches pattern

    def test_preserves_other_fields(self):
        """Test that other fields are preserved after filtering."""
        entry = LogEntry(level=LogLevel.WARNING, message="Keep this")
        result = LogAnalysisResult(
            warnings=[entry],
            all_entries=[entry],
            raw_content="original content",
        )
        filtered = filter_allowed_warnings(result, ["other"])
        assert len(filtered.warnings) == 1
        assert filtered.raw_content == "original content"
        assert len(filtered.all_entries) == 1

    def test_matches_raw_line(self):
        """Test that patterns can match against raw_line."""
        result = LogAnalysisResult(
            warnings=[
                LogEntry(
                    level=LogLevel.WARNING,
                    message="Short msg",
                    raw_line="WARNING:module.submodule:Short msg",
                )
            ]
        )
        # Pattern matches raw_line but not message
        filtered = filter_allowed_warnings(result, ["module\\.submodule"])
        assert len(filtered.warnings) == 0
