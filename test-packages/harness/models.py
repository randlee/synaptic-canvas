"""
Pydantic models for the Claude Code Test Harness report schema v3.0.

This module defines strongly-typed models for test reports, supporting:
- Fixture-level reports containing multiple tests
- Individual test results with expectations and timeline
- Tool calls, hook events, and subagent tracking
- Side effects and Claude response capture

Schema version: 3.0

Example:
    from harness.models import FixtureReport, TestResult, Expectation

    # Create a test result
    test = TestResult(
        test_id="sc-startup-001",
        test_name="Startup readonly mode",
        status=TestStatus.PASS,
        ...
    )

    # Create fixture report
    report = FixtureReport(
        fixture=FixtureMeta(fixture_id="test_sc_startup", ...),
        tests=[test]
    )

    # Export to JSON
    json_data = report.model_dump_json(indent=2)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Enums
# =============================================================================


class TestStatus(str, Enum):
    """Overall test status."""
    __test__ = False  # Prevent pytest collection

    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"
    SKIPPED = "skipped"


class StatusIcon(str, Enum):
    """Visual status indicator for HTML reports."""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIPPED = "skipped"


class ExpectationType(str, Enum):
    """Types of expectations that can be evaluated."""

    TOOL_CALL = "tool_call"
    TOOL_NOT_CALLED = "tool_not_called"
    HOOK_EVENT = "hook_event"
    HOOK_EVENT_ABSENT = "hook_event_absent"
    SUBAGENT_EVENT = "subagent_event"
    SUBAGENT_LIFECYCLE = "subagent_lifecycle"
    OUTPUT_CONTAINS = "output_contains"
    EXECUTION_PARAM = "execution_param"
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"


class TimelineEntryType(str, Enum):
    """Types of timeline entries."""

    PROMPT = "prompt"
    TOOL_CALL = "tool_call"
    RESPONSE = "response"
    SUBAGENT_START = "subagent_start"
    SUBAGENT_STOP = "subagent_stop"


class HookEventType(str, Enum):
    """Types of hook events captured."""

    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    SUBAGENT_START = "SubagentStart"
    SUBAGENT_STOP = "SubagentStop"
    STOP = "Stop"
    NOTIFICATION = "Notification"
    PERMISSION_REQUEST = "PermissionRequest"


# =============================================================================
# Sub-models for Fixture
# =============================================================================


class FixtureSummary(BaseModel):
    """Summary statistics for a fixture's test results."""

    total_tests: int = Field(ge=0, description="Total number of tests in the fixture")
    passed: int = Field(ge=0, description="Number of tests that passed")
    failed: int = Field(ge=0, description="Number of tests that failed")
    partial: int = Field(ge=0, description="Number of tests with partial pass")
    skipped: int = Field(ge=0, description="Number of skipped tests")


class FixtureMeta(BaseModel):
    """Metadata about a test fixture."""

    fixture_id: str = Field(description="Unique identifier for the fixture")
    fixture_name: str = Field(description="Human-readable fixture name")
    package: str = Field(description="Package being tested (e.g., 'sc-startup')")
    agent_or_skill: str = Field(description="Agent or skill being tested")
    agent_or_skill_path: str | None = Field(
        default=None, description="Path to skill/agent markdown file"
    )
    fixture_path: str | None = Field(
        default=None, description="Path to fixture.yaml file"
    )
    report_path: str = Field(description="Path to the generated report file")
    generated_at: datetime = Field(description="When the report was generated")
    summary: FixtureSummary = Field(description="Summary statistics")
    tags: list[str] = Field(default_factory=list, description="Tags for filtering")


# =============================================================================
# Sub-models for Test Results
# =============================================================================


class TestMetadata(BaseModel):
    """Metadata about a specific test run."""
    __test__ = False  # Prevent pytest collection

    fixture: str = Field(description="Parent fixture ID")
    package: str = Field(description="Package being tested")
    model: str = Field(description="Claude model used (e.g., 'haiku', 'sonnet')")
    session_id: str | None = Field(default=None, description="Claude session ID")
    test_repo: str = Field(description="Path to test repository")


class GitState(BaseModel):
    """Git state at test execution time."""

    branch: str = Field(description="Current git branch")
    commit: str = Field(description="Current commit hash (short)")
    modified_files: list[str] = Field(
        default_factory=list, description="Files modified since last commit"
    )


class ReproduceSection(BaseModel):
    """Commands and environment needed to reproduce the test."""

    setup_commands: list[str] = Field(
        default_factory=list, description="Commands to set up the test environment"
    )
    test_command: str = Field(description="The Claude CLI command to run")
    cleanup_commands: list[str] = Field(
        default_factory=list, description="Commands to clean up after the test"
    )
    environment: dict[str, str] = Field(
        default_factory=dict, description="Required environment variables"
    )
    git_state: GitState | None = Field(
        default=None, description="Git state when test was run"
    )


class TokenUsage(BaseModel):
    """Token usage statistics from Claude."""

    input: int = Field(ge=0, description="Input tokens consumed")
    output: int = Field(ge=0, description="Output tokens generated")
    total: int = Field(ge=0, description="Total tokens (input + output)")


class ExecutionSection(BaseModel):
    """Test execution parameters."""

    prompt: str = Field(description="The prompt sent to Claude")
    model: str = Field(description="Model used for execution")
    tools_allowed: list[str] = Field(
        default_factory=list, description="Tools allowed via --tools flag"
    )
    token_usage: TokenUsage | None = Field(
        default=None, description="Token usage statistics"
    )


# =============================================================================
# Expectation Models
# =============================================================================


class ExpectationMatch(BaseModel):
    """Location where an expectation was matched."""

    sequence: int = Field(ge=1, description="Sequence number in timeline (1-based)")
    timestamp: datetime = Field(description="When the match occurred")


class ToolCallExpected(BaseModel):
    """Expected values for a tool_call expectation."""

    tool: str = Field(description="Expected tool name (e.g., 'Bash', 'Read')")
    pattern: str = Field(description="Regex pattern to match against tool input")


class ToolCallActual(BaseModel):
    """Actual values observed for a tool_call expectation."""

    tool: str = Field(description="Tool name that was called")
    command: str = Field(description="The actual command/input used")
    output_preview: str = Field(description="Truncated output preview")


class HookEventExpected(BaseModel):
    """Expected values for a hook_event expectation."""

    event: HookEventType = Field(description="Expected hook event type")
    filters: dict[str, Any] = Field(
        default_factory=dict, description="Optional field filters"
    )


class SubagentEventExpected(BaseModel):
    """Expected values for a subagent_event expectation."""

    event: str = Field(description="Expected event (SubagentStart or SubagentStop)")
    agent_id: str | None = Field(
        default=None, description="Expected agent ID (optional)"
    )
    agent_type: str | None = Field(
        default=None, description="Expected agent type (optional)"
    )


class OutputContainsExpected(BaseModel):
    """Expected values for an output_contains expectation."""

    pattern: str = Field(description="Regex pattern to search for in output")
    flags: str = Field(default="", description="Regex flags (e.g., 'i' for ignore case)")


class OutputContainsActual(BaseModel):
    """Actual values for an output_contains match."""

    matched_text: str = Field(description="The text that matched the pattern")
    context: str = Field(description="Surrounding context of the match")


class FileExpected(BaseModel):
    """Expected values for file-based expectations."""

    path: str = Field(description="Expected file path")


class FileActual(BaseModel):
    """Actual values for file-based expectations."""

    path: str = Field(description="Actual file path")
    size: int | None = Field(default=None, description="File size in bytes")


class Expectation(BaseModel):
    """A single expectation and its evaluation result.

    Expectations define what we expect to observe during a test and
    whether those expectations were met.
    """

    id: str = Field(description="Unique expectation ID (e.g., 'exp-001')")
    description: str = Field(description="Human-readable description")
    type: ExpectationType = Field(description="Type of expectation")
    status: TestStatus = Field(description="Whether expectation was met")
    has_details: bool = Field(
        default=False, description="Whether details should be shown in UI"
    )
    expected: dict[str, Any] = Field(
        description="Expected values (type-specific structure)"
    )
    actual: dict[str, Any] | None = Field(
        default=None, description="Actual observed values (null if not found)"
    )
    matched_at: ExpectationMatch | None = Field(
        default=None, description="Where the match occurred (if pass)"
    )
    failure_reason: str | None = Field(
        default=None, description="Explanation of why expectation failed"
    )


# =============================================================================
# Timeline Models
# =============================================================================


class ToolInput(BaseModel):
    """Input parameters for a tool call."""

    model_config = ConfigDict(extra="allow")

    command: str | None = Field(default=None, description="For Bash tool")
    description: str | None = Field(
        default=None, description="Description of the command"
    )
    file_path: str | None = Field(default=None, description="For Read/Write tools")
    skill: str | None = Field(default=None, description="For Skill tool")
    args: str | None = Field(default=None, description="For Skill tool arguments")
    # Generic catch-all for other tool inputs
    extra: dict[str, Any] = Field(
        default_factory=dict, description="Additional tool-specific inputs"
    )


class ToolOutput(BaseModel):
    """Output from a tool execution."""

    model_config = ConfigDict(extra="allow")

    stdout: str | None = Field(default=None, description="Standard output")
    stderr: str | None = Field(default=None, description="Standard error")
    exit_code: int | None = Field(default=None, description="Exit code (for Bash)")
    content: str | None = Field(
        default=None, description="Content (for Read/Write tools)"
    )
    is_error: bool = Field(default=False, description="Whether tool resulted in error")
    # Generic catch-all for other tool outputs
    extra: dict[str, Any] = Field(
        default_factory=dict, description="Additional tool-specific outputs"
    )


class TimelineEntry(BaseModel):
    """A single entry in the test execution timeline.

    Timeline entries capture the chronological sequence of events
    during test execution, including prompts, tool calls, and responses.
    """

    seq: int = Field(ge=1, description="Sequence number (1-based)")
    type: TimelineEntryType = Field(description="Type of timeline entry")
    timestamp: datetime = Field(description="When this entry occurred")
    elapsed_ms: int = Field(ge=0, description="Milliseconds since test start")

    # For tool_call type
    tool: str | None = Field(default=None, description="Tool name")
    input: ToolInput | None = Field(default=None, description="Tool input parameters")
    output: ToolOutput | None = Field(default=None, description="Tool output")
    duration_ms: int | None = Field(
        default=None, description="Tool execution duration in ms"
    )
    intent: str | None = Field(
        default=None, description="Inferred purpose of this action"
    )

    # For prompt/response types
    content: str | None = Field(default=None, description="Full content")
    content_preview: str | None = Field(default=None, description="Truncated preview")
    content_length: int | None = Field(
        default=None, description="Full content length in chars"
    )

    # For subagent types
    agent_id: str | None = Field(default=None, description="Subagent ID")
    agent_type: str | None = Field(default=None, description="Subagent type")
    agent_transcript_path: str | None = Field(
        default=None, description="Path to subagent transcript"
    )


# =============================================================================
# Side Effects and Response Models
# =============================================================================


class SideEffects(BaseModel):
    """File system changes made during test execution."""

    files_created: list[str] = Field(
        default_factory=list, description="Files created during test"
    )
    files_modified: list[str] = Field(
        default_factory=list, description="Files modified during test"
    )
    files_deleted: list[str] = Field(
        default_factory=list, description="Files deleted during test"
    )
    git_changes: bool = Field(default=False, description="Whether git state changed")


class ClaudeResponse(BaseModel):
    """Claude's final response to the user."""

    preview: str = Field(description="First ~200 characters of response")
    full_text: str = Field(description="Complete response text")
    word_count: int = Field(ge=0, description="Word count of response")


class DebugInfo(BaseModel):
    """Debug information for troubleshooting test failures."""

    pytest_output: str | None = Field(default=None, description="Raw pytest output")
    pytest_status: TestStatus | None = Field(default=None, description="Pytest result")
    raw_trace_file: str | None = Field(
        default=None, description="Path to trace.jsonl file"
    )
    errors: list[str] = Field(
        default_factory=list, description="Errors encountered during test"
    )


# =============================================================================
# Main Test Result Model
# =============================================================================


class TestResult(BaseModel):
    """Complete result for a single test execution.

    Contains all data collected during a test run including:
    - Test identification and metadata
    - Reproduction instructions
    - Execution parameters
    - Expectations and their evaluations
    - Timeline of events
    - Side effects
    - Claude's response
    - Debug information
    """
    __test__ = False  # Prevent pytest collection

    # Identification
    test_id: str = Field(description="Unique test identifier")
    test_name: str = Field(description="Human-readable test name")
    tab_label: str = Field(description="Short label for tab display")
    description: str = Field(description="Test description")

    # Status
    timestamp: datetime = Field(description="When test was executed")
    duration_ms: int = Field(ge=0, description="Test duration in milliseconds")
    status: TestStatus = Field(description="Overall test status")
    status_icon: StatusIcon = Field(description="Visual status indicator")
    pass_rate: str = Field(description="Pass rate string (e.g., '4/7')")
    tags: list[str] = Field(default_factory=list, description="Test tags")
    skip_reason: str | None = Field(
        default=None, description="Reason for skipping (if skipped)"
    )

    # Sections
    metadata: TestMetadata = Field(description="Test metadata")
    reproduce: ReproduceSection = Field(description="Reproduction instructions")
    execution: ExecutionSection = Field(description="Execution parameters")
    expectations: list[Expectation] = Field(
        default_factory=list, description="Test expectations"
    )
    timeline: list[TimelineEntry] = Field(
        default_factory=list, description="Execution timeline"
    )
    side_effects: SideEffects = Field(
        default_factory=SideEffects, description="File system changes"
    )
    claude_response: ClaudeResponse = Field(description="Claude's response")
    debug: DebugInfo = Field(default_factory=DebugInfo, description="Debug information")

    def compute_status(self) -> TestStatus:
        """Compute overall status from expectations.

        Returns:
            TestStatus.PASS if all expectations passed
            TestStatus.FAIL if no expectations passed
            TestStatus.PARTIAL if some expectations passed
            TestStatus.PASS if no expectations (vacuously true)
        """
        if not self.expectations:
            return TestStatus.PASS

        passed = sum(1 for e in self.expectations if e.status == TestStatus.PASS)
        total = len(self.expectations)

        if passed == total:
            return TestStatus.PASS
        elif passed == 0:
            return TestStatus.FAIL
        else:
            return TestStatus.PARTIAL

    def compute_pass_rate(self) -> str:
        """Compute pass rate string from expectations.

        Returns:
            String like "4/7" representing passed/total expectations
        """
        if not self.expectations:
            return "0/0"

        passed = sum(1 for e in self.expectations if e.status == TestStatus.PASS)
        total = len(self.expectations)
        return f"{passed}/{total}"


# =============================================================================
# Fixture Report Model (Top-level)
# =============================================================================


class FixtureReport(BaseModel):
    """Complete report for a test fixture.

    A fixture report contains multiple related tests for a single
    package/skill being tested. This is the top-level model for
    serialization to JSON.

    Schema version: 3.0
    """

    schema_version: str = Field(default="3.0", description="Schema version")
    fixture: FixtureMeta = Field(description="Fixture metadata")
    tests: list[TestResult] = Field(description="List of test results")

    def compute_summary(self) -> FixtureSummary:
        """Compute summary statistics from test results.

        Returns:
            FixtureSummary with counts for each status category
        """
        passed = sum(1 for t in self.tests if t.status == TestStatus.PASS)
        failed = sum(1 for t in self.tests if t.status == TestStatus.FAIL)
        partial = sum(1 for t in self.tests if t.status == TestStatus.PARTIAL)
        skipped = sum(1 for t in self.tests if t.status == TestStatus.SKIPPED)

        return FixtureSummary(
            total_tests=len(self.tests),
            passed=passed,
            failed=failed,
            partial=partial,
            skipped=skipped,
        )


# =============================================================================
# Hook Event Models (for trace.jsonl parsing)
# =============================================================================


class BaseHookEvent(BaseModel):
    """Base model for all hook events."""

    model_config = ConfigDict(populate_by_name=True)

    timestamp: datetime = Field(alias="ts", description="Event timestamp")
    event: HookEventType = Field(description="Hook event type")
    session_id: str = Field(description="Session identifier")
    transcript_path: str | None = Field(
        default=None, description="Path to transcript file"
    )
    cwd: str | None = Field(default=None, description="Current working directory")


class SessionStartEvent(BaseHookEvent):
    """SessionStart hook event."""

    source: str | None = Field(default=None, description="Source of startup")


class SessionEndEvent(BaseHookEvent):
    """SessionEnd hook event."""

    reason: str | None = Field(default=None, description="Reason for ending")


class UserPromptSubmitEvent(BaseHookEvent):
    """UserPromptSubmit hook event."""

    prompt: str = Field(description="User prompt text")
    permission_mode: str | None = Field(default=None, description="Permission mode")


class PreToolUseEvent(BaseHookEvent):
    """PreToolUse hook event."""

    tool_name: str = Field(description="Name of tool being used")
    tool_input: dict[str, Any] = Field(description="Tool input parameters")
    tool_use_id: str = Field(description="Unique tool use identifier")
    permission_mode: str | None = Field(default=None, description="Permission mode")


class PostToolUseEvent(BaseHookEvent):
    """PostToolUse hook event."""

    tool_name: str = Field(description="Name of tool that was used")
    tool_input: dict[str, Any] = Field(description="Tool input parameters")
    tool_response: dict[str, Any] = Field(description="Tool response")
    tool_use_id: str = Field(description="Unique tool use identifier")
    permission_mode: str | None = Field(default=None, description="Permission mode")


class SubagentStartEvent(BaseHookEvent):
    """SubagentStart hook event."""

    agent_id: str = Field(description="Unique subagent identifier")
    agent_type: str = Field(description="Type of subagent")


class SubagentStopEvent(BaseHookEvent):
    """SubagentStop hook event."""

    agent_id: str = Field(description="Unique subagent identifier")
    agent_transcript_path: str | None = Field(
        default=None, description="Path to subagent transcript"
    )


class StopEvent(BaseHookEvent):
    """Stop hook event."""

    stop_hook_active: bool | None = Field(
        default=None, description="Whether stop hook is active"
    )


# Type alias for all hook event types
HookEvent = (
    SessionStartEvent
    | SessionEndEvent
    | UserPromptSubmitEvent
    | PreToolUseEvent
    | PostToolUseEvent
    | SubagentStartEvent
    | SubagentStopEvent
    | StopEvent
)


# =============================================================================
# Transcript Entry Models (for session.jsonl parsing)
# =============================================================================


class TranscriptEntryType(str, Enum):
    """Types of entries in transcript files."""

    USER = "user"
    ASSISTANT = "assistant"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"


class TranscriptEntry(BaseModel):
    """Base model for transcript entries."""

    type: TranscriptEntryType = Field(description="Entry type")


class UserTranscriptEntry(TranscriptEntry):
    """User message in transcript."""

    message: dict[str, Any] = Field(description="User message content")


class AssistantTranscriptEntry(TranscriptEntry):
    """Assistant response in transcript."""

    message: dict[str, Any] = Field(description="Assistant message with content array")


class ToolUseTranscriptEntry(TranscriptEntry):
    """Tool use request in transcript."""

    id: str = Field(description="Tool use ID")
    name: str = Field(description="Tool name")
    input: dict[str, Any] = Field(description="Tool input")


class ToolResultTranscriptEntry(TranscriptEntry):
    """Tool result in transcript."""

    tool_use_id: str = Field(description="Matching tool use ID")
    content: str | list[dict[str, Any]] = Field(description="Tool result content")
    is_error: bool = Field(default=False, description="Whether result is an error")
