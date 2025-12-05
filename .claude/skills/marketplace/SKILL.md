# Marketplace Package Manager

## Overview

The Marketplace Package Manager skill provides a comprehensive interface for discovering, managing, and installing Synaptic Canvas marketplace packages directly through Claude. This skill bridges the gap between Claude's conversational interface and the marketplace CLI, enabling natural language package management.

## Description

Discover and manage Synaptic Canvas marketplace packages through natural conversation. List available packages, search by functionality, install packages to your Claude environment, and manage marketplace registries - all without leaving your Claude session.

## Features

### Package Discovery
- **List All Packages**: Browse all available packages in configured marketplaces
- **Search by Name**: Find packages matching specific keywords
- **Search by Tags**: Discover packages by functionality (automation, git, documentation, etc.)
- **Package Details**: View comprehensive metadata including description, version, dependencies, and artifacts

### Package Installation
- **One-Command Install**: Install packages with simple commands
- **Scope Control**: Install globally (--global) or locally (--local)
- **Version Management**: Track installed package versions
- **Dependency Resolution**: View and manage package dependencies
- **Installation Verification**: Confirm successful installation with file checks

### Registry Management
- **List Registries**: View all configured marketplace registries
- **Add Registries**: Register custom marketplace sources
- **Remove Registries**: Clean up unused registries
- **Default Registry**: Configure which marketplace is queried by default
- **Registry Status**: Check registry health and connectivity

### User Experience
- **Natural Language**: Use conversational commands like "find delay package" or "show me automation tools"
- **Guided Installation**: Step-by-step prompts for installation decisions
- **Clear Feedback**: Informative status messages and error explanations
- **Next Steps**: Actionable suggestions after each operation

## Capabilities

This skill provides:

1. **Package Discovery Agent** - Query and search marketplace registries
2. **Package Installer Agent** - Handle package installation with verification
3. **Registry Manager Agent** - Manage marketplace registry configuration
4. **Marketplace Command** - Slash command interface (`/marketplace`)
5. **Integration Functions** - Python API for skill-to-CLI communication

## Prerequisites

- Synaptic Canvas CLI installed (`sc-install` command available)
- Python 3.12 or higher
- PyYAML library (for config management)
- Git (for repository-based packages)
- Network access (for remote registry queries)

## Installation

The marketplace skill is typically pre-installed with Synaptic Canvas. To install or update:

```bash
sc-install install marketplace-skill --global
```

## Getting Started

### Quick Start Examples

**List all available packages:**
```
/marketplace list
```
or conversationally:
```
Show me all available marketplace packages
```

**Search for specific functionality:**
```
/marketplace search delay
```
or:
```
Find packages for scheduling delayed tasks
```

**Install a package:**
```
/marketplace install delay-tasks --global
```
or:
```
Install the delay-tasks package to my global Claude directory
```

**Manage registries:**
```
/marketplace registry list
```
or:
```
Show me my configured marketplace registries
```

## Agents

This skill provides four specialized agents:

### 1. marketplace-package-discovery
Discovers and searches for packages across configured registries.

**Use when you need to:**
- Browse available packages
- Search for specific functionality
- View package details and metadata
- Compare packages across registries

### 2. marketplace-package-installer
Installs packages from marketplace registries.

**Use when you need to:**
- Install a specific package
- Choose installation scope (global/local)
- Verify installation success
- Handle installation errors

### 3. marketplace-registry-manager
Manages marketplace registry configuration.

**Use when you need to:**
- View configured registries
- Add custom registries
- Remove unused registries
- Configure default registry

### 4. marketplace-management-skill
Main orchestration agent that routes requests to appropriate sub-agents.

**Use when you need to:**
- General marketplace operations
- Natural language marketplace queries
- Multi-step marketplace workflows

## Commands

### /marketplace

Unified command interface for marketplace operations.

**Syntax:**
```
/marketplace <action> [options]
```

**Actions:**
- `list` - List all available packages
- `search <query>` - Search packages by name or tags
- `install <package>` - Install a package
- `registry list` - Show configured registries
- `registry add <name> <url>` - Add new registry
- `registry remove <name>` - Remove registry

**Options:**
- `--global` - Install to ~/.claude (user-level)
- `--local` - Install to ./.claude-local (project-level)
- `--force` - Overwrite existing files
- `--registry <name>` - Use specific registry

## Examples

### Example 1: Discover and Install Package
```
User: "I need a way to schedule delayed tasks in my workflows"

Claude: Let me search for packages related to task scheduling...
[Uses marketplace-package-discovery agent]

Found: delay-tasks package - "Schedule delayed or interval-based actions"
Would you like to install this package?

User: "Yes, install it globally"

Claude: Installing delay-tasks to ~/.claude...
[Uses marketplace-package-installer agent]
✓ Installed delay-tasks successfully
✓ Added 1 command, 1 skill, 3 agents, 1 script
```

### Example 2: Manage Registries
```
User: "/marketplace registry list"

Configured registries:

* synaptic-canvas    https://github.com/randlee/synaptic-canvas
  path:              docs/registries/nuget/registry.json
  status:            active
  added:             2025-12-04

Use "/marketplace registry add <name> <url>" to add more registries.
```

### Example 3: Search Packages
```
User: "Find me packages for git workflows"

Claude: Searching marketplace for git-related packages...

Found 1 package:

• git-worktree (v0.4.0)
  "Create, manage, scan, and clean up git worktrees for parallel development"
  Tags: git, worktree, branches, development, parallel
  Artifacts: 1 command, 1 skill, 4 agents

Install with: /marketplace install git-worktree --global
```

## Integration with CLI

This skill integrates with the `sc-install` CLI through the `skill_integration.py` module:

**Available Functions:**
- `query_marketplace_packages()` - Fetch package lists from registries
- `install_marketplace_package()` - Execute package installation
- `get_marketplace_config()` - Retrieve registry configuration

These functions provide a Python API for skills and agents to interact with the marketplace CLI without direct subprocess calls.

## Configuration

Marketplace configuration is stored in `~/.claude/config.yaml`:

```yaml
marketplaces:
  default: synaptic-canvas
  registries:
    synaptic-canvas:
      url: https://github.com/randlee/synaptic-canvas
      path: docs/registries/nuget/registry.json
      status: active
      added_date: 2025-12-04
```

## Troubleshooting

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues and solutions.

**Quick troubleshooting:**
- **Registry not accessible**: Check network connection and registry URL
- **Package not found**: Verify package name and registry configuration
- **Installation fails**: Check write permissions and disk space
- **Command not found**: Ensure `sc-install` is in PATH

## Use Cases

See [USE-CASES.md](./USE-CASES.md) for detailed use case scenarios including:
1. Discover available marketplace packages
2. Search for specific package functionality
3. Install package from marketplace
4. List packages in specific registry
5. Compare packages across registries
6. Update package installation
7. Troubleshoot package issues

## Version

**Skill Version**: 0.4.0
**Compatible with**: Synaptic Canvas 0.4.x
**Last Updated**: 2025-12-04

## License

MIT License - See repository for details

## Support

- Documentation: See README.md and USE-CASES.md
- Troubleshooting: See TROUBLESHOOTING.md
- Issues: GitHub repository issue tracker
- Discussions: GitHub repository discussions
