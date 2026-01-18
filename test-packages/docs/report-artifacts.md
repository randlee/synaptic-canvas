# Test Report Artifacts

This document describes the artifact preservation system for PQA test runs, including what data is captured, folder structure, and retention policies.

---

## Overview

When pytest runs fixture tests, the harness captures multiple data sources for debugging and observability. These artifacts are preserved in two locations:

1. **Latest** (`reports/<fixture>/`) - Most recent run, cleaned before each new run
2. **History** (`reports/history/<fixture>/<timestamp>/`) - Timestamped archive, auto-pruned

---

## Artifacts Captured

| File | Source | Description |
|------|--------|-------------|
| `{test_id}-session.jsonl` | `collected_data.raw_transcript_entries` | Claude session transcript with full message history |
| `{test_id}-trace.jsonl` | `collected_data.raw_hook_events` | Hook events (SessionStart, PreToolUse, PostToolUse, etc.) |
| `{test_id}-claude-cli.txt` | `collected_data.claude_cli_stdout/stderr` | Raw Claude CLI output |
| `{test_id}-pytest.txt` | `result_data["pytest_output"]` | Pytest captured output for the test |

### Session Transcript (`-session.jsonl`)

Contains the full Claude session record including:
- User messages and prompts
- Assistant responses
- Tool use requests and results
- Parent-child message relationships (`parentUuid`, `isSidechain`)

### Trace File (`-trace.jsonl`)

Contains hook events captured by `scripts/log-hook.py`:
- `SessionStart` / `SessionEnd` - Session lifecycle
- `PreToolUse` / `PostToolUse` - Tool call tracking with `tool_use_id`
- `SubagentStart` / `SubagentStop` - Subagent lifecycle
- Process IDs (`pid`, `ppid`) for correlation

### Claude CLI Output (`-claude-cli.txt`)

Raw stdout/stderr from the Claude CLI process, useful for:
- Permission prompts and responses
- Error messages not captured in transcript
- CLI-level debugging

### Pytest Output (`-pytest.txt`)

Pytest's captured output including:
- Harness log messages
- Test setup/teardown output
- Assertion details on failure

---

## Folder Structure

```
test-packages/reports/
├── sc-startup.html                         # Latest HTML report
├── sc-startup.json                         # Latest JSON report
├── sc-startup/                             # Latest artifacts
│   ├── sc-startup-init-001-session.jsonl
│   ├── sc-startup-init-001-trace.jsonl
│   ├── sc-startup-init-001-claude-cli.txt
│   └── sc-startup-init-001-pytest.txt
│
└── history/                                # .gitignored
    └── sc-startup/
        ├── 2026-01-18T11-39-44/            # Older run
        │   └── ...
        └── 2026-01-18T12-15-22/            # Newer run
            └── ...
```

---

## Retention Policy

| Location | Retention | Cleanup |
|----------|-----------|---------|
| Latest (`reports/<fixture>/`) | 1 run | Cleaned before each new run |
| History (`reports/history/`) | 10 runs per fixture | Oldest deleted when limit exceeded |

History folders are sorted chronologically by timestamp (ISO format ensures lexicographic ordering matches chronological ordering).

---

## Git Configuration

The history folder is excluded from version control:

```gitignore
# Test artifact history (timestamped runs)
test-packages/reports/history/
```

Latest artifacts and HTML/JSON reports remain tracked for review purposes.

---

## Implementation Details

### Primary Implementation

**File:** `test-packages/harness/pytest_plugin.py`

**Key Functions:**
- `_preserve_artifacts()` - Main preservation logic (~line 1480)
- `_generate_fixture_report()` - Calls artifact preservation after report generation

### Data Flow

```
Test Execution
    ↓
DataCollector.collect()  →  CollectedData (raw_transcript_entries, raw_hook_events, etc.)
    ↓
_generate_fixture_report()  →  HTML/JSON reports
    ↓
_preserve_artifacts()  →  Latest folder + History folder
```

### Verification Checks

The preservation function includes:
- Warning if session transcript is empty
- Warning if trace file is empty
- Info logging for successful preservation
- Error handling with detailed logging on failure

---

## Usage

### Running Tests with Artifact Preservation

```bash
# Run tests - artifacts preserved automatically
pytest test-packages/fixtures/sc-startup/ -v

# View latest artifacts
ls test-packages/reports/sc-startup/

# View history
ls test-packages/reports/history/sc-startup/
```

### Accessing Artifacts Programmatically

```python
from pathlib import Path

reports_dir = Path("test-packages/reports")
fixture_name = "sc-startup"

# Latest artifacts
latest = reports_dir / fixture_name
for artifact in latest.glob("*.jsonl"):
    print(f"Latest: {artifact}")

# History
history = reports_dir / "history" / fixture_name
for run_folder in sorted(history.iterdir(), reverse=True)[:5]:
    print(f"Historical run: {run_folder.name}")
```

---

## Future Enhancements

- **pytest-html integration** - Generate pytest-html reports and cross-link with fixture HTML reports
- **Artifact compression** - Compress history folders to save disk space
- **Remote storage** - Option to push artifacts to cloud storage for CI/CD
- **Diff tooling** - Compare artifacts between runs for regression analysis
