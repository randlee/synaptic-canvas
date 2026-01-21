# Synaptic Canvas Package Registry

The registry provides centralized package metadata for discovery, installation, and marketplace operations.

## Overview

The Synaptic Canvas registry is a JSON-based metadata store that enables:

- **Package Discovery** - Search and filter packages by tags, category, or name
- **Installation Management** - Track installed packages and their versions
- **Dependency Resolution** - Understand package requirements and compatibility
- **Version Tracking** - Monitor package versions across the marketplace
- **Metadata Retrieval** - Access package documentation, changelogs, and authors

## Registry Locations

### Primary Registry
**File**: `docs/registries/nuget/registry.json`
**Format**: JSON
**Version**: 2.0.0

Contains:
- 4 official Synaptic Canvas packages
- Version metadata for all packages and artifacts
- Artifact counts and categorization
- Dependency information
- Changelog references

### Schema
**Location**: `docs/registries/nuget/registry.schema.json` (future)

## Registry Structure

### Root Properties

```json
{
  "$schema": "URL to schema",
  "version": "2.0.0",
  "generated": "ISO timestamp",
  "repo": "GitHub repo path",
  "marketplace": { ... },
  "packages": { ... },
  "metadata": { ... },
  "versionCompatibility": { ... }
}
```

### Marketplace Object

Metadata about the marketplace platform itself:

```json
"marketplace": {
  "name": "Synaptic Canvas",
  "version": "0.5.0",
  "status": "beta",
  "url": "https://github.com/randlee/synaptic-canvas"
}
```

### Package Entry

Each package in the registry contains:

```json
"package-name": {
  "name": "display-name",
  "version": "X.Y.Z",
  "status": "beta|stable",
  "tier": 0|1|2,
  "description": "What this package does",
  "github": "repo-path",
  "repo": "repo-url",
  "path": "packages/package-name",
  "readme": "raw-readme-url",
  "license": "MIT",
  "author": "name",
  "tags": ["tag1", "tag2"],
  "artifacts": {
    "commands": count,
    "skills": count,
    "agents": count,
    "scripts": count
  },
  "dependencies": ["dep1", "dep2"],
  "variables": {
    "VAR_NAME": {
      "auto": "detection-method",
      "description": "Variable description"
    }
  },
  "changelog": "changelog-url",
  "lastUpdated": "YYYY-MM-DD",
  "dependents": []
}
```

### Metadata Object

Registry-level statistics and categorization:

```json
"metadata": {
  "registryVersion": "2.0.0",
  "schemaVersion": "1.0.0",
  "totalPackages": count,
  "totalCommands": count,
  "totalSkills": count,
  "totalAgents": count,
  "totalScripts": count,
  "categories": {
    "category-name": ["package1", "package2"],
    ...
  }
}
```

### Version Compatibility

Marketplace and package version constraints:

```json
"versionCompatibility": {
  "marketplace": "0.5.0",
  "minimumPackageVersion": "0.5.0",
  "maximumPackageVersion": "0.x.x",
  "note": "Additional information"
}
```

## Package Tiers

### Tier 0: Direct Copy
- No token substitution
- No dependencies
- Works immediately after installation
- Example: `sc-delay-tasks`

### Tier 1: Token Substitution
- Requires variable substitution at install time
- May have dependencies
- Customized per repository
- Example: `sc-git-worktree`, `sc-repomix-nuget`

### Tier 2: Runtime Dependencies
- External tools required
- Must be installed before use
- Dependencies documented in registry
- Example: (Future packages)

## Updating the Registry

### When to Update

- New package added to marketplace
- Package version changed
- Metadata needs correction
- Package deprecated or archived

### How to Update

1. **Modify** `docs/registries/nuget/registry.json`
2. **Update** package entry or add new entry
3. **Verify** JSON is valid: `python3 -m json.tool registry.json`
4. **Update** "generated" timestamp (ISO format)
5. **Recalculate** metadata statistics
6. **Commit** with clear message: `chore(registry): update package metadata`

### Automation (Future)

Future enhancement: Automated registry generation from manifest files:

```bash
python3 scripts/generate-registry.py --output docs/registries/nuget/registry.json
```

## Package Categories

Current package organization:

| Category | Packages | Purpose |
|----------|----------|---------|
| **Automation** | sc-delay-tasks | Schedule and poll tasks |
| **Development Tools** | sc-git-worktree | Git workflow management |
| **Package Management** | sc-manage | Package discovery and management |
| **Documentation** | sc-repomix-nuget | Repository analysis and documentation |

## Searching the Registry

### By Category
```javascript
registry.metadata.categories["development-tools"]
// Returns: ["sc-git-worktree"]
```

### By Tag
```javascript
Object.entries(registry.packages)
  .filter(([_, pkg]) => pkg.tags.includes("git"))
  .map(([name, _]) => name)
// Returns: ["sc-git-worktree"]
```

### By Status
```javascript
Object.entries(registry.packages)
  .filter(([_, pkg]) => pkg.status === "beta")
  .map(([name, pkg]) => ({ name, version: pkg.version }))
```

### By Tier
```javascript
Object.entries(registry.packages)
  .filter(([_, pkg]) => pkg.tier === 0)
  .map(([name, _]) => name)
// Returns: ["sc-delay-tasks", "sc-manage"]
```

## Version Management

### Package Versions

Each package maintains independent versioning:

- **Current**: All packages at 0.6.0 (beta)
- **Policy**: Synchronized within marketplace during beta
- **Bumping**: Use `python3 scripts/set-package-version.py NAME X.Y.Z`

### Marketplace Version

Platform-level version indicating infrastructure:

- **Current**: 0.6.0 (beta)
- **When to bump**: Breaking changes to registry format or CLI
- **Minimum package requirement**: All packages >= 0.4.0

See [Versioning Strategy](../versioning-strategy.md) for details.

## Registry API

### Accessing the Registry

The registry is designed for static access via HTTP:

```bash
# Fetch registry from GitHub raw content
curl https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registries/nuget/registry.json

# Parse and query with jq
jq '.packages | keys' registry.json
```

### Planned Enhancements

- REST API endpoint for registry queries
- Automated registry updates on PR merge
- Schema validation in CI/CD
- Version compatibility checking

## Related Documentation

- [Versioning Strategy](../versioning-strategy.md) - Package versioning policy
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Adding new packages
- [Package Manifests](../../packages) - Individual package definitions
