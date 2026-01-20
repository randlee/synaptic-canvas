# sc-kanban v0.7.0

![Version](https://img.shields.io/badge/version-0.7.0-blue)
![Status](https://img.shields.io/badge/status-beta-yellow)
![License](https://img.shields.io/badge/license-MIT-green)

Kanban state machine for Synaptic Canvas: manage task lifecycle with backlog → board → done workflow, automatic scrubbing, gate validation, and shared board configuration.

## Overview

**sc-kanban** provides a pure state machine for task tracking with three-file lifecycle management, provider abstraction (kanban vs checklist), and integration with sc-project-manager via shared YAML configuration. Cards flow from lean backlog entries through rich board tracking to scrubbed archive, with automatic field management and WIP enforcement.

## Features

- **Three-File Lifecycle**: Backlog (lean, 100s items) → Board (rich, 10-20 active) → Done (scrubbed archive)
- **Automatic Field Management**: Cards expand during planning, scrub automatically on archive
- **Provider Abstraction**: Kanban provider (full features) or checklist fallback (markdown-based)
- **Gate Validation**: PR URL enforcement (v0.7.0), full gate suite planned (v0.7.1)
- **WIP Enforcement**: Configurable limits per column (active, review)
- **Shared Board Config**: Single YAML source of truth with sc-project-manager (`.project/board.config.yaml`)
- **v0.5 Compliance**: Fenced JSON envelopes, versioned frontmatter, registry attestation
- **Execution Tracking**: pr_url, status_report, actual_cycles, started_at, completed_at, base_branch
- **Integration Ready**: Works with sc-git-worktree for worktree tracking, custom dev/QA agents

## Installation

### Prerequisites

- Python 3.8+
- PyYAML, pydantic (see requirements-dev.txt)
- sc-git-worktree v0.5.2+ (optional but recommended for worktree integration)

### Install via sc-manage

```bash
/sc-manage install sc-kanban
```

### Manual Installation

```bash
# Clone repository
git clone https://github.com/randlee/synaptic-canvas.git
cd synaptic-canvas

# Install dependencies
pip install -r requirements-dev.txt

# Link package to .claude directory
python3 tools/sc-install.py install sc-kanban
```

## Quick Start

### 1. Initialize Board Config

Create `.project/board.config.yaml` (see `templates/board.config.example.yaml`):

```yaml
version: 0.7
board:
  backlog_path: .project/backlog.json
  board_path: .project/board.json
  done_path: .project/done.json
  provider: kanban
```

### 2. Create Backlog Cards (Lean)

Create lean backlog entries with minimal fields:

```json
{
  "sprint_id": "1.1",
  "title": "Project Setup",
  "dependencies": []
}
```

### 3. Plan Sprint Items (Expand to Board)

Use `kanban-card` to expand backlog → board with rich fields:

```bash
# Creates rich board entry with worktree, prompts, acceptance_criteria
kanban-card create --target-status planned \
  --card '{"sprint_id":"1.1","worktree":"main/1-1-setup","dev_prompt":"..."}'
```

### 4. Track Progress

Query cards by status, worktree, or sprint_id:

```bash
# List all active cards
kanban-query --status active

# Find specific card
kanban-query --worktree main/1-1-setup
```

### 5. Archive Completed Work (Automatic Scrubbing)

Transition review → done automatically scrubs rich fields:

```bash
# Moves to done.json, keeps only: sprint_id, title, pr_url, completed_at, actual_cycles
kanban-transition --sprint-id 1.1 --target-status done
```

## Configuration

### Board Config Structure

`.project/board.config.yaml` defines:
- File paths (backlog, board, done)
- Provider selection (kanban vs checklist)
- WIP limits per column
- Card field schemas
- Agent references

### Provider Selection

**Kanban Provider** (default):
- Three-file lifecycle with automatic expansion/scrubbing
- Gate validation (PR, git, worktree)
- WIP enforcement
- Rich execution tracking

**Checklist Provider** (fallback):
- Markdown-based workflow (roadmap.md + prompts/)
- No gates or WIP enforcement
- Lightweight for small projects

Set `provider: checklist` in board config to use checklist mode.

## Integration

### With sc-project-manager

Shared board config enables PM agents to:
- Read backlog and plan sprint items
- Coordinate dev/QA agent execution
- Track execution metadata (PR URLs, cycle counts)
- Archive completed work with automatic scrubbing

### With sc-git-worktree

Worktree naming convention: `<project-branch>/<sprint-id>-<sprint-name>`

Example: `main/1-1-project-setup`

Cards reference worktrees for 1:1 tracking.

### Custom Dev/QA Agents

Board cards can specify custom agents:
- `dev_agent`: Agent for implementation
- `qa_agent`: Agent for testing/validation
- `dev_prompt`: Rich context for dev agent
- `qa_prompt`: Acceptance criteria for QA agent

## Commands

| Command | Agent | Purpose |
|---------|-------|---------|
| `/kanban create` | kanban-card | Create/update cards |
| `/kanban move` | kanban-transition | Move cards across columns |
| `/kanban archive` | kanban-transition | Move to done with scrubbing |
| `/kanban list` | kanban-query | Query cards by filters |
| `/kanban status` | kanban-query | Board status summary |

## Documentation

- **[Use Cases](./USE-CASES.md)**: 7 detailed scenarios with step-by-step examples
- **[Troubleshooting](./TROUBLESHOOTING.md)**: 10+ common issues with diagnostics and fixes
- **[Changelog](./CHANGELOG.md)**: Version history and release notes

## Card Lifecycle

### Backlog (Lean)
Fields: `sprint_id`, `title`, `dependencies`

### Board (Rich)
Adds: `worktree`, `dev_agent`, `qa_agent`, `dev_prompt`, `qa_prompt`, `acceptance_criteria`, `max_retries`, `base_branch`, `status`, `pr_url`, `status_report`, `actual_cycles`, `started_at`, `completed_at`

### Done (Scrubbed)
Keeps: `sprint_id`, `title`, `pr_url`, `completed_at`, `actual_cycles`

## Security

- Local file operations only; no remote access
- Gate validation prevents incomplete work from progressing
- WIP enforcement limits concurrent active work
- All state changes logged for audit

## Status

**v0.7.0 (Current)**:
- ✅ Three-file lifecycle operations
- ✅ Board config validation (Pydantic v2 strict mode)
- ✅ Provider abstraction (kanban/checklist)
- ✅ Automatic card scrubbing
- ✅ WIP enforcement
- ✅ PR URL gate validation
- ✅ Comprehensive test suite (85-95% coverage)

**v0.7.1 (Planned)**:
- Full gate execution suite (PR state, git cleanliness, worktree validation)
- Advanced query operations (rollups, dependencies)
- Template scaffolding wizard

## License

MIT License - see LICENSE file for details

## Contributing

See main repository [CONTRIBUTING.md](../../CONTRIBUTING.md) for package authoring guidelines.

## Support

- **Issues**: https://github.com/randlee/synaptic-canvas/issues
- **Documentation**: https://github.com/randlee/synaptic-canvas/tree/main/docs
- **Discussions**: https://github.com/randlee/synaptic-canvas/discussions
