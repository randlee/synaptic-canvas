# Marketplace Package Manager - User Guide

Welcome to the Marketplace Package Manager! This skill enables you to discover, install, and manage Synaptic Canvas packages directly through Claude, using natural language or simple commands.

## Quick Start

### List Available Packages

**Command:**
```
/marketplace list
```

**Natural language:**
```
Show me all available packages
What packages are available in the marketplace?
List all marketplace packages
```

**What you'll see:**
- Package names and versions
- Brief descriptions
- Installation commands

### Search for Packages

**Command:**
```
/marketplace search <keyword>
```

**Natural language:**
```
Find packages for delay scheduling
Search for git workflow tools
What packages help with documentation?
```

**Search tips:**
- Search by package name: "delay", "worktree", "repomix"
- Search by functionality: "git", "automation", "documentation"
- Search by tag: "ci", "nuget", "tasks"

### Install a Package

**Command:**
```
/marketplace install <package-name> --global
```

**Natural language:**
```
Install delay-tasks globally
Add the git-worktree package to my global Claude setup
Install repomix-nuget for this project
```

**Installation scopes:**
- `--global`: Install to ~/.claude (available system-wide)
- `--local`: Install to ./.claude-local (project-specific)

### Manage Registries

**List registries:**
```
/marketplace registry list
```

**Add a registry:**
```
/marketplace registry add custom-registry https://github.com/org/marketplace
```

**Remove a registry:**
```
/marketplace registry remove custom-registry
```

## Common Workflows

### Workflow 1: Discover and Install

1. **Search for what you need:**
   ```
   Find packages for scheduling tasks
   ```

2. **Review the results:**
   - Read package descriptions
   - Check versions and dependencies
   - Note the installation command

3. **Install the package:**
   ```
   /marketplace install delay-tasks --global
   ```

4. **Verify installation:**
   - Check the success message
   - Try using the new package features

### Workflow 2: Explore Categories

1. **List all packages:**
   ```
   /marketplace list
   ```

2. **Browse by category:**
   - Automation tools
   - Development tools
   - Documentation tools
   - Package management tools

3. **Get package details:**
   ```
   Tell me more about the git-worktree package
   ```

4. **Install if useful:**
   ```
   /marketplace install git-worktree --global
   ```

### Workflow 3: Custom Registry Setup

1. **Check current registries:**
   ```
   /marketplace registry list
   ```

2. **Add your custom registry:**
   ```
   /marketplace registry add my-org https://github.com/my-org/marketplace --path packages/registry.json
   ```

3. **Verify registry was added:**
   ```
   /marketplace registry list
   ```

4. **Search packages in new registry:**
   ```
   /marketplace search --registry my-org
   ```

## Package Information

When you view package details, you'll see:

- **Name**: Package identifier (e.g., "delay-tasks")
- **Version**: Current version (e.g., "0.4.0")
- **Status**: Development status (beta, stable, deprecated)
- **Description**: What the package does
- **Tags**: Functionality keywords
- **Artifacts**: What's included (commands, skills, agents, scripts)
- **Dependencies**: Required software or packages
- **Repository**: Source code location
- **License**: Usage terms

## Installation Details

### Global Installation (--global)

**Location**: `~/.claude/`

**Use when:**
- You want packages available in all projects
- You frequently use the package
- It's a general-purpose tool

**Example:**
```bash
/marketplace install delay-tasks --global
```

### Local Installation (--local)

**Location**: `./.claude-local/`

**Use when:**
- Package is project-specific
- Testing before global install
- Different versions needed per project

**Example:**
```bash
/marketplace install delay-tasks --local
```

### Installation Process

1. **Validation**: Checks package exists and is accessible
2. **Dependency Check**: Verifies required dependencies
3. **File Copy**: Installs commands, skills, agents, and scripts
4. **Configuration**: Updates registry and config files
5. **Verification**: Confirms all files installed correctly
6. **Feedback**: Shows installation summary

## Registry Management

### Understanding Registries

A **registry** is a package catalog - a source where packages are listed and described. Think of it like an app store catalog.

**Default registry:**
- Name: `synaptic-canvas`
- URL: https://github.com/randlee/synaptic-canvas
- Contains: Official Synaptic Canvas packages

### Adding Custom Registries

You can add registries for:
- Your organization's private packages
- Community package collections
- Experimental or beta packages

**Syntax:**
```
/marketplace registry add <name> <url> [--path <path-to-registry.json>]
```

**Example:**
```
/marketplace registry add my-team https://github.com/my-team/claude-packages --path registry/packages.json
```

### Registry Configuration

Registries are stored in `~/.claude/config.yaml`:

```yaml
marketplaces:
  default: synaptic-canvas
  registries:
    synaptic-canvas:
      url: https://github.com/randlee/synaptic-canvas
      path: docs/registries/nuget/registry.json
      status: active
      added_date: 2025-12-04
    my-team:
      url: https://github.com/my-team/claude-packages
      path: registry/packages.json
      status: active
      added_date: 2025-12-04
```

## Natural Language Examples

The marketplace skill understands natural language queries. Here are examples:

### Discovery
- "What packages are available?"
- "Show me all marketplace packages"
- "List packages in the marketplace"

### Search
- "Find packages for git workflows"
- "Search for automation tools"
- "What packages help with delay scheduling?"
- "Show me documentation packages"

### Installation
- "Install delay-tasks globally"
- "Add git-worktree to my Claude setup"
- "Install the repomix-nuget package"
- "Set up delay-tasks for this project"

### Registry Management
- "Show my configured registries"
- "Add a custom registry"
- "List all marketplace sources"
- "Remove the old-registry"

### Information
- "Tell me about the delay-tasks package"
- "What does git-worktree do?"
- "Show details for repomix-nuget"
- "What's included in sc-manage?"

## Integration with Other Skills

The marketplace skill works well with:

### delay-tasks
Install with: `/marketplace install delay-tasks --global`

Use for: Scheduling delayed actions, CI/CD polling, interval-based tasks

### git-worktree
Install with: `/marketplace install git-worktree --global`

Use for: Managing parallel git worktrees, branch management, development workflows

### repomix-nuget
Install with: `/marketplace install repomix-nuget --global`

Use for: NuGet repository analysis, package documentation, .NET project context

### sc-manage
Install with: `/marketplace install sc-manage --global`

Use for: Managing Synaptic Canvas itself, package utilities, system tools

## Tips and Best Practices

### Package Discovery
1. **Start broad**: List all packages first to get familiar
2. **Use tags**: Search by functionality tags for better results
3. **Read descriptions**: Understand what each package does before installing
4. **Check dependencies**: Ensure you have required software

### Installation
1. **Global for common tools**: Install frequently-used packages globally
2. **Local for experiments**: Test new packages locally first
3. **Use --force sparingly**: Only override existing files when necessary
4. **Verify after install**: Check that commands and agents are available

### Registry Management
1. **Keep registries clean**: Remove unused registries
2. **Use descriptive names**: Name custom registries clearly
3. **Document registry URLs**: Keep track of what each registry provides
4. **Set appropriate defaults**: Configure your most-used registry as default

### Troubleshooting
1. **Check error messages**: Read the full error output
2. **Verify prerequisites**: Ensure CLI tools are installed
3. **Test connectivity**: Confirm network access to registries
4. **Review permissions**: Check file system write access

## Next Steps

After familiarizing yourself with the marketplace:

1. **Explore packages**: Browse what's available
2. **Install useful tools**: Add packages that fit your workflow
3. **Try custom registries**: Set up organization-specific packages
4. **Provide feedback**: Report issues or suggest improvements

## Getting Help

If you encounter issues:

1. **Check TROUBLESHOOTING.md**: Common issues and solutions
2. **Review USE-CASES.md**: Detailed workflow examples
3. **Read package documentation**: Each package has its own docs
4. **Check GitHub issues**: Known issues and workarounds

## Examples by Use Case

### For CI/CD Automation
```
# Find automation tools
/marketplace search automation

# Install delay package for CI polling
/marketplace install delay-tasks --global

# Use delay command to wait for builds
/delay wait 5m then check "gh run view"
```

### For Git Workflow Management
```
# Find git tools
/marketplace search git

# Install worktree manager
/marketplace install git-worktree --global

# Create worktrees for parallel development
/git-worktree create feature/new-feature
```

### For Documentation Generation
```
# Find documentation tools
/marketplace search documentation

# Install NuGet context generator
/marketplace install repomix-nuget --global

# Generate repository context
Use repomix-nuget agents to analyze .NET projects
```

### For Package Management
```
# Get package manager tools
/marketplace install sc-manage --global

# Manage Synaptic Canvas packages
Use sc-manage commands to maintain your installation
```

## Skill Architecture

This skill consists of:

- **4 Agents**: Discovery, Installation, Registry Management, Orchestration
- **1 Command**: `/marketplace` with multiple actions
- **Integration Module**: Python API for CLI interaction
- **Configuration**: YAML-based registry management

All components work together to provide seamless package management through Claude.

## Version Compatibility

- **Skill Version**: 0.4.0
- **CLI Version**: Requires sc-install v0.4.0+
- **Python**: Requires Python 3.12+
- **Marketplace**: Compatible with registry schema v2.0.0

## Feedback and Contributions

Help improve the marketplace skill:

- Report bugs in GitHub issues
- Suggest features in discussions
- Contribute to documentation
- Share your custom registries

---

**Ready to start?** Try: `/marketplace list`
