"""
Unit tests for harness.expectations module.

Tests the expectations/assertions framework including:
- ToolCallExpectation
- HookEventExpectation
- SubagentEventExpectation
- OutputContainsExpectation
- NotExpectation (negation wrapper)
- Evaluation functions

Each expectation type is tested for both passing and failing scenarios
using mock data that simulates real hook events and responses.
"""

from datetime import datetime, timedelta

import pytest

from harness.collector import (
    ClaudeResponseText,
    CollectedData,
    CorrelatedToolCall,
    SubagentLifecycle,
)
from harness.expectations import (
    ExpectationResult,
    HookEventExpectation,
    NotExpectation,
    OutputContainsExpectation,
    SubagentEventExpectation,
    ToolCallExpectation,
    compute_overall_status,
    compute_pass_rate,
    evaluate_expectations,
)
from harness.models import ExpectationMatch
from harness.models import ExpectationType, HookEventType, TestStatus


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def base_timestamp():
    """Base timestamp for test data."""
    return datetime(2026, 1, 16, 10, 0, 0)


@pytest.fixture
def sample_tool_calls(base_timestamp):
    """Sample tool calls for testing."""
    return [
        CorrelatedToolCall(
            tool_use_id="toolu_001",
            tool_name="Bash",
            tool_input={"command": "cat .claude/sc-startup.yaml", "description": "Read config"},
            tool_response={"stdout": "prompt_file: pm/ARCH-SC.md\n", "stderr": ""},
            pre_timestamp=base_timestamp,
            post_timestamp=base_timestamp + timedelta(milliseconds=100),
        ),
        CorrelatedToolCall(
            tool_use_id="toolu_002",
            tool_name="Bash",
            tool_input={"command": "cat pm/ARCH-SC.md"},
            tool_response={"stdout": "# Architecture\n...", "stderr": ""},
            pre_timestamp=base_timestamp + timedelta(seconds=1),
            post_timestamp=base_timestamp + timedelta(seconds=1, milliseconds=200),
        ),
        CorrelatedToolCall(
            tool_use_id="toolu_003",
            tool_name="Read",
            tool_input={"file_path": "/path/to/config.yaml"},
            tool_response={"content": "setting: value"},
            pre_timestamp=base_timestamp + timedelta(seconds=2),
        ),
        CorrelatedToolCall(
            tool_use_id="toolu_004",
            tool_name="Skill",
            tool_input={"skill": "sc-startup", "args": "--readonly"},
            tool_response={"content": "Skill invoked"},
            pre_timestamp=base_timestamp + timedelta(seconds=3),
        ),
    ]


@pytest.fixture
def sample_hook_events(base_timestamp):
    """Sample raw hook events for testing."""
    return [
        {
            "event": "SessionStart",
            "session_id": "sess-123",
            "ts": base_timestamp.isoformat(),
            "cwd": "/path/to/project",
        },
        {
            "event": "UserPromptSubmit",
            "session_id": "sess-123",
            "prompt": "/sc-startup --readonly",
            "ts": (base_timestamp + timedelta(seconds=1)).isoformat(),
        },
        {
            "event": "PreToolUse",
            "session_id": "sess-123",
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
            "tool_use_id": "toolu_005",
            "ts": (base_timestamp + timedelta(seconds=2)).isoformat(),
        },
        {
            "event": "PostToolUse",
            "session_id": "sess-123",
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
            "tool_response": {"stdout": "file.txt"},
            "tool_use_id": "toolu_005",
            "ts": (base_timestamp + timedelta(seconds=3)).isoformat(),
        },
        {
            "event": "SessionEnd",
            "session_id": "sess-123",
            "reason": "completed",
            "ts": (base_timestamp + timedelta(seconds=10)).isoformat(),
        },
    ]


@pytest.fixture
def sample_subagents(base_timestamp):
    """Sample subagent lifecycle data for testing."""
    return [
        SubagentLifecycle(
            agent_id="agent-001",
            agent_type="Explore",
            start_timestamp=base_timestamp + timedelta(seconds=5),
            stop_timestamp=base_timestamp + timedelta(seconds=8),
            transcript_path="/path/to/subagent/transcript.jsonl",
        ),
        SubagentLifecycle(
            agent_id="agent-002",
            agent_type="Task",
            start_timestamp=base_timestamp + timedelta(seconds=6),
            stop_timestamp=None,  # Still running or no stop event
        ),
    ]


@pytest.fixture
def sample_responses(base_timestamp):
    """Sample Claude responses for testing."""
    return [
        ClaudeResponseText(
            text="I'll analyze the SC-Startup configuration for you.",
            timestamp=base_timestamp + timedelta(seconds=1),
        ),
        ClaudeResponseText(
            text="""## SC-Startup Report

The startup configuration has been analyzed successfully.

### Key Findings:
- Configuration file loaded
- Prompt file read
- No errors detected

Status: **Complete**""",
            timestamp=base_timestamp + timedelta(seconds=9),
        ),
    ]


@pytest.fixture
def sample_collected_data(
    base_timestamp,
    sample_tool_calls,
    sample_hook_events,
    sample_subagents,
    sample_responses,
):
    """Complete sample CollectedData for testing."""
    return CollectedData(
        session_id="sess-123",
        cwd="/path/to/project",
        start_timestamp=base_timestamp,
        end_timestamp=base_timestamp + timedelta(seconds=10),
        prompt="/sc-startup --readonly",
        prompt_timestamp=base_timestamp + timedelta(seconds=1),
        tool_calls=sample_tool_calls,
        subagents=sample_subagents,
        claude_responses=sample_responses,
        raw_hook_events=sample_hook_events,
    )


@pytest.fixture
def empty_collected_data():
    """Empty CollectedData for testing failure cases."""
    return CollectedData()


# =============================================================================
# ToolCallExpectation Tests
# =============================================================================


class TestToolCallExpectation:
    """Tests for ToolCallExpectation."""

    def test_matches_tool_name_only(self, sample_collected_data):
        """Test matching by tool name without pattern."""
        exp = ToolCallExpectation(
            id="exp-001",
            description="Bash tool used",
            tool="Bash",
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.PASS
        assert result.actual["tool"] == "Bash"
        assert result.matched_at is not None
        assert result.matched_at.sequence == 1

    def test_matches_tool_with_pattern(self, sample_collected_data):
        """Test matching tool name and command pattern."""
        exp = ToolCallExpectation(
            id="exp-002",
            description="Read config file",
            tool="Bash",
            pattern=r"cat.*sc-startup\.yaml",
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.PASS
        assert "sc-startup.yaml" in result.actual["command"]

    def test_matches_read_tool(self, sample_collected_data):
        """Test matching Read tool by file path pattern."""
        exp = ToolCallExpectation(
            id="exp-003",
            description="Read yaml config",
            tool="Read",
            pattern=r"config\.yaml$",
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.PASS
        assert result.actual["tool"] == "Read"

    def test_matches_skill_tool(self, sample_collected_data):
        """Test matching Skill tool by skill name."""
        exp = ToolCallExpectation(
            id="exp-004",
            description="Invoke sc-startup skill",
            tool="Skill",
            pattern=r"sc-startup.*--readonly",
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.PASS
        assert "sc-startup" in result.actual["command"]

    def test_fails_when_tool_not_found(self, sample_collected_data):
        """Test failure when tool not used."""
        exp = ToolCallExpectation(
            id="exp-005",
            description="Write tool used",
            tool="Write",
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.FAIL
        assert "No Write tool calls found" in result.failure_reason

    def test_fails_when_pattern_not_matched(self, sample_collected_data):
        """Test failure when pattern doesn't match."""
        exp = ToolCallExpectation(
            id="exp-006",
            description="Read nonexistent file",
            tool="Bash",
            pattern=r"cat.*nonexistent\.txt",
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.FAIL
        assert "none matched pattern" in result.failure_reason

    def test_fails_on_empty_data(self, empty_collected_data):
        """Test failure with no data."""
        exp = ToolCallExpectation(
            id="exp-007",
            description="Any Bash call",
            tool="Bash",
        )

        result = exp.evaluate(empty_collected_data)

        assert result.status == TestStatus.FAIL
        assert "No Bash tool calls found" in result.failure_reason

    def test_includes_output_preview(self, sample_collected_data):
        """Test that output preview is included in actual data."""
        exp = ToolCallExpectation(
            id="exp-008",
            description="Read config",
            tool="Bash",
            pattern=r"cat.*sc-startup\.yaml",
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.PASS
        assert "output_preview" in result.actual
        assert "prompt_file" in result.actual["output_preview"]

    def test_expectation_type(self):
        """Test that expectation type is correct."""
        exp = ToolCallExpectation(id="exp", description="test", tool="Bash")
        assert exp.expectation_type == ExpectationType.TOOL_CALL


# =============================================================================
# HookEventExpectation Tests
# =============================================================================


class TestHookEventExpectation:
    """Tests for HookEventExpectation."""

    def test_matches_session_start(self, sample_collected_data):
        """Test matching SessionStart event."""
        exp = HookEventExpectation(
            id="exp-001",
            description="Session started",
            event=HookEventType.SESSION_START,
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.PASS
        assert result.actual["event"] == "SessionStart"

    def test_matches_with_filter(self, sample_collected_data):
        """Test matching with field filter."""
        exp = HookEventExpectation(
            id="exp-002",
            description="Specific session",
            event=HookEventType.SESSION_START,
            filters={"session_id": "sess-123"},
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.PASS

    def test_matches_pre_tool_use(self, sample_collected_data):
        """Test matching PreToolUse event."""
        exp = HookEventExpectation(
            id="exp-003",
            description="Bash tool invoked",
            event=HookEventType.PRE_TOOL_USE,
            filters={"tool_name": "Bash"},
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.PASS
        assert result.actual["tool_name"] == "Bash"

    def test_fails_when_event_not_found(self, sample_collected_data):
        """Test failure when event type not found."""
        exp = HookEventExpectation(
            id="exp-004",
            description="Notification event",
            event=HookEventType.NOTIFICATION,
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.FAIL
        assert "No Notification events found" in result.failure_reason

    def test_fails_when_filter_not_matched(self, sample_collected_data):
        """Test failure when filter doesn't match."""
        exp = HookEventExpectation(
            id="exp-005",
            description="Wrong session",
            event=HookEventType.SESSION_START,
            filters={"session_id": "wrong-session"},
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.FAIL
        assert "none matched filters" in result.failure_reason

    def test_fails_on_empty_data(self, empty_collected_data):
        """Test failure with no hook events."""
        exp = HookEventExpectation(
            id="exp-006",
            description="Any session",
            event=HookEventType.SESSION_START,
        )

        result = exp.evaluate(empty_collected_data)

        assert result.status == TestStatus.FAIL

    def test_regex_filter(self, sample_collected_data):
        """Test regex pattern in filter."""
        exp = HookEventExpectation(
            id="exp-007",
            description="Session with pattern",
            event=HookEventType.SESSION_START,
            filters={"session_id": "regex:sess-\\d+"},
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.PASS

    def test_expectation_type(self):
        """Test that expectation type is correct."""
        exp = HookEventExpectation(
            id="exp", description="test", event=HookEventType.SESSION_START
        )
        assert exp.expectation_type == ExpectationType.HOOK_EVENT


# =============================================================================
# SubagentEventExpectation Tests
# =============================================================================


class TestSubagentEventExpectation:
    """Tests for SubagentEventExpectation."""

    def test_matches_subagent_start(self, sample_collected_data):
        """Test matching SubagentStart event."""
        exp = SubagentEventExpectation(
            id="exp-001",
            description="Subagent spawned",
            event="SubagentStart",
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.PASS
        assert result.actual["event"] == "SubagentStart"

    def test_matches_by_agent_type(self, sample_collected_data):
        """Test matching by agent type."""
        exp = SubagentEventExpectation(
            id="exp-002",
            description="Explore subagent",
            event="SubagentStart",
            agent_type="Explore",
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.PASS
        assert result.actual["agent_type"] == "Explore"

    def test_matches_by_agent_id(self, sample_collected_data):
        """Test matching by agent ID."""
        exp = SubagentEventExpectation(
            id="exp-003",
            description="Specific agent",
            event="SubagentStart",
            agent_id="agent-001",
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.PASS
        assert result.actual["agent_id"] == "agent-001"

    def test_matches_subagent_stop(self, sample_collected_data):
        """Test matching SubagentStop event."""
        exp = SubagentEventExpectation(
            id="exp-004",
            description="Subagent completed",
            event="SubagentStop",
            agent_id="agent-001",
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.PASS

    def test_fails_when_type_not_found(self, sample_collected_data):
        """Test failure when agent type not found."""
        exp = SubagentEventExpectation(
            id="exp-005",
            description="Code subagent",
            event="SubagentStart",
            agent_type="Code",
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.FAIL
        assert "none matched criteria" in result.failure_reason

    def test_fails_on_empty_data(self, empty_collected_data):
        """Test failure with no subagents."""
        exp = SubagentEventExpectation(
            id="exp-006",
            description="Any subagent",
            event="SubagentStart",
        )

        result = exp.evaluate(empty_collected_data)

        assert result.status == TestStatus.FAIL
        assert "No subagent events found" in result.failure_reason

    def test_stop_without_timestamp_not_matched(self, sample_collected_data):
        """Test that SubagentStop requires stop_timestamp."""
        # agent-002 has no stop_timestamp
        exp = SubagentEventExpectation(
            id="exp-007",
            description="Task agent stopped",
            event="SubagentStop",
            agent_type="Task",
        )

        result = exp.evaluate(sample_collected_data)

        # Should fail because agent-002 (Task) has no stop_timestamp
        assert result.status == TestStatus.FAIL

    def test_expectation_type(self):
        """Test that expectation type is correct."""
        exp = SubagentEventExpectation(id="exp", description="test", event="SubagentStart")
        assert exp.expectation_type == ExpectationType.SUBAGENT_EVENT


# =============================================================================
# OutputContainsExpectation Tests
# =============================================================================


class TestOutputContainsExpectation:
    """Tests for OutputContainsExpectation."""

    def test_matches_simple_pattern(self, sample_collected_data):
        """Test matching simple text pattern."""
        exp = OutputContainsExpectation(
            id="exp-001",
            description="Report header",
            pattern=r"SC-Startup Report",
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.PASS
        assert "SC-Startup Report" in result.actual["matched_text"]

    def test_matches_case_insensitive(self, sample_collected_data):
        """Test case-insensitive matching."""
        exp = OutputContainsExpectation(
            id="exp-002",
            description="Report header (case insensitive)",
            pattern=r"sc-startup report",
            flags="i",
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.PASS

    def test_matches_with_regex(self, sample_collected_data):
        """Test matching with regex pattern."""
        exp = OutputContainsExpectation(
            id="exp-003",
            description="Status complete",
            pattern=r"Status:\s*\*\*Complete\*\*",
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.PASS

    def test_provides_context(self, sample_collected_data):
        """Test that context is provided around match."""
        exp = OutputContainsExpectation(
            id="exp-004",
            description="Key findings",
            pattern=r"Key Findings",
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.PASS
        assert "context" in result.actual
        # Context should include surrounding text
        assert len(result.actual["context"]) > len("Key Findings")

    def test_fails_when_pattern_not_found(self, sample_collected_data):
        """Test failure when pattern not found."""
        exp = OutputContainsExpectation(
            id="exp-005",
            description="Error message",
            pattern=r"Error:\s+.*failed",
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.FAIL
        assert "not found" in result.failure_reason

    def test_fails_on_empty_responses(self, empty_collected_data):
        """Test failure with no responses."""
        exp = OutputContainsExpectation(
            id="exp-006",
            description="Any content",
            pattern=r".*",
        )

        result = exp.evaluate(empty_collected_data)

        assert result.status == TestStatus.FAIL
        assert "No Claude responses" in result.failure_reason

    def test_multiline_flag(self, sample_collected_data):
        """Test multiline flag."""
        exp = OutputContainsExpectation(
            id="exp-007",
            description="Markdown header at line start",
            pattern=r"^### Key Findings",
            flags="m",
        )

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.PASS

    def test_expectation_type(self):
        """Test that expectation type is correct."""
        exp = OutputContainsExpectation(id="exp", description="test", pattern="test")
        assert exp.expectation_type == ExpectationType.OUTPUT_CONTAINS


# =============================================================================
# NotExpectation Tests
# =============================================================================


class TestNotExpectation:
    """Tests for NotExpectation wrapper."""

    def test_negates_passing_expectation(self, sample_collected_data):
        """Test that passing inner expectation becomes fail."""
        inner = SubagentEventExpectation(
            id="exp-001",
            description="Subagent spawned",
            event="SubagentStart",
        )
        exp = NotExpectation(inner)

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.FAIL
        assert "Expected NOT to find" in result.failure_reason

    def test_negates_failing_expectation(self, sample_collected_data):
        """Test that failing inner expectation becomes pass."""
        inner = SubagentEventExpectation(
            id="exp-002",
            description="Code subagent spawned",
            event="SubagentStart",
            agent_type="Code",  # Not in sample data
        )
        exp = NotExpectation(inner)

        result = exp.evaluate(sample_collected_data)

        assert result.status == TestStatus.PASS
        assert result.actual is None  # Nothing found, which is correct

    def test_preserves_id(self):
        """Test that ID is preserved."""
        inner = ToolCallExpectation(
            id="exp-original",
            description="test",
            tool="Bash",
        )
        exp = NotExpectation(inner)

        assert exp.id == "exp-original"

    def test_modifies_description(self):
        """Test that description is prefixed with NOT."""
        inner = ToolCallExpectation(
            id="exp",
            description="Bash tool used",
            tool="Bash",
        )
        exp = NotExpectation(inner)

        assert "NOT:" in exp.description
        assert "Bash tool used" in exp.description

    def test_no_write_tool_used(self, sample_collected_data):
        """Test asserting no Write tool was used."""
        inner = ToolCallExpectation(
            id="exp-003",
            description="Write tool used",
            tool="Write",
        )
        exp = NotExpectation(inner)

        result = exp.evaluate(sample_collected_data)

        # Write tool was not used, so NOT(Write) should pass
        assert result.status == TestStatus.PASS


# =============================================================================
# ExpectationResult Tests
# =============================================================================


class TestExpectationResult:
    """Tests for ExpectationResult model."""

    def test_to_expectation_model(self):
        """Test conversion to Expectation model."""
        result = ExpectationResult(
            id="exp-001",
            description="Test expectation",
            type=ExpectationType.TOOL_CALL,
            status=TestStatus.PASS,
            expected={"tool": "Bash"},
            actual={"tool": "Bash", "command": "ls"},
            matched_at=ExpectationMatch(
                sequence=1,
                timestamp=datetime(2026, 1, 16, 10, 0, 0),
            ),
        )

        expectation = result.to_expectation_model()

        assert expectation.id == "exp-001"
        assert expectation.status == TestStatus.PASS
        assert expectation.has_details is True

    def test_failing_result(self):
        """Test creating a failing result."""
        result = ExpectationResult(
            id="exp-002",
            description="Missing tool",
            type=ExpectationType.TOOL_CALL,
            status=TestStatus.FAIL,
            expected={"tool": "Write"},
            actual=None,
            failure_reason="No Write tool calls found",
        )

        assert result.status == TestStatus.FAIL
        assert result.actual is None
        assert "Write" in result.failure_reason


# =============================================================================
# Evaluation Functions Tests
# =============================================================================


class TestEvaluateExpectations:
    """Tests for evaluate_expectations function."""

    def test_evaluates_multiple_expectations(self, sample_collected_data):
        """Test evaluating multiple expectations."""
        expectations = [
            ToolCallExpectation(
                id="exp-001",
                description="Bash used",
                tool="Bash",
            ),
            HookEventExpectation(
                id="exp-002",
                description="Session started",
                event=HookEventType.SESSION_START,
            ),
            OutputContainsExpectation(
                id="exp-003",
                description="Report generated",
                pattern=r"SC-Startup Report",
            ),
        ]

        results = evaluate_expectations(expectations, sample_collected_data)

        assert len(results) == 3
        assert all(r.status == TestStatus.PASS for r in results)

    def test_mixed_results(self, sample_collected_data):
        """Test with mixed pass/fail results."""
        expectations = [
            ToolCallExpectation(
                id="exp-001",
                description="Bash used",
                tool="Bash",
            ),
            ToolCallExpectation(
                id="exp-002",
                description="Write used",
                tool="Write",  # Not in sample data
            ),
        ]

        results = evaluate_expectations(expectations, sample_collected_data)

        assert len(results) == 2
        assert results[0].status == TestStatus.PASS
        assert results[1].status == TestStatus.FAIL

    def test_handles_empty_list(self, sample_collected_data):
        """Test with empty expectations list."""
        results = evaluate_expectations([], sample_collected_data)
        assert results == []


class TestComputeOverallStatus:
    """Tests for compute_overall_status function."""

    def test_all_pass(self):
        """Test status when all expectations pass."""
        results = [
            ExpectationResult(
                id="e1",
                description="",
                type=ExpectationType.TOOL_CALL,
                status=TestStatus.PASS,
                expected={},
            ),
            ExpectationResult(
                id="e2",
                description="",
                type=ExpectationType.TOOL_CALL,
                status=TestStatus.PASS,
                expected={},
            ),
        ]

        assert compute_overall_status(results) == TestStatus.PASS

    def test_all_fail(self):
        """Test status when all expectations fail."""
        results = [
            ExpectationResult(
                id="e1",
                description="",
                type=ExpectationType.TOOL_CALL,
                status=TestStatus.FAIL,
                expected={},
            ),
            ExpectationResult(
                id="e2",
                description="",
                type=ExpectationType.TOOL_CALL,
                status=TestStatus.FAIL,
                expected={},
            ),
        ]

        assert compute_overall_status(results) == TestStatus.FAIL

    def test_partial(self):
        """Test status when some pass, some fail."""
        results = [
            ExpectationResult(
                id="e1",
                description="",
                type=ExpectationType.TOOL_CALL,
                status=TestStatus.PASS,
                expected={},
            ),
            ExpectationResult(
                id="e2",
                description="",
                type=ExpectationType.TOOL_CALL,
                status=TestStatus.FAIL,
                expected={},
            ),
        ]

        assert compute_overall_status(results) == TestStatus.PARTIAL

    def test_empty_list(self):
        """Test status with no expectations (vacuously true)."""
        assert compute_overall_status([]) == TestStatus.PASS


class TestComputePassRate:
    """Tests for compute_pass_rate function."""

    def test_all_pass(self):
        """Test pass rate when all pass."""
        results = [
            ExpectationResult(
                id="e1",
                description="",
                type=ExpectationType.TOOL_CALL,
                status=TestStatus.PASS,
                expected={},
            ),
            ExpectationResult(
                id="e2",
                description="",
                type=ExpectationType.TOOL_CALL,
                status=TestStatus.PASS,
                expected={},
            ),
        ]

        assert compute_pass_rate(results) == "2/2"

    def test_some_pass(self):
        """Test pass rate with partial pass."""
        results = [
            ExpectationResult(
                id="e1",
                description="",
                type=ExpectationType.TOOL_CALL,
                status=TestStatus.PASS,
                expected={},
            ),
            ExpectationResult(
                id="e2",
                description="",
                type=ExpectationType.TOOL_CALL,
                status=TestStatus.FAIL,
                expected={},
            ),
            ExpectationResult(
                id="e3",
                description="",
                type=ExpectationType.TOOL_CALL,
                status=TestStatus.PASS,
                expected={},
            ),
        ]

        assert compute_pass_rate(results) == "2/3"

    def test_none_pass(self):
        """Test pass rate when none pass."""
        results = [
            ExpectationResult(
                id="e1",
                description="",
                type=ExpectationType.TOOL_CALL,
                status=TestStatus.FAIL,
                expected={},
            ),
        ]

        assert compute_pass_rate(results) == "0/1"

    def test_empty_list(self):
        """Test pass rate with no expectations."""
        assert compute_pass_rate([]) == "0/0"


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests combining multiple expectation types."""

    def test_realistic_test_scenario(self, sample_collected_data):
        """Test a realistic test scenario with multiple expectations."""
        expectations = [
            # Should pass: Bash tool was used
            ToolCallExpectation(
                id="exp-001",
                description="Load configuration file",
                tool="Bash",
                pattern=r"cat.*sc-startup\.yaml",
            ),
            # Should pass: Session started
            HookEventExpectation(
                id="exp-002",
                description="Session started",
                event=HookEventType.SESSION_START,
            ),
            # Should pass: Report was generated
            OutputContainsExpectation(
                id="exp-003",
                description="Report generated",
                pattern=r"SC-Startup Report",
                flags="i",
            ),
            # Should pass: Subagent was NOT Code type (using NotExpectation)
            NotExpectation(
                SubagentEventExpectation(
                    id="exp-004",
                    description="Code subagent NOT used",
                    event="SubagentStart",
                    agent_type="Code",
                )
            ),
            # Should fail: Write tool was not used
            ToolCallExpectation(
                id="exp-005",
                description="Write output file",
                tool="Write",
            ),
        ]

        results = evaluate_expectations(expectations, sample_collected_data)

        assert len(results) == 5
        assert results[0].status == TestStatus.PASS  # Config loaded
        assert results[1].status == TestStatus.PASS  # Session started
        assert results[2].status == TestStatus.PASS  # Report generated
        assert results[3].status == TestStatus.PASS  # No Code subagent
        assert results[4].status == TestStatus.FAIL  # No Write tool

        assert compute_overall_status(results) == TestStatus.PARTIAL
        assert compute_pass_rate(results) == "4/5"

    def test_all_expectations_pass(self, sample_collected_data):
        """Test scenario where all expectations pass."""
        expectations = [
            ToolCallExpectation(
                id="exp-001",
                description="Bash used",
                tool="Bash",
            ),
            ToolCallExpectation(
                id="exp-002",
                description="Read used",
                tool="Read",
            ),
            ToolCallExpectation(
                id="exp-003",
                description="Skill invoked",
                tool="Skill",
            ),
            HookEventExpectation(
                id="exp-004",
                description="Session started",
                event=HookEventType.SESSION_START,
            ),
            SubagentEventExpectation(
                id="exp-005",
                description="Explore subagent",
                event="SubagentStart",
                agent_type="Explore",
            ),
            OutputContainsExpectation(
                id="exp-006",
                description="Complete status",
                pattern=r"Complete",
            ),
        ]

        results = evaluate_expectations(expectations, sample_collected_data)

        assert all(r.status == TestStatus.PASS for r in results)
        assert compute_overall_status(results) == TestStatus.PASS
        assert compute_pass_rate(results) == "6/6"
