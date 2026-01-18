"""Enrichment module for building timeline tree structure from transcript and trace data.

This module implements the tree-building algorithm described in the Timeline Tree
Architecture design document. It builds a hierarchical tree structure from Claude
session transcript entries and hook trace events.

Key phases:
1. Index transcript entries by UUID
2. Build parent-child relationships from parentUuid field
3. Enrich with trace data (agent attribution via tool_use_id)
4. Compute depths and tree statistics

The output is an EnrichedData structure that references transcript entries by UUID
rather than duplicating content, following the design principle of "preserve native
+ augment".
"""

from typing import List, Dict, Tuple, Optional, Any

from .schemas import (
    EnrichedData,
    TestContext,
    ArtifactPaths,
    TimelineTree,
    TreeNode,
    TimelineNodeType,
    AgentSummary,
    TreeStats,
)


def build_timeline_tree(
    transcript_entries: List[dict],
    trace_events: List[dict],
    test_context: TestContext,
    artifact_paths: ArtifactPaths,
) -> EnrichedData:
    """Build enriched data with tree structure from raw transcript and trace.

    This is the main entry point for tree construction. It follows the algorithm
    defined in the design document:

    Phase 1: Index transcript entries by uuid
    Phase 2: Build parent-child relationships from parentUuid
    Phase 3: Enrich with trace data (agent attribution)
    Phase 4: Compute depths and statistics

    Args:
        transcript_entries: List of raw transcript entry dicts from Claude session
        trace_events: List of hook trace event dicts
        test_context: Test identification metadata
        artifact_paths: Paths to artifact files

    Returns:
        EnrichedData with complete tree structure and statistics
    """
    # Phase 1: Index transcript entries by uuid
    by_uuid: Dict[str, dict] = {}
    for entry in transcript_entries:
        uuid = entry.get("uuid")
        if uuid:
            by_uuid[uuid] = entry

    # Phase 3 (early): Build tool_use_id to agent mapping from trace events
    # We do this before creating nodes so we can attribute agents during node creation
    tool_to_agent = _build_tool_to_agent_map(trace_events)

    # Phase 2: Build tree structure
    nodes: Dict[str, TreeNode] = {}
    root_children: List[str] = []

    # First pass: Create all nodes
    for uuid, entry in by_uuid.items():
        node = _create_tree_node(entry, tool_to_agent)
        nodes[uuid] = node

    # Second pass: Link parents to children and identify roots
    for uuid, entry in by_uuid.items():
        parent_uuid = entry.get("parentUuid")
        if parent_uuid and parent_uuid in nodes:
            # Link child to parent
            nodes[uuid].parent_uuid = parent_uuid
            # Add child UUID to parent's children list
            if uuid not in nodes[parent_uuid].children:
                nodes[parent_uuid].children.append(uuid)
        else:
            # No parent or parent not found - this is a root-level entry
            root_children.append(uuid)

    # Create synthetic root node
    root_uuid = "root"
    root_node = TreeNode(
        parent_uuid=None,
        depth=0,
        node_type=TimelineNodeType.ROOT,
        agent_id=None,
        agent_type=None,
        tool_name=None,
        children=root_children,
    )
    nodes[root_uuid] = root_node

    # Phase 4: Compute depths (root is 0, children are parent+1)
    _compute_depths(nodes, root_uuid, 0)

    # Build agent summaries from trace events
    agents = _build_agent_summaries(trace_events, nodes)

    # Compute tree statistics
    stats = _compute_tree_stats(nodes, agents)

    # Build the timeline tree
    tree = TimelineTree(
        root_uuid=root_uuid,
        nodes=nodes,
    )

    return EnrichedData(
        test_context=test_context,
        artifacts=artifact_paths,
        tree=tree,
        agents=agents,
        stats=stats,
    )


def _create_tree_node(entry: dict, agent_map: Dict[str, Tuple[str, str]]) -> TreeNode:
    """Create a TreeNode from a transcript entry.

    Args:
        entry: Raw transcript entry dict
        agent_map: Mapping from tool_use_id to (agent_id, agent_type)

    Returns:
        TreeNode with classified type and agent attribution if available
    """
    node_type = _classify_node_type(entry)

    # Get tool information
    tool_use_id = entry.get("toolUseID")
    tool_name = None
    agent_id = None
    agent_type = None

    # Extract tool name from message content if this is a tool call
    if node_type == TimelineNodeType.TOOL_CALL:
        message = entry.get("message", {})
        content = message.get("content", [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_name = block.get("name")
                    tool_use_id = tool_use_id or block.get("id")
                    break

    # Attribute agent from tool_use_id mapping
    if tool_use_id and tool_use_id in agent_map:
        agent_id, agent_type = agent_map[tool_use_id]

    return TreeNode(
        parent_uuid=None,  # Will be set in second pass
        depth=0,  # Will be computed in phase 4
        node_type=node_type,
        agent_id=agent_id,
        agent_type=agent_type,
        tool_name=tool_name,
        children=[],
    )


def _classify_node_type(entry: dict) -> TimelineNodeType:
    """Classify the node type based on transcript entry type.

    Classification logic from design doc:
    - type: "user" -> PROMPT (unless content has tool_result)
    - type: "assistant" with tool_use in content -> TOOL_CALL
    - type: "assistant" without tool_use -> RESPONSE
    - type: "user" with tool_result in content -> TOOL_RESULT

    Args:
        entry: Raw transcript entry dict

    Returns:
        TimelineNodeType classification
    """
    entry_type = entry.get("type", "")
    message = entry.get("message", {})
    content = message.get("content", [])

    # Check for tool_use or tool_result in content blocks
    has_tool_use = False
    has_tool_result = False

    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                block_type = block.get("type", "")
                if block_type == "tool_use":
                    has_tool_use = True
                elif block_type == "tool_result":
                    has_tool_result = True

    # Classify based on entry type and content
    if entry_type == "user":
        if has_tool_result:
            return TimelineNodeType.TOOL_RESULT
        return TimelineNodeType.PROMPT
    elif entry_type == "assistant":
        if has_tool_use:
            return TimelineNodeType.TOOL_CALL
        return TimelineNodeType.RESPONSE

    # Fallback to RESPONSE for unknown types
    return TimelineNodeType.RESPONSE


def _build_tool_to_agent_map(trace_events: List[dict]) -> Dict[str, Tuple[str, str]]:
    """Build mapping from tool_use_id to (agent_id, agent_type).

    Uses SubagentStart/SubagentStop events to determine which agent context
    a tool call executed in. Tool calls (PreToolUse/PostToolUse) occurring
    between a SubagentStart and its corresponding SubagentStop are attributed
    to that agent.

    Args:
        trace_events: List of hook trace event dicts

    Returns:
        Dict mapping tool_use_id to (agent_id, agent_type) tuple
    """
    tool_to_agent: Dict[str, Tuple[str, str]] = {}

    # Track active agents by their agent_id
    # We'll use a simple approach: track all SubagentStart events and their end times
    active_agents: Dict[str, Dict[str, Any]] = {}

    # First pass: collect agent lifecycle info
    agent_starts: Dict[str, Dict[str, Any]] = {}
    agent_stops: Dict[str, str] = {}  # agent_id -> stop timestamp

    for event in trace_events:
        event_type = event.get("event", "")
        agent_id = event.get("agent_id")

        if event_type == "SubagentStart" and agent_id:
            agent_starts[agent_id] = {
                "agent_type": event.get("agent_type", "unknown"),
                "ts": event.get("ts"),
                "pid": event.get("pid"),
            }
        elif event_type == "SubagentStop" and agent_id:
            agent_stops[agent_id] = event.get("ts", "")

    # Second pass: attribute tool calls to agents
    # For each tool call, find the most recently started agent that hasn't stopped yet
    current_agent_id: Optional[str] = None
    current_agent_type: Optional[str] = None

    for event in trace_events:
        event_type = event.get("event", "")

        if event_type == "SubagentStart":
            agent_id = event.get("agent_id")
            if agent_id:
                current_agent_id = agent_id
                current_agent_type = event.get("agent_type", "unknown")
                active_agents[agent_id] = {
                    "agent_type": current_agent_type,
                }

        elif event_type == "SubagentStop":
            agent_id = event.get("agent_id")
            if agent_id and agent_id in active_agents:
                del active_agents[agent_id]
            # Update current agent to any remaining active agent
            if active_agents:
                # Use the most recently added (last) active agent
                current_agent_id = list(active_agents.keys())[-1]
                current_agent_type = active_agents[current_agent_id]["agent_type"]
            else:
                current_agent_id = None
                current_agent_type = None

        elif event_type in ("PreToolUse", "PostToolUse"):
            tool_use_id = event.get("tool_use_id")
            if tool_use_id and current_agent_id:
                tool_to_agent[tool_use_id] = (current_agent_id, current_agent_type or "unknown")

    return tool_to_agent


def _compute_depths(nodes: Dict[str, TreeNode], node_uuid: str, depth: int) -> None:
    """Recursively compute depth for all nodes in the tree.

    Args:
        nodes: Dict mapping UUID to TreeNode
        node_uuid: Current node UUID to process
        depth: Depth value to assign to current node
    """
    if node_uuid not in nodes:
        return

    node = nodes[node_uuid]
    node.depth = depth

    for child_uuid in node.children:
        _compute_depths(nodes, child_uuid, depth + 1)


def _build_agent_summaries(
    trace_events: List[dict], nodes: Dict[str, TreeNode]
) -> Dict[str, AgentSummary]:
    """Build agent summary information from trace events.

    Args:
        trace_events: List of hook trace event dicts
        nodes: Dict mapping UUID to TreeNode (used for tool count)

    Returns:
        Dict mapping agent_id to AgentSummary
    """
    agents: Dict[str, AgentSummary] = {}

    # Track agent lifecycle from trace events
    for event in trace_events:
        event_type = event.get("event", "")
        agent_id = event.get("agent_id")

        if not agent_id:
            continue

        if event_type == "SubagentStart":
            if agent_id not in agents:
                agents[agent_id] = AgentSummary(
                    agent_type=event.get("agent_type", "unknown"),
                    start_uuid=None,
                    stop_uuid=None,
                    tool_count=0,
                )

        elif event_type == "SubagentStop":
            if agent_id in agents:
                # Agent already exists, just update any missing fields
                pass

    # Count tool calls per agent from nodes
    tool_counts: Dict[str, int] = {}
    for node in nodes.values():
        if node.node_type == TimelineNodeType.TOOL_CALL and node.agent_id:
            tool_counts[node.agent_id] = tool_counts.get(node.agent_id, 0) + 1

    # Update tool counts in agent summaries
    for agent_id, count in tool_counts.items():
        if agent_id in agents:
            agents[agent_id].tool_count = count

    return agents


def _compute_tree_stats(
    nodes: Dict[str, TreeNode], agents: Dict[str, AgentSummary]
) -> TreeStats:
    """Compute summary statistics for the tree.

    Args:
        nodes: Dict mapping UUID to TreeNode
        agents: Dict mapping agent_id to AgentSummary

    Returns:
        TreeStats with computed values
    """
    # Exclude the synthetic root node from count
    total_nodes = len(nodes) - 1 if "root" in nodes else len(nodes)

    # Find max depth (excluding root which is depth 0)
    max_depth = 0
    tool_call_count = 0

    for uuid, node in nodes.items():
        if uuid == "root":
            continue
        if node.depth > max_depth:
            max_depth = node.depth
        if node.node_type == TimelineNodeType.TOOL_CALL:
            tool_call_count += 1

    return TreeStats(
        total_nodes=total_nodes,
        max_depth=max_depth,
        agent_count=len(agents),
        tool_call_count=tool_call_count,
    )
