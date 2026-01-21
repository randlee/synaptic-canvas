# sc-startup Test Coverage Expansion Plan

**Date:** 2026-01-17
**Package:** sc-startup v0.7.0
**Current Coverage:** ~3% (3 working tests)
**Target Coverage:** 80%+

---

## Executive Summary

The sc-startup package provides startup workflow orchestration for Synaptic Canvas projects. It includes:
- 1 Command: `/sc-startup` (user-invocable slash command)
- 1 Skill: `sc-startup` (orchestration logic)
- 2 Agents: `sc-startup-init`, `sc-checklist-status` (background task agents)

**Component Type Testing Strategies:**
| Type | Invocation | Testing Approach |
|------|------------|------------------|
| **Command** | `/sc-startup [flags]` | Direct prompt invocation, verify output and tool calls |
| **Agent** | Task tool with `subagent_type` | Spawn via Task tool, verify SubagentStart/Stop hooks |
| **Skill** | Skill tool or `/skill-name` | Check Skill tool call, verify skill execution |

**Current test status:**
| Test | Status | Notes |
|------|--------|-------|
| Readonly Mode | PARTIAL | 4/7 expectations pass |
| Init Mode | PASS | Config detection works |
| Missing Config | PASS | Error handling works |
| PR Integration | SKIPPED | Dependency on ci-pr-agent |

**Gap Analysis:** Missing tests for `--fast`, `--help`, `--pull`, flag combinations, agent error handling, path safety, and config validation.

---

## Test Data Management

### Problem
Currently, sc-test-harness has test data files committed to the repo:
- `pm/ARCH-SC.md` - Test startup prompt
- `pm/checklist.md` - Test checklist
- `.claude/sc-startup.yaml` - Test config

This violates test isolation principles. Each test should control its own data.

### Solution
**Remove these files from sc-test-harness and manage them in fixture setup/teardown.**

Files to remove from sc-test-harness:
```bash
# In sc-test-harness repo:
git rm pm/ARCH-SC.md
git rm pm/checklist.md
git rm .claude/sc-startup.yaml
# Keep pm/ directory but make it empty (add .gitkeep if needed)
```

Each fixture's `setup` section creates required test data:
```yaml
setup:
  commands:
    # Create test config
    - mkdir -p .claude pm
    - |
      cat > .claude/sc-startup.yaml << 'EOF'
      startup-prompt: pm/ARCH-SC.md
      check-list: pm/checklist.md
      worktree-scan: scan
      pr-enabled: false
      worktree-enabled: false
      EOF
    # Create test prompt
    - |
      cat > pm/ARCH-SC.md << 'EOF'
      # Test Startup Prompt
      This is a test prompt for sc-startup testing.
      EOF
    # Create test checklist
    - |
      cat > pm/checklist.md << 'EOF'
      # Test Checklist
      - [ ] Item 1
      - [ ] Item 2
      EOF
```

Each fixture's `teardown` removes test data:
```yaml
teardown:
  commands:
    - rm -f .claude/sc-startup.yaml
    - rm -f pm/ARCH-SC.md pm/checklist.md
```

---

## Test Fixture Structure

```
test-packages/
├── sc-startup/                    # All sc-startup package tests
│   ├── fixture.yaml               # Shared fixture config
│   └── tests/
│       ├── test_help.yaml         # COMMAND: --help flag
│       ├── test_fast.yaml         # COMMAND: --fast flag
│       ├── test_readonly.yaml     # COMMAND: --readonly flag
│       ├── test_init.yaml         # COMMAND: --init flag
│       ├── test_missing_config.yaml # COMMAND: error handling
│       ├── test_path_escape.yaml  # COMMAND: security (path safety)
│       ├── test_config_escape.yaml # COMMAND: security (config paths)
│       ├── test_agent_init.yaml   # AGENT: sc-startup-init
│       └── test_agent_checklist.yaml # AGENT: sc-checklist-status
```

---

## Phase 1: Command Tests (`/sc-startup`)

### Test 1.1: Help Flag
| Field | Value |
|-------|-------|
| **Test ID** | `sc-startup-help-001` |
| **Component Type** | COMMAND |
| **Purpose** | Verify `--help` shows usage and exits without agent invocation |

```yaml
test_id: sc-startup-help-001
test_name: Help flag shows usage
component_type: command
description: Verify /sc-startup --help displays usage information without invoking agents

execution:
  prompt: "/sc-startup --help"
  model: haiku
  timeout_ms: 30000

expectations:
  - id: exp-help-usage
    description: Output contains usage information
    type: output_contains
    expected:
      pattern: "(usage|Usage|options|flags)"
      flags: "i"
  - id: exp-help-flags
    description: Output lists available flags
    type: output_contains
    expected:
      pattern: "(--readonly|--init|--fast|--pr|--pull)"
  - id: exp-no-agent
    description: No agents spawned for help
    type: hook_event_absent
    expected:
      event: SubagentStart
```

### Test 1.2: Missing Config Error (P0)
| Field | Value |
|-------|-------|
| **Test ID** | `sc-startup-missing-001` |
| **Component Type** | COMMAND |
| **Purpose** | Verify graceful error when config is missing |

```yaml
test_id: sc-startup-missing-001
test_name: Missing config shows error
component_type: command
description: Verify /sc-startup without config shows actionable error

setup:
  commands:
    - rm -f .claude/sc-startup.yaml  # Ensure no config

execution:
  prompt: "/sc-startup"
  model: haiku
  timeout_ms: 45000

expectations:
  - id: exp-missing-error
    description: Error mentions missing config
    type: output_contains
    expected:
      pattern: "(missing|not found|does not exist|sc-startup\\.yaml)"
      flags: "i"
  - id: exp-suggestion
    description: Suggests --init or creation
    type: output_contains
    expected:
      pattern: "(--init|create|configure)"
      flags: "i"
```

### Test 1.3: Config Path Escape (P0 - Security)
| Field | Value |
|-------|-------|
| **Test ID** | `sc-startup-config-escape-001` |
| **Component Type** | COMMAND |
| **Purpose** | Verify path safety validation in config |

```yaml
test_id: sc-startup-config-escape-001
test_name: Config path escape blocked
component_type: command
description: Paths escaping repo root are rejected (security test)

setup:
  commands:
    - mkdir -p .claude
    - |
      cat > .claude/sc-startup.yaml << 'EOF'
      startup-prompt: ../../../etc/passwd
      check-list: pm/checklist.md
      EOF

execution:
  prompt: "/sc-startup"
  model: haiku
  timeout_ms: 30000

expectations:
  - id: exp-escape-error
    description: Path escape attempt rejected
    type: output_contains
    expected:
      pattern: "(path|escape|security|invalid|outside|traversal)"
      flags: "i"
```

---

## Phase 2: Agent Tests

### Test 2.1: Checklist Path Escape (P0 - Security)
| Field | Value |
|-------|-------|
| **Test ID** | `sc-checklist-escape-001` |
| **Component Type** | AGENT |
| **Agent** | `sc-checklist-status` |
| **Purpose** | Verify path traversal is blocked |

```yaml
test_id: sc-checklist-escape-001
test_name: Checklist path escape blocked
component_type: agent
agent_name: sc-checklist-status
description: Agent rejects paths that escape repo root (security test)

execution:
  # Direct agent invocation requires special handling
  # The agent is spawned via Task tool with specific inputs
  prompt: |
    Run the sc-checklist-status agent with these inputs:
    - checklist_path: ../../../etc/passwd
    - repo_root: /Users/randlee/Documents/github/sc-test-harness
    - mode: report
  model: haiku
  timeout_ms: 30000

expectations:
  - id: exp-path-error
    description: Path escape attempt detected and blocked
    type: output_contains
    expected:
      pattern: "(INVALID_PATH|escape|security|blocked|rejected|outside)"
      flags: "i"
  - id: exp-success-false
    description: Agent returns success=false
    type: output_contains
    expected:
      pattern: "success.*false"
      flags: "i"
```

---

## Test Priority Matrix

| Priority | Test ID | Component | Risk Area | Effort |
|----------|---------|-----------|-----------|--------|
| **P0** | sc-startup-help-001 | COMMAND | User experience | Low |
| **P0** | sc-startup-missing-001 | COMMAND | Error handling | Low |
| **P0** | sc-checklist-escape-001 | AGENT | Security | Medium |
| **P0** | sc-startup-config-escape-001 | COMMAND | Security | Medium |
| P1 | sc-startup-fast-001 | COMMAND | Core functionality | Low |
| P1 | sc-startup-readonly-002 | COMMAND | Data safety | Medium |
| P1 | sc-startup-init-001 | COMMAND | Onboarding | Medium |
| P1 | sc-checklist-report-001 | AGENT | Core functionality | Medium |
| P2 | sc-startup-pull-001 | COMMAND | Integration | High |
| P2 | sc-startup-combo-001 | COMMAND | Flag handling | Medium |
| P2 | sc-startup-init-plugins-001 | AGENT | Discovery | Medium |
| P3 | sc-checklist-update-001 | AGENT | Mutation testing | High |

---

## Implementation Plan

### Step 0: Clean sc-test-harness (Pre-requisite)
Remove committed test data files from sc-test-harness:
```bash
cd /Users/randlee/Documents/github/sc-test-harness
git rm pm/ARCH-SC.md pm/checklist.md .claude/sc-startup.yaml
mkdir -p pm && touch pm/.gitkeep
git add pm/.gitkeep
git commit -m "chore: remove test data files, manage via fixture setup"
```

### Step 1: Create Fixture Infrastructure
Create test directory and fixture.yaml:
```bash
mkdir -p test-packages/sc-startup/tests
```

### Step 2: P0 Tests (Security & Error Handling)
1. Implement `sc-startup-help-001` (COMMAND)
2. Implement `sc-startup-missing-001` (COMMAND)
3. Implement `sc-checklist-escape-001` (AGENT)
4. Implement `sc-startup-config-escape-001` (COMMAND)

### Step 3: Run & Validate
```bash
pytest test-packages/sc-startup/ -v --open-report
```

### Step 4: Iterate Based on Results
Review HTML reports, identify issues, adjust tests.

---

## Dependencies & Prerequisites

- **sc-test-harness**: Must be cloned to `../sc-test-harness/`
- **API Key**: `ANTHROPIC_API_KEY` environment variable
- **Plugin Installation**: Tests install `sc-startup@synaptic-canvas` via `setup.plugins`
- **Clean Repo**: sc-test-harness should not have committed test data files

---

## Report Observability Requirements

All tests must generate HTML reports showing:
1. Full timeline of tool calls
2. Agent invocations (SubagentStart/Stop events)
3. Expectation pass/fail with actual values
4. Reproduction commands
5. Side effects (files created/modified)

---

## Estimated Coverage After Implementation

| Component | Type | Before | After |
|-----------|------|--------|-------|
| `/sc-startup --help` | COMMAND | 0% | 100% |
| `/sc-startup --fast` | COMMAND | 0% | 100% |
| `/sc-startup --readonly` | COMMAND | 50% | 100% |
| `/sc-startup --init` | COMMAND | 50% | 100% |
| `/sc-startup --pr` | COMMAND | 0% | 50% |
| `/sc-startup --pull` | COMMAND | 0% | 50% |
| `sc-startup-init` | AGENT | 30% | 80% |
| `sc-checklist-status` | AGENT | 20% | 80% |
| Config validation | COMMAND | 30% | 90% |
| Path safety | COMMAND/AGENT | 0% | 100% |
| **Overall** | | ~3% | ~80% |
