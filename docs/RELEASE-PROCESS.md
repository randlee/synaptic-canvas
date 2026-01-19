# Synaptic Canvas Release Process

This document defines the complete release process for the Synaptic Canvas marketplace platform, including versioning strategy, pre-release procedures, execution steps, and post-release verification.

## Table of Contents

- [Overview](#overview)
- [Versioning System](#versioning-system)
- [Release Roles and Responsibilities](#release-roles-and-responsibilities)
- [Pre-Release Checklist](#pre-release-checklist)
- [Release Execution](#release-execution)
- [Release Scenarios](#release-scenarios)
- [Post-Release Procedures](#post-release-procedures)
- [Rollback and Incident Procedures](#rollback-and-incident-procedures)
- [Command Reference](#command-reference)

## Overview

The Synaptic Canvas release process manages three versioning layers:

1. **Marketplace Platform** (`version.yaml`) - Infrastructure and CLI
2. **Packages** (`packages/*/manifest.yaml`) - Individual package versions
3. **Artifacts** (YAML frontmatter) - Commands, skills, agents synchronized with package

**Current Status:** 0.4.0 (Beta)

### Release Frequency

- **Beta Phase (0.x.x):** As-needed releases for new features and bug fixes
- **Stable Phase (1.0.0+):** Monthly releases or as-needed hotfixes

### Semantic Versioning

All versions follow MAJOR.MINOR.PATCH format:

- **MAJOR (X):** Breaking changes, major refactoring, incompatible API changes
- **MINOR (Y):** New features, new artifacts, functionality enhancements
- **PATCH (Z):** Bug fixes, documentation updates, minor refinements

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

- All commands in a package → same version as manifest
- All skills in a package → same version as manifest
- All agents in a package → same version as manifest
- Cross-package agents → can use marketplace version

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

**Typical Activities:**
- Review proposed version changes
- Run audit and validation scripts
- Execute release commands
- Monitor CI/CD pipeline
- Create GitHub release notes

### Package Maintainers

**Qualifications:** Package owner or designated contributor

**Responsibilities:**
- Update package version in manifest
- Update CHANGELOG.md with release notes
- Ensure all artifacts are current
- Request version bump from Release Manager

**Typical Activities:**
- Create PR with version changes
- Document features/fixes in CHANGELOG
- Test locally before submission
- Address feedback in PR review

### Release Verifier

**Qualifications:** Any maintainer or designated tester

**Responsibilities:**
- Verify post-release packages are installable
- Test core functionality
- Confirm registry metadata is accurate
- Report any issues immediately

**Typical Activities:**
- Install packages from registry
- Verify artifact functionality
- Check registry entries
- Test rollback procedures

## Pre-Release Checklist

### 1. Version Number Review and Approval

**Purpose:** Ensure version bump is appropriate

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
  echo "0.4.0" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$'
  ```

- [ ] **Release Manager approval obtained**
  - PR review approved
  - Release plan confirmed
  - Timeline confirmed

**Example:**
```
Release Plan for 2025-12-15

Marketplace Version: 0.4.0 → 0.5.0 (MINOR - new features)
  - Reason: New registry format, enhanced installer

Packages:
  - sc-delay-tasks: 0.4.0 → 0.5.0 (new agent, feature)
  - sc-git-worktree: 0.4.0 → 0.4.1 (bugfix only)
  - sc-manage: 0.4.0 (no change)
  - sc-repomix-nuget: 0.4.0 (no change)

Approval: @maintainer-name ✓
```

### 2. CHANGELOG Verification

**Purpose:** Ensure release notes are complete and accurate

**For each package being released:**

- [ ] **CHANGELOG.md exists and is complete**
  ```bash
  # Check file exists
  ls packages/<package-name>/CHANGELOG.md
  ```

- [ ] **Unreleased section properly formatted**
  - Follow "Keep a Changelog" format
  - Include Added/Changed/Fixed/Deprecated sections as needed
  - Cross-reference PRs/issues where available

- [ ] **Version and date filled in**
  ```markdown
  ## [0.5.0] - 2025-12-15

  ### Added
  - New feature description
  - Reference to #123 (PR number)
  ```

- [ ] **CHANGELOG content reviewed for accuracy**
  - All features listed are actually in release
  - No features listed are missing from code
  - Breaking changes are clearly marked
  - Migration instructions provided if needed

- [ ] **Generate CHANGELOG preview**
  ```bash
  # View upcoming release section
  head -30 packages/<package-name>/CHANGELOG.md
  ```

**Example CHANGELOG Entry:**
```markdown
## [0.5.0] - 2025-12-15

### Added
- New delay scheduler with persistent task storage (#42)
- Support for cron-like scheduling patterns
- `/delay --schedule` command for recurring tasks
- delay-scheduler agent for advanced scheduling

### Fixed
- Memory leak in polling loop (#38)
- Incorrect interval calculation for sub-minute delays (#40)

### Changed
- Minimum polling interval increased from 1s to 60s for stability
- Improved error messages for invalid delay values

### Deprecated
- Direct use of `delay-run.py` (use agents instead)
```

### 3. Documentation Updates

**Purpose:** Ensure all documentation reflects new features/changes

**For each package being released:**

- [ ] **README.md updated (if applicable)**
  - New features documented with examples
  - Breaking changes highlighted
  - Installation instructions current
  - Dependencies updated

- [ ] **Artifact documentation current**
  - Command help text describes new options
  - Agent descriptions updated
  - Skill documentation reflects changes
  - Usage examples working

- [ ] **README includes version info**
  ```markdown
  # Package Name

  **Version:** 0.5.0
  **Status:** Beta
  **Compatibility:** Marketplace 0.5.0+
  ```

- [ ] **Link documentation verified**
  - All internal links resolve correctly
  - External links (if any) still valid
  - No broken references in CHANGELOG

**Verification Script:**
```bash
# Check for documentation links
for package in packages/*/; do
  echo "Checking $(basename $package)..."
  grep -r "^\[.*\]:.*" "$package/CHANGELOG.md" "$package/README.md" 2>/dev/null || echo "  (no links)"
done
```

### 4. Registry Metadata Updates

**Purpose:** Ensure registry accurately reflects new release

**Registry metadata includes:**

- [ ] **Package entry in registry.json**
  - Version field updated to new version
  - `lastUpdated` timestamp updated
  - Status field reflects release status (beta/stable)
  - Changelog URL points to correct version

- [ ] **Artifact counts accurate**
  - Command count matches actual commands
  - Skill count matches actual skills
  - Agent count matches actual agents
  - Script count matches actual scripts

- [ ] **Metadata aggregates updated**
  - `totalPackages` reflects current packages
  - `totalCommands`, `totalSkills`, `totalAgents` accurate
  - Categories reflect current organization

**Example Registry Entry:**
```json
"sc-delay-tasks": {
  "name": "sc-delay-tasks",
  "version": "0.5.0",
  "status": "beta",
  "lastUpdated": "2025-12-15",
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

- [ ] **Version audit passes**
  ```bash
  ./scripts/audit-versions.py --verbose
  # Should exit with code 0 and report all checks passed
  ```

- [ ] **Version sync script works**
  ```bash
  # Dry run to verify no errors
  python3 scripts/sync-versions.py --package <name> --version <new-version> --dry-run
  ```

- [ ] **Manifest validation passes**
  ```bash
  # GitHub Actions will run this automatically
  # Manual verification:
  python3 -c "
  import yaml
  for pkg in ['sc-delay-tasks', 'sc-git-worktree', 'sc-manage', 'sc-repomix-nuget']:
    with open(f'packages/{pkg}/manifest.yaml') as f:
      data = yaml.safe_load(f)
      print(f'{pkg}: v{data[\"version\"]}')
  "
  ```

- [ ] **CI pipeline passes**
  - All GitHub Actions workflows successful
  - No version audit failures
  - No manifest validation errors
  - All tests passing (if applicable)

**Manual Tests:**

- [ ] **Local package installation**
  ```bash
  # Create test directory
  mkdir -p /tmp/test-release

  # Test installation (single package)
  python3 tools/sc-install.py install <package-name> --dest /tmp/test-release/.claude

  # Verify artifacts installed
  ls -la /tmp/test-release/.claude/commands/
  ls -la /tmp/test-release/.claude/agents/
  ```

- [ ] **Version consistency**
  ```bash
  # Check installed artifact versions match manifest
  grep "version:" packages/<package-name>/manifest.yaml
  grep -r "version:" /tmp/test-release/.claude/commands/
  grep -r "version:" /tmp/test-release/.claude/agents/
  # All should match
  ```

- [ ] **Artifact functionality (smoke tests)**
  - Commands respond to `--help`
  - Agents return valid JSON
  - Skills reference correct agents
  - No broken references in documentation

- [ ] **Uninstall works cleanly**
  ```bash
  python3 tools/sc-install.py uninstall <package-name> --dest /tmp/test-release/.claude

  # Verify removed
  ls /tmp/test-release/.claude/commands/ | wc -l  # Should be 0 if uninstall successful
  ```

**Testing Checklist Template:**
```bash
#!/bin/bash
# Pre-release testing checklist

PACKAGE=$1
VERSION=$2

echo "Testing $PACKAGE v$VERSION..."

# 1. Version audit
./scripts/audit-versions.py --verbose || exit 1

# 2. Manifest validation
python3 -c "import yaml; yaml.safe_load(open('packages/$PACKAGE/manifest.yaml'))" || exit 1

# 3. Local install test
mkdir -p /tmp/test-$PACKAGE-$VERSION
python3 tools/sc-install.py install $PACKAGE --dest /tmp/test-$PACKAGE-$VERSION/.claude || exit 1

# 4. Verify installation
test -d /tmp/test-$PACKAGE-$VERSION/.claude/commands/ || exit 1
test -d /tmp/test-$PACKAGE-$VERSION/.claude/agents/ || exit 1

# 5. Cleanup
rm -rf /tmp/test-$PACKAGE-$VERSION

echo "✓ All tests passed for $PACKAGE v$VERSION"
```

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
git checkout -b release/marketplace-v0.5.0

# Single package
git checkout -b release/package-sc-delay-tasks-v0.5.0

# All packages
git checkout -b release/packages-v0.5.0

# Hotfix
git checkout -b release/patch-sc-delay-tasks-v0.4.1
```

**Push branch (create PR early for feedback):**

```bash
git push origin release/marketplace-v0.5.0
# Create PR via GitHub interface or gh CLI
gh pr create --title "release: Marketplace v0.5.0" \
  --body "Marketplace platform v0.5.0 release including enhanced installer and new registry format"
```

### Step 2: Update Version Numbers

**2a. Update marketplace version (if applicable):**

```bash
# Edit version.yaml
# Change: version: "0.4.0" → version: "0.5.0"

cat > version.yaml <<'EOF'
# Marketplace Platform Version (NOT package versions)
#
# This is the version of the Synaptic Canvas marketplace platform/CLI infrastructure itself.
# It is NOT the source of truth for individual package versions.
#
# Three-layer versioning system:
# 1. Marketplace Version (this file): Platform/CLI version (e.g., sc-install.py, registry format)
# 2. Package Version (manifest.yaml): Per-package version (independent for each package)
# 3. Artifact Version (frontmatter): Individual command/skill/agent version (synchronized with package)
#
# See: docs/versioning-strategy.md for complete versioning policy
#
version: "0.5.0"
EOF
```

**2b. Update package versions (for each package being released):**

```bash
# Option 1: Manual update (small changes)
vi packages/sc-delay-tasks/manifest.yaml
# Change: version: 0.4.0 → version: 0.5.0

# Option 2: Automated sync (recommended for multiple packages)
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.0 --dry-run

# Review changes first
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.0
```

**2c. Verify versions are synchronized:**

```bash
# Run audit to verify all versions match
./scripts/audit-versions.py --verbose

# Should output:
# ✅ All checks passed (N checks)
# Exit code 0
```

**Sync-versions.py Examples:**

```bash
# Single package release
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.0

# All packages to same version
python3 scripts/sync-versions.py --all --version 0.5.0

# Marketplace platform only
python3 scripts/sync-versions.py --marketplace --version 0.5.0

# Dry run to preview changes
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.0 --dry-run

# Sync and create git commit
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.0 --commit
```

**Files Modified by Sync:**
- `packages/<name>/manifest.yaml` - Package version
- `packages/<name>/commands/*.md` - Command artifact versions
- `packages/<name>/skills/*/SKILL.md` - Skill artifact versions
- `packages/<name>/agents/*.md` - Agent artifact versions

### Step 3: Update CHANGELOG

**For each package being released:**

```bash
# Edit CHANGELOG.md - move [Unreleased] → [X.Y.Z] - YYYY-MM-DD
vi packages/sc-delay-tasks/CHANGELOG.md
```

**CHANGELOG update template:**

```markdown
# Original structure
## [Unreleased]
### Added
- New feature 1
- New feature 2

## [0.4.0] - 2025-12-02
...

# After release, becomes:
## [Unreleased]
### Planned
- Future feature 1

## [0.5.0] - 2025-12-15
### Added
- New feature 1
- New feature 2

## [0.4.0] - 2025-12-02
...
```

**Bash script to update CHANGELOG date:**

```bash
#!/bin/bash
# Script to move Unreleased → Version with today's date

PACKAGE=$1
VERSION=$2
DATE=$(date +%Y-%m-%d)

sed -i "s/## \[Unreleased\]/## [$VERSION] - $DATE/" packages/$PACKAGE/CHANGELOG.md

echo "Updated CHANGELOG for $PACKAGE to v$VERSION ($DATE)"
```

### Step 4: Commit and Create Git Tag

**Commit changes:**

```bash
# Stage version changes
git add version.yaml packages/*/manifest.yaml packages/*/CHANGELOG.md

# Commit with clear message
git commit -m "chore: release marketplace v0.5.0

- Update marketplace platform version to 0.5.0
- Enhanced installer with new registry format support
- Updated all affected packages
- See CHANGELOG.md for full details"
```

**Commit message template:**

```
chore: release <scope> v<version>

<description of what changed>

- Reason for release
- Key improvements/fixes
- Package versions updated
- Registry metadata updated

Closes #<issue-number> (if applicable)
```

**Alternative for single package:**

```bash
git commit -m "chore(sc-delay-tasks): release v0.5.0

- Add new delay scheduler with persistent storage
- Support cron-like scheduling patterns
- Fix memory leak in polling loop
- Minimum polling interval now 60 seconds

Breaking: Direct delay-run.py usage deprecated

See packages/sc-delay-tasks/CHANGELOG.md for full details"
```

**Create annotated git tag:**

```bash
# Tag format: v<version> for marketplace, v<package>-<version> for packages

# Marketplace release
git tag -a v0.5.0 -m "Marketplace Platform v0.5.0

- Enhanced installer
- New registry format (v2.0.0+)
- Better error handling
- See CHANGELOG.md for full details"

# Single package release
git tag -a v0.5.0-sc-delay-tasks -m "sc-delay-tasks v0.5.0

- New delay scheduler with persistent storage
- Support cron-like scheduling patterns
- Fix memory leak in polling loop

See packages/sc-delay-tasks/CHANGELOG.md"

# Multiple packages (tag each)
git tag -a v0.5.0-all -m "All packages v0.5.0 release

- sc-delay-tasks v0.5.0
- sc-git-worktree v0.5.0
- sc-manage v0.5.0
- sc-repomix-nuget v0.5.0

See individual CHANGELOG.md files"
```

**Push changes and tags:**

```bash
# Verify tags are created
git tag -l | grep "v0.5"

# Push to remote
git push origin release/marketplace-v0.5.0

# Push tags
git push origin v0.5.0

# Or push all tags at once
git push origin --tags
```

### Step 5: Run All Audit and Validation Scripts

**Full validation suite:**

```bash
#!/bin/bash
# Pre-release validation suite

echo "====== Pre-Release Validation ======"

# 1. Version audit
echo ""
echo "1. Running version audit..."
./scripts/audit-versions.py --verbose
if [ $? -ne 0 ]; then
  echo "❌ Version audit failed!"
  exit 1
fi

# 2. Compare versions
echo ""
echo "2. Comparing versions by package..."
./scripts/compare-versions.sh --by-package

# 3. Check for version mismatches
echo ""
echo "3. Checking for version mismatches..."
./scripts/compare-versions.sh --mismatches
if [ $? -ne 0 ]; then
  echo "⚠️  Version mismatches detected (review above)"
fi

# 4. Validate manifests
echo ""
echo "4. Validating package manifests..."
python3 -c "
import yaml
from pathlib import Path

issues = 0
for manifest in sorted(Path('packages').glob('*/manifest.yaml')):
  try:
    with open(manifest) as f:
      data = yaml.safe_load(f)
      required = ['name', 'version', 'description', 'author', 'license', 'artifacts']
      for field in required:
        if field not in data:
          print(f'❌ {manifest}: Missing field: {field}')
          issues += 1
        else:
          print(f'✅ {manifest}: {field}={data[field]}')
  except Exception as e:
    print(f'❌ {manifest}: Parse error - {e}')
    issues += 1

if issues > 0:
  print(f'\n❌ Found {issues} manifest issues')
  exit(1)
"

# 5. Check CHANGELOG files
echo ""
echo "5. Checking CHANGELOG files..."
for package in packages/*/; do
  PACKAGE_NAME=$(basename "$package")
  if [ -f "$package/CHANGELOG.md" ]; then
    echo "✅ CHANGELOG exists: $PACKAGE_NAME"
  else
    echo "⚠️  Missing CHANGELOG: $PACKAGE_NAME"
  fi
done

echo ""
echo "====== Validation Complete ======"
```

**Run with output capture:**

```bash
# Run validation and save results
./scripts/audit-versions.py --verbose > /tmp/release-validation.log 2>&1

# Check for failures
if grep -q "check(s) failed" /tmp/release-validation.log; then
  echo "❌ Validation failed - see log:"
  cat /tmp/release-validation.log
  exit 1
else
  echo "✅ Validation passed"
fi
```

### Step 6: GitHub Release Creation

**Using gh CLI:**

```bash
# Create release from tag
gh release create v0.5.0 \
  --title "Marketplace v0.5.0" \
  --notes "$(cat release-notes-0.5.0.md)"

# For packages
gh release create v0.5.0-sc-delay-tasks \
  --title "sc-delay-tasks v0.5.0" \
  --notes "$(head -30 packages/sc-delay-tasks/CHANGELOG.md)"
```

**Release Notes Format:**

```markdown
# Marketplace v0.5.0

## Overview

New registry format (v2.0.0), enhanced installer, and improved error handling.

## What's New

### Installer Improvements
- Faster package discovery
- Better error messages
- Automatic dependency checking

### Registry Format v2.0.0
- Enhanced metadata structure
- Backward compatibility with v1.x

### All Packages Updated

#### sc-delay-tasks v0.5.0
- New delay scheduler with persistent storage
- Support cron-like scheduling patterns
- Fix memory leak in polling loop (#38, #40)

**[View full CHANGELOG](https://github.com/randlee/synaptic-canvas/blob/main/packages/sc-delay-tasks/CHANGELOG.md)**

#### sc-git-worktree v0.4.0 (no changes)

#### sc-manage v0.4.0 (no changes)

#### sc-repomix-nuget v0.4.0 (no changes)

## Installation

```bash
# Install or update using sc-install
python3 tools/sc-install.py install <package> --dest ~/.claude
```

## Testing

All releases are automatically tested with:
- Version consistency audit
- Manifest validation
- Package installation tests

## Known Issues

None at this time.

## Contributors

@maintainer-name for this release

---

[Installation Guide](docs/registries/nuget/README.md) • [Versioning Policy](docs/versioning-strategy.md)
```

**Generate release notes from CHANGELOG:**

```bash
#!/bin/bash
# Extract release notes from CHANGELOG.md

PACKAGE=$1
VERSION=$2

# Extract section between version header and next version
sed -n "/^## \[$VERSION\]/,/^## \[/p" packages/$PACKAGE/CHANGELOG.md | head -n -1
```

**Create GitHub Release via Web UI:**

1. Navigate to https://github.com/randlee/synaptic-canvas/releases
2. Click "Draft a new release"
3. Select tag (v0.5.0)
4. Fill in title: "Marketplace v0.5.0"
5. Paste release notes
6. Set pre-release if applicable (for 0.x versions)
7. Click "Publish release"

### Step 7: Update Registry Metadata

**Registry file location:** `docs/registries/nuget/registry.json`

**Updates needed:**

```json
{
  "version": "2.0.0",
  "generated": "2025-12-15T14:30:00Z",
  "marketplace": {
    "version": "0.5.0",
    "lastUpdated": "2025-12-15"
  },
  "packages": {
    "sc-delay-tasks": {
      "version": "0.5.0",
      "lastUpdated": "2025-12-15"
    }
  }
}
```

**Script to update registry:**

```bash
#!/bin/bash
# Update registry metadata for release

PACKAGE=${1:-"all"}
VERSION=$2
REGISTRY="docs/registries/nuget/registry.json"

# Backup original
cp "$REGISTRY" "$REGISTRY.bak"

# Update timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Update using Python for JSON manipulation
python3 <<EOF
import json
from datetime import datetime

with open("$REGISTRY", "r") as f:
  registry = json.load(f)

# Update generated timestamp
registry["generated"] = "$TIMESTAMP"

# Update marketplace version if needed
if "$PACKAGE" == "marketplace" or "$PACKAGE" == "all":
  registry["marketplace"]["version"] = "$VERSION"
  registry["marketplace"]["lastUpdated"] = "$TIMESTAMP".split("T")[0]

# Update package version
if "$PACKAGE" != "marketplace":
  packages = "$PACKAGE".split(",")
  for pkg in packages:
    if pkg in registry["packages"]:
      registry["packages"][pkg]["version"] = "$VERSION"
      registry["packages"][pkg]["lastUpdated"] = "$TIMESTAMP".split("T")[0]

with open("$REGISTRY", "w") as f:
  json.dump(registry, f, indent=2)

print(f"✓ Updated {registry}")
EOF
```

**Verify registry is valid JSON:**

```bash
# Validate JSON syntax
python3 -m json.tool docs/registries/nuget/registry.json > /dev/null && echo "✓ Registry JSON is valid"

# Check specific entries
python3 -c "
import json
with open('docs/registries/nuget/registry.json') as f:
  reg = json.load(f)
  print(f'Marketplace: v{reg[\"marketplace\"][\"version\"]}')
  print(f'Packages: {len(reg[\"packages\"])}')
  for pkg, data in reg['packages'].items():
    print(f'  - {pkg}: v{data[\"version\"]}')
"
```

## Release Scenarios

### Scenario 1: Single Package Release

**Example:** Release only sc-delay-tasks v0.5.0 (marketplace stays 0.4.0)

**Steps:**

1. **Create release branch:**
   ```bash
   git checkout -b release/package-sc-delay-tasks-v0.5.0
   ```

2. **Update version:**
   ```bash
   python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.0
   ```

3. **Update CHANGELOG:**
   ```bash
   vi packages/sc-delay-tasks/CHANGELOG.md
   # Move [Unreleased] to [0.5.0] - 2025-12-15
   ```

4. **Commit:**
   ```bash
   git add packages/sc-delay-tasks/
   git commit -m "chore(sc-delay-tasks): release v0.5.0"
   ```

5. **Tag:**
   ```bash
   git tag -a v0.5.0-sc-delay-tasks -m "sc-delay-tasks v0.5.0"
   git push origin v0.5.0-sc-delay-tasks
   ```

6. **Create release:**
   ```bash
   gh release create v0.5.0-sc-delay-tasks --notes "$(head -30 packages/sc-delay-tasks/CHANGELOG.md)"
   ```

7. **Update registry:**
   ```bash
   # Update sc-delay-tasks entry to 0.5.0
   # Keep marketplace at 0.4.0
   ```

### Scenario 2: Marketplace Platform Release

**Example:** Release marketplace v0.5.0 with all packages

**Steps:**

1. **Create release branch:**
   ```bash
   git checkout -b release/marketplace-v0.5.0
   ```

2. **Update marketplace version:**
   ```bash
   vi version.yaml
   # Change version: "0.4.0" → version: "0.5.0"
   ```

3. **Update all packages (if needed):**
   ```bash
   python3 scripts/sync-versions.py --all --version 0.5.0
   ```

4. **Update all CHANGELOGs:**
   ```bash
   for pkg in packages/*/; do
     sed -i "s/## \[Unreleased\]/## [0.5.0] - $(date +%Y-%m-%d)/" "$pkg/CHANGELOG.md"
   done
   ```

5. **Validate all versions:**
   ```bash
   ./scripts/audit-versions.py --verbose
   ```

6. **Commit:**
   ```bash
   git add version.yaml packages/*/
   git commit -m "chore: release marketplace v0.5.0 with all packages"
   ```

7. **Tag:**
   ```bash
   git tag -a v0.5.0 -m "Marketplace v0.5.0 release"
   git push origin v0.5.0
   ```

8. **Create comprehensive release notes:**
   ```bash
   # Include all package changes
   # Reference marketplace-level improvements
   ```

### Scenario 3: All Packages Simultaneous Release

**Example:** Release sc-delay-tasks v0.5.0, sc-git-worktree v0.4.1, sc-repomix-nuget v0.5.0

**Note:** Marketplace version stays at 0.4.0

**Steps:**

1. **Create release branch:**
   ```bash
   git checkout -b release/packages-v0.5.0
   ```

2. **Update packages individually:**
   ```bash
   python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.0
   python3 scripts/sync-versions.py --package sc-git-worktree --version 0.4.1
   python3 scripts/sync-versions.py --package sc-repomix-nuget --version 0.5.0
   ```

3. **Update CHANGELOGs for each:**
   ```bash
   DATE=$(date +%Y-%m-%d)

   sed -i "s/## \[Unreleased\]/## [0.5.0] - $DATE/" packages/sc-delay-tasks/CHANGELOG.md
   sed -i "s/## \[Unreleased\]/## [0.4.1] - $DATE/" packages/sc-git-worktree/CHANGELOG.md
   sed -i "s/## \[Unreleased\]/## [0.5.0] - $DATE/" packages/sc-repomix-nuget/CHANGELOG.md
   ```

4. **Validate:**
   ```bash
   ./scripts/audit-versions.py --verbose
   ```

5. **Commit:**
   ```bash
   git add packages/*/
   git commit -m "chore: release multiple packages

- sc-delay-tasks v0.5.0 with new scheduler
- sc-git-worktree v0.4.1 with bugfixes
- sc-repomix-nuget v0.5.0 with enhancements"
   ```

6. **Create individual tags:**
   ```bash
   git tag -a v0.5.0-sc-delay-tasks -m "sc-delay-tasks v0.5.0"
   git tag -a v0.4.1-sc-git-worktree -m "sc-git-worktree v0.4.1"
   git tag -a v0.5.0-sc-repomix-nuget -m "sc-repomix-nuget v0.5.0"
   git push origin --tags
   ```

### Scenario 4: Patch/Hotfix Release

**Example:** Release patch v0.4.1 for sc-delay-tasks (critical bugfix)

**Steps:**

1. **Create patch branch from tag:**
   ```bash
   git checkout -b release/patch-sc-delay-tasks-v0.4.1 v0.4.0-sc-delay-tasks
   ```

2. **Apply bugfix commits:**
   ```bash
   # Cherry-pick fix commits from main
   git cherry-pick <commit-hash>

   # Or apply manually
   vi packages/sc-delay-tasks/scripts/delay-run.py
   git add packages/sc-delay-tasks/scripts/delay-run.py
   git commit -m "fix(sc-delay-tasks): correct memory leak in polling loop"
   ```

3. **Update to patch version:**
   ```bash
   python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.4.1
   ```

4. **Update CHANGELOG:**
   ```bash
   # Add [0.4.1] section with bugfix details
   vi packages/sc-delay-tasks/CHANGELOG.md
   ```

5. **Commit version bump:**
   ```bash
   git add packages/sc-delay-tasks/
   git commit -m "chore(sc-delay-tasks): bump to v0.4.1"
   ```

6. **Tag:**
   ```bash
   git tag -a v0.4.1-sc-delay-tasks -m "sc-delay-tasks v0.4.1 - Critical bugfix"
   git push origin release/patch-sc-delay-tasks-v0.4.1
   git push origin v0.4.1-sc-delay-tasks
   ```

7. **Create hotfix release notes:**
   ```bash
   gh release create v0.4.1-sc-delay-tasks \
     --prerelease \
     --title "sc-delay-tasks v0.4.1 - Critical Hotfix" \
     --notes "## Critical Bugfix

Fix for memory leak in polling loop affecting long-running delays.

**Affected:** v0.4.0 users
**Workaround:** None available; upgrade required
**Fix:** $(grep -A2 'v0.4.1' packages/sc-delay-tasks/CHANGELOG.md | tail -1)"
   ```

8. **Merge back to main:**
   ```bash
   # Create PR from patch branch to main
   git checkout main
   git pull origin main
   git merge release/patch-sc-delay-tasks-v0.4.1
   ```

## Post-Release Procedures

### Step 1: Verification Checks

**Verify GitHub Release Created:**

```bash
# List releases
gh release list --repo randlee/synaptic-canvas

# Verify specific release
gh release view v0.5.0

# Check release assets (if any)
gh release view v0.5.0 --json assets
```

**Verify Git Tags:**

```bash
# List tags
git tag -l "v*" | sort -V | tail -10

# Check tag details
git show v0.5.0

# Verify tag is signed (if applicable)
git verify-tag v0.5.0
```

**Verify Registry Updated:**

```bash
# Check registry.json is updated
grep '"version": "0.5.0"' docs/registries/nuget/registry.json

# Verify all expected packages listed
python3 -c "
import json
with open('docs/registries/nuget/registry.json') as f:
  reg = json.load(f)
  for pkg, data in reg['packages'].items():
    print(f'{pkg}: v{data[\"version\"]} (updated {data[\"lastUpdated\"]})')
"
```

### Step 2: Installation and Functionality Tests

**Test Package Installation:**

```bash
#!/bin/bash
# Post-release installation verification

PACKAGE=$1
TEST_DIR="/tmp/post-release-test-$PACKAGE-$$"

echo "Testing $PACKAGE installation..."

# Create test directory
mkdir -p "$TEST_DIR/.claude"

# Install package
python3 tools/sc-install.py install "$PACKAGE" --dest "$TEST_DIR/.claude"

if [ $? -ne 0 ]; then
  echo "❌ Installation failed"
  exit 1
fi

# Verify commands installed
if [ -d "$TEST_DIR/.claude/commands" ]; then
  echo "✅ Commands installed: $(ls -1 $TEST_DIR/.claude/commands/*.md | wc -l)"
else
  echo "⚠️  No commands found"
fi

# Verify agents installed
if [ -d "$TEST_DIR/.claude/agents" ]; then
  echo "✅ Agents installed: $(ls -1 $TEST_DIR/.claude/agents/*.md | wc -l)"
else
  echo "⚠️  No agents found"
fi

# Check artifact versions
echo "Checking artifact versions..."
for artifact in $TEST_DIR/.claude/agents/*.md; do
  VERSION=$(grep "^version:" "$artifact" | head -1 | cut -d'"' -f2)
  echo "  - $(basename $artifact): v$VERSION"
done

# Cleanup
rm -rf "$TEST_DIR"

echo "✓ Post-release verification complete"
```

**Test from Public Registry:**

```bash
# Test installation using published registry
python3 tools/sc-install.py install sc-delay-tasks \
  --registry https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registries/nuget/registry.json \
  --dest /tmp/test-public

# Verify success
if [ -d /tmp/test-public/.claude/agents ]; then
  echo "✓ Public registry installation successful"
else
  echo "❌ Public registry installation failed"
fi
```

**Smoke Tests for Each Artifact:**

```bash
#!/bin/bash
# Smoke tests for installed artifacts

TEST_DIR=$1

echo "Running smoke tests..."

# Test command help
if [ -f "$TEST_DIR/.claude/commands/delay.md" ]; then
  echo "✓ delay command found"
else
  echo "✗ delay command missing"
fi

# Test agent availability
for agent in delay-once delay-poll git-pr-check-delay; do
  if [ -f "$TEST_DIR/.claude/agents/${agent}.md" ]; then
    echo "✓ $agent agent found"
  else
    echo "✗ $agent agent missing"
  fi
done

# Test skill availability
if [ -f "$TEST_DIR/.claude/skills/delaying-tasks/SKILL.md" ]; then
  echo "✓ delaying-tasks skill found"
else
  echo "✗ delaying-tasks skill missing"
fi
```

### Step 3: Announcement Procedures

**Create Release Announcement:**

```markdown
# Release Announcement: Synaptic Canvas v0.5.0

**Release Date:** December 15, 2025
**Type:** Marketplace Platform Release
**Status:** Beta

## What's Included

### Marketplace Platform v0.5.0
- Enhanced installer with faster discovery
- Registry format v2.0.0 with improved metadata
- Better error messages and diagnostics

### Package Updates
- **sc-delay-tasks v0.5.0** - New persistent scheduler
- **sc-git-worktree v0.4.0** - No changes
- **sc-manage v0.4.0** - No changes
- **sc-repomix-nuget v0.4.0** - No changes

## Installation

```bash
python3 tools/sc-install.py install sc-delay-tasks --dest ~/.claude
```

## Documentation

- [Release Notes](https://github.com/randlee/synaptic-canvas/releases/tag/v0.5.0)
- [Installation Guide](docs/registries/nuget/README.md)
- [Changelog](packages/sc-delay-tasks/CHANGELOG.md)

## Known Issues

None reported.

## Feedback

Please report issues or suggestions to:
- [GitHub Issues](https://github.com/randlee/synaptic-canvas/issues)
- [GitHub Discussions](https://github.com/randlee/synaptic-canvas/discussions)
```

**Post to README (if significant release):**

```markdown
## Latest Release

**[v0.5.0](https://github.com/randlee/synaptic-canvas/releases/tag/v0.5.0)** - December 15, 2025

Enhanced installer and new registry format. See [release notes](https://github.com/randlee/synaptic-canvas/releases/tag/v0.5.0) for details.
```

**Notify Users:**

- Update GitHub releases page with clear release notes
- Update README.md with latest version
- Update registry.json with release metadata
- (Optional) Post to project discussions/forums

### Step 4: Monitor for Issues

**Immediate Post-Release Monitoring (first 24 hours):**

```bash
#!/bin/bash
# Monitor for post-release issues

echo "Monitoring for post-release issues..."

# Check GitHub issues
echo ""
echo "Recent issues:"
gh issue list --repo randlee/synaptic-canvas --limit 5 --state open

# Check discussions
echo ""
echo "Recent discussions:"
gh discussion list --repo randlee/synaptic-canvas --limit 3

# Monitor CI pipeline
echo ""
echo "Workflow status:"
gh run list --repo randlee/synaptic-canvas --limit 3 --json "name,status,conclusion"
```

**Escalation Procedure:**

```
If critical issue found within 24 hours:

1. Severity Assessment
   - Critical (users cannot use): Immediate hotfix required
   - Major (some features broken): Hotfix within 24 hours
   - Minor (workaround exists): Include in next release

2. Create Emergency Issue
   - Title: "[CRITICAL] <issue description>"
   - Add to milestone: "<version> Hotfix"
   - Assign to release manager

3. Hotfix Process
   - Branch from tag: git checkout -b hotfix/<issue> v0.5.0
   - Apply fix and test
   - Tag as v0.5.1
   - Release to registry immediately
   - Announce hotfix

4. Post-Mortem
   - Document root cause
   - Add testing to prevent recurrence
   - Update release checklist if needed
```

## Rollback and Incident Procedures

### Scenario: Critical Issue Detected Post-Release

**Example:** sc-delay-tasks v0.5.0 has memory leak affecting all users

**Immediate Actions:**

1. **Assess impact:**
   ```bash
   # Determine scope
   - How many users affected?
   - Is there a workaround?
   - Can users revert to v0.4.0?
   ```

2. **Escalate:**
   ```bash
   # Create critical issue
   gh issue create \
     --title "CRITICAL: Memory leak in sc-delay-tasks v0.5.0" \
     --body "All polling operations leak memory. Revert to v0.4.0 or apply hotfix.

   Impact: High - all polling users affected
   Workaround: Use v0.4.0 delay-poll agent
   Timeline: Hotfix required within 4 hours" \
     --label "critical,bug"
   ```

3. **Notify users immediately:**
   ```markdown
   # CRITICAL ALERT: sc-delay-tasks v0.5.0

   A memory leak has been discovered in sc-delay-tasks v0.5.0.

   **Workaround:** Revert to v0.4.0 using:
   ```bash
   python3 tools/sc-install.py uninstall sc-delay-tasks
   python3 tools/sc-install.py install sc-delay-tasks --version 0.4.0
   ```

   **Status:** Hotfix v0.5.1 in progress
   **ETA:** 2 hours

   See GitHub issue #NNN for updates.
   ```

### Rollback Procedure

**Option 1: Revert to Previous Release (if critical):**

```bash
# Revert the release commit
git revert <release-commit-hash> --no-edit

# Create rollback tag
git tag -a v0.5.0-rollback -m "Rollback: sc-delay-tasks v0.5.0 - Memory leak in polling"

# Push rollback
git push origin main
git push origin v0.5.0-rollback

# Announce rollback
gh issue comment <issue-number> \
  --body "v0.5.0 has been rolled back. Use v0.4.0 until hotfix v0.5.1 is released."
```

**Option 2: Quick Hotfix (preferred):**

```bash
# Create hotfix branch from tag
git checkout -b hotfix/sc-delay-tasks-memory-leak v0.5.0-sc-delay-tasks

# Apply fix
vi packages/sc-delay-tasks/scripts/delay-run.py
# Fix the memory leak

# Test fix
./scripts/audit-versions.py
python3 -m pytest tests/sc-delay-tasks/ -v

# Update version to 0.5.1
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.1

# Update CHANGELOG
vi packages/sc-delay-tasks/CHANGELOG.md
# Add [0.5.1] - 2025-12-15 with fix details

# Commit and tag
git add packages/sc-delay-tasks/
git commit -m "fix(sc-delay-tasks): memory leak in polling loop (v0.5.1)"
git tag -a v0.5.1-sc-delay-tasks -m "sc-delay-tasks v0.5.1 - Critical bugfix"

# Push
git push origin hotfix/sc-delay-tasks-memory-leak
git push origin v0.5.1-sc-delay-tasks

# Create hotfix release
gh release create v0.5.1-sc-delay-tasks \
  --prerelease \
  --title "sc-delay-tasks v0.5.1 - Critical Hotfix" \
  --notes "## Memory Leak Fix

Fixed critical memory leak in polling operations affecting v0.5.0 users.

**Upgrade immediately if using v0.5.0 polling features.**

See CHANGELOG.md for details."

# Update registry
# Update sc-delay-tasks entry to 0.5.1
```

### Retract a Release (Nuclear Option)

**When to retract:**
- Release pushed without testing (should not happen!)
- Contains sensitive information accidentally committed
- Completely broken and no fix available
- Legal/compliance issue

**Retraction procedure:**

```bash
# Step 1: Delete tag
git tag -d v0.5.0-sc-delay-tasks
git push origin :refs/tags/v0.5.0-sc-delay-tasks

# Step 2: Delete GitHub release
gh release delete v0.5.0-sc-delay-tasks --yes

# Step 3: Revert commit
git revert <release-commit-hash>
git push origin main

# Step 4: Publish announcement
gh issue create \
  --title "Release Retracted: sc-delay-tasks v0.5.0" \
  --body "## Retraction Notice

sc-delay-tasks v0.5.0 has been retracted due to [critical issue].

**Action Required:**
- Do not install v0.5.0
- If already installed, revert to v0.4.0:

\`\`\`bash
python3 tools/sc-install.py uninstall sc-delay-tasks
python3 tools/sc-install.py install sc-delay-tasks --version 0.4.0
\`\`\`

**Updated Version:** v0.5.1 will be released on [date]

We apologize for the inconvenience." \
  --label "critical,release"
```

### Post-Incident Review

**After resolving critical issue:**

```bash
#!/bin/bash
# Post-incident review template

cat > /tmp/incident-review.md <<'EOF'
# Incident Review: sc-delay-tasks v0.5.0 Memory Leak

## Incident Summary
- **Severity:** Critical
- **Duration:** 2 hours (discovery to hotfix release)
- **Users Affected:** ~X users with v0.5.0 installed
- **Root Cause:** Uncleared list in polling loop accumulating references

## Timeline
- 14:30 - v0.5.0 released
- 15:15 - First user report of memory leak
- 15:30 - Confirmed critical issue
- 16:00 - Fix deployed as v0.5.1
- 16:15 - All users notified

## Root Cause
Polling loop's results list was not being cleared between iterations, causing memory to grow indefinitely.

```python
# Bug (v0.5.0)
while True:
  results.append(check_status())  # Results never cleared!

# Fix (v0.5.1)
while True:
  results = []  # Clear each iteration
  results.append(check_status())
```

## Preventive Measures
1. Add memory tests to CI pipeline
2. Add long-running polling tests (>30 minutes)
3. Require code review for polling logic changes
4. Add memory profiling to release checklist

## Action Items
- [ ] Add memory test to CI: scripts/test-memory.py
- [ ] Update release checklist: Section 5.3 add memory tests
- [ ] Add 1-hour polling test to test suite
- [ ] Code review guidelines: flag long-running allocations
- [ ] Follow up: Verify no similar issues in other agents

EOF

echo "Incident review created. Please complete action items."
```

## Command Reference

### Version Management Scripts

**Audit versions:**
```bash
./scripts/audit-versions.py --verbose
```

**Compare versions:**
```bash
./scripts/compare-versions.sh --by-package
./scripts/compare-versions.sh --mismatches
```

**Sync versions:**
```bash
python3 scripts/sync-versions.py --package <name> --version <version>
python3 scripts/sync-versions.py --all --version <version>
python3 scripts/sync-versions.py --marketplace --version <version>
python3 scripts/sync-versions.py --package <name> --version <version> --dry-run
```

### Git Commands

**Create and manage branches:**
```bash
git checkout -b release/marketplace-v0.5.0
git push origin release/marketplace-v0.5.0
```

**Tag releases:**
```bash
git tag -a v0.5.0 -m "Release message"
git push origin v0.5.0
git show v0.5.0
git tag -d v0.5.0  # Delete local tag
git push origin :refs/tags/v0.5.0  # Delete remote tag
```

### GitHub CLI Commands

**Manage releases:**
```bash
gh release create v0.5.0 --title "Title" --notes "Release notes"
gh release list --repo randlee/synaptic-canvas
gh release view v0.5.0
gh release delete v0.5.0 --yes
```

**Manage issues:**
```bash
gh issue create --title "Title" --body "Description" --label "critical"
gh issue list --state open --label "release"
gh issue comment <number> --body "Comment text"
```

### Package Installation Commands

**Install packages:**
```bash
python3 tools/sc-install.py install <package> --dest ~/.claude
python3 tools/sc-install.py install <package> --version 0.4.0 --dest ~/.claude
```

**Uninstall packages:**
```bash
python3 tools/sc-install.py uninstall <package> --dest ~/.claude
```

**List packages:**
```bash
python3 tools/sc-install.py list
python3 tools/sc-install.py info <package>
```

## Appendix: Release Checklist Template

### Release Checklist - [Package Name] v[Version]

**Pre-Release (1 day before):**
- [ ] Version number reviewed and approved
- [ ] CHANGELOG.md updated and reviewed
- [ ] Documentation updated
- [ ] Registry metadata prepared
- [ ] Automated tests passing
- [ ] Manual smoke tests completed

**Release Day:**
- [ ] Create release branch
- [ ] Update version numbers
- [ ] Run audit scripts - all passing
- [ ] Commit changes
- [ ] Create git tag
- [ ] Create GitHub release with notes
- [ ] Update registry.json
- [ ] Verify registry JSON validity

**Post-Release (2 hours after):**
- [ ] Installation test successful
- [ ] Artifacts verify correctly
- [ ] No critical issues reported
- [ ] Close related issues (if any)
- [ ] Update README.md if major release

**Post-Release (24 hours after):**
- [ ] No critical issues reported
- [ ] Monitor GitHub issues/discussions
- [ ] Confirm user feedback positive
- [ ] Document any learnings

---

## References

- [Versioning Strategy](docs/versioning-strategy.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Package Registry Format](docs/registries/nuget/README.md)
- [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
- [Semantic Versioning](https://semver.org/)
