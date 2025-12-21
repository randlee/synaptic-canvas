# Getting Started

Welcome to Synaptic Canvas, the plugin marketplace for Claude Code.

## What is Synaptic Canvas?

Synaptic Canvas extends Claude Code with installable plugins that add new capabilities:

- **Workflow automation** — GitHub issues, CI/CD, project management
- **Git operations** — Worktrees, branch management, PR creation
- **Utilities** — Delays, polling, package management

Each plugin is documented with interactive diagrams showing exactly how the workflow operates.

## Installation

### Installing sc-manage (Bootstrap)

First, install the package manager:

```bash
# From any repository with Claude Code
/sc-manage --install sc-manage --global
```

### Installing Plugins

Once sc-manage is installed:

```bash
# List available plugins
/sc-manage --list

# Install a plugin locally (to current repo)
/sc-manage --install sc-github-issue

# Install globally (available in all repos)
/sc-manage --install sc-delay-tasks --global
```

## Understanding Plugin Documentation

Each plugin page features:

### 1. Interactive Workflow Diagram

Click any node to explore:
- **Input/Output schemas** — What data flows in and out
- **Context additions** — What gets added to the workflow state
- **Error handling** — What can go wrong and recovery paths

### 2. Node Types

| Type | Visual | Description |
|------|--------|-------------|
| Entry | 🔵 Blue | User command entry point |
| Agent | 🟡 Yellow | Automated agent execution |
| Gate | 🟣 Purple (dashed) | User decision point |
| Success | 🟢 Green | Successful completion |
| Error | 🔴 Red | Error state |

### 3. User Decision Gates

Gates are interactive prompts where the workflow pauses for user input:

```json
{
  "type": "confirmation_gate",
  "message": "Ready to proceed?",
  "options": {
    "proceed": "Continue workflow",
    "cancel": "Abort"
  }
}
```

Most gates can be skipped with `--yolo` flag for automation.

## Plugin Categories

### Workflow Automation
- [sc-github-issue](/plugins/sc-github-issue) — GitHub issue management
- [sc-ci-automation](/plugins/sc-ci-automation) — CI quality gates

### Git Operations
- [sc-git-worktree](/plugins/sc-git-worktree) — Worktree management

### Utilities
- [sc-delay-tasks](/plugins/sc-delay-tasks) — Async polling utilities
- [sc-manage](/plugins/sc-manage) — Package management

## Next Steps

1. Browse the [Plugins](/plugins/) to see what's available
2. Install `sc-manage` to get started
3. Try `sc-github-issue` for a full-featured example
