"""
Unit tests for harness.collector module.

Tests the data collection functionality including:
- Trace file parsing
- Transcript parsing
- Event correlation
- Error extraction
- Timeline building
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from harness.collector import (
    ClaudeResponseText,
    CollectedData,
    CorrelatedToolCall,
    DataCollector,
    SubagentLifecycle,
    ToolError,
    correlate_events,
    extract_claude_responses,
    extract_errors_from_transcript,
    extract_tool_names_from_transcript,
    parse_timestamp,
    parse_trace_file,
    parse_transcript,
)
from harness.log_analyzer import LogAnalysisResult, LogEntry, LogLevel
from harness.models import TimelineEntryType


class TestParseTimestamp:
    """Tests for parse_timestamp function."""

    def test_parses_iso8601_with_z(self):
        """Test parsing ISO8601 timestamp with Z suffix."""
        ts = parse_timestamp("2026-01-16T01:26:35Z")
        assert ts is not None
        assert ts.year == 2026
        assert ts.month == 1
        assert ts.day == 16

    def test_parses_iso8601_with_microseconds(self):
        """Test parsing ISO8601 with microseconds."""
        ts = parse_timestamp("2026-01-16T01:26:35.123456Z")
        assert ts is not None
        assert ts.microsecond == 123456

    def test_parses_iso8601_without_z(self):
        """Test parsing ISO8601 without Z suffix."""
        ts = parse_timestamp("2026-01-16T01:26:35")
        assert ts is not None

    def test_returns_none_for_invalid(self):
        """Test returns None for invalid timestamp."""
        ts = parse_timestamp("invalid")
        assert ts is None

    def test_returns_none_for_none(self):
        """Test returns None for None input."""
        ts = parse_timestamp(None)
        assert ts is None


class TestParseTraceFile:
    """Tests for parse_trace_file function."""

    def test_parses_valid_jsonl(self):
        """Test parsing valid JSONL file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"event": "SessionStart", "session_id": "123"}\n')
            f.write('{"event": "PreToolUse", "tool_name": "Bash"}\n')
            f.name

        try:
            events = parse_trace_file(f.name)
            assert len(events) == 2
            assert events[0]["event"] == "SessionStart"
            assert events[1]["event"] == "PreToolUse"
        finally:
            Path(f.name).unlink()

    def test_skips_invalid_lines(self):
        """Test that invalid JSON lines are skipped."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"valid": true}\n')
            f.write('invalid json line\n')
            f.write('{"also_valid": true}\n')
            f.name

        try:
            events = parse_trace_file(f.name)
            assert len(events) == 2
        finally:
            Path(f.name).unlink()

    def test_returns_empty_for_nonexistent(self):
        """Test returns empty list for nonexistent file."""
        events = parse_trace_file("/nonexistent/path.jsonl")
        assert events == []

    def test_skips_empty_lines(self):
        """Test that empty lines are skipped."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"event": "test"}\n')
            f.write('\n')
            f.write('   \n')
            f.write('{"event": "test2"}\n')
            f.name

        try:
            events = parse_trace_file(f.name)
            assert len(events) == 2
        finally:
            Path(f.name).unlink()

    def test_parses_nested_stdin_json(self):
        """Test that nested JSON in stdin field is parsed and merged into event.

        This is critical for SubagentStart/Stop events where agent_id, agent_type,
        tool_use_id, and session_id are stored inside the stdin field as a JSON string.
        """
        # Simulate how log-hook.py stores the Claude hook payload
        stdin_payload = json.dumps({
            "session_id": "abc123",
            "agent_id": "agent-456",
            "agent_type": "Explore",
            "hook_event_name": "SubagentStart"
        })
        trace_entry = json.dumps({
            "ts": "2026-01-16T19:17:11Z",
            "event": "SubagentStart",
            "cwd": "/test/path",
            "stdin": stdin_payload,
            "env": {}
        })

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(trace_entry + "\n")
            f.name

        try:
            events = parse_trace_file(f.name)
            assert len(events) == 1
            event = events[0]

            # Top-level fields should be preserved
            assert event["event"] == "SubagentStart"
            assert event["cwd"] == "/test/path"
            assert event["ts"] == "2026-01-16T19:17:11Z"

            # stdin fields should be merged into top level
            assert event["session_id"] == "abc123"
            assert event["agent_id"] == "agent-456"
            assert event["agent_type"] == "Explore"
            assert event["hook_event_name"] == "SubagentStart"

            # Original stdin should still be there
            assert "stdin" in event
        finally:
            Path(f.name).unlink()

    def test_stdin_parsing_does_not_overwrite_top_level(self):
        """Test that stdin data doesn't overwrite existing top-level fields."""
        stdin_payload = json.dumps({
            "event": "ShouldNotOverwrite",  # Try to overwrite
            "session_id": "from-stdin"
        })
        trace_entry = json.dumps({
            "event": "PreToolUse",  # Should be preserved
            "stdin": stdin_payload
        })

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(trace_entry + "\n")
            f.name

        try:
            events = parse_trace_file(f.name)
            event = events[0]

            # Top-level should NOT be overwritten
            assert event["event"] == "PreToolUse"

            # But new fields should be added
            assert event["session_id"] == "from-stdin"
        finally:
            Path(f.name).unlink()

    def test_handles_invalid_stdin_json_gracefully(self):
        """Test that invalid JSON in stdin field is handled gracefully."""
        trace_entry = json.dumps({
            "event": "PreToolUse",
            "stdin": "not valid json {{{",
        })

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(trace_entry + "\n")
            f.name

        try:
            events = parse_trace_file(f.name)
            assert len(events) == 1
            # Event should still be parsed, just without stdin data merged
            assert events[0]["event"] == "PreToolUse"
            assert events[0]["stdin"] == "not valid json {{{"
        finally:
            Path(f.name).unlink()


class TestParseTranscript:
    """Tests for parse_transcript function."""

    def test_parses_transcript_entries(self):
        """Test parsing transcript entries."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write('{"type": "user", "message": {"content": "hello"}}\n')
            f.write('{"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}}\n')
            f.name

        try:
            entries = parse_transcript(f.name)
            assert len(entries) == 2
            assert entries[0]["type"] == "user"
            assert entries[1]["type"] == "assistant"
        finally:
            Path(f.name).unlink()

    def test_returns_empty_for_nonexistent(self):
        """Test returns empty list for nonexistent file."""
        entries = parse_transcript("/nonexistent/transcript.jsonl")
        assert entries == []


class TestCorrelateEvents:
    """Tests for correlate_events function."""

    def test_correlates_pre_and_post_tool(self):
        """Test correlating PreToolUse and PostToolUse events."""
        events = [
            {
                "event": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "ls"},
                "tool_use_id": "toolu_123",
                "ts": "2026-01-16T01:00:00Z",
            },
            {
                "event": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "ls"},
                "tool_response": {"stdout": "file.txt"},
                "tool_use_id": "toolu_123",
                "ts": "2026-01-16T01:00:01Z",
            },
        ]

        tool_calls, subagents = correlate_events(events)

        assert len(tool_calls) == 1
        assert tool_calls[0].tool_use_id == "toolu_123"
        assert tool_calls[0].tool_name == "Bash"
        assert tool_calls[0].tool_input == {"command": "ls"}
        assert tool_calls[0].tool_response == {"stdout": "file.txt"}

    def test_handles_missing_post_tool(self):
        """Test handling PreToolUse without PostToolUse."""
        events = [
            {
                "event": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "exit 1"},
                "tool_use_id": "toolu_456",
                "ts": "2026-01-16T01:00:00Z",
            },
        ]

        tool_calls, _ = correlate_events(events)

        assert len(tool_calls) == 1
        assert tool_calls[0].tool_response is None
        assert tool_calls[0].post_timestamp is None

    def test_correlates_subagents(self):
        """Test correlating SubagentStart and SubagentStop events."""
        events = [
            {
                "event": "SubagentStart",
                "agent_id": "agent-123",
                "agent_type": "Explore",
                "ts": "2026-01-16T01:00:00Z",
            },
            {
                "event": "SubagentStop",
                "agent_id": "agent-123",
                "agent_transcript_path": "/path/to/transcript.jsonl",
                "ts": "2026-01-16T01:00:05Z",
            },
        ]

        _, subagents = correlate_events(events)

        assert len(subagents) == 1
        assert subagents[0].agent_id == "agent-123"
        assert subagents[0].agent_type == "Explore"
        assert subagents[0].transcript_path == "/path/to/transcript.jsonl"

    def test_handles_hook_event_name_field(self):
        """Test handling of hook_event_name field instead of event."""
        events = [
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Read",
                "tool_input": {"file_path": "/path"},
                "tool_use_id": "toolu_789",
            },
        ]

        tool_calls, _ = correlate_events(events)

        assert len(tool_calls) == 1
        assert tool_calls[0].tool_name == "Read"

    def test_calculates_duration(self):
        """Test duration calculation for tool calls."""
        events = [
            {
                "event": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {},
                "tool_use_id": "t1",
                "ts": "2026-01-16T01:00:00.000Z",
            },
            {
                "event": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {},
                "tool_response": {},
                "tool_use_id": "t1",
                "ts": "2026-01-16T01:00:00.500Z",  # 500ms later
            },
        ]

        tool_calls, _ = correlate_events(events)

        assert tool_calls[0].duration_ms == 500


class TestExtractErrorsFromTranscript:
    """Tests for extract_errors_from_transcript function."""

    def test_extracts_error_results(self):
        """Test extracting error tool results."""
        entries = [
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {}},
            {
                "type": "tool_result",
                "tool_use_id": "t1",
                "content": "Exit code 1\nFile not found",
                "is_error": True,
            },
        ]

        errors = extract_errors_from_transcript(entries)

        assert len(errors) == 1
        assert errors[0].tool_use_id == "t1"
        assert "File not found" in errors[0].error_content

    def test_ignores_non_error_results(self):
        """Test that non-error results are ignored."""
        entries = [
            {
                "type": "tool_result",
                "tool_use_id": "t1",
                "content": "Success",
                "is_error": False,
            },
        ]

        errors = extract_errors_from_transcript(entries)

        assert len(errors) == 0

    def test_handles_missing_is_error(self):
        """Test handling of missing is_error field."""
        entries = [
            {
                "type": "tool_result",
                "tool_use_id": "t1",
                "content": "Output",
            },
        ]

        errors = extract_errors_from_transcript(entries)

        assert len(errors) == 0


class TestExtractClaudeResponses:
    """Tests for extract_claude_responses function."""

    def test_extracts_text_responses(self):
        """Test extracting text responses from assistant messages."""
        entries = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "Hello!"},
                        {"type": "text", "text": "How can I help?"},
                    ]
                },
            },
        ]

        responses = extract_claude_responses(entries)

        assert len(responses) == 1
        assert "Hello!" in responses[0].text
        assert "How can I help?" in responses[0].text

    def test_handles_empty_content(self):
        """Test handling of empty content array."""
        entries = [
            {
                "type": "assistant",
                "message": {"content": []},
            },
        ]

        responses = extract_claude_responses(entries)

        assert len(responses) == 0

    def test_calculates_word_count(self):
        """Test word count calculation."""
        entries = [
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": "One two three four five"}]
                },
            },
        ]

        responses = extract_claude_responses(entries)

        assert responses[0].word_count == 5


class TestExtractToolNamesFromTranscript:
    """Tests for extract_tool_names_from_transcript function."""

    def test_adds_tool_names_to_errors(self):
        """Test adding tool names to error objects."""
        entries = [
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {}},
            {"type": "tool_use", "id": "t2", "name": "Read", "input": {}},
        ]

        errors = [
            ToolError(tool_use_id="t1", error_content="Error 1"),
            ToolError(tool_use_id="t2", error_content="Error 2"),
        ]

        extract_tool_names_from_transcript(entries, errors)

        assert errors[0].tool_name == "Bash"
        assert errors[1].tool_name == "Read"

    def test_handles_missing_tool_use(self):
        """Test handling of error with no matching tool_use."""
        entries = [
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {}},
        ]

        errors = [
            ToolError(tool_use_id="t999", error_content="Unknown error"),
        ]

        extract_tool_names_from_transcript(entries, errors)

        assert errors[0].tool_name is None


class TestCorrelatedToolCall:
    """Tests for CorrelatedToolCall dataclass."""

    def test_duration_calculation(self):
        """Test automatic duration calculation."""
        tc = CorrelatedToolCall(
            tool_use_id="t1",
            tool_name="Bash",
            tool_input={},
            pre_timestamp=datetime(2026, 1, 16, 1, 0, 0),
            post_timestamp=datetime(2026, 1, 16, 1, 0, 1),  # 1 second later
        )

        assert tc.duration_ms == 1000

    def test_no_duration_without_timestamps(self):
        """Test no duration when timestamps missing."""
        tc = CorrelatedToolCall(
            tool_use_id="t1",
            tool_name="Bash",
            tool_input={},
        )

        assert tc.duration_ms is None


class TestSubagentLifecycle:
    """Tests for SubagentLifecycle dataclass."""

    def test_duration_calculation(self):
        """Test automatic duration calculation."""
        sub = SubagentLifecycle(
            agent_id="a1",
            start_timestamp=datetime(2026, 1, 16, 1, 0, 0),
            stop_timestamp=datetime(2026, 1, 16, 1, 0, 5),  # 5 seconds later
        )

        assert sub.duration_ms == 5000


class TestClaudeResponseText:
    """Tests for ClaudeResponseText dataclass."""

    def test_word_count_calculation(self):
        """Test automatic word count calculation."""
        resp = ClaudeResponseText(text="This is a test response")
        assert resp.word_count == 5

    def test_empty_text(self):
        """Test handling of empty text."""
        resp = ClaudeResponseText(text="")
        assert resp.word_count == 0


class TestCollectedData:
    """Tests for CollectedData dataclass."""

    def test_duration_calculation(self):
        """Test session duration calculation."""
        data = CollectedData(
            start_timestamp=datetime(2026, 1, 16, 1, 0, 0),
            end_timestamp=datetime(2026, 1, 16, 1, 0, 10),
        )

        assert data.duration_ms == 10000

    def test_final_response(self):
        """Test getting final response."""
        data = CollectedData(
            claude_responses=[
                ClaudeResponseText(text="First"),
                ClaudeResponseText(text="Last"),
            ]
        )

        assert data.final_response == "Last"

    def test_final_response_empty(self):
        """Test final response when no responses."""
        data = CollectedData()
        assert data.final_response == ""

    def test_has_errors_true(self):
        """Test has_errors when errors present."""
        data = CollectedData(
            errors=[ToolError(tool_use_id="t1", error_content="Error")]
        )

        assert data.has_errors is True

    def test_has_errors_from_tool_calls(self):
        """Test has_errors from tool call errors."""
        data = CollectedData(
            tool_calls=[
                CorrelatedToolCall(
                    tool_use_id="t1",
                    tool_name="Bash",
                    tool_input={},
                    is_error=True,
                )
            ]
        )

        assert data.has_errors is True

    def test_has_errors_false(self):
        """Test has_errors when no errors."""
        data = CollectedData()
        assert data.has_errors is False

    def test_has_errors_from_log_analysis(self):
        """Test has_errors when log analysis has errors."""
        data = CollectedData(
            log_analysis=LogAnalysisResult(
                errors=[LogEntry(level=LogLevel.ERROR, message="Log error")]
            )
        )
        assert data.has_errors is True

    def test_has_log_issues_with_warnings(self):
        """Test has_log_issues when log analysis has warnings."""
        data = CollectedData(
            log_analysis=LogAnalysisResult(
                warnings=[LogEntry(level=LogLevel.WARNING, message="Log warning")]
            )
        )
        assert data.has_log_issues is True
        # Warnings alone don't set has_errors
        assert data.has_errors is False

    def test_has_log_issues_false_when_no_analysis(self):
        """Test has_log_issues is False when no log analysis."""
        data = CollectedData()
        assert data.has_log_issues is False

    def test_has_log_issues_false_when_empty_analysis(self):
        """Test has_log_issues is False when log analysis is empty."""
        data = CollectedData(log_analysis=LogAnalysisResult())
        assert data.has_log_issues is False


class TestDataCollector:
    """Tests for DataCollector class."""

    def test_collect_from_trace_only(self):
        """Test collecting data from trace file only."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(
                json.dumps(
                    {
                        "event": "SessionStart",
                        "session_id": "sess-123",
                        "ts": "2026-01-16T01:00:00Z",
                    }
                )
                + "\n"
            )
            f.write(
                json.dumps(
                    {
                        "event": "UserPromptSubmit",
                        "prompt": "test prompt",
                        "ts": "2026-01-16T01:00:01Z",
                    }
                )
                + "\n"
            )
            trace_path = f.name

        try:
            collector = DataCollector(trace_path=trace_path)
            data = collector.collect()

            assert data.session_id == "sess-123"
            assert data.prompt == "test prompt"
        finally:
            Path(trace_path).unlink()

    def test_collect_from_both_sources(self):
        """Test collecting data from trace and transcript."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tf:
            tf.write(
                json.dumps(
                    {
                        "event": "PreToolUse",
                        "tool_name": "Bash",
                        "tool_input": {"command": "ls"},
                        "tool_use_id": "t1",
                        "ts": "2026-01-16T01:00:00Z",
                    }
                )
                + "\n"
            )
            trace_path = tf.name

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tr:
            tr.write(
                json.dumps(
                    {
                        "type": "tool_result",
                        "tool_use_id": "t1",
                        "content": "Error",
                        "is_error": True,
                    }
                )
                + "\n"
            )
            tr.write(
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "content": [{"type": "text", "text": "I see an error"}]
                        },
                    }
                )
                + "\n"
            )
            transcript_path = tr.name

        try:
            collector = DataCollector(
                trace_path=trace_path, transcript_path=transcript_path
            )
            data = collector.collect()

            assert len(data.tool_calls) == 1
            assert data.tool_calls[0].is_error is True
            assert len(data.errors) == 1
            assert len(data.claude_responses) == 1
        finally:
            Path(trace_path).unlink()
            Path(transcript_path).unlink()

    def test_build_timeline(self):
        """Test building timeline from collected data."""
        data = CollectedData(
            prompt="test prompt",
            prompt_timestamp=datetime(2026, 1, 16, 1, 0, 0),
            start_timestamp=datetime(2026, 1, 16, 1, 0, 0),
            tool_calls=[
                CorrelatedToolCall(
                    tool_use_id="t1",
                    tool_name="Bash",
                    tool_input={"command": "ls"},
                    tool_response={"stdout": "file.txt"},
                    pre_timestamp=datetime(2026, 1, 16, 1, 0, 1),
                )
            ],
            claude_responses=[
                ClaudeResponseText(
                    text="Here are the files",
                    timestamp=datetime(2026, 1, 16, 1, 0, 2),  # After tool call
                ),
            ],
        )

        collector = DataCollector()
        timeline = collector.build_timeline(data)

        assert len(timeline) == 3  # prompt, tool_call, response
        assert timeline[0].type == TimelineEntryType.PROMPT
        assert timeline[1].type == TimelineEntryType.TOOL_CALL
        assert timeline[2].type == TimelineEntryType.RESPONSE

    def test_infer_bash_intent(self):
        """Test intent inference for Bash commands."""
        collector = DataCollector()

        tc_ls = CorrelatedToolCall(
            tool_use_id="t1",
            tool_name="Bash",
            tool_input={"command": "ls -la"},
        )
        assert "List" in collector._infer_intent(tc_ls)

        tc_cat = CorrelatedToolCall(
            tool_use_id="t2",
            tool_name="Bash",
            tool_input={"command": "cat file.txt"},
        )
        assert "Read" in collector._infer_intent(tc_cat)

        tc_git = CorrelatedToolCall(
            tool_use_id="t3",
            tool_name="Bash",
            tool_input={"command": "git status"},
        )
        assert "Git" in collector._infer_intent(tc_git)

    def test_infer_skill_intent(self):
        """Test intent inference for Skill tool."""
        collector = DataCollector()

        tc = CorrelatedToolCall(
            tool_use_id="t1",
            tool_name="Skill",
            tool_input={"skill": "sc-startup", "args": "--readonly"},
        )

        intent = collector._infer_intent(tc)
        assert "sc-startup" in intent
        assert "--readonly" in intent

    def test_infer_read_intent(self):
        """Test intent inference for Read tool."""
        collector = DataCollector()

        tc = CorrelatedToolCall(
            tool_use_id="t1",
            tool_name="Read",
            tool_input={"file_path": "/path/to/config.yaml"},
        )

        intent = collector._infer_intent(tc)
        assert "config.yaml" in intent

    def test_uses_explicit_description(self):
        """Test that explicit description is used if available."""
        collector = DataCollector()

        tc = CorrelatedToolCall(
            tool_use_id="t1",
            tool_name="Bash",
            tool_input={"command": "ls", "description": "Check for files"},
        )

        intent = collector._infer_intent(tc)
        assert intent == "Check for files"
