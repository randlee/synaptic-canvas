# Diagnostic Tools Reference Guide

**Version:** 0.4.0
**Last Updated:** 2025-12-02
**Repository:** [synaptic-canvas](https://github.com/randlee/synaptic-canvas)

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Available Tools](#available-tools)
3. [Installation Diagnostics](#installation-diagnostics)
4. [Version Diagnostics](#version-diagnostics)
5. [Registry Diagnostics](#registry-diagnostics)
6. [Package Diagnostics](#package-diagnostics)
7. [Integration Diagnostics](#integration-diagnostics)
8. [Performance Diagnostics](#performance-diagnostics)
9. [Environment Diagnostics](#environment-diagnostics)
10. [JSON Output Examples](#json-output-examples)
11. [Troubleshooting Diagnostic Issues](#troubleshooting-diagnostic-issues)
12. [Creating Custom Diagnostics](#creating-custom-diagnostics)

---

## Quick Start

### Most Common Diagnostic Commands

```bash
# Quick system health check
./scripts/audit-versions.sh

# Compare versions across packages
./scripts/compare-versions.sh

# Validate registry integrity
python3 docs/registries/nuget/validate-registry.py

# Check Git version
git --version

# Check Python version
python3 --version

# Check Node.js version (for repomix-nuget)
node --version
npm --version
```

### First-Time Setup Verification

```bash
# 1. Verify Git is installed and version is sufficient
git --version  # Should be >= 2.7.0

# 2. Verify Python 3 is installed
python3 --version  # Should be >= 3.6

# 3. Check repository is cloned properly
git status
git remote -v

# 4. Run comprehensive version audit
./scripts/audit-versions.sh --verbose

# 5. Validate registry
python3 docs/registries/nuget/validate-registry.py --verbose
```

---

## Available Tools

### Core Diagnostic Scripts

#### 1. `scripts/audit-versions.sh`

**Purpose:** Verify version consistency across packages and artifacts

**Location:** `/Users/randlee/Documents/github/synaptic-canvas/scripts/audit-versions.sh`

**Usage:**
```bash
./scripts/audit-versions.sh [OPTIONS]

Options:
  --verbose        Show all checks (including passing checks)
  --fix-warnings   Attempt to fix non-critical issues
```

**What It Checks:**
- ✅ All commands have version frontmatter
- ✅ All skills have version frontmatter
- ✅ All agents have version frontmatter
- ✅ Artifact versions match package manifest versions
- ✅ CHANGELOG files exist for all packages
- ✅ Marketplace version exists and is valid

**Example Output (Success):**

```bash
$ ./scripts/audit-versions.sh

=== Synaptic Canvas Version Audit ===

Checking commands...
Checking skills...
Checking agents...
Checking version consistency...
Checking CHANGELOGs...
Checking marketplace version...

=== Audit Results ===
Total checks: 42
Passed: 42
Failed: 0
Warnings: 0

All checks passed!
```

**Example Output (With Errors):**

```bash
$ ./scripts/audit-versions.sh

=== Synaptic Canvas Version Audit ===

Checking commands...
✗ FAIL Command: delay: Missing version frontmatter

Checking skills...
Checking agents...
Checking version consistency...
✗ FAIL Command in delay-tasks: Version mismatch: command=0.3.0, package=0.4.0

Checking CHANGELOGs...
⚠ WARN CHANGELOG for repomix-nuget: No CHANGELOG.md found

Checking marketplace version...

=== Audit Results ===
Total checks: 42
Passed: 38
Failed: 2
Warnings: 1

2 check(s) failed
```

**Exit Codes:**
- `0` - All checks passed
- `1` - Mismatches or missing versions found
- `2` - Critical errors (script failure)

**Common Issues:**

❌ **Missing version frontmatter:**
```
✗ FAIL Command: delay: Missing version frontmatter
```
**Fix:** Add version frontmatter to the command file:
```yaml
---
name: delay
description: Schedule delayed tasks
version: 0.4.0
---
```

❌ **Version mismatch:**
```
✗ FAIL Command in delay-tasks: Version mismatch: command=0.3.0, package=0.4.0
```
**Fix:** Use sync-versions.py to update:
```bash
python3 scripts/sync-versions.py --package delay-tasks --version 0.4.0
```

⚠️ **Missing CHANGELOG:**
```
⚠ WARN CHANGELOG for repomix-nuget: No CHANGELOG.md found
```
**Fix:** Create CHANGELOG.md in package directory following template.

---

#### 2. `scripts/sync-versions.py`

**Purpose:** Synchronize version numbers across package artifacts

**Location:** `/Users/randlee/Documents/github/synaptic-canvas/scripts/sync-versions.py`

**Usage:**
```bash
python3 scripts/sync-versions.py [OPTIONS]

Required:
  --version VERSION    Target version (SemVer: X.Y.Z)

Scope (choose one):
  --package NAME       Update version for specific package
  --marketplace        Update marketplace platform version (version.yaml)
  --all                Update all packages to same version

Options:
  --commit             Create git commit after update
  --dry-run            Show changes without applying
```

**Examples:**

**Update single package:**
```bash
# Update delay-tasks to version 0.5.0
python3 scripts/sync-versions.py --package delay-tasks --version 0.5.0

# Output:
Syncing delay-tasks to version 0.5.0...
  ✓ Updated: /path/to/packages/delay-tasks/manifest.yaml
  ✓ Updated: /path/to/packages/delay-tasks/commands/delay.md
  ✓ Updated: /path/to/packages/delay-tasks/skills/delaying-tasks/SKILL.md
  ✓ Updated: /path/to/packages/delay-tasks/agents/delay-once.md
  ✓ Updated: /path/to/packages/delay-tasks/agents/delay-poll.md
  ✓ Updated: /path/to/packages/delay-tasks/agents/git-pr-check-delay.md
Updated 6 file(s) in delay-tasks
```

**Update marketplace version:**
```bash
# Update marketplace platform version
python3 scripts/sync-versions.py --marketplace --version 0.5.0

# Output:
Syncing marketplace to version 0.5.0...
  ✓ Updated: /path/to/version.yaml
```

**Update all packages (rare):**
```bash
# Update ALL packages to version 1.0.0 (major release)
python3 scripts/sync-versions.py --all --version 1.0.0

# Output:
Syncing all packages to version 1.0.0...
Syncing delay-tasks to version 1.0.0...
  ✓ Updated: /path/to/packages/delay-tasks/manifest.yaml
  ...
Syncing git-worktree to version 1.0.0...
  ✓ Updated: /path/to/packages/git-worktree/manifest.yaml
  ...
```

**Dry run (preview changes):**
```bash
python3 scripts/sync-versions.py --package delay-tasks --version 0.5.0 --dry-run

# Shows what would be updated without making changes
```

**With automatic commit:**
```bash
python3 scripts/sync-versions.py --package delay-tasks --version 0.5.0 --commit

# Output:
Syncing delay-tasks to version 0.5.0...
  ✓ Updated: ...
Updated 6 file(s) in delay-tasks
✓ Created git commit: chore(versioning): sync versions across artifacts
```

**Exit Codes:**
- `0` - Success
- `1` - Validation error or update failure

**Validation:**

The script validates version format before updating:

```bash
# Invalid version format
python3 scripts/sync-versions.py --package delay-tasks --version 1.0

# Error:
Error: Invalid version format: 1.0
Must be semantic version (X.Y.Z)
```

**What It Updates:**

For package updates:
- ✅ `packages/<name>/manifest.yaml`
- ✅ `packages/<name>/commands/*.md` (version frontmatter)
- ✅ `packages/<name>/skills/*/SKILL.md` (version frontmatter)
- ✅ `packages/<name>/agents/*.md` (version frontmatter)

For marketplace updates:
- ✅ `version.yaml`

**Version Format:**

Must be semantic version (SemVer):
- ✅ Valid: `0.4.0`, `1.0.0`, `2.1.3`
- ❌ Invalid: `0.4`, `v0.4.0`, `1.0.0-beta` (pre-release tags not supported)

---

#### 3. `scripts/compare-versions.sh`

**Purpose:** Compare version numbers across packages and display discrepancies

**Location:** `/Users/randlee/Documents/github/synaptic-canvas/scripts/compare-versions.sh`

**Usage:**
```bash
./scripts/compare-versions.sh [OPTIONS]

Options:
  --by-package    Show versions grouped by package (default)
  --mismatches    Only show packages with version mismatches
  --verbose       Show all artifact versions individually
  --json          Output as JSON
```

**Examples:**

**Basic comparison:**
```bash
./scripts/compare-versions.sh

# Output:
=== Synaptic Canvas Version Comparison ===

Marketplace Version: 0.4.0

Package: delay-tasks (manifest: 0.4.0)

Package: git-worktree (manifest: 0.4.0)

Package: sc-manage (manifest: 0.4.0)

Package: repomix-nuget (manifest: 0.4.0)

All versions consistent!
```

**Show only mismatches:**
```bash
./scripts/compare-versions.sh --mismatches

# Output:
=== Synaptic Canvas Version Comparison ===

Marketplace Version: 0.4.0

Package: delay-tasks (manifest: 0.4.0)

(No other output if all versions consistent)
```

**Verbose output (show all artifacts):**
```bash
./scripts/compare-versions.sh --verbose

# Output:
=== Synaptic Canvas Version Comparison ===

Marketplace Version: 0.4.0

Package: delay-tasks (manifest: 0.4.0)
  ✓ command/delay: 0.4.0
  ✓ skill/delaying-tasks: 0.4.0
  ✓ agent/delay-once: 0.4.0
  ✓ agent/delay-poll: 0.4.0
  ✓ agent/git-pr-check-delay: 0.4.0

Package: git-worktree (manifest: 0.4.0)
  ✓ command/git-worktree: 0.4.0
  ✓ skill/managing-worktrees: 0.4.0
  ✓ agent/worktree-create: 0.4.0
  ✓ agent/worktree-scan: 0.4.0
  ✓ agent/worktree-cleanup: 0.4.0
  ✓ agent/worktree-abort: 0.4.0

...

All versions consistent!
```

**With version mismatches:**
```bash
./scripts/compare-versions.sh --verbose

# Output:
=== Synaptic Canvas Version Comparison ===

Marketplace Version: 0.4.0

Package: delay-tasks (manifest: 0.4.0)
  ✓ command/delay: 0.4.0
  ✗ skill/delaying-tasks: 0.3.0
  ✓ agent/delay-once: 0.4.0

Package: git-worktree (manifest: 0.4.0)
  ✓ command/git-worktree: 0.4.0

Version mismatches found
```

**JSON output:**
```bash
./scripts/compare-versions.sh --json

# Output:
{
  "marketplace": "0.4.0",
  "packages": [
    {"name": "delay-tasks", "version": "0.4.0", "consistent": true},
    {"name": "git-worktree", "version": "0.4.0", "consistent": true},
    {"name": "sc-manage", "version": "0.4.0", "consistent": true},
    {"name": "repomix-nuget", "version": "0.4.0", "consistent": true}
  ]
}
```

**Exit Codes:**
- `0` - All versions consistent
- `1` - Mismatches found

**Use Cases:**

- 📋 Pre-release version audit
- 🔍 Quick version consistency check
- 🤖 CI/CD pipeline validation
- 📊 Version reporting for documentation

---

#### 4. `docs/registries/nuget/validate-registry.py`

**Purpose:** Validate package registry against JSON Schema

**Location:** `/Users/randlee/Documents/github/synaptic-canvas/docs/registries/nuget/validate-registry.py`

**Usage:**
```bash
python3 docs/registries/nuget/validate-registry.py [OPTIONS]

Options:
  --registry PATH    Path to registry.json file (default: docs/registries/nuget/registry.json)
  --schema PATH      Path to schema file (default: docs/registries/nuget/registry.schema.json)
  --verbose, -v      Verbose output
  --json             Output validation result as JSON
```

**Examples:**

**Basic validation:**
```bash
python3 docs/registries/nuget/validate-registry.py

# Output:
======================================================================
SYNAPTIC CANVAS REGISTRY VALIDATION REPORT
======================================================================

Registry Version: 0.4.0
Generated: 2025-12-02T10:25:00Z
Packages: 4
Repository: randlee/synaptic-canvas

----------------------------------------------------------------------
STATUS: VALID
----------------------------------------------------------------------

All validation checks passed!

Registry Statistics:
  Total Packages: 4
  Total Commands: 4
  Total Skills: 6
  Total Agents: 16
  Total Scripts: 2

Categories: 5
  - automation: 1 package(s)
  - git: 1 package(s)
  - management: 1 package(s)
  - nuget: 1 package(s)
  - workflow: 2 package(s)

======================================================================
```

**With validation errors:**
```bash
python3 docs/registries/nuget/validate-registry.py

# Output:
======================================================================
SYNAPTIC CANVAS REGISTRY VALIDATION REPORT
======================================================================

Registry Version: 0.4.0
Generated: 2025-12-02T10:25:00Z
Packages: 4
Repository: randlee/synaptic-canvas

----------------------------------------------------------------------
STATUS: INVALID
----------------------------------------------------------------------

Found 3 validation error(s):

  1. Package 'delay-tasks': Invalid version format '0.4'
  2. Package 'git-worktree': Missing required field: 'description'
  3. Package 'repomix-nuget': Invalid repo URL (must be https://github.com/...)

======================================================================
```

**Verbose output:**
```bash
python3 docs/registries/nuget/validate-registry.py --verbose

# Shows additional validation details
```

**JSON output (for CI/CD):**
```bash
python3 docs/registries/nuget/validate-registry.py --json

# Output:
{
  "valid": true,
  "error_count": 0,
  "errors": [],
  "registry": {
    "version": "0.4.0",
    "packages": 4,
    "generated": "2025-12-02T10:25:00Z"
  }
}
```

**With errors (JSON):**
```bash
python3 docs/registries/nuget/validate-registry.py --json

# Output:
{
  "valid": false,
  "error_count": 2,
  "errors": [
    "Package 'delay-tasks': Invalid version format '0.4'",
    "Package 'git-worktree': Missing required field: 'description'"
  ],
  "registry": {
    "version": "0.4.0",
    "packages": 4,
    "generated": "2025-12-02T10:25:00Z"
  }
}
```

**Exit Codes:**
- `0` - Registry is valid
- `1` - Validation errors found

**What It Validates:**

**Root Level:**
- ✅ Required fields present (`$schema`, `version`, `generated`, `repo`, etc.)
- ✅ Version format is valid SemVer
- ✅ Generated timestamp is valid ISO 8601

**Packages:**
- ✅ Package name format (lowercase with hyphens)
- ✅ Required fields (`name`, `version`, `description`, etc.)
- ✅ Version format (SemVer)
- ✅ Status enum values (`alpha`, `beta`, `stable`, `deprecated`, `archived`)
- ✅ Tier range (0-5)
- ✅ URL formats (GitHub URLs)
- ✅ Tags format and count (minimum 1 tag)
- ✅ Artifacts structure and counts

**Metadata:**
- ✅ Registry version format
- ✅ Schema version format
- ✅ Statistics accuracy

**Common Validation Errors:**

❌ **Invalid version format:**
```
Package 'delay-tasks': Invalid version format '0.4'
```
**Fix:** Use three-part SemVer: `0.4.0`

❌ **Invalid package name:**
```
Invalid package name: 'DelayTasks' (must be lowercase with hyphens)
```
**Fix:** Use lowercase with hyphens: `delay-tasks`

❌ **Invalid status:**
```
Package 'delay-tasks': Invalid status 'production'
```
**Fix:** Use valid status: `alpha`, `beta`, `stable`, `deprecated`, or `archived`

❌ **Invalid tier:**
```
Package 'delay-tasks': Tier must be integer 0-5, got 10
```
**Fix:** Use tier between 0-5

❌ **Invalid URL:**
```
Package 'delay-tasks': Invalid repo URL (must be https://github.com/...)
```
**Fix:** Use proper GitHub URL format

❌ **Missing tags:**
```
Package 'delay-tasks': 'tags' must have at least 1 item
```
**Fix:** Add at least one tag to the package

---

### System Verification Commands

#### Git Version Check

**Check Git installation:**
```bash
git --version

# Expected output:
git version 2.39.0 (Apple Git-145)
```

**Minimum version required:** `2.7.0` (for worktree support)

**Version comparison:**
```bash
# Check if Git version is sufficient for worktrees
git_version=$(git --version | awk '{print $3}')
required_version="2.7.0"

# Compare versions (simplified)
if [[ "$(printf '%s\n' "$required_version" "$git_version" | sort -V | head -n1)" = "$required_version" ]]; then
    echo "✓ Git version is sufficient ($git_version >= $required_version)"
else
    echo "✗ Git version too old ($git_version < $required_version)"
fi
```

**Platform-specific Git versions:**

- **macOS:** Apple Git or Homebrew Git
  ```bash
  git --version  # Apple Git
  /usr/local/bin/git --version  # Homebrew Git
  ```

- **Linux:** System package manager
  ```bash
  git --version
  which git  # /usr/bin/git
  ```

- **Windows:** Git for Windows or WSL
  ```bash
  git --version  # Git for Windows
  # In WSL:
  git --version
  ```

---

#### Python Version Check

**Check Python 3 installation:**
```bash
python3 --version

# Expected output:
Python 3.11.5
```

**Minimum version required:** `3.6` (most scripts), `3.8` recommended

**Check Python location:**
```bash
which python3

# Expected output:
/usr/bin/python3  # System Python
# or
/usr/local/bin/python3  # Homebrew Python
# or
~/.pyenv/shims/python3  # pyenv Python
```

**Check multiple Python versions:**
```bash
# Check all available Python versions
python --version 2>/dev/null || echo "python not available"
python3 --version 2>/dev/null || echo "python3 not available"
python3.11 --version 2>/dev/null || echo "python3.11 not available"
```

**Verify Python can run scripts:**
```bash
python3 -c "import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"

# Output:
Python 3.11.5
```

**Check Python packages (if needed):**
```bash
# Check if specific packages are available
python3 -c "import json; print('json: OK')"
python3 -c "import re; print('re: OK')"
python3 -c "import pathlib; print('pathlib: OK')"

# Check optional packages
python3 -c "import jsonschema; print('jsonschema: OK')" 2>/dev/null || echo "jsonschema: NOT INSTALLED (optional)"
```

---

#### Node.js and npm Version Check

**Required for:** `repomix-nuget` package

**Check Node.js installation:**
```bash
node --version

# Expected output:
v18.17.0
```

**Minimum version required:** `18.0.0`

**Check npm installation:**
```bash
npm --version

# Expected output:
9.6.7
```

**Check Node.js location:**
```bash
which node

# Expected output:
/usr/local/bin/node  # Homebrew Node
# or
~/.nvm/versions/node/v18.17.0/bin/node  # nvm Node
```

**Verify Node.js can run:**
```bash
node -e "console.log('Node.js version:', process.version)"

# Output:
Node.js version: v18.17.0
```

**Check global npm packages:**
```bash
npm list -g --depth=0

# Shows globally installed packages
```

**Check npm configuration:**
```bash
npm config list

# Shows npm configuration
```

**Version compatibility check:**
```bash
# Check if Node.js version is sufficient
node_version=$(node --version | sed 's/v//')
required_version="18.0.0"

# Simple comparison (requires bc or awk)
if [[ "$(printf '%s\n' "$required_version" "$node_version" | sort -V | head -n1)" = "$required_version" ]]; then
    echo "✓ Node.js version is sufficient ($node_version >= $required_version)"
else
    echo "✗ Node.js version too old ($node_version < $required_version)"
fi
```

---

## Installation Diagnostics

### Verify Repository Clone

**Check repository is properly cloned:**
```bash
# Check Git repository status
git status

# Expected output:
On branch main
Your branch is up to date with 'origin/main'.

nothing to commit, working tree clean
```

**Verify remote configuration:**
```bash
git remote -v

# Expected output:
origin  https://github.com/randlee/synaptic-canvas.git (fetch)
origin  https://github.com/randlee/synaptic-canvas.git (push)
```

**Check repository structure:**
```bash
# Verify key directories exist
ls -d packages/ scripts/ docs/ .claude/

# Expected output:
packages/  scripts/  docs/  .claude/
```

**Verify all packages are present:**
```bash
ls packages/

# Expected output:
delay-tasks/  git-worktree/  repomix-nuget/  sc-manage/
```

---

### Verify Package Installation

**Check if packages are installed locally:**
```bash
# Check .claude directory exists
ls -la .claude/

# Expected subdirectories:
commands/  skills/  agents/  scripts/
```

**Check installed commands:**
```bash
ls .claude/commands/

# Example output:
delay.md  git-worktree.md  repomix-nuget.md  sc-manage.md
```

**Check installed skills:**
```bash
ls .claude/skills/

# Example output:
delaying-tasks/  managing-worktrees/  managing-sc-packages/  generating-nuget-context/
```

**Check installed agents:**
```bash
ls .claude/agents/

# Example output:
delay-once.md  delay-poll.md  git-pr-check-delay.md  worktree-create.md  ...
```

**Check installed scripts:**
```bash
ls .claude/scripts/

# Example output:
delay-run.py  generate.sh  validate-registry.sh
```

---

### Verify File Permissions

**Check script execute permissions:**
```bash
# Check audit script
ls -l scripts/audit-versions.sh

# Expected output:
-rwxr-xr-x  1 user  staff  6045 Dec  2 09:22 scripts/audit-versions.sh
#  ^^^  - Should have execute permission (x)
```

**Check all scripts have execute permissions:**
```bash
find scripts/ -name "*.sh" -type f ! -perm -u+x

# Expected: No output (all scripts should be executable)
# If output exists, those scripts need execute permission
```

**Fix missing execute permissions:**
```bash
# Add execute permission to specific script
chmod +x scripts/audit-versions.sh

# Add execute permission to all shell scripts
find scripts/ -name "*.sh" -type f -exec chmod +x {} \;
```

**Check Python scripts are readable:**
```bash
ls -l scripts/sync-versions.py

# Expected output:
-rwxr-xr-x  1 user  staff  9163 Dec  2 09:23 scripts/sync-versions.py
```

---

## Version Diagnostics

### Three-Layer Version System

Synaptic Canvas uses a three-layer versioning system. Understanding this is crucial for diagnostics.

```
Layer 1: Marketplace Platform Version
  Location: version.yaml
  Purpose: Platform/CLI infrastructure version

Layer 2: Package Versions
  Location: packages/*/manifest.yaml
  Purpose: Individual package versions (independent)

Layer 3: Artifact Versions
  Location: YAML frontmatter in commands/skills/agents
  Purpose: Individual artifact versions (synchronized with package)
```

### Check Layer 1: Marketplace Version

**Location:** `version.yaml`

```bash
# View marketplace version
cat version.yaml

# Extract just the version
grep "^version:" version.yaml | awk -F': *' '{print $2}' | tr -d '"'

# Output:
0.4.0
```

**Validate marketplace version format:**
```bash
marketplace_version=$(grep "^version:" version.yaml | awk -F': *' '{print $2}' | tr -d '"')

if [[ $marketplace_version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "✓ Valid marketplace version: $marketplace_version"
else
    echo "✗ Invalid marketplace version format: $marketplace_version"
fi
```

---

### Check Layer 2: Package Versions

**List all package versions:**
```bash
# For each package, extract version from manifest
for pkg in packages/*/; do
    pkg_name=$(basename "$pkg")
    version=$(grep "^version:" "$pkg/manifest.yaml" 2>/dev/null | awk -F': *' '{print $2}' | tr -d '"')
    echo "$pkg_name: $version"
done

# Output:
delay-tasks: 0.4.0
git-worktree: 0.4.0
repomix-nuget: 0.4.0
sc-manage: 0.4.0
```

**Check specific package version:**
```bash
# Check delay-tasks version
grep "^version:" packages/delay-tasks/manifest.yaml | awk -F': *' '{print $2}' | tr -d '"'

# Output:
0.4.0
```

**Compare all package versions:**
```bash
# Check if all packages have the same version
versions=$(for pkg in packages/*/; do
    grep "^version:" "$pkg/manifest.yaml" 2>/dev/null | awk -F': *' '{print $2}' | tr -d '"'
done | sort -u)

if [[ $(echo "$versions" | wc -l) -eq 1 ]]; then
    echo "✓ All packages have the same version: $versions"
else
    echo "⚠ Packages have different versions:"
    for pkg in packages/*/; do
        pkg_name=$(basename "$pkg")
        version=$(grep "^version:" "$pkg/manifest.yaml" 2>/dev/null | awk -F': *' '{print $2}' | tr -d '"')
        echo "  $pkg_name: $version"
    done
fi
```

---

### Check Layer 3: Artifact Versions

**Check command versions:**
```bash
# List all command versions
for cmd in packages/*/commands/*.md; do
    if [[ -f "$cmd" ]]; then
        cmd_name=$(basename "$cmd" .md)
        pkg_name=$(basename $(dirname $(dirname "$cmd")))
        version=$(grep "^version:" "$cmd" 2>/dev/null | head -1 | awk -F': *' '{print $2}' | tr -d '"')
        echo "$pkg_name/$cmd_name: $version"
    fi
done

# Output:
delay-tasks/delay: 0.4.0
git-worktree/git-worktree: 0.4.0
repomix-nuget/repomix-nuget: 0.4.0
sc-manage/sc-manage: 0.4.0
```

**Check skill versions:**
```bash
# List all skill versions
for skill in packages/*/skills/*/SKILL.md; do
    if [[ -f "$skill" ]]; then
        skill_name=$(basename $(dirname "$skill"))
        pkg_name=$(basename $(dirname $(dirname $(dirname "$skill"))))
        version=$(grep "^version:" "$skill" 2>/dev/null | head -1 | awk -F': *' '{print $2}' | tr -d '"')
        echo "$pkg_name/$skill_name: $version"
    fi
done

# Output:
delay-tasks/delaying-tasks: 0.4.0
git-worktree/managing-worktrees: 0.4.0
repomix-nuget/generating-nuget-context: 0.4.0
sc-manage/managing-sc-packages: 0.4.0
```

**Check agent versions:**
```bash
# List all agent versions
for agent in packages/*/agents/*.md .claude/agents/*.md; do
    if [[ -f "$agent" ]]; then
        agent_name=$(basename "$agent" .md)
        version=$(grep "^version:" "$agent" 2>/dev/null | head -1 | awk -F': *' '{print $2}' | tr -d '"')
        echo "$agent_name: $version"
    fi
done

# Output:
delay-once: 0.4.0
delay-poll: 0.4.0
git-pr-check-delay: 0.4.0
worktree-create: 0.4.0
...
```

---

### Cross-Layer Version Verification

**Verify artifact versions match package versions:**
```bash
# Run comprehensive audit
./scripts/audit-versions.sh

# Or check manually for a specific package
package_name="delay-tasks"
pkg_version=$(grep "^version:" "packages/$package_name/manifest.yaml" | awk -F': *' '{print $2}' | tr -d '"')

echo "Package $package_name version: $pkg_version"
echo "Artifact versions:"

for cmd in packages/$package_name/commands/*.md; do
    if [[ -f "$cmd" ]]; then
        cmd_name=$(basename "$cmd" .md)
        cmd_version=$(grep "^version:" "$cmd" 2>/dev/null | head -1 | awk -F': *' '{print $2}' | tr -d '"')
        if [[ "$cmd_version" == "$pkg_version" ]]; then
            echo "  ✓ command/$cmd_name: $cmd_version"
        else
            echo "  ✗ command/$cmd_name: $cmd_version (should be $pkg_version)"
        fi
    fi
done
```

---

## Registry Diagnostics

### Validate Registry JSON

**Full validation:**
```bash
python3 docs/registries/nuget/validate-registry.py --verbose
```

**Quick validation:**
```bash
python3 docs/registries/nuget/validate-registry.py

# Check exit code
if [ $? -eq 0 ]; then
    echo "✓ Registry is valid"
else
    echo "✗ Registry validation failed"
fi
```

**JSON validation for CI/CD:**
```bash
python3 docs/registries/nuget/validate-registry.py --json > registry-validation.json

# Check result
cat registry-validation.json | python3 -m json.tool | grep '"valid"'

# Output:
  "valid": true,
```

---

### Check Registry Structure

**Verify registry file exists:**
```bash
ls -l docs/registries/nuget/registry.json

# Expected output:
-rw-r--r--  1 user  staff  5673 Dec  2 09:25 docs/registries/nuget/registry.json
```

**Check registry is valid JSON:**
```bash
python3 -m json.tool docs/registries/nuget/registry.json > /dev/null

if [ $? -eq 0 ]; then
    echo "✓ Registry is valid JSON"
else
    echo "✗ Registry has invalid JSON syntax"
fi
```

**Extract registry version:**
```bash
python3 -c "import json; print(json.load(open('docs/registries/nuget/registry.json'))['version'])"

# Output:
0.4.0
```

**Count packages in registry:**
```bash
python3 -c "import json; print(len(json.load(open('docs/registries/nuget/registry.json'))['packages']))"

# Output:
4
```

**List packages in registry:**
```bash
python3 -c "import json; print('\n'.join(json.load(open('docs/registries/nuget/registry.json'))['packages'].keys()))"

# Output:
delay-tasks
git-worktree
repomix-nuget
sc-manage
```

---

### Check Registry Metadata

**View registry metadata:**
```bash
python3 -c "import json; import pprint; pprint.pprint(json.load(open('docs/registries/nuget/registry.json'))['metadata'])"

# Output:
{'categories': {'automation': ['delay-tasks'],
                'git': ['git-worktree'],
                'management': ['sc-manage'],
                'nuget': ['repomix-nuget'],
                'workflow': ['delay-tasks', 'git-worktree']},
 'registryVersion': '0.4.0',
 'schemaVersion': '1.0.0',
 'totalAgents': 16,
 'totalCommands': 4,
 'totalPackages': 4,
 'totalScripts': 2,
 'totalSkills': 6}
```

**Verify metadata statistics:**
```bash
# Count actual packages
actual_packages=$(ls -d packages/*/ | wc -l)
registry_packages=$(python3 -c "import json; print(json.load(open('docs/registries/nuget/registry.json'))['metadata']['totalPackages'])")

if [ "$actual_packages" -eq "$registry_packages" ]; then
    echo "✓ Package count matches: $actual_packages"
else
    echo "✗ Package count mismatch: actual=$actual_packages, registry=$registry_packages"
fi
```

---

## Package Diagnostics

### Check Package Structure

**Verify package directory structure:**
```bash
# Check delay-tasks package
package="delay-tasks"

echo "Checking $package structure..."

# Check required files
for file in manifest.yaml README.md CHANGELOG.md; do
    if [[ -f "packages/$package/$file" ]]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file (missing)"
    fi
done

# Check required directories
for dir in commands skills agents scripts; do
    if [[ -d "packages/$package/$dir" ]]; then
        echo "  ✓ $dir/"
    else
        echo "  ⚠ $dir/ (missing - may be optional)"
    fi
done
```

**Expected output:**
```
Checking delay-tasks structure...
  ✓ manifest.yaml
  ✓ README.md
  ✓ CHANGELOG.md
  ✓ commands/
  ✓ skills/
  ✓ agents/
  ✓ scripts/
```

---

### Check Package Manifests

**Validate manifest YAML syntax:**
```bash
python3 -c "import yaml; yaml.safe_load(open('packages/delay-tasks/manifest.yaml'))"

if [ $? -eq 0 ]; then
    echo "✓ Manifest is valid YAML"
else
    echo "✗ Manifest has invalid YAML syntax"
fi
```

**Check required manifest fields:**
```bash
package="delay-tasks"
manifest="packages/$package/manifest.yaml"

required_fields=("name" "version" "description" "author" "license")

echo "Checking manifest fields for $package..."

for field in "${required_fields[@]}"; do
    value=$(grep "^$field:" "$manifest" 2>/dev/null | awk -F': *' '{print $2}' | tr -d '"')
    if [[ -n "$value" ]]; then
        echo "  ✓ $field: $value"
    else
        echo "  ✗ $field: (missing)"
    fi
done
```

---

### Check Artifact Counts

**Count artifacts per package:**
```bash
package="delay-tasks"

echo "Artifact counts for $package:"

# Count commands
cmd_count=$(find "packages/$package/commands" -name "*.md" -type f 2>/dev/null | wc -l)
echo "  Commands: $cmd_count"

# Count skills
skill_count=$(find "packages/$package/skills" -name "SKILL.md" -type f 2>/dev/null | wc -l)
echo "  Skills: $skill_count"

# Count agents
agent_count=$(find "packages/$package/agents" -name "*.md" -type f 2>/dev/null | wc -l)
echo "  Agents: $agent_count"

# Count scripts
script_count=$(find "packages/$package/scripts" -type f 2>/dev/null | wc -l)
echo "  Scripts: $script_count"
```

**Verify artifact counts match manifest:**
```bash
package="delay-tasks"
manifest="packages/$package/manifest.yaml"

# Extract artifact counts from manifest
manifest_commands=$(grep -A 10 "^artifacts:" "$manifest" | grep "commands:" -A 1 | grep "^  - " | wc -l)
manifest_skills=$(grep -A 10 "^artifacts:" "$manifest" | grep "skills:" -A 1 | grep "^  - " | wc -l)
manifest_agents=$(grep -A 10 "^artifacts:" "$manifest" | grep "agents:" -A 1 | grep "^  - " | wc -l)
manifest_scripts=$(grep -A 10 "^artifacts:" "$manifest" | grep "scripts:" -A 1 | grep "^  - " | wc -l)

# Count actual artifacts
actual_commands=$(find "packages/$package/commands" -name "*.md" -type f 2>/dev/null | wc -l)
actual_skills=$(find "packages/$package/skills" -name "SKILL.md" -type f 2>/dev/null | wc -l)
actual_agents=$(find "packages/$package/agents" -name "*.md" -type f 2>/dev/null | wc -l)
actual_scripts=$(find "packages/$package/scripts" -type f 2>/dev/null | wc -l)

echo "Manifest vs Actual counts for $package:"
echo "  Commands: $manifest_commands (manifest) vs $actual_commands (actual)"
echo "  Skills: $manifest_skills (manifest) vs $actual_skills (actual)"
echo "  Agents: $manifest_agents (manifest) vs $actual_agents (actual)"
echo "  Scripts: $manifest_scripts (manifest) vs $actual_scripts (actual)"
```

---

## Integration Diagnostics

### CI/CD Pipeline Validation

**Check GitHub Actions workflows exist:**
```bash
ls -la .github/workflows/

# Expected output:
version-audit.yml
tests.yml
```

**Validate workflow syntax:**
```bash
# Check if workflows are valid YAML
for workflow in .github/workflows/*.yml; do
    echo "Checking $workflow..."
    python3 -c "import yaml; yaml.safe_load(open('$workflow'))" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "  ✓ Valid YAML"
    else
        echo "  ✗ Invalid YAML syntax"
    fi
done
```

**View version audit workflow:**
```bash
cat .github/workflows/version-audit.yml
```

**Test version audit locally (simulate CI):**
```bash
# Run the same command that CI runs
./scripts/audit-versions.sh

# Check exit code
if [ $? -eq 0 ]; then
    echo "✓ Version audit passed (CI would succeed)"
else
    echo "✗ Version audit failed (CI would fail)"
fi
```

---

### Git Integration

**Check Git hooks:**
```bash
ls -la .git/hooks/

# Check for custom hooks
for hook in pre-commit pre-push; do
    if [[ -f ".git/hooks/$hook" ]]; then
        echo "✓ $hook hook exists"
    else
        echo "⚠ $hook hook not installed"
    fi
done
```

**Test Git operations:**
```bash
# Check Git can fetch
git fetch --dry-run

# Check Git can create branches
git check-ref-format --branch "test-branch" && echo "✓ Branch name valid"

# Check Git worktree support
git worktree --help > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Git worktree support available"
else
    echo "✗ Git version too old for worktree support"
fi
```

---

## Performance Diagnostics

### Check System Resources

**Disk space:**
```bash
# Check available disk space
df -h .

# Output:
Filesystem      Size   Used  Avail Capacity
/dev/disk1s1   233Gi  180Gi   50Gi    79%
```

**Repository size:**
```bash
# Check repository size
du -sh .

# Output:
45M     .
```

**Package sizes:**
```bash
# Check size of each package
du -sh packages/*

# Output:
1.2M    packages/delay-tasks
800K    packages/git-worktree
2.5M    packages/repomix-nuget
1.0M    packages/sc-manage
```

---

### Check Execution Times

**Measure audit script performance:**
```bash
# Time the audit script
time ./scripts/audit-versions.sh

# Output:
=== Synaptic Canvas Version Audit ===
...
All checks passed!

real    0m0.523s
user    0m0.312s
sys     0m0.198s
```

**Measure sync script performance:**
```bash
# Time the sync script (dry run)
time python3 scripts/sync-versions.py --package delay-tasks --version 0.4.0 --dry-run

# Output:
Syncing delay-tasks to version 0.4.0...
...

real    0m0.145s
user    0m0.098s
sys     0m0.042s
```

**Measure registry validation performance:**
```bash
# Time registry validation
time python3 docs/registries/nuget/validate-registry.py --json > /dev/null

# Output:
real    0m0.231s
user    0m0.187s
sys     0m0.039s
```

---

## Environment Diagnostics

### OS Detection

**Detect operating system:**
```bash
# Check OS type
uname -s

# Output:
Darwin   # macOS
Linux    # Linux
MINGW64_NT  # Windows Git Bash
```

**Get OS version:**
```bash
# macOS
sw_vers
# Output:
ProductName:    macOS
ProductVersion: 14.5
BuildVersion:   23F79

# Linux
lsb_release -a
# or
cat /etc/os-release

# Windows (Git Bash)
wmic os get Caption,Version
```

**Architecture detection:**
```bash
uname -m

# Output:
x86_64   # Intel/AMD 64-bit
arm64    # Apple Silicon
```

---

### Path Validation

**Check PATH includes required directories:**
```bash
echo "$PATH" | tr ':' '\n'

# Should include (examples):
/usr/local/bin
/usr/bin
/bin
/opt/homebrew/bin  # macOS Homebrew
~/.local/bin       # User local binaries
```

**Verify command locations:**
```bash
# Check where commands are located
which git
which python3
which node
which npm

# Output:
/usr/bin/git
/usr/bin/python3
/usr/local/bin/node
/usr/local/bin/npm
```

**Check for multiple installations:**
```bash
# Find all Git installations
which -a git

# Output:
/usr/bin/git
/usr/local/bin/git

# Find all Python installations
which -a python3

# Output:
/usr/bin/python3
/usr/local/bin/python3
~/.pyenv/shims/python3
```

---

### Shell Compatibility

**Check shell type:**
```bash
echo "$SHELL"

# Output:
/bin/bash    # Bash
/bin/zsh     # Zsh
/bin/sh      # POSIX sh
```

**Check shell version:**
```bash
# Bash
bash --version

# Output:
GNU bash, version 5.2.15(1)-release (x86_64-apple-darwin23.0.0)

# Zsh
zsh --version

# Output:
zsh 5.9 (x86_64-apple-darwin23.0.0)
```

**Test POSIX compatibility:**
```bash
# Run script with POSIX sh
sh scripts/audit-versions.sh

# If it works, scripts are POSIX compatible
```

---

## JSON Output Examples

### Audit Script JSON

Currently, `audit-versions.sh` does not output JSON. Consider using `compare-versions.sh --json` for structured output.

**Feature request:** Add `--json` flag to `audit-versions.sh`

---

### Compare Versions JSON

```bash
./scripts/compare-versions.sh --json
```

**Output:**
```json
{
  "marketplace": "0.4.0",
  "packages": [
    {
      "name": "delay-tasks",
      "version": "0.4.0",
      "consistent": true
    },
    {
      "name": "git-worktree",
      "version": "0.4.0",
      "consistent": true
    },
    {
      "name": "sc-manage",
      "version": "0.4.0",
      "consistent": true
    },
    {
      "name": "repomix-nuget",
      "version": "0.4.0",
      "consistent": true
    }
  ]
}
```

**With mismatches:**
```json
{
  "marketplace": "0.4.0",
  "packages": [
    {
      "name": "delay-tasks",
      "version": "0.4.0",
      "consistent": false
    },
    {
      "name": "git-worktree",
      "version": "0.4.0",
      "consistent": true
    }
  ]
}
```

---

### Registry Validation JSON

```bash
python3 docs/registries/nuget/validate-registry.py --json
```

**Valid registry output:**
```json
{
  "valid": true,
  "error_count": 0,
  "errors": [],
  "registry": {
    "version": "0.4.0",
    "packages": 4,
    "generated": "2025-12-02T10:25:00Z"
  }
}
```

**Invalid registry output:**
```json
{
  "valid": false,
  "error_count": 3,
  "errors": [
    "Package 'delay-tasks': Invalid version format '0.4'",
    "Package 'git-worktree': Missing required field: 'description'",
    "Package 'repomix-nuget': Invalid repo URL (must be https://github.com/...)"
  ],
  "registry": {
    "version": "0.4.0",
    "packages": 4,
    "generated": "2025-12-02T10:25:00Z"
  }
}
```

---

## Troubleshooting Diagnostic Issues

### Common Problems

#### 1. Script Not Found or Permission Denied

**Problem:**
```bash
$ ./scripts/audit-versions.sh
-bash: ./scripts/audit-versions.sh: Permission denied
```

**Solution:**
```bash
# Add execute permission
chmod +x scripts/audit-versions.sh

# Run again
./scripts/audit-versions.sh
```

---

#### 2. Python Script Fails to Run

**Problem:**
```bash
$ python3 scripts/sync-versions.py
-bash: python3: command not found
```

**Solution:**
```bash
# Check Python installations
python --version
python3 --version

# Install Python 3 if needed
# macOS:
brew install python3

# Linux (Ubuntu/Debian):
sudo apt-get install python3

# Try with python instead of python3
python scripts/sync-versions.py
```

---

#### 3. Registry Validation Fails

**Problem:**
```bash
$ python3 docs/registries/nuget/validate-registry.py
ERROR: File not found: docs/registries/nuget/registry.json
```

**Solution:**
```bash
# Check file exists
ls -l docs/registries/nuget/registry.json

# If missing, regenerate registry
# (This would require a registry generation script)

# Or check you're in the right directory
pwd
cd /path/to/synaptic-canvas
```

---

#### 4. Version Mismatches After Update

**Problem:**
```bash
$ ./scripts/audit-versions.sh
✗ FAIL Command in delay-tasks: Version mismatch: command=0.3.0, package=0.4.0
```

**Solution:**
```bash
# Use sync script to fix
python3 scripts/sync-versions.py --package delay-tasks --version 0.4.0

# Verify fix
./scripts/audit-versions.sh
```

---

#### 5. Git Version Too Old

**Problem:**
```bash
$ git worktree --help
git: 'worktree' is not a git command. See 'git --help'.
```

**Solution:**
```bash
# Check Git version
git --version

# Upgrade Git
# macOS:
brew upgrade git

# Linux (Ubuntu/Debian):
sudo apt-get update
sudo apt-get upgrade git

# Verify new version
git --version
```

---

#### 6. Node.js Version Too Old

**Problem:**
```bash
$ node --version
v14.17.0  # Too old, need >= 18
```

**Solution:**
```bash
# Using nvm (recommended)
nvm install 18
nvm use 18

# Or using Homebrew (macOS)
brew upgrade node

# Verify version
node --version
```

---

## Creating Custom Diagnostics

### Creating a Custom Diagnostic Script

**Example: Check all package READMEs exist**

```bash
#!/bin/bash
# check-readmes.sh - Verify all packages have README files

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FAILED=0

echo "=== Checking Package READMEs ==="
echo ""

for package_dir in "$REPO_ROOT"/packages/*/; do
    package_name=$(basename "$package_dir")
    readme="$package_dir/README.md"

    if [[ -f "$readme" ]]; then
        echo "✓ $package_name: README.md exists"
    else
        echo "✗ $package_name: README.md missing"
        FAILED=1
    fi
done

echo ""
if [[ $FAILED -eq 0 ]]; then
    echo "All packages have READMEs!"
    exit 0
else
    echo "Some packages are missing READMEs"
    exit 1
fi
```

**Usage:**
```bash
chmod +x scripts/check-readmes.sh
./scripts/check-readmes.sh
```

---

### Creating a Python Diagnostic Tool

**Example: Check artifact naming conventions**

```python
#!/usr/bin/env python3
"""check-naming.py - Verify artifact naming conventions"""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
FAILED = False

print("=== Checking Artifact Naming Conventions ===\n")

# Check commands (should be lowercase with hyphens)
for cmd_file in REPO_ROOT.glob("packages/*/commands/*.md"):
    name = cmd_file.stem
    if not name.islower() or " " in name:
        print(f"✗ Invalid command name: {cmd_file.relative_to(REPO_ROOT)}")
        FAILED = True
    else:
        print(f"✓ Valid command name: {name}")

# Check agents (should be lowercase with hyphens)
for agent_file in REPO_ROOT.glob("packages/*/agents/*.md"):
    name = agent_file.stem
    if not name.islower() or " " in name:
        print(f"✗ Invalid agent name: {agent_file.relative_to(REPO_ROOT)}")
        FAILED = True
    else:
        print(f"✓ Valid agent name: {name}")

print()
if not FAILED:
    print("All artifact names follow conventions!")
    sys.exit(0)
else:
    print("Some artifacts have invalid names")
    sys.exit(1)
```

**Usage:**
```bash
chmod +x scripts/check-naming.py
python3 scripts/check-naming.py
```

---

### Integrating Custom Diagnostics into CI/CD

**Add to `.github/workflows/tests.yml`:**

```yaml
name: Tests

on: [push, pull_request]

jobs:
  diagnostics:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Check versions
        run: ./scripts/audit-versions.sh

      - name: Check READMEs
        run: ./scripts/check-readmes.sh

      - name: Check naming conventions
        run: python3 scripts/check-naming.py

      - name: Validate registry
        run: python3 docs/registries/nuget/validate-registry.py --json
```

---

## Best Practices

### Regular Diagnostic Schedule

**Daily (automated):**
- CI/CD runs version audit on every commit
- Registry validation on pull requests

**Weekly (manual):**
- Run full diagnostic suite locally
- Check for outdated dependencies
- Review performance metrics

**Before releases:**
- Run all diagnostic tools with `--verbose`
- Validate registry thoroughly
- Check version consistency across all layers
- Verify all packages are installable
- Test on multiple platforms

---

### Diagnostic Checklists

**Pre-Commit Checklist:**
- [ ] Run `./scripts/audit-versions.sh`
- [ ] Run `./scripts/compare-versions.sh`
- [ ] Check no uncommitted version changes

**Pre-Release Checklist:**
- [ ] Run `./scripts/audit-versions.sh --verbose`
- [ ] Run `python3 docs/registries/nuget/validate-registry.py --verbose`
- [ ] Verify all package versions match
- [ ] Check all CHANGELOGs are updated
- [ ] Validate registry metadata
- [ ] Test on macOS, Linux, and Windows

---

## Related Documentation

- [DIAGNOSTIC-WORKFLOW.md](DIAGNOSTIC-WORKFLOW.md) - Step-by-step diagnostic workflows
- [VERSION-CHECKING-GUIDE.md](VERSION-CHECKING-GUIDE.md) - Complete version verification guide
- [DEPENDENCY-VALIDATION.md](DEPENDENCY-VALIDATION.md) - Dependencies and validation procedures
- [versioning-strategy.md](versioning-strategy.md) - Three-layer versioning system
- [RELEASE-PROCESS.md](RELEASE-PROCESS.md) - Release process and procedures

---

## Appendix

### Tool Version Matrix

| Tool | Minimum Version | Recommended | Purpose |
|------|----------------|-------------|---------|
| Git | 2.7.0 | 2.30+ | Worktree support |
| Python 3 | 3.6 | 3.11+ | Scripts |
| Node.js | 18.0 | 18.17+ | repomix-nuget |
| npm | 8.0 | 9.6+ | Package management |
| Bash | 4.0 | 5.0+ | Shell scripts |

---

### Exit Code Reference

| Exit Code | Meaning | Tools |
|-----------|---------|-------|
| 0 | Success | All |
| 1 | Validation failure | audit-versions.sh, compare-versions.sh, validate-registry.py |
| 2 | Critical error | audit-versions.sh |

---

**End of Diagnostic Tools Reference Guide**
