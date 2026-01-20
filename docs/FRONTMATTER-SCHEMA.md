# Frontmatter Schema Documentation

Comprehensive documentation for frontmatter schemas used in Synaptic Canvas marketplace artifacts.

## Overview

Frontmatter is YAML metadata placed at the beginning of markdown files, delimited by triple dashes (`---`). In Synaptic Canvas, frontmatter provides essential metadata for commands, skills, agents, and reference documents that enables:

- **Discovery**: Finding artifacts by name, version, or capabilities
- **Validation**: Ensuring artifacts meet quality standards
- **Registry Integration**: Proper listing in the marketplace
- **Dependency Management**: Understanding artifact relationships
- **Tool Configuration**: Proper execution and permission handling

### Why Frontmatter Matters

1. **Automation**: CI/CD pipelines rely on frontmatter for validation and deployment
2. **Consistency**: Standardized metadata ensures predictable behavior
3. **Discoverability**: Users find artifacts through frontmatter-indexed searches
4. **Versioning**: Proper version tracking enables upgrade paths
5. **Security**: Tool permissions and restrictions are defined in frontmatter

## Common Fields

All artifact types share these common frontmatter fields:

### Required Fields

| Field | Type | Format | Description |
|-------|------|--------|-------------|
| `name` | string | kebab-case | Unique identifier for the artifact |
| `version` | string | semver (X.Y.Z) | Semantic version number |
| `description` | string | plain text | Brief description of the artifact's purpose |

### Field Specifications

#### name
- **Type**: string
- **Format**: kebab-case (lowercase letters, numbers, hyphens)
- **Pattern**: `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`
- **Examples**: `my-command`, `data-processor`, `git-helper-v2`

**Valid names:**
```yaml
name: my-command
name: data-processor
name: ci-automation
```

**Invalid names:**
```yaml
name: MyCommand      # No uppercase
name: my_command     # No underscores
name: -my-command    # Cannot start with hyphen
name: my--command    # No consecutive hyphens
```

#### version
- **Type**: string
- **Format**: Semantic Versioning (semver)
- **Pattern**: `^\d+\.\d+\.\d+$`
- **Examples**: `1.0.0`, `2.3.1`, `0.1.0`

**Valid versions:**
```yaml
version: 1.0.0
version: 2.3.1
version: 0.1.0
```

**Invalid versions:**
```yaml
version: 1.0        # Missing patch version
version: v1.0.0     # No 'v' prefix
version: 1.0.0-beta # No pre-release tags (use separate field)
```

#### description
- **Type**: string
- **Format**: Plain text, single line recommended
- **Length**: 10-200 characters recommended
- **Examples**: `"Automates git commit workflows"`, `"Validates JSON schemas"`

```yaml
description: Automates git commit workflows with conventional commit support
```

## Command Frontmatter

Commands are user-invocable operations that perform specific tasks.

### Schema

```yaml
---
name: string          # Required: kebab-case identifier
version: string       # Required: semver X.Y.Z
description: string   # Required: brief description
options: array        # Optional: command-line options
allowed-tools: string # Optional: permitted tool restrictions
---
```

### Field Details

#### options (optional)
- **Type**: array of objects
- **Purpose**: Define command-line arguments and flags

Each option object contains:
| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | string | Yes | Option name (e.g., `--verbose`) |
| `short` | string | No | Short form (e.g., `-v`) |
| `type` | string | No | Value type: `string`, `boolean`, `number` |
| `default` | any | No | Default value |
| `description` | string | No | Help text for the option |

#### allowed-tools (optional)
- **Type**: string
- **Purpose**: Restrict which tools the command can use
- **Format**: Comma-separated tool names or patterns

### Complete Example

```yaml
---
name: git-commit
version: 1.2.0
description: Automates git commit workflows with conventional commit message formatting
options:
  - name: --message
    short: -m
    type: string
    description: Commit message (required)
  - name: --verbose
    short: -v
    type: boolean
    default: false
    description: Show detailed output
  - name: --dry-run
    type: boolean
    default: false
    description: Show what would be committed without committing
allowed-tools: Bash, Read, Edit
---

# Git Commit Command

This command automates the git commit workflow...
```

## Skill Frontmatter

Skills are reusable capabilities that can be invoked by commands or other skills.

### Schema

```yaml
---
name: string        # Required: kebab-case identifier
version: string     # Required: semver X.Y.Z
description: string # Required: brief description
entry_point: string # Required: path starting with /
---
```

### Field Details

#### entry_point (required)
- **Type**: string
- **Format**: Absolute path starting with `/`
- **Purpose**: Specifies the main entry point for skill invocation
- **Pattern**: `^/[a-z][a-z0-9-/]*$`

**Valid entry points:**
```yaml
entry_point: /process-data
entry_point: /validate/schema
entry_point: /git/commit
```

**Invalid entry points:**
```yaml
entry_point: process-data      # Must start with /
entry_point: /Process-Data     # Must be lowercase
entry_point: /process_data     # Use hyphens, not underscores
```

### Complete Example

```yaml
---
name: data-validation
version: 2.1.0
description: Validates data against configurable schemas with detailed error reporting
entry_point: /validate
---

# Data Validation Skill

This skill provides comprehensive data validation capabilities...
```

## Agent Frontmatter

Agents are autonomous entities with specific configurations and capabilities.

### Schema

```yaml
---
name: string        # Required: kebab-case identifier
version: string     # Required: semver X.Y.Z
description: string # Required: brief description
model: string       # Required: enum [sonnet, opus, haiku]
color: string       # Required: enum [gray, green, purple, blue, red, yellow]
---
```

### Field Details

#### model (required)
- **Type**: string
- **Allowed Values**: `sonnet`, `opus`, `haiku`
- **Purpose**: Specifies the Claude model to use for the agent

| Value | Use Case |
|-------|----------|
| `sonnet` | Balanced performance and capability |
| `opus` | Complex reasoning and analysis |
| `haiku` | Fast, lightweight tasks |

#### color (required)
- **Type**: string
- **Allowed Values**: `gray`, `green`, `purple`, `blue`, `red`, `yellow`
- **Purpose**: Visual identifier for the agent in UI displays

| Color | Suggested Use |
|-------|--------------|
| `gray` | Utility/helper agents |
| `green` | Success/validation agents |
| `purple` | Creative/generation agents |
| `blue` | Information/analysis agents |
| `red` | Critical/security agents |
| `yellow` | Warning/review agents |

### Complete Example

```yaml
---
name: code-reviewer
version: 1.0.0
description: Autonomous code review agent that analyzes PRs for quality and security
model: opus
color: purple
---

# Code Reviewer Agent

This agent performs comprehensive code reviews...
```

## Reference Document Frontmatter

Reference documents provide supplementary information and are the simplest artifact type.

### Schema

```yaml
---
name: string        # Required: kebab-case identifier
version: string     # Required: semver X.Y.Z
description: string # Required: brief description
---
```

### Complete Example

```yaml
---
name: api-reference
version: 1.0.0
description: Complete API reference documentation for the validation module
---

# API Reference

This document provides comprehensive API documentation...
```

## Complete Examples

### Command Example

```yaml
---
name: ci-automation
version: 1.3.0
description: Run CI quality gates with optional auto-fix and PR creation
options:
  - name: --fix
    type: boolean
    default: false
    description: Automatically fix linting issues
  - name: --pr
    type: boolean
    default: false
    description: Create PR after successful validation
  - name: --branch
    short: -b
    type: string
    description: Target branch for PR
allowed-tools: Bash, Read, Edit, Write
---

# CI Automation Command

Automates continuous integration workflows...
```

### Skill Example

```yaml
---
name: git-worktree
version: 2.0.0
description: Manage git worktrees for parallel development with automatic cleanup
entry_point: /worktree
---

# Git Worktree Skill

This skill provides comprehensive git worktree management...
```

### Agent Example

```yaml
---
name: security-auditor
version: 1.1.0
description: Security-focused agent that scans code for vulnerabilities and secrets
model: sonnet
color: red
---

# Security Auditor Agent

An autonomous agent specialized in security analysis...
```

## Validation

### Using the Validation Script

Validate frontmatter using the provided validation script:

```bash
# Validate all artifacts
python scripts/validate-frontmatter-schema.py

# Validate specific artifact type
python scripts/validate-frontmatter-schema.py --type command

# Validate specific file
python scripts/validate-frontmatter-schema.py --path .claude-plugin/commands/my-command.md

# Verbose output
python scripts/validate-frontmatter-schema.py --verbose
```

### Validation Rules

The validator checks:

1. **Required Fields**: All required fields must be present
2. **Field Types**: Values must match expected types
3. **Format Patterns**: Names must be kebab-case, versions must be semver
4. **Enum Values**: Restricted fields must use allowed values
5. **Path Validity**: Entry points must start with `/`

### Common Validation Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Missing required field 'name'` | No name field | Add `name: your-name` |
| `Invalid name format` | Not kebab-case | Use lowercase with hyphens |
| `Invalid version format` | Not X.Y.Z | Use semantic versioning |
| `Invalid model value` | Unknown model | Use sonnet, opus, or haiku |
| `entry_point must start with /` | Missing leading slash | Add `/` prefix |

## JSON Schema Files

JSON Schema definitions for frontmatter validation are located in `docs/schemas/`:

| File | Purpose |
|------|---------|
| `command-frontmatter.schema.json` | Command artifact validation |
| `skill-frontmatter.schema.json` | Skill artifact validation |
| `agent-frontmatter.schema.json` | Agent artifact validation |
| `reference-frontmatter.schema.json` | Reference document validation |
| `common-frontmatter.schema.json` | Shared field definitions |

### Schema Structure

```
docs/schemas/
├── common-frontmatter.schema.json    # Base definitions
├── command-frontmatter.schema.json   # Command-specific
├── skill-frontmatter.schema.json     # Skill-specific
├── agent-frontmatter.schema.json     # Agent-specific
└── reference-frontmatter.schema.json # Reference-specific
```

### Using Schemas Programmatically

```python
import json
import jsonschema

# Load schema
with open('docs/schemas/command-frontmatter.schema.json') as f:
    schema = json.load(f)

# Validate frontmatter
frontmatter = {
    "name": "my-command",
    "version": "1.0.0",
    "description": "My command description"
}

jsonschema.validate(frontmatter, schema)
```

## Related Documentation

- [VALIDATION-QUICK-REFERENCE.md](./VALIDATION-QUICK-REFERENCE.md) - Quick reference for all validators
- [claude-code-skills-agents-guidelines-0.4.md](./claude-code-skills-agents-guidelines-0.4.md) - Full guidelines
- [MARKETPLACE-INFRASTRUCTURE.md](./MARKETPLACE-INFRASTRUCTURE.md) - Marketplace architecture
