# Synaptic Canvas Release Process

This document defines the complete release process for the Synaptic Canvas marketplace platform, including versioning strategy, pre-release procedures, execution steps, and post-release verification.

## Table of Contents

- [Script Mapping Reference](#script-mapping-reference)
- [Overview](#overview)
- [Versioning System](#versioning-system)
- [Release Roles and Responsibilities](#release-roles-and-responsibilities)
- [Pre-Release Checklist](#pre-release-checklist)
- [Release Execution](#release-execution)
- [Release Scenarios](#release-scenarios)
- [Post-Release Procedures](#post-release-procedures)
- [Rollback and Incident Procedures](#rollback-and-incident-procedures)
- [Script Usage Examples](#script-usage-examples)
- [Command Reference](#command-reference)

---

## Script Mapping Reference

All release automation is handled by Python scripts in the `scripts/` directory. This table provides a quick reference for which script to use at each release step.

### Primary Release Scripts

| Script | Purpose | Exit Codes | Usage Phase |
|--------|---------|------------|-------------|
| `scripts/sync-versions.py` | Synchronize versions across package artifacts | 0=success, 1=error | Version bump |
| `scripts/update-registry.py` | Update registry.json with new versions | 0=success, 1=error | Pre-release |
| `scripts/sync-marketplace-json.py` | Sync marketplace.json with registry | 0=success, 1=error | Pre-release |
| `scripts/validate-all.py` | Run all validation checks | 0=pass, 1=fail, 2=critical | Pre-release gate |
| `scripts/audit-versions.py` | Check version consistency | 0=pass, 1=fail, 2=critical | Any time |
| `scripts/compare-versions.py` | Compare versions across packages | 0=consistent | Any time |
| `scripts/generate-validation-report.py` | Generate HTML validation reports | 0=success | Pre-release |

### Validation Scripts

| Script | Purpose | Exit Codes |
|--------|---------|------------|
| `scripts/validate-agents.py` | Validate agent artifact structure | 0=pass, 1=fail |
| `scripts/validate-cross-references.py` | Check cross-references between artifacts | 0=pass, 1=fail |
| `scripts/validate-frontmatter-schema.py` | Validate YAML frontmatter schemas | 0=pass, 1=fail |
| `scripts/validate-manifest-artifacts.py` | Verify manifests match actual artifacts | 0=pass, 1=fail |
| `scripts/validate-marketplace-sync.py` | Ensure marketplace.json is in sync | 0=pass, 1=fail |
| `scripts/validate-script-references.py` | Check script references in artifacts | 0=pass, 1=fail |
| `scripts/security-scan.py` | Run security vulnerability scan | 0=pass, 1=warnings, 2=critical |

---

## Overview

The Synaptic Canvas release process manages three versioning layers:

1. **Marketplace Platform** (`version.yaml`) - Infrastructure and CLI
2. **Packages** (`packages/*/manifest.yaml`) - Individual package versions
3. **Artifacts** (YAML frontmatter) - Commands, skills, agents synchronized with package

**Current Status:** 0.7.0 (Beta)

### Release Frequency

- **Beta Phase (0.x.x):** As-needed releases for new features and bug fixes
- **Stable Phase (1.0.0+):** Monthly releases or as-needed hotfixes

### Semantic Versioning

All versions follow MAJOR.MINOR.PATCH format:

- **MAJOR (X):** Breaking changes, major refactoring, incompatible API changes
- **MINOR (Y):** New features, new artifacts, functionality enhancements
- **PATCH (Z):** Bug fixes, documentation updates, minor refinements

---

## Versioning System

### Three-Layer Architecture

**Layer 1: Marketplace Platform Version**
- Location: `/version.yaml`
- Purpose: Infrastructure and CLI version
- Bump when: Major changes to registry format, installer changes, marketplace-wide features

**Layer 2: Package Versions**
- Location: `packages/<package-name>/manifest.yaml`
- Purpose: Individual package versions (independent per package)
- Synchronization: All artifacts in a package share the package version

**Layer 3: Artifact Versions**
- Location: Frontmatter YAML in `.md` files
- Purpose: Track command, skill, and agent versions
- Synchronization: Must match parent package version

### Version Synchronization Rules

- All commands in a package must have the same version as manifest
- All skills in a package must have the same version as manifest
- All agents in a package must have the same version as manifest
- Cross-package agents can use marketplace version

---

## Release Roles and Responsibilities

### Release Manager

**Qualifications:** Maintainer with repository write access

**Responsibilities:**
- Determine release scope (packages, version numbers)
- Approve version bumps
- Execute release commands
- Create GitHub releases
- Update registry metadata
- Communicate status to team

### Package Maintainers

**Qualifications:** Package owner or designated contributor

**Responsibilities:**
- Update package version in manifest
- Update CHANGELOG.md with release notes
- Ensure all artifacts are current
- Request version bump from Release Manager

### Release Verifier

**Qualifications:** Any maintainer or designated tester

**Responsibilities:**
- Verify post-release packages are installable
- Test core functionality
- Confirm registry metadata is accurate
- Report any issues immediately

---

## Pre-Release Checklist

### 1. Version Number Review and Approval

**Purpose:** Ensure version bump is appropriate

**Script:** `python3 scripts/audit-versions.py --verbose`

**Checklist:**

- [ ] **Version bump is appropriate**
  - Check semantic versioning rules
  - Confirm no breaking changes for PATCH
  - Verify feature completeness for MINOR

- [ ] **All packages to release identified**
  - List all packages getting new versions
  - Note if this is marketplace-wide release
  - Identify dependencies between packages

- [ ] **Version number format validated**
  ```bash
  # Should match X.Y.Z format
  echo "0.7.0" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$'
  ```

- [ ] **Release Manager approval obtained**

**Example Release Plan:**
```
Release Plan for 2025-01-15

Marketplace Version: 0.7.0 (MINOR - new features)
  - Reason: New registry format, enhanced installer

Packages:
  - sc-delay-tasks: 0.7.0 (new agent, feature)
  - sc-git-worktree: 0.7.0 (bugfix only)
  - sc-manage: 0.7.0 (no change)
  - sc-repomix-nuget: 0.7.0 (no change)

Approval: @maintainer-name
```

### 2. CHANGELOG Verification

**Purpose:** Ensure release notes are complete and accurate

**For each package being released:**

- [ ] **CHANGELOG.md exists and is complete**
  ```bash
  ls packages/<package-name>/CHANGELOG.md
  ```

- [ ] **Unreleased section properly formatted**
  - Follow "Keep a Changelog" format
  - Include Added/Changed/Fixed/Deprecated sections as needed

- [ ] **Version and date filled in**
  ```markdown
  ## [0.7.0] - 2025-01-15

  ### Added
  - New feature description
  ```

### 3. Run Full Validation Suite

**Script:** `python3 scripts/validate-all.py`

This runs all validation scripts in sequence:

```bash
# Full validation suite
python3 scripts/validate-all.py

# Or run individual validations
python3 scripts/audit-versions.py --verbose
python3 scripts/validate-agents.py
python3 scripts/validate-manifest-artifacts.py
python3 scripts/validate-cross-references.py
python3 scripts/validate-frontmatter-schema.py
python3 scripts/validate-marketplace-sync.py
python3 scripts/validate-script-references.py
```

**Expected Output:**
```
=== Synaptic Canvas Validation Suite ===

Running audit-versions.py... PASSED
Running validate-agents.py... PASSED
Running validate-manifest-artifacts.py... PASSED
Running validate-cross-references.py... PASSED
Running validate-frontmatter-schema.py... PASSED
Running validate-marketplace-sync.py... PASSED
Running validate-script-references.py... PASSED

=== All Validations Passed ===
```

### 4. Registry Metadata Updates

**Script:** `python3 scripts/update-registry.py`

**Purpose:** Ensure registry accurately reflects new release

**Checklist:**

- [ ] **Package entry in registry.json**
  - Version field updated to new version
  - `lastUpdated` timestamp updated
  - Status field reflects release status

- [ ] **Artifact counts accurate**
  - Command count matches actual commands
  - Skill count matches actual skills
  - Agent count matches actual agents

**Example Registry Entry:**
```json
"sc-delay-tasks": {
  "name": "sc-delay-tasks",
  "version": "0.7.0",
  "status": "beta",
  "lastUpdated": "2025-01-15",
  "description": "Schedule delayed or interval-based actions with minimal heartbeats",
  "artifacts": {
    "commands": 1,
    "skills": 1,
    "agents": 3,
    "scripts": 1
  }
}
```

### 5. Testing Requirements

**Automated Tests:**

```bash
# Version audit
python3 scripts/audit-versions.py --verbose

# Version sync dry run
python3 scripts/sync-versions.py --package <name> --version <new-version> --dry-run

# Manifest validation
python3 -c "
import yaml
for pkg in ['sc-delay-tasks', 'sc-git-worktree', 'sc-manage', 'sc-repomix-nuget']:
    with open(f'packages/{pkg}/manifest.yaml') as f:
        data = yaml.safe_load(f)
        print(f'{pkg}: v{data[\"version\"]}')
"
```

**Manual Tests:**

- [ ] **Local package installation**
  ```bash
  mkdir -p /tmp/test-release
  python3 tools/sc-install.py install <package-name> --dest /tmp/test-release/.claude
  ls -la /tmp/test-release/.claude/commands/
  ls -la /tmp/test-release/.claude/agents/
  ```

- [ ] **Version consistency**
  ```bash
  grep "version:" packages/<package-name>/manifest.yaml
  grep -r "version:" /tmp/test-release/.claude/commands/
  grep -r "version:" /tmp/test-release/.claude/agents/
  ```

---

## Release Execution

### Step 1: Create Release Branch

**Branch naming conventions:**

```
release/marketplace-v<version>      # Marketplace release
release/package-<name>-v<version>   # Single package
release/packages-v<version>         # All packages simultaneous
release/patch-<name>-v<version>     # Hotfix/patch release
```

**Create branch:**

```bash
# Marketplace release
git checkout -b release/marketplace-v0.7.0

# Single package
git checkout -b release/package-sc-delay-tasks-v0.7.0

# All packages
git checkout -b release/packages-v0.7.0
```

### Step 2: Update Version Numbers

**Script:** `python3 scripts/sync-versions.py`

**2a. Update marketplace version (if applicable):**

```bash
python3 scripts/sync-versions.py --marketplace --version 0.7.0
```

**2b. Update package versions:**

```bash
# Single package
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.7.0

# All packages to same version
python3 scripts/sync-versions.py --all --version 0.7.0

# Dry run to preview changes
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.7.0 --dry-run
```

**2c. Verify versions are synchronized:**

```bash
python3 scripts/audit-versions.py --verbose
# Should output: All checks passed (N checks)
# Exit code 0
```

**Files Modified by Sync:**
- `packages/<name>/manifest.yaml` - Package version
- `packages/<name>/commands/*.md` - Command artifact versions
- `packages/<name>/skills/*/SKILL.md` - Skill artifact versions
- `packages/<name>/agents/*.md` - Agent artifact versions

### Step 3: Update Registry and Marketplace JSON

**Scripts:**
- `python3 scripts/update-registry.py`
- `python3 scripts/sync-marketplace-json.py`

```bash
# Update registry with new versions
python3 scripts/update-registry.py

# Sync marketplace.json
python3 scripts/sync-marketplace-json.py

# Verify registry is valid JSON
python3 -m json.tool docs/registries/nuget/registry.json > /dev/null && echo "Valid JSON"
```

### Step 4: Update CHANGELOG

**For each package being released:**

```bash
# Edit CHANGELOG.md - move [Unreleased] to [X.Y.Z] - YYYY-MM-DD
vi packages/sc-delay-tasks/CHANGELOG.md
```

**CHANGELOG update template:**

```markdown
## [Unreleased]
### Planned
- Future feature 1

## [0.7.0] - 2025-01-15
### Added
- New feature 1
- New feature 2

## [0.6.0] - 2024-12-02
...
```

### Step 5: Generate Validation Report

**Script:** `python3 scripts/generate-validation-report.py`

```bash
# Generate HTML validation report
python3 scripts/generate-validation-report.py --output reports/

# View the report
open reports/validation-report.html
```

### Step 6: Commit and Create Git Tag

**Commit changes:**

```bash
# Stage version changes
git add version.yaml packages/*/manifest.yaml packages/*/CHANGELOG.md
git add docs/registries/nuget/registry.json
git add .claude-plugin/marketplace.json

# Commit with clear message
git commit -m "chore: release marketplace v0.7.0

- Update marketplace platform version to 0.7.0
- Enhanced installer with new registry format support
- Updated all affected packages
- See CHANGELOG.md for full details"
```

**Create annotated git tag:**

```bash
# Marketplace release
git tag -a v0.7.0 -m "Marketplace Platform v0.7.0

- Enhanced installer
- New registry format (v2.0.0+)
- Better error handling
- See CHANGELOG.md for full details"

# Single package release
git tag -a v0.7.0-sc-delay-tasks -m "sc-delay-tasks v0.7.0

- New delay scheduler with persistent storage
- Support cron-like scheduling patterns
- Fix memory leak in polling loop

See packages/sc-delay-tasks/CHANGELOG.md"
```

**Push changes and tags:**

```bash
git push origin release/marketplace-v0.7.0
git push origin v0.7.0
```

### Step 7: Create GitHub Release

**Using gh CLI:**

```bash
gh release create v0.7.0 \
  --title "Marketplace v0.7.0" \
  --notes "$(cat release-notes-0.7.0.md)"
```

---

## Release Scenarios

### Scenario 1: Single Package Release

**Example:** Release only sc-delay-tasks v0.7.1 (marketplace stays 0.7.0)

```bash
# 1. Create release branch
git checkout -b release/package-sc-delay-tasks-v0.7.1

# 2. Update version
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.7.1

# 3. Update CHANGELOG
vi packages/sc-delay-tasks/CHANGELOG.md

# 4. Update registry
python3 scripts/update-registry.py

# 5. Run validations
python3 scripts/validate-all.py

# 6. Commit
git add packages/sc-delay-tasks/
git commit -m "chore(sc-delay-tasks): release v0.7.1"

# 7. Tag
git tag -a v0.7.1-sc-delay-tasks -m "sc-delay-tasks v0.7.1"
git push origin v0.7.1-sc-delay-tasks

# 8. Create release
gh release create v0.7.1-sc-delay-tasks --notes "$(head -30 packages/sc-delay-tasks/CHANGELOG.md)"
```

### Scenario 2: Marketplace Platform Release

**Example:** Release marketplace v0.8.0 with all packages

```bash
# 1. Create release branch
git checkout -b release/marketplace-v0.8.0

# 2. Update marketplace version
python3 scripts/sync-versions.py --marketplace --version 0.8.0

# 3. Update all packages
python3 scripts/sync-versions.py --all --version 0.8.0

# 4. Update all CHANGELOGs
for pkg in packages/*/; do
  vi "$pkg/CHANGELOG.md"
done

# 5. Update registry and marketplace.json
python3 scripts/update-registry.py
python3 scripts/sync-marketplace-json.py

# 6. Run validations
python3 scripts/validate-all.py

# 7. Commit
git add version.yaml packages/*/ docs/registries/
git commit -m "chore: release marketplace v0.8.0 with all packages"

# 8. Tag
git tag -a v0.8.0 -m "Marketplace v0.8.0 release"
git push origin v0.8.0
```

### Scenario 3: Patch/Hotfix Release

**Example:** Release patch v0.7.1 for sc-delay-tasks (critical bugfix)

```bash
# 1. Create patch branch from tag
git checkout -b release/patch-sc-delay-tasks-v0.7.1 v0.7.0-sc-delay-tasks

# 2. Apply bugfix commits
git cherry-pick <commit-hash>

# 3. Update to patch version
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.7.1

# 4. Update CHANGELOG
vi packages/sc-delay-tasks/CHANGELOG.md

# 5. Run validations
python3 scripts/validate-all.py

# 6. Commit and tag
git add packages/sc-delay-tasks/
git commit -m "fix(sc-delay-tasks): memory leak in polling loop (v0.7.1)"
git tag -a v0.7.1-sc-delay-tasks -m "sc-delay-tasks v0.7.1 - Critical bugfix"

# 7. Push
git push origin release/patch-sc-delay-tasks-v0.7.1
git push origin v0.7.1-sc-delay-tasks

# 8. Create hotfix release
gh release create v0.7.1-sc-delay-tasks \
  --prerelease \
  --title "sc-delay-tasks v0.7.1 - Critical Hotfix" \
  --notes "## Critical Bugfix
Fixed memory leak in polling operations affecting v0.7.0 users.
**Upgrade immediately if using v0.7.0 polling features.**"
```

---

## Post-Release Procedures

### Step 1: Verification Checks

**Verify GitHub Release:**

```bash
gh release list --repo randlee/synaptic-canvas
gh release view v0.7.0
```

**Verify Git Tags:**

```bash
git tag -l "v*" | sort -V | tail -10
git show v0.7.0
```

**Verify Registry Updated:**

```bash
python3 -c "
import json
with open('docs/registries/nuget/registry.json') as f:
    reg = json.load(f)
    print(f'Marketplace: v{reg[\"marketplace\"][\"version\"]}')
    for pkg, data in reg['packages'].items():
        print(f'  {pkg}: v{data[\"version\"]}')
"
```

### Step 2: Installation and Functionality Tests

```bash
# Test installation
mkdir -p /tmp/post-release-test
python3 tools/sc-install.py install <package-name> --dest /tmp/post-release-test/.claude

# Verify installation
ls /tmp/post-release-test/.claude/commands/
ls /tmp/post-release-test/.claude/agents/

# Check artifact versions
for artifact in /tmp/post-release-test/.claude/agents/*.md; do
    VERSION=$(grep "^version:" "$artifact" | head -1 | cut -d'"' -f2)
    echo "  - $(basename $artifact): v$VERSION"
done

# Cleanup
rm -rf /tmp/post-release-test
```

### Step 3: Monitor for Issues

**First 24 hours monitoring:**

```bash
# Check GitHub issues
gh issue list --repo randlee/synaptic-canvas --limit 5 --state open

# Monitor CI pipeline
gh run list --repo randlee/synaptic-canvas --limit 3
```

---

## Rollback and Incident Procedures

### Quick Rollback (Revert Release)

```bash
# Revert the release commit
git revert <release-commit-hash> --no-edit

# Create rollback tag
git tag -a v0.7.0-rollback -m "Rollback: v0.7.0 - Critical issue"

# Push rollback
git push origin main
git push origin v0.7.0-rollback
```

### Hotfix Procedure

```bash
# Create hotfix branch from tag
git checkout -b hotfix/<issue> v0.7.0

# Apply fix
vi packages/<package>/scripts/<file>.py

# Update version to patch
python3 scripts/sync-versions.py --package <name> --version 0.7.1

# Commit and tag
git add packages/<name>/
git commit -m "fix(<package>): <description> (v0.7.1)"
git tag -a v0.7.1-<package> -m "<package> v0.7.1 - Critical bugfix"

# Push
git push origin hotfix/<issue>
git push origin v0.7.1-<package>
```

### Delete/Retract Release (Emergency)

```bash
# Delete tag
git tag -d v0.7.0
git push origin :refs/tags/v0.7.0

# Delete GitHub release
gh release delete v0.7.0 --yes

# Revert commit
git revert <release-commit-hash>
git push origin main
```

---

## Script Usage Examples

### sync-versions.py

```bash
# Preview changes (dry run)
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.7.1 --dry-run

# Update single package
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.7.1

# Update all packages
python3 scripts/sync-versions.py --all --version 0.7.0

# Update marketplace only
python3 scripts/sync-versions.py --marketplace --version 0.7.0

# Update with auto-commit
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.7.1 --commit
```

### audit-versions.py

```bash
# Quick audit
python3 scripts/audit-versions.py

# Verbose output
python3 scripts/audit-versions.py --verbose

# Exit codes:
# 0 = All checks passed
# 1 = Mismatches found
# 2 = Critical errors
```

### compare-versions.py

```bash
# Show by package
python3 scripts/compare-versions.py --by-package

# Show mismatches only
python3 scripts/compare-versions.py --mismatches

# Verbose with artifact details
python3 scripts/compare-versions.py --verbose --by-package

# JSON output for automation
python3 scripts/compare-versions.py --json
```

### update-registry.py

```bash
# Update registry from manifests
python3 scripts/update-registry.py

# Verify update
python3 -m json.tool docs/registries/nuget/registry.json > /dev/null && echo "Valid"
```

### validate-all.py

```bash
# Run all validations
python3 scripts/validate-all.py

# Individual validations
python3 scripts/validate-agents.py
python3 scripts/validate-manifest-artifacts.py
python3 scripts/validate-cross-references.py
python3 scripts/validate-frontmatter-schema.py
python3 scripts/validate-marketplace-sync.py
python3 scripts/validate-script-references.py
```

### generate-validation-report.py

```bash
# Generate HTML report
python3 scripts/generate-validation-report.py --output reports/

# Generate with custom format
python3 scripts/generate-validation-report.py --format json --output reports/

# Open report
open reports/validation-report.html
```

---

## Command Reference

### Version Management Scripts

```bash
# Audit versions
python3 scripts/audit-versions.py --verbose

# Compare versions
python3 scripts/compare-versions.py --by-package

# Sync versions
python3 scripts/sync-versions.py --package <name> --version <version>
python3 scripts/sync-versions.py --all --version <version>
python3 scripts/sync-versions.py --marketplace --version <version>
```

### Registry Scripts

```bash
# Update registry
python3 scripts/update-registry.py

# Sync marketplace.json
python3 scripts/sync-marketplace-json.py
```

### Validation Scripts

```bash
# Run all validations
python3 scripts/validate-all.py

# Individual validations
python3 scripts/validate-agents.py
python3 scripts/validate-manifest-artifacts.py
python3 scripts/validate-cross-references.py
python3 scripts/validate-frontmatter-schema.py
python3 scripts/validate-marketplace-sync.py
python3 scripts/validate-script-references.py
python3 scripts/security-scan.py
```

### Git Commands

```bash
# Create and manage branches
git checkout -b release/marketplace-v0.7.0
git push origin release/marketplace-v0.7.0

# Tag releases
git tag -a v0.7.0 -m "Release message"
git push origin v0.7.0
git tag -d v0.7.0  # Delete local tag
git push origin :refs/tags/v0.7.0  # Delete remote tag
```

### GitHub CLI Commands

```bash
# Manage releases
gh release create v0.7.0 --title "Title" --notes "Release notes"
gh release list --repo randlee/synaptic-canvas
gh release view v0.7.0
gh release delete v0.7.0 --yes

# Manage issues
gh issue create --title "Title" --body "Description" --label "critical"
gh issue list --state open --label "release"
```

### Package Installation Commands

```bash
# Install packages
python3 tools/sc-install.py install <package> --dest ~/.claude
python3 tools/sc-install.py install <package> --version 0.7.0 --dest ~/.claude

# Uninstall packages
python3 tools/sc-install.py uninstall <package> --dest ~/.claude

# List packages
python3 tools/sc-install.py list
python3 tools/sc-install.py info <package>
```

---

## Appendix: Release Checklist Template

### Release Checklist - [Package Name] v[Version]

**Pre-Release (1 day before):**
- [ ] Version number reviewed and approved
- [ ] CHANGELOG.md updated and reviewed
- [ ] Documentation updated
- [ ] Registry metadata prepared
- [ ] `python3 scripts/validate-all.py` passes
- [ ] Manual smoke tests completed

**Release Day:**
- [ ] Create release branch
- [ ] `python3 scripts/sync-versions.py` executed
- [ ] `python3 scripts/update-registry.py` executed
- [ ] `python3 scripts/sync-marketplace-json.py` executed
- [ ] `python3 scripts/audit-versions.py --verbose` passes
- [ ] `python3 scripts/generate-validation-report.py` executed
- [ ] Commit changes
- [ ] Create git tag
- [ ] Create GitHub release with notes
- [ ] Verify registry JSON validity

**Post-Release (2 hours after):**
- [ ] Installation test successful
- [ ] Artifacts verify correctly
- [ ] No critical issues reported

**Post-Release (24 hours after):**
- [ ] No critical issues reported
- [ ] Monitor GitHub issues/discussions
- [ ] Document any learnings

---

## References

- [RELEASING.md](../RELEASING.md) - High-level release overview
- [Versioning Strategy](versioning-strategy.md)
- [Package Registry Format](registries/nuget/README.md)
- [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
- [Semantic Versioning](https://semver.org/)

---

**Document Version:** 0.7.0
**Last Updated:** January 2025
**Maintained By:** Synaptic Canvas Maintainers
