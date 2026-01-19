# Synaptic Canvas Version Release Guide

**Audience:** Marketplace maintainers, package developers, release coordinators
**Last Updated:** December 2, 2025
**Current System Version:** 0.4.0 (Beta)
**Registry Version:** 2.0.0 (Stable)

---

## Table of Contents

1. [Understanding Version Changes](#1-understanding-version-changes)
2. [Preparing for Release](#2-preparing-for-release)
3. [Version Update Procedures](#3-version-update-procedures)
4. [Version Verification](#4-version-verification)
5. [Coordinated Release Scenarios](#5-coordinated-release-scenarios)
6. [Version Compatibility](#6-version-compatibility)
7. [Documentation Updates](#7-documentation-updates)
8. [Release Branching Strategy](#8-release-branching-strategy)
9. [Common Scenarios with Examples](#9-common-scenarios-with-examples)
10. [Automation & CI/CD](#10-automation--cicd)
11. [Rollback Procedures](#11-rollback-procedures)
12. [Best Practices](#12-best-practices)

---

## 1. Understanding Version Changes

Synaptic Canvas uses **Semantic Versioning (SemVer)** format: `MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]`

### The Three-Layer Versioning System

```
┌─────────────────────────────────────┐
│  Layer 1: Marketplace Platform      │  version.yaml
│  (Infrastructure, CLI, Registry)    │  Example: 0.4.0
└─────────────────────────────────────┘
           ↓ references
┌─────────────────────────────────────┐
│  Layer 2: Package Versions          │  manifest.yaml per package
│  (Independent per package)          │  Example: sc-delay-tasks v0.4.0
└─────────────────────────────────────┘
           ↓ synchronized with
┌─────────────────────────────────────┐
│  Layer 3: Artifact Versions         │  Frontmatter in commands/
│  (Commands, Skills, Agents)         │  skills/, agents/*.md
│  Synchronized with package version  │  Example: delay.md v0.4.0
└─────────────────────────────────────┘
```

### Current Versions

| Component | Version | Status | Location |
|-----------|---------|--------|----------|
| **Marketplace** | 0.4.0 | Beta | `version.yaml` |
| **sc-delay-tasks** | 0.4.0 | Beta | `packages/sc-delay-tasks/manifest.yaml` |
| **sc-git-worktree** | 0.4.0 | Beta | `packages/sc-git-worktree/manifest.yaml` |
| **sc-manage** | 0.4.0 | Beta | `packages/sc-manage/manifest.yaml` |
| **sc-repomix-nuget** | 0.4.0 | Beta | `packages/sc-repomix-nuget/manifest.yaml` |
| **Registry Format** | 2.0.0 | Stable | `docs/registries/nuget/registry.json` |

### When to Bump MAJOR Version

Bump the first digit when:

- **Breaking changes** to APIs, manifests, or installed artifacts
- **Incompatible registry format** changes
- **CLI interface changes** that break existing workflows
- **Package removal or deprecation**
- **Preparation for production/stable release** (e.g., 0.x.x → 1.0.0)
- **Major refactoring** with behavioral changes

**Examples:**
- Moving from 0.4.0 to 1.0.0 for production release
- Changing `manifest.yaml` schema format
- Removing deprecated commands or agents

### When to Bump MINOR Version

Bump the second digit when:

- **New features** (new commands, skills, agents, capabilities)
- **Functionality enhancements** to existing features
- **New package types** or artifact categories
- **Enhanced registry metadata** with new optional fields
- **Performance improvements** without changing behavior
- **New CLI options** with default fallback behavior

**Examples:**
- Adding a new agent to sc-delay-tasks: 0.4.0 → 0.5.0
- Adding optional fields to manifest.yaml schema: 0.4.0 → 0.5.0
- Releasing sc-manage package manager updates: 0.4.0 → 0.5.0

### When to Bump PATCH Version

Bump the third digit when:

- **Bug fixes** to existing functionality
- **Documentation updates** or corrections
- **Non-breaking improvements** to existing artifacts
- **Security patches** for vulnerabilities
- **Dependency updates** that don't affect API
- **CI/CD or test infrastructure** changes

**Examples:**
- Fixing a timeout issue in delay-poll agent: 0.4.0 → 0.4.1
- Correcting documentation in README files: 0.4.0 → 0.4.1
- Updating helper scripts with bug fixes: 0.4.0 → 0.4.1

### Pre-Release Versions

For features in development or testing phases before formal release:

**Format:** `MAJOR.MINOR.PATCH-PRERELEASE`

**Examples:**
- `0.5.0-alpha` - Early development, may be unstable
- `0.5.0-beta` - Feature complete, needs testing
- `0.5.0-rc1` - Release candidate, final testing phase
- `1.0.0-rc2` - Second release candidate

**Rules:**
- Pre-release versions are sorted lexicographically
- `1.0.0-alpha < 1.0.0-beta < 1.0.0-rc1 < 1.0.0`
- Pre-release versions should be used sparingly
- Move to release version once testing is complete

**Current Status:** All packages are at 0.4.0 (beta) - use pre-release tags for development cycles only

### Build Metadata

**Format:** `MAJOR.MINOR.PATCH+BUILD`

**Examples:**
- `0.4.0+20251202` - Build date metadata
- `0.4.0+git.9683dff` - Git commit hash metadata
- `0.4.0+build.123` - Build number metadata

**Rules:**
- Build metadata does NOT affect version precedence
- Used for internal tracking, not in public releases
- Generally not needed for marketplace releases

---

## 2. Preparing for Release

### Release Planning Checklist

Before bumping any versions, establish a release plan:

- [ ] **Identify release scope** - which packages are being released?
- [ ] **Determine version changes** - apply SemVer guidelines from Section 1
- [ ] **Review all CHANGELOGs** - ensure accurate feature/fix descriptions
- [ ] **Test all artifacts** - verify all commands, skills, agents work correctly
- [ ] **Check dependencies** - ensure package dependencies are satisfied
- [ ] **Verify backward compatibility** - no breaking changes unless intentional
- [ ] **Update documentation** - READMEs, guides, compatibility matrix
- [ ] **Notify stakeholders** - inform users of upcoming changes
- [ ] **Establish feature freeze** - no new features merged to release branch

### Version Audit

Before making any version changes, audit the current state using provided scripts.

#### Quick Audit (read-only)

```bash
# Check all version consistency
./scripts/audit-versions.py

# Expected output on success:
# === Audit Results ===
# Total checks: 45
# Passed: 45
# Failed: 0
# Warnings: 0
# All checks passed!
```

#### Detailed Audit with Verbose Output

```bash
# See each check being performed
./scripts/audit-versions.py --verbose

# Output shows:
# ✓ Command: delay.md (v0.4.0)
# ✓ Skill: delaying-tasks (v0.4.0)
# ✓ Agent: delay-once.md (v0.4.0)
# ... (one line per artifact)
```

#### Compare Versions Across Packages

```bash
# Show marketplace and all package versions
./scripts/compare-versions.sh --by-package

# Output:
# === Synaptic Canvas Version Comparison ===
# Marketplace Version: 0.4.0
# Package: sc-delay-tasks (manifest: 0.4.0)
# Package: sc-git-worktree (manifest: 0.4.0)
# ...

# Find only packages with mismatches
./scripts/compare-versions.sh --mismatches

# Show detailed artifact versions
./scripts/compare-versions.sh --verbose --by-package
```

### Review CHANGELOGs

Each package has a CHANGELOG.md following [Keep a Changelog](https://keepachangelog.com/) format:

**Location:** `packages/<package-name>/CHANGELOG.md`

**Structure:**
```markdown
# Changelog

## [Unreleased]
### Planned
- Future feature ideas

## [0.4.0] - 2025-12-02
### Added
- New features
### Fixed
- Bug fixes
### Changed
- Behavioral changes
```

**Audit CHANGELOG for release:**

```bash
# Verify all CHANGELOGs exist
for pkg in packages/*/; do
  if [ ! -f "$pkg/CHANGELOG.md" ]; then
    echo "Missing: $pkg/CHANGELOG.md"
  fi
done

# Check for [Unreleased] section (should exist for active development)
grep -l "## \[Unreleased\]" packages/*/CHANGELOG.md
```

### Determine Version Strategy

Use this decision matrix to determine which packages need version bumps:

```
┌─────────────────────────────────────┬──────────────┐
│ Scenario                            │ Version Bump │
├─────────────────────────────────────┼──────────────┤
│ New features, backward compatible   │ MINOR bump   │
│ Bug fixes only                      │ PATCH bump   │
│ Breaking changes                    │ MAJOR bump   │
│ Production release from beta        │ MAJOR bump   │
│ Documentation fixes only            │ PATCH bump   │
│ New artifacts (commands/agents)     │ MINOR bump   │
│ Emergency security fix              │ PATCH bump   │
│ Dependency update (no API change)   │ PATCH bump   │
│ No changes needed                   │ No bump      │
└─────────────────────────────────────┴──────────────┘
```

**Example Decision Process:**

> I want to release sc-delay-tasks with 2 new agents and 1 bug fix.
> - New agents = MINOR bump
> - Bug fix = would be PATCH, but MINOR takes precedence
> - Decision: 0.4.0 → 0.5.0

### Feature Freeze and Testing Period

1. **Feature Freeze** (3-5 days before release)
   - No new features merged to release branch
   - Only bug fixes and documentation updates permitted
   - All developers freeze feature work for this package

2. **Testing Period** (2-3 days minimum)
   - Install package from development branch
   - Test all new artifacts
   - Verify backward compatibility with existing scripts
   - Run full test suite if available
   - Manual integration testing

3. **Documentation Review** (1-2 days)
   - Update READMEs with new features
   - Update version compatibility matrix
   - Update CHANGELOG with release date
   - Review CI/CD configuration

4. **Sign-Off** (before merge to main)
   - At least one maintainer review
   - All CI/CD checks passing
   - No known breaking issues
   - Registry metadata prepared

---

## 3. Version Update Procedures

### Understanding the Sync Process

The `sync-versions.py` script updates:

1. **Package manifest** (`manifest.yaml`) - source of truth for package version
2. **All commands** (`commands/*.md`) - frontmatter version field
3. **All skills** (`skills/*/SKILL.md`) - frontmatter version field
4. **All agents** (`agents/*.md` and `.claude/agents/*.md`) - frontmatter version field
5. **Marketplace version** (`version.yaml`) - if using `--marketplace` flag

**Important:** The script ONLY handles version synchronization. You must still:
- Update CHANGELOG.md manually
- Create git commits manually (or use `--commit` flag)
- Push to remote manually
- Update registry metadata manually

### Single Package Update

Release a new version of one package only.

**Syntax:**
```bash
python3 scripts/sync-versions.py --package <NAME> --version <VERSION> [--commit] [--dry-run]
```

**Parameters:**
- `--package NAME` - package name (must match `packages/*/` directory name)
- `--version VERSION` - semantic version (X.Y.Z format only, no pre-release in this tool)
- `--commit` - automatically create git commit with changes
- `--dry-run` - show what would change without making changes

**Example: Release sc-delay-tasks v0.5.0**

```bash
# First, verify what will change
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.0 --dry-run

# Output:
# Syncing sc-delay-tasks to version 0.5.0...
#   ✓ Updated: packages/sc-delay-tasks/manifest.yaml
#   ✓ Updated: packages/sc-delay-tasks/commands/delay.md
#   ✓ Updated: packages/sc-delay-tasks/skills/delaying-tasks/SKILL.md
#   ✓ Updated: packages/sc-delay-tasks/agents/delay-once.md
#   ✓ Updated: packages/sc-delay-tasks/agents/delay-poll.md
#   ✓ Updated: packages/sc-delay-tasks/agents/git-pr-check-delay.md
# Updated 6 file(s) in sc-delay-tasks

# Apply the changes
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.0

# Create commit with auto message
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.0 --commit

# Or commit manually after with custom message
git add packages/sc-delay-tasks/
git commit -m "chore(release): bump sc-delay-tasks to v0.5.0

- Added new agent: delay-exponential-backoff
- Added new agent: delay-conditional
- Fixed timeout issue in delay-poll
- Updated documentation with examples"
```

### Marketplace Version Update

Release a new version of the marketplace infrastructure (registry format, CLI, installation system).

**Syntax:**
```bash
python3 scripts/sync-versions.py --marketplace --version <VERSION> [--commit] [--dry-run]
```

**When to use:**
- Major changes to `version.yaml` schema
- Breaking changes to registry format
- New marketplace-wide features
- CLI or installer updates

**Example: Release marketplace v1.0.0 for production**

```bash
# Preview changes
python3 scripts/sync-versions.py --marketplace --version 1.0.0 --dry-run

# Output:
# Syncing marketplace to version 1.0.0...
#   ✓ Updated: version.yaml

# Apply with automatic commit
python3 scripts/sync-versions.py --marketplace --version 1.0.0 --commit

# Check what changed
git show --name-only
```

### All Packages Simultaneous Update

Release all packages to the same version at once (used for coordinated releases).

**Syntax:**
```bash
python3 scripts/sync-versions.py --all --version <VERSION> [--commit] [--dry-run]
```

**When to use:**
- Coordinated marketplace release where all packages move together
- Transitioning from beta (0.x) to stable (1.x)
- Critical security fixes affecting all packages

**Example: Release all packages v1.0.0 together**

```bash
# Verify changes
python3 scripts/sync-versions.py --all --version 1.0.0 --dry-run

# Output:
# Syncing all packages to version 1.0.0...
# Syncing sc-delay-tasks to version 1.0.0...
#   ✓ Updated: packages/sc-delay-tasks/manifest.yaml
#   ✓ Updated: packages/sc-delay-tasks/commands/delay.md
#   ... (5 more files)
# Updated 6 file(s) in sc-delay-tasks
# Syncing sc-git-worktree to version 1.0.0...
#   ✓ Updated: packages/sc-git-worktree/manifest.yaml
# ... (repeated for each package)

# Apply changes and commit
python3 scripts/sync-versions.py --all --version 1.0.0 --commit

# Git history shows:
# chore(versioning): sync versions across artifacts
```

### Manual Verification Steps

After running sync scripts, always verify manually:

```bash
# Step 1: Check git status
git status

# Expected output shows modified files in packages/ and version.yaml
# M packages/sc-delay-tasks/manifest.yaml
# M packages/sc-delay-tasks/commands/delay.md
# ... etc

# Step 2: Verify YAML syntax in modified files
python3 -c "
import yaml
import sys
from pathlib import Path

for f in Path('.').glob('packages/*/manifest.yaml'):
    with open(f) as fp:
        try:
            yaml.safe_load(fp)
            print(f'✓ {f}')
        except Exception as e:
            print(f'✗ {f}: {e}')
            sys.exit(1)
"

# Step 3: Spot-check a few files
grep "^version:" packages/sc-delay-tasks/manifest.yaml
grep "^version:" packages/sc-delay-tasks/commands/delay.md
grep "^version:" packages/sc-git-worktree/manifest.yaml

# Step 4: Run audit to confirm consistency
./scripts/audit-versions.py

# Step 5: Review diff before committing
git diff packages/sc-delay-tasks/manifest.yaml | head -20
```

---

## 4. Version Verification

### Version Audit Script

Verifies that all artifacts have versions and they match their package versions.

**Quick check:**
```bash
./scripts/audit-versions.py
```

**Detailed check:**
```bash
./scripts/audit-versions.py --verbose
```

**What it checks:**
- [ ] All commands have version frontmatter
- [ ] All skills have version frontmatter
- [ ] All agents have version frontmatter
- [ ] Artifact versions match package versions
- [ ] CHANGELOG.md files exist
- [ ] Marketplace version is set

**Expected output (success):**
```
=== Synaptic Canvas Version Audit ===

Checking commands...
Checking skills...
Checking agents...
Checking version consistency...
Checking CHANGELOGs...
Checking marketplace version...

=== Audit Results ===
Total checks: 45
Passed: 45
Failed: 0
Warnings: 0

All checks passed!
```

**Exit codes:**
- `0` - All checks passed
- `1` - Mismatches or missing versions found
- `2` - Critical errors (missing directories, etc.)

### Version Comparison Script

Shows versions across packages side-by-side.

**Basic view:**
```bash
./scripts/compare-versions.sh --by-package
```

**Output:**
```
=== Synaptic Canvas Version Comparison ===

Marketplace Version: 0.4.0

Package: sc-delay-tasks (manifest: 0.4.0)
Package: sc-git-worktree (manifest: 0.4.0)
Package: sc-repomix-nuget (manifest: 0.4.0)
Package: sc-manage (manifest: 0.4.0)

All versions consistent!
```

**Detailed view:**
```bash
./scripts/compare-versions.sh --verbose --by-package
```

**Output shows each artifact:**
```
Package: sc-delay-tasks (manifest: 0.4.0)
  ✓ command/delay: 0.4.0
  ✓ skill/delaying-tasks: 0.4.0
  ✓ agent/delay-once: 0.4.0
  ✓ agent/delay-poll: 0.4.0
  ✓ agent/git-pr-check-delay: 0.4.0
```

**Find mismatches only:**
```bash
./scripts/compare-versions.sh --mismatches

# Output only shows packages with version mismatches
# If all consistent, shows "All versions consistent!"
```

**JSON output (for automation):**
```bash
./scripts/compare-versions.sh --json

# Output:
# {
#   "marketplace": "0.4.0",
#   "packages": [
#     {"name": "sc-delay-tasks", "version": "0.4.0", "consistent": true},
#     ...
#   ]
# }
```

### Checking for Mismatches

**Scenario: You suspect a version mismatch exists**

```bash
# Find the mismatch
./scripts/compare-versions.sh --verbose

# Example mismatch output:
# Package: sc-delay-tasks (manifest: 0.5.0)
#   ✗ command/delay: 0.4.0          <-- MISMATCH!
#   ✓ skill/delaying-tasks: 0.5.0
#   ✓ agent/delay-once: 0.5.0

# To find which files are wrong:
grep -r "^version:" packages/sc-delay-tasks/

# Fix the mismatched file:
# Edit packages/sc-delay-tasks/commands/delay.md
# Change: version: 0.4.0
# To:     version: 0.5.0
```

### Registry Validation

Verify the registry JSON is syntactically correct:

```bash
# Validate JSON syntax
python3 -m json.tool docs/registries/nuget/registry.json > /dev/null && echo "✓ Valid JSON"

# Validate against schema (if schema validator available)
python3 docs/registries/nuget/validate-registry.py

# Check registry version and metadata
python3 -c "
import json
with open('docs/registries/nuget/registry.json') as f:
    reg = json.load(f)
    print(f'Registry version: {reg[\"version\"]}')
    print(f'Marketplace: {reg[\"marketplace\"][\"name\"]} v{reg[\"marketplace\"][\"version\"]}')
    print(f'Packages: {list(reg[\"packages\"].keys())}')
"
```

### CI/CD Verification

The repository includes a GitHub Actions workflow that automatically validates versions:

**Workflow:** `.github/workflows/version-audit.yml`

**Checks performed on every push to main/develop:**
1. Run full version audit
2. Compare versions across packages
3. Validate manifest YAML format
4. Check for CHANGELOG files

**View CI/CD results:**
- Go to GitHub repository → Actions tab
- Click "Version Audit" workflow
- See check results and logs

**What happens on CI/CD failure:**
- Pull request cannot be merged
- Maintainers are notified
- Version mismatches must be fixed before merge

### IDE Schema Validation

Set up your IDE to validate manifest and artifact frontmatter:

**Visual Studio Code:**

1. Install YAML extension: `eviline.rainbow-yam`
2. Create/update `.vscode/settings.json`:

```json
{
  "yaml.schemas": {
    "docs/registries/nuget/registry.schema.json": [
      "docs/registries/nuget/registry.json"
    ]
  }
}
```

3. Hover over fields in IDE for validation feedback

**Schema location:** `docs/registries/nuget/registry.schema.json`

---

## 5. Coordinated Release Scenarios

### Scenario 1: Marketplace + All Packages Together

**Situation:** Major coordinated release (e.g., beta → production)

**Release Plan:**
- Marketplace moves 0.4.0 → 1.0.0
- All packages move 0.4.0 → 1.0.0
- Coordinated feature release across ecosystem

**Execution Steps:**

```bash
# Step 1: Create release branch
git checkout -b release/v1.0.0

# Step 2: Update all CHANGELOGs
# Edit each CHANGELOG.md:
# - Move [Unreleased] to [1.0.0] with release date
# - Update all descriptions
# Example for each package:
vim packages/sc-delay-tasks/CHANGELOG.md      # Update to [1.0.0] - 2025-12-15
vim packages/sc-git-worktree/CHANGELOG.md
vim packages/sc-manage/CHANGELOG.md
vim packages/sc-repomix-nuget/CHANGELOG.md

# Step 3: Sync all package versions
python3 scripts/sync-versions.py --all --version 1.0.0

# Step 4: Sync marketplace version
python3 scripts/sync-versions.py --marketplace --version 1.0.0

# Step 5: Verify everything is consistent
./scripts/audit-versions.py

# Step 6: Commit and push
git add -A
git commit -m "chore(release): v1.0.0 - Production Release

All packages and marketplace upgraded to v1.0.0:
- sc-delay-tasks: Added exponential backoff support
- sc-git-worktree: Enhanced worktree cleanup
- sc-manage: Improved package resolution
- sc-repomix-nuget: Production-ready NuGet integration"

git push origin release/v1.0.0

# Step 7: Create pull request
gh pr create --title "Release v1.0.0" --body "Coordinated release of all packages and marketplace"

# Step 8: After review and CI passes, merge
git checkout main
git merge --no-ff release/v1.0.0
git tag -a v1.0.0 -m "Production Release v1.0.0"
git push origin main
git push origin v1.0.0

# Step 9: Update registry
# Edit docs/registries/nuget/registry.json:
# - Update marketplace version to 1.0.0
# - Update all package versions to 1.0.0
# - Update lastUpdated timestamps
# - Regenerate if using automated registry generation

git add docs/registries/nuget/registry.json
git commit -m "chore(registry): update for v1.0.0 release"
git push origin main
```

### Scenario 2: Single Package with Dependencies

**Situation:** Release new version of sc-delay-tasks that requires specific sc-git-worktree version

**Release Plan:**
- sc-delay-tasks 0.4.0 → 0.5.0 (new features)
- sc-git-worktree remains 0.4.0 (no changes)
- Document dependency relationship

**Execution Steps:**

```bash
# Step 1: Create feature branch
git checkout -b feature/sc-delay-tasks-v0.5

# Step 2: Update sc-delay-tasks CHANGELOG
vim packages/sc-delay-tasks/CHANGELOG.md
# Add section:
# ## [0.5.0] - 2025-12-15
# ### Added
# - Exponential backoff agent
# - Conditional delay support
# ### Dependencies
# - Requires: sc-git-worktree >= 0.4.0

# Step 3: Sync sc-delay-tasks version only
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.0

# Step 4: Verify no cross-package impact
./scripts/compare-versions.sh --verbose

# Expected: sc-git-worktree still 0.4.0, sc-delay-tasks now 0.5.0

# Step 5: Commit
git add packages/sc-delay-tasks/
git commit -m "feat(release): sc-delay-tasks v0.5.0 - Exponential backoff support

Added:
- Exponential backoff retry agent
- Conditional delay with environment variable support
- Improved timeout handling

Depends on: sc-git-worktree >= 0.4.0"

git push origin feature/sc-delay-tasks-v0.5

# Step 6: Create PR with clear dependency notes
gh pr create --title "Release sc-delay-tasks v0.5.0" \
  --body "New features for sc-delay-tasks

Dependencies: Requires sc-git-worktree v0.4.0 or later

This release is backward compatible with existing installations."
```

### Scenario 3: Staggered Releases Across Packages

**Situation:** Different packages have different release schedules

**Release Plan:**
- Week 1: sc-git-worktree 0.4.0 → 0.4.1 (bug fix)
- Week 2: sc-delay-tasks 0.4.0 → 0.5.0 (new features)
- Week 3: sc-manage 0.4.0 → 0.5.0 (new features)
- Week 4: sc-repomix-nuget 0.4.0 → 0.5.0 (new features)

**Execution (per package):**

```bash
# WEEK 1: sc-git-worktree patch

git checkout -b hotfix/sc-git-worktree-0.4.1
vim packages/sc-git-worktree/CHANGELOG.md  # Add [0.4.1] entry
python3 scripts/sync-versions.py --package sc-git-worktree --version 0.4.1
./scripts/audit-versions.py
git add packages/sc-git-worktree/
git commit -m "fix(release): sc-git-worktree v0.4.1 - Worktree cleanup fix"
git push origin hotfix/sc-git-worktree-0.4.1

# (After PR review and merge)
git checkout main
git merge hotfix/sc-git-worktree-0.4.1
git tag -a v0.4.1-sc-git-worktree -m "sc-git-worktree v0.4.1"
git push origin main v0.4.1-sc-git-worktree

---

# WEEK 2: sc-delay-tasks minor

git checkout -b feature/sc-delay-tasks-0.5
vim packages/sc-delay-tasks/CHANGELOG.md    # Add [0.5.0] entry
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.0
./scripts/audit-versions.py
git add packages/sc-delay-tasks/
git commit -m "feat(release): sc-delay-tasks v0.5.0 - New agents and improvements"
git push origin feature/sc-delay-tasks-0.5

# (After PR review and merge)
git checkout main
git pull  # Get latest including sc-git-worktree 0.4.1
git merge feature/sc-delay-tasks-0.5
git tag -a v0.5.0-sc-delay-tasks -m "sc-delay-tasks v0.5.0"
git push origin main v0.5.0-sc-delay-tasks

# (Continue for remaining packages...)
```

**Version state over time:**

```
Week 1 (sc-git-worktree 0.4.1):
  sc-delay-tasks:    0.4.0 → 0.4.0
  sc-git-worktree:   0.4.0 → 0.4.1  ← moved
  sc-manage:      0.4.0 → 0.4.0
  sc-repomix-nuget:  0.4.0 → 0.4.0

Week 2 (sc-delay-tasks 0.5.0):
  sc-delay-tasks:    0.4.0 → 0.5.0  ← moved
  sc-git-worktree:   0.4.1 → 0.4.1
  sc-manage:      0.4.0 → 0.4.0
  sc-repomix-nuget:  0.4.0 → 0.4.0

Week 3 (sc-manage 0.5.0):
  sc-delay-tasks:    0.5.0 → 0.5.0
  sc-git-worktree:   0.4.1 → 0.4.1
  sc-manage:      0.4.0 → 0.5.0  ← moved
  sc-repomix-nuget:  0.4.0 → 0.4.0

Week 4 (sc-repomix-nuget 0.5.0):
  sc-delay-tasks:    0.5.0 → 0.5.0
  sc-git-worktree:   0.4.1 → 0.4.1
  sc-manage:      0.5.0 → 0.5.0
  sc-repomix-nuget:  0.4.0 → 0.5.0  ← moved
```

### Scenario 4: Emergency Hotfix for All Packages

**Situation:** Critical security vulnerability discovered affecting all packages

**Release Plan:**
- All packages move to patch version immediately
- Skip normal release processes
- Communicate urgently to users

**Execution Steps:**

```bash
# Step 1: Create hotfix branch (no feature branch delay)
git checkout main
git pull
git checkout -b hotfix/security-patch

# Step 2: Update all CHANGELOGs with security notice
for pkg in packages/*/; do
  vim "$pkg/CHANGELOG.md"
  # Add section:
  # ## [X.Y.1] - 2025-12-15 (URGENT SECURITY PATCH)
  # ### Security
  # - Critical: Fixed XYZ vulnerability
done

# Step 3: Determine current versions and patch
# Current: 0.5.0, 0.4.1, 0.5.0, 0.5.0
# New:     0.5.1, 0.4.2, 0.5.1, 0.5.1

# Step 4: Update each package individually
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.1
python3 scripts/sync-versions.py --package sc-git-worktree --version 0.4.2
python3 scripts/sync-versions.py --package sc-manage --version 0.5.1
python3 scripts/sync-versions.py --package sc-repomix-nuget --version 0.5.1

# Step 5: Verify all changes
./scripts/audit-versions.py

# Step 6: Commit with clear security message
git add -A
git commit -m "SECURITY: Critical patch for all packages

URGENT: All users must upgrade immediately

Security fixes:
- sc-delay-tasks v0.5.1: Fixed XYZ vulnerability
- sc-git-worktree v0.4.2: Fixed XYZ vulnerability
- sc-manage v0.5.1: Fixed XYZ vulnerability
- sc-repomix-nuget v0.5.1: Fixed XYZ vulnerability

CVE: CVE-2025-XXXXX
Severity: Critical

No feature changes. Security patch only."

# Step 7: Push and create high-priority PR
git push origin hotfix/security-patch
gh pr create --title "SECURITY: Critical patch for all packages" \
  --body "URGENT SECURITY PATCH

All packages need immediate update for critical vulnerability.
See commit message for details."

# Step 8: Expedited review and merge
# (After approval)
git checkout main
git merge hotfix/security-patch
git tag -a v0.5.1-security-patch -m "Security patch for all packages"
git push origin main v0.5.1-security-patch

# Step 9: Announce to users
# Create GitHub Release with security notice
# Post security advisory to security contacts
# Update documentation with urgency notice
```

---

## 6. Version Compatibility

### Marketplace and Package Compatibility

**Rule:** Any marketplace version is compatible with any package version currently in the registry.

```
Marketplace v1.0.0 can install:
  ✓ sc-delay-tasks v0.5.0
  ✓ sc-delay-tasks v0.5.1
  ✓ sc-git-worktree v0.4.1
  ✓ sc-git-worktree v0.5.0
  ✓ Any package in registry
```

**Exception:** Breaking changes must be documented:

```yaml
# In registry.json - if breaking change exists
"breaking_changes": [
  {
    "version": "1.0.0",
    "description": "New manifest schema requires 'tier' field",
    "required_marketplace_version": "1.0.0"
  }
]
```

### Inter-Package Dependencies

Document dependencies between packages clearly:

```yaml
# In manifest.yaml for dependent packages
dependencies:
  - name: sc-git-worktree
    version: ">=0.4.0"
    required_for: "Worktree context features"
```

**Verification:**

```bash
# Check for unmet dependencies after installation
./scripts/audit-versions.py
# Will detect if required packages are missing or outdated
```

### Artifact Compatibility

**Commands and Skills:** Always use package version of parent

```
If: packages/sc-delay-tasks/manifest.yaml version: 0.5.0
Then: packages/sc-delay-tasks/commands/delay.md must have version: 0.5.0
```

**Agents:** Can use either package version or marketplace version

```
If package version is different from marketplace version:
  - Global agents (.claude/agents/*) → use marketplace version
  - Package agents (packages/*/agents/*) → use package version
```

### Breaking Change Documentation

When introducing breaking changes, document clearly:

**In CHANGELOG.md:**
```markdown
## [1.0.0] - 2025-12-15

### BREAKING CHANGES
- Removed `legacy-delay` agent (deprecated in 0.5.0)
  - **Migration:** Use `delay-poll` agent instead
  - **Impact:** Existing scripts using legacy-delay will fail
  - **Required Action:** Update scripts before upgrading
```

**In manifest.yaml:**
```yaml
breaking_changes:
  - version: "1.0.0"
    description: "Removed legacy-delay agent"
    migration: "Use delay-poll agent instead"
    minimum_marketplace_version: "1.0.0"
```

### Backward Compatibility Verification

Before releasing, verify backward compatibility:

```bash
# Test 1: Can old commands still be used?
/delay --once --minutes 5 --action "echo done"
# Should work if no breaking changes

# Test 2: Do new versions install alongside old?
# (for development/testing only)

# Test 3: Can scripts written for v0.4.0 run on v0.5.0?
# Run legacy scripts and verify they work

# Test 4: Does new version break existing workflows?
# Run integration tests with real-world scenarios
```

### Feature Parity Checks

If releasing multiple packages, ensure feature consistency:

```bash
# After releases, verify:
# - All packages have compatible versions available
# - No package left behind in beta while others in production
# - Version compatibility matrix updated

# Example matrix for v1.0.0 release:
```

**Version Compatibility Matrix** (before and after release):

```
BEFORE v1.0.0 release:
  sc-delay-tasks:    0.4.0 (beta)
  sc-git-worktree:   0.4.0 (beta)
  sc-manage:      0.4.0 (beta)
  sc-repomix-nuget:  0.4.0 (beta)
  Marketplace:    0.4.0 (beta)

AFTER v1.0.0 release:
  sc-delay-tasks:    1.0.0 (stable) ← aligned
  sc-git-worktree:   1.0.0 (stable) ← aligned
  sc-manage:      1.0.0 (stable) ← aligned
  sc-repomix-nuget:  1.0.0 (stable) ← aligned
  Marketplace:    1.0.0 (stable) ← aligned
```

---

## 7. Documentation Updates

### Updating CHANGELOG.md

**Location:** `packages/<package-name>/CHANGELOG.md`

**Format:** Keep a Changelog standard (https://keepachangelog.com/)

**Steps for release:**

```markdown
# BEFORE (during development)
## [Unreleased]
### Added
- New exponential backoff agent
- Conditional delay support

### Fixed
- Timeout issue in delay-poll

## [0.4.0] - 2025-12-02
### Added
- Initial sc-delay-tasks package
...

# AFTER (ready for release)
## [Unreleased]
# (empty for now - will be filled in next development cycle)

## [0.5.0] - 2025-12-15          ← Date of release
### Added
- New exponential backoff agent
- Conditional delay support

### Fixed
- Timeout issue in delay-poll

## [0.4.0] - 2025-12-02
### Added
- Initial sc-delay-tasks package
...
```

**Command to update CHANGELOG:**

```bash
# Edit the file
vim packages/sc-delay-tasks/CHANGELOG.md

# Verify format is correct
grep -A 5 "## \[0.5.0\]" packages/sc-delay-tasks/CHANGELOG.md

# Expected output:
# ## [0.5.0] - 2025-12-15
# ### Added
# - New exponential backoff agent
# - Conditional delay support
```

### Updating version.yaml

**Location:** `/version.yaml` (marketplace)

**When to update:** Only when releasing marketplace infrastructure updates

**Example:**

```yaml
# Before
version: "0.4.0"

# After
version: "1.0.0"
```

**Verification:**

```bash
grep "^version:" version.yaml
# Output: version: "1.0.0"
```

### Updating manifest.yaml

**Location:** `packages/<package-name>/manifest.yaml`

**Updated by:** `sync-versions.py` script (do not edit manually)

**Manual verification:**

```bash
# Check manifest version matches package release
cat packages/sc-delay-tasks/manifest.yaml | grep "^version:"
# Output: version: 0.5.0
```

### Updating Artifact Frontmatter

**Files affected:**
- `packages/<package>/commands/*.md`
- `packages/<package>/skills/*/SKILL.md`
- `packages/<package>/agents/*.md`

**Updated by:** `sync-versions.py` script (do not edit manually)

**Manual verification:**

```bash
# Spot-check commands
grep "^version:" packages/sc-delay-tasks/commands/delay.md
# Output: version: 0.5.0

# Spot-check skills
grep "^version:" packages/sc-delay-tasks/skills/delaying-tasks/SKILL.md
# Output: version: 0.5.0

# Spot-check agents
grep "^version:" packages/sc-delay-tasks/agents/delay-once.md
# Output: version: 0.5.0
```

### Updating registry.json

**Location:** `docs/registries/nuget/registry.json`

**When to update:** After every package release

**Automated approach (if available):**

```bash
# Regenerate registry from source files
python3 scripts/generate-registry.py

# Manual approach:
# Edit docs/registries/nuget/registry.json
```

**Fields to update:**

```json
{
  "version": "2.0.0",
  "generated": "2025-12-15T10:30:00Z",
  "marketplace": {
    "version": "0.5.0"    ← if marketplace version changed
  },
  "packages": {
    "sc-delay-tasks": {
      "version": "0.5.0", ← update if package released
      "lastUpdated": "2025-12-15",
      ...
    },
    ...
  }
}
```

**Verification:**

```bash
# Validate JSON syntax
python3 -m json.tool docs/registries/nuget/registry.json > /dev/null \
  && echo "✓ Valid JSON" || echo "✗ Invalid JSON"

# Check marketplace version
python3 -c "
import json
with open('docs/registries/nuget/registry.json') as f:
    print('Marketplace:', json.load(f)['marketplace']['version'])
"
```

### Updating version-compatibility-matrix.md

**Location:** `docs/version-compatibility-matrix.md`

**When to update:** After every marketplace or package release

**Quick Reference table update:**

```markdown
# BEFORE
### Current Marketplace Status

| Component | Version | Status | Support Level |
|-----------|---------|--------|----------------|
| **Marketplace** | 0.4.0 | Beta | Active Development |
| **All Packages** | 0.4.0 | Beta | Active Development |

# AFTER
### Current Marketplace Status

| Component | Version | Status | Support Level |
|-----------|---------|--------|----------------|
| **Marketplace** | 0.5.0 | Beta | Active Development |
| **All Packages** | 0.5.0 | Beta | Active Development |
```

**Individual package updates:**

```markdown
# BEFORE
| Package | Tier | Current Version | Runtime Requirements |
|---------|------|-----------------|----------------------|
| `sc-delay-tasks` | 0 | 0.4.0 | None |

# AFTER
| Package | Tier | Current Version | Runtime Requirements |
|---------|------|-----------------|----------------------|
| `sc-delay-tasks` | 0 | 0.5.0 | None |
```

**Script to help find and update:**

```bash
# Find all version references
grep -n "0.4.0\|0\.4\.0" docs/version-compatibility-matrix.md

# Update all at once (use with caution - verify before applying)
sed -i '' 's/0\.4\.0/0.5.0/g' docs/version-compatibility-matrix.md

# Verify changes
git diff docs/version-compatibility-matrix.md
```

---

## 8. Release Branching Strategy

### Branch Naming Conventions

**Main branches:**
- `main` - Production-ready code, all releases go here
- `develop` - Development branch (optional), where features integrate

**Feature branches:**
- `feature/<package>-<feature-name>` - New feature development
- Example: `feature/sc-delay-tasks-exponential-backoff`

**Release branches:**
- `release/v<VERSION>` - Preparation for version release
- Example: `release/v0.5.0`

**Hotfix branches:**
- `hotfix/<issue>` - Emergency fixes to production
- Example: `hotfix/security-vulnerability`

### Git Workflow Diagrams

**Standard Feature Release Flow:**

```
main (v0.4.0)
  ↓
feature/sc-delay-tasks-v0.5
  ├─ Update CHANGELOG.md → v0.5.0
  ├─ Add new agents (3 commits)
  ├─ Bug fixes (2 commits)
  └─ run sync-versions.py
     └─ Ready for PR
        ↓
    (PR Review & CI/CD checks)
        ↓
    (Merge to main)
        ↓
main (v0.5.0) ← Tagged with v0.5.0-sc-delay-tasks
```

**Release Branch Flow (Coordinated):**

```
main (v0.4.0 - marketplace & all packages)
  ↓
release/v1.0.0
  ├─ Update all CHANGELOGs → v1.0.0
  ├─ run sync-versions.py --all --version 1.0.0
  ├─ run sync-versions.py --marketplace --version 1.0.0
  ├─ Update docs/version-compatibility-matrix.md
  ├─ Update registry.json
  └─ Ready for PR
     ↓
 (PR Review & CI/CD checks)
     ↓
 (Merge to main)
     ↓
main (v1.0.0 - marketplace & all packages)
  └─ Tagged with v1.0.0
```

**Hotfix Flow:**

```
main (v1.0.0 - stable)
  ↓
hotfix/security-patch
  ├─ Update CHANGELOGs → v1.0.1 for each affected package
  ├─ run sync-versions.py --package <name> --version X.Y.1
  └─ Security fix commits
     ↓
 (Expedited PR Review)
     ↓
 (Merge to main)
     ↓
main (v1.0.1 - all packages)
  └─ Tagged with v1.0.1-security-patch
```

### Branch Commands

**Create and work on feature branch:**

```bash
# Start new feature branch
git checkout main
git pull
git checkout -b feature/sc-delay-tasks-v0.5

# Make changes, commit normally
git add packages/sc-delay-tasks/CHANGELOG.md
git commit -m "docs: prepare CHANGELOG for v0.5.0 release"

git add packages/sc-delay-tasks/
git commit -m "feat: add exponential backoff agent"

# Update versions before push
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.0
git add packages/sc-delay-tasks/
git commit -m "chore: bump sc-delay-tasks to v0.5.0"

# Push to remote
git push origin feature/sc-delay-tasks-v0.5
```

**Create release branch:**

```bash
# Start release branch for coordinated release
git checkout main
git pull
git checkout -b release/v1.0.0

# Update all CHANGELOGs
# Then sync versions...
python3 scripts/sync-versions.py --all --version 1.0.0
python3 scripts/sync-versions.py --marketplace --version 1.0.0

# Commit
git add -A
git commit -m "chore(release): prepare v1.0.0"
git push origin release/v1.0.0
```

**Create and merge hotfix:**

```bash
# Emergency hotfix
git checkout main
git pull
git checkout -b hotfix/security-patch

# Make fixes and commit
# Update versions...
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.1
# etc for other packages

git add -A
git commit -m "SECURITY: patch all packages for CVE-2025-XXXXX"
git push origin hotfix/security-patch

# After expedited review:
git checkout main
git merge hotfix/security-patch
git tag -a v0.5.1-security-patch -m "Security patch"
git push origin main --follow-tags
```

### Pull Request Process

**Before creating PR:**
- [ ] All commits follow commit message conventions
- [ ] CHANGELOG.md updated with release notes
- [ ] Version synced via `sync-versions.py`
- [ ] Audit passes: `./scripts/audit-versions.py`
- [ ] All tests pass locally

**PR description template:**

```markdown
## Release: sc-delay-tasks v0.5.0

### Changes
- Added exponential backoff agent
- Added conditional delay support
- Fixed timeout issue in delay-poll

### Verification
- [x] audit-versions.py passes
- [x] compare-versions.sh shows consistency
- [x] CHANGELOG.md updated
- [x] All artifacts updated via sync-versions.py
- [x] Local testing complete

### Dependency Notes
- Requires: sc-git-worktree >= 0.4.0
- Marketplace: >= 0.4.0

### Breaking Changes
- None

### Release Date
- Target: 2025-12-15
```

**Merge strategy:**

```bash
# Option 1: Squash merge (clean history)
git merge --squash feature/sc-delay-tasks-v0.5

# Option 2: Merge commit (preserve history)
git merge --no-ff feature/sc-delay-tasks-v0.5

# Option 3: Rebase merge (linear history)
git merge --rebase feature/sc-delay-tasks-v0.5
```

---

## 9. Common Scenarios with Examples

### Example 1: Release sc-delay-tasks v0.5.0 (New Features)

**Scenario:** Adding 2 new agents and 3 bug fixes.

**Complete Command Sequence:**

```bash
# 1. Start on fresh main
git checkout main
git pull

# 2. Create feature branch
git checkout -b feature/sc-delay-tasks-v0.5

# 3. Update CHANGELOG.md
vim packages/sc-delay-tasks/CHANGELOG.md
# Change:
#   ## [Unreleased]
# To:
#   ## [0.5.0] - 2025-12-15
#   ### Added
#   - New exponential backoff agent
#   - New conditional delay agent
#   ### Fixed
#   - Timeout issue in delay-poll
#   - Memory leak in long-running delays
#   - Documentation typos
#   ## [Unreleased]  ← new empty section

git add packages/sc-delay-tasks/CHANGELOG.md
git commit -m "docs: prepare CHANGELOG for v0.5.0 release"

# 4. Add new features
# (Actually add new agent files - assume done)
vim packages/sc-delay-tasks/agents/delay-exponential-backoff.md
vim packages/sc-delay-tasks/agents/delay-conditional.md
git add packages/sc-delay-tasks/agents/
git commit -m "feat: add exponential backoff and conditional delay agents"

# 5. Fix bugs
vim packages/sc-delay-tasks/agents/delay-poll.md
git add packages/sc-delay-tasks/agents/
git commit -m "fix: resolve timeout issue in delay-poll"

# 6. Verify current state
./scripts/compare-versions.sh --verbose

# Output should show:
# Package: sc-delay-tasks (manifest: 0.4.0)
#   ✓ command/delay: 0.4.0
#   ✓ skill/delaying-tasks: 0.4.0
#   ... (all still 0.4.0)

# 7. Sync versions to 0.5.0
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.0

# 8. Verify sync worked
./scripts/audit-versions.py
# Should show all sc-delay-tasks artifacts at 0.5.0

# 9. Review what changed
git status
# Should show modified files in packages/sc-delay-tasks/

# 10. Commit the version sync
git add packages/sc-delay-tasks/
git commit -m "chore: bump sc-delay-tasks to v0.5.0"

# 11. Push to remote
git push origin feature/sc-delay-tasks-v0.5

# 12. Create PR
gh pr create \
  --title "Release sc-delay-tasks v0.5.0 - New agents and bug fixes" \
  --body "## Summary

Release new features and bug fixes for sc-delay-tasks.

## Changes
- Added exponential backoff retry agent
- Added conditional delay agent
- Fixed timeout issue in delay-poll
- Fixed memory leak in long-running delays

## Verification
- audit-versions.py: PASSED
- compare-versions.sh: PASSED
- Manual testing: PASSED

## Compatibility
- Backward compatible: YES
- Breaking changes: NONE
- Requires: Marketplace >= 0.4.0"

# 13. After PR approval and CI passes, merge
git checkout main
git pull
git merge --no-ff feature/sc-delay-tasks-v0.5

# 14. Create tag
git tag -a v0.5.0-sc-delay-tasks -m "sc-delay-tasks v0.5.0 release

New agents:
- Exponential backoff retry
- Conditional delay

Bug fixes:
- Timeout handling in delay-poll
- Memory leak in long-running delays"

# 15. Push changes and tags
git push origin main
git push origin v0.5.0-sc-delay-tasks

# 16. Update registry (manual - or automated if available)
vim docs/registries/nuget/registry.json
# Change sc-delay-tasks version from 0.4.0 to 0.5.0
# Update lastUpdated to current date

git add docs/registries/nuget/registry.json
git commit -m "chore(registry): update sc-delay-tasks to v0.5.0"
git push origin main

# 17. Verify final state
./scripts/compare-versions.sh

# Expected output:
# Package: sc-delay-tasks (manifest: 0.5.0)  ← updated!
# All versions consistent!
```

### Example 2: Patch sc-git-worktree v0.4.1 (Bug Fix)

**Scenario:** Critical bug fix only, no new features.

**Complete Command Sequence:**

```bash
# 1. Start from main with latest code
git checkout main
git pull

# 2. Create hotfix branch (even though not emergency, use for consistency)
git checkout -b feature/sc-git-worktree-v0.4.1

# 3. Update CHANGELOG.md
vim packages/sc-git-worktree/CHANGELOG.md
# Change:
#   ## [Unreleased]
# To:
#   ## [0.4.1] - 2025-12-15
#   ### Fixed
#   - Incorrect worktree path resolution on Windows
#   - Status check timeout in cleanup operation

git add packages/sc-git-worktree/CHANGELOG.md
git commit -m "docs: prepare CHANGELOG for v0.4.1 release"

# 4. Make bug fix
vim packages/sc-git-worktree/scripts/worktree-cleanup.sh
# Fix: Update path resolution logic
git add packages/sc-git-worktree/scripts/
git commit -m "fix: correct worktree path resolution on Windows"

vim packages/sc-git-worktree/agents/worktree-cleanup.md
# Fix: Add timeout parameter to status check
git add packages/sc-git-worktree/agents/
git commit -m "fix: add configurable timeout to status check in cleanup"

# 5. Sync versions to 0.4.1
python3 scripts/sync-versions.py --package sc-git-worktree --version 0.4.1

# 6. Verify
./scripts/audit-versions.py

# 7. Commit version sync
git add packages/sc-git-worktree/
git commit -m "chore: bump sc-git-worktree to v0.4.1"

# 8. Push
git push origin feature/sc-git-worktree-v0.4.1

# 9. Create PR (note: patch release = faster review)
gh pr create \
  --title "Patch sc-git-worktree v0.4.1 - Bug fixes" \
  --body "## Summary

Patch release with critical bug fixes.

## Changes
- Fixed incorrect worktree path resolution on Windows
- Added configurable timeout to status check in cleanup

## Verification
- audit-versions.py: PASSED
- Tested on Windows and Linux: PASSED
- Backward compatible: YES

## Impact
- PATCH release: 0.4.0 → 0.4.1
- Breaking changes: NONE
- Users should upgrade to fix Windows path issue"

# 10. After review, merge
git checkout main
git merge --ff-only feature/sc-git-worktree-v0.4.1

# 11. Tag release
git tag -a v0.4.1-sc-git-worktree -m "sc-git-worktree v0.4.1

Bug fixes:
- Windows path resolution
- Timeout handling in cleanup"

# 12. Push
git push origin main
git push origin v0.4.1-sc-git-worktree

# 13. Update registry
vim docs/registries/nuget/registry.json
# Change sc-git-worktree version from 0.4.0 to 0.4.1

git add docs/registries/nuget/registry.json
git commit -m "chore(registry): update sc-git-worktree to v0.4.1"
git push origin main
```

### Example 3: Release Marketplace v1.0.0 (Production)

**Scenario:** Stable production release of entire ecosystem.

**Complete Command Sequence:**

```bash
# 1. Ensure main branch is clean and up to date
git checkout main
git pull
git status  # Should show nothing to commit

# 2. Create release branch
git checkout -b release/v1.0.0

# 3. Update all CHANGELOGs to version 1.0.0
for pkg in packages/{sc-delay-tasks,sc-git-worktree,sc-manage,sc-repomix-nuget}; do
  vim "$pkg/CHANGELOG.md"
  # Change all [Unreleased] → [1.0.0] - 2025-12-15
  # Add status: "Production Release - Stable"
done

git add packages/*/CHANGELOG.md
git commit -m "docs: prepare CHANGELOGs for v1.0.0 production release"

# 4. Update version.yaml for marketplace
grep "^version:" version.yaml
# Current: version: "0.4.0"

# 5. Sync all packages to 1.0.0
python3 scripts/sync-versions.py --all --version 1.0.0

# 6. Sync marketplace to 1.0.0
python3 scripts/sync-versions.py --marketplace --version 1.0.0

# 7. Verify all versions consistent
./scripts/audit-versions.py

# 8. Check detailed version comparison
./scripts/compare-versions.sh --verbose

# 9. Update version compatibility matrix
vim docs/version-compatibility-matrix.md
# Update all references from 0.4.0 to 1.0.0
# Mark all packages as "Stable" instead of "Beta"

git add docs/version-compatibility-matrix.md
git commit -m "docs: update version compatibility matrix for v1.0.0"

# 10. Update registry
vim docs/registries/nuget/registry.json
# Change marketplace.version: "1.0.0"
# Change all package versions to "1.0.0"
# Change status to "stable" for each
# Update lastUpdated timestamps
# Update generated timestamp

git add docs/registries/nuget/registry.json
git commit -m "chore(registry): update all versions to v1.0.0 production release"

# 11. Review all changes
git log --oneline -10
# Should show:
# chore(registry): update all versions to v1.0.0 production release
# docs: update version compatibility matrix for v1.0.0
# chore: bump all packages to v1.0.0
# docs: prepare CHANGELOGs for v1.0.0 production release

# 12. Push release branch
git push origin release/v1.0.0

# 13. Create comprehensive PR
gh pr create \
  --title "Release v1.0.0 - Production Stable Release" \
  --body "## Release Notes

Production release of Synaptic Canvas v1.0.0.

## Version Changes
- Marketplace: 0.4.0 → 1.0.0
- sc-delay-tasks: 0.4.0 → 1.0.0
- sc-git-worktree: 0.4.0 → 1.0.0
- sc-manage: 0.4.0 → 1.0.0
- sc-repomix-nuget: 0.4.0 → 1.0.0

## Key Achievements
- [x] All packages feature-complete
- [x] Comprehensive test coverage
- [x] Documentation complete
- [x] No known critical issues
- [x] Production-ready status

## Features
### sc-delay-tasks
- Exponential backoff agent
- Conditional delay support
- Improved timeout handling

### sc-git-worktree
- Full worktree lifecycle management
- Cross-platform path resolution
- Enhanced status tracking

### sc-manage
- Package installation and management
- Dependency resolution
- Version compatibility checking

### sc-repomix-nuget
- NuGet package generation
- Automated registry updates
- Version synchronization

## Verification
- [x] audit-versions.py: PASSED
- [x] compare-versions.sh: PASSED
- [x] Full regression testing: PASSED
- [x] Production readiness checklist: PASSED

## Breaking Changes
- None from 0.4.0 to 1.0.0

## Migration Guide
- Users on 0.4.0 can upgrade directly
- No special migration steps required
- All 0.4.0 scripts remain compatible

## Support
- This release enters long-term support (LTS)
- Critical bug fixes will be provided
- Feature requests for v1.1.0 being collected"

# 14. After review and CI passing, merge
git checkout main
git pull  # Get any last-minute changes
git merge --no-ff release/v1.0.0

# 15. Create release tag
git tag -a v1.0.0 -m "Production Release v1.0.0 - Stable

All packages upgraded to production-ready status.

Included:
- sc-delay-tasks v1.0.0
- sc-git-worktree v1.0.0
- sc-manage v1.0.0
- sc-repomix-nuget v1.0.0
- Marketplace v1.0.0

This release enters long-term support."

# 16. Push main and tags
git push origin main
git push origin v1.0.0

# 17. Clean up release branch
git branch -d release/v1.0.0
git push origin --delete release/v1.0.0

# 18. Verify final state
./scripts/compare-versions.sh

# Expected:
# === Synaptic Canvas Version Comparison ===
# Marketplace Version: 1.0.0
# Package: sc-delay-tasks (manifest: 1.0.0)
# Package: sc-git-worktree (manifest: 1.0.0)
# Package: sc-repomix-nuget (manifest: 1.0.0)
# Package: sc-manage (manifest: 1.0.0)
# All versions consistent!
```

### Example 4: Emergency Hotfix for All Packages

**Scenario:** Critical security vulnerability discovered, all packages need immediate patch.

**Complete Command Sequence:**

```bash
# 1. Immediate action - create hotfix branch
git checkout main
git pull
git checkout -b hotfix/CVE-2025-XXXXX

# 2. Update all CHANGELOGs with security notice
# Current versions: sc-delay-tasks 0.5.0, sc-git-worktree 0.4.1,
#                  sc-manage 0.5.0, sc-repomix-nuget 0.5.0
# New versions:    all get patch bump (0.5.1, 0.4.2, etc.)

vim packages/sc-delay-tasks/CHANGELOG.md
# Add section:
# ## [0.5.1] - 2025-12-10 (URGENT SECURITY PATCH)
# ### Security
# - CRITICAL: Fixed XYZ vulnerability that allows arbitrary code execution

vim packages/sc-git-worktree/CHANGELOG.md
# Add section:
# ## [0.4.2] - 2025-12-10 (URGENT SECURITY PATCH)
# ### Security
# - CRITICAL: Fixed XYZ vulnerability that allows arbitrary code execution

vim packages/sc-manage/CHANGELOG.md
# Add section:
# ## [0.5.1] - 2025-12-10 (URGENT SECURITY PATCH)
# ### Security
# - CRITICAL: Fixed XYZ vulnerability that allows arbitrary code execution

vim packages/sc-repomix-nuget/CHANGELOG.md
# Add section:
# ## [0.5.1] - 2025-12-10 (URGENT SECURITY PATCH)
# ### Security
# - CRITICAL: Fixed XYZ vulnerability that allows arbitrary code execution

git add packages/*/CHANGELOG.md
git commit -m "docs: SECURITY UPDATE - prepare for emergency patches"

# 3. Add security fixes to each package
vim packages/sc-delay-tasks/commands/delay.md
# Add security check fix
git add packages/sc-delay-tasks/commands/
git commit -m "SECURITY: patch sc-delay-tasks CVE-2025-XXXXX"

vim packages/sc-git-worktree/scripts/worktree-git.py
# Add security check fix
git add packages/sc-git-worktree/scripts/
git commit -m "SECURITY: patch sc-git-worktree CVE-2025-XXXXX"

vim packages/sc-manage/src/manager.py
# Add security check fix
git add packages/sc-manage/src/
git commit -m "SECURITY: patch sc-manage CVE-2025-XXXXX"

vim packages/sc-repomix-nuget/src/generator.py
# Add security check fix
git add packages/sc-repomix-nuget/src/
git commit -m "SECURITY: patch sc-repomix-nuget CVE-2025-XXXXX"

# 4. Update versions for all affected packages
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.1
python3 scripts/sync-versions.py --package sc-git-worktree --version 0.4.2
python3 scripts/sync-versions.py --package sc-manage --version 0.5.1
python3 scripts/sync-versions.py --package sc-repomix-nuget --version 0.5.1

# 5. Verify all changes
./scripts/audit-versions.py

# 6. Review what changed
git status
./scripts/compare-versions.sh --verbose

# 7. Single comprehensive commit for all version changes
git add packages/*/
git commit -m "chore: bump security patch versions for CVE-2025-XXXXX

- sc-delay-tasks: 0.5.0 → 0.5.1
- sc-git-worktree: 0.4.1 → 0.4.2
- sc-manage: 0.5.0 → 0.5.1
- sc-repomix-nuget: 0.5.0 → 0.5.1"

# 8. Push immediately
git push origin hotfix/CVE-2025-XXXXX

# 9. Create URGENT PR
gh pr create \
  --title "SECURITY: Emergency patch for CVE-2025-XXXXX" \
  --body "## URGENT SECURITY PATCH

All packages contain a critical vulnerability that allows arbitrary code execution.

### Vulnerability Details
- CVE: CVE-2025-XXXXX
- Severity: CRITICAL
- CVSS Score: 9.8
- Description: [Technical details]

### Affected Packages
- sc-delay-tasks: 0.5.0 → 0.5.1
- sc-git-worktree: 0.4.1 → 0.4.2
- sc-manage: 0.5.0 → 0.5.1
- sc-repomix-nuget: 0.5.0 → 0.5.1

### Action Required
**ALL USERS MUST UPDATE IMMEDIATELY**

### Workaround
Until updated, [describe temporary workaround if available]

### Timeline
- Discovered: 2025-12-10
- Fixed: This patch
- Tested: YES
- Ready for production: YES"

# 10. Expedited review (get team lead approval immediately)
# Notify: maintainers, security team, users

# 11. After approval (usually within 1 hour), merge
git checkout main
git merge --no-ff hotfix/CVE-2025-XXXXX

# 12. Create urgent release tag
git tag -a v-SECURITY-PATCH-2025-12-10 \
  -m "URGENT SECURITY PATCH for CVE-2025-XXXXX

All packages patched for critical vulnerability.

Versions:
- sc-delay-tasks v0.5.1
- sc-git-worktree v0.4.2
- sc-manage v0.5.1
- sc-repomix-nuget v0.5.1

Users must upgrade immediately."

# 13. Push main and tag
git push origin main
git push origin v-SECURITY-PATCH-2025-12-10

# 14. Update registry immediately
vim docs/registries/nuget/registry.json
# Update ALL package versions to patch versions

git add docs/registries/nuget/registry.json
git commit -m "chore(registry): URGENT - update all packages for security patch"
git push origin main

# 15. Notify users
# Send security advisory email
# Post to GitHub security advisories
# Update status page
# Notify package managers

# 16. Verify deployment
./scripts/compare-versions.sh

# Expected:
# Package: sc-delay-tasks (manifest: 0.5.1)  ← patched
# Package: sc-git-worktree (manifest: 0.4.2) ← patched
# Package: sc-manage (manifest: 0.5.1)    ← patched
# Package: sc-repomix-nuget (manifest: 0.5.1) ← patched
# All versions consistent!

# 17. Clean up hotfix branch
git branch -d hotfix/CVE-2025-XXXXX
git push origin --delete hotfix/CVE-2025-XXXXX
```

---

## 10. Automation & CI/CD

### CI/CD Version Validation Workflow

**File:** `.github/workflows/version-audit.yml`

**Triggered on:**
- Push to `main` or `develop`
- Pull requests to `main` or `develop`

**Jobs:**

1. **audit-versions** - Comprehensive consistency check
2. **validate-manifests** - YAML format validation
3. **changelog-check** - CHANGELOG file verification

**Validation Steps:**

```yaml
# Audit versions consistency
- ./scripts/audit-versions.py --verbose

# Compare versions across packages
- ./scripts/compare-versions.sh --by-package

# Validate YAML format
- python3 -c "import yaml; yaml.safe_load(open('packages/*/manifest.yaml'))"

# Check for CHANGELOGs
- [ -f packages/*/CHANGELOG.md ] || echo "Warning: Missing CHANGELOG"
```

**Success Criteria:**
- [ ] `audit-versions.py` exits with code 0 (all checks passed)
- [ ] No version mismatches detected
- [ ] All manifests valid YAML
- [ ] All packages have CHANGELOG.md

**Failure Handling:**

If CI/CD fails:

```bash
# CI fails because version mismatch detected
# Fix locally first:
./scripts/audit-versions.py  # See which check failed

# Fix the issue
vim packages/sc-delay-tasks/commands/delay.md
# Change version to match manifest

# Re-run audit
./scripts/audit-versions.py

# Commit fix
git add -A
git commit -m "fix: correct version mismatch in sc-delay-tasks"
git push origin feature/branch

# CI should now pass
```

### Pre-Commit Hooks (Optional)

Set up local git hooks to catch version issues before pushing:

**File:** `.git/hooks/pre-commit`

```bash
#!/bin/bash
# Pre-commit hook: Verify versions are consistent

echo "Running version audit..."
./scripts/audit-versions.py

if [ $? -ne 0 ]; then
  echo "❌ Version audit failed. Fix issues before committing."
  exit 1
fi

echo "✅ Versions are consistent"
exit 0
```

**Install:**

```bash
# Make hook executable
chmod +x .git/hooks/pre-commit

# Or create if doesn't exist
mkdir -p .git/hooks
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
./scripts/audit-versions.py || exit 1
EOF
chmod +x .git/hooks/pre-commit
```

### Automated Version Sync (Future)

Potential future enhancements:

```bash
# Auto-increment patch version
python3 scripts/sync-versions.py --package sc-delay-tasks --auto-patch

# Auto-increment minor version
python3 scripts/sync-versions.py --package sc-delay-tasks --auto-minor

# Auto-increment major version
python3 scripts/sync-versions.py --package sc-delay-tasks --auto-major

# Generate CHANGELOG section
python3 scripts/generate-changelog.py --package sc-delay-tasks --version 0.5.0
```

### PR Validation for Version Changes

**GitHub PR validation rules:**

```yaml
# Branch protection rules for main
- Require status checks to pass before merging
  - Check: "Version Audit"
  - Check: "Validate Manifests"
  - Check: "Check for CHANGELOGs"

- Dismiss stale pull request approvals
- Require branches to be up to date before merging

# Additional check: Version must be bumped if code changed
- Require code changes to include version update
```

**PR Template to enforce verification:**

```markdown
# Checklist

- [ ] audit-versions.py passes locally
- [ ] compare-versions.sh shows consistency
- [ ] CHANGELOG.md updated
- [ ] version synced via sync-versions.py
- [ ] CI/CD checks passing
- [ ] At least one maintainer approval

# Version Changes
- [ ] No version change (documentation only)
- [x] PATCH bump (0.4.0 → 0.4.1)
- [ ] MINOR bump (0.4.0 → 0.5.0)
- [ ] MAJOR bump (0.4.0 → 1.0.0)

# Breaking Changes
- [ ] Yes (requires MAJOR bump)
- [x] No (backward compatible)
```

---

## 11. Rollback Procedures

### Scenario: Need to Undo a Released Version

**Situation:** Released version 0.5.0, but discovered critical bug immediately after release

**Steps:**

```bash
# 1. Verify current state
git log --oneline -5
# Should show v0.5.0 tag

# 2. Create hotfix branch from current main
git checkout main
git checkout -b hotfix/revert-v0.5.0

# 3. Revert the release commit
# Find the commit that released v0.5.0
git log --oneline | grep -i "release\|v0.5"
# Example: abc1234 Release v0.5.0

# Revert that commit
git revert abc1234

# 4. This creates new commit with undone changes
git log --oneline -3
# Should show: Revert "Release v0.5.0"

# 5. Update back to 0.4.0
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.4.0

# 6. Update CHANGELOG to document rollback
vim packages/sc-delay-tasks/CHANGELOG.md
# Add section:
# ## [0.4.0-rollback] - 2025-12-15
# ### Note
# - v0.5.0 was yanked due to critical bug
# - Reverted to 0.4.0
# - v0.5.1 will be released after fix

git add packages/sc-delay-tasks/CHANGELOG.md
git commit -m "docs: document rollback from v0.5.0"

# 7. Push and create PR
git push origin hotfix/revert-v0.5.0
gh pr create --title "Rollback sc-delay-tasks from v0.5.0 to v0.4.0"

# 8. After merge, delete v0.5.0 tag
git checkout main
git merge hotfix/revert-v0.5.0
git tag -d v0.5.0-sc-delay-tasks  # Delete local tag
git push origin :v0.5.0-sc-delay-tasks  # Delete remote tag

# 9. (Optional) Yank from registry
vim docs/registries/nuget/registry.json
# Mark v0.5.0 as yanked:
# "versions": {
#   "0.5.0": {
#     "yanked": true,
#     "reason": "Critical bug - use 0.4.0 or wait for 0.5.1"
#   }
# }

git add docs/registries/nuget/registry.json
git commit -m "chore(registry): yank sc-delay-tasks v0.5.0"
git push origin main

# 10. Notify users
# Post notice: "v0.5.0 yanked, use v0.4.0 until fixed"
```

### Scenario: Handling Failed Release

**Situation:** Started release process but encountered issue before merge to main

**Steps:**

```bash
# If issue caught before merge to main:

# 1. Simply delete the branch and start over
git branch -D release/v0.5.0
git push origin --delete release/v0.5.0

# 2. Fix the issues locally
git checkout feature/branch
# Fix whatever caused the issue

# 3. Re-run verification
./scripts/audit-versions.py
./scripts/compare-versions.sh

# 4. Retry the release process from the beginning
```

### Yanking Versions from Registry

Mark a version as "yanked" (deprecated but not deleted):

```json
{
  "packages": {
    "sc-delay-tasks": {
      "version": "0.4.0",
      "versions": {
        "0.4.0": {
          "status": "active"
        },
        "0.5.0": {
          "status": "yanked",
          "yanked_at": "2025-12-15T10:30:00Z",
          "reason": "Critical bug in delay-poll agent",
          "use_instead": "0.4.0 or 0.5.1"
        }
      }
    }
  }
}
```

### Communication Procedures

**When rolling back or yanking:**

1. **Notify immediately**
   ```
   Subject: URGENT: Pulling version X.Y.Z

   We have identified a critical issue in version X.Y.Z.
   Please do not install this version.
   Revert to X.Y.(Z-1) if already installed.
   ```

2. **Post to channels**
   - GitHub Discussions
   - Project announcements
   - Email to active users
   - Status page update

3. **Document in CHANGELOG**
   - Add note about yanked version
   - Link to issue report
   - Direct users to working version

4. **Follow up**
   - Announce when fix is available
   - Provide migration steps
   - Thank users for quick reporting

---

## 12. Best Practices

### Version Numbering Dos and Don'ts

**DO:**
- ✅ Use semantic versioning strictly (X.Y.Z format)
- ✅ Bump versions only when releasing
- ✅ Use pre-release tags for development (alpha, beta, rc)
- ✅ Keep version changes minimal and justified
- ✅ Document why each version was bumped
- ✅ Use consistent version across all artifacts in package

**DON'T:**
- ❌ Use 4-part versions (X.Y.Z.W)
- ❌ Use non-numeric version parts (v0.4.alpha)
- ❌ Skip version numbers (jump 0.4.0 to 0.6.0)
- ❌ Bump versions without releasing
- ❌ Have different versions for same package
- ❌ Use leading zeros (use 0.4.0 not 0.04.0 or 00.4.0)

**Examples:**

```
✅ GOOD               ❌ BAD
0.4.0                0.4.0.0
1.0.0-beta           1.0-beta
1.0.0-rc1            1.0rc1
0.5.0-alpha          alpha-0.5.0
```

### Release Frequency Recommendations

**Optimal release cycle:**

```
PATCH (bug fixes):          Every 1-2 weeks as needed
MINOR (features):           Every 4-6 weeks
MAJOR (stable release):     Every 3-4 months
BREAKING CHANGES:           Major releases only

Beta period:                3-6 months minimum
RC period:                  2-4 weeks minimum
```

**Current Project Status (Beta):**
- Release minor versions frequently (new features)
- Collect patch fixes, release weekly if needed
- Plan major v1.0.0 release for stable phase
- Avoid breaking changes until major release

**Future Status (Stable):**
- More conservative: 1 minor per quarter
- Patch releases as needed for bugs
- Major only for significant platform changes

### Beta to Stable Migration Path

**Phase 1: Beta Development (0.x releases)**
```
0.1.0 → 0.2.0 → 0.3.0 → 0.4.0 → 0.5.0
  ↑        ↑        ↑        ↑        ↑
Early   Early    Stable   Current   Next
Stage   Alpha    Beta     Beta    Planned
```

**Phase 2: Release Candidate**
```
0.5.0 (final beta)
    ↓
0.6.0-rc1 (first RC)
    ↓
0.6.0-rc2 (fixes from rc1)
    ↓
0.6.0 (ready for 1.0)
```

**Phase 3: Production Release**
```
0.6.0 (final beta)
    ↓
1.0.0-rc1 (first release candidate for v1)
    ↓
1.0.0-rc2 (minor fixes)
    ↓
1.0.0 (PRODUCTION STABLE)
```

**Criteria for 1.0.0:**
- [ ] All packages feature-complete for first release
- [ ] Comprehensive documentation
- [ ] Production-ready testing
- [ ] No known critical bugs
- [ ] Backward compatibility established
- [ ] User base testing feedback incorporated

### Long-Term Versioning Strategy

**Year 1 (Current):**
- v0.4.0 - Current beta
- Goal: Reach v0.6.0 with feature stability

**Year 2 (Planned):**
- v1.0.0 - Production release
- v1.1.0, v1.2.0 - Feature releases
- v1.0.x - Patch releases and LTS

**Long-term (3+ years):**
- v2.0.0 - Major platform redesign (if needed)
- v1.x.x - Long-term support line
- Maintain backward compatibility within major version

### Maintenance Windows

**Version support timeline:**

```
0.4.0 (Beta)
├─ Active development: 6 months
├─ Minimal support: Until 1.0.0
└─ Deprecated: N/A

1.0.0 (Stable LTS)
├─ Active development: 2 years
├─ Security fixes only: 2 additional years
├─ End of life: Year 4
└─ Support: 4 years total

1.1.0 (Regular)
├─ Active: 1 year
├─ Security only: 6 months
└─ EOL: 1.5 years

2.0.0 (Next major)
└─ (Planned for year 3+)
```

### Changelog Best Practices

**Keep CHANGELOGs:**
- Up to date with every release
- Organized by change type (Added, Fixed, Changed, Removed, Security, Deprecated)
- Human-readable descriptions
- Links to related issues/PRs when available
- Semantic version compliant

**Example CHANGELOG structure:**

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New feature X

### Fixed
- Bug fix Y

## [0.5.0] - 2025-12-15

### Added
- Exponential backoff agent
- Conditional delay support

### Fixed
- Timeout issue in delay-poll
- Memory leak in long-running delays

### Changed
- Improved error messages for clarity

## [0.4.0] - 2025-12-02

### Added
- Initial release of sc-delay-tasks package
```

### Version Documentation

**Keep these documents updated with each release:**

1. **CHANGELOG.md** - Per-package (auto-updated with releases)
2. **version.yaml** - Marketplace (manual + script)
3. **manifest.yaml** - Per-package (script-updated)
4. **README.md** - Per-package (manual as needed)
5. **docs/version-compatibility-matrix.md** - Central (manual, after releases)
6. **docs/registries/nuget/registry.json** - Central registry (manual or script)
7. **docs/versioning-strategy.md** - Central policy (manual, as policy changes)

---

## Quick Reference

### Most Common Commands

```bash
# Audit versions before release
./scripts/audit-versions.py

# Compare versions across packages
./scripts/compare-versions.sh --verbose

# Bump single package
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.0

# Bump marketplace
python3 scripts/sync-versions.py --marketplace --version 1.0.0

# Bump all packages
python3 scripts/sync-versions.py --all --version 1.0.0 --commit

# Verify everything
./scripts/audit-versions.py && echo "✅ Ready to release"
```

### Version Bump Decision Tree

```
Is this a breaking change?
├─ YES → MAJOR bump (e.g., 0.4.0 → 1.0.0)
└─ NO → Continue

Are there new features?
├─ YES → MINOR bump (e.g., 0.4.0 → 0.5.0)
└─ NO → Continue

Are there bug fixes?
├─ YES → PATCH bump (e.g., 0.4.0 → 0.4.1)
└─ NO → No version change needed
```

### Release Checklist

**Before Release:**
- [ ] Code review completed
- [ ] All tests pass
- [ ] CHANGELOG updated with release notes
- [ ] Version numbers determined using SemVer guidelines
- [ ] `./scripts/audit-versions.py` passes
- [ ] `./scripts/compare-versions.sh` shows consistency

**During Release:**
- [ ] Create release branch
- [ ] Run version sync script
- [ ] Commit and push
- [ ] Create PR with description
- [ ] Wait for CI/CD to pass
- [ ] Merge to main
- [ ] Create git tag

**After Release:**
- [ ] Push tag to remote
- [ ] Update registry.json
- [ ] Update version-compatibility-matrix.md
- [ ] Create GitHub Release (optional)
- [ ] Announce to users
- [ ] Delete release branch

---

## Support and Questions

For issues or questions about the version system:

1. Check this guide and existing documentation
2. Review existing releases in git history: `git log --oneline | grep -i release`
3. Run audit scripts to diagnose issues: `./scripts/audit-versions.py --verbose`
4. Check CI/CD logs for validation errors
5. Contact project maintainers with specific issues

---

**Document Version:** 1.0.0
**Last Updated:** December 2, 2025
**Maintained By:** Synaptic Canvas Maintainers
**License:** MIT
