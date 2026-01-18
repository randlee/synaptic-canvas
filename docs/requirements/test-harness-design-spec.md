# Claude Code Test Harness - Design Specification

**Version**: 1.0
**Date**: 2026-01-16
**Status**: Draft
**Authors**: Synaptic Canvas Team

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Environment Isolation](#3-environment-isolation)
4. [Data Collection](#4-data-collection)
5. [Report Schema v2.0](#5-report-schema-v20)
6. [HTML Report Requirements](#6-html-report-requirements)
7. [Test Fixture Design](#7-test-fixture-design)
8. [Git Branch Strategy](#8-git-branch-strategy)
9. [Harness Code Requirements](#9-harness-code-requirements)
10. [Implementation Priorities](#10-implementation-priorities)
11. [Appendices](#11-appendices)
12. [Implementation Status](#12-implementation-status)

---

## 1. Overview

### 1.1 Purpose

The Claude Code Test Harness provides automated testing infrastructure for validating Claude Code skills, commands, and agents. It enables developers to write reproducible tests that verify Claude's behavior when executing prompts, invoking tools, and delegating to subagents.

### 1.2 Scope

The test harness covers:

- **Skill Testing**: Validate that skills execute expected tool sequences and produce correct outputs
- **Integration Testing**: Test interactions between multiple skills and agents
- **Regression Testing**: Ensure changes don't break existing functionality
- **Behavior Verification**: Assert on Claude's tool usage patterns, not just final outputs

### 1.3 Goals

| Goal | Description |
|------|-------------|
| **Isolation** | Tests run in a clean environment without interference from user plugins or global settings |
| **Observability** | Capture comprehensive data about Claude's execution for assertions and debugging |
| **Reproducibility** | Tests produce consistent results given the same git state and configuration |
| **Actionable Reports** | Reports clearly show pass/fail status with debugging context |
| **Maintainability** | Harness code is modular, unit-tested, and well-documented |

### 1.4 Non-Goals

- Real-time test monitoring dashboard
- Distributed test execution across multiple machines
- Performance benchmarking (focus is correctness, not speed)
- Testing Claude's core model behavior (only skill/tool orchestration)

---

## 2. Architecture

### 2.1 High-Level Components

```
+------------------+     +-------------------+     +------------------+
|   Test Runner    |---->|   Claude CLI      |---->|   Hooks          |
|   (pytest)       |     |   (isolated)      |     |   (log-hook.py)  |
+------------------+     +-------------------+     +------------------+
        |                        |                        |
        v                        v                        v
+------------------+     +-------------------+     +------------------+
|   Test Fixtures  |     |   Transcript      |     |   Trace File     |
|   (YAML configs) |     |   (session.jsonl) |     |   (trace.jsonl)  |
+------------------+     +-------------------+     +------------------+
                                 |                        |
                                 +----------+-------------+
                                            |
                                            v
                                 +-------------------+
                                 |   Report Builder  |
                                 +-------------------+
                                            |
                          +-----------------+-----------------+
                          |                                   |
                          v                                   v
                 +------------------+               +------------------+
                 |   JSON Report    |               |   HTML Report    |
                 +------------------+               +------------------+
```

### 2.2 Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **Test Runner** | Orchestrates test execution, manages isolation, invokes Claude CLI |
| **Test Fixtures** | Define test prompts, expectations, and configurations |
| **Claude CLI** | Executes prompts in isolated environment with hooks enabled |
| **Hooks** | Capture real-time events (tool calls, subagents) to trace file |
| **Transcript** | Complete session record including Claude's responses |
| **Report Builder** | Correlates hook events with transcript, evaluates expectations |
| **JSON Report** | Machine-readable test results with full detail |
| **HTML Report** | Human-readable test results with interactive features |

### 2.3 Data Flow

1. Test runner creates isolated environment (unique `$HOME`)
2. Test runner invokes Claude CLI with test prompt
3. Hooks capture events to `trace.jsonl` in real-time
4. Claude writes transcript to `$HOME/.claude/projects/.../session.jsonl`
5. Test runner waits for Claude to complete
6. Report builder reads both trace and transcript files
7. Report builder correlates events using `session_id` and `tool_use_id`
8. Report builder evaluates expectations against collected data
9. Report builder generates JSON and HTML reports

---

## 3. Environment Isolation

### 3.1 Isolation Requirements

Tests must run in complete isolation from:
- User-installed plugins (`~/.claude/plugins/`)
- User settings (`~/.claude/settings.json`)
- Other test sessions

### 3.2 Isolation Mechanism

The primary isolation mechanism is the `HOME` environment variable override combined with `--setting-sources project`.

#### 3.2.1 HOME Override

```bash
# Create unique isolated HOME for this test run
TEST_HOME="/tmp/claude-test-$(uuidgen)"
mkdir -p "$TEST_HOME/.claude"

# Run Claude with isolation
HOME="$TEST_HOME" claude -p "$PROMPT" \
    --setting-sources project \
    --dangerously-skip-permissions \
    --model "$MODEL"

# Clean up after test
rm -rf "$TEST_HOME"
```

**Rationale**: The `HOME` override completely hides all user-scoped plugins. Claude stores plugin data under `~/.claude/`, so changing `HOME` creates a fresh plugin-free environment.

#### 3.2.2 Setting Sources Flag

The `--setting-sources project` flag ensures only the test project's `.claude/settings.json` is loaded, not global settings.

**Important**: This flag alone does NOT isolate plugins. The `HOME` override is required for plugin isolation.

### 3.3 Transcript Path Handling

With `HOME` override, transcripts are written to a different path:

```
# Normal path
~/.claude/projects/-Users-randlee-Documents-github-sc-test-harness/<session-id>.jsonl

# With HOME=/tmp/claude-test-abc
/tmp/claude-test-abc/.claude/projects/-Users-randlee-Documents-github-sc-test-harness/<session-id>.jsonl
```

The test harness must:
1. Capture `transcript_path` from `SessionStart` hook event
2. Use that path to read the transcript after completion
3. Handle the path transformation transparently

### 3.4 Plugin Installation for Tests

If a test requires specific plugins:

```bash
# Copy marketplace registry to isolated HOME
mkdir -p "$TEST_HOME/.claude/plugins"
cp ~/.claude/plugins/known_marketplaces.json "$TEST_HOME/.claude/plugins/"
cp -r ~/.claude/plugins/marketplaces "$TEST_HOME/.claude/plugins/"

# Install plugin in isolated environment
HOME="$TEST_HOME" claude plugin install $PLUGIN_NAME --scope project
```

**Note**: Marketplace data must be copied from the real HOME for plugin installation to work.

### 3.5 Known Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Marketplace access requires real HOME data | Plugin installation fails without copying | Copy marketplace registry to isolated HOME |
| Local skills directory takes precedence | Project `.claude/skills/` is still visible | Acceptable - tests often need local skills |
| Environment variables may leak | PATH, etc. inherited | Document expected env state |

---

## 4. Data Collection

### 4.1 Dual-Source Approach

The test harness uses two data sources:

| Source | Strengths | Weaknesses |
|--------|-----------|------------|
| **Hooks** (trace.jsonl) | Real-time capture, structured events, tool inputs/outputs | PostToolUse may not fire on errors |
| **Transcript** (session.jsonl) | Complete record, includes errors, Claude responses | Larger files, requires parsing |

**Recommendation**: Use hooks as primary source, transcript as fallback for errors and Claude responses.

### 4.2 Hook Events

The test harness captures all available hook events:

| Event | When Fired | Key Data Captured |
|-------|------------|-------------------|
| `SessionStart` | Session startup | `session_id`, `transcript_path`, `cwd` |
| `UserPromptSubmit` | Prompt submitted | `session_id`, `prompt` |
| `PreToolUse` | Before tool execution | `tool_name`, `tool_input`, `tool_use_id` |
| `PostToolUse` | After tool execution | `tool_name`, `tool_input`, `tool_response`, `tool_use_id` |
| `SubagentStart` | Subagent spawned | `agent_id`, `agent_type` |
| `SubagentStop` | Subagent completed | `agent_id`, `agent_transcript_path` |
| `Stop` | Claude stops responding | `session_id` |
| `SessionEnd` | Session ends | `session_id`, `reason` |

### 4.3 Hook Configuration

Hooks are defined in the test project's `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [{ "matcher": ".*", "commands": ["python3 scripts/log-hook.py --event SessionStart"] }],
    "SessionEnd": [{ "matcher": ".*", "commands": ["python3 scripts/log-hook.py --event SessionEnd"] }],
    "UserPromptSubmit": [{ "matcher": ".*", "commands": ["python3 scripts/log-hook.py --event UserPromptSubmit"] }],
    "PreToolUse": [{ "matcher": ".*", "commands": ["python3 scripts/log-hook.py --event PreToolUse"] }],
    "PostToolUse": [{ "matcher": ".*", "commands": ["python3 scripts/log-hook.py --event PostToolUse"] }],
    "SubagentStart": [{ "matcher": ".*", "commands": ["python3 scripts/log-hook.py --event SubagentStart"] }],
    "SubagentStop": [{ "matcher": ".*", "commands": ["python3 scripts/log-hook.py --event SubagentStop"] }],
    "Stop": [{ "matcher": ".*", "commands": ["python3 scripts/log-hook.py --event Stop"] }]
  }
}
```

### 4.4 Correlation Strategy

Events are correlated using these identifiers:

| Identifier | Purpose | Scope |
|------------|---------|-------|
| `session_id` | Correlate all events in a session | Global within session |
| `tool_use_id` | Match PreToolUse to PostToolUse to transcript tool_result | Per tool invocation |
| `agent_id` | Track subagent lifecycle | Per subagent |

### 4.5 Error Capture Gap

**Finding**: `PostToolUse` does not fire when tools fail with errors.

**Solution**: Parse transcript for tool results with `"is_error": true`:

```json
{
  "type": "tool_result",
  "content": "Exit code 1\nls: /nonexistent/directory/path: No such file or directory",
  "is_error": true,
  "tool_use_id": "toolu_01LG2zWV4GUKozxX5tSNEcYw"
}
```

### 4.6 Claude Response Capture

**Finding**: Hooks do not capture Claude's text responses to the user.

**Solution**: Parse transcript for assistant messages:

```json
{
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [
      {
        "type": "text",
        "text": "Here are the files and directories..."
      }
    ]
  }
}
```

---

## 5. Report Schema v2.0

### 5.1 Schema Overview

The report schema v2.0 provides a structured, comprehensive format for test results.

```json
{
  "schema_version": "2.0",
  "meta": { ... },
  "reproduce": { ... },
  "execution": { ... },
  "expectations": [ ... ],
  "timeline": [ ... ],
  "side_effects": { ... },
  "claude_response": { ... },
  "debug": { ... }
}
```

### 5.2 Schema Definition

#### 5.2.1 Root Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | Yes | Schema version (e.g., "2.0") |
| `meta` | object | Yes | Test metadata and status |
| `reproduce` | object | Yes | Commands to reproduce the test |
| `execution` | object | Yes | Execution parameters |
| `expectations` | array | Yes | List of expectations and their results |
| `timeline` | array | Yes | Chronological sequence of events |
| `side_effects` | object | Yes | File system changes |
| `claude_response` | object | Yes | Claude's final response |
| `debug` | object | No | Debug information |

#### 5.2.2 Meta Object

```json
{
  "meta": {
    "test_id": "string",          // Unique test identifier
    "test_name": "string",        // Human-readable test name
    "description": "string",      // Test description
    "timestamp": "ISO8601",       // When test ran
    "duration_ms": 0,             // Test duration in milliseconds
    "status": "pass|fail|partial",// Overall test status
    "pass_rate": "4/7",           // Expectations passed / total
    "tags": ["string"]            // Test tags for filtering
  }
}
```

#### 5.2.3 Reproduce Object

```json
{
  "reproduce": {
    "setup_commands": ["string"], // Commands to set up test environment
    "test_command": "string",     // The Claude CLI command
    "cleanup_commands": ["string"],// Commands to clean up after test
    "environment": {              // Required environment variables
      "ANTHROPIC_API_KEY": "(required)"
    },
    "git_state": {                // Git state at test time
      "branch": "string",
      "commit": "string",
      "modified_files": ["string"]
    }
  }
}
```

#### 5.2.4 Execution Object

```json
{
  "execution": {
    "prompt": "string",           // The prompt sent to Claude
    "model": "string",            // Model used (e.g., "haiku")
    "tools_allowed": ["string"],  // Tools allowed via --tools flag
    "session_id": "string",       // Claude session ID
    "token_usage": {
      "input": 0,
      "output": 0,
      "total": 0
    }
  }
}
```

#### 5.2.5 Expectations Array

Each expectation object:

```json
{
  "id": "exp-001",                  // Unique expectation ID
  "description": "string",          // What we're checking
  "type": "tool_call|hook_event|subagent_event|output_contains",
  "status": "pass|fail",            // Expectation result
  "expected": {                     // What we expected
    // Type-specific expected fields
  },
  "actual": {                       // What we observed (null if not found)
    // Type-specific actual fields
  },
  "matched_at": {                   // Where the match occurred (if pass)
    "sequence": 0,
    "timestamp": "ISO8601"
  },
  "failure_reason": "string"        // Why it failed (if fail)
}
```

**Expectation Types**:

| Type | Expected Fields | Actual Fields |
|------|-----------------|---------------|
| `tool_call` | `tool`, `pattern` | `tool`, `command`, `output_preview` |
| `hook_event` | `event`, optional filters | Event data or null |
| `subagent_event` | `event`, `agent_id` | Event data or null |
| `output_contains` | `pattern`, `flags` | `matched_text`, `context` |

#### 5.2.6 Timeline Array

Each timeline entry:

```json
{
  "seq": 1,                         // Sequence number (1-based)
  "type": "prompt|tool_call|response",
  "timestamp": "ISO8601",           // When this occurred
  "tool": "string",                 // Tool name (for tool_call type)
  "input": { ... },                 // Tool input (for tool_call type)
  "output": {                       // Tool output (for tool_call type)
    "stdout": "string",
    "stderr": "string",
    "exit_code": 0
  },
  "duration_ms": 0,                 // Duration in milliseconds
  "intent": "string",               // Inferred purpose of this action
  "content": "string",              // For prompt/response types
  "content_preview": "string",      // Truncated content
  "content_length": 0               // Full content length
}
```

#### 5.2.7 Side Effects Object

```json
{
  "side_effects": {
    "files_created": ["string"],    // Files created during test
    "files_modified": ["string"],   // Files modified during test
    "files_deleted": ["string"],    // Files deleted during test
    "git_changes": true|false       // Whether git state changed
  }
}
```

#### 5.2.8 Claude Response Object

```json
{
  "claude_response": {
    "preview": "string",            // First ~200 chars
    "full_text": "string",          // Complete response
    "word_count": 0                 // Word count
  }
}
```

#### 5.2.9 Debug Object

```json
{
  "debug": {
    "pytest_output": "string",      // Raw pytest output
    "pytest_status": "pass|fail",   // Pytest exit status
    "raw_trace_file": "string"      // Path to trace.jsonl
  }
}
```

### 5.3 Status Computation

```python
def compute_status(expectations: list) -> str:
    """Compute overall test status from expectations."""
    passed = sum(1 for e in expectations if e.get("status") == "pass")
    total = len(expectations)

    if total == 0:
        return "pass"  # No expectations = vacuously true
    elif passed == total:
        return "pass"
    elif passed == 0:
        return "fail"
    else:
        return "partial"
```

---

## 6. HTML Report Requirements

### 6.1 Layout Overview

The HTML report provides a human-readable view of test results with interactive features.

```
+------------------------------------------------------------------+
|  TEST: sc-startup-readonly-001                     [PARTIAL] 4/7 |
+------------------------------------------------------------------+
|  [Summary] [Expectations] [Timeline] [Debug]                     |
+------------------------------------------------------------------+
|                                                                  |
|  Current tab content...                                          |
|                                                                  |
+------------------------------------------------------------------+
```

### 6.2 Tab Structure

| Tab | Purpose | Content |
|-----|---------|---------|
| **Summary** | Quick overview | Status, reproduce commands, execution params |
| **Expectations** | Detailed results | Each expectation with expected/actual/reason |
| **Timeline** | Execution flow | Chronological list of all events |
| **Debug** | Raw data | Pytest output, trace file contents |

### 6.3 Status Indicators

| Status | Visual | Meaning |
|--------|--------|---------|
| Pass | Green checkmark | All expectations met |
| Fail | Red X | No expectations met |
| Partial | Yellow warning | Some expectations met |

### 6.4 Interactive Features

#### 6.4.1 Copy Functionality

Each of these should have a "Copy" button:
- Reproduce commands (as shell script)
- Individual tool commands
- Claude's full response
- Trace file contents

#### 6.4.2 Collapsible Sections

These sections should be collapsible:
- Individual expectations (expand for details)
- Timeline entries (expand for full output)
- Debug information

#### 6.4.3 Syntax Highlighting

Apply syntax highlighting to:
- JSON content
- Shell commands
- Markdown content

### 6.5 Responsive Design

The HTML report should be:
- Viewable on desktop and mobile
- Printable with reasonable formatting
- Self-contained (no external dependencies)

### 6.6 Implementation Approach

The HTML generator should:
1. Read JSON report as input
2. Use a template engine (e.g., Jinja2)
3. Embed all CSS/JS inline for portability
4. Generate single-file HTML output

---

## 7. Test Fixture Design

### 7.1 Fixture Structure

Each skill being tested has a dedicated fixture directory:

```
test-packages/
  fixtures/
    sc-startup/
      fixture.yaml           # Fixture configuration
      tests/
        test_readonly.yaml   # Individual test
        test_init.yaml
        test_checklist.yaml
        ...
    sc-github-issue/
      fixture.yaml
      tests/
        test_list.yaml
        test_create.yaml
        ...
```

### 7.2 Fixture Configuration (fixture.yaml)

```yaml
# Fixture-level configuration
name: sc-startup
description: Tests for the sc-startup skill
package: sc-startup@synaptic-canvas

# Shared setup for all tests in this fixture
setup:
  plugins:
    - sc-startup@synaptic-canvas
  files:
    - src: fixtures/sc-startup/data/sc-startup.yaml
      dest: .claude/sc-startup.yaml
    - src: fixtures/sc-startup/data/ARCH-SC.md
      dest: pm/ARCH-SC.md

# Shared teardown
teardown:
  commands:
    - git checkout -- .claude/
    - rm -f reports/trace.jsonl
```

### 7.3 Individual Test Configuration (test_*.yaml)

```yaml
# Test-level configuration
test_id: sc-startup-readonly-001
test_name: Startup runs in readonly mode
description: Verify /sc-startup --readonly reads config without mutation
tags:
  - readonly
  - integration

# Test execution
execution:
  prompt: "/sc-startup --readonly"
  model: haiku
  tools:
    - Bash
  timeout_ms: 30000

# Additional setup for this test (added to fixture setup)
setup:
  files:
    - src: fixtures/sc-startup/data/checklist.md
      dest: pm/checklist.md

# Expectations
expectations:
  - id: exp-001
    description: Load sc-startup.yaml config file
    type: tool_call
    expected:
      tool: Bash
      pattern: "cat.*sc-startup\\.yaml"

  - id: exp-002
    description: Read startup prompt file
    type: tool_call
    expected:
      tool: Bash
      pattern: "cat.*ARCH-SC\\.md"

  - id: exp-003
    description: Startup report emitted in output
    type: output_contains
    expected:
      pattern: "(startup.*report|SC-Startup Report)"
      flags: "i"
```

### 7.4 Test Count Guidelines

| Fixture Size | Number of Tests | Rationale |
|--------------|-----------------|-----------|
| Minimum | 10 | Cover core functionality |
| Target | 15-20 | Balance coverage and maintenance |
| Maximum | 25 | Avoid fixture sprawl |

### 7.5 Sequential Execution

Tests within a fixture execute sequentially to:
- Avoid resource contention
- Allow tests to depend on prior state (when needed)
- Simplify debugging

```python
# Test runner behavior
for fixture in fixtures:
    fixture.setup()
    for test in fixture.tests:
        test.setup()
        test.execute()
        test.teardown()
    fixture.teardown()
```

### 7.6 Test Isolation

Despite sequential execution, tests should be isolated:
- Each test starts with fixture.setup() state
- Tests should not depend on side effects from previous tests
- Explicit dependencies must be documented

---

## 8. Git Branch Strategy

### 8.1 Purpose

Git branches provide reproducible state for tests. Instead of complex setup scripts, tests can checkout a branch with pre-configured state.

### 8.2 Branch Naming Convention

```
test/<fixture-name>/<scenario>
```

Examples:
- `test/sc-startup/valid-config`
- `test/sc-startup/missing-checklist`
- `test/sc-github-issue/has-open-issues`

### 8.3 Branch Maintenance

| Branch Type | Maintenance | Owner |
|-------------|-------------|-------|
| `test/*` branches | Frozen after creation | Test maintainer |
| `main` | Active development | Team |
| `develop` | Feature integration | Team |

### 8.4 Branch Creation Process

1. Create branch from known good state
2. Configure test scenario (create/modify files)
3. Commit with message: `test: setup for <scenario>`
4. Document branch in fixture.yaml
5. Never modify branch after tests depend on it

### 8.5 Test Repository

Tests run against a dedicated test repository (`sc-test-harness`) that:
- Contains test branches with pre-configured state
- Has no production code (only test data)
- Can be reset/rebuilt without affecting production

---

## 9. Harness Code Requirements

### 9.1 Code Organization

```
sc-test-harness/
  src/
    harness/
      __init__.py
      runner.py           # Test orchestration
      isolation.py        # Environment isolation
      collector.py        # Data collection (hooks + transcript)
      correlator.py       # Event correlation
      reporter.py         # Report generation
      assertions.py       # Assertion helpers
      models.py           # Data models (dataclasses)
  tests/
    test_runner.py
    test_isolation.py
    test_collector.py
    test_correlator.py
    test_reporter.py
    test_assertions.py
  scripts/
    log-hook.py           # Hook event logger
```

### 9.2 Unit Test Requirements

All harness code must have unit tests:

| Module | Test Focus |
|--------|------------|
| `runner.py` | Test orchestration logic, fixture loading |
| `isolation.py` | HOME override, path transformation |
| `collector.py` | Hook parsing, transcript parsing |
| `correlator.py` | Event correlation by session_id, tool_use_id |
| `reporter.py` | JSON/HTML generation, status computation |
| `assertions.py` | Expectation evaluation logic |

**Minimum coverage target**: 80%

### 9.3 Modular Design Principles

1. **Single Responsibility**: Each module has one clear purpose
2. **Dependency Injection**: Pass dependencies explicitly for testability
3. **Interface-Based**: Define protocols/ABCs for key components
4. **Immutable Data**: Use dataclasses with frozen=True where possible

### 9.4 Error Handling

| Error Type | Handling |
|------------|----------|
| Claude CLI failure | Capture exit code, stderr; mark test as failed |
| Hook script failure | Log warning, continue with transcript-only data |
| Transcript parse error | Fail test with clear error message |
| Timeout | Kill Claude process, mark test as timeout |

### 9.5 Logging

```python
import logging

logger = logging.getLogger("harness")

# Log levels:
# DEBUG: Detailed execution trace
# INFO: Test progress (start, end, status)
# WARNING: Recoverable issues (hook failure, missing data)
# ERROR: Test failures, unrecoverable issues
```

---

## 10. Implementation Priorities

### 10.1 Phase 1: Foundation (Week 1-2)

**Goal**: Minimal viable test harness

| Task | Priority | Effort |
|------|----------|--------|
| Implement environment isolation (HOME override) | P0 | Low |
| Create hook logger script | P0 | Low |
| Build basic test runner | P0 | Medium |
| Implement JSON report generation | P0 | Medium |
| Create first fixture (sc-startup) | P0 | Low |

**Exit Criteria**: Can run a single test and produce JSON report

### 10.2 Phase 2: Data Collection (Week 3-4)

**Goal**: Comprehensive data capture

| Task | Priority | Effort |
|------|----------|--------|
| Implement transcript parser | P0 | Medium |
| Build event correlator | P0 | Medium |
| Add error capture (transcript fallback) | P1 | Low |
| Add Claude response capture | P1 | Low |
| Implement side effects tracking | P2 | Medium |

**Exit Criteria**: Reports include all data from hooks and transcript

### 10.3 Phase 3: Assertions & Expectations (Week 5-6)

**Goal**: Rich assertion framework

| Task | Priority | Effort |
|------|----------|--------|
| Implement tool_call expectations | P0 | Medium |
| Implement hook_event expectations | P0 | Medium |
| Implement output_contains expectations | P1 | Low |
| Implement subagent_event expectations | P1 | Medium |
| Add pattern matching (regex support) | P1 | Low |

**Exit Criteria**: Can write complex expectations with multiple assertion types

### 10.4 Phase 4: Reporting (Week 7-8)

**Goal**: Actionable HTML reports

| Task | Priority | Effort |
|------|----------|--------|
| Design HTML report template | P0 | Medium |
| Implement HTML generator | P0 | Medium |
| Add copy functionality | P1 | Low |
| Add collapsible sections | P1 | Low |
| Add syntax highlighting | P2 | Low |

**Exit Criteria**: HTML reports are usable for debugging failures

### 10.5 Phase 5: Scale & Polish (Week 9-10)

**Goal**: Production-ready harness

| Task | Priority | Effort |
|------|----------|--------|
| Create 10+ tests for sc-startup fixture | P0 | Medium |
| Create sc-github-issue fixture | P1 | Medium |
| Add unit tests for harness code | P0 | High |
| Write documentation | P1 | Medium |
| Performance optimization | P2 | Low |

**Exit Criteria**: Harness is documented, tested, and has multiple fixtures

---

## 11. Appendices

### Appendix A: Hook Event Payloads

#### SessionStart

```json
{
  "session_id": "4a69f9b0-a586-49ea-8a4a-ee356768841e",
  "transcript_path": "/path/to/session.jsonl",
  "cwd": "/path/to/project",
  "hook_event_name": "SessionStart",
  "source": "startup"
}
```

#### PreToolUse

```json
{
  "session_id": "...",
  "transcript_path": "...",
  "cwd": "...",
  "permission_mode": "bypassPermissions",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "ls -la",
    "description": "List files"
  },
  "tool_use_id": "toolu_016tu1oYHSRV37rwRkTNgGaA"
}
```

#### PostToolUse

```json
{
  "session_id": "...",
  "transcript_path": "...",
  "cwd": "...",
  "permission_mode": "bypassPermissions",
  "hook_event_name": "PostToolUse",
  "tool_name": "Bash",
  "tool_input": { ... },
  "tool_response": {
    "stdout": "...",
    "stderr": "",
    "interrupted": false,
    "isImage": false
  },
  "tool_use_id": "toolu_016tu1oYHSRV37rwRkTNgGaA"
}
```

#### SubagentStart

```json
{
  "session_id": "...",
  "transcript_path": "...",
  "cwd": "...",
  "hook_event_name": "SubagentStart",
  "agent_id": "a41d2ca",
  "agent_type": "Explore"
}
```

#### SubagentStop

```json
{
  "session_id": "...",
  "transcript_path": "...",
  "cwd": "...",
  "hook_event_name": "SubagentStop",
  "agent_id": "a41d2ca",
  "agent_transcript_path": "/path/to/subagent/transcript.jsonl"
}
```

### Appendix B: Transcript Entry Types

| Type | Description |
|------|-------------|
| `user` | User message (prompt) |
| `assistant` | Claude's response |
| `tool_use` | Tool invocation request |
| `tool_result` | Tool execution result |

### Appendix C: Example Test Run Output

```
$ pytest tests/test_sc_startup.py -v

========================== test session starts ==========================
collected 7 items

tests/test_sc_startup.py::test_readonly_loads_config PASSED     [ 14%]
tests/test_sc_startup.py::test_readonly_reads_prompt PASSED     [ 28%]
tests/test_sc_startup.py::test_readonly_reads_checklist PASSED  [ 42%]
tests/test_sc_startup.py::test_readonly_no_subagent FAILED      [ 57%]
tests/test_sc_startup.py::test_readonly_emits_report PASSED     [ 71%]
tests/test_sc_startup.py::test_readonly_no_mutations PASSED     [ 85%]
tests/test_sc_startup.py::test_readonly_no_git_changes PASSED   [100%]

======================== 6 passed, 1 failed in 45.2s ========================

Report generated: reports/sc-startup-readonly-001.json
HTML report: reports/sc-startup-readonly-001.html
```

### Appendix D: References

- **Spike 1: Environment Isolation**: `/Users/randlee/Documents/github/sc-test-harness/docs/spike-1-clean-environment-configuration.md`
- **Spike 2: Hook Observability**: `/Users/randlee/Documents/github/sc-test-harness/docs/spike-2-hook-observability.md`
- **Spike 3: Report Design**: `/Users/randlee/Documents/github/synaptic-canvas/test-packages/reports/spike3-gap-analysis.md`
- **Example Report Schema**: `/Users/randlee/Documents/github/synaptic-canvas/test-packages/reports/example-report.json`

---

## 12. Implementation Status

### 12.1 Phase 1: Foundation (COMPLETE ✅)

**Completed**: 2026-01-16

| Module | Lines | Tests | Coverage | Status |
|--------|-------|-------|----------|--------|
| `harness/__init__.py` | 38 | - | - | ✅ |
| `harness/models.py` | 683 | 33 | 99% | ✅ |
| `harness/environment.py` | 564 | 28 | 87% | ✅ |
| `harness/collector.py` | 871 | 42 | 85% | ✅ |
| `harness/reporter.py` | 1,442 | - | - | ✅ |
| `harness/runner.py` | 710 | - | - | ✅ |
| **Total** | **~6,000** | **103** | **~90%** | ✅ |

**Key Deliverables**:
- Pydantic models matching v3.0 JSON schema
- `isolated_claude_session()` context manager with HOME override
- Dual-source data collection (hooks + transcript)
- Event correlation via session_id and tool_use_id
- HTML report generation with tabs, copy buttons, editor links

### 12.2 Phase 2: Assertions & Expectations (PENDING)

- [ ] Expectation DSL for defining test assertions
- [ ] Pattern matching for tool calls
- [ ] Subagent lifecycle assertions
- [ ] Output content assertions

### 12.3 Phase 3: Fixtures & Configuration (PENDING)

- [ ] YAML-based fixture definitions
- [ ] Git branch state management
- [ ] Test discovery from fixture files
- [ ] Parameterized test generation

### 12.4 Phase 4: Reporting Enhancements (IN PROGRESS)

- [x] HTML report v2 with tabbed layout
- [x] Editor links (VS Code / PyCharm)
- [x] Copy buttons with source attribution
- [x] Timeline elapsed time display
- [~] Agent Assessment section (HTML/CSS added, display issue - see Known Issues)
- [ ] Report aggregation across fixtures

### 12.5 Known Issues

| Issue | Status | Description |
|-------|--------|-------------|
| Agent Assessment not displaying | OPEN | Section added to `example-report-v2.html` with CSS `.visible { display: block }` but not rendering in Safari/Chrome. Needs CSS specificity debugging. |
| fetch() limitation | DOCUMENTED | Dynamic markdown loading via `fetch()` doesn't work with local `file://` URLs. Content must be embedded or served via HTTP. |

### 12.6 Deprecated Code

The following code has been moved to `test-packages/deprecated/`:
- `run_local_tests.py` - Original monolithic test runner
- `test_fixtures/` - Old plugin test harness utilities

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-16 | Synaptic Canvas Team | Initial specification |
| 1.1 | 2026-01-16 | Synaptic Canvas Team | Added Section 12: Implementation Status |
| 1.2 | 2026-01-16 | Synaptic Canvas Team | Added Known Issues section, updated Phase 4 status |
