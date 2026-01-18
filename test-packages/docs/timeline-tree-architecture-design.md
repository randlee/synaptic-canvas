# Timeline Tree Architecture Design

**Status:** Approved Design
**Created:** 2026-01-18
**Updated:** 2026-01-18
**Author:** Claude (Planning Agent)

---

## Executive Summary

This document defines the architecture for replacing the current flat timeline with a tree-based architecture that leverages the `parentUuid` field from Claude session transcripts to build accurate parent-child relationships between agents and their tool calls.

---

## 1. Current Limitations Analysis

### 1.1 Timestamp-Based Correlation is Fragile

The current `correlate_tool_calls_with_agents()` function in `collector.py` (lines 453-543) uses a two-pass approach:

1. **Primary**: Uses `ppid` (parent process ID) to determine which subagent context a tool call executed in
2. **Fallback**: Uses timestamp-based correlation when ppid is unavailable

**Problems with this approach:**

- **Concurrent Agents**: When multiple subagents run simultaneously, timestamp ranges overlap. A tool call at `T+5s` could fall within the time ranges of multiple active subagents.
- **Process ID Instability**: The `ppid` approach requires that hook events capture the correct parent process ID, which may not always be reliable across different execution environments.
- **No True Hierarchy**: The correlation produces a flat mapping (`tool_use_id -> agent_id`), losing the hierarchical relationship between nested agents.

### 1.2 Flat Timeline Structure

The current `TimelineEntry` model lacks:

- No `parent_id` field to link to parent entry
- No `children` collection for nested entries
- No `depth` field for indentation level
- The `build_timeline()` method sorts by timestamp and renumbers sequentially, destroying any hierarchical information

### 1.3 Underutilized Data Sources

The session transcript (`-session.jsonl`) contains rich relationship data that is currently ignored:

| Field | Purpose | Current Usage |
|-------|---------|---------------|
| `uuid` | Unique entry identifier | Not used |
| `parentUuid` | Links to parent entry (null for root) | Not used |
| `toolUseID` | Identifies tool invocation | Partially used |
| `parentToolUseID` | Links tool results to tool invocations | Not used |
| `isSidechain` | Indicates branching conversation | Not used |

---

## 2. Available Data Sources and Relationships

### 2.1 Session Transcript Structure

Each transcript entry has the following relationship fields:

```json
{
  "uuid": "03b81000-842d-40ec-8e2f-02a6b4c81e34",
  "parentUuid": "1f0f2116-fba9-465c-8b21-e25c2ba45408",
  "isSidechain": false,
  "toolUseID": "toolu_01ABC123",
  "parentToolUseID": "toolu_01XYZ789",
  "type": "assistant",
  "timestamp": "2026-01-18T19:55:26.390Z"
}
```

**Key relationships:**

1. **Message Chain**: `parentUuid` forms a linked list from response back to initial prompt
2. **Tool Correlation**: `toolUseID` identifies tool invocations; tool results reference this via `parentToolUseID`
3. **Sidechain Branching**: `isSidechain: true` indicates a parallel conversation branch (subagent)

### 2.2 Trace File Structure

Hook events provide:

```json
{
  "event": "SubagentStart",
  "agent_id": "agent-abc123",
  "agent_type": "Explore",
  "ts": "2026-01-18T19:55:25.000Z",
  "pid": 12345,
  "ppid": 12340
}
```

**Key relationships:**

1. **Subagent Lifecycle**: `SubagentStart` and `SubagentStop` events share `agent_id`
2. **Tool Attribution**: `PreToolUse`/`PostToolUse` events have `tool_use_id`

### 2.3 Proposed Correlation Strategy

Build a tree by:
1. Using `parentUuid` chains from transcript as the primary relationship
2. Cross-referencing `toolUseID` between transcript and trace events
3. Using `isSidechain` to identify subagent conversation branches

---

## 3. Proposed Data Model Changes

### 3.1 New TimelineNode Model

Replace the flat `TimelineEntry` with a tree node:

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class TimelineNodeType(str, Enum):
    """Types of nodes in the timeline tree."""
    ROOT = "root"              # Session root
    PROMPT = "prompt"          # User prompt
    RESPONSE = "response"      # Assistant response
    TOOL_CALL = "tool_call"    # Tool invocation
    TOOL_RESULT = "tool_result" # Tool result
    SUBAGENT_START = "subagent_start"
    SUBAGENT_STOP = "subagent_stop"
    SIDECHAIN = "sidechain"    # Branching conversation


class TimelineNode(BaseModel):
    """A node in the timeline tree representing a conversation element."""

    # Identity
    uuid: str = Field(description="Unique identifier (from transcript uuid)")
    node_type: TimelineNodeType

    # Tree structure
    parent_uuid: Optional[str] = Field(default=None, description="Parent node UUID")
    children: List["TimelineNode"] = Field(default_factory=list)
    depth: int = Field(default=0, description="Tree depth (0 for root)")

    # Timing
    timestamp: datetime
    elapsed_ms: int = Field(default=0, description="Time since session start")
    duration_ms: Optional[int] = Field(default=None, description="Duration for this node")

    # Context
    agent_id: Optional[str] = Field(default=None, description="Owning agent ID")
    agent_type: Optional[str] = Field(default=None)
    is_sidechain: bool = Field(default=False)

    # Content (varies by type)
    tool_name: Optional[str] = Field(default=None)
    tool_use_id: Optional[str] = Field(default=None)
    content: Optional[str] = Field(default=None)
    input_data: Optional[dict] = Field(default=None)
    output_data: Optional[dict] = Field(default=None)
    is_error: bool = Field(default=False)

    # Display helpers
    intent: Optional[str] = Field(default=None, description="Inferred purpose")
    seq: int = Field(default=0, description="Flat sequence number for rendering")


# Enable self-referencing
TimelineNode.model_rebuild()
```

### 3.2 TimelineTree Container

```python
class TimelineTree(BaseModel):
    """Complete timeline tree for a test session."""

    root: TimelineNode = Field(description="Root node (session start)")

    # Indexes for efficient lookup
    by_uuid: dict[str, TimelineNode] = Field(default_factory=dict)
    by_tool_use_id: dict[str, TimelineNode] = Field(default_factory=dict)
    by_agent_id: dict[str, List[TimelineNode]] = Field(default_factory=dict)

    # Metadata
    total_nodes: int = 0
    max_depth: int = 0
    agent_count: int = 0

    def flatten(self, depth_first: bool = True) -> List[TimelineNode]:
        """Flatten tree to list for rendering, preserving order."""
        pass

    def get_agent_subtree(self, agent_id: str) -> Optional[TimelineNode]:
        """Get the subtree rooted at a specific agent."""
        pass

    def get_tool_calls_for_agent(self, agent_id: str) -> List[TimelineNode]:
        """Get all tool calls attributed to an agent."""
        pass
```

---

## 4. Proposed Algorithm for Tree Construction

### 4.1 High-Level Flow

```
                  Session Transcript                    Trace Events
                       (JSONL)                           (JSONL)
                          │                                 │
                          ▼                                 ▼
                   ┌──────────────┐                  ┌──────────────┐
                   │ Parse entries│                  │ Parse events │
                   │ with uuid,   │                  │ with tool_id,│
                   │ parentUuid   │                  │ agent_id     │
                   └──────┬───────┘                  └──────┬───────┘
                          │                                 │
                          └──────────────┬──────────────────┘
                                         │
                                         ▼
                              ┌────────────────────┐
                              │  build_uuid_index  │
                              │  (uuid → entry)    │
                              └─────────┬──────────┘
                                        │
                                        ▼
                              ┌────────────────────┐
                              │  build_tree_from   │
                              │  parentUuid chains │
                              └─────────┬──────────┘
                                        │
                                        ▼
                              ┌────────────────────┐
                              │  enrich_with_trace │
                              │  (tool_use_id →    │
                              │   agent_id)        │
                              └─────────┬──────────┘
                                        │
                                        ▼
                              ┌────────────────────┐
                              │  compute_depths    │
                              │  and assign seq    │
                              └─────────┬──────────┘
                                        │
                                        ▼
                                  TimelineTree
```

### 4.2 Detailed Algorithm

```python
def build_timeline_tree(
    transcript_entries: List[dict],
    trace_events: List[dict]
) -> TimelineTree:
    """Build a tree from transcript and trace data.

    Phase 1: Index transcript entries by uuid
    Phase 2: Build parent-child relationships from parentUuid
    Phase 3: Enrich with trace data (agent attribution)
    Phase 4: Compute depths and flatten sequence
    """

    # Phase 1: Index by uuid
    by_uuid: dict[str, dict] = {}
    for entry in transcript_entries:
        if uuid := entry.get("uuid"):
            by_uuid[uuid] = entry

    # Phase 2: Build tree structure
    nodes: dict[str, TimelineNode] = {}
    roots: List[TimelineNode] = []

    for uuid, entry in by_uuid.items():
        node = _create_node_from_entry(entry)
        nodes[uuid] = node

    # Link parents to children
    for uuid, node in nodes.items():
        parent_uuid = by_uuid[uuid].get("parentUuid")
        if parent_uuid and parent_uuid in nodes:
            parent_node = nodes[parent_uuid]
            parent_node.children.append(node)
            node.parent_uuid = parent_uuid
        elif parent_uuid is None:
            roots.append(node)

    # Phase 3: Enrich with trace data
    tool_to_agent = _build_tool_to_agent_map(trace_events)
    for node in nodes.values():
        if node.tool_use_id and node.tool_use_id in tool_to_agent:
            agent_id, agent_type = tool_to_agent[node.tool_use_id]
            node.agent_id = agent_id
            node.agent_type = agent_type

    # Phase 4: Compute depths
    def compute_depth(node: TimelineNode, depth: int):
        node.depth = depth
        for child in node.children:
            compute_depth(child, depth + 1)

    # Create root container
    root = TimelineNode(
        uuid="session-root",
        node_type=TimelineNodeType.ROOT,
        timestamp=min(n.timestamp for n in roots) if roots else datetime.min,
        children=roots
    )
    compute_depth(root, 0)

    # Phase 5: Assign flat sequence numbers (depth-first)
    seq = 0
    def assign_seq(node: TimelineNode):
        nonlocal seq
        seq += 1
        node.seq = seq
        for child in sorted(node.children, key=lambda n: n.timestamp):
            assign_seq(child)

    assign_seq(root)

    return TimelineTree(
        root=root,
        by_uuid=nodes,
        total_nodes=len(nodes),
        max_depth=max(n.depth for n in nodes.values()) if nodes else 0
    )
```

---

## 5. HTML Rendering Considerations

### 5.1 Tree Visualization Options

**Option A: Indentation-Based (Recommended)**

Visual hierarchy through CSS indentation:

```html
<div class="timeline-tree">
  <div class="timeline-node depth-0 type-prompt" data-uuid="uuid-1">
    <!-- Prompt content -->
  </div>
  <div class="timeline-node depth-0 type-tool-call" data-uuid="uuid-2">
    <!-- Tool call (main session) -->
  </div>
  <div class="timeline-node depth-1 type-subagent-start" data-uuid="uuid-3">
    <!-- Subagent start -->
  </div>
  <div class="timeline-node depth-2 type-tool-call" data-uuid="uuid-4">
    <!-- Tool call (subagent) - indented -->
  </div>
  <div class="timeline-node depth-1 type-subagent-stop" data-uuid="uuid-5">
    <!-- Subagent stop -->
  </div>
</div>
```

CSS for indentation:

```css
.timeline-node { --indent: 24px; }
.depth-0 { margin-left: 0; }
.depth-1 { margin-left: calc(1 * var(--indent)); border-left: 2px solid var(--subagent); }
.depth-2 { margin-left: calc(2 * var(--indent)); border-left: 2px solid var(--subagent); }
.depth-3 { margin-left: calc(3 * var(--indent)); border-left: 2px solid var(--subagent); }
```

**Option B: Collapsible Sections**

Group subagent activity into collapsible `<details>` elements:

```html
<details class="subagent-section" data-agent-id="agent-123">
  <summary>
    <span class="agent-badge">Explore Agent</span>
    <span class="tool-count">3 tool calls</span>
    <span class="duration">+2.5s</span>
  </summary>
  <div class="subagent-timeline">
    <!-- Nested tool calls -->
  </div>
</details>
```

### 5.2 JavaScript Enhancements

```javascript
// Filter timeline by agent
function filterByAgent(agentId) {
  document.querySelectorAll('.timeline-node').forEach(node => {
    const nodeAgent = node.dataset.agent;
    if (agentId === 'all' || nodeAgent === agentId) {
      node.style.display = 'block';
    } else {
      node.style.display = 'none';
    }
  });
}

// Highlight tool call path (from subagent up to main session)
function highlightPath(uuid) {
  document.querySelectorAll('.highlighted').forEach(el => {
    el.classList.remove('highlighted');
  });

  let current = document.querySelector(`[data-uuid="${uuid}"]`);
  while (current) {
    current.classList.add('highlighted');
    const parentUuid = current.dataset.parentUuid;
    current = parentUuid ? document.querySelector(`[data-uuid="${parentUuid}"]`) : null;
  }
}
```

---

## 6. Migration Path from Current Flat Timeline

### Phase 1: Extend Data Model (Non-Breaking)

1. Add optional fields to `TimelineEntry`:
   - `parent_uuid: str | None`
   - `depth: int = 0`
   - `is_sidechain: bool = False`

2. Update `build_timeline()` to populate these fields when available

3. Update HTML rendering to use `depth` for indentation (CSS-only change)

### Phase 2: Introduce Tree Builder (Parallel Implementation)

1. Create `TimelineNode` and `TimelineTree` models in `models.py`
2. Create `build_timeline_tree()` in `collector.py`
3. Create `TreeTimelineBuilder` alongside existing `TimelineBuilder`
4. Feature flag: `use_tree_timeline: bool` in test config

### Phase 3: Full Migration

1. Deprecate flat `build_timeline()` method
2. Update all callers to use `build_timeline_tree()`
3. Remove legacy `TimelineBuilder`
4. Update documentation

### Phase 4: Enhanced Features

1. Add subagent filtering UI
2. Add path highlighting
3. Add collapsible subagent sections
4. Export tree as JSON for external tools

---

## 7. Design Decisions

The following design decisions have been made based on review and discussion:

### 7.1 Detail Level: HIGH

**Decision:** Capture ALL information in JSON for full audit capability.

**Rationale:**
- HTML display is a separate concern - the UI can selectively choose what to display
- Future tools will depend on comprehensive data collection
- Do NOT simplify data for rendering convenience
- Full audit trail enables debugging, compliance, and future feature development

### 7.2 Depth Cap: NONE for Data

**Decision:** No artificial limits on data structure depth.

**Rationale:**
- UI can implement rendering caps if needed (collapsible sections, separate pages)
- Consider lazy-loading nested HTML fragments for deep structures
- Data structure integrity is paramount - UI adapts to data, not vice versa
- Artificial depth limits would lose valuable information about deeply nested agent interactions

### 7.3 Sidechain/Subagent Display: COLLAPSIBLE

**Decision:** Default to collapsible sections for subagents with smart defaults.

**Smart defaults for `IsCollapsed`:**
- If subagent performs >66% of tasks -> default **EXPANDED**
- Otherwise -> default **COLLAPSED**

**Rationale:**
- This is UI logic, not a data model concern
- Allows users to focus on the most relevant activity
- Preserves full detail while managing visual complexity
- Subagents doing most of the work deserve prominence

### 7.4 Missing Data Handling

**Decision:** Entries without `parentUuid` become root-level entries.

**Rationale:**
- Inferring parent from timestamp proximity reintroduces the fragility we're trying to eliminate
- Root-level orphans are visible and can be manually investigated
- Data integrity over heuristic guessing

---

## 8. Data Architecture Philosophy

### 8.1 Core Principle: Preserve Native + Augment

The timeline data architecture follows a strict principle of **preserving native Claude JSON structures while adding enrichment data alongside**.

```
┌─────────────────────────────────────────────────────────────────┐
│                     TimelineNode                                 │
├─────────────────────────────────────────────────────────────────┤
│  NATIVE DATA (preserved exactly as received)                    │
│  ├── uuid                                                        │
│  ├── parentUuid                                                  │
│  ├── toolUseID                                                   │
│  ├── parentToolUseID                                            │
│  ├── isSidechain                                                │
│  ├── type                                                        │
│  ├── timestamp                                                   │
│  └── message (full content block)                               │
├─────────────────────────────────────────────────────────────────┤
│  ENRICHMENT DATA (computed/added beside native)                 │
│  ├── node_type (classified from native type)                    │
│  ├── depth (computed from tree structure)                       │
│  ├── elapsed_ms (computed from session start)                   │
│  ├── duration_ms (computed from child timestamps)               │
│  ├── agent_id (correlated from trace events)                    │
│  ├── agent_type (correlated from trace events)                  │
│  ├── intent (inferred purpose)                                  │
│  └── seq (flat sequence for rendering)                          │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Why Preservation Over Transformation

**Avoid embedding bugs:** When you transform native data into a different structure, you risk:
- Losing information that seems unimportant now but matters later
- Introducing mapping errors that are hard to debug
- Creating drift between what Claude produces and what we store

**Design for regeneration:** The JSON data should be sufficient to generate any UI after the fact:
- HTML report is just the first application of this data
- Future applications: CLI viewers, VS Code extensions, API endpoints, diff tools
- Each consumer picks what it needs from the comprehensive data

### 8.3 Augmentation Strategy

Enrichment data is added **beside** native data, never replacing it:

```python
# GOOD: Add enrichment alongside native data
node = TimelineNode(
    # Native (preserved exactly)
    uuid=entry["uuid"],
    parent_uuid=entry.get("parentUuid"),
    tool_use_id=entry.get("toolUseID"),
    is_sidechain=entry.get("isSidechain", False),
    timestamp=parse_timestamp(entry["timestamp"]),
    native_message=entry.get("message"),  # Full original content

    # Enrichment (computed/added)
    node_type=classify_node_type(entry),
    depth=0,  # Computed later
    agent_id=None,  # Correlated from trace
    intent=infer_intent(entry),
)

# BAD: Transform native data
node = TimelineNode(
    id=entry["uuid"],  # Renamed field - loses original field name
    parent=entry.get("parentUuid"),  # Renamed field
    content=extract_text(entry["message"]),  # Transformed - loses original structure
)
```

### 8.4 UI as Data Consumer

The HTML viewer (and any future UI) is a **consumer** of the data, not a **driver** of data structure:

| Principle | Implementation |
|-----------|----------------|
| Data completeness first | Store everything; UI picks what to show |
| UI adapts to data | Deep nesting? UI adds collapsible sections |
| No data model changes for UI | UI can filter, but data model stays comprehensive |
| Multiple UIs, one data model | Same JSON feeds HTML, CLI, API, etc. |

### 8.5 Practical Implications

1. **JSON schema is stable:** Adding new UI features doesn't require data model changes
2. **Debugging is straightforward:** Native data is always available for comparison with source
3. **Future-proof:** New tools can access data we're collecting now but not yet using
4. **Audit-ready:** Full trail of what Claude actually produced

---

## 9. Implementation Notes

### 9.1 Performance Considerations

For large sessions (1000+ entries):
- Build full tree upfront (data integrity over lazy loading)
- UI can lazy-load HTML fragments for deep subtrees
- Index structures (`by_uuid`, `by_tool_use_id`, `by_agent_id`) enable O(1) lookups

### 9.2 Backward Compatibility

- JSON report schema will include tree structure alongside existing flat timeline
- Existing consumers continue working with flat timeline
- New consumers can use tree structure
- Eventual deprecation of flat timeline after migration period

### 9.3 Test Fixtures Required

Validate tree construction for:
- Simple sessions (no subagents)
- Single subagent
- Nested subagents (agent spawns another agent)
- Concurrent subagents (multiple agents running simultaneously)
- Sessions with missing `parentUuid` entries (orphan handling)

---

## 10. Critical Files for Implementation

| File | Purpose |
|------|---------|
| `test-packages/harness/models.py` | Add `TimelineNode` and `TimelineTree` models |
| `test-packages/harness/collector.py` | Add `build_timeline_tree()` and modify correlation logic |
| `test-packages/harness/html_report/components/timeline.py` | Update rendering for tree structure |
| `test-packages/harness/tests/test_collector.py` | Add tests for tree construction |

---

## 11. References

- **Current Implementation**: `collector.py:correlate_tool_calls_with_agents()` (lines 453-543)
- **HTML Report Design**: `test-packages/docs/html-report-builder-design.md`
- **Example Artifacts**: `test-packages/reports/sc-startup/` (session.jsonl, trace.jsonl)
