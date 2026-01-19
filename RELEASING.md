# Releasing Synaptic Canvas

This document provides a high-level overview of the Synaptic Canvas release process. For complete step-by-step procedures, see [docs/RELEASE-PROCESS.md](docs/RELEASE-PROCESS.md).

## Table of Contents

- [Versioning Strategy Overview](#versioning-strategy-overview)
- [Quick Release Checklist](#quick-release-checklist)
- [Key Scripts Reference](#key-scripts-reference)
- [Release Types](#release-types)
- [Common Commands](#common-commands)

---

## Versioning Strategy Overview

Synaptic Canvas uses a **three-layer versioning system** to manage releases across the marketplace platform, individual packages, and their artifacts.

### Three-Layer Architecture

```
+-----------------------------------------+
|  Layer 1: Marketplace Platform          |  version.yaml
|  (Infrastructure, CLI, Registry)        |  Example: 0.7.0
+-----------------------------------------+
               |
               v references
+-----------------------------------------+
|  Layer 2: Package Versions              |  manifest.yaml per package
|  (Independent per package)              |  Example: sc-delay-tasks v0.7.0
+-----------------------------------------+
               |
               v synchronized with
+-----------------------------------------+
|  Layer 3: Artifact Versions             |  Frontmatter in commands/,
|  (Commands, Skills, Agents)             |  skills/, agents/*.md
|  Synchronized with package version      |  Example: delay.md v0.7.0
+-----------------------------------------+
```

### Version Locations

| Layer | Location | Purpose |
|-------|----------|---------|
| **Marketplace** | `/version.yaml` | Platform infrastructure version |
| **Packages** | `packages/<name>/manifest.yaml` | Individual package versions |
| **Artifacts** | Frontmatter in `.md` files | Command, skill, agent versions |

### Semantic Versioning

All versions follow **MAJOR.MINOR.PATCH** format:

- **MAJOR (X)**: Breaking changes, incompatible API changes
- **MINOR (Y)**: New features, backward-compatible functionality
- **PATCH (Z)**: Bug fixes, documentation updates

**Current Status:** 0.7.0 (Beta)

---

## Quick Release Checklist

### Pre-Release

- [ ] Determine release scope (which packages, version numbers)
- [ ] Update CHANGELOG.md for each package being released
- [ ] Run version audit: `./scripts/audit-versions.py --verbose`
- [ ] Run all validations: `python3 scripts/validate-all.py`
- [ ] Review and approve version bump (semantic versioning compliance)
- [ ] Ensure all tests pass and CI is green

### Release Execution

- [ ] Create release branch: `git checkout -b release/v<VERSION>`
- [ ] Sync versions: `python3 scripts/sync-versions.py --package <name> --version <version>`
- [ ] Update registry: `python3 scripts/update-registry.py`
- [ ] Sync marketplace.json: `python3 scripts/sync-marketplace-json.py`
- [ ] Generate validation report: `python3 scripts/generate-validation-report.py`
- [ ] Commit changes with descriptive message
- [ ] Create git tag: `git tag -a v<VERSION> -m "Release message"`
- [ ] Push branch and tags to remote

### Post-Release

- [ ] Verify installation works from registry
- [ ] Run smoke tests on installed artifacts
- [ ] Monitor for issues (first 24 hours)
- [ ] Announce release (GitHub release notes, README update)
- [ ] Clean up release branch after merge

---

## Key Scripts Reference

The following Python scripts automate the release process. All scripts are located in the `scripts/` directory.

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `scripts/sync-versions.py` | Update versions across package artifacts | During version bump |
| `scripts/update-registry.py` | Update registry.json with new versions | Before creating release |
| `scripts/sync-marketplace-json.py` | Sync marketplace.json with registry | Before creating release |
| `scripts/validate-all.py` | Run all validation checks | Pre-release gate |
| `scripts/audit-versions.py` | Check version consistency across artifacts | Anytime |
| `scripts/generate-validation-report.py` | Generate HTML validation reports | Pre-release |

### Additional Validation Scripts

| Script | Purpose |
|--------|---------|
| `scripts/compare-versions.py` | Compare versions across packages side-by-side |
| `scripts/validate-agents.py` | Validate agent artifact structure and content |
| `scripts/validate-cross-references.py` | Check cross-references between artifacts |
| `scripts/validate-frontmatter-schema.py` | Validate YAML frontmatter schemas |
| `scripts/validate-manifest-artifacts.py` | Verify manifests match actual artifacts |
| `scripts/validate-marketplace-sync.py` | Ensure marketplace.json is in sync |
| `scripts/validate-script-references.py` | Check script references in artifacts |
| `scripts/security-scan.py` | Run security vulnerability scan |

### Script Exit Codes

All validation scripts follow these exit code conventions:

| Exit Code | Meaning |
|-----------|---------|
| `0` | All checks passed |
| `1` | Validation failures detected |
| `2` | Critical errors (missing files, etc.) |

---

## Release Types

### Single Package Release

Release one package while others remain unchanged.

```bash
# Example: Release sc-delay-tasks v0.7.1
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.7.1
```

### Marketplace Platform Release

Release marketplace infrastructure updates with all packages.

```bash
# Example: Release marketplace v0.8.0 with all packages
python3 scripts/sync-versions.py --marketplace --version 0.8.0
python3 scripts/sync-versions.py --all --version 0.8.0
```

### Patch/Hotfix Release

Emergency bug fix release.

```bash
# Example: Hotfix for sc-git-worktree
git checkout -b hotfix/sc-git-worktree-v0.7.1
python3 scripts/sync-versions.py --package sc-git-worktree --version 0.7.1
```

### Coordinated Release

Release multiple packages simultaneously.

```bash
# Example: Release multiple packages
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.7.1
python3 scripts/sync-versions.py --package sc-git-worktree --version 0.7.1
python3 scripts/sync-versions.py --package sc-manage --version 0.7.1
```

---

## Common Commands

### Version Management

```bash
# Audit all versions for consistency
./scripts/audit-versions.py --verbose

# Compare versions across packages
python3 scripts/compare-versions.py --by-package

# Find version mismatches
python3 scripts/compare-versions.py --mismatches

# Dry run version sync (preview changes)
python3 scripts/sync-versions.py --package <name> --version <version> --dry-run

# Sync package version
python3 scripts/sync-versions.py --package <name> --version <version>

# Sync all packages to same version
python3 scripts/sync-versions.py --all --version <version>

# Sync marketplace version
python3 scripts/sync-versions.py --marketplace --version <version>
```

### Validation

```bash
# Run all validations
python3 scripts/validate-all.py

# Validate agent artifacts
python3 scripts/validate-agents.py

# Validate manifest-artifact alignment
python3 scripts/validate-manifest-artifacts.py

# Generate validation report
python3 scripts/generate-validation-report.py --output reports/
```

### Registry Management

```bash
# Update registry.json
python3 scripts/update-registry.py

# Sync marketplace.json
python3 scripts/sync-marketplace-json.py

# Verify registry JSON syntax
python3 -m json.tool docs/registries/nuget/registry.json > /dev/null && echo "Valid JSON"
```

### Git Operations

```bash
# Create release branch
git checkout -b release/v<VERSION>

# Create annotated tag
git tag -a v<VERSION> -m "Release message"

# Push with tags
git push origin <branch> --follow-tags

# Delete tag (if needed)
git tag -d v<VERSION>
git push origin :refs/tags/v<VERSION>
```

---

## Branch Naming Conventions

| Branch Type | Pattern | Example |
|-------------|---------|---------|
| Marketplace release | `release/marketplace-v<version>` | `release/marketplace-v0.8.0` |
| Single package | `release/package-<name>-v<version>` | `release/package-sc-delay-tasks-v0.7.1` |
| All packages | `release/packages-v<version>` | `release/packages-v0.7.0` |
| Hotfix/patch | `release/patch-<name>-v<version>` | `release/patch-sc-delay-tasks-v0.7.1` |

---

## Tag Naming Conventions

| Tag Type | Pattern | Example |
|----------|---------|---------|
| Marketplace | `v<version>` | `v0.8.0` |
| Package | `v<version>-<package>` | `v0.7.1-sc-delay-tasks` |
| All packages | `v<version>-all` | `v0.7.0-all` |
| Security patch | `v-SECURITY-PATCH-<date>` | `v-SECURITY-PATCH-2025-01-15` |

---

## Detailed Documentation

For complete step-by-step procedures, including:

- Detailed pre-release checklists with verification steps
- Complete release execution workflows
- Release scenarios with examples
- Post-release verification procedures
- Rollback and incident procedures
- CI/CD integration details

See: **[docs/RELEASE-PROCESS.md](docs/RELEASE-PROCESS.md)**

---

## Quick Reference Card

```
+-------------------+--------------------------------+------------------+
| Action            | Command                        | Exit Code        |
+-------------------+--------------------------------+------------------+
| Audit versions    | ./scripts/audit-versions.py    | 0=pass, 1=fail   |
| Compare versions  | python3 scripts/compare-       | 0=pass           |
|                   | versions.py --by-package       |                  |
| Sync versions     | python3 scripts/sync-          | 0=success        |
|                   | versions.py --package X --v Y  |                  |
| Update registry   | python3 scripts/update-        | 0=success        |
|                   | registry.py                    |                  |
| Validate all      | python3 scripts/validate-      | 0=pass, 1=fail   |
|                   | all.py                         |                  |
+-------------------+--------------------------------+------------------+
```

---

**Document Version:** 0.7.0
**Last Updated:** January 2025
**Maintained By:** Synaptic Canvas Maintainers
