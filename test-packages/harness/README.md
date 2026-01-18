# Claude Code Test Harness

A testing framework for validating Claude Code skills, commands, and agents.

## Status

**Version**: 0.1.0
**Phase**: 1 (Foundation) Complete
**Tests**: 103 passing

## Quick Start

```python
from harness.environment import isolated_claude_session
from harness.collector import DataCollector
from harness.reporter import ReportBuilder

with isolated_claude_session() as session:
    # Run Claude with isolated environment
    result = session.run_prompt("/sc-startup --readonly")

    # Collect data from hooks and transcript
    collector = DataCollector(session.trace_path, session.transcript_path)
    data = collector.collect()

    # Build report
    report = ReportBuilder(data).build()
```

## Modules

| Module | Purpose | Key Classes/Functions |
|--------|---------|----------------------|
| `models.py` | Pydantic models for v3.0 schema | `FixtureReport`, `TestResult`, `Expectation`, `TimelineEntry` |
| `environment.py` | Environment isolation | `isolated_claude_session()`, `create_isolated_home()` |
| `collector.py` | Data collection | `DataCollector`, `parse_trace_file()`, `correlate_events()` |
| `reporter.py` | Report generation | `ReportBuilder`, `HTMLReportGenerator` |
| `runner.py` | Test orchestration | `TestRunner`, `FixtureConfig`, `TestConfig` |

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Test Runner   │────▶│   Claude CLI    │────▶│   Hooks         │
│   (pytest)      │     │   (isolated)    │     │   (log-hook.py) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Fixture       │     │   Transcript    │     │   Trace File    │
│   Config        │     │   (session)     │     │   (trace.jsonl) │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │                       │
                                └───────────┬───────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │   Report Builder        │
                               │   (correlate + build)   │
                               └─────────────────────────┘
                                            │
                          ┌─────────────────┴─────────────────┐
                          ▼                                   ▼
                 ┌─────────────────┐               ┌─────────────────┐
                 │   JSON Report   │               │   HTML Report   │
                 └─────────────────┘               └─────────────────┘
```

## Key Features

### Environment Isolation
- Uses `HOME=/tmp/claude-test-<uuid>` to isolate from user plugins
- Combines with `--setting-sources project` for complete isolation
- Safe cleanup with protection against deleting real HOME

### Dual-Source Data Collection
- **Primary**: Hook events from `trace.jsonl` (PreToolUse, PostToolUse, etc.)
- **Fallback**: Transcript file for errors and Claude responses (PostToolUse may not fire on errors)
- Correlation via `session_id` and `tool_use_id`

### Report Schema v3.0
- Supports multiple tests per fixture (tabbed HTML)
- Structured expectations with expected/actual/failure_reason
- Timeline with sequence numbers and elapsed time
- Side effects tracking (files created/modified/deleted)

## Running Tests

```bash
cd /Users/randlee/Documents/github/synaptic-canvas
python -m pytest test-packages/harness/tests/ -v
```

## Documentation

- **Design Spec**: `/docs/requirements/test-harness-design-spec.md`
- **Spike Reports**:
  - Environment isolation: `/sc-test-harness/docs/spike-1-clean-environment-configuration.md`
  - Hook observability: `/sc-test-harness/docs/spike-2-hook-observability.md`
  - Report design: `/test-packages/reports/spike3-gap-analysis.md`

## Deprecated Code

The original test runner has been moved to `test-packages/deprecated/`:
- `run_local_tests.py` - Monolithic test runner (~749 lines)
- `test_fixtures/` - Old plugin test utilities

See `deprecated/README.md` for details.
