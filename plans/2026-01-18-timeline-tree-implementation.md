# Timeline Tree Architecture Implementation Plan

**Date:** 2026-01-18
**Design Doc:** [timeline-tree-architecture-design.md](../test-packages/docs/timeline-tree-architecture-design.md)
**Schemas:** [schemas.py](../test-packages/harness/schemas.py)
**Worktree:** `/Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/timeline-tree-architecture`

---

## Overview

This plan implements the timeline tree architecture as specified in the design document. The current flat timeline loses hierarchical relationships between parent agents and their tool calls. The new architecture uses Claude's `parentUuid` field from transcripts to build accurate parent-child relationships, preserves native Claude JSON structures, and generates enriched data files alongside the raw artifacts.

**Key Deliverables:**
1. Rename artifact files from `-session.jsonl` to `-transcript.jsonl` (design doc alignment)
2. Create `enrichment.py` module for tree construction
3. Generate `-enriched.json` files with full tree structure
4. Update HTML timeline rendering with depth-based indentation
5. Add collapsible sections for subagent activity

---

## Sprint 1: Artifact Storage Refactor

**Goal:** Update artifact preservation to use new file naming and ensure native transcript is stored untouched.

### Parallel Agents

#### Agent 1A: Update `_preserve_artifacts()` in `pytest_plugin.py`

**Tasks:**
1. Rename `-session.jsonl` to `-transcript.jsonl` (line ~1533)
2. Ensure native Claude transcript entries are written verbatim (no transformation)
3. Update artifact path references throughout the function
4. Update `_cleanup_history_folders()` if needed for new naming

**Files Modified:**
- `test-packages/harness/pytest_plugin.py` (lines 1480-1614)

**Code Changes:**
```python
# Change from:
dest_name = f"{test_id}-session.jsonl"
# Change to:
dest_name = f"{test_id}-transcript.jsonl"
```

#### Agent 1B: Update tests referencing old artifact names

**Tasks:**
1. Search for references to `-session.jsonl` in test files
2. Update any assertions or path references to use `-transcript.jsonl`
3. Verify existing tests still pass with new naming

**Files to Check:**
- `test-packages/harness/tests/test_collector.py`
- `test-packages/harness/tests/test_pytest_report_integration.py`
- Any fixture files referencing artifact names

### QA Gate

```bash
cd /Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/timeline-tree-architecture

# Run harness unit tests
python -m pytest test-packages/harness/tests/ -v

# Run a quick fixture test to verify artifact naming
python -m pytest test-packages/fixtures/sc-startup/ -v -k "help"

# Verify artifact naming in reports folder
ls -la test-packages/reports/sc-startup/*.jsonl 2>/dev/null | head -5
```

**Deliverable:** PR to develop, then develop -> main

---

## Sprint 2: Enrichment Generator Module

**Goal:** Create the enrichment module that builds tree structure from transcript + trace data.

### Parallel Agents

#### Agent 2A: Create `test-packages/harness/enrichment.py`

**Tasks:**
1. Create new module with `build_timeline_tree()` function
2. Implement Phase 1: Index transcript entries by `uuid`
3. Implement Phase 2: Build parent-child relationships from `parentUuid`
4. Implement Phase 3: Enrich with trace data (agent attribution via `tool_use_id`)
5. Implement Phase 4: Compute depths and assign sequence numbers
6. Return `EnrichedData` Pydantic model from `schemas.py`

**Key Functions to Implement:**
```python
def build_timeline_tree(
    transcript_entries: List[dict],
    trace_events: List[dict],
    test_context: TestContext,
    artifact_paths: ArtifactPaths,
) -> EnrichedData:
    """Build enriched data with tree structure from raw transcript and trace."""
    ...

def _create_tree_node(entry: dict) -> TreeNode:
    """Create a TreeNode from a transcript entry."""
    ...

def _classify_node_type(entry: dict) -> TimelineNodeType:
    """Classify the node type based on transcript entry type."""
    ...

def _build_tool_to_agent_map(trace_events: List[dict]) -> Dict[str, Tuple[str, str]]:
    """Build mapping from tool_use_id to (agent_id, agent_type)."""
    ...

def _compute_tree_stats(nodes: Dict[str, TreeNode], agents: Dict[str, AgentSummary]) -> TreeStats:
    """Compute summary statistics for the tree."""
    ...
```

**Files Created:**
- `test-packages/harness/enrichment.py`

#### Agent 2B: Create tests for enrichment module

**Tasks:**
1. Create `test-packages/harness/tests/test_enrichment.py`
2. Test tree building from sample transcript/trace data
3. Test `parentUuid` chain resolution
4. Test agent correlation via `tool_use_id`
5. Test stats calculation
6. Test orphan handling (entries without `parentUuid`)
7. Test edge cases: empty transcript, empty trace, missing fields

**Test Fixtures Needed:**
```python
# Sample transcript with parentUuid chains
SAMPLE_TRANSCRIPT = [
    {"uuid": "uuid-1", "parentUuid": None, "type": "user", ...},
    {"uuid": "uuid-2", "parentUuid": "uuid-1", "type": "assistant", ...},
    {"uuid": "uuid-3", "parentUuid": "uuid-2", "type": "tool_use", "toolUseID": "toolu_01ABC", ...},
    {"uuid": "uuid-4", "parentUuid": "uuid-3", "type": "tool_result", ...},
]

# Sample trace with agent correlation
SAMPLE_TRACE = [
    {"event": "SubagentStart", "agent_id": "a123", "agent_type": "Explore", ...},
    {"event": "PreToolUse", "tool_use_id": "toolu_01ABC", "ppid": 12345, ...},
    {"event": "PostToolUse", "tool_use_id": "toolu_01ABC", ...},
    {"event": "SubagentStop", "agent_id": "a123", ...},
]
```

**Files Created:**
- `test-packages/harness/tests/test_enrichment.py`

### QA Gate

```bash
cd /Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/timeline-tree-architecture

# Run enrichment tests specifically
python -m pytest test-packages/harness/tests/test_enrichment.py -v

# Run all harness tests to ensure no regression
python -m pytest test-packages/harness/tests/ -v
```

**Deliverable:** PR to develop, then develop -> main

---

## Sprint 3: Integration with Artifact Preservation

**Goal:** Generate `enriched.json` as part of artifact preservation flow.

### Parallel Agents

#### Agent 3A: Update `_preserve_artifacts()` to call enrichment

**Tasks:**
1. Import enrichment module in `pytest_plugin.py`
2. After writing transcript and trace, call `build_timeline_tree()`
3. Build `TestContext` from test result data
4. Build `ArtifactPaths` with relative paths
5. Write `enriched.json` with full `EnrichedData` structure
6. Add error handling (don't fail test if enrichment fails)

**Code Integration Point (after line ~1562):**
```python
# Write enriched.json
try:
    from .enrichment import build_timeline_tree
    from .schemas import TestContext, TestContextPaths, ArtifactPaths

    test_context = TestContext(
        fixture_id=fixture_name,
        test_id=test_id,
        test_name=test_config.test_name,
        package=fixture_config.package if fixture_config else "",
        paths=TestContextPaths(
            fixture_yaml=str(fixture_config.source_path) if fixture_config else "",
            test_yaml=str(test_config.source_path) if test_config else "",
        )
    )

    artifact_paths = ArtifactPaths(
        transcript=f"{fixture_name}/{test_id}-transcript.jsonl",
        trace=f"{fixture_name}/{test_id}-trace.jsonl",
        enriched=f"{fixture_name}/{test_id}-enriched.json",
    )

    enriched_data = build_timeline_tree(
        transcript_entries=entries,
        trace_events=events,
        test_context=test_context,
        artifact_paths=artifact_paths,
    )

    # Write enriched.json
    dest_name = f"{test_id}-enriched.json"
    for dest_dir in [latest_dir, history_dir]:
        dest_path = dest_dir / dest_name
        with open(dest_path, "w") as f:
            f.write(enriched_data.model_dump_json(indent=2))
        logger.debug(f"Preserved enriched data: {dest_path}")

except Exception as e:
    logger.warning(f"Failed to generate enriched data for {test_id}: {e}")
```

**Files Modified:**
- `test-packages/harness/pytest_plugin.py`

#### Agent 3B: Ensure collector exposes raw data needed

**Tasks:**
1. Verify `CollectedData.raw_transcript_entries` is populated correctly
2. Verify `CollectedData.raw_hook_events` is populated correctly
3. Add any missing data needed for enrichment
4. Ensure data is not transformed before storage

**Verification Points in `collector.py`:**
- Line 695: `data.raw_hook_events = hook_events` (verify untransformed)
- Line 725: `data.raw_transcript_entries = transcript_entries` (verify untransformed)

**Files Modified:**
- `test-packages/harness/collector.py` (if changes needed)

### QA Gate

```bash
cd /Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/timeline-tree-architecture

# Run a fixture test that generates artifacts
python -m pytest test-packages/fixtures/sc-startup/ -v -k "init"

# Verify enriched.json exists
ls -la test-packages/reports/sc-startup/*-enriched.json

# Validate schema
python -c "
from test_packages.harness.schemas import EnrichedData
import json
import glob

for path in glob.glob('test-packages/reports/sc-startup/*-enriched.json'):
    with open(path) as f:
        data = EnrichedData.model_validate(json.load(f))
        print(f'{path}: OK - {data.stats.total_nodes} nodes, depth {data.stats.max_depth}')
"
```

**Deliverable:** PR to develop, then develop -> main

---

## Sprint 4: Fixture Report Integration

**Goal:** Include tree structure and artifact paths in fixture report (`sc-startup.json`).

### Parallel Agents

#### Agent 4A: Update `reporter.py` to include tree in TestResult

**Tasks:**
1. Add `timeline_tree` field to TestResult building in `ReportBuilder`
2. Add `artifacts` paths to TestResult
3. Load enriched data if available when building report
4. Populate tree structure from enriched data
5. Handle missing enriched data gracefully

**Files Modified:**
- `test-packages/harness/reporter.py`

#### Agent 4B: Update models with new optional fields

**Tasks:**
1. Add `timeline_tree: Optional[TimelineTree]` to `TestResult` model
2. Add `artifacts: Optional[ArtifactPaths]` to `TestResult` model
3. Ensure backward compatibility (fields are optional)
4. Update `FixtureReport` if needed

**Fields to Add to `models.py`:**
```python
class TestResult(BaseModel):
    # ... existing fields ...

    # New optional fields for tree architecture
    timeline_tree: Optional[TimelineTree] = None
    artifacts: Optional[ArtifactPaths] = None
```

**Files Modified:**
- `test-packages/harness/models.py`

### QA Gate

```bash
cd /Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/timeline-tree-architecture

# Run fixture tests
python -m pytest test-packages/fixtures/sc-startup/ -v

# Verify fixture report has new fields
python -c "
import json
with open('test-packages/reports/sc-startup.json') as f:
    data = json.load(f)
    for test in data.get('tests', []):
        has_tree = 'timeline_tree' in test or test.get('timeline_tree') is not None
        has_artifacts = 'artifacts' in test or test.get('artifacts') is not None
        print(f\"{test['test_id']}: tree={has_tree}, artifacts={has_artifacts}\")
"
```

**Deliverable:** PR to develop, then develop -> main

---

## Sprint 5: HTML Rendering Updates

**Goal:** Update HTML timeline to use tree structure with indentation and collapsible subagent sections.

### Parallel Agents

#### Agent 5A: Update timeline component for tree rendering

**Tasks:**
1. Update `TimelineBuilder` to accept tree structure data
2. Add depth-based CSS classes (`depth-0`, `depth-1`, etc.)
3. Add `data-uuid` and `data-parent-uuid` attributes to timeline items
4. Add `data-agent-id` attribute for filtering
5. Wrap subagent tool calls in `<details>` elements
6. Implement smart collapse defaults (expand if >66% of activity)

**Key Changes to `timeline.py`:**
```python
def _build_timeline_item(self, entry: TimelineItemDisplayModel) -> str:
    # Add depth class for indentation
    depth_class = f"depth-{entry.depth}" if hasattr(entry, 'depth') else "depth-0"

    # Add agent-id for filtering
    agent_attr = f'data-agent-id="{entry.agent_id}"' if entry.agent_id else ''
    uuid_attr = f'data-uuid="{entry.uuid}"' if hasattr(entry, 'uuid') else ''

    return f'''<div class="timeline-item {type_display.css_class} {depth_class}"
        data-seq="{entry.seq}"
        data-elapsed="{entry.elapsed_ms}ms"
        {agent_attr}
        {uuid_attr}>
        ...
    </div>'''
```

**Files Modified:**
- `test-packages/harness/html_report/components/timeline.py`
- `test-packages/harness/html_report/models.py` (add depth, uuid fields to display model)

#### Agent 5B: Update CSS styles for depth indentation

**Tasks:**
1. Add indentation CSS for depth levels 0-5+
2. Add left border styling for subagent context
3. Add subagent section header styles
4. Add collapsible section hover states
5. Add smooth transition animations

**New CSS to add to `styles.py`:**
```python
CSS_TIMELINE_TREE = """/* Timeline tree depth indentation */
.timeline-item.depth-0 { margin-left: 0; }
.timeline-item.depth-1 { margin-left: 24px; border-left: 2px solid #8b5cf6; padding-left: 12px; }
.timeline-item.depth-2 { margin-left: 48px; border-left: 2px solid #a78bfa; padding-left: 12px; }
.timeline-item.depth-3 { margin-left: 72px; border-left: 2px solid #c4b5fd; padding-left: 12px; }
.timeline-item.depth-4 { margin-left: 96px; border-left: 2px solid #ddd6fe; padding-left: 12px; }
.timeline-item.depth-5 { margin-left: 120px; border-left: 2px solid #ede9fe; padding-left: 12px; }

/* Subagent section collapsible */
.subagent-section {
  margin: 8px 0;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-subtle);
}
.subagent-section > summary {
  padding: 8px 12px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 500;
}
.subagent-section > summary:hover {
  background: rgba(139, 92, 246, 0.1);
}
.agent-badge {
  background: #8b5cf6;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}
.tool-count {
  color: var(--text-muted);
  font-size: 0.85rem;
}
.subagent-duration {
  font-family: monospace;
  font-size: 0.8rem;
  color: var(--text-muted);
}

/* Timeline item dot colors for subagent context */
.timeline-item.depth-1 .timeline-dot,
.timeline-item.depth-2 .timeline-dot,
.timeline-item.depth-3 .timeline-dot {
  border-color: #8b5cf6;
}

/* Highlighted path for debugging */
.timeline-item.highlighted {
  background: rgba(59, 130, 246, 0.1);
  border-left-color: #3b82f6 !important;
}"""
```

**Files Modified:**
- `test-packages/harness/html_report/assets/styles.py`

#### Agent 5C: Update JavaScript for interactivity

**Tasks:**
1. Add `filterByAgent(agentId)` function
2. Add `highlightPath(uuid)` function for debugging
3. Add collapse/expand all functionality
4. Add agent filter dropdown builder
5. Persist filter state in sessionStorage

**New JavaScript to add to `scripts.py`:**
```javascript
// Filter timeline by agent
function filterByAgent(agentId) {
  document.querySelectorAll('.timeline-item').forEach(node => {
    const nodeAgent = node.dataset.agentId;
    if (agentId === 'all' || nodeAgent === agentId || !nodeAgent) {
      node.style.display = 'block';
    } else {
      node.style.display = 'none';
    }
  });
  // Persist selection
  sessionStorage.setItem('timelineAgentFilter', agentId);
}

// Highlight path from node up to root
function highlightPath(uuid) {
  // Clear existing highlights
  document.querySelectorAll('.highlighted').forEach(el => {
    el.classList.remove('highlighted');
  });

  // Highlight path to root
  let current = document.querySelector(`[data-uuid="${uuid}"]`);
  while (current) {
    current.classList.add('highlighted');
    const parentUuid = current.dataset.parentUuid;
    current = parentUuid ? document.querySelector(`[data-uuid="${parentUuid}"]`) : null;
  }
}

// Collapse/expand all subagent sections
function toggleAllSubagents(expand) {
  document.querySelectorAll('.subagent-section').forEach(section => {
    section.open = expand;
  });
}

// Build agent filter dropdown
function buildAgentFilter(containerId) {
  const agents = new Set();
  document.querySelectorAll('[data-agent-id]').forEach(el => {
    if (el.dataset.agentId) {
      agents.add(el.dataset.agentId);
    }
  });

  if (agents.size === 0) return;

  const container = document.getElementById(containerId);
  if (!container) return;

  const select = document.createElement('select');
  select.className = 'agent-filter-select';
  select.innerHTML = '<option value="all">All Agents</option>';
  agents.forEach(agent => {
    select.innerHTML += `<option value="${agent}">${agent}</option>`;
  });
  select.onchange = () => filterByAgent(select.value);
  container.appendChild(select);

  // Restore persisted selection
  const saved = sessionStorage.getItem('timelineAgentFilter');
  if (saved && agents.has(saved)) {
    select.value = saved;
    filterByAgent(saved);
  }
}
```

**Files Modified:**
- `test-packages/harness/html_report/assets/scripts.py`
- `test-packages/harness/html_report/builder.py` (to include agent filter container)

### QA Gate

```bash
cd /Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/timeline-tree-architecture

# Run fixture test with subagent activity (if available)
python -m pytest test-packages/fixtures/sc-startup/ -v -k "init"

# Open HTML report for manual verification
open test-packages/reports/sc-startup.html

# Manual verification checklist:
# - [ ] Timeline shows indentation for subagent tool calls
# - [ ] Subagent sections are collapsible
# - [ ] Agent filter dropdown appears if multiple agents
# - [ ] Highlight path works when clicking a node
# - [ ] Collapse/expand all works
```

**Deliverable:** PR to develop, then develop -> main

---

## Sprint 6: Schema Validation & Documentation

**Goal:** Add runtime schema validation and update documentation.

### Parallel Agents

#### Agent 6A: Add schema validation to artifact preservation

**Tasks:**
1. Validate `enriched.json` against `EnrichedData` schema before writing
2. Add lenient validation for Claude transcript (log warnings, don't fail)
3. Add validation test for trace events against `HookEvent` schema
4. Log validation warnings but don't fail test execution
5. Add metrics for schema validation success rate

**Code to add in `_preserve_artifacts()`:**
```python
# Validate enriched data before writing
try:
    EnrichedData.model_validate(enriched_data.model_dump())
    logger.debug(f"Schema validation passed for {test_id}")
except ValidationError as e:
    logger.warning(f"Enriched data schema validation failed for {test_id}: {e}")

# Lenient validation for Claude transcript entries
from .schemas import ClaudeTranscriptEntry
for i, entry in enumerate(entries[:5]):  # Sample first 5
    try:
        ClaudeTranscriptEntry.model_validate(entry)
    except ValidationError as e:
        logger.debug(f"Transcript entry {i} has extra/missing fields: {e}")
```

**Files Modified:**
- `test-packages/harness/pytest_plugin.py`

#### Agent 6B: Update documentation

**Tasks:**
1. Update `test-packages/docs/report-artifacts.md` with new structure
2. Add examples of `-enriched.json` format
3. Document tree node types and their meanings
4. Add section on regenerating enriched data
5. Update `pm/PQA.md` if test harness documentation exists there

**Documentation Structure:**
```markdown
# Report Artifacts

## File Structure

After running tests, the following artifacts are generated:

```
reports/
├── {fixture-name}.html          # HTML report
├── {fixture-name}.json          # JSON fixture report
└── {fixture-name}/              # Artifacts folder
    ├── {test-id}-transcript.jsonl   # Native Claude session (UNTOUCHED)
    ├── {test-id}-trace.jsonl        # Hook events (our instrumentation)
    ├── {test-id}-enriched.json      # Tree structure + metadata
    ├── {test-id}-claude-cli.txt     # CLI output
    └── {test-id}-pytest.txt         # Pytest output
```

## Enriched Data Structure

The `-enriched.json` file contains:
- `test_context`: Test identification and source paths
- `artifacts`: Relative paths to all artifact files
- `tree`: Hierarchical structure with `root_uuid` and `nodes` map
- `agents`: Summary of subagent activity
- `stats`: Quick-access metrics (total_nodes, max_depth, etc.)

...
```

**Files Modified/Created:**
- `test-packages/docs/report-artifacts.md` (update or create)
- `test-packages/docs/timeline-tree-architecture-design.md` (add examples section)

### QA Gate

```bash
cd /Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/timeline-tree-architecture

# Run full test suite
python -m pytest test-packages/ -v

# Verify all tests pass
python -m pytest test-packages/harness/tests/ -v
python -m pytest test-packages/fixtures/ -v

# Check documentation links are valid
# (manual review of markdown files)
```

**Deliverable:** PR to develop, then develop -> main

---

## Execution Notes

### Agent Parallelization

- Within each sprint, agents A/B/C can run in parallel
- Sprints must be sequential (each builds on previous)
- Use worktree: `/Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/timeline-tree-architecture`

### Worktree Setup

```bash
# Create worktree from develop branch
cd /Users/randlee/Documents/github/synaptic-canvas
git worktree add ../synaptic-canvas-worktrees/feature/timeline-tree-architecture develop
cd ../synaptic-canvas-worktrees/feature/timeline-tree-architecture
git checkout -b feature/timeline-tree-architecture
```

### QA Process

1. All unit tests pass: `pytest test-packages/harness/tests/ -v`
2. Fixture tests pass: `pytest test-packages/fixtures/ -v`
3. Schema validation passes for generated artifacts
4. Manual HTML report review (Sprint 5)

### PR Strategy

- Each sprint = 1 PR to develop
- After QA passes on develop, PR develop -> main
- Use conventional commits:
  - `feat(harness): add enrichment module for timeline tree`
  - `test(harness): add enrichment unit tests`
  - `docs(harness): update report artifacts documentation`
  - `refactor(harness): rename artifact files to match design`

### Rollback Plan

- Each sprint is self-contained
- Can revert sprint PR if issues found
- Worktree allows isolated development
- Enriched files are regenerable from source artifacts

---

## Timeline Estimate

| Sprint | Description | Agents | Estimated Effort | Dependencies |
|--------|-------------|--------|------------------|--------------|
| 1 | Artifact Storage Refactor | 2 parallel | Small (1-2 hours) | None |
| 2 | Enrichment Generator | 2 parallel | Medium (3-4 hours) | Sprint 1 |
| 3 | Artifact Integration | 2 parallel | Medium (2-3 hours) | Sprint 2 |
| 4 | Fixture Report Integration | 2 parallel | Small (1-2 hours) | Sprint 3 |
| 5 | HTML Rendering Updates | 3 parallel | Large (4-6 hours) | Sprint 4 |
| 6 | Validation & Docs | 2 parallel | Small (1-2 hours) | Sprint 5 |

**Total Estimated Effort:** 12-19 hours across all agents

---

## Success Criteria

1. **All existing tests continue to pass** - No regression in current functionality
2. **New `-transcript.jsonl` naming** - Artifact files follow design doc naming
3. **`-enriched.json` files generated** - Every test produces enriched data
4. **Schema validation** - All generated files validate against Pydantic schemas
5. **Tree structure accuracy** - `parentUuid` chains correctly resolved
6. **Agent correlation** - Tool calls correctly attributed to subagents
7. **HTML indentation** - Timeline visually shows depth hierarchy
8. **Collapsible sections** - Subagent activity can be collapsed/expanded
9. **Documentation complete** - All new artifacts documented

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Claude transcript schema changes | Use `extra="allow"` in Pydantic models; log warnings |
| Missing `parentUuid` in transcripts | Treat as root-level entries (per design doc) |
| Performance with large transcripts | Build full tree upfront; UI lazy-loads |
| Breaking existing reports | All new fields are optional; backward compatible |
| Enrichment fails | Log warning and continue; don't fail test |

---

## References

- **Design Document:** `test-packages/docs/timeline-tree-architecture-design.md`
- **Schema Definitions:** `test-packages/harness/schemas.py`
- **Current Implementation:**
  - `collector.py:correlate_tool_calls_with_agents()` (lines 454-544)
  - `pytest_plugin.py:_preserve_artifacts()` (lines 1480-1614)
  - `html_report/components/timeline.py`
  - `html_report/assets/styles.py`
