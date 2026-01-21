# Registry Schema Quick Reference

This guide provides quick access to common schema information for the Synaptic Canvas package registry.

## Files

- **`registry.schema.json`** - Complete JSON Schema v7 specification
- **`registry.json`** - Current registry data
- **`validate-registry.py`** - Python validation utility
- **`SCHEMA_DOCUMENTATION.md`** - Detailed documentation
- **`SCHEMA_QUICK_REFERENCE.md`** - This file

## Quick Validation

```bash
# Basic validation
python3 docs/registries/nuget/validate-registry.py

# Verbose output
python3 docs/registries/nuget/validate-registry.py --verbose

# JSON output (for CI/CD)
python3 docs/registries/nuget/validate-registry.py --json
```

## Registry Structure

```
registry.json
├── $schema                    (URI to schema)
├── version                    (X.Y.Z)
├── generated                  (ISO-8601 timestamp)
├── repo                       (owner/repo)
├── marketplace                (object)
│   ├── name
│   ├── version
│   ├── status
│   └── url
├── packages                   (object of package definitions)
│   └── {package-name}
│       ├── name
│       ├── version
│       ├── status
│       ├── tier
│       ├── description
│       ├── github
│       ├── repo
│       ├── path
│       ├── readme
│       ├── license
│       ├── author
│       ├── tags
│       ├── artifacts
│       ├── variables (optional)
│       ├── dependencies
│       ├── changelog
│       ├── lastUpdated
│       └── dependents
├── metadata                   (object)
│   ├── registryVersion
│   ├── schemaVersion
│   ├── totalPackages
│   ├── totalCommands
│   ├── totalSkills
│   ├── totalAgents
│   ├── totalScripts
│   ├── totalSchemas
│   └── categories
└── versionCompatibility       (object)
    ├── marketplace
    ├── minimumPackageVersion
    ├── maximumPackageVersion
    └── note
```

## Common Field Constraints

### Versions
- Format: Semantic Versioning (X.Y.Z)
- Pattern: `^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d?)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$`
- Examples: `2.0.0`, `0.4.0`, `1.0.0-beta.1`

### Package Names
- Lowercase alphanumeric with hyphens
- Pattern: `^[a-z0-9]+(-[a-z0-9]+)*$`
- Examples: `sc-delay-tasks`, `sc-git-worktree`, `sc-manage`
- Invalid: `DelayTasks`, `delay_tasks`, `delay.tasks`

### Tags
- Lowercase alphanumeric, hyphens, dots, hash symbols
- Pattern: `^[.#a-z0-9]([a-z0-9.\-#]*[a-z0-9])?$`
- Examples: `.net`, `c#`, `asp.net`, `f#`, `ci-cd`, `automation`
- 1-20 unique tags per package

### Status Values
| Value | Meaning |
|-------|---------|
| `alpha` | Early development, features may change significantly |
| `beta` | Feature complete, not production-ready, API may change |
| `stable` | Production-ready, stable API |
| `deprecated` | Planned for removal in future version |
| `archived` | No longer maintained |

### Tier Values
| Value | Meaning |
|-------|---------|
| `0` | No dependencies, standalone utilities |
| `1` | Single major dependency or moderate complexity |
| `2` | Multiple dependencies or advanced configuration |
| `3` | Complex with several integrations |
| `4` | Enterprise-grade complexity |
| `5` | Highly complex multi-component system |

### URLs
- Repository: `https://github.com/owner/repo`
- Raw content: `https://raw.githubusercontent.com/owner/repo/branch/path/file`
- All must use HTTPS

## Package Definition Template

```json
{
  "name": "package-name",
  "version": "1.0.0",
  "status": "stable",
  "tier": 1,
  "description": "Description of what this package does and its use cases.",
  "github": "owner/repo",
  "repo": "https://github.com/owner/repo",
  "path": "packages/package-name",
  "readme": "https://raw.githubusercontent.com/owner/repo/main/packages/package-name/README.md",
  "license": "MIT",
  "author": "Author Name",
  "tags": ["tag1", "tag2", "tag3"],
  "artifacts": {
    "commands": 1,
    "skills": 2,
    "agents": 3,
    "scripts": 0,
    "schemas": 1
  },
  "dependencies": ["git >= 2.27"],
  "changelog": "https://raw.githubusercontent.com/owner/repo/main/packages/package-name/CHANGELOG.md",
  "lastUpdated": "2025-12-02",
  "dependents": []
}
```

## Optional Fields

### Variables (Package-Level)

Defines environment or configuration variables:

```json
"variables": {
  "REPO_NAME": {
    "auto": "git-repo-basename",
    "description": "Repository name from git toplevel"
  }
}
```

Auto-population methods:
- `git-repo-basename` - Repository name from git toplevel
- `git-repo-root` - Repository root directory path
- `current-user` - Current user name
- `timestamp` - Current timestamp
- `uuid` - Generated UUID

## Artifact Types

| Type | Description |
|------|-------------|
| `commands` | Slash commands (e.g., `/delay`) |
| `skills` | Callable skills/capabilities |
| `agents` | Automated workflows |
| `scripts` | Utility scripts |

All are integer counters with minimum value of 0.

## Validation Examples

### Valid
```json
{
  "name": "my-package",
  "version": "1.2.3",
  "tags": [".net", "c#", "asp.net"]
}
```

### Invalid
```json
{
  "name": "My-Package",           // ERROR: Must be lowercase
  "version": "1.2",               // ERROR: Missing patch version
  "tags": ["My Tag", "tag_name"]  // ERROR: Invalid tag format
}
```

## IDE Setup

### VS Code

Add to `.vscode/settings.json`:

```json
{
  "json.schemas": [
    {
      "fileMatch": ["docs/registries/nuget/registry.json"],
      "url": "file:///absolute/path/to/registry.schema.json"
    }
  ]
}
```

This enables autocomplete and validation when editing the registry.

## Common Issues

| Issue | Solution |
|-------|----------|
| Version format error | Use X.Y.Z format (e.g., 1.0.0, not 1.0) |
| Package name error | Use lowercase with hyphens (my-package, not MyPackage) |
| Tag format error | Use lowercase, allow hyphens/dots/hashes (`.net` is valid) |
| URL format error | Use HTTPS URLs, raw.githubusercontent.com for files |
| Missing required field | Check against required fields list above |
| Invalid enum value | Use exact values from status/auto enumerations |

## Metadata Validation

The metadata object contains aggregate counts that should match package data:

```json
"metadata": {
  "totalPackages": 4,           // Count of entries in packages object
  "totalCommands": 4,           // Sum of all commands across packages
  "totalSkills": 4,             // Sum of all skills across packages
  "totalAgents": 14,            // Sum of all agents across packages
  "totalScripts": 2             // Sum of all scripts across packages
  "totalSchemas": 1            // Sum of all schemas across packages
}
```

Use the validation script to verify these counts are accurate.

## Version Compatibility

The `versionCompatibility` object ensures version constraints:

```json
"versionCompatibility": {
  "marketplace": "0.4.0",
  "minimumPackageVersion": "0.4.0",
  "maximumPackageVersion": "0.x.x",
  "note": "Marketplace is in beta..."
}
```

- `maximumPackageVersion` with 'x' wildcard prevents major version changes
  - `0.x.x` allows 0.0.0 through 0.999.999
  - `1.x.x` allows 1.0.0 through 1.999.999

## Further Information

- See `SCHEMA_DOCUMENTATION.md` for complete details
- Check `registry.schema.json` for precise JSON Schema specification
- Run `python3 validate-registry.py --help` for validation options
