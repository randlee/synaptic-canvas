---
command: marketplace
description: Discover, search, install, and manage Synaptic Canvas marketplace packages
version: 0.4.0
category: package-management
---

# /marketplace - Marketplace Package Manager

Unified command interface for discovering, installing, and managing Synaptic Canvas marketplace packages and registries.

## Synopsis

```
/marketplace <action> [options]
```

## Actions

### list
List all available packages from configured registries.

**Usage:**
```
/marketplace list [--registry <name>]
```

**Options:**
- `--registry <name>`: Query specific registry only

**Example:**
```
/marketplace list
/marketplace list --registry synaptic-canvas
```

**Output:**
```
Available packages:

• delay-tasks (v0.4.0) - beta
  "Schedule delayed or interval-based actions..."
  Tags: delay, polling, tasks, ci, automation
  Install: /marketplace install delay-tasks --global

• git-worktree (v0.4.0) - beta
  ...
```

---

### search
Search for packages by name, description, or tags.

**Usage:**
```
/marketplace search <query> [--registry <name>] [--tag <tag>]
```

**Options:**
- `<query>`: Search term (name, description, keywords)
- `--registry <name>`: Search specific registry only
- `--tag <tag>`: Filter by tag

**Examples:**
```
/marketplace search delay
/marketplace search automation
/marketplace search git --tag worktree
/marketplace search --registry my-org ci
```

**Output:**
```
Found 1 package matching "delay":

• delay-tasks (v0.4.0)
  "Schedule delayed or interval-based actions..."
  Install: /marketplace install delay-tasks --global
```

---

### install
Install a package from marketplace.

**Usage:**
```
/marketplace install <package> (--global | --local) [--force] [--registry <name>]
```

**Options:**
- `<package>`: Package name to install
- `--global`: Install to ~/.claude (required or --local)
- `--local`: Install to ./.claude-local (required or --global)
- `--force`: Overwrite existing files
- `--registry <name>`: Install from specific registry

**Examples:**
```
/marketplace install delay-tasks --global
/marketplace install git-worktree --local
/marketplace install sc-manage --global --force
/marketplace install custom-package --global --registry my-org
```

**Output:**
```
Installing delay-tasks to ~/.claude...
✓ Package validated
✓ Dependencies checked
✓ Artifacts installed (1 command, 1 skill, 3 agents, 1 script)
✓ Registry updated
✓ Installation verified

Successfully installed delay-tasks (v0.4.0)

Try: /delay help
```

---

### info
Show detailed information about a package.

**Usage:**
```
/marketplace info <package> [--registry <name>]
```

**Options:**
- `<package>`: Package name
- `--registry <name>`: Query specific registry

**Example:**
```
/marketplace info delay-tasks
```

**Output:**
```
Package: delay-tasks
Version: 0.4.0
Status: beta

Description:
Schedule delayed or interval-based actions with minimal heartbeats...

Tags: delay, polling, tasks, ci, automation

Artifacts:
- 1 command: /delay
- 1 skill: delay-tasks skill
- 3 agents: delay-runner, delay-waiter, delay-poller
- 1 script: delay-run.py

Dependencies: none

Repository: https://github.com/randlee/synaptic-canvas
License: MIT
Last Updated: 2025-12-02

Install: /marketplace install delay-tasks --global
```

---

### registry list
List all configured marketplace registries.

**Usage:**
```
/marketplace registry list
```

**Output:**
```
Configured registries:

* synaptic-canvas    https://github.com/randlee/synaptic-canvas
  path:              docs/registries/nuget/registry.json
  status:            active
  added:             2025-12-04

Total: 1 registry
(* = default registry)
```

---

### registry add
Add a new marketplace registry.

**Usage:**
```
/marketplace registry add <name> <url> [--path <path>]
```

**Options:**
- `<name>`: Unique registry name (alphanumeric, dash, underscore)
- `<url>`: Registry URL (https:// or http://)
- `--path <path>`: Relative path to registry.json (optional)

**Examples:**
```
/marketplace registry add my-org https://github.com/my-org/marketplace
/marketplace registry add company https://github.com/company/packages --path custom/registry.json
```

**Output:**
```
✓ Added registry: my-org
  URL: https://github.com/my-org/marketplace
  Status: active

Use: /marketplace list --registry my-org
```

---

### registry remove
Remove a marketplace registry.

**Usage:**
```
/marketplace registry remove <name>
```

**Options:**
- `<name>`: Registry name to remove

**Example:**
```
/marketplace registry remove old-registry
```

**Output:**
```
✓ Removed registry: old-registry

Remaining registries: 1
Default: synaptic-canvas
```

---

### registry set-default
Set the default marketplace registry.

**Usage:**
```
/marketplace registry set-default <name>
```

**Options:**
- `<name>`: Registry name to set as default

**Example:**
```
/marketplace registry set-default my-org
```

**Output:**
```
✓ Default registry changed to: my-org

All package queries will use my-org by default.
```

---

## Natural Language Alternative

Instead of using slash commands, you can use natural language with the marketplace skill:

**Discovery:**
- "List all marketplace packages"
- "Show me available packages"
- "What packages are in the marketplace?"

**Search:**
- "Find packages for CI/CD"
- "Search for git workflow tools"
- "Show me automation packages"

**Installation:**
- "Install delay-tasks globally"
- "Add git-worktree to my Claude setup"
- "Set up the sc-repomix-nuget package"

**Registry Management:**
- "Show my registries"
- "Add a custom registry"
- "Remove old-registry"

Claude will understand these requests and execute the appropriate marketplace operations.

---

## Examples

### Example 1: Discover and Install

```bash
# List available packages
/marketplace list

# Found delay-tasks looks useful, get details
/marketplace info delay-tasks

# Install globally
/marketplace install delay-tasks --global

# Try it out
/delay help
```

### Example 2: Search and Install

```bash
# Search for git tools
/marketplace search git

# Install git-worktree
/marketplace install git-worktree --global

# Create a worktree
/git-worktree create feature/new-feature
```

### Example 3: Add Custom Registry

```bash
# Add organization registry
/marketplace registry add my-org https://github.com/my-org/marketplace

# List registries to verify
/marketplace registry list

# Search in new registry
/marketplace search --registry my-org

# Install from custom registry
/marketplace install custom-package --global --registry my-org
```

### Example 4: Update Package

```bash
# Reinstall with latest version
/marketplace install delay-tasks --global --force

# Verify update
/delay --version
```

---

## Agents

This command works with these agents:

- **marketplace-package-discovery**: Lists and searches packages
- **marketplace-package-installer**: Installs packages
- **marketplace-registry-manager**: Manages registries
- **marketplace-management-skill**: Orchestrates operations

These agents are automatically invoked when you use the `/marketplace` command or natural language requests.

---

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

---

## Error Handling

### Package not found
```
Error: Package "xyz" not found

Try:
- /marketplace list (see all packages)
- /marketplace search xyz (find similar)
- /marketplace registry list (check registries)
```

### Permission denied
```
Error: Permission denied writing to ~/.claude

Fix:
- mkdir -p ~/.claude
- sudo chown -R $USER:$USER ~/.claude
- Or try: /marketplace install xyz --local
```

### Registry unreachable
```
Error: Could not fetch registry from [URL]

Check:
- Network connection
- Registry URL is correct
- Registry server is online
```

### Invalid registry name
```
Error: Invalid registry name "my org"

Requirements:
- Alphanumeric characters only
- May contain dash (-) or underscore (_)
- No spaces or special characters
```

---

## Tips

1. **Use natural language**: Easier than remembering command syntax
2. **Start with list**: Browse what's available first
3. **Read package info**: Understand packages before installing
4. **Test locally**: Use --local to test before global install
5. **Keep registries clean**: Remove unused registries
6. **Check dependencies**: Verify prerequisites before installing

---

## Documentation

- Skill documentation: `.claude/skills/marketplace/SKILL.md`
- User guide: `.claude/skills/marketplace/README.md`
- Use cases: `.claude/skills/marketplace/USE-CASES.md`
- Troubleshooting: `.claude/skills/marketplace/TROUBLESHOOTING.md`

---

## See Also

- `/delay` - Task scheduling (from delay-tasks package)
- `/git-worktree` - Git worktree management
- `/sc-manage` - Synaptic Canvas management
- `/sc-repomix-nuget` - NuGet repository analysis

---

## Version

- Command Version: 0.4.0
- Marketplace Skill: 0.4.0
- Compatible with: Synaptic Canvas 0.4.x
- Last Updated: 2025-12-04
