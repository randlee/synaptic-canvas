"""
Log analysis for Claude Code test harness.

This module provides functionality to parse and analyze logs for warnings
and errors. It integrates with pytest's capture fixture for analyzing
test output.

Key Design Principles:
- Default fail on warnings: Any warning in logs = test failure
- Explicit override only: Tests can disable with allow_warnings: true
- Full reporting: Complete all reporting before failing

Example usage:
    from harness.log_analyzer import analyze_logs, LogAnalysisResult

    # Analyze raw log content
    result = analyze_logs(log_content)
    if result.has_issues:
        print(f"Found {len(result.warnings)} warnings and {len(result.errors)} errors")

    # Analyze pytest captured output
    result = analyze_captured_output(captured)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture


class LogLevel(str, Enum):
    """Log level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """A single parsed log entry.

    Attributes:
        level: The log level (WARNING, ERROR, etc.)
        message: The log message content
        logger_name: Name of the logger that produced this entry
        timestamp: Optional timestamp when the log was produced
        line_number: Line number in the log content where this entry was found
        raw_line: The original raw log line
    """

    level: LogLevel
    message: str
    logger_name: str = ""
    timestamp: datetime | None = None
    line_number: int = 0
    raw_line: str = ""


@dataclass
class LogAnalysisResult:
    """Result of analyzing logs for issues.

    Attributes:
        warnings: List of WARNING level log entries
        errors: List of ERROR and CRITICAL level log entries
        all_entries: All parsed log entries (for debugging)
        raw_content: The original log content analyzed
    """

    warnings: list[LogEntry] = field(default_factory=list)
    errors: list[LogEntry] = field(default_factory=list)
    all_entries: list[LogEntry] = field(default_factory=list)
    raw_content: str = ""

    @property
    def has_issues(self) -> bool:
        """Check if any warnings or errors were found."""
        return len(self.warnings) > 0 or len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if any warnings were found."""
        return len(self.warnings) > 0

    @property
    def has_errors(self) -> bool:
        """Check if any errors were found."""
        return len(self.errors) > 0

    @property
    def issue_count(self) -> int:
        """Total count of warnings and errors."""
        return len(self.warnings) + len(self.errors)

    def summary(self) -> str:
        """Generate a human-readable summary of findings."""
        if not self.has_issues:
            return "No issues found in logs"

        parts = []
        if self.warnings:
            parts.append(f"{len(self.warnings)} warning(s)")
        if self.errors:
            parts.append(f"{len(self.errors)} error(s)")

        return f"Log analysis: {', '.join(parts)}"


# Common log format patterns
# Standard Python logging format: LEVEL:logger:message or LEVEL - logger - message
# Also handles pytest logging format and timestamped formats

# Pattern for standard logging: "2024-01-01 12:00:00,123 - logger - LEVEL - message"
_TIMESTAMPED_LOG_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*[-:]\s*"
    r"(\w+(?:\.\w+)*)\s*[-:]\s*"
    r"(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*[-:]\s*"
    r"(.*)$",
    re.MULTILINE,
)

# Pattern for simple logging: "LEVEL:logger:message" or "LEVEL - logger - message"
_SIMPLE_LOG_PATTERN = re.compile(
    r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*[-:]\s*"
    r"(\w+(?:\.\w+)*)\s*[-:]\s*"
    r"(.*)$",
    re.MULTILINE,
)

# Pattern for pytest-style: "WARNING module:function:line message"
_PYTEST_LOG_PATTERN = re.compile(
    r"^(WARNING|ERROR|CRITICAL)\s+"
    r"(\w+(?:\.\w+)*):(\w+):(\d+)\s+"
    r"(.*)$",
    re.MULTILINE,
)

# Pattern for bare level prefix: "WARNING: message" or "ERROR: message"
_BARE_LEVEL_PATTERN = re.compile(
    r"^(WARNING|ERROR|CRITICAL):\s*(.*)$",
    re.MULTILINE,
)


def _parse_timestamp(ts_str: str) -> datetime | None:
    """Parse a timestamp string to datetime."""
    try:
        # Handle both comma and dot for milliseconds
        ts_str = ts_str.replace(",", ".")
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        return None


def _parse_log_line(line: str, line_number: int) -> LogEntry | None:
    """Parse a single log line into a LogEntry if it matches known patterns.

    Args:
        line: The log line to parse
        line_number: The line number in the source

    Returns:
        LogEntry if the line matches a log pattern, None otherwise
    """
    line = line.strip()
    if not line:
        return None

    # Try timestamped format first (most specific)
    match = _TIMESTAMPED_LOG_PATTERN.match(line)
    if match:
        ts_str, logger_name, level_str, message = match.groups()
        return LogEntry(
            level=LogLevel(level_str),
            message=message.strip(),
            logger_name=logger_name,
            timestamp=_parse_timestamp(ts_str),
            line_number=line_number,
            raw_line=line,
        )

    # Try simple format
    match = _SIMPLE_LOG_PATTERN.match(line)
    if match:
        level_str, logger_name, message = match.groups()
        return LogEntry(
            level=LogLevel(level_str),
            message=message.strip(),
            logger_name=logger_name,
            line_number=line_number,
            raw_line=line,
        )

    # Try pytest format
    match = _PYTEST_LOG_PATTERN.match(line)
    if match:
        level_str, module, func, lineno, message = match.groups()
        return LogEntry(
            level=LogLevel(level_str),
            message=message.strip(),
            logger_name=f"{module}:{func}:{lineno}",
            line_number=line_number,
            raw_line=line,
        )

    # Try bare level format
    match = _BARE_LEVEL_PATTERN.match(line)
    if match:
        level_str, message = match.groups()
        return LogEntry(
            level=LogLevel(level_str),
            message=message.strip(),
            line_number=line_number,
            raw_line=line,
        )

    return None


def analyze_logs(log_content: str) -> LogAnalysisResult:
    """Parse logs for WARNING and ERROR level entries.

    This function analyzes log content and extracts all warning and error
    entries. It supports multiple common log formats:
    - Timestamped: "2024-01-01 12:00:00,123 - logger - LEVEL - message"
    - Simple: "LEVEL:logger:message" or "LEVEL - logger - message"
    - Pytest-style: "WARNING module:function:line message"
    - Bare: "WARNING: message" or "ERROR: message"

    Args:
        log_content: Raw log text to analyze

    Returns:
        LogAnalysisResult containing parsed warnings and errors
    """
    result = LogAnalysisResult(raw_content=log_content)

    if not log_content:
        return result

    lines = log_content.split("\n")
    for line_number, line in enumerate(lines, start=1):
        entry = _parse_log_line(line, line_number)
        if entry is None:
            continue

        result.all_entries.append(entry)

        if entry.level == LogLevel.WARNING:
            result.warnings.append(entry)
        elif entry.level in (LogLevel.ERROR, LogLevel.CRITICAL):
            result.errors.append(entry)

    return result


def analyze_captured_output(captured: "CaptureFixture") -> LogAnalysisResult:
    """Analyze pytest captured output for issues.

    This function reads both stdout and stderr from pytest's capture
    fixture and analyzes them for warnings and errors.

    Args:
        captured: pytest's CaptureFixture (typically from capfd or capsys)

    Returns:
        LogAnalysisResult containing parsed warnings and errors from captured output
    """
    # Read captured output without clearing the buffer
    out, err = captured.readouterr()

    # Combine stdout and stderr for analysis
    combined_content = ""
    if out:
        combined_content += f"--- stdout ---\n{out}\n"
    if err:
        combined_content += f"--- stderr ---\n{err}\n"

    return analyze_logs(combined_content)


def analyze_structured_logs(
    records: list[dict[str, object]],
    source: str = "structured",
) -> LogAnalysisResult:
    """Analyze structured log records for warnings/errors.

    Args:
        records: List of JSON-decoded log records.
        source: Label describing the source of records.
    """
    result = LogAnalysisResult(raw_content=f"structured:{source}")
    if not records:
        return result

    for idx, record in enumerate(records, start=1):
        level = record.get("level") or record.get("severity")
        status = record.get("status")
        if not level and status:
            status_str = str(status).lower()
            if status_str == "error":
                level = "ERROR"
            elif status_str == "warning":
                level = "WARNING"
            else:
                continue
        if not level:
            continue

        try:
            level_enum = LogLevel(str(level).upper())
        except ValueError:
            continue

        message = record.get("message") or record.get("error") or record.get("event") or "structured log entry"
        if isinstance(message, dict):
            message = json.dumps(message)
        elif not isinstance(message, str):
            message = str(message)

        entry = LogEntry(
            level=level_enum,
            message=message,
            logger_name=str(record.get("component") or record.get("logger") or ""),
            line_number=idx,
            raw_line=json.dumps(record),
        )
        result.all_entries.append(entry)
        if entry.level == LogLevel.WARNING:
            result.warnings.append(entry)
        elif entry.level in (LogLevel.ERROR, LogLevel.CRITICAL):
            result.errors.append(entry)

    return result


def merge_log_analysis(results: list[LogAnalysisResult]) -> LogAnalysisResult:
    """Merge multiple LogAnalysisResults into a single result."""
    merged = LogAnalysisResult(raw_content="")
    for result in results:
        if not result:
            continue
        merged.warnings.extend(result.warnings)
        merged.errors.extend(result.errors)
        merged.all_entries.extend(result.all_entries)
        if result.raw_content:
            merged.raw_content += result.raw_content + "\n"
    return merged


def filter_allowed_warnings(
    result: LogAnalysisResult,
    allowed_patterns: list[str] | None = None,
) -> LogAnalysisResult:
    """Filter out warnings that match allowed patterns.

    This is useful when certain warnings are expected and should not
    cause test failures.

    Args:
        result: The original LogAnalysisResult
        allowed_patterns: List of regex patterns for warnings to allow

    Returns:
        New LogAnalysisResult with matching warnings removed
    """
    if not allowed_patterns:
        return result

    compiled_patterns = [re.compile(p) for p in allowed_patterns]

    def is_allowed(entry: LogEntry) -> bool:
        for pattern in compiled_patterns:
            if pattern.search(entry.message) or pattern.search(entry.raw_line):
                return True
        return False

    filtered_warnings = [w for w in result.warnings if not is_allowed(w)]

    return LogAnalysisResult(
        warnings=filtered_warnings,
        errors=result.errors,  # Errors are never filtered
        all_entries=result.all_entries,
        raw_content=result.raw_content,
    )
