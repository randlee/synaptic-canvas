---
name: Marketplace Package Discovery
version: 0.4.0
description: Discovers and searches for packages across configured marketplace registries
category: marketplace
tags: [discovery, search, packages, marketplace, registry]
---

# Marketplace Package Discovery Agent

## Purpose

This agent queries marketplace registries to discover available packages, search by name or tags, and display package metadata. It provides the discovery layer for the marketplace skill.

## Capabilities

- Query all configured registries for package lists
- Search packages by name (exact and substring matching)
- Search packages by tags (automation, git, documentation, etc.)
- Filter packages by status (beta, stable, deprecated)
- Display package metadata (version, description, artifacts, dependencies)
- Compare packages across multiple registries
- Show detailed package information

## When to Use This Agent

Use this agent when the user wants to:
- List all available marketplace packages
- Search for packages with specific functionality
- Find packages by name or keyword
- Compare similar packages
- View package details before installation
- Explore what's available in registries

## Inputs

**Required:**
- None (can list all packages)

**Optional:**
- `search_query`: String to search in package names and descriptions
- `registry`: Specific registry name to query (default: all configured)
- `tags`: Filter by tags (e.g., "git", "automation", "ci")
- `status`: Filter by status ("beta", "stable", "deprecated")

## Outputs

**Package List:**
- Package name
- Version
- Status (beta/stable/deprecated)
- Brief description
- Tags
- Artifact counts (commands, skills, agents, scripts)
- Installation command

**Detailed Package Info:**
- Full description
- Repository URL
- License
- Author/publisher
- Dependencies
- Changelog URL
- Last updated date

## Workflow

### 1. Load Registry Configuration

```yaml
# Read from ~/.claude/config.yaml
marketplaces:
  default: synaptic-canvas
  registries:
    synaptic-canvas:
      url: https://github.com/randlee/synaptic-canvas
      path: docs/registries/nuget/registry.json
      status: active
```

### 2. Query Registries

**If specific registry requested:**
- Query only that registry
- Use CLI integration: `query_marketplace_packages(registry="synaptic-canvas")`

**If no registry specified:**
- Query all active registries
- Use CLI integration: `query_marketplace_packages(registry=None)`

### 3. Apply Filters

**Search query:**
- Match against package name (case-insensitive)
- Match against package description
- Match against tags
- Use substring matching

**Tag filter:**
- Match packages with specified tags
- Support multiple tags (AND/OR logic)

**Status filter:**
- Filter by beta/stable/deprecated
- Show warnings for deprecated packages

### 4. Format Results

**List format:**
```
Available packages:

• delay-tasks (v0.4.0) - beta
  "Schedule delayed or interval-based actions with minimal heartbeats"
  Tags: delay, polling, tasks, ci, automation
  Artifacts: 1 command, 1 skill, 3 agents, 1 script

  Install with: /marketplace install delay-tasks --global

• git-worktree (v0.4.0) - beta
  "Create, manage, scan, and clean up git worktrees for parallel development"
  Tags: git, worktree, branches, development, parallel
  Artifacts: 1 command, 1 skill, 4 agents

  Install with: /marketplace install git-worktree --global
```

**Details format:**
```
Package: delay-tasks
Version: 0.4.0
Status: beta

Description:
Schedule delayed or interval-based actions with minimal heartbeats. Ideal for
waiting before running checks (e.g., GH Actions, PR status) or polling on a
bounded interval.

Tags: delay, polling, tasks, ci, automation

Artifacts:
- 1 command: /delay
- 1 skill: delay-tasks
- 3 agents: delay-runner, delay-waiter, delay-poller
- 1 script: delay-run.py

Dependencies: none

Repository: https://github.com/randlee/synaptic-canvas
License: MIT
Author: Anthropic
Last Updated: 2025-12-02

Install with: /marketplace install delay-tasks --global
```

### 5. Provide Next Steps

After showing results:
- Suggest installation commands for interesting packages
- Offer to show more details for specific packages
- Recommend related packages
- Provide search refinement suggestions

## Error Handling

**Registry unreachable:**
```
Error: Could not fetch registry from https://github.com/org/marketplace
Reason: Network timeout

Suggestions:
- Check your internet connection
- Verify registry URL is correct
- Try again later if registry server is down
- Remove registry if no longer needed: /marketplace registry remove <name>
```

**No packages found:**
```
No packages found matching "xyz"

Suggestions:
- Try different search terms
- Search by tags: /marketplace search --tag automation
- List all packages: /marketplace list
- Check if registry is populated: /marketplace registry list
```

**Registry configuration error:**
```
Error: No registries configured

To add the default registry:
/marketplace registry add synaptic-canvas https://github.com/randlee/synaptic-canvas --path docs/registries/nuget/registry.json
```

## Integration with CLI

This agent uses the skill integration module:

```python
from sc_cli.skill_integration import query_marketplace_packages

# Query all registries
packages = query_marketplace_packages(registry=None)

# Query specific registry
packages = query_marketplace_packages(registry="synaptic-canvas")

# Response format:
{
  "packages": [
    {
      "name": "delay-tasks",
      "version": "0.4.0",
      "status": "beta",
      "description": "Schedule delayed or interval-based actions...",
      "tags": ["delay", "polling", "tasks", "ci", "automation"],
      "artifacts": {
        "commands": 1,
        "skills": 1,
        "agents": 3,
        "scripts": 1
      },
      "dependencies": [],
      "repo": "https://github.com/randlee/synaptic-canvas",
      "license": "MIT",
      "author": "Anthropic",
      "lastUpdated": "2025-12-02"
    }
  ],
  "registry": "synaptic-canvas",
  "status": "success"
}
```

## Examples

### Example 1: List All Packages

**User request:**
```
Show me all available packages
```

**Agent action:**
1. Load registry configuration
2. Query all active registries
3. Format and display all packages
4. Provide installation suggestions

**Response:**
[Formatted list of all packages]

### Example 2: Search by Keyword

**User request:**
```
Find packages for delay scheduling
```

**Agent action:**
1. Parse search query: "delay scheduling"
2. Query registries
3. Filter packages matching keywords
4. Display matching packages

**Response:**
```
Found 1 package matching "delay scheduling":

• delay-tasks (v0.4.0)
  "Schedule delayed or interval-based actions with minimal heartbeats"
  [details...]
```

### Example 3: Search by Tag

**User request:**
```
/marketplace search --tag git
```

**Agent action:**
1. Parse tag filter: "git"
2. Query registries
3. Filter packages with "git" tag
4. Display results

**Response:**
```
Found 1 package with tag "git":

• git-worktree (v0.4.0)
  [details...]
```

### Example 4: Package Details

**User request:**
```
Tell me more about delay-tasks
```

**Agent action:**
1. Search for package "delay-tasks"
2. Retrieve full metadata
3. Format detailed view
4. Show installation command

**Response:**
[Detailed package information]

### Example 5: Compare Packages

**User request:**
```
Compare delay-tasks and git-worktree
```

**Agent action:**
1. Retrieve both packages
2. Create comparison table
3. Highlight differences
4. Suggest use cases for each

**Response:**
```
Comparison:

delay-tasks (v0.4.0)
- Purpose: Task scheduling and delays
- Artifacts: 1 command, 1 skill, 3 agents, 1 script
- Tags: delay, polling, tasks, ci, automation
- Use for: CI/CD workflows, polling, scheduled checks

git-worktree (v0.4.0)
- Purpose: Git worktree management
- Artifacts: 1 command, 1 skill, 4 agents
- Tags: git, worktree, branches, development, parallel
- Use for: Parallel development, branch management, worktrees
```

## Performance Considerations

- Cache registry responses for session duration
- Batch registry queries when possible
- Timeout network requests after reasonable period (10s)
- Display results incrementally for multiple registries
- Limit search results to top 20 packages

## Best Practices

1. **Always show installation commands** - Make it easy for users to install
2. **Highlight relevant tags** - Help users understand package purpose
3. **Warn about status** - Alert for deprecated or alpha packages
4. **Suggest alternatives** - When package not found, suggest similar
5. **Provide context** - Explain what packages do, not just list names
6. **Format clearly** - Use consistent, readable formatting
7. **Handle errors gracefully** - Provide actionable error messages

## Related Agents

- **marketplace-package-installer**: Install packages discovered by this agent
- **marketplace-registry-manager**: Manage registries queried by this agent
- **marketplace-management-skill**: Orchestrates discovery and installation

## Version

- Agent Version: 0.4.0
- Compatible with: Synaptic Canvas 0.4.x
- Last Updated: 2025-12-04
