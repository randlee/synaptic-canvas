from __future__ import annotations

from datetime import datetime

from harness.collector import CollectedData, CorrelatedToolCall, SubagentLifecycle
from harness.models import ExpectationType, TestStatus
from harness.reporter import ExpectationEvaluator


def _sample_data() -> CollectedData:
    now = datetime.now()
    data = CollectedData(
        tool_calls=[
            CorrelatedToolCall(
                tool_use_id="tool-1",
                tool_name="Agent",
                tool_input={
                    "description": "Find YAML files",
                    "prompt": "Find all YAML files in this repository",
                    "subagent_type": "Explore",
                },
                pre_timestamp=now,
                post_timestamp=now,
            ),
            CorrelatedToolCall(
                tool_use_id="tool-2",
                tool_name="Skill",
                tool_input={"skill": "sc-github-issue", "args": "list"},
                pre_timestamp=now,
                post_timestamp=now,
            ),
        ],
        raw_hook_events=[
            {"event": "PreToolUse", "tool_name": "Agent"},
            {"event": "SubagentStart", "agent_id": "agent-1", "agent_type": "Explore"},
            {"event": "SubagentStop", "agent_id": "agent-1", "agent_type": "Explore"},
        ],
        subagents=[
            SubagentLifecycle(
                agent_id="agent-1",
                agent_type="Explore",
                start_timestamp=now,
                stop_timestamp=now,
            )
        ],
    )
    data.execution_params = {"model": "haiku", "timeout_ms": 60000}
    return data


def test_tool_call_respects_regex_flags() -> None:
    evaluator = ExpectationEvaluator(_sample_data())
    result = evaluator.evaluate(
        expectation_id="exp-001",
        expectation_type=ExpectationType.TOOL_CALL,
        description="Agent call matches case-insensitively",
        expected={"tool": "Agent", "pattern": "find all yaml files", "flags": "i"},
    )
    assert result.status == TestStatus.PASS


def test_hook_event_uses_inline_filters_and_has_field() -> None:
    evaluator = ExpectationEvaluator(_sample_data())
    result = evaluator.evaluate(
        expectation_id="exp-002",
        expectation_type=ExpectationType.HOOK_EVENT,
        description="Subagent start includes agent_type",
        expected={"event": "SubagentStart", "agent_type": "Explore", "has_field": "agent_id"},
    )
    assert result.status == TestStatus.PASS


def test_tool_not_called_passes_when_tool_absent() -> None:
    evaluator = ExpectationEvaluator(_sample_data())
    result = evaluator.evaluate(
        expectation_id="exp-003",
        expectation_type=ExpectationType.TOOL_NOT_CALLED,
        description="Task tool was not used",
        expected={"tool": "Task"},
    )
    assert result.status == TestStatus.PASS


def test_subagent_lifecycle_passes_for_start_and_stop_pair() -> None:
    evaluator = ExpectationEvaluator(_sample_data())
    result = evaluator.evaluate(
        expectation_id="exp-004",
        expectation_type=ExpectationType.SUBAGENT_LIFECYCLE,
        description="Subagent start/stop share agent_id",
        expected={"events": ["SubagentStart", "SubagentStop"], "correlation": "agent_id"},
    )
    assert result.status == TestStatus.PASS


def test_execution_param_matches_test_configuration() -> None:
    evaluator = ExpectationEvaluator(_sample_data())
    result = evaluator.evaluate(
        expectation_id="exp-005",
        expectation_type=ExpectationType.EXECUTION_PARAM,
        description="Execution uses haiku model",
        expected={"param": "model", "value": "haiku"},
    )
    assert result.status == TestStatus.PASS
