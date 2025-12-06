# Version Checking Guide

**Version:** 0.5.0
**Last Updated:** 2025-12-05
**Repository:** [synaptic-canvas](https://github.com/randlee/synaptic-canvas)

---

## Table of Contents

1. [Version Architecture Overview](#version-architecture-overview)
2. [Layer 1: Marketplace Version](#layer-1-marketplace-version)
3. [Layer 2: Package Manifests](#layer-2-package-manifests)
4. [Layer 3: Artifact Versions](#layer-3-artifact-versions)
5. [Version Consistency Rules](#version-consistency-rules)
6. [Version Verification Commands](#version-verification-commands)
7. [Cross-Layer Version Checking](#cross-layer-version-checking)
8. [Version History](#version-history)
9. [Pre-Release Version Validation](#pre-release-version-validation)
10. [Common Version Mismatches](#common-version-mismatches)
11. [Version Rollback](#version-rollback)
12. [Automated Version Checking](#automated-version-checking)

---

## Version Architecture Overview

Synaptic Canvas uses a **three-layer versioning system** based on semantic versioning (SemVer):

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Marketplace Platform Version                     │
│  Location: version.yaml                                     │
│  Scope: Infrastructure, CLI, registry format               │
│  Current: 0.5.0                                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ manages
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Package Versions                                  │
│  Location: packages/*/manifest.yaml                         │
│  Scope: Individual packages (independent versioning)        │
│  Current: sc-delay-tasks=0.5.0, sc-git-worktree=0.5.0, etc. │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ contains
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: Artifact Versions                                 │
│  Location: YAML frontmatter in commands/skills/agents       │
│  Scope: Individual artifacts (synchronized with package)    │
│  Current: Must match parent package version                │
└─────────────────────────────────────────────────────────────┘
```

### Version Independence

| Layer | Independence | Rationale |
|-------|-------------|-----------|
| Marketplace | Independent | Infrastructure can evolve separately |
| Packages | Independent | Each package has its own release cycle |
| Artifacts | **Synchronized** | Must match parent package for consistency |

### Semantic Versioning

All versions follow SemVer format: `MAJOR.MINOR.PATCH`

- **MAJOR** (X.0.0): Breaking changes, incompatible API changes
- **MINOR** (0.X.0): New features, functionality enhancements
- **PATCH** (0.0.X): Bug fixes, stability improvements

**Examples:**
- ✅ `0.4.0` - Valid
- ✅ `1.0.0` - Valid
- ✅ `2.1.3` - Valid
- ❌ `0.4` - Invalid (missing patch)
- ❌ `v0.4.0` - Invalid (no 'v' prefix)
- ❌ `1.0.0-beta` - Invalid (pre-release tags not supported in current system)

---

## Layer 1: Marketplace Version

### Location and Purpose

**File:** `version.yaml` (repository root)

**Purpose:** Tracks the version of the Synaptic Canvas marketplace platform itself, not individual packages.

**What it controls:**
- Installation system (`sc-install.py`)
- Registry format and schema
- Marketplace infrastructure
- CLI tool interfaces

**What it does NOT control:**
- Individual package versions (those are in Layer 2)
- Artifact versions (those follow Layer 2)

---

### Current Version and History

**Check current marketplace version:**

```bash
cat version.yaml
```

**Output:**
```yaml
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
# When to bump this version:
# - Major changes to installation system or marketplace infrastructure
# - Breaking changes to registry format
# - New marketplace-wide features
#
# Package versions are managed independently in packages/*/manifest.yaml
#
version: "0.4.0"
```

**Extract version only:**

```bash
grep "^version:" version.yaml | awk -F': *' '{print $2}' | tr -d '"'
```

**Output:**
```
0.4.0
```

---

### Version History

**View version history in Git:**

```bash
# Show version changes over time
git log -p version.yaml | grep "^[+-]version:" | head -20
```

**Example output:**
```
+version: "0.4.0"
-version: "0.3.0"
+version: "0.3.0"
-version: "0.2.0"
```

**See when version was last changed:**

```bash
git log -1 --format="%ai %s" version.yaml
```

**Output:**
```
2025-12-02 10:00:00 -0800 chore(versioning): bump marketplace to 0.4.0
```

---

### When to Update Marketplace Version

**MAJOR version (X.0.0):**
- Breaking changes to installation system
- Incompatible registry format changes
- Major architectural changes
- CLI interface breaking changes

**MINOR version (0.X.0):**
- New marketplace features
- New installation options
- Registry format additions (backward-compatible)
- New CLI commands

**PATCH version (0.0.X):**
- Bug fixes in installation system
- Registry format clarifications
- Documentation updates
- Minor improvements

**Examples:**

```bash
# Example: Bug fix in installer
# Current: 0.4.0
# New: 0.4.1
echo 'version: "0.4.1"' > version.yaml

# Example: New marketplace feature
# Current: 0.4.1
# New: 0.5.0
echo 'version: "0.5.0"' > version.yaml

# Example: Breaking change to registry
# Current: 0.5.0
# New: 1.0.0
echo 'version: "1.0.0"' > version.yaml
```

---

### How to Check Marketplace Version

**Method 1: Direct file read**
```bash
cat version.yaml | grep "^version:"
```

**Method 2: Using grep and awk**
```bash
grep "^version:" version.yaml | awk -F': *' '{print $2}' | tr -d '"'
```

**Method 3: Using Python**
```bash
python3 -c "import yaml; print(yaml.safe_load(open('version.yaml'))['version'])"
```

**Method 4: In a script**
```bash
MARKETPLACE_VERSION=$(grep "^version:" version.yaml | awk -F': *' '{print $2}' | tr -d '"')
echo "Marketplace version: $MARKETPLACE_VERSION"
```

---

### How to Update Marketplace Version

**Method 1: Manual edit**
```bash
# Edit version.yaml
vim version.yaml
# Update version line
# Save and commit
```

**Method 2: Using sync-versions.py**
```bash
# Sync marketplace to new version
python3 scripts/sync-versions.py --marketplace --version 0.5.0

# With commit
python3 scripts/sync-versions.py --marketplace --version 0.5.0 --commit
```

**Method 3: Using sed**
```bash
# Replace version in-place
new_version="0.5.0"
sed -i.bak "s/^version: .*/version: \"$new_version\"/" version.yaml

# Verify
grep "^version:" version.yaml
```

---

## Layer 2: Package Manifests

### Individual Package Versions

Each package maintains its own version independently in its `manifest.yaml` file.

**Package list and locations:**

```
packages/sc-delay-tasks/manifest.yaml
packages/sc-git-worktree/manifest.yaml
packages/sc-repomix-nuget/manifest.yaml
packages/sc-manage/manifest.yaml
```

---

### Version Independence Rules

**Key principle:** Packages can have different versions.

**Why independence matters:**
- Packages evolve at different rates
- Bug fixes in one package don't require updating all packages
- New features can be released per-package
- Simplifies maintenance

**Example scenario:**
```
Marketplace: 0.4.0
sc-delay-tasks: 0.4.0
sc-git-worktree: 0.4.0
sc-repomix-nuget: 0.4.0  ← Gets bug fix
sc-manage: 0.4.0

After bug fix:
Marketplace: 0.4.0  (no change)
sc-delay-tasks: 0.4.0  (no change)
sc-git-worktree: 0.4.0  (no change)
sc-repomix-nuget: 0.4.1  ← Version bumped
sc-manage: 0.4.0  (no change)
```

---

### Checking All Package Versions

**Method 1: Loop through packages**

```bash
for pkg in packages/*/; do
    pkg_name=$(basename "$pkg")
    version=$(grep "^version:" "$pkg/manifest.yaml" 2>/dev/null | awk -F': *' '{print $2}' | tr -d '"')
    echo "$pkg_name: $version"
done
```

**Output:**
```
sc-delay-tasks: 0.4.0
sc-git-worktree: 0.4.0
sc-repomix-nuget: 0.4.0
sc-manage: 0.4.0
```

**Method 2: Using compare-versions.sh**

```bash
./scripts/compare-versions.sh
```

**Output:**
```
=== Synaptic Canvas Version Comparison ===

Marketplace Version: 0.4.0

Package: sc-delay-tasks (manifest: 0.4.0)
Package: sc-git-worktree (manifest: 0.4.0)
Package: sc-manage (manifest: 0.4.0)
Package: sc-repomix-nuget (manifest: 0.4.0)

All versions consistent!
```

**Method 3: JSON output for scripting**

```bash
./scripts/compare-versions.sh --json
```

**Output:**
```json
{
  "marketplace": "0.4.0",
  "packages": [
    {"name": "sc-delay-tasks", "version": "0.4.0", "consistent": true},
    {"name": "sc-git-worktree", "version": "0.4.0", "consistent": true},
    {"name": "sc-manage", "version": "0.4.0", "consistent": true},
    {"name": "sc-repomix-nuget", "version": "0.4.0", "consistent": true}
  ]
}
```

---

### Comparing Package Versions

**Check if all packages have the same version:**

```bash
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

**Find packages with specific version:**

```bash
target_version="0.4.0"

echo "Packages with version $target_version:"
for pkg in packages/*/; do
    pkg_name=$(basename "$pkg")
    version=$(grep "^version:" "$pkg/manifest.yaml" 2>/dev/null | awk -F': *' '{print $2}' | tr -d '"')
    if [[ "$version" == "$target_version" ]]; then
        echo "  ✓ $pkg_name"
    fi
done
```

**Find packages with outdated versions:**

```bash
latest_version="0.4.0"

echo "Packages not at version $latest_version:"
for pkg in packages/*/; do
    pkg_name=$(basename "$pkg")
    version=$(grep "^version:" "$pkg/manifest.yaml" 2>/dev/null | awk -F': *' '{print $2}' | tr -d '"')
    if [[ "$version" != "$latest_version" ]]; then
        echo "  ⚠ $pkg_name: $version"
    fi
done
```

---

### Checking Specific Package Version

**Check sc-delay-tasks version:**

```bash
grep "^version:" packages/sc-delay-tasks/manifest.yaml | awk -F': *' '{print $2}' | tr -d '"'
```

**Check all fields in manifest:**

```bash
cat packages/sc-delay-tasks/manifest.yaml
```

**Output:**
```yaml
name: sc-delay-tasks
version: 0.4.0
description: >
  Schedule delayed one-shot or bounded polling actions with minimal heartbeats.
  Useful for waiting before running checks (e.g., CI status) or polling with stop-on-success.
author: randlee
license: MIT
tags:
  - delay
  - polling
  - scheduler
  - ci
  - workflow
  - agents
...
```

**Extract version with Python:**

```bash
python3 -c "import yaml; print(yaml.safe_load(open('packages/sc-delay-tasks/manifest.yaml'))['version'])"
```

---

### Updating Package Version

**Method 1: Using sync-versions.py (Recommended)**

```bash
# Update specific package
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.0

# With dry-run first
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.0 --dry-run

# With commit
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.5.0 --commit
```

**Method 2: Manual edit**

```bash
# Edit manifest
vim packages/sc-delay-tasks/manifest.yaml

# Update version line
# version: 0.4.0  →  version: 0.5.0

# Also update all artifact versions manually
# (see Layer 3 section)
```

**Method 3: Using sed**

```bash
package="sc-delay-tasks"
new_version="0.5.0"

# Update manifest
sed -i.bak "s/^version: .*/version: $new_version/" "packages/$package/manifest.yaml"

# Note: This only updates manifest, not artifacts
# Use sync-versions.py to update artifacts
```

---

## Layer 3: Artifact Versions

### Where Artifacts Are Versioned

Artifacts have version information in their YAML frontmatter:

**Artifact types and locations:**

1. **Commands:** `packages/*/commands/*.md`
2. **Skills:** `packages/*/skills/*/SKILL.md`
3. **Agents:** `packages/*/agents/*.md`
4. **Installed agents:** `.claude/agents/*.md`

**Frontmatter format:**

```yaml
---
name: artifact-name
description: Artifact description
version: 0.4.0
---

# Artifact content here
```

---

### Synchronization with Package Versions

**Critical rule:** Artifact versions MUST match their parent package version.

**Why synchronization matters:**
- Ensures version consistency
- Makes it clear which package version an artifact belongs to
- Simplifies troubleshooting
- Required for registry validation

**Verification:**

```bash
# Check if artifact version matches package version
package="sc-delay-tasks"
pkg_version=$(grep "^version:" "packages/$package/manifest.yaml" | awk -F': *' '{print $2}' | tr -d '"')

for cmd in packages/$package/commands/*.md; do
    if [[ -f "$cmd" ]]; then
        cmd_name=$(basename "$cmd" .md)
        cmd_version=$(grep "^version:" "$cmd" 2>/dev/null | head -1 | awk -F': *' '{print $2}' | tr -d '"')

        if [[ "$cmd_version" == "$pkg_version" ]]; then
            echo "✓ $cmd_name: $cmd_version (matches $pkg_version)"
        else
            echo "✗ $cmd_name: $cmd_version (expected $pkg_version)"
        fi
    fi
done
```

---

### Checking Artifact Consistency

**Check all commands:**

```bash
echo "=== Command Versions ==="
for cmd in packages/*/commands/*.md; do
    if [[ -f "$cmd" ]]; then
        pkg=$(basename $(dirname $(dirname "$cmd")))
        cmd_name=$(basename "$cmd" .md)
        version=$(grep "^version:" "$cmd" 2>/dev/null | head -1 | awk -F': *' '{print $2}' | tr -d '"')
        echo "$pkg/$cmd_name: $version"
    fi
done
```

**Check all skills:**

```bash
echo "=== Skill Versions ==="
for skill in packages/*/skills/*/SKILL.md; do
    if [[ -f "$skill" ]]; then
        pkg=$(basename $(dirname $(dirname $(dirname "$skill"))))
        skill_name=$(basename $(dirname "$skill"))
        version=$(grep "^version:" "$skill" 2>/dev/null | head -1 | awk -F': *' '{print $2}' | tr -d '"')
        echo "$pkg/$skill_name: $version"
    fi
done
```

**Check all agents:**

```bash
echo "=== Agent Versions ==="
for agent in packages/*/agents/*.md; do
    if [[ -f "$agent" ]]; then
        pkg=$(basename $(dirname $(dirname "$agent")))
        agent_name=$(basename "$agent" .md)
        version=$(grep "^version:" "$agent" 2>/dev/null | head -1 | awk -F': *' '{print $2}' | tr -d '"')
        echo "$pkg/$agent_name: $version"
    fi
done
```

**Check installed artifacts:**

```bash
echo "=== Installed Agent Versions ==="
for agent in .claude/agents/*.md; do
    if [[ -f "$agent" ]]; then
        agent_name=$(basename "$agent" .md)
        version=$(grep "^version:" "$agent" 2>/dev/null | head -1 | awk -F': *' '{print $2}' | tr -d '"')
        echo "$agent_name: $version"
    fi
done
```

---

### Comprehensive Artifact Version Check

**Use audit-versions.sh for complete check:**

```bash
./scripts/audit-versions.sh --verbose
```

**Output (example with all checks):**

```
=== Synaptic Canvas Version Audit ===

Checking commands...
✓ Command: delay (v0.4.0)
✓ Command: sc-git-worktree (v0.4.0)
✓ Command: sc-repomix-nuget (v0.4.0)
✓ Command: sc-manage (v0.4.0)

Checking skills...
✓ Skill: delaying-tasks (v0.4.0)
✓ Skill: managing-worktrees (v0.4.0)
✓ Skill: generating-nuget-context (v0.4.0)
✓ Skill: managing-sc-packages (v0.4.0)

Checking agents...
✓ Agent: delay-once (v0.4.0)
✓ Agent: delay-poll (v0.4.0)
✓ Agent: git-pr-check-delay (v0.4.0)
✓ Agent: worktree-create (v0.4.0)
✓ Agent: worktree-scan (v0.4.0)
✓ Agent: worktree-cleanup (v0.4.0)
✓ Agent: worktree-abort (v0.4.0)
... (all agents)

Checking version consistency...
Checking CHANGELOGs...
✓ CHANGELOG for sc-delay-tasks
✓ CHANGELOG for sc-git-worktree
✓ CHANGELOG for sc-repomix-nuget
✓ CHANGELOG for sc-manage

Checking marketplace version...
✓ Marketplace version (v0.4.0)

=== Audit Results ===
Total checks: 42
Passed: 42
Failed: 0
Warnings: 0

All checks passed!
```

---

## Version Consistency Rules

### Three-Layer Hierarchy

```
1. Marketplace Version (version.yaml)
   ├─ Independent of package versions
   └─ Defines platform/infrastructure version

2. Package Versions (manifest.yaml)
   ├─ Independent of each other
   ├─ Independent of marketplace version
   └─ Defines package release version

3. Artifact Versions (YAML frontmatter)
   ├─ MUST match parent package version
   └─ Synchronized during version updates
```

---

### When Versions Should Match

**Artifacts MUST match package:**

```
✓ CORRECT:
packages/sc-delay-tasks/manifest.yaml:          version: 0.4.0
packages/sc-delay-tasks/commands/delay.md:      version: 0.4.0
packages/sc-delay-tasks/agents/delay-once.md:   version: 0.4.0

✗ INCORRECT:
packages/sc-delay-tasks/manifest.yaml:          version: 0.4.0
packages/sc-delay-tasks/commands/delay.md:      version: 0.3.0  ← MISMATCH!
packages/sc-delay-tasks/agents/delay-once.md:   version: 0.4.0
```

---

### When Versions Can Differ

**Packages can differ from each other:**

```
✓ CORRECT:
version.yaml:                               version: 0.4.0
packages/sc-delay-tasks/manifest.yaml:         version: 0.4.0
packages/sc-git-worktree/manifest.yaml:        version: 0.4.1  ← Different OK
packages/sc-repomix-nuget/manifest.yaml:       version: 0.3.0  ← Different OK
packages/sc-manage/manifest.yaml:           version: 0.5.0  ← Different OK
```

**Marketplace can differ from packages:**

```
✓ CORRECT:
version.yaml:                               version: 0.5.0  ← Different OK
packages/sc-delay-tasks/manifest.yaml:         version: 0.4.0
packages/sc-git-worktree/manifest.yaml:        version: 0.4.0
```

---

### Validation Rules

**Rule 1:** All artifacts in a package must have the same version

**Rule 2:** Artifact versions must match their package manifest version

**Rule 3:** Packages can have different versions from each other

**Rule 4:** Marketplace version is independent of package versions

**Rule 5:** All versions must be valid SemVer (X.Y.Z)

**Validation command:**

```bash
# Check all rules
./scripts/audit-versions.sh
```

---

## Version Verification Commands

### Quick Version Check

**Single command to check all versions:**

```bash
# Quick check
./scripts/compare-versions.sh

# With details
./scripts/compare-versions.sh --verbose

# Only show problems
./scripts/compare-versions.sh --mismatches
```

---

### Detailed Version Audit

**Full audit with all checks:**

```bash
# Standard audit
./scripts/audit-versions.sh

# With verbose output
./scripts/audit-versions.sh --verbose

# With automatic fixes for warnings
./scripts/audit-versions.sh --fix-warnings
```

---

### Version Extraction Commands

**Extract marketplace version:**

```bash
grep "^version:" version.yaml | awk -F': *' '{print $2}' | tr -d '"'
```

**Extract package version:**

```bash
package="sc-delay-tasks"
grep "^version:" "packages/$package/manifest.yaml" | awk -F': *' '{print $2}' | tr -d '"'
```

**Extract artifact version:**

```bash
artifact="packages/sc-delay-tasks/commands/delay.md"
grep "^version:" "$artifact" | head -1 | awk -F': *' '{print $2}' | tr -d '"'
```

---

### Version Comparison Commands

**Compare marketplace vs packages:**

```bash
marketplace_version=$(grep "^version:" version.yaml | awk -F': *' '{print $2}' | tr -d '"')

echo "Marketplace: $marketplace_version"
echo "Packages:"

for pkg in packages/*/; do
    pkg_name=$(basename "$pkg")
    pkg_version=$(grep "^version:" "$pkg/manifest.yaml" 2>/dev/null | awk -F': *' '{print $2}' | tr -d '"')

    if [[ "$pkg_version" == "$marketplace_version" ]]; then
        echo "  ✓ $pkg_name: $pkg_version"
    else
        echo "  ≠ $pkg_name: $pkg_version"
    fi
done
```

**Compare package vs artifacts:**

```bash
package="sc-delay-tasks"
pkg_version=$(grep "^version:" "packages/$package/manifest.yaml" | awk -F': *' '{print $2}' | tr -d '"')

echo "Package $package: $pkg_version"
echo "Artifacts:"

# Check commands
for cmd in packages/$package/commands/*.md; do
    if [[ -f "$cmd" ]]; then
        cmd_name=$(basename "$cmd" .md)
        cmd_version=$(grep "^version:" "$cmd" 2>/dev/null | head -1 | awk -F': *' '{print $2}' | tr -d '"')

        if [[ "$cmd_version" == "$pkg_version" ]]; then
            echo "  ✓ command/$cmd_name: $cmd_version"
        else
            echo "  ✗ command/$cmd_name: $cmd_version (expected $pkg_version)"
        fi
    fi
done

# Check skills
for skill in packages/$package/skills/*/SKILL.md; do
    if [[ -f "$skill" ]]; then
        skill_name=$(basename $(dirname "$skill"))
        skill_version=$(grep "^version:" "$skill" 2>/dev/null | head -1 | awk -F': *' '{print $2}' | tr -d '"')

        if [[ "$skill_version" == "$pkg_version" ]]; then
            echo "  ✓ skill/$skill_name: $skill_version"
        else
            echo "  ✗ skill/$skill_name: $skill_version (expected $pkg_version)"
        fi
    fi
done

# Check agents
for agent in packages/$package/agents/*.md; do
    if [[ -f "$agent" ]]; then
        agent_name=$(basename "$agent" .md)
        agent_version=$(grep "^version:" "$agent" 2>/dev/null | head -1 | awk -F': *' '{print $2}' | tr -d '"')

        if [[ "$agent_version" == "$pkg_version" ]]; then
            echo "  ✓ agent/$agent_name: $agent_version"
        else
            echo "  ✗ agent/$agent_name: $agent_version (expected $pkg_version)"
        fi
    fi
done
```

---

## Cross-Layer Version Checking

### Verify All Three Layers

**Complete three-layer check:**

```bash
#!/bin/bash
# check-all-versions.sh - Comprehensive version check

echo "=== Three-Layer Version Check ==="
echo ""

# Layer 1: Marketplace
echo "Layer 1: Marketplace Version"
marketplace_version=$(grep "^version:" version.yaml | awk -F': *' '{print $2}' | tr -d '"')
echo "  Marketplace: $marketplace_version"
echo ""

# Layer 2: Packages
echo "Layer 2: Package Versions"
for pkg in packages/*/; do
    pkg_name=$(basename "$pkg")
    pkg_version=$(grep "^version:" "$pkg/manifest.yaml" 2>/dev/null | awk -F': *' '{print $2}' | tr -d '"')
    echo "  $pkg_name: $pkg_version"
done
echo ""

# Layer 3: Artifacts (sample)
echo "Layer 3: Artifact Versions (sample)"
for pkg in packages/*/; do
    pkg_name=$(basename "$pkg")
    pkg_version=$(grep "^version:" "$pkg/manifest.yaml" 2>/dev/null | awk -F': *' '{print $2}' | tr -d '"')

    # Check one command from each package
    cmd=$(find "$pkg/commands" -name "*.md" -type f 2>/dev/null | head -1)
    if [[ -f "$cmd" ]]; then
        cmd_name=$(basename "$cmd" .md)
        cmd_version=$(grep "^version:" "$cmd" 2>/dev/null | head -1 | awk -F': *' '{print $2}' | tr -d '"')

        if [[ "$cmd_version" == "$pkg_version" ]]; then
            echo "  ✓ $pkg_name/$cmd_name: $cmd_version"
        else
            echo "  ✗ $pkg_name/$cmd_name: $cmd_version (package: $pkg_version)"
        fi
    fi
done

echo ""
echo "=== Use './scripts/audit-versions.sh' for complete check ==="
```

**Usage:**
```bash
chmod +x check-all-versions.sh
./check-all-versions.sh
```

---

### Version Synchronization Check

**Check if any versions need synchronization:**

```bash
./scripts/compare-versions.sh --mismatches

# If output is empty, all versions are synchronized
# If output shows packages, those need synchronization
```

---

## Version History

### Viewing Version Changes Over Time

**Marketplace version history:**

```bash
# Show all version changes
git log --all --oneline --grep="version" version.yaml

# Show version changes with diffs
git log -p version.yaml | grep -A 2 -B 2 "^[+-]version:"
```

**Package version history:**

```bash
package="sc-delay-tasks"

# Show all version changes for package
git log --all --oneline "packages/$package/manifest.yaml"

# Show version changes with diffs
git log -p "packages/$package/manifest.yaml" | grep -A 2 -B 2 "^[+-]version:"
```

**When was current version introduced:**

```bash
# Marketplace
git log -1 --format="%ai %s" version.yaml

# Package
package="sc-delay-tasks"
git log -1 --format="%ai %s" "packages/$package/manifest.yaml"
```

---

### Version Timeline

**Create version timeline:**

```bash
# Show version progression
echo "=== Marketplace Version Timeline ==="
git log --all --format="%ai %H" version.yaml | while read date time tz hash; do
    version=$(git show $hash:version.yaml 2>/dev/null | grep "^version:" | awk -F': *' '{print $2}' | tr -d '"')
    echo "$date $time - $version"
done | head -10
```

---

## Pre-Release Version Validation

### Before Creating a Release

**Complete pre-release checklist:**

```bash
echo "=== Pre-Release Version Validation ==="
echo ""

# 1. Check working tree is clean
if [[ -z $(git status --porcelain) ]]; then
    echo "✓ Working tree is clean"
else
    echo "✗ Working tree has uncommitted changes"
    git status --short
fi
echo ""

# 2. Check all versions are consistent
echo "Running version audit..."
./scripts/audit-versions.sh
echo ""

# 3. Check registry is valid
echo "Validating registry..."
python3 docs/registries/nuget/validate-registry.py --json | python3 -c "import sys, json; data=json.load(sys.stdin); sys.exit(0 if data['valid'] else 1)"
if [ $? -eq 0 ]; then
    echo "✓ Registry is valid"
else
    echo "✗ Registry validation failed"
fi
echo ""

# 4. Check all CHANGELOGs are updated
echo "Checking CHANGELOGs..."
for pkg in packages/*/; do
    pkg_name=$(basename "$pkg")
    if [[ -f "$pkg/CHANGELOG.md" ]]; then
        echo "  ✓ $pkg_name: CHANGELOG.md exists"
    else
        echo "  ✗ $pkg_name: CHANGELOG.md missing"
    fi
done
echo ""

echo "=== Pre-Release Validation Complete ==="
```

---

### Version Bump Planning

**Determine what version to use for release:**

**Questions to ask:**

1. **Are there breaking changes?**
   - Yes → MAJOR bump (e.g., 0.4.0 → 1.0.0)
   - No → Continue

2. **Are there new features?**
   - Yes → MINOR bump (e.g., 0.4.0 → 0.5.0)
   - No → Continue

3. **Are there only bug fixes?**
   - Yes → PATCH bump (e.g., 0.4.0 → 0.4.1)

**Example version bump script:**

```bash
#!/bin/bash
# determine-next-version.sh

current_version=$(grep "^version:" version.yaml | awk -F': *' '{print $2}' | tr -d '"')

echo "Current marketplace version: $current_version"
echo ""
echo "What type of release is this?"
echo "1) MAJOR - Breaking changes (0.4.0 → 1.0.0)"
echo "2) MINOR - New features (0.4.0 → 0.5.0)"
echo "3) PATCH - Bug fixes (0.4.0 → 0.4.1)"
echo ""
read -p "Enter choice [1-3]: " choice

IFS='.' read -r major minor patch <<< "$current_version"

case $choice in
    1)
        major=$((major + 1))
        minor=0
        patch=0
        ;;
    2)
        minor=$((minor + 1))
        patch=0
        ;;
    3)
        patch=$((patch + 1))
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

next_version="$major.$minor.$patch"
echo ""
echo "Next version: $next_version"
echo ""
echo "To update marketplace:"
echo "  python3 scripts/sync-versions.py --marketplace --version $next_version"
echo ""
echo "To update package:"
echo "  python3 scripts/sync-versions.py --package PACKAGE_NAME --version $next_version"
```

---

## Common Version Mismatches

### Problem 1: Artifact Version Doesn't Match Package

**Symptom:**
```
✗ FAIL Command in sc-delay-tasks: Version mismatch: command=0.3.0, package=0.4.0
```

**Diagnosis:**
```bash
# Check package version
grep "^version:" packages/sc-delay-tasks/manifest.yaml

# Check command version
grep "^version:" packages/sc-delay-tasks/commands/delay.md
```

**Fix:**
```bash
# Use sync script
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.4.0

# Verify fix
./scripts/audit-versions.sh
```

---

### Problem 2: Missing Version Frontmatter

**Symptom:**
```
✗ FAIL Command: delay: Missing version frontmatter
```

**Diagnosis:**
```bash
# Check if version exists
head -10 packages/sc-delay-tasks/commands/delay.md
```

**Fix:**
```bash
# Add version frontmatter manually
# Edit file and add:
# ---
# version: 0.4.0
# ---

# Or use sync script to add all at once
python3 scripts/sync-versions.py --package sc-delay-tasks --version 0.4.0
```

---

### Problem 3: Inconsistent Package Versions

**Symptom:**
```
Package: sc-delay-tasks (manifest: 0.4.0)
Package: sc-git-worktree (manifest: 0.3.0)
Package: sc-repomix-nuget (manifest: 0.4.0)
Package: sc-manage (manifest: 0.4.0)
```

**Diagnosis:**
This may not be a problem! Packages can have different versions.

**Decision:**
- If packages should be at same version → Update the outdated package
- If packages should be independent → No action needed

**Fix (if updating is desired):**
```bash
# Update sc-git-worktree to 0.4.0
python3 scripts/sync-versions.py --package sc-git-worktree --version 0.4.0
```

---

### Problem 4: Marketplace and Package Versions Differ

**Symptom:**
```
Marketplace Version: 0.5.0
Package: sc-delay-tasks (manifest: 0.4.0)
```

**Diagnosis:**
This is expected! Marketplace and packages have independent versions.

**Decision:**
- If this is intentional → No action needed
- If packages should match marketplace → Update packages

**Fix (if desired):**
```bash
# Update all packages to match marketplace
marketplace_version=$(grep "^version:" version.yaml | awk -F': *' '{print $2}' | tr -d '"')

python3 scripts/sync-versions.py --all --version $marketplace_version
```

---

## Version Rollback

### Rollback Single Package

**Rollback sc-delay-tasks to previous version:**

```bash
# Check current version
current=$(grep "^version:" packages/sc-delay-tasks/manifest.yaml | awk -F': *' '{print $2}' | tr -d '"')
echo "Current version: $current"

# Find previous version in git history
previous=$(git log -2 --oneline packages/sc-delay-tasks/manifest.yaml | tail -1 | awk '{print $1}')
previous_version=$(git show $previous:packages/sc-delay-tasks/manifest.yaml | grep "^version:" | awk -F': *' '{print $2}' | tr -d '"')
echo "Previous version: $previous_version"

# Rollback
python3 scripts/sync-versions.py --package sc-delay-tasks --version $previous_version

# Commit rollback
git add packages/sc-delay-tasks/
git commit -m "revert(sc-delay-tasks): rollback to version $previous_version"
```

---

### Rollback Marketplace Version

**Rollback marketplace to previous version:**

```bash
# Check current version
current=$(grep "^version:" version.yaml | awk -F': *' '{print $2}' | tr -d '"')
echo "Current version: $current"

# Find previous version
previous=$(git log -2 --oneline version.yaml | tail -1 | awk '{print $1}')
previous_version=$(git show $previous:version.yaml | grep "^version:" | awk -F': *' '{print $2}' | tr -d '"')
echo "Previous version: $previous_version"

# Rollback
python3 scripts/sync-versions.py --marketplace --version $previous_version

# Commit rollback
git add version.yaml
git commit -m "revert(marketplace): rollback to version $previous_version"
```

---

### Complete Rollback Using Git

**Rollback entire repository to previous state:**

```bash
# Find commit to rollback to
git log --oneline -10

# Example: Rollback to commit abc1234
commit="abc1234"

# Create new branch for rollback
git checkout -b rollback-to-$commit

# Reset to previous commit
git reset --hard $commit

# Verify versions
./scripts/compare-versions.sh

# If satisfied, merge back to main
git checkout main
git merge rollback-to-$commit
```

---

## Automated Version Checking

### CI/CD Integration

**GitHub Actions workflow for version checking:**

**File:** `.github/workflows/version-audit.yml`

```yaml
name: Version Audit

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  version-audit:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Run version audit
        run: |
          chmod +x scripts/audit-versions.sh
          ./scripts/audit-versions.sh

      - name: Compare versions
        run: |
          chmod +x scripts/compare-versions.sh
          ./scripts/compare-versions.sh --json

      - name: Validate registry
        run: |
          python3 docs/registries/nuget/validate-registry.py --json
```

---

### Pre-Commit Hook

**Automatically check versions before commit:**

**File:** `.git/hooks/pre-commit`

```bash
#!/bin/bash

echo "Running pre-commit version checks..."

# Run version audit
./scripts/audit-versions.sh

if [ $? -ne 0 ]; then
    echo ""
    echo "Version audit failed. Commit aborted."
    echo "Fix version mismatches and try again."
    exit 1
fi

echo "Version checks passed."
exit 0
```

**Install hook:**
```bash
# Copy hook to .git/hooks
cp scripts/pre-commit-hook .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

---

### Scheduled Version Checks

**Cron job for daily version checks:**

```bash
# Add to crontab
crontab -e

# Add line:
0 9 * * * cd /path/to/synaptic-canvas && ./scripts/audit-versions.sh >> /var/log/version-audit.log 2>&1
```

---

## Best Practices

### Version Management Workflow

1. **Before making changes:**
   ```bash
   ./scripts/compare-versions.sh
   ```

2. **When updating a package:**
   ```bash
   # Update package and all its artifacts
   python3 scripts/sync-versions.py --package PACKAGE_NAME --version NEW_VERSION

   # Verify
   ./scripts/audit-versions.sh

   # Commit
   git add packages/PACKAGE_NAME/
   git commit -m "chore(PACKAGE_NAME): bump version to NEW_VERSION"
   ```

3. **Before creating a release:**
   ```bash
   # Run full audit
   ./scripts/audit-versions.sh --verbose

   # Validate registry
   python3 docs/registries/nuget/validate-registry.py

   # Check all versions
   ./scripts/compare-versions.sh --verbose
   ```

4. **After creating a release:**
   ```bash
   # Verify tag
   git tag -l

   # Check versions in tag
   git show v0.4.0:version.yaml
   ```

---

### Documentation

- Always update CHANGELOG.md when bumping versions
- Document breaking changes clearly
- Update version compatibility matrix
- Keep versioning-strategy.md current

---

## Related Documentation

- [DIAGNOSTIC-TOOLS.md](DIAGNOSTIC-TOOLS.md) - Available diagnostic tools
- [DIAGNOSTIC-WORKFLOW.md](DIAGNOSTIC-WORKFLOW.md) - Step-by-step workflows
- [DEPENDENCY-VALIDATION.md](DEPENDENCY-VALIDATION.md) - Dependencies and validation
- [versioning-strategy.md](versioning-strategy.md) - Versioning policy
- [RELEASE-PROCESS.md](RELEASE-PROCESS.md) - Release procedures

---

## Quick Reference

### Common Commands

```bash
# Check all versions
./scripts/compare-versions.sh

# Run version audit
./scripts/audit-versions.sh

# Update package version
python3 scripts/sync-versions.py --package NAME --version X.Y.Z

# Update marketplace version
python3 scripts/sync-versions.py --marketplace --version X.Y.Z

# Validate registry
python3 docs/registries/nuget/validate-registry.py
```

### Version Files

```
version.yaml                        # Marketplace version
packages/*/manifest.yaml            # Package versions
packages/*/commands/*.md            # Command versions (frontmatter)
packages/*/skills/*/SKILL.md        # Skill versions (frontmatter)
packages/*/agents/*.md              # Agent versions (frontmatter)
```

---

**End of Version Checking Guide**
