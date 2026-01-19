"""
Unit tests for harness.enrichment module.

Tests the enrichment functionality including:
- Timeline tree building from transcript entries
- parentUuid chain resolution
- Agent correlation via tool_use_id
- Tree stats calculation
- Orphan handling
- Edge cases
- Result pattern (Success/Failure with warnings)
"""

import pytest

from harness.enrichment import (
    build_timeline_tree,
    _classify_node_type,
    _build_tool_to_agent_map,
    _compute_tree_stats,
)
from harness.result import Success, Failure, EnrichmentError
from harness.schemas import (
    TestContext,
    TestContextPaths,
    ArtifactPaths,
    TimelineNodeType,
    EnrichedData,
    TreeNode,
    AgentSummary,
    TreeStats,
)


# =============================================================================
# Test Fixtures
# =============================================================================


# Sample transcript with parentUuid chains
SAMPLE_TRANSCRIPT = [
    {
        "uuid": "uuid-1",
        "parentUuid": None,
        "type": "user",
        "message": {"role": "user", "content": "Hello"},
    },
    {
        "uuid": "uuid-2",
        "parentUuid": "uuid-1",
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [{"type": "text", "text": "Hi there!"}],
        },
    },
    {
        "uuid": "uuid-3",
        "parentUuid": "uuid-2",
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "toolu_01ABC", "name": "Read", "input": {}}
            ],
        },
    },
    {
        "uuid": "uuid-4",
        "parentUuid": "uuid-3",
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_01ABC",
                    "content": "file contents",
                }
            ],
        },
    },
]


# Sample trace with agent correlation
SAMPLE_TRACE = [
    {
        "ts": "2026-01-16T12:00:00.000Z",
        "event": "SessionStart",
        "session_id": "test-123",
    },
    {
        "ts": "2026-01-16T12:00:01.000Z",
        "event": "SubagentStart",
        "agent_id": "a123",
        "agent_type": "Explore",
    },
    {
        "ts": "2026-01-16T12:00:02.000Z",
        "event": "PreToolUse",
        "tool_use_id": "toolu_01ABC",
        "tool_name": "Read",
    },
    {
        "ts": "2026-01-16T12:00:03.000Z",
        "event": "PostToolUse",
        "tool_use_id": "toolu_01ABC",
    },
    {
        "ts": "2026-01-16T12:00:04.000Z",
        "event": "SubagentStop",
        "agent_id": "a123",
    },
]


# Deeply nested transcript for depth testing
# Note: Don't use "root" as a UUID - it conflicts with the synthetic root node
DEEP_NESTED_TRANSCRIPT = [
    {"uuid": "entry-0", "parentUuid": None, "type": "user", "message": {"content": "Start"}},
    {"uuid": "entry-1", "parentUuid": "entry-0", "type": "assistant", "message": {"content": []}},
    {"uuid": "entry-2", "parentUuid": "entry-1", "type": "assistant", "message": {"content": []}},
    {"uuid": "entry-3", "parentUuid": "entry-2", "type": "assistant", "message": {"content": []}},
    {"uuid": "entry-4", "parentUuid": "entry-3", "type": "assistant", "message": {"content": []}},
    {"uuid": "entry-5", "parentUuid": "entry-4", "type": "assistant", "message": {"content": []}},
]


# Transcript with multiple tool calls for stats testing
MULTI_TOOL_TRANSCRIPT = [
    {"uuid": "u1", "parentUuid": None, "type": "user", "message": {"content": "Run commands"}},
    {
        "uuid": "a1",
        "parentUuid": "u1",
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Bash"}]},
    },
    {
        "uuid": "r1",
        "parentUuid": "a1",
        "type": "user",
        "message": {"content": [{"type": "tool_result", "tool_use_id": "t1"}]},
    },
    {
        "uuid": "a2",
        "parentUuid": "r1",
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "id": "t2", "name": "Read"}]},
    },
    {
        "uuid": "r2",
        "parentUuid": "a2",
        "type": "user",
        "message": {"content": [{"type": "tool_result", "tool_use_id": "t2"}]},
    },
    {
        "uuid": "a3",
        "parentUuid": "r2",
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "id": "t3", "name": "Write"}]},
    },
    {
        "uuid": "r3",
        "parentUuid": "a3",
        "type": "user",
        "message": {"content": [{"type": "tool_result", "tool_use_id": "t3"}]},
    },
]


# Transcript with orphaned entries (missing parentUuid)
ORPHAN_TRANSCRIPT = [
    {"uuid": "orphan-1", "parentUuid": None, "type": "user", "message": {"content": "First message"}},
    {"uuid": "orphan-2", "parentUuid": None, "type": "user", "message": {"content": "Second message"}},
    {"uuid": "child-1", "parentUuid": "orphan-1", "type": "assistant", "message": {"content": []}},
]


# Trace with multiple agents
MULTI_AGENT_TRACE = [
    {"ts": "2026-01-16T12:00:00.000Z", "event": "SessionStart", "session_id": "test-456"},
    {"ts": "2026-01-16T12:00:01.000Z", "event": "SubagentStart", "agent_id": "agent-1", "agent_type": "Explore"},
    {"ts": "2026-01-16T12:00:02.000Z", "event": "PreToolUse", "tool_use_id": "t1", "tool_name": "Bash"},
    {"ts": "2026-01-16T12:00:03.000Z", "event": "PostToolUse", "tool_use_id": "t1"},
    {"ts": "2026-01-16T12:00:04.000Z", "event": "SubagentStop", "agent_id": "agent-1"},
    {"ts": "2026-01-16T12:00:05.000Z", "event": "SubagentStart", "agent_id": "agent-2", "agent_type": "Task"},
    {"ts": "2026-01-16T12:00:06.000Z", "event": "PreToolUse", "tool_use_id": "t2", "tool_name": "Read"},
    {"ts": "2026-01-16T12:00:07.000Z", "event": "PreToolUse", "tool_use_id": "t3", "tool_name": "Write"},
    {"ts": "2026-01-16T12:00:08.000Z", "event": "PostToolUse", "tool_use_id": "t2"},
    {"ts": "2026-01-16T12:00:09.000Z", "event": "PostToolUse", "tool_use_id": "t3"},
    {"ts": "2026-01-16T12:00:10.000Z", "event": "SubagentStop", "agent_id": "agent-2"},
]


@pytest.fixture
def sample_test_context():
    """Sample test context for use in tests."""
    return TestContext(
        fixture_id="test-fixture",
        test_id="test-001",
        test_name="Test Name",
        package="test-package",
        paths=TestContextPaths(fixture_yaml="fixture.yaml", test_yaml="test.yaml"),
    )


@pytest.fixture
def sample_artifact_paths():
    """Sample artifact paths for use in tests."""
    return ArtifactPaths(
        transcript="test-fixture/test-001-transcript.jsonl",
        trace="test-fixture/test-001-trace.jsonl",
        enriched="test-fixture/test-001-enriched.json",
    )


# =============================================================================
# Test: Basic Tree Building
# =============================================================================


class TestBasicTreeBuilding:
    """Tests for basic tree construction."""

    def test_builds_tree_with_user_assistant_exchange(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test building tree with simple user/assistant exchange."""
        result = build_timeline_tree(
            transcript_entries=SAMPLE_TRANSCRIPT,
            trace_events=SAMPLE_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        assert isinstance(enriched, EnrichedData)
        assert enriched.tree is not None
        assert enriched.tree.root_uuid is not None
        assert len(enriched.tree.nodes) > 0

    def test_creates_root_node(self, sample_test_context, sample_artifact_paths):
        """Test that a root node is created."""
        result = build_timeline_tree(
            transcript_entries=SAMPLE_TRANSCRIPT,
            trace_events=SAMPLE_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        root_uuid = enriched.tree.root_uuid
        assert root_uuid in enriched.tree.nodes
        root_node = enriched.tree.nodes[root_uuid]
        assert root_node.node_type == TimelineNodeType.ROOT
        assert root_node.depth == 0
        assert root_node.parent_uuid is None

    def test_parent_child_relationships(self, sample_test_context, sample_artifact_paths):
        """Test that parent-child relationships are correctly established."""
        result = build_timeline_tree(
            transcript_entries=SAMPLE_TRANSCRIPT,
            trace_events=SAMPLE_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        # Find uuid-2 node and verify it has uuid-1 as parent
        if "uuid-2" in enriched.tree.nodes:
            node_2 = enriched.tree.nodes["uuid-2"]
            assert node_2.parent_uuid == "uuid-1"

        # Verify children list is populated
        if "uuid-1" in enriched.tree.nodes:
            node_1 = enriched.tree.nodes["uuid-1"]
            assert "uuid-2" in node_1.children

    def test_preserves_test_context(self, sample_test_context, sample_artifact_paths):
        """Test that test context is preserved in enriched data."""
        result = build_timeline_tree(
            transcript_entries=SAMPLE_TRANSCRIPT,
            trace_events=SAMPLE_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        assert enriched.test_context.fixture_id == "test-fixture"
        assert enriched.test_context.test_id == "test-001"
        assert enriched.test_context.test_name == "Test Name"
        assert enriched.test_context.package == "test-package"

    def test_preserves_artifact_paths(self, sample_test_context, sample_artifact_paths):
        """Test that artifact paths are preserved in enriched data."""
        result = build_timeline_tree(
            transcript_entries=SAMPLE_TRANSCRIPT,
            trace_events=SAMPLE_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        assert enriched.artifacts.transcript == "test-fixture/test-001-transcript.jsonl"
        assert enriched.artifacts.trace == "test-fixture/test-001-trace.jsonl"
        assert enriched.artifacts.enriched == "test-fixture/test-001-enriched.json"


# =============================================================================
# Test: parentUuid Chain Resolution
# =============================================================================


class TestParentUuidChainResolution:
    """Tests for parentUuid chain resolution and depth calculation."""

    def test_resolves_nested_chain_depth_3(self, sample_test_context, sample_artifact_paths):
        """Test resolving nested parent-child chains at depth 3+."""
        result = build_timeline_tree(
            transcript_entries=SAMPLE_TRANSCRIPT,
            trace_events=SAMPLE_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        # uuid-4 should be at depth 4 (root=0, uuid-1=1, uuid-2=2, uuid-3=3, uuid-4=4)
        # or depth 3 if counting from first transcript entry
        if "uuid-4" in enriched.tree.nodes:
            node_4 = enriched.tree.nodes["uuid-4"]
            assert node_4.depth >= 3  # At least depth 3 from root

    def test_resolves_deep_chain_depth_5(self, sample_test_context, sample_artifact_paths):
        """Test resolving deeply nested chains at depth 5+."""
        result = build_timeline_tree(
            transcript_entries=DEEP_NESTED_TRANSCRIPT,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        # entry-5 should have the highest depth (depth 6 counting from synthetic root)
        # root(0) -> entry-0(1) -> entry-1(2) -> entry-2(3) -> entry-3(4) -> entry-4(5) -> entry-5(6)
        if "entry-5" in enriched.tree.nodes:
            node = enriched.tree.nodes["entry-5"]
            assert node.depth >= 6

    def test_depth_calculation_is_correct(self, sample_test_context, sample_artifact_paths):
        """Test that depth calculation follows the chain correctly."""
        result = build_timeline_tree(
            transcript_entries=DEEP_NESTED_TRANSCRIPT,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        # Verify depth increases by 1 at each level
        # entry-0 is at depth 1 (child of synthetic root at depth 0)
        # entry-1 is at depth 2 (child of entry-0)
        if "entry-0" in enriched.tree.nodes and "entry-1" in enriched.tree.nodes:
            entry0_depth = enriched.tree.nodes["entry-0"].depth
            entry1_depth = enriched.tree.nodes["entry-1"].depth
            assert entry1_depth == entry0_depth + 1

    def test_max_depth_stat_matches_deepest_node(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that max_depth stat matches the deepest node in tree."""
        result = build_timeline_tree(
            transcript_entries=DEEP_NESTED_TRANSCRIPT,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        # Find actual max depth in nodes
        actual_max_depth = max(node.depth for node in enriched.tree.nodes.values())
        assert enriched.stats.max_depth == actual_max_depth


# =============================================================================
# Test: Agent Correlation via tool_use_id
# =============================================================================


class TestAgentCorrelation:
    """Tests for agent correlation via tool_use_id."""

    def test_tool_calls_attributed_to_correct_subagent(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that tool calls are attributed to the correct subagent."""
        result = build_timeline_tree(
            transcript_entries=SAMPLE_TRANSCRIPT,
            trace_events=SAMPLE_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        # Check if any node has agent attribution
        nodes_with_agent = [
            node for node in enriched.tree.nodes.values() if node.agent_id is not None
        ]

        # The tool_use with toolu_01ABC should be attributed to agent a123
        for uuid, node in enriched.tree.nodes.items():
            if node.tool_name == "Read":
                assert node.agent_id == "a123"
                assert node.agent_type == "Explore"

    def test_subagent_start_stop_processing(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test SubagentStart/SubagentStop event processing."""
        result = build_timeline_tree(
            transcript_entries=SAMPLE_TRANSCRIPT,
            trace_events=SAMPLE_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        # Check agents dictionary is populated
        assert "a123" in enriched.agents or len(enriched.agents) > 0

        # Verify agent summary contains expected data
        if "a123" in enriched.agents:
            agent_summary = enriched.agents["a123"]
            assert agent_summary.agent_type == "Explore"

    def test_multiple_agents_tracked_separately(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that multiple agents are tracked separately."""
        result = build_timeline_tree(
            transcript_entries=MULTI_TOOL_TRANSCRIPT,
            trace_events=MULTI_AGENT_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        # Should have 2 agents
        assert len(enriched.agents) >= 2

        # Verify different agent types
        agent_types = [agent.agent_type for agent in enriched.agents.values()]
        assert "Explore" in agent_types
        assert "Task" in agent_types

    def test_tool_to_agent_map_building(self):
        """Test _build_tool_to_agent_map function directly."""
        tool_map = _build_tool_to_agent_map(SAMPLE_TRACE)

        # toolu_01ABC should map to (a123, Explore)
        assert "toolu_01ABC" in tool_map
        agent_id, agent_type = tool_map["toolu_01ABC"]
        assert agent_id == "a123"
        assert agent_type == "Explore"

    def test_tool_to_agent_map_with_multiple_agents(self):
        """Test tool map with multiple agents."""
        tool_map = _build_tool_to_agent_map(MULTI_AGENT_TRACE)

        # t1 should map to agent-1
        assert "t1" in tool_map
        assert tool_map["t1"][0] == "agent-1"

        # t2 and t3 should map to agent-2
        assert "t2" in tool_map
        assert tool_map["t2"][0] == "agent-2"
        assert "t3" in tool_map
        assert tool_map["t3"][0] == "agent-2"


# =============================================================================
# Test: Stats Calculation
# =============================================================================


class TestStatsCalculation:
    """Tests for tree statistics calculation."""

    def test_total_nodes_count(self, sample_test_context, sample_artifact_paths):
        """Test total_nodes count is correct."""
        result = build_timeline_tree(
            transcript_entries=SAMPLE_TRANSCRIPT,
            trace_events=SAMPLE_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        # Total nodes excludes the synthetic root node
        # So it should be len(nodes) - 1
        expected_count = len(enriched.tree.nodes) - 1  # Exclude synthetic root
        assert enriched.stats.total_nodes == expected_count

    def test_max_depth_calculation(self, sample_test_context, sample_artifact_paths):
        """Test max_depth calculation is correct."""
        result = build_timeline_tree(
            transcript_entries=DEEP_NESTED_TRANSCRIPT,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        # Max depth should be at least 6 for deep nested transcript
        # synthetic root(0) -> entry-0(1) -> ... -> entry-5(6)
        assert enriched.stats.max_depth >= 6

    def test_agent_count(self, sample_test_context, sample_artifact_paths):
        """Test agent_count is correct."""
        result = build_timeline_tree(
            transcript_entries=MULTI_TOOL_TRANSCRIPT,
            trace_events=MULTI_AGENT_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        # Should count 2 agents
        assert enriched.stats.agent_count == 2

    def test_tool_call_count(self, sample_test_context, sample_artifact_paths):
        """Test tool_call_count is correct."""
        result = build_timeline_tree(
            transcript_entries=MULTI_TOOL_TRANSCRIPT,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        # MULTI_TOOL_TRANSCRIPT has 3 tool_use entries
        assert enriched.stats.tool_call_count == 3

    def test_compute_tree_stats_directly(self):
        """Test _compute_tree_stats function directly."""
        nodes = {
            "root": TreeNode(
                node_type=TimelineNodeType.ROOT, depth=0, children=["n1", "n2"]
            ),
            "n1": TreeNode(
                node_type=TimelineNodeType.TOOL_CALL,
                depth=1,
                parent_uuid="root",
                tool_name="Bash",
            ),
            "n2": TreeNode(
                node_type=TimelineNodeType.TOOL_CALL,
                depth=1,
                parent_uuid="root",
                tool_name="Read",
            ),
        }
        agents = {
            "a1": AgentSummary(agent_type="Explore", tool_count=2),
        }

        stats = _compute_tree_stats(nodes, agents, [])

        # total_nodes excludes the synthetic root node
        assert stats.total_nodes == 2  # n1 and n2, not counting root
        assert stats.max_depth == 1
        assert stats.agent_count == 1
        assert stats.tool_call_count == 2
        # token_usage should be zero with empty transcript
        assert stats.token_usage is not None
        assert stats.token_usage.total_all == 0


# =============================================================================
# Test: Orphan Handling
# =============================================================================


class TestOrphanHandling:
    """Tests for handling entries without parentUuid."""

    def test_entries_without_parentuuid_attached_to_root(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that entries without parentUuid become children of root."""
        result = build_timeline_tree(
            transcript_entries=ORPHAN_TRANSCRIPT,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        root_uuid = enriched.tree.root_uuid
        root_node = enriched.tree.nodes[root_uuid]

        # Both orphan-1 and orphan-2 should be children of root
        assert "orphan-1" in root_node.children or any(
            enriched.tree.nodes[child].parent_uuid == root_uuid
            for child in root_node.children
            if child in enriched.tree.nodes
        )

    def test_multiple_root_level_entries(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test handling multiple entries with null parentUuid."""
        result = build_timeline_tree(
            transcript_entries=ORPHAN_TRANSCRIPT,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        # orphan-1 and orphan-2 should both exist
        assert "orphan-1" in enriched.tree.nodes
        assert "orphan-2" in enriched.tree.nodes

        # Both should have depth 1 (children of root)
        orphan1_depth = enriched.tree.nodes["orphan-1"].depth
        orphan2_depth = enriched.tree.nodes["orphan-2"].depth
        assert orphan1_depth == orphan2_depth

    def test_orphan_children_still_linked(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that children of orphans are still properly linked."""
        result = build_timeline_tree(
            transcript_entries=ORPHAN_TRANSCRIPT,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        # child-1 should have orphan-1 as parent
        if "child-1" in enriched.tree.nodes:
            child_node = enriched.tree.nodes["child-1"]
            assert child_node.parent_uuid == "orphan-1"


# =============================================================================
# Test: Node Type Classification
# =============================================================================


class TestNodeTypeClassification:
    """Tests for _classify_node_type function."""

    def test_classifies_user_type_as_prompt(self):
        """Test that user type is classified as PROMPT."""
        entry = {"type": "user", "message": {"content": "Hello"}}
        node_type = _classify_node_type(entry)
        assert node_type == TimelineNodeType.PROMPT

    def test_classifies_assistant_text_as_response(self):
        """Test that assistant text is classified as RESPONSE."""
        entry = {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "Hi"}]},
        }
        node_type = _classify_node_type(entry)
        assert node_type == TimelineNodeType.RESPONSE

    def test_classifies_tool_use_as_tool_call(self):
        """Test that tool_use is classified as TOOL_CALL."""
        entry = {
            "type": "assistant",
            "message": {
                "content": [{"type": "tool_use", "id": "t1", "name": "Bash"}]
            },
        }
        node_type = _classify_node_type(entry)
        assert node_type == TimelineNodeType.TOOL_CALL

    def test_classifies_tool_result_as_tool_result(self):
        """Test that tool_result is classified as TOOL_RESULT."""
        entry = {
            "type": "user",
            "message": {
                "content": [{"type": "tool_result", "tool_use_id": "t1"}]
            },
        }
        node_type = _classify_node_type(entry)
        assert node_type == TimelineNodeType.TOOL_RESULT

    def test_handles_missing_type_field(self):
        """Test handling of entry without type field."""
        entry = {"message": {"content": "No type field"}}
        node_type = _classify_node_type(entry)
        # Should default to RESPONSE or handle gracefully
        assert node_type is not None


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_transcript_returns_valid_enriched_data(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that empty transcript returns valid EnrichedData with empty tree."""
        result = build_timeline_tree(
            transcript_entries=[],
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        assert isinstance(enriched, EnrichedData)
        assert enriched.tree is not None
        assert enriched.tree.root_uuid is not None
        # Tree should have the synthetic root node
        assert len(enriched.tree.nodes) >= 1
        # total_nodes excludes root, so empty transcript = 0 nodes
        assert enriched.stats.total_nodes == 0

    def test_empty_trace_still_builds_tree(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that empty trace still builds tree (just no agent attribution)."""
        result = build_timeline_tree(
            transcript_entries=SAMPLE_TRANSCRIPT,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        assert isinstance(enriched, EnrichedData)
        assert len(enriched.tree.nodes) > 1  # More than just root
        # No agents should be present
        assert len(enriched.agents) == 0

    def test_handles_missing_uuid_field_gracefully(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test handling of entries without uuid field."""
        transcript = [
            {"type": "user", "message": {"content": "No uuid"}},  # Missing uuid
            {
                "uuid": "valid-uuid",
                "parentUuid": None,
                "type": "user",
                "message": {"content": "Has uuid"},
            },
        ]

        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        assert isinstance(enriched, EnrichedData)
        # Should handle gracefully without crashing
        # Should have warning about missing uuid
        assert len(result.warnings) > 0
        assert "missing uuid" in result.warnings[0].lower()

    def test_handles_missing_message_field_gracefully(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test handling of entries without message field."""
        transcript = [
            {"uuid": "u1", "parentUuid": None, "type": "user"},  # Missing message
        ]

        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        assert isinstance(result.value, EnrichedData)

    def test_handles_circular_reference_gracefully(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test handling of circular parentUuid references."""
        # This shouldn't happen in practice but we should handle it gracefully
        # Note: Our current implementation doesn't detect true cycles in the
        # depth computation since the cycle causes nodes to become orphans
        # (attached to root) rather than infinite recursion
        transcript = [
            {"uuid": "a", "parentUuid": "b", "type": "user", "message": {}},
            {"uuid": "b", "parentUuid": "a", "type": "user", "message": {}},
        ]

        # Should not hang or crash
        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        # This case produces a Success with warnings since both nodes
        # reference each other but get attached to root (broken refs)
        assert isinstance(result, Success)
        assert isinstance(result.value, EnrichedData)

    def test_handles_broken_parent_chain_gracefully(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test handling of entries with non-existent parentUuid."""
        transcript = [
            {"uuid": "child", "parentUuid": "non-existent-parent", "type": "user", "message": {}},
        ]

        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        assert isinstance(enriched, EnrichedData)
        # Child should still be in the tree (attached to root as orphan)
        assert "child" in enriched.tree.nodes or len(enriched.tree.nodes) > 1
        # Should have warning about broken parent reference
        assert len(result.warnings) > 0
        assert "broken" in result.warnings[0].lower() or "parentuuid" in result.warnings[0].lower()

    def test_build_tool_to_agent_map_empty_trace(self):
        """Test _build_tool_to_agent_map with empty trace."""
        tool_map = _build_tool_to_agent_map([])
        assert tool_map == {}

    def test_build_tool_to_agent_map_no_subagents(self):
        """Test _build_tool_to_agent_map with trace without subagents."""
        trace = [
            {"ts": "2026-01-16T12:00:00.000Z", "event": "SessionStart"},
            {"ts": "2026-01-16T12:00:01.000Z", "event": "PreToolUse", "tool_use_id": "t1"},
        ]
        tool_map = _build_tool_to_agent_map(trace)
        # Tools without active subagent should not be in map
        assert "t1" not in tool_map or tool_map.get("t1") == (None, None)

    def test_compute_tree_stats_empty_nodes(self):
        """Test _compute_tree_stats with empty nodes dictionary."""
        stats = _compute_tree_stats({}, {}, [])
        assert stats.total_nodes == 0
        assert stats.max_depth == 0
        assert stats.agent_count == 0
        assert stats.tool_call_count == 0
        # token_usage should be zero with empty transcript
        assert stats.token_usage is not None
        assert stats.token_usage.total_all == 0


# =============================================================================
# Test: Integration / Schema Validation
# =============================================================================


class TestSchemaValidation:
    """Tests for validating output conforms to Pydantic schemas."""

    def test_enriched_data_is_serializable(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that EnrichedData can be serialized to JSON."""
        result = build_timeline_tree(
            transcript_entries=SAMPLE_TRANSCRIPT,
            trace_events=SAMPLE_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        # Should not raise an exception
        json_str = enriched.model_dump_json()
        assert isinstance(json_str, str)
        assert len(json_str) > 0

    def test_enriched_data_roundtrip(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that EnrichedData can be serialized and deserialized."""
        import json

        result = build_timeline_tree(
            transcript_entries=SAMPLE_TRANSCRIPT,
            trace_events=SAMPLE_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value
        # Serialize and deserialize
        json_str = enriched.model_dump_json()
        data_dict = json.loads(json_str)
        restored = EnrichedData.model_validate(data_dict)

        assert restored.test_context.test_id == enriched.test_context.test_id
        assert restored.stats.total_nodes == enriched.stats.total_nodes
        assert restored.tree.root_uuid == enriched.tree.root_uuid


# =============================================================================
# Test: Result Pattern (Success/Failure/Warnings)
# =============================================================================


class TestResultPattern:
    """Tests for Result pattern implementation in enrichment."""

    def test_success_result_has_empty_warnings_on_clean_input(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that clean input produces Success with no warnings."""
        result = build_timeline_tree(
            transcript_entries=SAMPLE_TRANSCRIPT,
            trace_events=SAMPLE_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        assert result.is_success()
        assert not result.is_failure()
        # Clean input should have no warnings
        assert len(result.warnings) == 0

    def test_success_with_warnings_for_missing_uuid(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that missing uuid entries produce Success with warnings."""
        transcript = [
            {"type": "user", "message": {"content": "No uuid"}},  # Missing uuid
            {"uuid": "valid-1", "parentUuid": None, "type": "user", "message": {}},
        ]

        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        assert len(result.warnings) >= 1
        # Warning should mention Phase 1 and missing uuid
        assert any("Phase 1" in w for w in result.warnings)

    def test_success_with_warnings_for_broken_parent_refs(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that broken parentUuid refs produce Success with warnings."""
        transcript = [
            {"uuid": "orphan", "parentUuid": "non-existent", "type": "user", "message": {}},
        ]

        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        assert len(result.warnings) >= 1
        # Warning should mention Phase 2 and broken references
        assert any("Phase 2" in w for w in result.warnings)
        assert any("broken" in w.lower() for w in result.warnings)

    def test_success_with_warnings_for_uncorrelated_tools(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that tool calls without agent correlation produce warnings."""
        # Transcript with tool calls but trace without agents
        transcript = [
            {"uuid": "u1", "parentUuid": None, "type": "user", "message": {"content": "Run"}},
            {
                "uuid": "a1",
                "parentUuid": "u1",
                "type": "assistant",
                "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Bash"}]},
            },
        ]
        # Trace with tool events but no SubagentStart/Stop
        trace = [
            {"ts": "2026-01-16T12:00:00.000Z", "event": "SessionStart"},
            {"ts": "2026-01-16T12:00:01.000Z", "event": "PreToolUse", "tool_use_id": "t1"},
        ]

        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=trace,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        # Should have warning about uncorrelated tool calls
        assert len(result.warnings) >= 1
        assert any("Phase 3" in w for w in result.warnings)

    def test_accumulated_warnings_from_multiple_phases(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that warnings from multiple phases accumulate."""
        # Input that triggers warnings from multiple phases
        transcript = [
            {"type": "user", "message": {"content": "No uuid"}},  # Phase 1 warning
            {"uuid": "orphan", "parentUuid": "missing", "type": "user", "message": {}},  # Phase 2
        ]

        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        # Should have warnings from both Phase 1 and Phase 2
        assert len(result.warnings) >= 2
        phases_mentioned = [w for w in result.warnings if "Phase" in w]
        assert len(phases_mentioned) >= 2

    def test_success_value_accessible(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that Success.value contains complete EnrichedData."""
        result = build_timeline_tree(
            transcript_entries=SAMPLE_TRANSCRIPT,
            trace_events=SAMPLE_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value

        # Verify complete structure
        assert enriched.test_context == sample_test_context
        assert enriched.artifacts == sample_artifact_paths
        assert enriched.tree is not None
        assert enriched.tree.root_uuid is not None
        assert len(enriched.tree.nodes) > 0
        assert enriched.stats is not None
        assert isinstance(enriched.agents, dict)

    def test_result_is_success_and_is_failure_methods(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test is_success() and is_failure() methods work correctly."""
        result = build_timeline_tree(
            transcript_entries=SAMPLE_TRANSCRIPT,
            trace_events=SAMPLE_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert result.is_success() is True
        assert result.is_failure() is False

    def test_warnings_include_context_details(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that warnings include useful context details."""
        transcript = [
            {"uuid": "c1", "parentUuid": "missing-1", "type": "user", "message": {}},
            {"uuid": "c2", "parentUuid": "missing-2", "type": "user", "message": {}},
            {"uuid": "c3", "parentUuid": "missing-3", "type": "user", "message": {}},
        ]

        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        # Warning should include count of broken references
        broken_warning = [w for w in result.warnings if "broken" in w.lower()]
        assert len(broken_warning) >= 1
        assert "3" in broken_warning[0]  # Should mention the count

    def test_partial_result_not_present_on_success(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that Success does not have partial_result attribute."""
        result = build_timeline_tree(
            transcript_entries=SAMPLE_TRANSCRIPT,
            trace_events=SAMPLE_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        # Success should have value and warnings, not partial_result
        assert hasattr(result, "value")
        assert hasattr(result, "warnings")
        assert not hasattr(result, "partial_result")


class TestResultPatternFailure:
    """Tests for Failure cases in Result pattern."""

    def test_failure_has_error_attribute(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that if we get a Failure, it has proper error structure."""
        # Note: Currently our implementation is very resilient and
        # doesn't return Failure for most edge cases. This test documents
        # the expected structure if a Failure were returned.

        # For now, verify the EnrichmentError structure
        error = EnrichmentError(
            phase="test_phase",
            message="Test error message",
            context={"key": "value"},
        )

        assert error.phase == "test_phase"
        assert error.message == "Test error message"
        assert error.context == {"key": "value"}

    def test_failure_structure_with_partial_result(self):
        """Test Failure dataclass with partial_result."""
        # Create a mock failure with partial result
        partial_data = {"some": "data"}
        error = EnrichmentError(
            phase="depth_compute",
            message="Circular reference",
            context={},
        )
        failure = Failure(error=error, partial_result=partial_data)

        assert failure.is_failure() is True
        assert failure.is_success() is False
        assert failure.error == error
        assert failure.partial_result == partial_data
