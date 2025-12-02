# Synaptic Canvas Package Registry Schema Documentation

## Overview

This document describes the JSON Schema v7 specification for the Synaptic Canvas Package Registry. The schema defines the complete structure, validation rules, and requirements for the registry format used to catalog and distribute packages within the marketplace.

**Schema Location:** `registry.schema.json`
**Registry Location:** `registry.json`
**Current Schema Version:** 1.0.0
**Current Registry Version:** 2.0.0

## Purpose

The registry schema provides:

- **Validation**: Ensures registry data conforms to expected structure in CI/CD pipelines
- **IDE Support**: Enables autocomplete and validation in VS Code and other editors via JSON Schema support
- **Documentation**: Specifies all required and optional fields with descriptions
- **API Contract**: Defines the interface for programmatic registry consumption

## Registry Structure

### Root Level Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `$schema` | string (URI) | ✓ | Reference to this schema document |
| `version` | string (semver) | ✓ | Registry format version (X.Y.Z) |
| `generated` | string (ISO-8601) | ✓ | Timestamp when registry was generated |
| `repo` | string | ✓ | GitHub repository (owner/repo) |
| `marketplace` | object | ✓ | Marketplace metadata |
| `packages` | object | ✓ | Dictionary of package definitions |
| `metadata` | object | ✓ | Registry statistics and organization |
| `versionCompatibility` | object | ✓ | Version constraints and compatibility info |

### Marketplace Object

The `marketplace` object describes the package marketplace itself:

```json
{
  "name": "Synaptic Canvas",
  "version": "0.4.0",
  "status": "beta",
  "url": "https://github.com/randlee/synaptic-canvas"
}
```

| Field | Type | Required | Enum Values | Description |
|-------|------|----------|-------------|-------------|
| `name` | string | ✓ | - | Display name of marketplace |
| `version` | string | ✓ | - | Marketplace version (semver) |
| `status` | string | ✓ | alpha, beta, stable, deprecated | Marketplace lifecycle status |
| `url` | string (URI) | ✓ | - | Primary marketplace URL |

### Package Object

Each package in the registry contains complete metadata about a distributable unit:

```json
{
  "name": "delay-tasks",
  "version": "0.4.0",
  "status": "beta",
  "tier": 0,
  "description": "Schedule delayed or interval-based actions...",
  "github": "randlee/synaptic-canvas",
  "repo": "https://github.com/randlee/synaptic-canvas",
  "path": "packages/delay-tasks",
  "readme": "https://raw.githubusercontent.com/...",
  "license": "MIT",
  "author": "Anthropic",
  "tags": ["delay", "polling", "tasks", "ci", "automation"],
  "artifacts": {
    "commands": 1,
    "skills": 1,
    "agents": 3,
    "scripts": 1
  },
  "dependencies": [],
  "changelog": "https://raw.githubusercontent.com/...",
  "lastUpdated": "2025-12-02",
  "dependents": []
}
```

#### Required Package Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `name` | string | lowercase, hyphens, 1-64 chars | Unique package identifier |
| `version` | string | Semver (X.Y.Z) | Current package version |
| `status` | string | alpha, beta, stable, deprecated, archived | Lifecycle status |
| `tier` | integer | 0-5 | Complexity level (0=basic, 5=complex) |
| `description` | string | 10-500 chars | Package purpose and use cases |
| `github` | string | owner/repo format | GitHub repository identifier |
| `repo` | string | HTTPS GitHub URL | Full repository URL |
| `path` | string | alphanumeric, /, - | Relative package path in repo |
| `readme` | string | Raw GitHub URL | README documentation URL |
| `license` | string | SPDX identifier | License type (e.g., MIT, Apache-2.0) |
| `author` | string | 1+ chars | Package maintainer/author |
| `tags` | array | 1-20 unique, lowercase | Searchable keywords |
| `artifacts` | object | - | Artifact type counts |
| `dependencies` | array | - | Required system/package dependencies |
| `changelog` | string | Raw GitHub URL | CHANGELOG documentation URL |
| `lastUpdated` | string | ISO-8601 date (YYYY-MM-DD) | Last update timestamp |
| `dependents` | array | - | Packages depending on this one |

#### Optional Package Fields

| Field | Type | Description |
|-------|------|-------------|
| `variables` | object | Environment/config variables exposed by package |

### Artifacts Object

Specifies the count of different artifact types in a package:

```json
{
  "commands": 1,
  "skills": 1,
  "agents": 3,
  "scripts": 1
}
```

All fields are integers with minimum value of 0:
- `commands`: Slash commands available
- `skills`: Callable skills/capabilities
- `agents`: Automated workflows
- `scripts`: Utility scripts

### Variables Object (Optional)

Defines environment variables or configuration parameters:

```json
{
  "REPO_NAME": {
    "auto": "git-repo-basename",
    "description": "Repository name from git toplevel"
  }
}
```

Each variable entry has:

| Field | Type | Required | Enum Values | Description |
|-------|------|----------|-------------|-------------|
| `auto` | string | - | git-repo-basename, git-repo-root, current-user, timestamp, uuid | Auto-population method |
| `description` | string | ✓ | - | Variable purpose and usage |

### Metadata Object

Aggregated statistics and organizational information:

```json
{
  "registryVersion": "2.0.0",
  "schemaVersion": "1.0.0",
  "totalPackages": 4,
  "totalCommands": 4,
  "totalSkills": 4,
  "totalAgents": 14,
  "totalScripts": 2,
  "categories": {
    "automation": ["delay-tasks"],
    "development-tools": ["git-worktree"],
    "package-management": ["sc-manage"],
    "documentation": ["repomix-nuget"]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `registryVersion` | string (semver) | Version of registry format |
| `schemaVersion` | string (semver) | Version of this schema document |
| `totalPackages` | integer | Count of packages in registry |
| `totalCommands` | integer | Aggregate command count |
| `totalSkills` | integer | Aggregate skill count |
| `totalAgents` | integer | Aggregate agent count |
| `totalScripts` | integer | Aggregate script count |
| `categories` | object | Category-to-packages mapping |

### Version Compatibility Object

Specifies version constraints and compatibility information:

```json
{
  "marketplace": "0.4.0",
  "minimumPackageVersion": "0.4.0",
  "maximumPackageVersion": "0.x.x",
  "note": "Marketplace is in beta. All packages should remain at 0.x versions until first stable release (1.0.0)"
}
```

| Field | Type | Required | Pattern | Description |
|-------|------|----------|---------|-------------|
| `marketplace` | string | ✓ | semver X.Y.Z | Current marketplace version |
| `minimumPackageVersion` | string | ✓ | semver X.Y.Z | Minimum accepted package version |
| `maximumPackageVersion` | string | ✓ | X.Y.Z with x wildcards | Maximum allowed package version |
| `note` | string | - | - | Human-readable compatibility notes |

The `maximumPackageVersion` field supports 'x' as a wildcard:
- `0.x.x`: Accept any 0.* version (prevents major version 1+)
- `1.x.x`: Accept any 1.* version
- `2.3.x`: Accept 2.3.0, 2.3.1, etc.

## Validation Rules

### Semantic Versioning

All version fields follow Semantic Versioning 2.0.0:

```
X.Y.Z[-prerelease][+build]

Examples:
- 2.0.0
- 0.4.0
- 1.0.0-beta.1
- 2.1.0-rc.1+build.123
```

Pattern: `^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d?)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$`

### Package Names and Tags

Package names and tags must be lowercase with hyphens only:

- Pattern: `^[a-z0-9]+(-[a-z0-9]+)*$`
- Examples: `delay-tasks`, `git-worktree`, `package-name`
- Invalid: `DelayTasks`, `delay_tasks`, `delay.tasks`

### URL Formats

- **GitHub Repository URLs**: Must be HTTPS URLs starting with `https://github.com/`
- **Raw GitHub URLs**: Must start with `https://raw.githubusercontent.com/` for README and CHANGELOG
- **Schema Reference**: Must be valid URI format

### Status Values

Allowed status values indicate lifecycle stage:

- `alpha`: Early development, features may change significantly
- `beta`: Feature complete, not production-ready, API may change
- `stable`: Production-ready, stable API
- `deprecated`: Planned for removal in future version
- `archived`: No longer maintained

### Tier Values

Tier indicates complexity/dependency level:

- `0`: No dependencies, standalone utilities
- `1`: Single major dependency or moderate complexity
- `2`: Multiple dependencies or advanced configuration
- `3`: Complex with several integrations
- `4`: Enterprise-grade complexity
- `5`: Highly complex multi-component system

## IDE Integration

### VS Code

To enable JSON Schema validation in VS Code:

1. Add to your workspace settings (`.vscode/settings.json`):

```json
{
  "json.schemas": [
    {
      "fileMatch": ["docs/registries/nuget/registry.json"],
      "url": "file:///path/to/registry.schema.json"
    }
  ]
}
```

2. VS Code will now provide:
   - Autocomplete suggestions while editing
   - Type hints for each property
   - Validation warnings for invalid values
   - Hover documentation

### Other Editors

Most modern editors supporting JSON Schema Draft 7 can use this schema. Consult your editor's documentation for JSON Schema configuration.

## Programmatic Validation

### Python Example

```python
import json
import jsonschema

# Load schema and registry
with open('registry.schema.json') as f:
    schema = json.load(f)

with open('registry.json') as f:
    registry = json.load(f)

# Validate
try:
    jsonschema.validate(instance=registry, schema=schema)
    print("Registry is valid!")
except jsonschema.ValidationError as e:
    print(f"Validation error: {e.message}")
```

### JavaScript/TypeScript Example

```typescript
import Ajv from 'ajv';

const ajv = new Ajv();
const schema = require('./registry.schema.json');
const registry = require('./registry.json');

const validate = ajv.compile(schema);
const valid = validate(registry);

if (!valid) {
  console.error('Validation errors:', validate.errors);
} else {
  console.log('Registry is valid!');
}
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Validate Registry

on: [pull_request, push]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Validate Registry Schema
        run: |
          python3 << 'EOF'
          import json
          import jsonschema
          
          with open('docs/registries/nuget/registry.schema.json') as f:
              schema = json.load(f)
          with open('docs/registries/nuget/registry.json') as f:
              registry = json.load(f)
          
          try:
              jsonschema.validate(registry, schema)
              print("✓ Registry is valid")
          except jsonschema.ValidationError as e:
              print(f"✗ Validation failed: {e.message}")
              exit(1)
          EOF
```

## Schema Evolution

### Versioning Strategy

The schema uses semantic versioning:

- **MAJOR**: Breaking changes to registry structure (requires registry version bump)
- **MINOR**: New optional fields or constraints (backward compatible)
- **PATCH**: Documentation updates or non-breaking clarifications

### Migration Guidelines

When updating the schema:

1. Update `schemaVersion` in metadata if structure changes
2. Add migration notes in `versionCompatibility.note` if breaking
3. Provide examples for new fields
4. Update this documentation

## Examples

### Minimal Package

```json
{
  "name": "simple-tool",
  "version": "1.0.0",
  "status": "stable",
  "tier": 0,
  "description": "A simple utility package for basic tasks.",
  "github": "owner/repo",
  "repo": "https://github.com/owner/repo",
  "path": "packages/simple-tool",
  "readme": "https://raw.githubusercontent.com/owner/repo/main/packages/simple-tool/README.md",
  "license": "MIT",
  "author": "Developer Name",
  "tags": ["utility"],
  "artifacts": {
    "commands": 0,
    "skills": 1,
    "agents": 0,
    "scripts": 0
  },
  "dependencies": [],
  "changelog": "https://raw.githubusercontent.com/owner/repo/main/packages/simple-tool/CHANGELOG.md",
  "lastUpdated": "2025-12-02",
  "dependents": []
}
```

### Complex Package with Dependencies

```json
{
  "name": "advanced-toolkit",
  "version": "2.1.0-rc.1",
  "status": "beta",
  "tier": 3,
  "description": "Advanced toolkit with multiple integrations and powerful features for enterprise deployment.",
  "github": "owner/repo",
  "repo": "https://github.com/owner/repo",
  "path": "packages/advanced-toolkit",
  "readme": "https://raw.githubusercontent.com/owner/repo/main/packages/advanced-toolkit/README.md",
  "license": "Apache-2.0",
  "author": "Enterprise Team",
  "tags": ["advanced", "integration", "enterprise", "deployment"],
  "artifacts": {
    "commands": 3,
    "skills": 5,
    "agents": 8,
    "scripts": 4
  },
  "variables": {
    "API_KEY": {
      "description": "API key for external service integration"
    },
    "DEPLOYMENT_ENV": {
      "description": "Deployment environment (dev, staging, prod)"
    }
  },
  "dependencies": [
    "node >= 16.0.0",
    "python3 >= 3.9",
    "docker >= 20.0"
  ],
  "changelog": "https://raw.githubusercontent.com/owner/repo/main/packages/advanced-toolkit/CHANGELOG.md",
  "lastUpdated": "2025-12-01",
  "dependents": ["consumer-package"]
}
```

## Troubleshooting

### Common Validation Errors

**"version" does not match pattern**
- Ensure version follows X.Y.Z format (semantic versioning)
- Pre-release versions: X.Y.Z-alpha, X.Y.Z-beta, X.Y.Z-rc.1

**"name" does not match pattern**
- Use lowercase only
- Separate words with hyphens: `my-package` not `my_package` or `MyPackage`
- No spaces or special characters

**Invalid URI format**
- Check URLs use HTTPS
- Ensure GitHub URLs follow correct format: `https://github.com/owner/repo`
- Raw URLs must use: `https://raw.githubusercontent.com/...`

**Missing required property**
- Verify all required fields are present in package or root object
- Refer to tables above for required vs optional fields

**Invalid enum value**
- Check `status` is one of: alpha, beta, stable, deprecated, archived
- Check `tier` is integer 0-5

## References

- [JSON Schema Draft 7](https://json-schema.org/draft-07/)
- [Semantic Versioning 2.0.0](https://semver.org/)
- [SPDX License List](https://spdx.org/licenses/)
- [RFC 3339 - ISO 8601 Timestamps](https://tools.ietf.org/html/rfc3339)
