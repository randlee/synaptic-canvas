# Timeline Tree Architecture Implementation Plan

**Date:** 2026-01-18
**Design Doc:** [timeline-tree-architecture-design.md](../test-packages/docs/timeline-tree-architecture-design.md)
**Schemas:** [schemas.py](../test-packages/harness/schemas.py)
**Worktree:** `/Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/timeline-tree-architecture`
**Branch:** `feature/timeline-tree-architecture` (based on `develop`)
**PRs:** [#31](https://github.com/randlee/synaptic-canvas/pull/31) (Sprints 1-6, merged), [#32](https://github.com/randlee/synaptic-canvas/pull/32) (Sprint 7)

---

## Progress Tracker

| Sprint | Status | Commit | Date | Notes |
|--------|--------|--------|------|-------|
| 1 | ✅ Complete | `112e8ab` | 2026-01-18 | Renamed `-session.jsonl` to `-transcript.jsonl` |
| 2 | ✅ Complete | `c875bb0` | 2026-01-18 | Created `enrichment.py` module + 38 tests |
| 3 | ✅ Complete | `c6b98f8` | 2026-01-18 | Integrated enrichment into artifact preservation |
| 4 | ✅ Complete | `702ef4e` | 2026-01-18 | Added timeline_tree + artifacts to TestResult |
| 5 | ✅ Complete | `dc100f1` | 2026-01-18 | Timeline tree HTML + CSS + JS |
| 6 | ✅ Complete | `9d9bc5d` | 2026-01-18 | Schema validation & documentation |
| 7 | ✅ Complete | `b79ed0b` | 2026-01-19 | Token consumption reporting |
| 8 | ⏳ Pending | - | - | Result[T,E] error handling pattern |
| 9 | ⏳ Pending | - | - | Log analysis & warning detection |
| 10 | ⏳ Pending | - | - | Collapsible subagent sections (HTML) |
| 11 | ⏳ Pending | - | - | Test coverage gaps (HIGH priority) |

**Current Test Count:** 505 tests (485 + 20 token extraction tests)

**Active PR:** [#32](https://github.com/randlee/synaptic-canvas/pull/32) (Sprint 7)

---

## Session Startup Checklist

When starting a new session to work on this plan:

```bash
# 1. Verify worktree exists and is clean
cd /Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/timeline-tree-architecture
git status

# 2. Sync with develop (get any merged PRs)
git fetch origin
git merge origin/develop

# 3. Verify tests pass before starting work
python -m pytest test-packages/harness/tests/ -v --tb=short
```

**Context files to read:**
- `pm/PQA.md` - Role and responsibilities
- `plans/2026-01-18-timeline-tree-implementation.md` - This plan
- `test-packages/docs/timeline-tree-architecture-design.md` - Technical design

---

## Agent Execution Model

**IMPORTANT: All implementation work should be done by BACKGROUND AGENTS.**

For each sprint:
1. Launch parallel background agents (one per Agent task listed)
2. Each agent works in the worktree at `/Users/randlee/Documents/github/synaptic-canvas-worktrees/feature/timeline-tree-architecture`
3. Wait for all parallel agents to complete
4. Run QA gate checks
5. If QA passes: commit, push, create PR
6. If QA fails: debug with additional agents

**Example agent launch for Sprint 1:**
```
Task tool with subagent_type="general-purpose", run_in_background=true:
- Agent 1A: "Implement Sprint 1 Agent 1A tasks from timeline-tree-implementation.md..."
- Agent 1B: "Implement Sprint 1 Agent 1B tasks from timeline-tree-implementation.md..."
```

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

## Sprint 1: Artifact Storage Refactor ✅

**Status:** Complete (2026-01-18)
**Commit:** `112e8ab` - `refactor(harness): rename -session.jsonl artifacts to -transcript.jsonl`

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

**Files Modified (Sprint 1):**
- `test-packages/harness/pytest_plugin.py` - Artifact file naming
- `test-packages/harness/collector.py` - Docstrings
- `test-packages/harness/models.py` - Section comment
- `test-packages/harness/tests/test_environment.py` - Test fixtures
- `test-packages/conftest.py` - Sample trace events
- `test-packages/docs/report-artifacts.md` - Documentation
- `test-packages/docs/timeline-tree-architecture-design.md` - Design doc reference

---

## Sprint 2: Enrichment Generator Module ✅

**Status:** Complete (2026-01-18)
**Commit:** `c875bb0` - `feat(harness): add enrichment module for timeline tree building`

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

**Files Created (Sprint 2):**
- `test-packages/harness/enrichment.py` (12,922 bytes) - Main enrichment module
- `test-packages/harness/tests/test_enrichment.py` (38 tests) - Test suite

**Functions Implemented:**
- `build_timeline_tree()` - Main entry point returning `EnrichedData`
- `_classify_node_type()` - Classify transcript entries as PROMPT/RESPONSE/TOOL_CALL/TOOL_RESULT
- `_build_tool_to_agent_map()` - Correlate `tool_use_id` to subagent context
- `_compute_tree_stats()` - Calculate total_nodes, max_depth, agent_count, tool_call_count
- `_compute_depths()` - Recursively compute node depths
- `_build_agent_summaries()` - Build AgentSummary objects from trace events

**Test Coverage (38 tests):**
- Basic tree building (5 tests)
- parentUuid chain resolution (4 tests)
- Agent correlation via tool_use_id (5 tests)
- Stats calculation (5 tests)
- Orphan handling (3 tests)
- Node type classification (5 tests)
- Edge cases (9 tests)
- Schema validation (2 tests)

---

## Sprint 3: Integration with Artifact Preservation ✅

**Status:** Complete (2026-01-18)
**Commit:** `c6b98f8` - `feat(harness): integrate enrichment into artifact preservation`

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

## Sprint 4: Fixture Report Integration ✅

**Status:** Complete (2026-01-18)
**Commit:** `702ef4e` - `feat(harness): add timeline_tree and artifacts fields to fixture reports`

**Goal:** Include tree structure and artifact paths in fixture report (`sc-startup.json`).

**Files Modified (Sprint 4):**
- `test-packages/harness/models.py` - Added `timeline_tree` and `artifacts` optional fields to `TestResult`
- `test-packages/harness/reporter.py` - Added enriched data loading in `ReportBuilder.build_test_result()`
- `test-packages/harness/tests/test_report_parity.py` - Updated field mappings for new fields

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

## Sprint 5: HTML Rendering Updates ✅

**Status:** Complete (2026-01-18)
**Commit:** `dc100f1` - `feat(harness): add timeline tree HTML rendering with depth indentation`

**Goal:** Update HTML timeline to use tree structure with indentation and collapsible subagent sections.

**Files Modified (Sprint 5):**
- `test-packages/harness/html_report/models.py` - Added `depth`, `uuid`, `parent_uuid` fields to `TimelineItemDisplayModel`
- `test-packages/harness/html_report/components/timeline.py` - Added depth classes and data attributes to timeline items
- `test-packages/harness/html_report/assets/styles.py` - Added `CSS_TIMELINE_TREE` (depth indentation, subagent styles)
- `test-packages/harness/html_report/assets/scripts.py` - Added `JS_TIMELINE_TREE` (filterByAgent, highlightPath, toggleAllSubagents)
- `test-packages/harness/tests/html_report/test_components.py` - Updated test expectations for depth class

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

## Sprint 7: Token Consumption Reporting ✅

**Status:** Complete (2026-01-19)
**Commit:** `b79ed0b` - `feat(harness): add token consumption reporting (Sprint 7)`
**PR:** [#32](https://github.com/randlee/synaptic-canvas/pull/32)

**Goal:** Extract and display token usage from Claude transcripts for cost analysis and performance comparison.

### Data Source

Token data is already present in `-transcript.jsonl` files:

```json
// In assistant messages (message.usage)
{
  "input_tokens": 46,
  "output_tokens": 9,
  "cache_creation_input_tokens": 15466,
  "cache_read_input_tokens": 99728
}

// In subagent results (toolUseResult)
{
  "totalTokens": 11414,
  "totalToolUseCount": 15
}
```

### Parallel Agents

#### Agent 7A: Token extraction and schema updates

**Tasks:**
1. Create `TokenUsage` model in `schemas.py` with detailed breakdown:
   ```python
   class TokenUsage(BaseModel):
       input_tokens: int = 0
       output_tokens: int = 0
       cache_creation_tokens: int = 0
       cache_read_tokens: int = 0
       subagent_tokens: int = 0

       @property
       def total_billable(self) -> int:
           """Tokens likely billed (excludes cache reads)."""
           return self.input_tokens + self.output_tokens + self.cache_creation_tokens
   ```
2. Add `extract_token_usage()` function to `collector.py`
3. Add `token_usage: Optional[TokenUsage]` to `TreeStats`
4. Wire extraction into `enrichment.py`

**Files Modified:**
- `test-packages/harness/schemas.py`
- `test-packages/harness/collector.py`
- `test-packages/harness/enrichment.py`

#### Agent 7B: HTML report display

**Tasks:**
1. Add token display to status banner: `Input: 46 | Output: 9 | Total: 126,663`
2. Add detailed breakdown section (collapsible):
   - Input tokens
   - Output tokens
   - Cache creation tokens
   - Cache read tokens
   - Subagent tokens
   - Total / Billable total
3. Add CSS styling for token display
4. Update `StatusBannerDisplayModel` and builder

**Files Modified:**
- `test-packages/harness/html_report/models.py`
- `test-packages/harness/html_report/builder.py`
- `test-packages/harness/html_report/components/status_banner.py`
- `test-packages/harness/html_report/assets/styles.py`

#### Agent 7C: Tests for token extraction

**Tasks:**
1. Create `test_token_extraction.py` with tests for:
   - Basic token aggregation from transcript
   - Subagent token aggregation
   - Empty transcript handling
   - Missing usage fields handling
2. Integration test: transcript → enriched → HTML with token display

**Files Created:**
- `test-packages/harness/tests/test_token_extraction.py`

### QA Gate

```bash
# Verify token extraction
python -c "
from test_packages.harness.collector import extract_token_usage
import json
with open('test-packages/reports/sc-startup/sc-startup-init-001-transcript.jsonl') as f:
    entries = [json.loads(line) for line in f]
tokens = extract_token_usage(entries)
print(f'Input: {tokens.input_tokens}, Output: {tokens.output_tokens}, Total: {tokens.total_billable}')
"

# Run fixture test and verify HTML shows tokens
pytest test-packages/fixtures/sc-startup/ -v -k "init" --open-report
```

**Files Created (Sprint 7):**
- `test-packages/harness/tests/test_token_extraction.py` - 20 comprehensive tests

**Files Modified (Sprint 7):**
- `test-packages/harness/schemas.py` - Added `TokenUsage` model with `total_billable`/`total_all` properties
- `test-packages/harness/collector.py` - Added `extract_token_usage()` function
- `test-packages/harness/enrichment.py` - Wire token extraction into `_compute_tree_stats()`
- `test-packages/harness/html_report/models.py` - Added token fields to `StatusBannerDisplayModel`
- `test-packages/harness/html_report/builder.py` - Extract token data from `timeline_tree.stats`
- `test-packages/harness/html_report/components/status_banner.py` - Token display HTML
- `test-packages/harness/html_report/assets/styles.py` - Added `CSS_TOKEN_DISPLAY`
- `test-packages/harness/tests/test_enrichment.py` - Updated for new `transcript_entries` parameter
- `test-packages/docs/timeline-tree-architecture-design.md` - Documentation updates

**Test Results:** 505 passed (485 + 20 new token extraction tests)

**Implementation Notes:**
- 3 parallel background agents (7A, 7B, 7C) completed in ~4 minutes
- Token display shows in status banner: `Tokens: Input X | Output Y | Total Z`
- Collapsible detail section shows cache creation/read, subagent tokens, billable total
- `extract_token_usage()` parses both `message.usage` and `toolUseResult.totalTokens`

---

## Sprint 8: Result[T,E] Error Handling Pattern

**Goal:** Implement discriminated union pattern for explicit error handling. Errors percolate up while allowing maximum work completion (fail late, not fast).

### Design Principles

1. **Explicit over implicit:** Functions return `Result[T, E]` instead of raising exceptions
2. **Fail late:** Complete as much work as possible before reporting errors
3. **Error accumulation:** Collect multiple errors rather than stopping at first
4. **Type safety:** Errors are typed and documented in function signatures

### Parallel Agents

#### Agent 8A: Create Result[T,E] infrastructure

**Tasks:**
1. Create `test-packages/harness/result.py` with:
   ```python
   from typing import TypeVar, Generic, Union
   from dataclasses import dataclass

   T = TypeVar('T')
   E = TypeVar('E')

   @dataclass(frozen=True)
   class Success(Generic[T]):
       value: T
       warnings: list[str] = field(default_factory=list)

       def is_success(self) -> bool:
           return True

   @dataclass(frozen=True)
   class Failure(Generic[E]):
       error: E
       partial_result: Any = None  # Work completed before failure

       def is_success(self) -> bool:
           return False

   Result = Union[Success[T], Failure[E]]

   # Error types
   @dataclass
   class EnrichmentError:
       phase: str  # "index", "tree_build", "depth_compute", etc.
       message: str
       context: dict = field(default_factory=dict)

   @dataclass
   class ArtifactError:
       operation: str  # "read", "write", "validate"
       path: str
       message: str
   ```

2. Add helper functions:
   - `collect_results()` - Aggregate multiple Results, accumulating errors
   - `map_result()` - Transform success value
   - `flat_map_result()` - Chain Result-returning operations

**Files Created:**
- `test-packages/harness/result.py`

#### Agent 8B: Refactor enrichment.py to use Result

**Tasks:**
1. Change `build_timeline_tree()` signature:
   ```python
   def build_timeline_tree(...) -> Result[EnrichedData, EnrichmentError]:
   ```
2. Each phase returns Result, errors accumulated
3. On error, include `partial_result` with work completed
4. Update callers in `pytest_plugin.py` to handle Result

**Files Modified:**
- `test-packages/harness/enrichment.py`
- `test-packages/harness/pytest_plugin.py`

#### Agent 8C: Refactor artifact preservation to use Result

**Tasks:**
1. Change `_preserve_artifacts()` to return `Result[ArtifactReport, list[ArtifactError]]`
2. Continue on individual file errors, accumulate all errors
3. Return partial success with list of failed operations
4. Update HTML report to show artifact errors if any

**Files Modified:**
- `test-packages/harness/pytest_plugin.py`
- `test-packages/harness/html_report/` (error display)

### QA Gate

```bash
# Run tests ensuring Result pattern works
python -m pytest test-packages/harness/tests/ -v

# Verify error handling with intentionally bad data
python -c "
from test_packages.harness.enrichment import build_timeline_tree
result = build_timeline_tree([], [], None, None)  # Invalid inputs
print(f'Success: {result.is_success()}')
if not result.is_success():
    print(f'Error: {result.error}')
"
```

---

## Sprint 9: Log Analysis & Warning Detection

**Goal:** Automatically detect warnings/errors in logs and fail tests accordingly. Silent failures are unacceptable.

### Design Principles

1. **Default fail on warnings:** Any warning in logs = test failure
2. **Explicit override only:** Tests can disable with `allow_warnings: true` (requires user approval)
3. **Full reporting:** Even on failure, complete all reporting before failing
4. **Clear documentation:** Guidelines document that overrides require explicit user permission

### Parallel Agents

#### Agent 9A: Log capture and analysis

**Tasks:**
1. Create `test-packages/harness/log_analyzer.py`:
   ```python
   @dataclass
   class LogAnalysisResult:
       warnings: list[LogEntry]
       errors: list[LogEntry]
       has_issues: bool

   def analyze_logs(log_content: str) -> LogAnalysisResult:
       """Parse logs for WARNING and ERROR level entries."""

   def analyze_captured_output(captured: CaptureFixture) -> LogAnalysisResult:
       """Analyze pytest captured output for issues."""
   ```
2. Integrate into test execution flow
3. Add `LogAnalysisResult` to `CollectedData`

**Files Created:**
- `test-packages/harness/log_analyzer.py`

**Files Modified:**
- `test-packages/harness/collector.py`
- `test-packages/harness/models.py`

#### Agent 9B: Automatic failure expectation

**Tasks:**
1. Add implicit expectation that runs after all others:
   ```python
   class NoWarningsExpectation(Expectation):
       """Implicit expectation: no warnings/errors in logs."""

       def evaluate(self, data: CollectedData) -> ExpectationResult:
           if data.log_analysis.has_issues and not self.allow_warnings:
               return ExpectationResult(
                   passed=False,
                   reason=f"Found {len(data.log_analysis.warnings)} warnings"
               )
   ```
2. Support `allow_warnings: true` in test YAML (with clear documentation)
3. Add warnings/errors to HTML report even on pass

**Files Modified:**
- `test-packages/harness/expectations.py`
- `test-packages/harness/pytest_plugin.py`

#### Agent 9C: Update guidelines and HTML display

**Tasks:**
1. Update `test-packages/docs/plugin-test-creation-guidelines.md`:
   - Document that warnings cause test failure by default
   - Document that `allow_warnings: true` requires explicit user approval
   - Add examples of when override is appropriate (never for production)
2. Add log warnings/errors section to HTML report
3. Style warnings in yellow, errors in red

**Files Modified:**
- `test-packages/docs/plugin-test-creation-guidelines.md`
- `test-packages/harness/html_report/components/` (new log section)
- `test-packages/harness/html_report/assets/styles.py`

### QA Gate

```bash
# Test that warnings cause failure
python -m pytest test-packages/fixtures/sc-startup/ -v -k "help"
# Should fail if any warnings in logs

# Verify override works (for testing the feature only)
# Create temporary test with allow_warnings: true
```

---

## Sprint 10: Collapsible Subagent Sections (HTML)

**Goal:** Implement the collapsible subagent sections that were identified as CRITICAL missing feature in design review.

### Design Gap Identified

CSS (`.subagent-section`) and JavaScript (`toggleAllSubagents()`) exist but `TimelineBuilder` doesn't generate `<details class="subagent-section">` wrapper HTML.

### Parallel Agents

#### Agent 10A: Update TimelineBuilder to generate collapsible sections

**Tasks:**
1. Modify `TimelineBuilder.build()` to:
   - Detect subagent boundaries from agent_id transitions
   - Wrap subagent tool calls in `<details class="subagent-section">`
   - Add summary with agent badge, tool count, duration
2. Implement smart collapse defaults (>66% of activity = expanded)
3. Add `data-agent-id` to wrapper for filtering

**Code Structure:**
```html
<details class="subagent-section" data-agent-id="a123" open>
  <summary>
    <span class="agent-badge">Explore</span>
    <span class="tool-count">5 tool calls</span>
    <span class="subagent-duration">+2.5s</span>
  </summary>
  <div class="subagent-timeline">
    <!-- Nested timeline items with depth classes -->
  </div>
</details>
```

**Files Modified:**
- `test-packages/harness/html_report/components/timeline.py`
- `test-packages/harness/html_report/models.py`

#### Agent 10B: Add missing design fields

**Tasks:**
1. Add `SIDECHAIN` to `TimelineNodeType` enum
2. Add `timestamp`, `elapsed_ms` fields to `TreeNode`
3. Add `seq` field and depth-first sequence numbering in enrichment
4. Update enrichment to populate new fields

**Files Modified:**
- `test-packages/harness/schemas.py`
- `test-packages/harness/enrichment.py`

#### Agent 10C: Tests for collapsible sections

**Tasks:**
1. Test HTML output contains `<details class="subagent-section">`
2. Test smart collapse defaults
3. Test agent filter integration with collapsed sections
4. Visual verification test with fixture that has subagents

**Files Modified:**
- `test-packages/harness/tests/html_report/test_components.py`

### QA Gate

```bash
# Run fixture with subagents
pytest test-packages/fixtures/sc-startup/ -v -k "init" --open-report

# Manual verification:
# - [ ] Subagent sections show as collapsible
# - [ ] Agent badge displays agent type
# - [ ] Tool count is accurate
# - [ ] Collapse/expand works
# - [ ] Filter by agent works with collapsed sections
```

---

## Sprint 11: Test Coverage Gaps (HIGH Priority)

**Goal:** Address HIGH priority test coverage gaps identified in gap analysis.

### HIGH Priority Gaps

1. **Deep trees (depth > 10):** Stack overflow risk in recursive `_compute_depths()`
2. **Large node counts (100+):** No performance testing
3. **File I/O errors:** Silent failures in artifact preservation
4. **JSON serialization errors:** Partial artifacts on failure

### Parallel Agents

#### Agent 11A: Deep tree and large node tests

**Tasks:**
1. Add iterative depth computation (replace recursion):
   ```python
   def _compute_depths_iterative(nodes: dict, root_uuid: str) -> None:
       """Iterative depth computation to avoid stack overflow."""
       stack = [(root_uuid, 0)]
       while stack:
           uuid, depth = stack.pop()
           if uuid in nodes:
               nodes[uuid].depth = depth
               for child_uuid in nodes[uuid].children:
                   stack.append((child_uuid, depth + 1))
   ```
2. Add tests:
   - `test_handles_depth_50_tree()` - No stack overflow
   - `test_handles_depth_100_tree()` - Stress test
   - `test_handles_100_nodes_efficiently()` - Performance < 2s
   - `test_handles_500_nodes()` - Larger scale test

**Files Modified:**
- `test-packages/harness/enrichment.py`
- `test-packages/harness/tests/test_enrichment.py`

#### Agent 11B: Error handling tests

**Tasks:**
1. Add tests for file I/O errors:
   - `test_handles_permission_denied()`
   - `test_handles_disk_full()`
   - `test_reports_partial_failure()`
2. Add tests for serialization errors:
   - `test_handles_non_serializable_content()`
   - `test_handles_circular_reference_in_data()`
3. Ensure errors are captured in Result, not swallowed

**Files Created/Modified:**
- `test-packages/harness/tests/test_artifact_preservation.py`
- `test-packages/harness/tests/test_enrichment.py`

#### Agent 11C: Edge case tests

**Tasks:**
1. Self-referential parentUuid test
2. Nested agents (agent within agent) test
3. Wide tree (50 siblings) test
4. Duplicate UUID handling test
5. Unicode content handling test

**Files Modified:**
- `test-packages/harness/tests/test_enrichment.py`

### QA Gate

```bash
# Run all new tests
python -m pytest test-packages/harness/tests/ -v -k "depth or large or error or edge"

# Performance benchmark
python -c "
import time
from test_packages.harness.enrichment import build_timeline_tree
# Generate 500 node transcript
transcript = [{'uuid': f'n-{i}', 'parentUuid': f'n-{i//10*10}' if i > 0 else None, 'type': 'user', 'message': {}} for i in range(500)]
start = time.time()
result = build_timeline_tree(transcript, [], mock_context, mock_paths)
print(f'500 nodes: {time.time()-start:.2f}s')
"
```

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
| 7 | Token Consumption Reporting | 3 parallel | Medium (3-4 hours) | Sprint 6 |
| 8 | Result[T,E] Error Handling | 3 parallel | Large (4-6 hours) | Sprint 6 |
| 9 | Log Analysis & Warnings | 3 parallel | Medium (3-4 hours) | Sprint 8 |
| 10 | Collapsible Subagent Sections | 3 parallel | Medium (3-4 hours) | Sprint 7 |
| 11 | Test Coverage Gaps | 3 parallel | Medium (3-4 hours) | Sprint 8 |

**Sprints 1-6 Complete:** 12-19 hours
**Sprints 7-11 Estimated:** 16-22 hours additional
**Total Estimated Effort:** 28-41 hours across all agents

---

## Success Criteria

### Phase 1 (Sprints 1-6) ✅ Complete
1. **All existing tests continue to pass** - No regression in current functionality
2. **New `-transcript.jsonl` naming** - Artifact files follow design doc naming
3. **`-enriched.json` files generated** - Every test produces enriched data
4. **Schema validation** - All generated files validate against Pydantic schemas
5. **Tree structure accuracy** - `parentUuid` chains correctly resolved
6. **Agent correlation** - Tool calls correctly attributed to subagents
7. **HTML depth classes** - Timeline items have depth-based CSS classes
8. **Documentation complete** - All new artifacts documented

### Phase 2 (Sprints 7-11) ⏳ In Progress
9. ✅ **Token consumption displayed** - Input/output tokens shown in HTML report
10. ✅ **Detailed token breakdown** - Cache creation/read, subagent tokens visible
11. **Result[T,E] pattern** - All enrichment/artifact functions return discriminated unions
12. **Error percolation** - Errors accumulated and reported, not swallowed
13. **Log warning detection** - Warnings in logs cause automatic test failure
14. **Warning override documented** - Guidelines require user approval for `allow_warnings`
15. **Collapsible subagent HTML** - `<details>` wrappers generated for subagent sections
16. **Deep tree safety** - Iterative depth computation, no stack overflow
17. **Performance tested** - 500+ node trees complete in < 2 seconds
18. **Edge cases covered** - Self-reference, nested agents, wide trees tested

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Claude transcript schema changes | Use `extra="allow"` in Pydantic models; log warnings |
| Missing `parentUuid` in transcripts | Treat as root-level entries (per design doc) |
| Performance with large transcripts | Build full tree upfront; UI lazy-loads; iterative algorithms |
| Breaking existing reports | All new fields are optional; backward compatible |
| Enrichment fails | Return `Result[T,E]` with partial_result; complete as much as possible |
| Stack overflow on deep trees | Use iterative depth computation instead of recursion |
| Silent failures | Use Result pattern; analyze logs for warnings; fail explicitly |
| Swallowed errors | Discriminated unions force callers to handle errors |
| Test flakiness from warnings | Allow explicit per-test override with documented approval requirement |

---

## References

- **Design Document:** `test-packages/docs/timeline-tree-architecture-design.md`
- **Schema Definitions:** `test-packages/harness/schemas.py`
- **Current Implementation:**
  - `collector.py:correlate_tool_calls_with_agents()` (lines 454-544)
  - `pytest_plugin.py:_preserve_artifacts()` (lines 1480-1614)
  - `html_report/components/timeline.py`
  - `html_report/assets/styles.py`
