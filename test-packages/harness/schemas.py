"""Pydantic schemas for test harness JSON structures.

This module defines validation schemas for all JSON files produced and consumed
by the test harness:

- EnrichedData: Strict validation for *-enriched.json files (our generated data)
- ClaudeTranscriptEntry: Lenient validation for *-transcript.jsonl (Claude's output)
- HookEvent: Lenient validation for *-trace.jsonl (hook events)

Claude schemas use `model_config = {"extra": "allow"}` to handle future Claude
upgrades gracefully. Runtime uses best-effort parsing; test suite validates
schema compliance.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


# =============================================================================
# Test Context and Artifacts (strict validation - our generated data)
# =============================================================================


class TestContextPaths(BaseModel):
    """Source file paths for test traceability."""

    fixture_yaml: str
    test_yaml: str
    skill_md: Optional[str] = None
    agent_md: Optional[str] = None


class TestContext(BaseModel):
    """Test identification metadata."""

    fixture_id: str
    test_id: str
    test_name: str
    package: str
    paths: TestContextPaths


class ArtifactPaths(BaseModel):
    """Test output file paths (relative to reports directory)."""

    transcript: str
    trace: str
    enriched: str
    claude_cli: Optional[str] = None
    pytest_output: Optional[str] = None


# =============================================================================
# Timeline Tree Nodes (strict validation - our generated data)
# =============================================================================


class TimelineNodeType(str, Enum):
    """Types of nodes in the timeline tree."""

    ROOT = "root"
    PROMPT = "prompt"
    RESPONSE = "response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SUBAGENT_START = "subagent_start"
    SUBAGENT_STOP = "subagent_stop"


class TreeNode(BaseModel):
    """A node in the timeline tree (structure only, no content)."""

    parent_uuid: Optional[str] = None
    depth: int = 0
    node_type: TimelineNodeType
    agent_id: Optional[str] = None
    agent_type: Optional[str] = None
    tool_name: Optional[str] = None
    children: List[str] = Field(default_factory=list)  # List of child UUIDs


class AgentSummary(BaseModel):
    """Summary information for a subagent."""

    agent_type: str
    start_uuid: Optional[str] = None
    stop_uuid: Optional[str] = None
    tool_count: int = 0



class TokenUsage(BaseModel):
    """Token usage metrics aggregated from transcript entries."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    subagent_tokens: int = 0

    @property
    def total_billable(self) -> int:
        """Tokens likely billed (excludes cache reads)."""
        return self.input_tokens + self.output_tokens + self.cache_creation_tokens

    @property
    def total_all(self) -> int:
        """Total tokens including cache reads."""
        return self.total_billable + self.cache_read_tokens + self.subagent_tokens

class TreeStats(BaseModel):
    """Quick-access metrics for the timeline tree."""

    total_nodes: int = 0
    max_depth: int = 0
    agent_count: int = 0
    tool_call_count: int = 0
    token_usage: Optional[TokenUsage] = None


class TimelineTree(BaseModel):
    """Hierarchical structure of the timeline."""

    root_uuid: str
    nodes: Dict[str, TreeNode]


class EnrichedData(BaseModel):
    """Schema for *-enriched.json files.

    This is the primary schema for our generated enrichment data.
    Uses strict validation since we control the output format.
    """

    test_context: TestContext
    artifacts: ArtifactPaths
    tree: TimelineTree
    agents: Dict[str, AgentSummary] = Field(default_factory=dict)
    stats: TreeStats = Field(default_factory=TreeStats)


# =============================================================================
# Claude Transcript Schema (lenient validation for runtime)
# =============================================================================


class ClaudeTranscriptEntry(BaseModel):
    """Schema for Claude session transcript entries.

    Note: This schema should be lenient at runtime to handle Claude upgrades.
    Test failures on schema mismatch are acceptable, but runtime should
    make best effort and not fail-fast if Claude schema changes.

    The transcript contains messages from the Claude conversation session,
    including prompts, responses, tool calls, and tool results.
    """

    model_config = {"extra": "allow"}  # Allow extra fields from Claude

    uuid: Optional[str] = None
    parentUuid: Optional[str] = None
    isSidechain: Optional[bool] = None
    type: Optional[str] = None
    timestamp: Optional[str] = None
    sessionId: Optional[str] = None
    toolUseID: Optional[str] = None
    parentToolUseID: Optional[str] = None
    # Content varies by type - keep flexible
    message: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None


# =============================================================================
# Hook Trace Event Schema (lenient validation for runtime)
# =============================================================================


class HookEventType(str, Enum):
    """Types of hook events captured during test execution."""

    SESSION_START = "SessionStart"
    SESSION_END = "SessionEnd"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    SUBAGENT_START = "SubagentStart"
    SUBAGENT_STOP = "SubagentStop"
    STOP = "Stop"


class HookEvent(BaseModel):
    """Schema for hook trace events.

    Hook events are captured by test instrumentation and provide information
    about tool usage, subagent lifecycle, and session boundaries.

    Uses lenient validation to handle potential changes in hook output format.
    """

    model_config = {"extra": "allow"}

    ts: str
    event: HookEventType
    cwd: Optional[str] = None
    pid: Optional[int] = None
    ppid: Optional[int] = None
    session_id: Optional[str] = None
    tool_use_id: Optional[str] = None
    agent_id: Optional[str] = None
    agent_type: Optional[str] = None
    # Input/output varies by event type
    stdin: Optional[Dict[str, Any]] = None
