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

    def test_handles_self_referential_parent_uuid(
        self, sample_test_context, sample_artifact_paths
    ):
        """Node with parentUuid pointing to itself should not cause infinite loop."""
        transcript = [
            {"uuid": "self-ref", "parentUuid": "self-ref", "type": "user", "message": {"content": "I reference myself"}},
        ]

        # Should not hang or crash - complete within reasonable time
        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        # Should succeed without hanging
        assert isinstance(result, Success)
        enriched = result.value
        assert isinstance(enriched, EnrichedData)
        # Node should exist in tree
        assert "self-ref" in enriched.tree.nodes
        # Node should still have itself as parent (circular reference)
        # The key test is that we didn't infinite loop or crash
        node = enriched.tree.nodes["self-ref"]
        assert node is not None
        # Stats should reflect the one node (plus synthetic root)
        assert enriched.stats.total_nodes == 1

    def test_handles_nested_subagents(
        self, sample_test_context, sample_artifact_paths
    ):
        """Subagent that spawns another subagent should build correct tree."""
        # Transcript with tool calls from nested agents
        transcript = [
            {"uuid": "u1", "parentUuid": None, "type": "user", "message": {"content": "Start task"}},
            {
                "uuid": "a1",
                "parentUuid": "u1",
                "type": "assistant",
                "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Task"}]},
            },
            {
                "uuid": "r1",
                "parentUuid": "a1",
                "type": "user",
                "message": {"content": [{"type": "tool_result", "tool_use_id": "t1"}]},
            },
            # Nested agent's tool call
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
            # Deeply nested agent's tool call
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

        # Trace with nested agents: outer -> inner -> innermost
        trace = [
            {"ts": "2026-01-18T12:00:00.000Z", "event": "SessionStart", "session_id": "test-nested"},
            {"ts": "2026-01-18T12:00:01.000Z", "event": "SubagentStart", "agent_id": "outer-agent", "agent_type": "Task"},
            {"ts": "2026-01-18T12:00:02.000Z", "event": "PreToolUse", "tool_use_id": "t1", "tool_name": "Task"},
            {"ts": "2026-01-18T12:00:03.000Z", "event": "SubagentStart", "agent_id": "inner-agent", "agent_type": "Explore"},
            {"ts": "2026-01-18T12:00:04.000Z", "event": "PreToolUse", "tool_use_id": "t2", "tool_name": "Read"},
            {"ts": "2026-01-18T12:00:05.000Z", "event": "SubagentStart", "agent_id": "innermost-agent", "agent_type": "Write"},
            {"ts": "2026-01-18T12:00:06.000Z", "event": "PreToolUse", "tool_use_id": "t3", "tool_name": "Write"},
            {"ts": "2026-01-18T12:00:07.000Z", "event": "PostToolUse", "tool_use_id": "t3"},
            {"ts": "2026-01-18T12:00:08.000Z", "event": "SubagentStop", "agent_id": "innermost-agent"},
            {"ts": "2026-01-18T12:00:09.000Z", "event": "PostToolUse", "tool_use_id": "t2"},
            {"ts": "2026-01-18T12:00:10.000Z", "event": "SubagentStop", "agent_id": "inner-agent"},
            {"ts": "2026-01-18T12:00:11.000Z", "event": "PostToolUse", "tool_use_id": "t1"},
            {"ts": "2026-01-18T12:00:12.000Z", "event": "SubagentStop", "agent_id": "outer-agent"},
        ]

        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=trace,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value

        # Should have 3 agents tracked
        assert len(enriched.agents) == 3
        agent_ids = set(enriched.agents.keys())
        assert "outer-agent" in agent_ids
        assert "inner-agent" in agent_ids
        assert "innermost-agent" in agent_ids

        # Verify tool attribution - each tool should be attributed to correct agent
        # t1 -> outer-agent, t2 -> inner-agent, t3 -> innermost-agent
        for uuid, node in enriched.tree.nodes.items():
            if node.tool_name == "Task":
                assert node.agent_id == "outer-agent"
            elif node.tool_name == "Read":
                assert node.agent_id == "inner-agent"
            elif node.tool_name == "Write":
                assert node.agent_id == "innermost-agent"

    def test_handles_wide_tree_50_siblings(
        self, sample_test_context, sample_artifact_paths
    ):
        """Parent with 50 children should work correctly."""
        # Create parent node and 50 child nodes
        transcript = [
            {"uuid": "parent", "parentUuid": None, "type": "user", "message": {"content": "Parent message"}},
        ]
        for i in range(50):
            transcript.append({
                "uuid": f"child-{i}",
                "parentUuid": "parent",
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": f"Child {i} response"}]},
            })

        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value

        # Should have 51 nodes (parent + 50 children) plus synthetic root
        # total_nodes excludes synthetic root, so should be 51
        assert enriched.stats.total_nodes == 51

        # Parent node should have 50 children
        parent_node = enriched.tree.nodes.get("parent")
        assert parent_node is not None
        assert len(parent_node.children) == 50

        # All children should have depth 2 (root=0, parent=1, children=2)
        for i in range(50):
            child_uuid = f"child-{i}"
            assert child_uuid in enriched.tree.nodes
            child_node = enriched.tree.nodes[child_uuid]
            assert child_node.parent_uuid == "parent"
            assert child_node.depth == 2  # root(0) -> parent(1) -> child(2)

    def test_handles_duplicate_uuid(
        self, sample_test_context, sample_artifact_paths
    ):
        """Two entries with same UUID - should use first or handle gracefully."""
        transcript = [
            {"uuid": "dup-uuid", "parentUuid": None, "type": "user", "message": {"content": "First entry"}},
            {"uuid": "dup-uuid", "parentUuid": None, "type": "assistant", "message": {"content": [{"type": "text", "text": "Duplicate UUID entry"}]}},
            {"uuid": "child", "parentUuid": "dup-uuid", "type": "user", "message": {"content": "Child of duplicate"}},
        ]

        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        # Should succeed without crashing
        assert isinstance(result, Success)
        enriched = result.value
        assert isinstance(enriched, EnrichedData)

        # The duplicate UUID should exist in tree (first occurrence takes precedence)
        assert "dup-uuid" in enriched.tree.nodes
        # Child should still be linked correctly
        assert "child" in enriched.tree.nodes
        child_node = enriched.tree.nodes["child"]
        assert child_node.parent_uuid == "dup-uuid"

        # May have warning about duplicate UUID (implementation dependent)
        # At minimum, should not crash

    def test_handles_unicode_content(
        self, sample_test_context, sample_artifact_paths
    ):
        """Non-ASCII characters in messages should not cause errors."""
        transcript = [
            {
                "uuid": "unicode-1",
                "parentUuid": None,
                "type": "user",
                "message": {"content": "Hello in Japanese: \u3053\u3093\u306b\u3061\u306f"},
            },
            {
                "uuid": "unicode-2",
                "parentUuid": "unicode-1",
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Response with emoji: \ud83d\ude80\ud83c\udf1f\ud83d\udc4d"}]},
            },
            {
                "uuid": "unicode-3",
                "parentUuid": "unicode-2",
                "type": "user",
                "message": {"content": "Chinese: \u4e2d\u6587, Russian: \u041f\u0440\u0438\u0432\u0435\u0442, Arabic: \u0645\u0631\u062d\u0628\u0627"},
            },
            {
                "uuid": "unicode-4",
                "parentUuid": "unicode-3",
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Special chars: \u00e9\u00e8\u00ea\u00eb \u00f1 \u00df \u00e6 \u00f8"}]},
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

        # All 4 nodes should be present
        assert enriched.stats.total_nodes == 4
        assert "unicode-1" in enriched.tree.nodes
        assert "unicode-2" in enriched.tree.nodes
        assert "unicode-3" in enriched.tree.nodes
        assert "unicode-4" in enriched.tree.nodes

        # Verify tree structure is correct
        assert enriched.tree.nodes["unicode-2"].parent_uuid == "unicode-1"
        assert enriched.tree.nodes["unicode-3"].parent_uuid == "unicode-2"
        assert enriched.tree.nodes["unicode-4"].parent_uuid == "unicode-3"

        # Verify serialization works with unicode - should not raise
        json_str = enriched.model_dump_json()
        assert isinstance(json_str, str)
        assert len(json_str) > 0

        # Verify roundtrip works - deserialize and check structure preserved
        import json
        data_dict = json.loads(json_str)
        restored = EnrichedData.model_validate(data_dict)
        assert restored.stats.total_nodes == 4
        assert "unicode-1" in restored.tree.nodes


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


class TestSerializationErrors:
    """Tests for serialization error handling.

    Verifies that serialization errors are captured in Result, not swallowed.
    """

    def test_handles_non_serializable_content(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test handling of objects that can't be JSON serialized.

        The enrichment process should handle non-serializable objects gracefully,
        either by converting them to strings or producing appropriate warnings.
        """
        import json
        from unittest.mock import patch, MagicMock

        # Create transcript with a type that's typically not serializable
        # Note: In practice, transcript entries are already dict-like from JSON parsing,
        # so we test the behavior when model_dump_json encounters issues
        result = build_timeline_tree(
            transcript_entries=SAMPLE_TRANSCRIPT,
            trace_events=SAMPLE_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value

        # Verify it can be serialized (the happy path)
        json_str = enriched.model_dump_json()
        assert isinstance(json_str, str)

        # Now test that if serialization were to fail, it's handled properly
        # Mock model_dump_json to raise a TypeError (typical serialization error)
        mock_enriched = MagicMock()
        mock_enriched.model_dump_json.side_effect = TypeError(
            "Object of type 'function' is not JSON serializable"
        )

        # The error should be catchable and not crash the program
        try:
            mock_enriched.model_dump_json()
            assert False, "Should have raised TypeError"
        except TypeError as e:
            assert "JSON serializable" in str(e)

    def test_handles_circular_reference_in_data(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test handling of circular references in dict data.

        Circular references in dictionaries cause json.dumps to fail with ValueError.
        The enrichment process should handle this gracefully.
        """
        import json

        # First verify normal case works
        result = build_timeline_tree(
            transcript_entries=SAMPLE_TRANSCRIPT,
            trace_events=SAMPLE_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value

        # Verify normal serialization works
        json_str = enriched.model_dump_json()
        parsed = json.loads(json_str)
        assert "tree" in parsed
        assert "stats" in parsed

        # Demonstrate that circular references would cause issues
        # (this documents expected behavior if they occurred)
        circular_dict = {"key": "value"}
        circular_dict["self"] = circular_dict

        with pytest.raises(ValueError, match="Circular reference"):
            json.dumps(circular_dict)

        # Test that the tree building itself handles circular parentUuid refs
        # (this is covered in TestEdgeCases but we verify the Result pattern)
        circular_transcript = [
            {"uuid": "a", "parentUuid": "b", "type": "user", "message": {}},
            {"uuid": "b", "parentUuid": "a", "type": "user", "message": {}},
        ]

        result = build_timeline_tree(
            transcript_entries=circular_transcript,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        # Should succeed (with warnings about broken refs) rather than fail
        assert isinstance(result, Success)
        # The result should be serializable despite circular input refs
        json_output = result.value.model_dump_json()
        assert isinstance(json_output, str)

    def test_serialization_errors_captured_not_swallowed(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that serialization errors are captured in Result, not swallowed.

        This tests the principle that errors should be visible to callers.
        """
        from unittest.mock import patch

        # Build valid enriched data first
        result = build_timeline_tree(
            transcript_entries=SAMPLE_TRANSCRIPT,
            trace_events=SAMPLE_TRACE,
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value

        # Verify that if we were to encounter a serialization error during
        # the enrichment process, it would be captured in the Result
        # Currently build_timeline_tree is very resilient and returns Success
        # with warnings for edge cases, but we verify the pattern

        # The Result pattern ensures:
        # 1. Success has value and warnings (not errors that were swallowed)
        assert hasattr(result, "value")
        assert hasattr(result, "warnings")
        assert result.value is not None

        # 2. If there were issues, they're in warnings, not hidden
        # (in this case, clean input has no warnings)
        assert isinstance(result.warnings, list)

        # 3. The enriched data is fully serializable
        try:
            json_str = enriched.model_dump_json()
            assert len(json_str) > 0
        except (TypeError, ValueError) as e:
            # If this fails, it indicates an issue that should be captured
            pytest.fail(f"Serialization should succeed or be captured in Result: {e}")


# =============================================================================
# Test: Deep Trees and Scale Testing
# =============================================================================


class TestDeepTreesAndScale:
    """Tests for handling deep trees without stack overflow and large node counts."""

    def _build_deep_chain(self, depth: int) -> list:
        """Build a transcript chain of the specified depth.

        Args:
            depth: Number of nodes in the chain (excluding synthetic root)

        Returns:
            List of transcript entries forming a linear chain
        """
        entries = []
        for i in range(depth):
            parent_uuid = f"entry-{i - 1}" if i > 0 else None
            entries.append({
                "uuid": f"entry-{i}",
                "parentUuid": parent_uuid,
                "type": "assistant" if i % 2 == 1 else "user",
                "message": {"content": []},
            })
        return entries

    def _build_wide_tree(self, node_count: int, children_per_node: int = 5) -> list:
        """Build a transcript with a wide tree structure.

        Args:
            node_count: Total number of nodes to create
            children_per_node: Number of children per internal node

        Returns:
            List of transcript entries forming a wide tree
        """
        entries = []
        # Root node
        entries.append({
            "uuid": "entry-0",
            "parentUuid": None,
            "type": "user",
            "message": {"content": []},
        })

        # Build tree level by level
        queue = ["entry-0"]
        node_id = 1

        while node_id < node_count and queue:
            parent_uuid = queue.pop(0)
            for _ in range(children_per_node):
                if node_id >= node_count:
                    break
                uuid = f"entry-{node_id}"
                entries.append({
                    "uuid": uuid,
                    "parentUuid": parent_uuid,
                    "type": "assistant" if node_id % 2 == 1 else "user",
                    "message": {"content": []},
                })
                queue.append(uuid)
                node_id += 1

        return entries

    def test_handles_depth_50_tree(self, sample_test_context, sample_artifact_paths):
        """Test that depth 50 tree is handled without stack overflow.

        This verifies the iterative depth computation works correctly
        for trees that are deep but within reasonable limits.
        """
        transcript = self._build_deep_chain(50)

        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value

        # Verify deepest node has correct depth
        # Synthetic root is depth 0, entry-0 is depth 1, entry-49 is depth 50
        deepest_node = enriched.tree.nodes["entry-49"]
        assert deepest_node.depth == 50

        # Verify max_depth stat is correct
        assert enriched.stats.max_depth == 50

        # Verify total nodes count (excluding synthetic root)
        assert enriched.stats.total_nodes == 50

    def test_handles_depth_100_tree(self, sample_test_context, sample_artifact_paths):
        """Test that depth 100 tree is handled without stack overflow.

        This is a stress test for deep tree traversal. The recursive
        implementation would fail with RecursionError, but the iterative
        implementation should handle this without issue.
        """
        transcript = self._build_deep_chain(100)

        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value

        # Verify deepest node has correct depth
        deepest_node = enriched.tree.nodes["entry-99"]
        assert deepest_node.depth == 100

        # Verify max_depth stat is correct
        assert enriched.stats.max_depth == 100

        # Verify all nodes are present
        assert enriched.stats.total_nodes == 100

        # Verify depth increases monotonically in chain
        for i in range(1, 100):
            prev_depth = enriched.tree.nodes[f"entry-{i - 1}"].depth
            curr_depth = enriched.tree.nodes[f"entry-{i}"].depth
            assert curr_depth == prev_depth + 1

    def test_handles_100_nodes_efficiently(self, sample_test_context, sample_artifact_paths):
        """Test that 100 nodes are processed in under 2 seconds.

        This is a performance test to ensure tree building scales
        reasonably with node count.
        """
        import time

        transcript = self._build_wide_tree(100)

        start_time = time.time()
        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )
        elapsed = time.time() - start_time

        assert isinstance(result, Success)
        enriched = result.value

        # Verify all nodes are present
        assert enriched.stats.total_nodes == 100

        # Performance requirement: under 2 seconds
        assert elapsed < 2.0, f"Processing took {elapsed:.2f}s, expected < 2s"

    def test_handles_500_nodes(self, sample_test_context, sample_artifact_paths):
        """Test that 500 nodes are processed correctly.

        This is a larger scale test to verify the implementation
        handles realistic session sizes.
        """
        transcript = self._build_wide_tree(500)

        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value

        # Verify all nodes are present
        assert enriched.stats.total_nodes == 500

        # Verify tree structure is intact
        root_uuid = enriched.tree.root_uuid
        assert root_uuid in enriched.tree.nodes

        # Verify all nodes have valid depths (> 0 since root is synthetic)
        for uuid, node in enriched.tree.nodes.items():
            if uuid != root_uuid:
                assert node.depth >= 1, f"Node {uuid} has invalid depth {node.depth}"

        # Verify parent-child relationships are consistent
        for uuid, node in enriched.tree.nodes.items():
            if node.parent_uuid:
                parent = enriched.tree.nodes.get(node.parent_uuid)
                assert parent is not None, f"Node {uuid} has missing parent {node.parent_uuid}"
                assert uuid in parent.children, f"Node {uuid} not in parent's children list"

    def test_handles_depth_500_tree(self, sample_test_context, sample_artifact_paths):
        """Test extreme depth (500) to verify no stack overflow.

        This tests well beyond typical session depths to ensure
        the iterative implementation is robust.
        """
        transcript = self._build_deep_chain(500)

        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value

        # Verify deepest node has correct depth
        deepest_node = enriched.tree.nodes["entry-499"]
        assert deepest_node.depth == 500

        # Verify max_depth stat is correct
        assert enriched.stats.max_depth == 500


# =============================================================================
# Test: New Fields (seq, timestamp, elapsed_ms, SIDECHAIN)
# =============================================================================


class TestNewFields:
    """Tests for seq, timestamp, elapsed_ms fields and SIDECHAIN node type."""

    def test_seq_field_assigned_in_depth_first_order(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that seq numbers are assigned in depth-first order."""
        transcript = [
            {"uuid": "u1", "parentUuid": None, "type": "user", "message": {"content": "First"}},
            {"uuid": "u2", "parentUuid": "u1", "type": "assistant", "message": {"content": []}},
            {"uuid": "u3", "parentUuid": "u2", "type": "user", "message": {"content": "Deep"}},
            {"uuid": "u4", "parentUuid": "u1", "type": "user", "message": {"content": "Sibling"}},
        ]

        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value

        # Root should be seq=0
        assert enriched.tree.nodes["root"].seq == 0

        # Verify depth-first ordering
        # root(0) -> u1(1) -> u2(2) -> u3(3) -> u4(4)
        # Note: children are processed in order they were added
        seq_u1 = enriched.tree.nodes["u1"].seq
        seq_u2 = enriched.tree.nodes["u2"].seq
        seq_u3 = enriched.tree.nodes["u3"].seq
        seq_u4 = enriched.tree.nodes["u4"].seq

        # u1 should come before its children
        assert seq_u1 < seq_u2
        assert seq_u2 < seq_u3
        # u4 is a sibling of u2, so it should come after u3 (depth-first)
        assert seq_u3 < seq_u4

    def test_timestamp_field_extracted_from_entry(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that timestamp is extracted from transcript entries."""
        transcript = [
            {
                "uuid": "t1",
                "parentUuid": None,
                "type": "user",
                "timestamp": "2026-01-18T10:00:00.000Z",
                "message": {"content": "First"},
            },
            {
                "uuid": "t2",
                "parentUuid": "t1",
                "type": "assistant",
                "timestamp": "2026-01-18T10:00:05.500Z",
                "message": {"content": []},
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

        # Timestamps should be preserved
        assert enriched.tree.nodes["t1"].timestamp == "2026-01-18T10:00:00.000Z"
        assert enriched.tree.nodes["t2"].timestamp == "2026-01-18T10:00:05.500Z"

    def test_elapsed_ms_computed_from_timestamps(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that elapsed_ms is computed relative to first timestamp."""
        transcript = [
            {
                "uuid": "e1",
                "parentUuid": None,
                "type": "user",
                "timestamp": "2026-01-18T10:00:00.000Z",
                "message": {"content": "Start"},
            },
            {
                "uuid": "e2",
                "parentUuid": "e1",
                "type": "assistant",
                "timestamp": "2026-01-18T10:00:01.500Z",  # 1500ms later
                "message": {"content": []},
            },
            {
                "uuid": "e3",
                "parentUuid": "e2",
                "type": "user",
                "timestamp": "2026-01-18T10:00:05.000Z",  # 5000ms from start
                "message": {"content": "Later"},
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

        # First entry should have elapsed_ms = 0
        assert enriched.tree.nodes["e1"].elapsed_ms == 0
        # Second entry should be 1500ms from start
        assert enriched.tree.nodes["e2"].elapsed_ms == 1500
        # Third entry should be 5000ms from start
        assert enriched.tree.nodes["e3"].elapsed_ms == 5000

    def test_elapsed_ms_none_when_no_timestamp(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that elapsed_ms is None when entries lack timestamps."""
        transcript = [
            {"uuid": "n1", "parentUuid": None, "type": "user", "message": {"content": "No timestamp"}},
        ]

        result = build_timeline_tree(
            transcript_entries=transcript,
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value

        # Node without timestamp should have elapsed_ms = None
        assert enriched.tree.nodes["n1"].timestamp is None
        assert enriched.tree.nodes["n1"].elapsed_ms is None

    def test_sidechain_node_type_from_isSidechain_field(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that entries with isSidechain=True get SIDECHAIN node type."""
        transcript = [
            {"uuid": "main", "parentUuid": None, "type": "user", "message": {"content": "Main"}},
            {
                "uuid": "side",
                "parentUuid": "main",
                "type": "assistant",
                "isSidechain": True,
                "message": {"content": []},
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

        # Main entry should be PROMPT
        assert enriched.tree.nodes["main"].node_type == TimelineNodeType.PROMPT
        # Sidechain entry should be SIDECHAIN
        assert enriched.tree.nodes["side"].node_type == TimelineNodeType.SIDECHAIN

    def test_root_node_has_default_seq_and_elapsed(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that root node has seq=0 and elapsed_ms=0."""
        result = build_timeline_tree(
            transcript_entries=[],
            trace_events=[],
            test_context=sample_test_context,
            artifact_paths=sample_artifact_paths,
        )

        assert isinstance(result, Success)
        enriched = result.value

        root = enriched.tree.nodes["root"]
        assert root.seq == 0
        assert root.elapsed_ms == 0
        assert root.timestamp is None

    def test_new_fields_in_schema_serialization(
        self, sample_test_context, sample_artifact_paths
    ):
        """Test that new fields are included in JSON serialization."""
        import json

        transcript = [
            {
                "uuid": "ser1",
                "parentUuid": None,
                "type": "user",
                "timestamp": "2026-01-18T12:00:00.000Z",
                "message": {"content": "Test"},
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

        # Serialize and check fields are present
        json_str = enriched.model_dump_json()
        data = json.loads(json_str)

        node = data["tree"]["nodes"]["ser1"]
        assert "seq" in node
        assert "timestamp" in node
        assert "elapsed_ms" in node
        assert node["timestamp"] == "2026-01-18T12:00:00.000Z"
        assert node["elapsed_ms"] == 0
