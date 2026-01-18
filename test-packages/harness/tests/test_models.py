"""
Unit tests for harness.models module.

Tests the Pydantic models for the v3.0 report schema including:
- Model instantiation and validation
- Status computation
- JSON serialization/deserialization
- Enum handling
"""

from datetime import datetime

import pytest

from harness.models import (
    ClaudeResponse,
    DebugInfo,
    ExecutionSection,
    Expectation,
    ExpectationMatch,
    ExpectationType,
    FixtureMeta,
    FixtureReport,
    FixtureSummary,
    GitState,
    HookEventType,
    PostToolUseEvent,
    PreToolUseEvent,
    ReproduceSection,
    SessionStartEvent,
    SideEffects,
    StatusIcon,
    TestMetadata,
    TestResult,
    TestStatus,
    TimelineEntry,
    TimelineEntryType,
    TokenUsage,
    ToolInput,
    ToolOutput,
    UserPromptSubmitEvent,
)


class TestEnums:
    """Tests for enum definitions."""

    def test_test_status_values(self):
        """Test TestStatus enum has expected values."""
        assert TestStatus.PASS.value == "pass"
        assert TestStatus.FAIL.value == "fail"
        assert TestStatus.PARTIAL.value == "partial"
        assert TestStatus.SKIPPED.value == "skipped"

    def test_status_icon_values(self):
        """Test StatusIcon enum has expected values."""
        assert StatusIcon.PASS.value == "pass"
        assert StatusIcon.FAIL.value == "fail"
        assert StatusIcon.WARNING.value == "warning"
        assert StatusIcon.SKIPPED.value == "skipped"

    def test_expectation_type_values(self):
        """Test ExpectationType enum has expected values."""
        assert ExpectationType.TOOL_CALL.value == "tool_call"
        assert ExpectationType.HOOK_EVENT.value == "hook_event"
        assert ExpectationType.SUBAGENT_EVENT.value == "subagent_event"
        assert ExpectationType.OUTPUT_CONTAINS.value == "output_contains"
        assert ExpectationType.FILE_CREATED.value == "file_created"

    def test_timeline_entry_type_values(self):
        """Test TimelineEntryType enum has expected values."""
        assert TimelineEntryType.PROMPT.value == "prompt"
        assert TimelineEntryType.TOOL_CALL.value == "tool_call"
        assert TimelineEntryType.RESPONSE.value == "response"

    def test_hook_event_type_values(self):
        """Test HookEventType enum has expected values."""
        assert HookEventType.SESSION_START.value == "SessionStart"
        assert HookEventType.PRE_TOOL_USE.value == "PreToolUse"
        assert HookEventType.POST_TOOL_USE.value == "PostToolUse"


class TestFixtureSummary:
    """Tests for FixtureSummary model."""

    def test_create_summary(self):
        """Test creating a fixture summary."""
        summary = FixtureSummary(
            total_tests=10,
            passed=7,
            failed=2,
            partial=1,
            skipped=0,
        )
        assert summary.total_tests == 10
        assert summary.passed == 7
        assert summary.failed == 2

    def test_summary_validation_ge_zero(self):
        """Test that summary values must be >= 0."""
        with pytest.raises(ValueError):
            FixtureSummary(
                total_tests=-1,
                passed=0,
                failed=0,
                partial=0,
                skipped=0,
            )


class TestGitState:
    """Tests for GitState model."""

    def test_create_git_state(self):
        """Test creating git state."""
        git = GitState(
            branch="develop",
            commit="abc123",
            modified_files=["file1.py", "file2.py"],
        )
        assert git.branch == "develop"
        assert git.commit == "abc123"
        assert len(git.modified_files) == 2

    def test_empty_modified_files(self):
        """Test git state with no modified files."""
        git = GitState(branch="main", commit="def456")
        assert git.modified_files == []


class TestTokenUsage:
    """Tests for TokenUsage model."""

    def test_create_token_usage(self):
        """Test creating token usage."""
        tokens = TokenUsage(input=1000, output=500, total=1500)
        assert tokens.input == 1000
        assert tokens.output == 500
        assert tokens.total == 1500

    def test_token_usage_validation(self):
        """Test that token counts must be >= 0."""
        with pytest.raises(ValueError):
            TokenUsage(input=-1, output=0, total=0)


class TestToolInput:
    """Tests for ToolInput model."""

    def test_bash_tool_input(self):
        """Test creating Bash tool input."""
        input = ToolInput(
            command="ls -la",
            description="List files",
        )
        assert input.command == "ls -la"
        assert input.description == "List files"

    def test_read_tool_input(self):
        """Test creating Read tool input."""
        input = ToolInput(file_path="/path/to/file.py")
        assert input.file_path == "/path/to/file.py"

    def test_skill_tool_input(self):
        """Test creating Skill tool input."""
        input = ToolInput(skill="sc-startup", args="--readonly")
        assert input.skill == "sc-startup"
        assert input.args == "--readonly"


class TestToolOutput:
    """Tests for ToolOutput model."""

    def test_bash_tool_output(self):
        """Test creating Bash tool output."""
        output = ToolOutput(
            stdout="file1.py\nfile2.py",
            stderr="",
            exit_code=0,
        )
        assert output.stdout == "file1.py\nfile2.py"
        assert output.exit_code == 0
        assert output.is_error is False

    def test_error_tool_output(self):
        """Test creating error tool output."""
        output = ToolOutput(
            stderr="File not found",
            exit_code=1,
            is_error=True,
        )
        assert output.is_error is True
        assert output.exit_code == 1

    def test_content_as_string(self):
        """Test ToolOutput with content as a plain string."""
        output = ToolOutput(content="This is the file content")
        assert output.content == "This is the file content"

    def test_content_as_list_single_text_block(self):
        """Test ToolOutput with content as a list with single text block."""
        content_blocks = [{"type": "text", "text": "Single text block"}]
        output = ToolOutput(content=content_blocks)
        assert output.content == "Single text block"

    def test_content_as_list_multiple_text_blocks(self):
        """Test ToolOutput with content as a list with multiple text blocks."""
        content_blocks = [
            {"type": "text", "text": "First block."},
            {"type": "text", "text": " Second block."},
            {"type": "text", "text": " Third block."},
        ]
        output = ToolOutput(content=content_blocks)
        assert output.content == "First block. Second block. Third block."

    def test_content_as_list_mixed_types(self):
        """Test ToolOutput with content list containing non-text types (ignored)."""
        content_blocks = [
            {"type": "text", "text": "Text content"},
            {"type": "image", "data": "base64data"},  # Non-text block
            {"type": "text", "text": " More text"},
        ]
        output = ToolOutput(content=content_blocks)
        assert output.content == "Text content More text"

    def test_content_as_list_empty_list(self):
        """Test ToolOutput with empty content list."""
        output = ToolOutput(content=[])
        assert output.content == ""

    def test_content_as_none(self):
        """Test ToolOutput with None content."""
        output = ToolOutput(content=None)
        assert output.content is None

    def test_content_claude_api_format(self):
        """Test ToolOutput with exact Claude API response format from error message."""
        # This is the exact format from the error message
        content_blocks = [
            {"type": "text", "text": "Found a total of **518 files**."}
        ]
        output = ToolOutput(content=content_blocks)
        assert output.content == "Found a total of **518 files**."


class TestExpectation:
    """Tests for Expectation model."""

    def test_passing_expectation(self):
        """Test creating a passing expectation."""
        exp = Expectation(
            id="exp-001",
            description="Tool was called",
            type=ExpectationType.TOOL_CALL,
            status=TestStatus.PASS,
            expected={"tool": "Bash", "pattern": "ls.*"},
            actual={"tool": "Bash", "command": "ls -la"},
            matched_at=ExpectationMatch(
                sequence=1,
                timestamp=datetime.now(),
            ),
        )
        assert exp.status == TestStatus.PASS
        assert exp.failure_reason is None

    def test_failing_expectation(self):
        """Test creating a failing expectation."""
        exp = Expectation(
            id="exp-002",
            description="Expected subagent",
            type=ExpectationType.SUBAGENT_EVENT,
            status=TestStatus.FAIL,
            expected={"event": "SubagentStart"},
            actual=None,
            failure_reason="No SubagentStart event found",
        )
        assert exp.status == TestStatus.FAIL
        assert exp.actual is None
        assert "SubagentStart" in exp.failure_reason


class TestTimelineEntry:
    """Tests for TimelineEntry model."""

    def test_prompt_entry(self):
        """Test creating a prompt timeline entry."""
        entry = TimelineEntry(
            seq=1,
            type=TimelineEntryType.PROMPT,
            timestamp=datetime.now(),
            elapsed_ms=0,
            content="/sc-startup --readonly",
        )
        assert entry.seq == 1
        assert entry.type == TimelineEntryType.PROMPT
        assert entry.content == "/sc-startup --readonly"

    def test_tool_call_entry(self):
        """Test creating a tool call timeline entry."""
        entry = TimelineEntry(
            seq=2,
            type=TimelineEntryType.TOOL_CALL,
            timestamp=datetime.now(),
            elapsed_ms=100,
            tool="Bash",
            input=ToolInput(command="ls"),
            output=ToolOutput(stdout="files"),
            duration_ms=50,
            intent="List files",
        )
        assert entry.tool == "Bash"
        assert entry.duration_ms == 50
        assert entry.intent == "List files"

    def test_response_entry(self):
        """Test creating a response timeline entry."""
        entry = TimelineEntry(
            seq=3,
            type=TimelineEntryType.RESPONSE,
            timestamp=datetime.now(),
            elapsed_ms=500,
            content="Here are the files...",
            content_preview="Here are the files...",
            content_length=21,
        )
        assert entry.type == TimelineEntryType.RESPONSE


class TestTestResult:
    """Tests for TestResult model."""

    @pytest.fixture
    def sample_test_result(self):
        """Create a sample test result for testing."""
        return TestResult(
            test_id="test-001",
            test_name="Sample Test",
            tab_label="Sample",
            description="A sample test",
            timestamp=datetime.now(),
            duration_ms=1000,
            status=TestStatus.PASS,
            status_icon=StatusIcon.PASS,
            pass_rate="2/2",
            tags=["sample"],
            metadata=TestMetadata(
                fixture="sample_fixture",
                package="sample-package",
                model="haiku",
                session_id="session-123",
                test_repo="/path/to/repo",
            ),
            reproduce=ReproduceSection(
                test_command='claude -p "test"',
            ),
            execution=ExecutionSection(
                prompt="test prompt",
                model="haiku",
                tools_allowed=["Bash"],
            ),
            expectations=[
                Expectation(
                    id="exp-001",
                    description="Pass",
                    type=ExpectationType.TOOL_CALL,
                    status=TestStatus.PASS,
                    expected={"tool": "Bash"},
                ),
                Expectation(
                    id="exp-002",
                    description="Also pass",
                    type=ExpectationType.OUTPUT_CONTAINS,
                    status=TestStatus.PASS,
                    expected={"pattern": "success"},
                ),
            ],
            timeline=[],
            side_effects=SideEffects(),
            claude_response=ClaudeResponse(
                preview="Success",
                full_text="Success",
                word_count=1,
            ),
            debug=DebugInfo(),
        )

    def test_compute_status_all_pass(self, sample_test_result):
        """Test status computation when all expectations pass."""
        assert sample_test_result.compute_status() == TestStatus.PASS

    def test_compute_status_all_fail(self):
        """Test status computation when all expectations fail."""
        result = TestResult(
            test_id="test-002",
            test_name="Fail Test",
            tab_label="Fail",
            description="",
            timestamp=datetime.now(),
            duration_ms=100,
            status=TestStatus.FAIL,
            status_icon=StatusIcon.FAIL,
            pass_rate="0/2",
            metadata=TestMetadata(
                fixture="f", package="p", model="haiku", test_repo="/r"
            ),
            reproduce=ReproduceSection(test_command=""),
            execution=ExecutionSection(prompt="", model="haiku"),
            expectations=[
                Expectation(
                    id="e1",
                    description="",
                    type=ExpectationType.TOOL_CALL,
                    status=TestStatus.FAIL,
                    expected={},
                ),
                Expectation(
                    id="e2",
                    description="",
                    type=ExpectationType.TOOL_CALL,
                    status=TestStatus.FAIL,
                    expected={},
                ),
            ],
            claude_response=ClaudeResponse(preview="", full_text="", word_count=0),
        )
        assert result.compute_status() == TestStatus.FAIL

    def test_compute_status_partial(self):
        """Test status computation when some expectations pass."""
        result = TestResult(
            test_id="test-003",
            test_name="Partial Test",
            tab_label="Partial",
            description="",
            timestamp=datetime.now(),
            duration_ms=100,
            status=TestStatus.PARTIAL,
            status_icon=StatusIcon.WARNING,
            pass_rate="1/2",
            metadata=TestMetadata(
                fixture="f", package="p", model="haiku", test_repo="/r"
            ),
            reproduce=ReproduceSection(test_command=""),
            execution=ExecutionSection(prompt="", model="haiku"),
            expectations=[
                Expectation(
                    id="e1",
                    description="",
                    type=ExpectationType.TOOL_CALL,
                    status=TestStatus.PASS,
                    expected={},
                ),
                Expectation(
                    id="e2",
                    description="",
                    type=ExpectationType.TOOL_CALL,
                    status=TestStatus.FAIL,
                    expected={},
                ),
            ],
            claude_response=ClaudeResponse(preview="", full_text="", word_count=0),
        )
        assert result.compute_status() == TestStatus.PARTIAL

    def test_compute_status_no_expectations(self):
        """Test status computation with no expectations."""
        result = TestResult(
            test_id="test-004",
            test_name="No Exp Test",
            tab_label="NoExp",
            description="",
            timestamp=datetime.now(),
            duration_ms=100,
            status=TestStatus.PASS,
            status_icon=StatusIcon.PASS,
            pass_rate="0/0",
            metadata=TestMetadata(
                fixture="f", package="p", model="haiku", test_repo="/r"
            ),
            reproduce=ReproduceSection(test_command=""),
            execution=ExecutionSection(prompt="", model="haiku"),
            expectations=[],
            claude_response=ClaudeResponse(preview="", full_text="", word_count=0),
        )
        assert result.compute_status() == TestStatus.PASS

    def test_compute_pass_rate(self, sample_test_result):
        """Test pass rate computation."""
        assert sample_test_result.compute_pass_rate() == "2/2"

    def test_json_serialization(self, sample_test_result):
        """Test JSON serialization roundtrip."""
        json_str = sample_test_result.model_dump_json()
        assert "test-001" in json_str
        assert "Sample Test" in json_str


class TestFixtureReport:
    """Tests for FixtureReport model."""

    def test_create_fixture_report(self):
        """Test creating a fixture report."""
        report = FixtureReport(
            fixture=FixtureMeta(
                fixture_id="test_fixture",
                fixture_name="Test Fixture",
                package="test-package",
                agent_or_skill="test-skill",
                report_path="/path/to/report.json",
                generated_at=datetime.now(),
                summary=FixtureSummary(
                    total_tests=2,
                    passed=1,
                    failed=1,
                    partial=0,
                    skipped=0,
                ),
            ),
            tests=[],
        )
        assert report.schema_version == "3.0"
        assert report.fixture.fixture_id == "test_fixture"

    def test_compute_summary(self):
        """Test summary computation from test results."""
        # Create minimal test results
        pass_result = TestResult(
            test_id="t1",
            test_name="Pass",
            tab_label="P",
            description="",
            timestamp=datetime.now(),
            duration_ms=0,
            status=TestStatus.PASS,
            status_icon=StatusIcon.PASS,
            pass_rate="0/0",
            metadata=TestMetadata(
                fixture="f", package="p", model="haiku", test_repo="/r"
            ),
            reproduce=ReproduceSection(test_command=""),
            execution=ExecutionSection(prompt="", model="haiku"),
            claude_response=ClaudeResponse(preview="", full_text="", word_count=0),
        )
        fail_result = TestResult(
            test_id="t2",
            test_name="Fail",
            tab_label="F",
            description="",
            timestamp=datetime.now(),
            duration_ms=0,
            status=TestStatus.FAIL,
            status_icon=StatusIcon.FAIL,
            pass_rate="0/0",
            metadata=TestMetadata(
                fixture="f", package="p", model="haiku", test_repo="/r"
            ),
            reproduce=ReproduceSection(test_command=""),
            execution=ExecutionSection(prompt="", model="haiku"),
            claude_response=ClaudeResponse(preview="", full_text="", word_count=0),
        )

        report = FixtureReport(
            fixture=FixtureMeta(
                fixture_id="f",
                fixture_name="F",
                package="p",
                agent_or_skill="a",
                report_path="/r",
                generated_at=datetime.now(),
                summary=FixtureSummary(
                    total_tests=0, passed=0, failed=0, partial=0, skipped=0
                ),
            ),
            tests=[pass_result, fail_result],
        )

        summary = report.compute_summary()
        assert summary.total_tests == 2
        assert summary.passed == 1
        assert summary.failed == 1


class TestHookEventModels:
    """Tests for hook event models."""

    def test_session_start_event(self):
        """Test SessionStartEvent model."""
        event = SessionStartEvent(
            ts=datetime.now(),
            event=HookEventType.SESSION_START,
            session_id="session-123",
            transcript_path="/path/to/transcript.jsonl",
            cwd="/path/to/project",
            source="startup",
        )
        assert event.session_id == "session-123"
        assert event.source == "startup"

    def test_pre_tool_use_event(self):
        """Test PreToolUseEvent model."""
        event = PreToolUseEvent(
            ts=datetime.now(),
            event=HookEventType.PRE_TOOL_USE,
            session_id="session-123",
            tool_name="Bash",
            tool_input={"command": "ls"},
            tool_use_id="toolu_123",
        )
        assert event.tool_name == "Bash"
        assert event.tool_use_id == "toolu_123"

    def test_post_tool_use_event(self):
        """Test PostToolUseEvent model."""
        event = PostToolUseEvent(
            ts=datetime.now(),
            event=HookEventType.POST_TOOL_USE,
            session_id="session-123",
            tool_name="Bash",
            tool_input={"command": "ls"},
            tool_response={"stdout": "file.txt"},
            tool_use_id="toolu_123",
        )
        assert event.tool_response["stdout"] == "file.txt"

    def test_user_prompt_submit_event(self):
        """Test UserPromptSubmitEvent model."""
        event = UserPromptSubmitEvent(
            ts=datetime.now(),
            event=HookEventType.USER_PROMPT_SUBMIT,
            session_id="session-123",
            prompt="list files",
        )
        assert event.prompt == "list files"
