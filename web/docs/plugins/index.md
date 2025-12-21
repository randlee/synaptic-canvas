# Plugins

Synaptic Canvas plugins extend Claude Code with specialized capabilities. Each plugin is documented with interactive workflow diagrams showing how users interact with the system.

## Understanding Plugin Documentation

Each plugin page includes:

1. **Workflow Overview** — An interactive D3.js diagram showing the plugin's state machine
2. **Click to Explore** — Click any node in the diagram to see:
   - Input/output schemas
   - Context additions
   - User gate prompts
   - Error handling
3. **Deep Dive Sections** — Detailed documentation organized by workflow stage

## Plugin Legend

| Node Type | Description |
|-----------|-------------|
| 🔵 **Entry** | User command entry point (`/command`) |
| 🟡 **Agent** | Automated agent execution |
| 🟣 **Gate** | User decision point (JSON prompt) |
| 🟢 **Success** | Workflow completion |
| 🔴 **Error** | Error state with recovery paths |

## Available Plugins

### Workflow Automation

- **[sc-github-issue](/plugins/sc-github-issue)** — Full GitHub issue lifecycle: list, create, update, and fix issues with worktree isolation
- **[sc-ci-automation](/plugins/sc-ci-automation)** — CI quality gates with pull, build, test, and auto-fix

### Git Operations

- **[sc-git-worktree](/plugins/sc-git-worktree)** — Manage git worktrees for isolated development

### Utilities

- **[sc-delay-tasks](/plugins/sc-delay-tasks)** — Polling and delay utilities for async operations
- **[sc-manage](/plugins/sc-manage)** — Install, uninstall, and manage Synaptic Canvas packages
- **[sc-repomix-nuget](/plugins/sc-repomix-nuget)** — Generate repomix context bundles for NuGet packages

## Plugin Dependencies

```
sc-manage (bootstrap)
    │
    └─▶ sc-git-worktree
            │
            └─▶ sc-github-issue
                    │
                    └─▶ sc-ci-automation (optional)

sc-delay-tasks (standalone, used by various plugins)
```
