# Versioning Strategy

This document defines the versioning system for Synaptic Canvas, establishing a single source of truth across the marketplace platform, individual packages, and their artifacts.

## Overview

Synaptic Canvas uses a **three-layer versioning system** based on semantic versioning (SemVer: MAJOR.MINOR.PATCH):

1. **Marketplace Platform Version** (`version.yaml`) - Infrastructure and CLI
2. **Package Versions** (`packages/*/manifest.yaml`) - Per-package releases
3. **Artifact Versions** (YAML frontmatter) - Commands, skills, agents

## Layer 1: Marketplace Platform Version

**Location:** `version.yaml`
**Purpose:** Version of the Synaptic Canvas platform infrastructure (installer, registry format, CLI)

### When to Bump

- Major changes to the installation system
- Breaking changes to registry format or manifest schema
- New marketplace-wide features affecting all packages
- CLI/installer interface changes

### Usage

The platform version is referenced in:
- Installer compatibility checks
- Registry API versioning
- CLI tool versioning

---

## Layer 2: Package Versions

**Location:** `packages/<package-name>/manifest.yaml`
**Purpose:** Version of an individual package and all its artifacts
**Scope:** Independent per package

### Package Versioning Policy

Each package maintains its own version independently:

```yaml
# packages/<package-name>/manifest.yaml
name: <package-name>
version: 0.8.0  # Package version (SemVer)
description: "..."
```

### When to Bump Package Version

- **PATCH** (0.8.1): Bug fixes, documentation updates, non-breaking improvements
- **MINOR** (0.9.0): New features, new agents/commands/skills, functionality enhancements
- **MAJOR** (1.0.0): Breaking changes, major refactoring, API changes, production-ready release

---

## Layer 3: Artifact Versions

**Location:** Frontmatter YAML in artifact files
**Scope:** Commands, skills, agents
**Policy:** Synchronized with parent package version

### Artifact Types

1. **Commands** (`packages/<package>/commands/*.md`)
2. **Skills** (`packages/<package>/skills/*/*.md` - `SKILL.md`)
3. **Agents** (`packages/<package>/agents/*.md` and `.claude/agents/*.md`)

### Artifact Frontmatter Format

All artifacts must include version in YAML frontmatter:

```yaml
---
name: <artifact-name>
description: >
  <description>
version: 0.8.0
---
```

### Synchronization Rules

- **Commands & Skills:** Version must match parent `manifest.yaml` version
- **Agents:** Version must match parent package version
- **Installed Artifacts:** `.claude/` artifacts follow their source package version

### Validation

Version mismatches are detected by the validation scripts:

```bash
python3 scripts/validate-all.py
python3 scripts/audit-versions.py
```

---

## Version Management Script

The `set-package-version.py` script is the **single source of truth** for version management.

### Usage

```bash
# Update a single package
python3 scripts/set-package-version.py sc-delay-tasks 0.8.0

# Update all packages to the same version
python3 scripts/set-package-version.py --all 0.8.0

# Update all packages AND marketplace platform version
python3 scripts/set-package-version.py --all --marketplace 0.8.0

# Preview changes without applying
python3 scripts/set-package-version.py --all 0.8.0 --dry-run
```

### What It Updates

For each package:
- `packages/<package>/manifest.yaml`
- `packages/<package>/.claude-plugin/plugin.json`
- `packages/<package>/commands/*.md` (frontmatter)
- `packages/<package>/skills/*/SKILL.md` (frontmatter)
- `packages/<package>/agents/*.md` (frontmatter)

Registry files (regenerated automatically):
- `.claude-plugin/marketplace.json`
- `.claude-plugin/registry.json`
- `docs/registries/nuget/registry.json`

If `--marketplace`:
- `version.yaml`

### Safety Features

- **Version decrement protection**: Errors if you try to set a lower version
- **Dry-run mode**: Preview all changes before applying
- **Skip detection**: Packages already at target version are skipped

---

## Examples

### Creating a New Version

When releasing version 0.9.0 of `sc-delay-tasks`:

```bash
# 1. Set the new version (updates all files automatically)
python3 scripts/set-package-version.py sc-delay-tasks 0.9.0

# 2. Run validation to verify
python3 scripts/validate-all.py

# 3. Update CHANGELOG
# Add entry to packages/sc-delay-tasks/CHANGELOG.md

# 4. Commit with clear message
git commit -m "chore(sc-delay-tasks): release v0.9.0"
```

### Marketplace-Wide Release

When releasing all packages at once:

```bash
# 1. Set version for all packages and marketplace
python3 scripts/set-package-version.py --all --marketplace 1.0.0

# 2. Run validation
python3 scripts/validate-all.py

# 3. Commit
git commit -m "chore: release v1.0.0"
```

### Checking Version Consistency

```bash
# Run full validation suite
python3 scripts/validate-all.py

# Audit versions specifically
python3 scripts/audit-versions.py

# Compare versions by package
python3 scripts/compare-versions.py --by-package
```

---

## Best Practices

1. **Use the script** - Always use `set-package-version.py`, never edit versions manually
2. **Validate after changes** - Run `validate-all.py` before committing
3. **Document changes** - Update CHANGELOG.md with every version bump
4. **Use semantic versioning** - Reserve MAJOR version for breaking changes
5. **Review before release** - Use `--dry-run` to preview changes

---

## Related Files

- `version.yaml` - Current marketplace platform version
- `packages/*/manifest.yaml` - Individual package manifests
- `CHANGELOG.md` - Release history for each package
- `scripts/set-package-version.py` - Version management script
- `scripts/validate-all.py` - Full validation suite
- `scripts/audit-versions.py` - Version consistency checker
- `RELEASING.md` - Step-by-step release process
