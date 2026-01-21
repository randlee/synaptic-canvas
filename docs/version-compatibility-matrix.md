# Version Compatibility Matrix

> **Last Updated:** December 2, 2025 | **Marketplace Version:** 0.4.0 (Beta)

This document provides comprehensive version compatibility information for the Synaptic Canvas marketplace. It serves as a reference for users installing packages, maintainers planning releases, and CI/CD systems validating compatibility.

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Compatibility Matrix](#compatibility-matrix)
3. [Current Status](#current-status)
4. [Release Timeline](#release-timeline)
5. [Upgrade Paths](#upgrade-paths)
6. [Package Versions](#package-versions)
7. [Supported Version Combinations](#supported-version-combinations)
8. [Deprecated & End-of-Life Versions](#deprecated--end-of-life-versions)
9. [Version Checking](#version-checking)
10. [Installation Examples](#installation-examples)
11. [Troubleshooting](#troubleshooting)

---

## Quick Reference

### Current Marketplace Status

| Component | Version | Status | Support Level |
|-----------|---------|--------|----------------|
| **Marketplace** | 0.4.0 | Beta | Active Development |
| **All Packages** | 0.4.0 | Beta | Active Development |
| **Registry Format** | 2.0.0 | Stable | Supported |
| **CLI Version** | 0.4.0 | Beta | Active Development |

### Minimum Installation Requirements

- **Marketplace CLI:** 0.4.0+
- **Individual Packages:** 0.4.0+
- **Package Tier Support:**
  - Tier 0 (No dependencies): Always compatible
  - Tier 1 (Token substitution): Requires git 2.27+
  - Tier 2 (Runtime dependencies): See package-specific requirements

### Package Tier Matrix

| Package | Tier | Current Version | Runtime Requirements |
|---------|------|-----------------|----------------------|
| `sc-delay-tasks` | 0 | 0.4.0 | None |
| `sc-manage` | 0 | 0.4.0 | None |
| `sc-git-worktree` | 1 | 0.4.0 | git >= 2.27 |
| `sc-repomix-nuget` | 2 | 0.4.0 | python3 >= 3.12 |

---

## Compatibility Matrix

### Marketplace Version Compatibility

This matrix shows which package versions are compatible with each marketplace version:

| Marketplace | Min Package | Max Package | Recommended | Status | Breaking Changes |
|-------------|-------------|-------------|-------------|--------|------------------|
| **0.4.0** | 0.4.0 | 0.4.x | 0.4.0 | Beta | None (initial) |
| **0.5.0** (planned) | 0.4.0 | 0.5.x | 0.5.0+ | Planned | Minor CLI updates |
| **1.0.0** (planned) | 1.0.0 | 1.x.x | 1.0.0+ | Planned | Registry format v3.0.0 |

### Per-Package Compatibility

#### sc-delay-tasks

| Version | Marketplace | Status | Notes |
|---------|-------------|--------|-------|
| 0.4.0 | 0.4.0+ | Beta | Supported, current release |
| 0.5.0 | 0.5.0+ (planned) | Planned | New scheduling features |
| 1.0.0 | 1.0.0+ (planned) | Planned | Stable release |

**Dependencies:** None
**Breaking Changes:** None yet
**Last Updated:** 2025-12-02

#### sc-git-worktree

| Version | Marketplace | Status | Notes |
|---------|-------------|--------|-------|
| 0.4.0 | 0.4.0+ | Beta | Supported, current release |
| 0.5.0 | 0.5.0+ (planned) | Planned | Enhanced worktree tracking |
| 1.0.0 | 1.0.0+ (planned) | Planned | Stable release, new agents |

**Dependencies:** `git >= 2.27`
**Breaking Changes:** None yet
**Last Updated:** 2025-12-02

#### sc-manage

| Version | Marketplace | Status | Notes |
|---------|-------------|--------|-------|
| 0.4.0 | 0.4.0+ | Beta | Supported, current release |
| 0.5.0 | 0.5.0+ (planned) | Planned | Registry v2.0.0 support |
| 1.0.0 | 1.0.0+ (planned) | Planned | Stable release |

**Dependencies:** None
**Breaking Changes:** None yet
**Last Updated:** 2025-12-02

#### sc-repomix-nuget

| Version | Marketplace | Status | Notes |
|---------|-------------|--------|-------|
| 0.4.0 | 0.4.0+ | Beta | Supported, current release |
| 0.5.0 | 0.5.0+ (planned) | Planned | .NET 8.0+ support |
| 1.0.0 | 1.0.0+ (planned) | Planned | Stable release |

**Dependencies:** `python3 >= 3.12`
**Breaking Changes:** None yet
**Last Updated:** 2025-12-02

---

## Current Status

### Version 0.4.0 (Current Beta)

**Release Date:** December 2, 2025
**Status:** Beta - Active Development
**Support Level:** Full
**Estimated Stability:** 70%

#### What's Included

- 4 marketplace packages (all v0.4.0)
- 4 commands
- 4 skills
- 14 agents
- 2 scripts
- Central registry at `docs/registries/nuget/registry.json`
- Registry format 2.0.0

#### Known Issues

- No known critical issues
- API stability may change before 1.0.0
- v0.5.0 (SC-prefix) is a breaking change from v0.4.0 - updates required for all packages

#### Breaking Change Policy

During beta (0.4.x):
- Minor breaking changes may occur with MINOR version bumps
- Major breaking changes reserved for MAJOR version bumps
- No long-term support for beta versions
- Beta users should expect to update frequently

---

## Release Timeline

### Historical

- **v0.4.0** (Dec 2, 2025) - Initial beta release
  - Marketplace infrastructure
  - 4 initial packages
  - Registry format 2.0.0
  - CLI version 0.4.0

### Planned

#### v0.5.0 (Planned - Q1 2025)

**Focus:** Feature expansion and API refinement

- Enhanced package discovery
- New agent templates
- Improved token substitution
- Additional scheduling features in sc-delay-tasks
- Worktree tracking improvements

**Breaking Changes:** Minor CLI adjustments
**Upgrade Path:** 0.4.0 → 0.5.0 (automatic compatibility)
**Migration Time:** < 1 minute

#### v0.6.0 (Planned - Q2 2025)

**Focus:** Additional package tier support

- Tier 2 package improvements
- Registry expansion
- Documentation enhancements

**Breaking Changes:** None expected
**Upgrade Path:** 0.5.0 → 0.6.0 (automatic)

#### v1.0.0 (Planned - Q3/Q4 2025)

**Focus:** Production-ready release

- Registry format 3.0.0
- Stable API contract
- Long-term support commitment (1 year)
- All packages at 1.0.0+

**Breaking Changes:** Registry format, CLI command structure
**Upgrade Path:** Complex (see [Upgrade Paths](#upgrade-paths))
**Migration Time:** 5-15 minutes (depends on installation complexity)
**Support Timeline:**
- Full support: v1.0.0 - v1.x.x for 12 months
- Security fixes only: 1 month after next major version

---

## Upgrade Paths

### Scenario 1: Beta to Beta (0.4.0 → 0.5.0)

**Complexity:** Low
**Risk:** Low
**Time Required:** 1-2 minutes
**Rollback:** Simple

#### Steps

1. **Backup current installation**
   ```bash
   cp -r .claude .claude.backup-0.4.0
   ```

2. **Remove old packages**
   ```bash
   rm -rf .claude/commands .claude/skills .claude/agents
   ```

3. **Install new version**
   ```bash
   python3 tools/sc-install.py install --version 0.5.0 [package-names]
   ```

4. **Verify installation**
   ```bash
   python3 tools/sc-install.py verify
   ```

5. **If issues, rollback**
   ```bash
   rm -rf .claude
   cp -r .claude.backup-0.4.0 .claude
   ```

#### Compatibility Notes

- No data loss expected
- All 0.4.0 artifacts remain compatible
- New agents may coexist with old ones
- No configuration file changes required

---

### Scenario 2: Beta to Stable (0.4.0 → 1.0.0)

**Complexity:** Medium
**Risk:** Medium
**Time Required:** 5-15 minutes
**Rollback:** Requires manual restoration

#### Breaking Changes

The 1.0.0 release includes several breaking changes:

1. **Registry Format Change**
   - Marketplace: v2.0.0 → v3.0.0
   - Package manifests: v1.0.0 → v2.0.0
   - New required fields: `minMarketplaceVersion`, `deprecationDate`

2. **CLI Changes**
   - Installation paths updated
   - Token substitution syntax refined
   - New validation requirements

3. **Package Tier Restructuring**
   - Tier 2 packages require explicit dependency declarations
   - New runtime validation on install

4. **Agent Versioning**
   - Marketplace agents must target 1.0.0+
   - Deprecated agents removed
   - New routing system

#### Migration Checklist

- [ ] Backup `.claude/` directory
- [ ] Update CLI to v1.0.0
- [ ] Review package-specific migration guides
- [ ] Update token substitution values if needed
- [ ] Test artifact loading with new version
- [ ] Verify all dependencies are available
- [ ] Update any custom agents/commands for new format
- [ ] Test in isolated environment first
- [ ] Deploy to production

#### Step-by-Step Migration

1. **Backup everything**
   ```bash
   cp -r .claude .claude.backup-1.0.0-migration
   git commit -am "backup: pre-1.0.0 migration backup"
   ```

2. **Update CLI**
   ```bash
   # Remove old CLI
   rm tools/sc-install.py

   # Install new CLI (v1.0.0)
   curl -o tools/sc-install.py https://raw.githubusercontent.com/randlee/synaptic-canvas/v1.0.0/tools/sc-install.py
   ```

3. **Review manifests**
   ```bash
   # Check each package's CHANGELOG.md for v1.0.0 section
   cat packages/sc-git-worktree/CHANGELOG.md | grep -A 20 "1.0.0"
   ```

4. **Reinstall packages with new version**
   ```bash
   rm -rf .claude
   python3 tools/sc-install.py install --version 1.0.0 sc-git-worktree sc-delay-tasks sc-manage
   ```

5. **Validate new installation**
   ```bash
   python3 tools/sc-install.py verify --strict
   ```

6. **Test functionality**
   ```bash
   # Test each installed command/skill
   python3 tools/sc-install.py test-all
   ```

7. **Commit changes**
   ```bash
   git add .claude/
   git commit -m "upgrade: migrate to Synaptic Canvas v1.0.0"
   ```

#### Compatibility Notes

- 0.4.0 packages incompatible with 1.0.0 marketplace
- New registry format not backward compatible
- 0.4.0 agents must be re-installed for 1.0.0
- Consider running both versions in parallel during transition

#### Rollback Plan

If 1.0.0 upgrade fails:

```bash
# Restore from backup
rm -rf .claude
cp -r .claude.backup-1.0.0-migration .claude

# Downgrade CLI
git checkout v0.4.0 tools/sc-install.py

# Verify
python3 tools/sc-install.py verify
```

---

### Scenario 3: Single Package Update

**Example:** Update `sc-git-worktree` from 0.4.0 to 0.5.0 only

**Complexity:** Low
**Risk:** Low
**Time Required:** 1 minute

#### Steps

1. **Backup package**
   ```bash
   tar -czf .claude/sc-git-worktree-backup.tar.gz .claude/commands/sc-git-worktree* .claude/agents/*worktree* .claude/skills/*worktree*
   ```

2. **Remove old version**
   ```bash
   rm .claude/commands/sc-git-worktree.md
   rm -rf .claude/agents/*worktree*
   rm -rf .claude/skills/*worktree*
   ```

3. **Install new version**
   ```bash
   python3 tools/sc-install.py install sc-git-worktree --version 0.5.0
   ```

4. **Verify**
   ```bash
   # Test a command
   git worktree list
   ```

5. **If fails, restore**
   ```bash
   tar -xzf .claude/sc-git-worktree-backup.tar.gz
   ```

#### Cross-Package Dependencies

When updating a package that is a dependency:

- Check `.claude/` for packages that depend on it
- Run compatibility checks on dependent packages
- Test dependent packages after update

---

### Scenario 4: Staged Rollout (Multiple Repositories)

**For:** Teams managing many repositories
**Complexity:** Medium
**Risk:** Low (controlled)

#### Process

1. **Create test environment**
   ```bash
   cd ~/test-upgrade
   git clone [your-repo]
   ```

2. **Test upgrade path**
   ```bash
   cd ~/test-upgrade/[your-repo]
   python3 tools/sc-install.py install --version 1.0.0 --dry-run
   ```

3. **Document compatibility**
   ```bash
   python3 tools/sc-install.py report compatibility > upgrade-report.txt
   ```

4. **Deploy to canary repos** (5% of total)
   ```bash
   # In each selected repo
   python3 tools/sc-install.py install --version 1.0.0 --force
   git commit -m "upgrade: canary deployment to v1.0.0"
   ```

5. **Monitor for issues** (48 hours)
   - Check CI/CD success rates
   - Review error logs
   - Gather feedback

6. **Deploy to staging repos** (50% of total)
   - Same process as canary
   - Wait 48 hours

7. **Full production rollout** (100%)
   - Deploy to all repos
   - Monitor continuously

---

## Package Versions

### Version Release Schedule

#### Maintenance Releases (0.4.x)

Beta maintenance releases focus on bug fixes and documentation:

- **0.4.1** (Planned) - Bug fixes
  - Expected: Early January 2025
  - Focus: Stability improvements

- **0.4.2** (Planned) - More bug fixes
  - Expected: Late January 2025
  - Focus: Performance tuning

#### Feature Releases (0.5.x)

Beta feature releases add new capabilities:

- **0.5.0** (Planned) - Feature expansion
  - Expected: March 2025
  - Focus: New agents, improved CLI

- **0.5.1** (Planned) - Feature follow-up
  - Expected: April 2025
  - Focus: Refinements

#### Pre-Stable Releases (0.6.x)

Polish and stability:

- **0.6.0** (Planned) - Final beta polish
  - Expected: May 2025
  - Focus: Performance, documentation

#### Stable Release (1.0.0+)

Long-term support begins:

- **1.0.0** - First stable release
  - Expected: July 2025
  - Focus: API stability, long-term support

---

## Supported Version Combinations

### Recommended Combinations

These combinations are tested and recommended for production use:

#### Combination A: Current Beta (Recommended for new projects)

```yaml
marketplace: 0.4.0
packages:
  - sc-delay-tasks: 0.4.0
  - sc-git-worktree: 0.4.0
  - sc-manage: 0.4.0
  - sc-repomix-nuget: 0.4.0
registry_format: 2.0.0
cli_version: 0.4.0
status: "Beta - Actively Tested"
```

**When to Use:** Development, testing, early adoption
**Support Level:** Full
**Update Frequency:** Every 2-4 weeks

#### Combination B: Mixed Marketplace Versions (Not Recommended)

```yaml
marketplace: 0.4.0
packages:
  - sc-delay-tasks: 0.3.0        # UNSUPPORTED
  - sc-git-worktree: 0.4.0
  - sc-manage: 0.5.0          # NOT YET RELEASED
registry_format: 2.0.0
status: "UNSUPPORTED"
```

**Issue:** Incompatible package versions
**Why Not:** May cause unpredictable behavior
**Fix:** Update all packages to 0.4.0

### Unsupported Combinations

#### Example 1: Skipped Marketplace Version

```yaml
marketplace: 0.3.5
packages:
  - sc-git-worktree: 0.4.0       # v0.4.0 requires marketplace 0.4.0+
registry_format: 1.0.0        # Old format incompatible
status: "UNSUPPORTED"
```

**Error:** `Package v0.4.0 requires marketplace >= 0.4.0`
**Solution:** Upgrade marketplace to 0.4.0

#### Example 2: Pre-Release Mixing

```yaml
marketplace: 1.0.0
packages:
  - sc-git-worktree: 0.4.0       # v0.4.0 incompatible with marketplace 1.0.0
  - sc-manage: 1.0.0          # Compatible
registry_format: 3.0.0
status: "UNSUPPORTED"
```

**Error:** `Package v0.4.0 incompatible with marketplace v1.0.0`
**Solution:** Upgrade sc-git-worktree to 1.0.0+

#### Example 3: Runtime Dependency Missing

```yaml
marketplace: 0.4.0
packages:
  - sc-repomix-nuget: 0.4.0      # Requires python3 >= 3.12
installed_python: "3.8"       # Too old
status: "UNSUPPORTED"
```

**Error:** `Runtime dependency not satisfied: python3 >= 3.12`
**Solution:** Install Python 3.12 or later

---

## Deprecated & End-of-Life Versions

### Deprecation Policy

1. **Announcement Phase** (2 weeks)
   - Public notice of deprecation
   - Documentation marked [DEPRECATED]
   - Still fully functional

2. **Deprecation Phase** (4 weeks)
   - Version shows deprecation warning on install
   - Alternative version recommended
   - Still receives critical security fixes

3. **End-of-Life** (After deprecation)
   - Version no longer available for new installations
   - Old installations still work (no forced upgrade)
   - Security issues not fixed

### Current Deprecation Status

| Version | Status | Reason | Supported Until |
|---------|--------|--------|-----------------|
| 0.4.0 | Active | Current | TBD (beta) |
| 0.3.x and earlier | N/A | Never released | N/A |
| 1.0.0 (planned) | Future | Stable | 1 year after release + 1 month overlap |

### End-of-Life Timeline

| Version | Released | Deprecated | EOL | Support Window |
|---------|----------|-----------|-----|-----------------|
| 0.4.0 (beta) | Dec 2024 | Q4 2025 | Q1 2026 | ~1 year (beta) |
| 0.5.0 (beta) | Q1 2025 (est) | Q3 2025 (est) | Q4 2025 (est) | ~6 months (beta) |
| 1.0.0 | Q3 2025 (est) | Q3 2026 (est) | Q4 2026 (est) | 12+ months (stable) |

### Migration Path for Deprecated Versions

When a version is deprecated:

```bash
# Check if you're using deprecated version
python3 tools/sc-install.py status

# Get migration guide
python3 tools/sc-install.py migrate-guide 0.4.0

# Perform migration
python3 tools/sc-install.py upgrade 0.5.0
```

---

## Version Checking

### Check Installation Version

```bash
# Check marketplace version
python3 tools/sc-install.py version

# Check installed packages
python3 tools/sc-install.py list --with-versions

# Check all versions
python3 tools/sc-install.py status --full
```

### Verify Compatibility

```bash
# Quick check
python3 tools/sc-install.py verify

# Detailed compatibility report
python3 tools/sc-install.py verify --detailed

# Strict validation (recommended for CI/CD)
python3 tools/sc-install.py verify --strict
```

### Compare Local vs Registry Versions

```bash
# Show version differences
python3 tools/sc-install.py compare-versions

# Show packages with updates available
python3 tools/sc-install.py outdated

# Check for breaking changes
python3 tools/sc-install.py check-breaking-changes
```

### Version Compatibility Check

```bash
# Check if version combination is supported
python3 tools/sc-install.py check-compatibility \
  --marketplace 0.4.0 \
  --package sc-git-worktree:0.4.0

# Check multiple packages
python3 tools/sc-install.py check-compatibility \
  --marketplace 0.4.0 \
  --package sc-git-worktree:0.4.0 \
  --package sc-delay-tasks:0.4.0 \
  --package sc-manage:0.4.0
```

### Automated CI/CD Checks

#### GitHub Actions Example

```yaml
name: Version Compatibility Check

on: [pull_request, push]

jobs:
  version-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Check version compatibility
        run: |
          python3 tools/sc-install.py verify --strict
          python3 tools/sc-install.py check-compatibility \
            --marketplace 0.4.0 \
            --package sc-git-worktree:0.4.0 \
            --package sc-delay-tasks:0.4.0 \
            --package sc-manage:0.4.0
```

#### Bash Script Example

```bash
#!/bin/bash
# scripts/check-version-compat.sh

set -e

echo "Checking version compatibility..."

MARKETPLACE_VERSION="0.4.0"
EXPECTED_PACKAGES=(
    "sc-git-worktree:0.4.0"
    "sc-delay-tasks:0.4.0"
    "sc-manage:0.4.0"
)

# Check each package
for pkg in "${EXPECTED_PACKAGES[@]}"; do
    python3 tools/sc-install.py check-compatibility \
        --marketplace "$MARKETPLACE_VERSION" \
        --package "$pkg" || {
        echo "ERROR: Incompatible version found: $pkg"
        exit 1
    }
done

echo "SUCCESS: All versions compatible"
```

---

## Installation Examples

### Example 1: Supported - Fresh Installation (0.4.0)

**Goal:** Install all packages on a new project
**Marketplace:** 0.4.0
**Packages:** All 0.4.0

```bash
# Initialize .claude directory
mkdir -p .claude/{commands,skills,agents,scripts}

# Install all packages
python3 tools/sc-install.py install \
  --marketplace 0.4.0 \
  sc-delay-tasks \
  sc-git-worktree \
  sc-manage \
  sc-repomix-nuget

# Verify
python3 tools/sc-install.py verify
```

**Result:** SUPPORTED ✓
**Verification:**
```
marketplace: 0.4.0 ✓
sc-delay-tasks: 0.4.0 ✓
sc-git-worktree: 0.4.0 ✓
sc-manage: 0.4.0 ✓
sc-repomix-nuget: 0.4.0 ✓
All versions compatible.
```

---

### Example 2: Supported - Single Package Installation

**Goal:** Install only sc-git-worktree
**Marketplace:** 0.4.0
**Package:** sc-git-worktree 0.4.0

```bash
# Install just one package
python3 tools/sc-install.py install sc-git-worktree

# Verify dependencies
python3 tools/sc-install.py verify sc-git-worktree
```

**Result:** SUPPORTED ✓
**Output:**
```
Package: sc-git-worktree 0.4.0
Status: Compatible with marketplace 0.4.0
Dependencies satisfied:
  - git >= 2.27: Found git 2.43.0 ✓
```

---

### Example 3: Unsupported - Version Mismatch

**Goal:** Attempt installation with mismatched versions
**Marketplace:** 0.4.0
**Package:** sc-git-worktree 0.3.0 (hypothetical)

```bash
python3 tools/sc-install.py install \
  --package-version 0.3.0 \
  sc-git-worktree
```

**Result:** UNSUPPORTED ✗
**Error Output:**
```
ERROR: Package version 0.3.0 not compatible with marketplace 0.4.0
Minimum package version: 0.4.0
Maximum package version: 0.4.x

Suggestions:
1. Upgrade package to 0.4.0+
2. Downgrade marketplace to version that supports 0.3.0 (none available)

Use --force to override (not recommended)
```

---

### Example 4: Unsupported - Missing Runtime Dependency

**Goal:** Install sc-repomix-nuget without Python 3.12
**Marketplace:** 0.4.0
**Package:** sc-repomix-nuget 0.4.0
**System Python:** 3.8

```bash
python3 tools/sc-install.py install sc-repomix-nuget
```

**Result:** UNSUPPORTED ✗
**Error Output:**
```
ERROR: Runtime dependency not satisfied for sc-repomix-nuget 0.4.0
Missing: python3 >= 3.12
Found: python3 3.8

Required runtime dependencies:
  - python3 >= 3.12: NOT FOUND (have 3.8)

To fix:
1. Install Python 3.12 or later
2. Set PYTHON3_VERSION environment variable to path of Python 3.12+

Example:
  export PYTHON3_VERSION=/usr/local/bin/python3.12
  python3 tools/sc-install.py install sc-repomix-nuget
```

---

### Example 5: Supported - Mixed Tier Installation

**Goal:** Install packages from different tiers
**Marketplace:** 0.4.0
**Packages:**
- sc-delay-tasks (Tier 0 - no dependencies)
- sc-git-worktree (Tier 1 - token substitution)
- sc-repomix-nuget (Tier 2 - runtime dependencies)

```bash
python3 tools/sc-install.py install \
  sc-delay-tasks \
  sc-git-worktree \
  sc-repomix-nuget

# Verify all
python3 tools/sc-install.py verify
```

**Result:** SUPPORTED (with conditions) ✓
**Output:**
```
Installation Report:
  Tier 0 packages (no dependencies):
    - sc-delay-tasks 0.4.0 ✓

  Tier 1 packages (token substitution):
    - sc-git-worktree 0.4.0 ✓
      Token substitution: REPO_NAME={{git-repo-basename}}

  Tier 2 packages (runtime dependencies):
    - sc-repomix-nuget 0.4.0 ✓
      Dependencies satisfied:
        - python3 >= 3.12: Found 3.12.1 ✓

Overall: SUPPORTED
```

---

### Example 6: Conditional Support - Partial Installation

**Goal:** Install sc-repomix-nuget only if Python 3.12+ available
**Marketplace:** 0.4.0

```bash
#!/bin/bash

# Install tier 0 and 1 packages (always available)
python3 tools/sc-install.py install sc-delay-tasks sc-git-worktree

# Check Python version for tier 2 package
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
MIN_PYTHON="3.12"

if [[ "$PYTHON_VERSION" > "$MIN_PYTHON" ]]; then
    echo "Installing tier 2 packages..."
    python3 tools/sc-install.py install sc-repomix-nuget
else
    echo "Python $MIN_PYTHON+ required for sc-repomix-nuget"
    echo "Current: Python $PYTHON_VERSION"
    echo "Skipping sc-repomix-nuget installation"
fi
```

**Result:** SUPPORTED (with optional tier 2) ✓

---

## Troubleshooting

### Issue 1: Version Conflict Detected

**Symptoms:**
```
ERROR: Version conflict detected
Package: sc-git-worktree
Expected version: 0.4.0
Found version: 0.3.0
```

**Diagnosis:**
```bash
# Check what's installed
ls -la .claude/agents/*worktree*
cat .claude/agents/*worktree*.md | grep "version:"
```

**Solutions:**

Option A - Reinstall correct version:
```bash
rm .claude/commands/sc-git-worktree.md
rm -rf .claude/agents/*worktree*
python3 tools/sc-install.py install --force sc-git-worktree
```

Option B - Update registry:
```bash
python3 tools/sc-install.py update-registry --force
python3 tools/sc-install.py install --force sc-git-worktree
```

Option C - Manual fix:
```bash
# Edit frontmatter in artifact files
# Change: version: 0.3.0
# To: version: 0.4.0
nano .claude/agents/sc-git-worktree-*.md
```

---

### Issue 2: Marketplace Version Too Old

**Symptoms:**
```
ERROR: Marketplace version 0.3.0 not supported
Package requires: 0.4.0+
```

**Diagnosis:**
```bash
python3 tools/sc-install.py version
# Output: Marketplace version: 0.3.0 (outdated)
```

**Solutions:**

Option A - Update CLI:
```bash
# Download and install new CLI
curl -o tools/sc-install.py https://raw.githubusercontent.com/randlee/synaptic-canvas/main/tools/sc-install.py
python3 tools/sc-install.py version
```

Option B - Verify registry:
```bash
python3 tools/sc-install.py check-registry
python3 tools/sc-install.py update-registry
```

Option C - Manual update:
```bash
# Edit version in manifest files
# Or reinstall from scratch
rm -rf .claude
python3 tools/sc-install.py init
python3 tools/sc-install.py install sc-delay-tasks
```

---

### Issue 3: Runtime Dependency Missing

**Symptoms:**
```
ERROR: Package sc-repomix-nuget requires:
  python3 >= 3.12
  Found: python3 3.8
```

**Diagnosis:**
```bash
# Check Python version
python3 --version

# List all Python versions
which -a python3 python3.12 python3.11
```

**Solutions:**

Option A - Install required Python:
```bash
# macOS
brew install python@3.12

# Ubuntu/Debian
sudo apt-get install python3.12

# Fedora/RHEL
sudo dnf install python3.12
```

Option B - Use system Python:
```bash
# If Python 3.12 installed elsewhere
export PYTHON3_VERSION=/usr/local/bin/python3.12
python3 tools/sc-install.py install sc-repomix-nuget
```

Option C - Skip tier 2 packages:
```bash
# Install only tier 0 and 1
python3 tools/sc-install.py install \
  sc-delay-tasks \
  sc-git-worktree \
  sc-manage
```

---

### Issue 4: Artifact Version Mismatch

**Symptoms:**
```
WARNING: Version mismatch detected
File: .claude/commands/delay.md
Package version: 0.4.0
Artifact version: 0.3.0
```

**Diagnosis:**
```bash
# Find all mismatches
grep -r "version:" .claude/ | sort
```

**Solutions:**

Option A - Reinstall package:
```bash
rm .claude/commands/delay.md
rm -rf .claude/agents/delay-*
python3 tools/sc-install.py install --force sc-delay-tasks
```

Option B - Manual sync:
```bash
# Update artifact frontmatter
sed -i 's/version: 0.3.0/version: 0.4.0/g' .claude/commands/*.md
sed -i 's/version: 0.3.0/version: 0.4.0/g' .claude/agents/*.md
```

Option C - Use sync script:
```bash
python3 scripts/set-package-version.py sc-delay-tasks 0.4.0
```

---

### Issue 5: Token Substitution Failed

**Symptoms:**
```
ERROR: Token substitution failed for sc-git-worktree
Variable: REPO_NAME
Value expected: {git-repo-basename}
Found: {{REPO_NAME}}
```

**Diagnosis:**
```bash
# Check git repository status
git rev-parse --show-toplevel
git rev-parse --abbrev-ref HEAD

# Check for tokens
grep -r "{{REPO_NAME}}" .claude/
```

**Solutions:**

Option A - Reinstall with token substitution:
```bash
cd /path/to/git/repo
python3 tools/sc-install.py install --force sc-git-worktree
```

Option B - Manual substitution:
```bash
# Find actual repo name
REPO_NAME=$(basename $(git rev-parse --show-toplevel))

# Replace tokens
sed -i "s/{{REPO_NAME}}/$REPO_NAME/g" .claude/agents/sc-git-worktree-*.md
```

Option C - Check environment:
```bash
# Verify git is available
which git
git --version

# Check git config
git config user.name
git config user.email
```

---

### Issue 6: Compatibility Check Fails in CI/CD

**Symptoms:**
```
ERROR in CI/CD pipeline: Version compatibility check failed
Required: marketplace 0.4.0, all packages 0.4.0
Found: marketplace 0.4.0, sc-git-worktree 0.3.0
```

**Diagnosis:**
```yaml
# Check CI workflow
cat .github/workflows/version-check.yml
```

**Solutions:**

Option A - Fix artifact in repo:
```bash
# Update mismatched artifact
git add .claude/agents/sc-git-worktree-*.md
git commit -m "fix: update artifact version to 0.4.0"
git push
```

Option B - Update CI check:
```yaml
# In .github/workflows/version-check.yml
- name: Version compatibility
  run: |
    python3 tools/sc-install.py verify --strict \
      --marketplace 0.4.0 \
      --package sc-git-worktree:0.4.0 \
      --package sc-delay-tasks:0.4.0
```

Option C - Skip until fixed:
```yaml
- name: Version compatibility
  continue-on-error: true  # Temporary
  run: python3 tools/sc-install.py verify --strict
```

---

### Issue 7: Cannot Determine Compatible Version

**Symptoms:**
```
UNKNOWN: Cannot determine compatible version for package
Package: custom-package
Available versions: [none]
```

**Diagnosis:**
```bash
# Check if package exists
python3 tools/sc-install.py list all

# Check registry
python3 tools/sc-install.py registry-info

# Search for package
python3 tools/sc-install.py search custom-package
```

**Solutions:**

Option A - Package not yet available:
```bash
# Wait for package release or request it
echo "custom-package not yet in marketplace"
python3 tools/sc-install.py request-package custom-package
```

Option B - Install from source:
```bash
# Clone and install manually
git clone https://github.com/user/custom-package.git
cp -r custom-package .claude/
```

Option C - Add to registry:
```bash
# If maintaining your own registry
python3 tools/sc-install.py add-package \
  --name custom-package \
  --version 0.1.0 \
  --path ./custom-package
```

---

### Issue 8: Downgrade Required

**Symptoms:**
```
ERROR: New version 0.5.0 not compatible with current setup
Need to downgrade to 0.4.0
```

**Diagnosis:**
```bash
python3 tools/sc-install.py version
python3 tools/sc-install.py status --detailed
```

**Solutions:**

Option A - Downgrade single package:
```bash
python3 tools/sc-install.py install \
  --package-version 0.4.0 \
  sc-git-worktree

# Verify
python3 tools/sc-install.py verify
```

Option B - Full downgrade:
```bash
# Backup current
cp -r .claude .claude.backup-0.5.0

# Remove new version
rm -rf .claude

# Install old version
python3 tools/sc-install.py init --version 0.4.0
python3 tools/sc-install.py install --version 0.4.0 \
  sc-delay-tasks sc-git-worktree sc-manage
```

Option C - Restore from backup:
```bash
# If backup exists from before upgrade
tar -xzf .claude-backup-0.4.0.tar.gz
python3 tools/sc-install.py verify
```

---

### Issue 9: Version String Parsing Error

**Symptoms:**
```
ERROR: Unable to parse version string "0.4.0-rc1"
Invalid semantic version format
```

**Diagnosis:**
```bash
# Check for non-standard version formats
grep -r "version:" .claude/ | grep -v -E "0\.[0-9]\.[0-9]"
```

**Solutions:**

Option A - Use standard semantic versioning:
```bash
# Incorrect: 0.4.0-rc1
# Correct: 0.4.0

# Edit artifact
sed -i 's/version: 0.4.0-rc1/version: 0.4.0/g' .claude/agents/*.md
```

Option B - Update to latest:
```bash
python3 tools/sc-install.py install --force sc-git-worktree
```

Option C - Verify all versions:
```bash
python3 tools/sc-install.py audit-versions --fix
```

---

### Issue 10: Upgrade Interrupted / Partial State

**Symptoms:**
```
ERROR: Installation interrupted
.claude directory in inconsistent state
Some artifacts from 0.4.0, some from 0.5.0
```

**Diagnosis:**
```bash
# List all artifact versions
python3 tools/sc-install.py audit-versions

# Show version summary
python3 tools/sc-install.py status --verbose
```

**Solutions:**

Option A - Complete the upgrade:
```bash
python3 tools/sc-install.py install --force --version 0.5.0 \
  sc-delay-tasks sc-git-worktree sc-manage
```

Option B - Rollback to previous state:
```bash
# Check for backups
ls -la .claude-backup-*

# Restore backup
cp -r .claude .claude-broken
cp -r .claude-backup-0.4.0 .claude

# Verify
python3 tools/sc-install.py verify
```

Option C - Clean slate:
```bash
# Remove everything and restart
rm -rf .claude
python3 tools/sc-install.py init
python3 tools/sc-install.py install sc-delay-tasks
```

---

## Additional Resources

### Documentation

- [Versioning Strategy](versioning-strategy.md) - Detailed versioning policy
- [Releases](https://github.com/randlee/synaptic-canvas/releases) - GitHub releases page
- [Changelog](https://github.com/randlee/synaptic-canvas/blob/main/CHANGELOG.md) - Project changelog
- [Package-Specific Changelogs](https://github.com/randlee/synaptic-canvas/tree/main/packages) - Individual package changelogs

### Tools

- [sc-install.py](../tools/sc-install.py) - Installation and version management CLI
- [Version Audit Script](../scripts/audit-versions.py) - Version validation
- [Registry Schema](../docs/registries/nuget/registry.json) - Registry format specification

### Support

- **GitHub Issues:** [Report version-related issues](https://github.com/randlee/synaptic-canvas/issues)
- **Discussions:** [Version compatibility discussions](https://github.com/randlee/synaptic-canvas/discussions)
- **Contributing:** [Contribute version improvements](../CONTRIBUTING.md)

---

## Glossary

**Artifact** - A CLI command, skill, agent, or script included in a package

**Beta** - Pre-release version (0.x.x) with active development and potential breaking changes

**Breaking Change** - A modification that requires updates to existing installations or code

**Compatibility** - The ability of different versions to work together without issues

**Dependency** - An external tool or library required by a package

**End-of-Life (EOL)** - When a version is no longer supported or available

**Marketplace** - The Synaptic Canvas platform that manages packages

**Package** - A collection of related artifacts (commands, skills, agents)

**Registry** - Centralized record of all available packages and versions

**Semantic Versioning** - Version numbering system (MAJOR.MINOR.PATCH)

**Stable** - Production-ready version (1.0.0+) with long-term support commitment

**Tier** - Package classification based on complexity and dependencies
- **Tier 0** - Direct copy, no dependencies
- **Tier 1** - Token substitution only
- **Tier 2** - External runtime dependencies

**Token Substitution** - Automatic replacement of placeholders (e.g., {{REPO_NAME}})

**Upgrade** - Moving from an older version to a newer one

**Version** - A specific release of a package or the marketplace platform

---

## Changelog for This Document

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Dec 2, 2025 | Initial release |

---

**Last Updated:** December 2, 2025
**Marketplace Version:** 0.4.0 (Beta)
**Document Version:** 1.0

For updates and corrections, please refer to the [Synaptic Canvas repository](https://github.com/randlee/synaptic-canvas).
