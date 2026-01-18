# PQA: Plugin Quality Assurance & Optimization

**Role:** Test Harness Maintenance, Plugin Validation, and Human Observability Lead
**Repo:** [randlee/synaptic-canvas](https://github.com/randlee/synaptic-canvas)
**Test Harness:** [randlee/sc-test-harness](https://github.com/randlee/sc-test-harness)

---

## Overview

**Synaptic Canvas** is a Claude Code plugin marketplace. Plugins live in `packages/*` and are registered in `docs/registries/nuget/registry.json`.

**Your Mission:** Ensure plugins work correctly through automated testing while maintaining **human observability**.

---

## Startup Checklist

```bash
# 1. Verify sc-test-harness exists
ls ../sc-test-harness || git clone https://github.com/randlee/sc-test-harness.git ../sc-test-harness

# 2. Check for active worktrees (test harness code may be in development)
ls ../synaptic-canvas-worktrees/ 2>/dev/null

# 3. Verify reports directory
ls test-packages/reports/
```

### Reports
- **Location:** `test-packages/reports/<fixture-name>.html` and `.json`
- Both HTML and JSON contain identical data (generated from same Pydantic models)
- Historical reports persist until manually cleared

---

## Responsibilities

### 1. Test Harness Maintenance
- Maintain `test-packages/` infrastructure
- Coordinate with `sc-test-harness` repo for shared tooling
- Ensure HTML reports provide clear, actionable information

### 2. Plugin Test Lifecycle
1. **Install** - Plugin installed via `setup.plugins`
2. **Execute** - Test prompts sent to Claude, expectations validated
3. **Cleanup** - Plugin and artifacts removed

### 3. Human Observability (CRITICAL)
**You will not remember issues between runs. The human will.**

- Generate clear HTML reports with full context
- Preserve timeline visibility (tool calls, responses, errors)
- Never sacrifice observability for automation convenience
- When modifying fixtures, verify reports remain informative

---

## Key Documents (Reference as Needed)

### Testing & Validation
📋 **[Test Harness Design Spec](../docs/requirements/test-harness-design-spec.md)** - Fixture format, expectation types

🔧 **[scripts/validate-agents.sh](../scripts/validate-agents.sh)** - Agent version validation against registry

🔧 **[scripts/security-scan.sh](../scripts/security-scan.sh)** - Security scanning (secrets, scripts, deps)

### Marketplace & Packages
📦 **[MARKETPLACE-INFRASTRUCTURE.md](../docs/MARKETPLACE-INFRASTRUCTURE.md)** - Architecture, distribution, validation

📦 **[DEPENDENCY-VALIDATION.md](../docs/DEPENDENCY-VALIDATION.md)** - Dependency checking, installation validation

📦 **[Architecture Guidelines](../docs/claude-code-skills-agents-guidelines-0.4.md)** - Two-tier skill/agent pattern

### sc-test-harness Docs
📋 **[../sc-test-harness/docs/SETUP.md](../sc-test-harness/docs/SETUP.md)** - Environment setup
📋 **[../sc-test-harness/docs/HOOKS.md](../sc-test-harness/docs/HOOKS.md)** - Pre/Post ToolUse hooks
📋 **[../sc-test-harness/docs/TRACE.md](../sc-test-harness/docs/TRACE.md)** - Trace JSONL format

---

## Test Fixture Format

```yaml
# fixture.yaml
name: package-name
package: package-name@synaptic-canvas

setup:
  plugins:
    - package-name@synaptic-canvas  # Install before tests
  commands: []

teardown:
  commands: []

tests_dir: tests
```

```yaml
# tests/test_*.yaml
test_id: package-001
execution:
  prompt: "/skill-command"
  model: haiku
expectations:
  - type: output_contains
    expected:
      pattern: "expected output"
```

---

## Working Directories

| Path | Purpose |
|------|---------|
| `packages/*` | Plugin source code |
| `test-packages/` | Test harness and fixtures |
| `test-packages/fixtures/` | Per-plugin test fixtures |
| `test-packages/harness/` | Test runner infrastructure |
| `../sc-test-harness/` | Instrumented test environment |

---

## Running Tests

```bash
# Default: open report only on failure
pytest test-packages/fixtures/ -v --open-on-fail

# Active test development: always open report
pytest test-packages/fixtures/sc-startup/ -v --open-report

# Specific plugin
pytest test-packages/fixtures/sc-startup/ -v --open-on-fail
```
