# Deprecated Test Infrastructure

This folder contains deprecated Python test code from the original Synaptic Canvas test runner implementation.

## Why These Files Were Deprecated

The original test runner (`run_local_tests.py`) and supporting fixtures grew into a tightly-coupled 749+ line monolith that:

1. **Mixed concerns**: Combined test execution, trace parsing, report generation, and expectation validation in a single file
2. **Lacked modularity**: Made it difficult to extend or maintain individual components
3. **Had scaling issues**: The monolithic design didn't support the growing needs of multi-package plugin testing

## What These Files Did

### `run_local_tests.py`
The original test runner that provided:
- Package-mapped test execution via pytest
- Integration test support with token usage tracking
- Trace file parsing from Claude CLI output
- Multiple report formats (Markdown, HTML, JSON)
- Expectation validation (expected tools, reads, events, prompts, outputs)
- Session line selection for multi-session traces

### `test_fixtures/`
Supporting test infrastructure:
- `plugin_test_harness.py` - Built temporary plugin bundles from `.claude-plugin/plugin.json`
- `helpers.py` - Shared test helpers (e.g., `require_yaml` for checking PyYAML availability)
- `__init__.py` - Package initialization

## New Implementation

The new test infrastructure follows a modular, well-tested design. See:

- **Design Spec**: `/docs/requirements/test-harness-design-spec.md`
- **Harness Code**: `/test-packages/harness/` (~6,000 lines, 103 unit tests)
- **Test Repository**: `/Users/randlee/Documents/github/sc-test-harness/` (instrumented test environment)

The new implementation provides:
- Pydantic models matching v3.0 JSON schema
- `isolated_claude_session()` context manager with HOME override
- Dual-source data collection (hooks + transcript fallback)
- Event correlation via session_id and tool_use_id
- HTML reports with tabs, copy buttons, and editor links (VS Code/PyCharm)
- 103 unit tests with ~90% coverage on core modules

## Reference Value

These files are kept as reference material for:
- Understanding the original trace parsing logic
- Reviewing expectation validation patterns
- Migrating any useful utilities to the new implementation
