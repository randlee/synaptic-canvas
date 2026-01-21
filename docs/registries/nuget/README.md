# Synaptic Canvas Package Registry

This directory contains the Synaptic Canvas package registry, schema definitions, validation tooling, and comprehensive documentation.

## Overview

The Synaptic Canvas package registry is a centralized catalog of packages (commands, skills, agents, and scripts) available in the marketplace. The registry uses JSON Schema v7 for validation and supports programmatic consumption via the registry.json file.

**Current Registry Version:** 2.0.0
**Current Schema Version:** 1.0.0

## Files in This Directory

### Core Registry Files

- **`registry.json`** - The complete package registry containing all package metadata, marketplace information, and aggregated statistics
- **`registry.schema.json`** - JSON Schema v7 definition that validates the structure, types, and constraints of registry.json

### Validation Tools

- **`validate-registry.py`** - Python-based validation utility for CI/CD pipelines
  - Validates registry structure against schema constraints
  - Supports both human-readable and JSON output formats
  - Can be integrated into GitHub Actions or other CI/CD systems

### Documentation

- **`SCHEMA_DOCUMENTATION.md`** - Complete reference documentation covering:
  - Detailed field descriptions for all registry components
  - Validation rules and constraints
  - Examples of minimal and complex packages
  - IDE integration instructions
  - Programmatic validation examples (Python, JavaScript/TypeScript)
  - CI/CD integration examples
  - Schema evolution strategy

- **`SCHEMA_QUICK_REFERENCE.md`** - Quick lookup guide with:
  - Common field constraints and patterns
  - Structure overview
  - Validation examples
  - Common issues and solutions
  - Template for new packages

### Configuration Templates

- **`.vscode-settings-template.json`** - VS Code settings template for enabling JSON Schema autocomplete and validation when editing registry.json

## Quick Start

### Validating the Registry

```bash
# Basic validation
python3 docs/registries/nuget/validate-registry.py

# Verbose output with statistics
python3 docs/registries/nuget/validate-registry.py --verbose

# JSON output for CI/CD automation
python3 docs/registries/nuget/validate-registry.py --json
```

### Understanding the Schema

1. **Quick Overview**: Start with `SCHEMA_QUICK_REFERENCE.md` for common tasks
2. **Detailed Info**: See `SCHEMA_DOCUMENTATION.md` for comprehensive documentation
3. **Validation**: Review `registry.schema.json` for precise constraints
4. **Examples**: Check actual packages in `registry.json` for real-world examples

### IDE Support (VS Code)

1. Copy settings from `.vscode-settings-template.json`
2. Paste into your `.vscode/settings.json`
3. Reload VS Code
4. Open `registry.json` for autocomplete and validation

## Registry Structure

### Root Level

The registry contains:

- **`$schema`** - Reference to this schema document
- **`version`** - Registry format version (2.0.0)
- **`generated`** - ISO-8601 timestamp of generation
- **`repo`** - GitHub repository (owner/repo)
- **`marketplace`** - Marketplace metadata (name, version, status, URL)
- **`packages`** - Dictionary of package definitions (keyed by package name)
- **`metadata`** - Aggregated statistics (package counts, categories)
- **`versionCompatibility`** - Version constraints and compatibility info

### Package Structure

Each package in the registry contains:

**Required Fields:**
- `name` - Unique lowercase identifier with hyphens
- `version` - Semantic version (X.Y.Z)
- `status` - Lifecycle status (alpha, beta, stable, deprecated, archived)
- `tier` - Complexity level (0-5)
- `description` - Purpose and use cases (10-500 characters)
- `github` - GitHub repository identifier (owner/repo)
- `repo` - Full HTTPS GitHub repository URL
- `path` - Relative path to package in repository
- `readme` - Raw GitHub URL to README.md
- `license` - SPDX license identifier
- `author` - Package maintainer
- `tags` - Searchable keywords (1-20, unique)
- `artifacts` - Artifact counts (commands, skills, agents, scripts, schemas)
- `dependencies` - Required system/package dependencies (array)
- `changelog` - Raw GitHub URL to CHANGELOG.md
- `lastUpdated` - ISO-8601 date of last update
- `dependents` - Packages that depend on this one

**Optional Fields:**
- `variables` - Environment/configuration variables with auto-population methods

## Validation Rules

### Semantic Versioning
All versions follow SemVer 2.0.0: `X.Y.Z[-prerelease][+build]`
- Examples: `2.0.0`, `0.4.0`, `1.0.0-beta.1`, `2.1.0-rc.1+build.123`

### Package Names and Tags
- Lowercase alphanumeric with hyphens and dots
- Tag pattern allows dots and hash symbols (for `.net`, `c#`, etc.)
- Examples: `sc-delay-tasks`, `.net`, `c#`, `asp.net`, `ci-cd`

### URLs
- GitHub repos: `https://github.com/owner/repo`
- Raw content: `https://raw.githubusercontent.com/owner/repo/branch/path`

### Status and Tier
- **Status**: alpha, beta, stable, deprecated, archived
- **Tier**: 0-5 (0=no dependencies, 5=highly complex)

## Programmatic Validation

### Python

```python
import json
import jsonschema

with open('registry.schema.json') as f:
    schema = json.load(f)
with open('registry.json') as f:
    registry = json.load(f)

try:
    jsonschema.validate(instance=registry, schema=schema)
    print("Registry is valid!")
except jsonschema.ValidationError as e:
    print(f"Validation error: {e.message}")
```

### JavaScript/TypeScript

```typescript
import Ajv from 'ajv';

const ajv = new Ajv();
const schema = require('./registry.schema.json');
const registry = require('./registry.json');

const validate = ajv.compile(schema);
const valid = validate(registry);

if (!valid) {
  console.error('Errors:', validate.errors);
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
      - name: Validate Registry
        run: python3 docs/registries/nuget/validate-registry.py --json
```

## Adding a New Package

1. Create package directory: `packages/my-package/`
2. Include README.md, CHANGELOG.md, and package files
3. Add entry to `registry.json` packages object with all required fields
4. Update metadata counts (totalPackages, totalSkills, etc.)
5. Add package to appropriate category
6. Run validation: `python3 validate-registry.py --verbose`
7. Verify no errors before committing

## Versioning Strategy

### Registry Format Versions (MAJOR.MINOR.PATCH)

- **MAJOR** - Breaking changes to registry structure
  - Requires registry version bump
  - May require migration of existing registries
  
- **MINOR** - New optional fields or non-breaking enhancements
  - Backward compatible
  - Older tools can still read the registry
  
- **PATCH** - Bug fixes, documentation updates
  - No structural changes
  - Fully backward compatible

### Schema Versions

The schema version is tracked separately and updated when:
- New definitions or properties are added
- Validation rules change
- Breaking changes occur

Update the schema by:
1. Modifying `registry.schema.json`
2. Updating `schemaVersion` in metadata
3. Documenting changes in `versionCompatibility.note`
4. Adding migration notes if breaking changes

## Troubleshooting

### Validation Errors

**"version" does not match pattern**
- Ensure version follows X.Y.Z format (semantic versioning)
- Pre-release: X.Y.Z-alpha, X.Y.Z-beta, X.Y.Z-rc.1

**"name" does not match pattern**
- Use lowercase only
- Separate words with hyphens: `my-package` not `my_package`
- No spaces or special characters

**"tags" contains invalid value**
- Use lowercase, hyphens, dots, or hashes
- Examples: `automation`, `.net`, `c#`, `asp.net`
- No spaces or underscores

**Invalid URI format**
- Use HTTPS URLs only
- GitHub repos: `https://github.com/owner/repo`
- Raw content: `https://raw.githubusercontent.com/...`

**Missing required property**
- Compare against package template in SCHEMA_QUICK_REFERENCE.md
- All listed required fields must be present

## Examples

### Minimal Package

```json
{
  "name": "simple-tool",
  "version": "1.0.0",
  "status": "stable",
  "tier": 0,
  "description": "A simple utility for basic tasks.",
  "github": "owner/repo",
  "repo": "https://github.com/owner/repo",
  "path": "packages/simple-tool",
  "readme": "https://raw.githubusercontent.com/owner/repo/main/packages/simple-tool/README.md",
  "license": "MIT",
  "author": "Developer",
  "tags": ["utility"],
  "artifacts": {
    "commands": 0,
    "skills": 1,
    "agents": 0,
    "scripts": 0,
    "schemas": 0
  },
  "dependencies": [],
  "changelog": "https://raw.githubusercontent.com/owner/repo/main/packages/simple-tool/CHANGELOG.md",
  "lastUpdated": "2025-12-02",
  "dependents": []
}
```

### Complex Package with Variables and Dependencies

```json
{
  "name": "advanced-toolkit",
  "version": "2.1.0-rc.1",
  "status": "beta",
  "tier": 3,
  "description": "Advanced toolkit with multiple integrations for enterprise deployment.",
  "github": "owner/repo",
  "repo": "https://github.com/owner/repo",
  "path": "packages/advanced-toolkit",
  "readme": "https://raw.githubusercontent.com/owner/repo/main/packages/advanced-toolkit/README.md",
  "license": "Apache-2.0",
  "author": "Enterprise Team",
  "tags": ["advanced", ".net", "c#", "enterprise"],
  "artifacts": {
    "commands": 3,
    "skills": 5,
    "agents": 8,
    "scripts": 2,
    "schemas": 1
  },
  "variables": {
    "API_KEY": {
      "description": "API key for external service"
    },
    "REPO_NAME": {
      "auto": "git-repo-basename",
      "description": "Auto-populated repository name"
    }
  },
  "dependencies": [
    "node >= 16.0.0",
    "python3 >= 3.9"
  ],
  "changelog": "https://raw.githubusercontent.com/owner/repo/main/packages/advanced-toolkit/CHANGELOG.md",
  "lastUpdated": "2025-12-01",
  "dependents": []
}
```

## References

- [JSON Schema Draft 7 Specification](https://json-schema.org/draft-07/)
- [Semantic Versioning 2.0.0](https://semver.org/)
- [SPDX License List](https://spdx.org/licenses/)
- [RFC 3339 - Date and Time Formats](https://tools.ietf.org/html/rfc3339)

## Support and Questions

For questions or issues related to the registry schema:

1. Check `SCHEMA_DOCUMENTATION.md` for detailed information
2. Review `SCHEMA_QUICK_REFERENCE.md` for common tasks
3. Run `validate-registry.py --verbose` to identify specific errors
4. Compare with existing packages in `registry.json` for examples

---

**Last Updated:** 2025-12-02
**Schema Version:** 1.0.0
**Registry Version:** 2.0.0
