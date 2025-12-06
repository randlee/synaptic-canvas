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
**Current Version:** 0.5.0 (Beta)

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
version: 0.4.0  # Package version (SemVer)
description: "..."
```

### Current Package Versions

| Package | Version | Status | Notes |
|---------|---------|--------|-------|
| `delay-tasks` | 1.0.0 | Beta | Core polling/delay functionality |
| `git-worktree` | 1.0.0 | Beta | Worktree management with tracking |
| `sc-repomix-nuget` | 0.5.0 | Beta | NuGet packaging integration |
| `sc-manage` | 0.5.0 | Beta | Package manager interface |

### When to Bump Package Version

- **PATCH** (0.4.1): Bug fixes, documentation updates, non-breaking improvements
- **MINOR** (0.5.0): New features, new agents/commands/skills, backward-compatible changes
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
version: 0.4.0
---
```

### Synchronization Rules

- **Commands & Skills:** Version must match parent `manifest.yaml` version
- **Agents:** Version must match parent package version OR marketplace version (for cross-package agents)
- **Installed Artifacts:** `.claude/` artifacts follow their source package version

### Validation

Version mismatches are detected by the version audit script:

```bash
./scripts/audit-versions.sh
```

---

## Implementation Tasks

### CCS.1: Document Versioning Strategy ✅

- [x] Create `docs/versioning-strategy.md` (this file)
- [x] Update `version.yaml` with clarifying comments
- [x] Document three-layer system clearly

### CCS.2: Add Version Frontmatter

- [x] Add version frontmatter to all commands
- [x] Add version frontmatter to all skills
- [x] Verify all agents have consistent versions
- [x] Create frontmatter templates for future artifacts

### CCS.3: Create Version Verification Scripts

- [ ] `scripts/audit-versions.sh` - Detect mismatches
- [ ] `scripts/sync-versions.py` - Bulk version updates
- [ ] `scripts/compare-versions.sh` - Version comparison tool

### CCS.4: CI/CD Integration

- [ ] Create `.github/workflows/version-audit.yml`
- [ ] Run audit on every PR and commit
- [ ] Block merge if versions don't match

### CCS.5: Update Registry Metadata

- [ ] Add version fields to `docs/registries/nuget/registry.json`
- [ ] Include artifact count per version
- [ ] Document version compatibility

### CCS.6: Developer Documentation

- [ ] Update `CONTRIBUTING.md` with versioning section
- [ ] Add version management instructions for package maintainers
- [ ] Document bump procedures

---

## Examples

### Creating a New Version

When releasing version 0.5.0 of `delay-tasks`:

1. Update package manifest:
   ```yaml
   # packages/delay-tasks/manifest.yaml
   version: 0.5.0
   ```

2. Update all artifacts:
   ```yaml
   # packages/delay-tasks/commands/delay.md
   version: 0.5.0

   # packages/delay-tasks/skills/delaying-tasks/SKILL.md
   version: 0.5.0

   # packages/delay-tasks/agents/delay-once.md
   version: 0.5.0
   ```

3. Use sync script:
   ```bash
   python3 scripts/sync-versions.py --package delay-tasks --version 0.5.0
   ```

4. Update CHANGELOG:
   ```bash
   # Add entry to packages/delay-tasks/CHANGELOG.md
   ```

5. Commit with clear message:
   ```bash
   git commit -m "chore(delay-tasks): release v0.5.0"
   ```

### Checking Version Consistency

```bash
# Audit all versions
./scripts/audit-versions.sh

# Compare versions by package
./scripts/compare-versions.sh --by-package

# Show version mismatches
./scripts/compare-versions.sh --mismatches
```

---

## Marketplace Release Cycle

When all packages reach feature parity and stability, bump the marketplace version:

```yaml
# version.yaml
version: 1.0.0  # Production release
```

At this point:
- All packages should be >= 1.0.0
- All breaking changes documented
- Registry format stable
- Installation process proven

---

## Version Compatibility Matrix

| Marketplace | Min Package | Agents | Commands | Skills |
|-------------|-------------|--------|----------|--------|
| 0.4.0 | 0.4.0 | 0.4.0+ | 0.4.0+ | 0.4.0+ |
| 1.0.0 | 1.0.0 | 1.0.0+ | 1.0.0+ | 1.0.0+ |

---

## Best Practices

1. **Always bump versions together** - Package and artifacts must stay in sync
2. **Use automated scripts** - `sync-versions.py` prevents manual errors
3. **Test after versioning** - Run `audit-versions.sh` before committing
4. **Document changes** - Update CHANGELOG.md with every bump
5. **Plan releases** - Coordinate version bumps across related packages
6. **Maintain backwards compatibility** - Use MAJOR version for breaking changes

---

## Related Files

- `version.yaml` - Current marketplace platform version
- `packages/*/manifest.yaml` - Individual package manifests
- `CHANGELOG.md` - Release history for each package
- `scripts/audit-versions.sh` - Version consistency checker
- `scripts/sync-versions.py` - Bulk version updater
- `.github/workflows/version-audit.yml` - CI enforcement
