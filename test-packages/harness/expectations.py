"""
Expectations and assertions framework for Claude Code test harness.

This module provides a flexible system for defining and evaluating test
expectations against collected data from Claude Code sessions.

Expectation Types:
- ToolCallExpectation: Match tool name and command pattern (regex)
- HookEventExpectation: Match specific hook events (SessionStart, PreToolUse, etc.)
- SubagentEventExpectation: Match SubagentStart/SubagentStop with agent_type
- OutputContainsExpectation: Regex match on Claude's response text

Usage:
    from harness.expectations import (
        ToolCallExpectation,
        OutputContainsExpectation,
        evaluate_expectations,
    )
    from harness.collector import DataCollector

    # Define expectations
    expectations = [
        ToolCallExpectation(
            id="exp-001",
            description="Read config file",
            tool="Bash",
            pattern=r"cat.*config\\.yaml",
        ),
        OutputContainsExpectation(
            id="exp-002",
            description="Report generated",
            pattern=r"(startup.*report|SC-Startup Report)",
            flags="i",
        ),
    ]

    # Collect data
    collector = DataCollector(trace_path="trace.jsonl")
    data = collector.collect()

    # Evaluate expectations
    results = evaluate_expectations(expectations, data)
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .collector import (
    ClaudeResponseText,
    CollectedData,
    CorrelatedToolCall,
    SubagentLifecycle,
)
from .models import (
    Expectation,
    ExpectationMatch,
    ExpectationType,
    HookEventType,
    TestStatus,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Result Models
# =============================================================================


class ExpectationResult(BaseModel):
    """Result of evaluating a single expectation.

    Captures whether the expectation was met and provides detailed
    information about what was expected, what was observed, and why
    it passed or failed.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(description="Expectation ID (e.g., 'exp-001')")
    description: str = Field(description="Human-readable description")
    type: ExpectationType = Field(description="Type of expectation")
    status: TestStatus = Field(description="Whether expectation was met")
    expected: dict[str, Any] = Field(description="What was expected")
    actual: dict[str, Any] | None = Field(
        default=None, description="What was observed (None if not found)"
    )
    matched_at: ExpectationMatch | None = Field(
        default=None, description="Where match occurred (if passed)"
    )
    failure_reason: str | None = Field(
        default=None, description="Why it failed (if failed)"
    )

    def to_expectation_model(self) -> Expectation:
        """Convert to the Expectation model for report serialization."""
        return Expectation(
            id=self.id,
            description=self.description,
            type=self.type,
            status=self.status,
            has_details=True,
            expected=self.expected,
            actual=self.actual,
            matched_at=self.matched_at,
            failure_reason=self.failure_reason,
        )


# =============================================================================
# Base Expectation Evaluator
# =============================================================================


class ExpectationEvaluator(ABC):
    """Abstract base class for expectation evaluators.

    Subclasses implement specific expectation types (tool calls,
    hook events, output matching, etc.) by implementing the
    evaluate() method.
    """

    def __init__(
        self,
        id: str,
        description: str,
    ):
        """Initialize the expectation evaluator.

        Args:
            id: Unique expectation ID (e.g., 'exp-001')
            description: Human-readable description of what's being checked
        """
        self.id = id
        self.description = description

    @property
    @abstractmethod
    def expectation_type(self) -> ExpectationType:
        """Return the type of this expectation."""
        ...

    @abstractmethod
    def evaluate(self, data: CollectedData) -> ExpectationResult:
        """Evaluate this expectation against collected data.

        Args:
            data: CollectedData from a test session

        Returns:
            ExpectationResult with pass/fail status and details
        """
        ...

    def _create_pass_result(
        self,
        expected: dict[str, Any],
        actual: dict[str, Any],
        sequence: int,
        timestamp: datetime,
    ) -> ExpectationResult:
        """Create a passing result."""
        return ExpectationResult(
            id=self.id,
            description=self.description,
            type=self.expectation_type,
            status=TestStatus.PASS,
            expected=expected,
            actual=actual,
            matched_at=ExpectationMatch(sequence=sequence, timestamp=timestamp),
        )

    def _create_fail_result(
        self,
        expected: dict[str, Any],
        failure_reason: str,
        actual: dict[str, Any] | None = None,
    ) -> ExpectationResult:
        """Create a failing result."""
        return ExpectationResult(
            id=self.id,
            description=self.description,
            type=self.expectation_type,
            status=TestStatus.FAIL,
            expected=expected,
            actual=actual,
            failure_reason=failure_reason,
        )


# =============================================================================
# Tool Call Expectation
# =============================================================================


class ToolCallExpectation(ExpectationEvaluator):
    """Expectation that a specific tool was called with matching input.

    Matches tool calls by tool name and an optional regex pattern against
    the tool input. For Bash tools, the pattern is matched against the
    command string. For other tools, it's matched against the JSON input.

    Example:
        # Match any 'cat' command reading a yaml file
        exp = ToolCallExpectation(
            id="exp-001",
            description="Read config file",
            tool="Bash",
            pattern=r"cat.*\\.yaml",
        )

        # Match any Read tool call (no pattern required)
        exp = ToolCallExpectation(
            id="exp-002",
            description="Read some file",
            tool="Read",
        )
    """

    def __init__(
        self,
        id: str,
        description: str,
        tool: str,
        pattern: str | None = None,
        match_output: bool = False,
    ):
        """Initialize tool call expectation.

        Args:
            id: Unique expectation ID
            description: Human-readable description
            tool: Expected tool name (e.g., 'Bash', 'Read', 'Skill')
            pattern: Regex pattern to match against tool input (optional)
            match_output: If True, also match pattern against output
        """
        super().__init__(id, description)
        self.tool = tool
        self.pattern = pattern
        self.match_output = match_output
        self._compiled_pattern = re.compile(pattern) if pattern else None

    @property
    def expectation_type(self) -> ExpectationType:
        return ExpectationType.TOOL_CALL

    def evaluate(self, data: CollectedData) -> ExpectationResult:
        """Evaluate against collected tool calls."""
        expected = {"tool": self.tool}
        if self.pattern:
            expected["pattern"] = self.pattern

        # Search through tool calls
        for idx, tool_call in enumerate(data.tool_calls, 1):
            if tool_call.tool_name != self.tool:
                continue

            # Get searchable text from tool input
            search_text = self._get_search_text(tool_call)

            # If no pattern, any call to this tool matches
            if not self._compiled_pattern:
                actual = self._build_actual(tool_call)
                timestamp = (
                    tool_call.pre_timestamp or tool_call.post_timestamp or datetime.now()
                )
                return self._create_pass_result(expected, actual, idx, timestamp)

            # Try to match the pattern
            if self._compiled_pattern.search(search_text):
                actual = self._build_actual(tool_call)
                timestamp = (
                    tool_call.pre_timestamp or tool_call.post_timestamp or datetime.now()
                )
                return self._create_pass_result(expected, actual, idx, timestamp)

            # Optionally match against output
            if self.match_output and tool_call.tool_response:
                output_text = self._get_output_text(tool_call)
                if self._compiled_pattern.search(output_text):
                    actual = self._build_actual(tool_call)
                    timestamp = (
                        tool_call.post_timestamp
                        or tool_call.pre_timestamp
                        or datetime.now()
                    )
                    return self._create_pass_result(expected, actual, idx, timestamp)

        # No match found
        tool_calls_found = [
            tc.tool_name for tc in data.tool_calls if tc.tool_name == self.tool
        ]
        if tool_calls_found:
            failure_reason = (
                f"Found {len(tool_calls_found)} {self.tool} calls but none matched "
                f"pattern: {self.pattern}"
            )
        else:
            failure_reason = f"No {self.tool} tool calls found"

        return self._create_fail_result(expected, failure_reason)

    def _get_search_text(self, tool_call: CorrelatedToolCall) -> str:
        """Extract searchable text from tool input."""
        tool_input = tool_call.tool_input

        if tool_call.tool_name == "Bash":
            return tool_input.get("command", "")
        elif tool_call.tool_name == "Read":
            return tool_input.get("file_path", "")
        elif tool_call.tool_name == "Write":
            return tool_input.get("file_path", "")
        elif tool_call.tool_name == "Edit":
            return tool_input.get("file_path", "")
        elif tool_call.tool_name == "Skill":
            skill = tool_input.get("skill", "")
            args = tool_input.get("args", "")
            return f"{skill} {args}"
        elif tool_call.tool_name == "Glob":
            return tool_input.get("pattern", "")
        elif tool_call.tool_name == "Grep":
            return tool_input.get("pattern", "")
        else:
            # Generic: stringify the input
            import json

            return json.dumps(tool_input)

    def _get_output_text(self, tool_call: CorrelatedToolCall) -> str:
        """Extract searchable text from tool output."""
        if not tool_call.tool_response:
            return ""

        response = tool_call.tool_response
        parts = []

        if "stdout" in response:
            parts.append(str(response["stdout"]))
        if "stderr" in response:
            parts.append(str(response["stderr"]))
        if "content" in response:
            parts.append(str(response["content"]))

        return "\n".join(parts)

    def _build_actual(self, tool_call: CorrelatedToolCall) -> dict[str, Any]:
        """Build actual data for the result."""
        actual = {
            "tool": tool_call.tool_name,
            "command": self._get_search_text(tool_call),
        }

        # Add output preview
        if tool_call.tool_response:
            output = self._get_output_text(tool_call)
            actual["output_preview"] = output[:200] + "..." if len(output) > 200 else output

        return actual


# =============================================================================
# Hook Event Expectation
# =============================================================================


class HookEventExpectation(ExpectationEvaluator):
    """Expectation that a specific hook event occurred.

    Matches hook events by event type and optional field filters.

    Example:
        # Expect SessionStart event
        exp = HookEventExpectation(
            id="exp-001",
            description="Session started",
            event=HookEventType.SESSION_START,
        )

        # Expect PreToolUse with specific tool
        exp = HookEventExpectation(
            id="exp-002",
            description="Bash tool used",
            event=HookEventType.PRE_TOOL_USE,
            filters={"tool_name": "Bash"},
        )
    """

    def __init__(
        self,
        id: str,
        description: str,
        event: HookEventType,
        filters: dict[str, Any] | None = None,
    ):
        """Initialize hook event expectation.

        Args:
            id: Unique expectation ID
            description: Human-readable description
            event: Expected hook event type
            filters: Optional dict of field names to expected values
        """
        super().__init__(id, description)
        self.event = event
        self.filters = filters or {}

    @property
    def expectation_type(self) -> ExpectationType:
        return ExpectationType.HOOK_EVENT

    def evaluate(self, data: CollectedData) -> ExpectationResult:
        """Evaluate against raw hook events."""
        expected = {"event": self.event.value}
        if self.filters:
            expected["filters"] = self.filters

        # Search through raw hook events
        for idx, event in enumerate(data.raw_hook_events, 1):
            event_type = event.get("event") or event.get("hook_event_name")

            if event_type != self.event.value:
                continue

            # Check filters
            if self._matches_filters(event):
                actual = {
                    "event": event_type,
                    **{k: event.get(k) for k in self.filters.keys() if k in event},
                }
                timestamp = self._parse_timestamp(event.get("ts"))
                return self._create_pass_result(expected, actual, idx, timestamp)

        # No match found
        matching_events = [
            e
            for e in data.raw_hook_events
            if (e.get("event") or e.get("hook_event_name")) == self.event.value
        ]

        if matching_events:
            failure_reason = (
                f"Found {len(matching_events)} {self.event.value} events but "
                f"none matched filters: {self.filters}"
            )
        else:
            failure_reason = f"No {self.event.value} events found"

        return self._create_fail_result(expected, failure_reason)

    def _matches_filters(self, event: dict[str, Any]) -> bool:
        """Check if event matches all filters."""
        for key, expected_value in self.filters.items():
            actual_value = event.get(key)

            # Support regex patterns for string values
            if isinstance(expected_value, str) and expected_value.startswith("regex:"):
                pattern = expected_value[6:]  # Remove "regex:" prefix
                if not re.search(pattern, str(actual_value)):
                    return False
            elif actual_value != expected_value:
                return False

        return True

    def _parse_timestamp(self, ts_str: str | None) -> datetime:
        """Parse timestamp string or return current time."""
        if not ts_str:
            return datetime.now()

        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now()


# =============================================================================
# Subagent Event Expectation
# =============================================================================


class SubagentEventExpectation(ExpectationEvaluator):
    """Expectation for subagent lifecycle events.

    Matches SubagentStart and SubagentStop events with optional
    filtering by agent_id or agent_type.

    Example:
        # Expect any subagent to start
        exp = SubagentEventExpectation(
            id="exp-001",
            description="Subagent spawned",
            event="SubagentStart",
        )

        # Expect Explore subagent specifically
        exp = SubagentEventExpectation(
            id="exp-002",
            description="Explore subagent used",
            event="SubagentStart",
            agent_type="Explore",
        )
    """

    def __init__(
        self,
        id: str,
        description: str,
        event: str,
        agent_id: str | None = None,
        agent_type: str | None = None,
    ):
        """Initialize subagent event expectation.

        Args:
            id: Unique expectation ID
            description: Human-readable description
            event: Either "SubagentStart" or "SubagentStop"
            agent_id: Optional specific agent ID to match
            agent_type: Optional agent type to match (e.g., "Explore", "Task")
        """
        super().__init__(id, description)
        self.event = event
        self.agent_id = agent_id
        self.agent_type = agent_type

    @property
    def expectation_type(self) -> ExpectationType:
        return ExpectationType.SUBAGENT_EVENT

    def evaluate(self, data: CollectedData) -> ExpectationResult:
        """Evaluate against collected subagent data."""
        expected: dict[str, Any] = {"event": self.event}
        if self.agent_id:
            expected["agent_id"] = self.agent_id
        if self.agent_type:
            expected["agent_type"] = self.agent_type

        # Search through subagents
        for idx, subagent in enumerate(data.subagents, 1):
            # Check event type
            if self.event == "SubagentStart":
                if not subagent.start_timestamp:
                    continue
                timestamp = subagent.start_timestamp
            elif self.event == "SubagentStop":
                if not subagent.stop_timestamp:
                    continue
                timestamp = subagent.stop_timestamp
            else:
                continue

            # Check agent_id filter
            if self.agent_id and subagent.agent_id != self.agent_id:
                continue

            # Check agent_type filter
            if self.agent_type and subagent.agent_type != self.agent_type:
                continue

            # Match found
            actual = {
                "event": self.event,
                "agent_id": subagent.agent_id,
                "agent_type": subagent.agent_type,
            }
            return self._create_pass_result(expected, actual, idx, timestamp)

        # No match found
        if data.subagents:
            types_found = [s.agent_type for s in data.subagents if s.agent_type]
            failure_reason = (
                f"Found {len(data.subagents)} subagents (types: {types_found}) "
                f"but none matched criteria"
            )
        else:
            failure_reason = "No subagent events found"

        return self._create_fail_result(expected, failure_reason)


# =============================================================================
# Output Contains Expectation
# =============================================================================


class OutputContainsExpectation(ExpectationEvaluator):
    """Expectation that Claude's response contains a pattern.

    Matches a regex pattern against Claude's text responses.
    Supports case-insensitive matching and other regex flags.

    Example:
        # Match report header (case insensitive)
        exp = OutputContainsExpectation(
            id="exp-001",
            description="Report generated",
            pattern=r"SC-Startup Report",
            flags="i",
        )

        # Match success message
        exp = OutputContainsExpectation(
            id="exp-002",
            description="Success indicated",
            pattern=r"successfully completed",
        )
    """

    def __init__(
        self,
        id: str,
        description: str,
        pattern: str,
        flags: str = "",
    ):
        """Initialize output contains expectation.

        Args:
            id: Unique expectation ID
            description: Human-readable description
            pattern: Regex pattern to search for
            flags: Regex flags as string (e.g., "i" for ignore case,
                   "m" for multiline, "s" for dotall)
        """
        super().__init__(id, description)
        self.pattern = pattern
        self.flags = flags
        self._compiled_pattern = self._compile_pattern()

    def _compile_pattern(self) -> re.Pattern:
        """Compile pattern with flags."""
        regex_flags = 0
        if "i" in self.flags:
            regex_flags |= re.IGNORECASE
        if "m" in self.flags:
            regex_flags |= re.MULTILINE
        if "s" in self.flags:
            regex_flags |= re.DOTALL

        return re.compile(self.pattern, regex_flags)

    @property
    def expectation_type(self) -> ExpectationType:
        return ExpectationType.OUTPUT_CONTAINS

    def evaluate(self, data: CollectedData) -> ExpectationResult:
        """Evaluate against Claude's responses."""
        expected = {"pattern": self.pattern}
        if self.flags:
            expected["flags"] = self.flags

        # Search through Claude responses
        for idx, response in enumerate(data.claude_responses, 1):
            search_text = response.text
            if data.prompt and data.prompt in search_text:
                search_text = search_text.replace(data.prompt, "")
            match = self._compiled_pattern.search(search_text)
            if match:
                # Extract matched text and context
                matched_text = match.group(0)
                start = max(0, match.start() - 50)
                end = min(len(search_text), match.end() + 50)
                context = search_text[start:end]

                actual = {
                    "matched_text": matched_text,
                    "context": f"...{context}..." if start > 0 or end < len(search_text) else context,
                }
                timestamp = response.timestamp or datetime.now()
                return self._create_pass_result(expected, actual, idx, timestamp)

        # No match found
        if data.claude_responses:
            total_chars = sum(len(r.text) for r in data.claude_responses)
            failure_reason = (
                f"Pattern '{self.pattern}' not found in {len(data.claude_responses)} "
                f"responses ({total_chars} total characters)"
            )
        else:
            failure_reason = "No Claude responses to search"

        return self._create_fail_result(expected, failure_reason)


# =============================================================================
# Negated Expectation Wrapper
# =============================================================================


class NotExpectation(ExpectationEvaluator):
    """Wrapper that negates another expectation.

    Useful for asserting that something did NOT happen.

    Example:
        # Expect NO subagent to be spawned
        exp = NotExpectation(
            SubagentEventExpectation(
                id="exp-001",
                description="No subagent spawned",
                event="SubagentStart",
            )
        )
    """

    def __init__(self, inner: ExpectationEvaluator):
        """Initialize with the expectation to negate.

        Args:
            inner: The expectation to negate
        """
        super().__init__(
            id=inner.id,
            description=f"NOT: {inner.description}",
        )
        self.inner = inner

    @property
    def expectation_type(self) -> ExpectationType:
        return self.inner.expectation_type

    def evaluate(self, data: CollectedData) -> ExpectationResult:
        """Evaluate by negating the inner expectation's result."""
        inner_result = self.inner.evaluate(data)

        if inner_result.status == TestStatus.PASS:
            # Inner passed, so negation fails
            return self._create_fail_result(
                expected={"NOT": inner_result.expected},
                failure_reason=f"Expected NOT to find: {inner_result.description}",
                actual=inner_result.actual,
            )
        else:
            # Inner failed, so negation passes
            return ExpectationResult(
                id=self.id,
                description=self.description,
                type=self.expectation_type,
                status=TestStatus.PASS,
                expected={"NOT": inner_result.expected},
                actual=None,  # Nothing found, which is correct
            )


# =============================================================================
# Evaluation Functions
# =============================================================================


def evaluate_expectations(
    expectations: list[ExpectationEvaluator],
    data: CollectedData,
) -> list[ExpectationResult]:
    """Evaluate a list of expectations against collected data.

    Args:
        expectations: List of expectation evaluators
        data: CollectedData from a test session

    Returns:
        List of ExpectationResult objects
    """
    results = []

    for expectation in expectations:
        try:
            result = expectation.evaluate(data)
            results.append(result)
            logger.debug(
                f"Expectation {result.id}: {result.status.value} - {result.description}"
            )
        except Exception as e:
            logger.error(f"Error evaluating expectation {expectation.id}: {e}")
            results.append(
                ExpectationResult(
                    id=expectation.id,
                    description=expectation.description,
                    type=expectation.expectation_type,
                    status=TestStatus.FAIL,
                    expected={},
                    failure_reason=f"Evaluation error: {str(e)}",
                )
            )

    return results


def compute_overall_status(results: list[ExpectationResult]) -> TestStatus:
    """Compute overall test status from expectation results.

    Args:
        results: List of ExpectationResult objects

    Returns:
        TestStatus.PASS if all passed
        TestStatus.FAIL if none passed
        TestStatus.PARTIAL if some passed
        TestStatus.PASS if no expectations (vacuously true)
    """
    if not results:
        return TestStatus.PASS

    passed = sum(1 for r in results if r.status == TestStatus.PASS)
    total = len(results)

    if passed == total:
        return TestStatus.PASS
    elif passed == 0:
        return TestStatus.FAIL
    else:
        return TestStatus.PARTIAL


def compute_pass_rate(results: list[ExpectationResult]) -> str:
    """Compute pass rate string from results.

    Args:
        results: List of ExpectationResult objects

    Returns:
        String like "4/7" representing passed/total
    """
    if not results:
        return "0/0"

    passed = sum(1 for r in results if r.status == TestStatus.PASS)
    return f"{passed}/{len(results)}"


# =============================================================================
# Implicit Expectations (Auto-generated)
# =============================================================================


class NoWarningsExpectation(ExpectationEvaluator):
    """Implicit expectation that no warnings or errors appear in logs.

    This expectation runs AFTER all explicit expectations and fails the test
    if any warnings or errors are detected in the log output, unless
    `allow_warnings: true` is set in the test YAML.

    The purpose is to prevent silent failures where a test appears to pass
    but actually contains concerning log entries that indicate problems.

    IMPORTANT: The `allow_warnings` flag should only be used with explicit
    user approval. Suppressing warnings is strongly discouraged for production
    tests and should only be used when:
    - The warning is a known false positive
    - The warning is being actively investigated in a separate issue
    - The test is specifically designed to trigger warnings (e.g., error path testing)

    Example YAML with override (requires user approval):
        test_id: sc-startup-error-handling
        test_name: Test error handling path
        allow_warnings: true  # APPROVED: This test intentionally triggers warnings
        execution:
          prompt: "Run /sc-startup with invalid config"

    Example:
        # Default: fail on warnings
        exp = NoWarningsExpectation(
            id="implicit-no-warnings",
            description="No warnings or errors in logs",
        )

        # Override: allow warnings (use sparingly!)
        exp = NoWarningsExpectation(
            id="implicit-no-warnings",
            description="No warnings or errors in logs",
            allow_warnings=True,
        )
    """

    def __init__(
        self,
        id: str = "implicit-no-warnings",
        description: str = "No warnings or errors in logs",
        allow_warnings: bool = False,
    ):
        """Initialize the no-warnings expectation.

        Args:
            id: Unique expectation ID (default: 'implicit-no-warnings')
            description: Human-readable description
            allow_warnings: If True, warnings are allowed (test won't fail).
                           This should only be used with explicit user approval.
        """
        super().__init__(id, description)
        self.allow_warnings = allow_warnings

    @property
    def expectation_type(self) -> ExpectationType:
        return ExpectationType.HOOK_EVENT  # Using HOOK_EVENT as closest match

    def evaluate(self, data: CollectedData) -> ExpectationResult:
        """Evaluate log analysis for warnings and errors.

        This expectation checks the `log_analysis` attribute on CollectedData.
        If log_analysis is not available (Agent 9A not yet implemented), the
        expectation passes with a note that log analysis is not available.

        Args:
            data: CollectedData from a test session

        Returns:
            ExpectationResult indicating pass/fail based on log analysis
        """
        expected = {
            "no_warnings": True,
            "no_errors": True,
            "allow_warnings": self.allow_warnings,
        }

        # Check if log_analysis is available
        log_analysis = getattr(data, "log_analysis", None)

        if log_analysis is None:
            # Log analysis not available yet (Agent 9A pending)
            # Pass the test but note that analysis is pending
            return ExpectationResult(
                id=self.id,
                description=self.description,
                type=self.expectation_type,
                status=TestStatus.PASS,
                expected=expected,
                actual={"log_analysis_available": False},
                matched_at=ExpectationMatch(
                    sequence=1,  # Use 1 as minimum (model requires >= 1)
                    timestamp=datetime.now(),
                ),
            )

        # Check if there are issues
        has_issues = getattr(log_analysis, "has_issues", False)
        warnings = getattr(log_analysis, "warnings", [])
        errors = getattr(log_analysis, "errors", [])

        # Build actual values
        actual = {
            "warning_count": len(warnings),
            "error_count": len(errors),
            "has_issues": has_issues,
        }

        # If warnings are allowed, pass even if there are warnings
        if self.allow_warnings:
            if errors:
                # Errors are never allowed, even with allow_warnings
                return self._create_fail_result(
                    expected=expected,
                    failure_reason=(
                        f"Found {len(errors)} error(s) in logs. "
                        "Errors are not suppressed by allow_warnings. "
                        f"First error: {self._format_log_entry(errors[0])}"
                    ),
                    actual=actual,
                )
            else:
                # Warnings are allowed, pass even if present
                return ExpectationResult(
                    id=self.id,
                    description=self.description,
                    type=self.expectation_type,
                    status=TestStatus.PASS,
                    expected=expected,
                    actual=actual,
                    matched_at=ExpectationMatch(
                        sequence=1,  # Use 1 as minimum (model requires >= 1)
                        timestamp=datetime.now(),
                    ),
                )

        # Default: fail on any warnings or errors
        if has_issues:
            # Build failure message
            issues = []
            if warnings:
                issues.append(f"{len(warnings)} warning(s)")
            if errors:
                issues.append(f"{len(errors)} error(s)")

            # Get first issue for detail
            first_issue = None
            if errors:
                first_issue = self._format_log_entry(errors[0])
            elif warnings:
                first_issue = self._format_log_entry(warnings[0])

            failure_reason = f"Found {', '.join(issues)} in logs."
            if first_issue:
                failure_reason += f" First issue: {first_issue}"
            failure_reason += (
                " Set 'allow_warnings: true' in test YAML to suppress "
                "(requires user approval)."
            )

            return self._create_fail_result(
                expected=expected,
                failure_reason=failure_reason,
                actual=actual,
            )

        # No issues found - pass
        return self._create_pass_result(
            expected=expected,
            actual=actual,
            sequence=1,  # Use 1 as minimum (model requires >= 1)
            timestamp=datetime.now(),
        )

    def _format_log_entry(self, entry: Any) -> str:
        """Format a log entry for display in failure message.

        Args:
            entry: LogEntry object or dict with log entry info

        Returns:
            Formatted string representation
        """
        if hasattr(entry, "message"):
            # LogEntry object
            level = getattr(entry, "level", "UNKNOWN")
            # Handle enum values (LogLevel.WARNING -> "WARNING")
            if hasattr(level, "value"):
                level = level.value
            message = entry.message
            return f"[{level}] {message[:100]}..." if len(message) > 100 else f"[{level}] {message}"
        elif isinstance(entry, dict):
            level = entry.get("level", "UNKNOWN")
            message = entry.get("message", str(entry))
            return f"[{level}] {message[:100]}..." if len(message) > 100 else f"[{level}] {message}"
        else:
            msg = str(entry)
            return msg[:100] + "..." if len(msg) > 100 else msg
