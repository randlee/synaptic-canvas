# test-packages/

Local test infrastructure for validating Synaptic Canvas plugins.

---

## Purpose

This directory contains:
- **Test fixtures** for validating plugins before release
- **Test harness** infrastructure (pytest integration, HTML reports)
- **Report output** from test runs

**Related repo:** [sc-test-harness](https://github.com/randlee/sc-test-harness) - Instrumented test environment with hook tracing.

---

## Human Observability

**This is the most important principle.**

Tests can run automatically, but humans must be able to see what happened. The test harness generates HTML reports that show:
- Full timeline of tool calls and responses
- Expectation pass/fail with actual vs expected
- Reproduction commands for failed tests
- Side effects (files created/modified/deleted)

**When modifying test infrastructure:**
- Always verify HTML reports remain informative
- Never remove context that helps humans debug
- Prefer verbose output over silent success
- Test reports are the primary debugging interface

---

## Directory Structure

```
test-packages/
├── README.md           # This file
├── conftest.py         # Pytest configuration and hooks
├── fixtures/           # Per-plugin test fixtures
│   └── <plugin>/
│       ├── fixture.yaml
│       └── tests/
│           └── test_*.yaml
├── harness/            # Test runner infrastructure
│   ├── collector.py    # Data collection from traces
│   ├── environment.py  # Isolated session management
│   ├── fixture_loader.py
│   ├── pytest_plugin.py
│   ├── reporter.py     # Report generation
│   └── html_report/    # HTML report builder
├── reports/            # Generated test reports
└── docs/               # Additional documentation
```

---

## Plugin Test Lifecycle

Each test follows this flow:

1. **Setup** - Install plugin via `setup.plugins`, run `setup.commands`
2. **Execute** - Send prompt to Claude in isolated environment
3. **Collect** - Gather trace data, transcript, tool calls
4. **Evaluate** - Check expectations against collected data
5. **Report** - Generate HTML report with full context
6. **Cleanup** - Run `teardown.commands`, remove artifacts

---

## Running Tests

```bash
# From synaptic-canvas root:

# Run all fixture tests
pytest test-packages/fixtures/ -v --open-report

# Run specific plugin tests
pytest test-packages/fixtures/sc-startup/ -v --open-report

# Generate report but don't open
pytest test-packages/fixtures/ -v --generate-report

# Open report only on failure
pytest test-packages/fixtures/ -v --open-on-fail
```

---

## Writing Test Fixtures

### fixture.yaml
```yaml
name: my-plugin
package: my-plugin@synaptic-canvas

setup:
  plugins:
    - my-plugin@synaptic-canvas  # Installs plugin before tests
  commands:
    - echo "Additional setup"

teardown:
  commands:
    - echo "Cleanup"

tests_dir: tests
```

### tests/test_example.yaml
```yaml
test_id: my-plugin-001
test_name: Basic invocation
description: Verify plugin responds correctly

execution:
  prompt: "/my-command"
  model: haiku
  tools:
    - Bash
    - Read
  timeout_ms: 60000

expectations:
  - id: exp-001
    description: Should mention expected keyword
    type: output_contains
    expected:
      pattern: "(success|complete)"
      flags: "i"
```

---

## Relationship to sc-test-harness

| Component | Location | Purpose |
|-----------|----------|---------|
| Test fixtures | `test-packages/fixtures/` | Define what to test |
| Test harness | `test-packages/harness/` | Run tests, generate reports |
| Instrumented env | `../sc-test-harness/` | Isolated Claude environment with hooks |

The `sc-test-harness` repo provides:
- Pre-configured hooks for tracing tool calls
- Reset scripts for clean test environments
- Trace format documentation

---

## See Also

- [PQA Startup Prompt](../pm/PQA.md) - Plugin QA coordinator role
- [Test Harness Design Spec](../docs/requirements/test-harness-design-spec.md) - Full specification
- [sc-test-harness README](https://github.com/randlee/sc-test-harness) - Instrumented environment
