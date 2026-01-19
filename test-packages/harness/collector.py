"""
Data collection for Claude Code test harness.

This module provides functionality to collect and correlate data from
two sources:
1. Hooks (trace.jsonl) - Real-time capture of tool calls, subagents
2. Transcript (transcript.jsonl) - Complete session record including errors

Key capabilities:
- Parse trace.jsonl from hook events
- Parse Claude transcript JSONL files
- Correlate PreToolUse to PostToolUse via tool_use_id
- Extract errors from transcript (fallback when PostToolUse doesn't fire)
- Extract Claude's text responses (not captured by hooks)

Based on findings from:
- spike-2-hook-observability.md
- spike3-gap-analysis.md

Example usage:
    from harness.collector import DataCollector

    collector = DataCollector(
        trace_path="/path/to/trace.jsonl",
        transcript_path="/path/to/transcript.jsonl"
    )
    data = collector.collect()

    # Access correlated tool calls
    for tool_call in data.tool_calls:
        print(f"{tool_call.tool_name}: {tool_call.input}")

    # Access Claude's responses
    for response in data.claude_responses:
        print(response.text)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import (
    HookEventType,
    PostToolUseEvent,
    PreToolUseEvent,
    SessionEndEvent,
    SessionStartEvent,
    StopEvent,
    SubagentStartEvent,
    SubagentStopEvent,
    TimelineEntry,
    TimelineEntryType,
    ToolInput,
    ToolOutput,
    UserPromptSubmitEvent,
)
from .log_analyzer import LogAnalysisResult, analyze_logs
from .schemas import TokenUsage

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes for Collected Data
# =============================================================================


@dataclass
class CorrelatedToolCall:
    """A tool call with correlated pre and post events.

    Represents a complete tool invocation with input, output, timing,
    and any error information.
    """

    tool_use_id: str
    tool_name: str
    tool_input: dict[str, Any]
    tool_response: dict[str, Any] | None = None
    pre_timestamp: datetime | None = None
    post_timestamp: datetime | None = None
    is_error: bool = False
    error_content: str | None = None
    duration_ms: int | None = None
    pid: int | None = None

    def __post_init__(self):
        """Compute duration if both timestamps available."""
        if self.pre_timestamp and self.post_timestamp:
            delta = self.post_timestamp - self.pre_timestamp
            self.duration_ms = int(delta.total_seconds() * 1000)


@dataclass
class SubagentLifecycle:
    """Lifecycle of a subagent from start to stop."""

    agent_id: str
    agent_type: str | None = None
    start_timestamp: datetime | None = None
    stop_timestamp: datetime | None = None
    transcript_path: str | None = None
    duration_ms: int | None = None

    def __post_init__(self):
        """Compute duration if both timestamps available."""
        if self.start_timestamp and self.stop_timestamp:
            delta = self.stop_timestamp - self.start_timestamp
            self.duration_ms = int(delta.total_seconds() * 1000)


@dataclass
class ClaudeResponseText:
    """A text response from Claude."""

    text: str
    timestamp: datetime | None = None
    word_count: int = 0

    def __post_init__(self):
        """Compute word count."""
        self.word_count = len(self.text.split())


@dataclass
class ToolError:
    """An error captured from a tool execution."""

    tool_use_id: str
    tool_name: str | None = None
    error_content: str = ""
    timestamp: datetime | None = None


@dataclass
class CollectedData:
    """All data collected from trace and transcript files.

    This is the primary output of the DataCollector, containing
    all events, tool calls, responses, and errors from a test session.
    """

    # Session info
    session_id: str | None = None
    transcript_path: str | None = None
    cwd: str | None = None
    start_timestamp: datetime | None = None
    end_timestamp: datetime | None = None
    end_reason: str | None = None

    # User prompt
    prompt: str | None = None
    prompt_timestamp: datetime | None = None

    # Tool calls (correlated)
    tool_calls: list[CorrelatedToolCall] = field(default_factory=list)

    # Subagents
    subagents: list[SubagentLifecycle] = field(default_factory=list)

    # Claude responses
    claude_responses: list[ClaudeResponseText] = field(default_factory=list)

    # Errors (from transcript, for when PostToolUse doesn't fire)
    errors: list[ToolError] = field(default_factory=list)

    # Tool to agent correlation: tool_use_id -> (agent_id, agent_type)
    tool_to_agent_map: dict[str, tuple[str, str | None]] = field(default_factory=dict)

    # Raw events (for timeline building)
    raw_hook_events: list[dict[str, Any]] = field(default_factory=list)
    raw_transcript_entries: list[dict[str, Any]] = field(default_factory=list)

    # Claude CLI output (for debugging)
    claude_cli_stdout: str = ""
    claude_cli_stderr: str = ""

    # Log analysis results (warnings/errors from logs)
    log_analysis: LogAnalysisResult | None = None

    @property
    def duration_ms(self) -> int | None:
        """Compute session duration in milliseconds."""
        if self.start_timestamp and self.end_timestamp:
            delta = self.end_timestamp - self.start_timestamp
            return int(delta.total_seconds() * 1000)
        return None

    @property
    def final_response(self) -> str:
        """Get the final Claude response text."""
        if self.claude_responses:
            return self.claude_responses[-1].text
        return ""

    @property
    def has_errors(self) -> bool:
        """Check if any errors were captured."""
        has_tool_errors = len(self.errors) > 0 or any(tc.is_error for tc in self.tool_calls)
        has_log_errors = self.log_analysis is not None and self.log_analysis.has_errors
        return has_tool_errors or has_log_errors

    @property
    def has_log_issues(self) -> bool:
        """Check if any warnings or errors were found in logs."""
        return self.log_analysis is not None and self.log_analysis.has_issues


# =============================================================================
# Parsing Functions
# =============================================================================


def parse_trace_file(trace_path: Path | str) -> list[dict[str, Any]]:
    """Parse trace.jsonl file from hook events.

    Reads and parses a JSONL file containing hook events captured
    during test execution. Automatically parses the nested JSON
    in the 'stdin' field and merges it into the top-level event.

    Args:
        trace_path: Path to trace.jsonl file

    Returns:
        List of parsed event dictionaries with stdin data merged

    Raises:
        FileNotFoundError: If trace file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    trace_path = Path(trace_path)

    if not trace_path.exists():
        logger.warning(f"Trace file not found: {trace_path}")
        return []

    events = []
    with open(trace_path, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)

                # Parse stdin JSON and merge into event (for agent_id, tool_use_id, etc.)
                # The log-hook.py may store stdin as a JSON string (old) or as a dict (new)
                stdin_raw = event.get("stdin", "")
                stdin_data = None
                if isinstance(stdin_raw, dict):
                    # Already parsed (new log-hook.py format)
                    stdin_data = stdin_raw
                elif stdin_raw and isinstance(stdin_raw, str):
                    # Legacy format - stdin is a JSON string
                    try:
                        stdin_data = json.loads(stdin_raw)
                    except json.JSONDecodeError:
                        logger.debug(f"stdin is not valid JSON at line {line_num}")

                # Merge stdin data, but don't overwrite existing top-level fields
                if stdin_data and isinstance(stdin_data, dict):
                    for key, value in stdin_data.items():
                        if key not in event:
                            event[key] = value

                events.append(event)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON at line {line_num}: {e}")
                continue

    logger.debug(f"Parsed {len(events)} events from trace file")
    return events


def parse_transcript(transcript_path: Path | str) -> list[dict[str, Any]]:
    """Parse Claude session transcript JSONL file.

    Reads and parses a transcript file containing the complete
    session record including messages, tool uses, and results.

    Args:
        transcript_path: Path to transcript.jsonl transcript file

    Returns:
        List of parsed transcript entries

    Raises:
        FileNotFoundError: If transcript file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    transcript_path = Path(transcript_path)

    if not transcript_path.exists():
        logger.warning(f"Transcript file not found: {transcript_path}")
        return []

    entries = []
    with open(transcript_path, "r") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON at line {line_num}: {e}")
                continue

    logger.debug(f"Parsed {len(entries)} entries from transcript")
    return entries


def parse_timestamp(ts_str: str | None) -> datetime | None:
    """Parse ISO8601 timestamp string to datetime.

    Handles various timestamp formats found in hook events and transcripts.

    Args:
        ts_str: ISO8601 timestamp string

    Returns:
        Parsed datetime or None if parsing fails
    """
    if not ts_str:
        return None

    # Try common formats
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue

    # Try fromisoformat as fallback
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except ValueError:
        logger.warning(f"Failed to parse timestamp: {ts_str}")
        return None


def correlate_events(
    events: list[dict[str, Any]],
) -> tuple[list[CorrelatedToolCall], list[SubagentLifecycle]]:
    """Correlate PreToolUse to PostToolUse events by tool_use_id.

    Matches PreToolUse events with their corresponding PostToolUse events
    using the tool_use_id field. Also correlates SubagentStart/Stop events.

    Args:
        events: List of hook events

    Returns:
        Tuple of (tool_calls, subagents)
    """
    # Index events by tool_use_id
    pre_tool_events: dict[str, dict[str, Any]] = {}
    post_tool_events: dict[str, dict[str, Any]] = {}
    subagent_starts: dict[str, dict[str, Any]] = {}
    subagent_stops: dict[str, dict[str, Any]] = {}

    for event in events:
        event_type = event.get("event") or event.get("hook_event_name")
        tool_use_id = event.get("tool_use_id")
        agent_id = event.get("agent_id")

        if event_type == "PreToolUse" and tool_use_id:
            pre_tool_events[tool_use_id] = event
        elif event_type == "PostToolUse" and tool_use_id:
            post_tool_events[tool_use_id] = event
        elif event_type == "SubagentStart" and agent_id:
            subagent_starts[agent_id] = event
        elif event_type == "SubagentStop" and agent_id:
            subagent_stops[agent_id] = event

    # Correlate tool calls
    tool_calls = []
    seen_ids = set()

    for tool_use_id, pre_event in pre_tool_events.items():
        post_event = post_tool_events.get(tool_use_id)

        tool_call = CorrelatedToolCall(
            tool_use_id=tool_use_id,
            tool_name=pre_event.get("tool_name", ""),
            tool_input=pre_event.get("tool_input", {}),
            tool_response=post_event.get("tool_response") if post_event else None,
            pre_timestamp=parse_timestamp(pre_event.get("ts")),
            post_timestamp=(
                parse_timestamp(post_event.get("ts")) if post_event else None
            ),
            pid=pre_event.get("pid"),
        )
        tool_calls.append(tool_call)
        seen_ids.add(tool_use_id)

    # Add any PostToolUse events without matching PreToolUse
    for tool_use_id, post_event in post_tool_events.items():
        if tool_use_id not in seen_ids:
            tool_call = CorrelatedToolCall(
                tool_use_id=tool_use_id,
                tool_name=post_event.get("tool_name", ""),
                tool_input=post_event.get("tool_input", {}),
                tool_response=post_event.get("tool_response"),
                post_timestamp=parse_timestamp(post_event.get("ts")),
                pid=post_event.get("pid"),
            )
            tool_calls.append(tool_call)

    # Sort by timestamp
    tool_calls.sort(
        key=lambda tc: tc.pre_timestamp or tc.post_timestamp or datetime.min
    )

    # Correlate subagents
    subagents = []
    seen_agents = set()

    for agent_id, start_event in subagent_starts.items():
        stop_event = subagent_stops.get(agent_id)

        subagent = SubagentLifecycle(
            agent_id=agent_id,
            agent_type=start_event.get("agent_type"),
            start_timestamp=parse_timestamp(start_event.get("ts")),
            stop_timestamp=(
                parse_timestamp(stop_event.get("ts")) if stop_event else None
            ),
            transcript_path=(
                stop_event.get("agent_transcript_path") if stop_event else None
            ),
        )
        subagents.append(subagent)
        seen_agents.add(agent_id)

    # Add any SubagentStop events without matching Start
    for agent_id, stop_event in subagent_stops.items():
        if agent_id not in seen_agents:
            subagent = SubagentLifecycle(
                agent_id=agent_id,
                stop_timestamp=parse_timestamp(stop_event.get("ts")),
                transcript_path=stop_event.get("agent_transcript_path"),
            )
            subagents.append(subagent)

    logger.debug(
        f"Correlated {len(tool_calls)} tool calls and {len(subagents)} subagents"
    )
    return tool_calls, subagents


def correlate_tool_calls_with_agents(
    events: list[dict[str, Any]]
) -> dict[str, tuple[str, str | None]]:
    """Correlate tool_use_ids with their parent subagent.

    Uses ppid (parent process ID) to determine which subagent context
    a tool call executed in. Falls back to timestamp-based correlation
    if ppid is not available.

    Args:
        events: List of hook events

    Returns:
        Dict mapping tool_use_id -> (agent_id, agent_type)
    """
    sorted_events = sorted(
        events,
        key=lambda e: parse_timestamp(e.get("ts")) or datetime.min
    )

    # Track active subagents by ppid: ppid -> (agent_id, agent_type)
    active_by_ppid: dict[int, tuple[str, str | None]] = {}

    # Track subagent time ranges for fallback: agent_id -> (start_ts, stop_ts, agent_type)
    subagent_ranges: dict[str, tuple[datetime | None, datetime | None, str | None]] = {}

    # Result: tool_use_id -> (agent_id, agent_type)
    tool_to_agent: dict[str, tuple[str, str | None]] = {}

    # First pass: build ppid mapping and time ranges
    for event in sorted_events:
        event_type = event.get("event") or event.get("hook_event_name")
        ppid = event.get("ppid")
        agent_id = event.get("agent_id")
        agent_type = event.get("agent_type")
        ts = parse_timestamp(event.get("ts"))

        if event_type == "SubagentStart" and agent_id:
            if ppid:
                active_by_ppid[ppid] = (agent_id, agent_type)
            subagent_ranges[agent_id] = (ts, None, agent_type)

        elif event_type == "SubagentStop" and agent_id:
            # Remove from ppid mapping
            for key, (aid, _) in list(active_by_ppid.items()):
                if aid == agent_id:
                    del active_by_ppid[key]
                    break
            # Update time range
            if agent_id in subagent_ranges:
                start_ts, _, atype = subagent_ranges[agent_id]
                subagent_ranges[agent_id] = (start_ts, ts, atype)

    # Reset ppid mapping for second pass
    active_by_ppid.clear()

    # Second pass: correlate tool calls
    for event in sorted_events:
        event_type = event.get("event") or event.get("hook_event_name")
        ppid = event.get("ppid")
        agent_id = event.get("agent_id")
        agent_type = event.get("agent_type")

        if event_type == "SubagentStart" and agent_id and ppid:
            active_by_ppid[ppid] = (agent_id, agent_type)

        elif event_type == "SubagentStop" and agent_id:
            for key, (aid, _) in list(active_by_ppid.items()):
                if aid == agent_id:
                    del active_by_ppid[key]
                    break

        elif event_type == "PreToolUse":
            tool_use_id = event.get("tool_use_id")
            if not tool_use_id:
                continue

            # Try ppid correlation first
            if ppid and ppid in active_by_ppid:
                tool_to_agent[tool_use_id] = active_by_ppid[ppid]
            else:
                # Fallback: timestamp-based correlation
                ts = parse_timestamp(event.get("ts"))
                if ts:
                    for aid, (start_ts, stop_ts, atype) in subagent_ranges.items():
                        if start_ts and start_ts <= ts:
                            if stop_ts is None or ts <= stop_ts:
                                tool_to_agent[tool_use_id] = (aid, atype)
                                break

    return tool_to_agent


def extract_errors_from_transcript(
    entries: list[dict[str, Any]],
) -> list[ToolError]:
    """Extract tool errors from transcript that hooks may have missed.

    PostToolUse hooks don't fire when tools fail with errors. This function
    extracts errors from the transcript's tool_result entries.

    Args:
        entries: List of transcript entries

    Returns:
        List of ToolError objects
    """
    errors = []

    for entry in entries:
        if entry.get("type") == "tool_result":
            if entry.get("is_error"):
                error = ToolError(
                    tool_use_id=entry.get("tool_use_id", ""),
                    error_content=entry.get("content", ""),
                )
                errors.append(error)

    logger.debug(f"Extracted {len(errors)} errors from transcript")
    return errors


def extract_claude_responses(
    entries: list[dict[str, Any]],
) -> list[ClaudeResponseText]:
    """Extract Claude's text responses from transcript.

    Hooks don't capture Claude's text responses to the user. This function
    extracts them from assistant messages in the transcript.

    Args:
        entries: List of transcript entries

    Returns:
        List of ClaudeResponseText objects
    """
    responses = []

    for entry in entries:
        if entry.get("type") == "assistant":
            message = entry.get("message", {})
            content = message.get("content", [])

            # Extract text from content array
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    text_parts.append(item)

            if text_parts:
                full_text = "\n".join(text_parts)
                response = ClaudeResponseText(text=full_text)
                responses.append(response)

    logger.debug(f"Extracted {len(responses)} Claude responses from transcript")
    return responses


def extract_tool_names_from_transcript(
    entries: list[dict[str, Any]],
    errors: list[ToolError],
) -> None:
    """Add tool names to errors from transcript tool_use entries.

    Updates ToolError objects with tool names by matching tool_use_id
    to tool_use entries in the transcript.

    Args:
        entries: List of transcript entries
        errors: List of ToolError objects to update (modified in place)
    """
    # Build tool_use_id -> tool_name mapping
    tool_names: dict[str, str] = {}
    for entry in entries:
        if entry.get("type") == "tool_use":
            tool_use_id = entry.get("id", "")
            tool_name = entry.get("name", "")
            if tool_use_id and tool_name:
                tool_names[tool_use_id] = tool_name

    # Update errors with tool names
    for error in errors:
        if error.tool_use_id in tool_names:
            error.tool_name = tool_names[error.tool_use_id]


def extract_token_usage(entries: list[dict[str, Any]]) -> TokenUsage:
    """Extract and aggregate token usage from transcript entries.

    Parses transcript entries for:
    - message.usage fields (input_tokens, output_tokens, cache_creation_input_tokens,
      cache_read_input_tokens) in assistant messages
    - toolUseResult.totalTokens for subagent tokens

    Args:
        entries: List of transcript entries from Claude session

    Returns:
        TokenUsage object with aggregated token counts
    """
    input_tokens = 0
    output_tokens = 0
    cache_creation_tokens = 0
    cache_read_tokens = 0
    subagent_tokens = 0

    for entry in entries:
        # Extract from message.usage in assistant messages
        message = entry.get("message", {})
        if message:
            usage = message.get("usage", {})
            if usage:
                input_tokens += usage.get("input_tokens", 0)
                output_tokens += usage.get("output_tokens", 0)
                cache_creation_tokens += usage.get("cache_creation_input_tokens", 0)
                cache_read_tokens += usage.get("cache_read_input_tokens", 0)

        # Extract from toolUseResult.totalTokens for subagent tokens
        tool_use_result = entry.get("toolUseResult", {})
        if tool_use_result:
            total_tokens = tool_use_result.get("totalTokens", 0)
            if total_tokens:
                subagent_tokens += total_tokens

    return TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_tokens=cache_creation_tokens,
        cache_read_tokens=cache_read_tokens,
        subagent_tokens=subagent_tokens,
    )


# =============================================================================
# Main Data Collector
# =============================================================================


class DataCollector:
    """Collects and correlates data from trace and transcript files.

    The DataCollector reads both hook events (trace.jsonl) and the session
    transcript (transcript.jsonl), correlating them to produce a comprehensive
    view of test execution.

    Attributes:
        trace_path: Path to trace.jsonl file
        transcript_path: Path to transcript.jsonl transcript file

    Example:
        collector = DataCollector(
            trace_path="reports/trace.jsonl",
            transcript_path="~/.claude/projects/.../transcript.jsonl"
        )
        data = collector.collect()
    """

    def __init__(
        self,
        trace_path: Path | str | None = None,
        transcript_path: Path | str | None = None,
    ):
        """Initialize the DataCollector.

        Args:
            trace_path: Path to trace.jsonl file (optional)
            transcript_path: Path to transcript.jsonl transcript (optional)
        """
        self.trace_path = Path(trace_path) if trace_path else None
        self.transcript_path = Path(transcript_path) if transcript_path else None
        self._tool_to_agent_map: dict[str, tuple[str, str | None]] = {}

    def collect(self) -> CollectedData:
        """Collect and correlate all data from trace and transcript.

        Reads both files, correlates events, and extracts all relevant
        information into a CollectedData object.

        Returns:
            CollectedData with all collected and correlated information
        """
        data = CollectedData()

        # Parse trace file
        if self.trace_path:
            hook_events = parse_trace_file(self.trace_path)
            data.raw_hook_events = hook_events

            # Extract session info from SessionStart
            for event in hook_events:
                event_type = event.get("event") or event.get("hook_event_name")

                if event_type == "SessionStart":
                    data.session_id = event.get("session_id")
                    data.transcript_path = event.get("transcript_path")
                    data.cwd = event.get("cwd")
                    data.start_timestamp = parse_timestamp(event.get("ts"))

                elif event_type == "SessionEnd":
                    data.end_timestamp = parse_timestamp(event.get("ts"))
                    data.end_reason = event.get("reason")

                elif event_type == "UserPromptSubmit":
                    data.prompt = event.get("prompt")
                    data.prompt_timestamp = parse_timestamp(event.get("ts"))

            # Correlate tool calls and subagents
            data.tool_calls, data.subagents = correlate_events(hook_events)

            # Correlate tool calls with their parent agents
            self._tool_to_agent_map = correlate_tool_calls_with_agents(hook_events)
            data.tool_to_agent_map = self._tool_to_agent_map

        # Parse transcript file
        if self.transcript_path:
            transcript_entries = parse_transcript(self.transcript_path)
            data.raw_transcript_entries = transcript_entries

            # Extract errors
            data.errors = extract_errors_from_transcript(transcript_entries)
            extract_tool_names_from_transcript(transcript_entries, data.errors)

            # Mark tool calls with errors
            error_ids = {e.tool_use_id for e in data.errors}
            for tool_call in data.tool_calls:
                if tool_call.tool_use_id in error_ids:
                    tool_call.is_error = True
                    # Find matching error content
                    for error in data.errors:
                        if error.tool_use_id == tool_call.tool_use_id:
                            tool_call.error_content = error.error_content
                            break

            # Extract Claude responses
            data.claude_responses = extract_claude_responses(transcript_entries)

        # Analyze logs from CLI output for warnings/errors
        if data.claude_cli_stdout or data.claude_cli_stderr:
            combined_output = ""
            if data.claude_cli_stdout:
                combined_output += data.claude_cli_stdout
            if data.claude_cli_stderr:
                combined_output += "\n" + data.claude_cli_stderr
            data.log_analysis = analyze_logs(combined_output)

        logger.info(
            f"Collected data: {len(data.tool_calls)} tool calls, "
            f"{len(data.subagents)} subagents, "
            f"{len(data.claude_responses)} responses, "
            f"{len(data.errors)} errors"
        )

        return data

    def build_timeline(
        self, data: CollectedData, start_time: datetime | None = None
    ) -> list[TimelineEntry]:
        """Build a chronological timeline from collected data.

        Creates TimelineEntry objects from the collected data, suitable
        for inclusion in the test report.

        Args:
            data: CollectedData from collect()
            start_time: Reference start time for elapsed_ms calculation

        Returns:
            List of TimelineEntry objects in chronological order
        """
        entries = []
        seq = 0
        start_time = start_time or data.start_timestamp or datetime.min

        # Add prompt entry
        if data.prompt:
            seq += 1
            prompt_time = data.prompt_timestamp or start_time
            entries.append(
                TimelineEntry(
                    seq=seq,
                    type=TimelineEntryType.PROMPT,
                    timestamp=prompt_time,
                    elapsed_ms=int((prompt_time - start_time).total_seconds() * 1000)
                    if prompt_time > start_time
                    else 0,
                    content=data.prompt,
                )
            )

        # Add tool call entries
        for tool_call in data.tool_calls:
            seq += 1
            tc_time = tool_call.pre_timestamp or tool_call.post_timestamp or start_time
            elapsed = (
                int((tc_time - start_time).total_seconds() * 1000)
                if tc_time > start_time
                else 0
            )

            # Build tool input
            tool_input = ToolInput(
                command=tool_call.tool_input.get("command"),
                description=tool_call.tool_input.get("description"),
                file_path=tool_call.tool_input.get("file_path"),
                skill=tool_call.tool_input.get("skill"),
                args=tool_call.tool_input.get("args"),
            )

            # Build tool output
            tool_output = None
            if tool_call.tool_response:
                resp = tool_call.tool_response
                tool_output = ToolOutput(
                    stdout=resp.get("stdout"),
                    stderr=resp.get("stderr"),
                    exit_code=resp.get("exit_code"),
                    content=resp.get("content"),
                    is_error=tool_call.is_error,
                )

            # Get agent association for this tool call
            # Use data.tool_to_agent_map if self._tool_to_agent_map is empty
            # (this happens when a new collector is created in reporter.py)
            tool_map = self._tool_to_agent_map or data.tool_to_agent_map
            agent_info = tool_map.get(tool_call.tool_use_id)

            entries.append(
                TimelineEntry(
                    seq=seq,
                    type=TimelineEntryType.TOOL_CALL,
                    timestamp=tc_time,
                    elapsed_ms=elapsed,
                    tool=tool_call.tool_name,
                    input=tool_input,
                    output=tool_output,
                    duration_ms=tool_call.duration_ms,
                    intent=self._infer_intent(tool_call),
                    agent_id=agent_info[0] if agent_info else None,
                    agent_type=agent_info[1] if agent_info else None,
                    pid=tool_call.pid,
                    tool_use_id=tool_call.tool_use_id,
                )
            )

        # Add subagent entries
        for subagent in data.subagents:
            if subagent.start_timestamp:
                seq += 1
                entries.append(
                    TimelineEntry(
                        seq=seq,
                        type=TimelineEntryType.SUBAGENT_START,
                        timestamp=subagent.start_timestamp,
                        elapsed_ms=int(
                            (subagent.start_timestamp - start_time).total_seconds()
                            * 1000
                        )
                        if subagent.start_timestamp > start_time
                        else 0,
                        agent_id=subagent.agent_id,
                        agent_type=subagent.agent_type,
                    )
                )

            if subagent.stop_timestamp:
                seq += 1
                entries.append(
                    TimelineEntry(
                        seq=seq,
                        type=TimelineEntryType.SUBAGENT_STOP,
                        timestamp=subagent.stop_timestamp,
                        elapsed_ms=int(
                            (subagent.stop_timestamp - start_time).total_seconds()
                            * 1000
                        )
                        if subagent.stop_timestamp > start_time
                        else 0,
                        agent_id=subagent.agent_id,
                        agent_transcript_path=subagent.transcript_path,
                        duration_ms=subagent.duration_ms,
                    )
                )

        # Add response entries
        for response in data.claude_responses:
            seq += 1
            resp_time = response.timestamp or start_time

            # Create preview
            preview = response.text[:200] + "..." if len(response.text) > 200 else response.text

            entries.append(
                TimelineEntry(
                    seq=seq,
                    type=TimelineEntryType.RESPONSE,
                    timestamp=resp_time,
                    elapsed_ms=int((resp_time - start_time).total_seconds() * 1000)
                    if resp_time > start_time
                    else 0,
                    content=response.text,
                    content_preview=preview,
                    content_length=len(response.text),
                )
            )

        # Sort by timestamp
        entries.sort(key=lambda e: e.timestamp)

        # Renumber sequences after sorting
        for i, entry in enumerate(entries, 1):
            entry.seq = i

        return entries

    def _infer_intent(self, tool_call: CorrelatedToolCall) -> str:
        """Infer the intent/purpose of a tool call.

        Attempts to determine what the tool call was meant to accomplish
        based on the tool name and input.

        Args:
            tool_call: The tool call to analyze

        Returns:
            Human-readable intent string
        """
        tool_name = tool_call.tool_name
        tool_input = tool_call.tool_input

        # Use explicit description if available
        if tool_input.get("description"):
            return tool_input["description"]

        # Infer from tool type and command
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            return self._infer_bash_intent(command)
        elif tool_name == "Read":
            file_path = tool_input.get("file_path", "")
            return f"Read file: {Path(file_path).name}"
        elif tool_name == "Write":
            file_path = tool_input.get("file_path", "")
            return f"Write file: {Path(file_path).name}"
        elif tool_name == "Edit":
            file_path = tool_input.get("file_path", "")
            return f"Edit file: {Path(file_path).name}"
        elif tool_name == "Skill":
            skill = tool_input.get("skill", "")
            args = tool_input.get("args", "")
            return f"Invoke skill: {skill} {args}".strip()
        elif tool_name == "Task":
            return tool_input.get("description", "Run subagent task")
        elif tool_name == "Glob":
            pattern = tool_input.get("pattern", "")
            return f"Find files: {pattern}"
        elif tool_name == "Grep":
            pattern = tool_input.get("pattern", "")
            return f"Search for: {pattern}"

        return f"Execute {tool_name}"

    def _infer_bash_intent(self, command: str) -> str:
        """Infer intent from a Bash command.

        Args:
            command: The bash command string

        Returns:
            Human-readable intent
        """
        command = command.strip()

        # Common patterns
        if command.startswith("ls"):
            return "List files/directories"
        elif command.startswith("cat"):
            # Extract filename
            parts = command.split()
            if len(parts) > 1:
                return f"Read file: {Path(parts[1]).name}"
            return "Read file contents"
        elif command.startswith("mkdir"):
            return "Create directory"
        elif command.startswith("rm"):
            return "Remove files/directories"
        elif command.startswith("cp"):
            return "Copy files"
        elif command.startswith("mv"):
            return "Move/rename files"
        elif command.startswith("git"):
            parts = command.split()
            if len(parts) > 1:
                return f"Git: {parts[1]}"
            return "Git operation"
        elif command.startswith("cd"):
            return "Change directory"
        elif command.startswith("echo"):
            return "Output text"
        elif command.startswith("grep"):
            return "Search in files"
        elif command.startswith("find"):
            return "Find files"
        elif "pytest" in command:
            return "Run tests"
        elif "python" in command:
            return "Run Python script"

        # Fallback: use first word or truncate
        first_word = command.split()[0] if command else "unknown"
        if len(command) > 50:
            return f"Execute: {first_word}..."
        return f"Execute: {command}"
