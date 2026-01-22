# Diagnostic Tools Reference Guide

**Version:** 0.4.0
**Last Updated:** 2025-12-02
**Repository:** [synaptic-canvas](https://github.com/randlee/synaptic-canvas)

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Common Workflows](#common-workflows)
3. [Available Tools](#available-tools)
4. [Installation Diagnostics](#installation-diagnostics)
5. [Version Diagnostics](#version-diagnostics)
6. [Registry Diagnostics](#registry-diagnostics)
7. [Package Diagnostics](#package-diagnostics)
8. [Integration Diagnostics](#integration-diagnostics)
9. [Performance Diagnostics](#performance-diagnostics)
10. [Environment Diagnostics](#environment-diagnostics)
11. [JSON Output Examples](#json-output-examples)
12. [Troubleshooting Diagnostic Issues](#troubleshooting-diagnostic-issues)
13. [Creating Custom Diagnostics](#creating-custom-diagnostics)

---

## Quick Start

### Most Common Diagnostic Commands

```bash
# Quick system health check
./scripts/audit-versions.py

# Compare versions across packages
python3 scripts/compare-versions.py

# Validate registry integrity
python3 docs/registries/nuget/validate-registry.py

# Check Git version
git --version

# Check Python version
python3 --version

# Check Node.js version (for sc-repomix-nuget)
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
./scripts/audit-versions.py --verbose

# 5. Validate registry
python3 docs/registries/nuget/validate-registry.py --verbose
```

---

## Common Workflows

This section provides step-by-step workflows for common diagnostic scenarios in the Synaptic Canvas marketplace. Each workflow includes prerequisites, detailed command sequences, expected output, troubleshooting tips, and success criteria.

### Workflow Quick Reference

| Workflow | Duration | When to Use |
|----------|----------|-------------|
| [New User Setup](#new-user-setup-verification) | 5-10 min | First time cloning repository |
| [Pre-Release Verification](#pre-release-verification-workflow) | 15-20 min | Before creating a release |
| [Post-Installation](#post-installation-verification) | 5 min | After installing packages |
| [Version Mismatch](#version-mismatch-investigation) | 10-15 min | When versions don't match |
| [Registry Integrity](#registry-integrity-check-workflow) | 5 min | Before publishing registry |
| [CI/CD Validation](#cicd-validation-workflow) | 10 min | Setting up or debugging CI |
| [Dependency Resolution](#dependency-resolution-workflow) | 10-20 min | Missing or incompatible dependencies |
| [Emergency Diagnostics](#emergency-diagnostics) | 2-5 min | Quick issue identification |
| [Full System Audit](#full-system-audit) | 20-30 min | Comprehensive health check |

---

### New User Setup Verification

**Purpose:** Verify a fresh clone of the repository is properly configured

**Duration:** 5-10 minutes

**When to use:**
- First time cloning the repository
- After resetting local repository
- When onboarding new contributors
- After switching machines

#### Prerequisites

- Git installed (>= 2.7.0)
- Python 3 installed (>= 3.6)
- Repository cloned

#### Step 1: Verify Repository Clone

**Command:**
```bash
cd /path/to/synaptic-canvas
git status
```

**Expected Output:**
```
On branch main
Your branch is up to date with 'origin/main'.

nothing to commit, working tree clean
```

**Success Criteria:** Git recognizes the repository and shows a clean working tree

**Common Issues:**

If you see:
```
fatal: not a git repository
```

**Fix:**
```bash
# Clone the repository
git clone https://github.com/randlee/synaptic-canvas.git
cd synaptic-canvas
```

#### Step 2: Verify Remote Configuration

**Command:**
```bash
git remote -v
```

**Expected Output:**
```
origin  https://github.com/randlee/synaptic-canvas.git (fetch)
origin  https://github.com/randlee/synaptic-canvas.git (push)
```

**Success Criteria:** Origin remote points to correct GitHub repository

**Common Issues:**

If remote is missing or incorrect:
```bash
# Add or update remote
git remote add origin https://github.com/randlee/synaptic-canvas.git
# or
git remote set-url origin https://github.com/randlee/synaptic-canvas.git
```

#### Step 3: Check Git Version

**Command:**
```bash
git --version
```

**Expected Output:**
```
git version 2.39.0 (or higher)
```

**Success Criteria:** Git version >= 2.7.0

**Common Issues:**

If version is too old:
```bash
# macOS
brew upgrade git

# Linux (Ubuntu/Debian)
sudo apt-get update && sudo apt-get upgrade git

# Check new version
git --version
```

#### Step 4: Check Python Version

**Command:**
```bash
python3 --version
```

**Expected Output:**
```
Python 3.11.5 (or higher)
```

**Success Criteria:** Python version >= 3.6

**Common Issues:**

If Python 3 is not found:
```bash
# macOS
brew install python3

# Linux (Ubuntu/Debian)
sudo apt-get install python3

# Verify
python3 --version
```

#### Step 5: Verify Repository Structure

**Command:**
```bash
ls -d packages/ scripts/ docs/ .claude/ version.yaml
```

**Expected Output:**
```
packages/  scripts/  docs/  .claude/  version.yaml
```

**Success Criteria:** All core directories and files exist

**Common Issues:**

If directories are missing:
```bash
# Check you're in the repository root
pwd

# Pull latest changes
git pull origin main

# If still missing, the clone may be incomplete
git fetch --all
git reset --hard origin/main
```

#### Step 6: Verify All Packages Exist

**Command:**
```bash
ls packages/
```

**Expected Output:**
```
sc-delay-tasks/  sc-git-worktree/  sc-repomix-nuget/  sc-manage/
```

**Success Criteria:** All 4 packages are present

**Common Issues:**

If packages are missing, pull latest changes:
```bash
git pull origin main
```

#### Step 7: Check Script Permissions

**Command:**
```bash
ls -l scripts/*.sh
```

**Expected Output:**
```
-rwxr-xr-x  1 user  staff  6045 Dec  2 09:22 scripts/audit-versions.py
-rwxr-xr-x  1 user  staff  5411 Dec  2 09:23 scripts/compare-versions.py
```

**Success Criteria:** Scripts have execute permission (x flag)

**Common Issues:**

If scripts are not executable:
```bash
# Add execute permission to all shell scripts
chmod +x scripts/*.sh

# Verify
ls -l scripts/*.sh
```

#### Step 8: Run Initial Version Audit

**Command:**
```bash
./scripts/audit-versions.py
```

**Expected Output:**
```
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

**Success Criteria:** All checks pass (0 failures)

**Common Issues:**

If audit fails, see [Version Mismatch Investigation](#version-mismatch-investigation) workflow

#### Step 9: Validate Registry

**Command:**
```bash
python3 docs/registries/nuget/validate-registry.py
```

**Expected Output:**
```
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

...

======================================================================
```

**Success Criteria:** Registry validation passes

**Common Issues:**

If validation fails, see [Registry Integrity Check](#registry-integrity-check-workflow) workflow

#### Step 10: Check for Node.js (Optional)

**Purpose:** Required only for `sc-repomix-nuget` package

**Command:**
```bash
node --version
npm --version
```

**Expected Output:**
```
v18.17.0 (or higher)
9.6.7 (or higher)
```

**Success Criteria:** Node.js >= 18.0.0 and npm are installed

**Note:** This is optional unless you plan to use sc-repomix-nuget

**Common Issues:**

If Node.js is not installed:
```bash
# macOS
brew install node

# Linux (using nvm - recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# Verify
node --version
npm --version
```

#### New User Setup Complete!

**Summary Checklist:**
- Repository cloned and clean
- Git remote configured correctly
- Git version >= 2.7.0
- Python 3 installed and working
- All directories and packages present
- Scripts are executable
- Version audit passes
- Registry validation passes
- Node.js installed (optional, for sc-repomix-nuget)

**Next Steps:**
- Read this Diagnostic Tools Reference Guide for available tools
- Read [VERSION-CHECKING-GUIDE.md](VERSION-CHECKING-GUIDE.md) for version management
- Install packages using sc-manage

---

### Pre-Release Verification Workflow

**Purpose:** Comprehensive checks before creating a new release

**Duration:** 15-20 minutes

**When to use:**
- Before creating a new release tag
- Before publishing to marketplace
- Before merging major changes
- As part of release process

#### Prerequisites

- All changes committed
- Working tree clean
- All tests passing locally

#### Step 1: Ensure Clean Working Tree

**Command:**
```bash
git status
```

**Expected Output:**
```
On branch main
Your branch is up to date with 'origin/main'.

nothing to commit, working tree clean
```

**Success Criteria:** No uncommitted changes

**Common Issues:**

If there are uncommitted changes:
```bash
# Commit changes
git add .
git commit -m "chore: prepare for release"

# Or stash for later
git stash
```

#### Step 2: Pull Latest Changes

**Command:**
```bash
git pull origin main
```

**Expected Output:**
```
Already up to date.
```

**Success Criteria:** Local branch is up to date

#### Step 3: Check Current Versions

**Command:**
```bash
python3 scripts/compare-versions.py --verbose
```

**Expected Output:**
```
=== Synaptic Canvas Version Comparison ===

Marketplace Version: 0.4.0

Package: sc-delay-tasks (manifest: 0.4.0)
  ✓ command/delay: 0.4.0
  ✓ skill/delaying-tasks: 0.4.0
  ✓ agent/delay-once: 0.4.0
  ✓ agent/delay-poll: 0.4.0
  ✓ agent/git-pr-check-delay: 0.4.0

Package: sc-git-worktree (manifest: 0.4.0)
  ✓ command/sc-git-worktree: 0.4.0
  ✓ skill/managing-worktrees: 0.4.0
  ✓ agent/worktree-create: 0.4.0
  ✓ agent/worktree-scan: 0.4.0
  ✓ agent/worktree-cleanup: 0.4.0
  ✓ agent/worktree-abort: 0.4.0

...

All versions consistent!
```

**Success Criteria:** All versions are consistent

**Common Issues:**

If versions are inconsistent, see [Version Mismatch Investigation](#version-mismatch-investigation)

#### Step 4: Run Comprehensive Version Audit

**Command:**
```bash
./scripts/audit-versions.py --verbose
```

**Expected Output:**
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

**Success Criteria:** All checks pass with 0 failures and 0 warnings

**Common Issues:**

See troubleshooting in [Troubleshooting Diagnostic Issues](#troubleshooting-diagnostic-issues)

#### Step 5: Validate Registry

**Command:**
```bash
python3 docs/registries/nuget/validate-registry.py --verbose
```

**Expected Output:**
```
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

**Success Criteria:** Registry is valid

#### Step 6: Check All CHANGELOGs Updated

**Command:**
```bash
for pkg in packages/*/; do
    pkg_name=$(basename "$pkg")
    echo "=== $pkg_name CHANGELOG ==="
    head -20 "$pkg/CHANGELOG.md"
    echo ""
done
```

**Success Criteria:** All CHANGELOGs have entries for current version

**Common Issues:**

If CHANGELOG is missing or outdated:
```bash
# Update CHANGELOG.md for the package
# Follow template in docs/RELEASE-NOTES-TEMPLATE.md
```

#### Step 7: Verify Package Manifests

**Command:**
```bash
for pkg in packages/*/; do
    pkg_name=$(basename "$pkg")
    echo "=== $pkg_name manifest ==="
    cat "$pkg/manifest.yaml"
    echo ""
done
```

**Success Criteria:** All manifests have correct version and metadata

#### Step 8: Check README Files

**Command:**
```bash
for pkg in packages/*/; do
    pkg_name=$(basename "$pkg")
    if [[ -f "$pkg/README.md" ]]; then
        echo "✓ $pkg_name: README.md exists"
    else
        echo "✗ $pkg_name: README.md missing"
    fi
done
```

**Expected Output:**
```
✓ sc-delay-tasks: README.md exists
✓ sc-git-worktree: README.md exists
✓ sc-repomix-nuget: README.md exists
✓ sc-manage: README.md exists
```

**Success Criteria:** All packages have READMEs

#### Step 9: Run Tests (if applicable)

**Command:**
```bash
# If you have tests
pytest tests/
# or
npm test
# or
./scripts/run-tests.sh
```

**Success Criteria:** All tests pass

#### Step 10: Check CI/CD Status

**Command:**
```bash
# View recent CI runs
gh run list --limit 5

# Or check on GitHub
# https://github.com/randlee/synaptic-canvas/actions
```

**Success Criteria:** Latest CI runs are passing

#### Step 11: Verify Documentation

**Command:**
```bash
# Check documentation index is up to date
cat docs/DOCUMENTATION-INDEX.md

# Verify all links work (manual check)
```

**Success Criteria:** Documentation is current and complete

#### Step 12: Create Release Tag (if all checks pass)

**Command:**
```bash
# Get current marketplace version
version=$(grep "^version:" version.yaml | awk -F': *' '{print $2}' | tr -d '"')

echo "Creating release for version: $version"

# Create annotated tag
git tag -a "v$version" -m "Release version $version"

# Push tag to remote
git push origin "v$version"
```

**Success Criteria:** Tag created and pushed successfully

#### Step 13: Create GitHub Release

**Command:**
```bash
# Using GitHub CLI
gh release create "v$version" \
    --title "Synaptic Canvas v$version" \
    --notes-file docs/RELEASE-NOTES.md

# Or create manually on GitHub
# https://github.com/randlee/synaptic-canvas/releases/new
```

**Success Criteria:** Release published on GitHub

#### Step 14: Update Registry (if needed)

**Command:**
```bash
# If registry generation script exists
./scripts/generate-registry.sh

# Commit and push
git add docs/registries/nuget/registry.json
git commit -m "chore(registry): update for v$version release"
git push origin main
```

**Success Criteria:** Registry updated and published

#### Step 15: Post-Release Verification

**Command:**
```bash
# Verify tag exists
git tag -l "v$version"

# Verify release on GitHub
gh release view "v$version"

# Check registry is accessible
curl -s https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registries/nuget/registry.json | python3 -m json.tool | head -20
```

**Success Criteria:** Release is accessible and registry is updated

#### Pre-Release Verification Complete!

**Summary Checklist:**
- Working tree is clean
- Local branch is up to date
- All versions are consistent
- Version audit passes
- Registry validation passes
- All CHANGELOGs updated
- All manifests correct
- All READMEs present
- Tests pass
- CI/CD is green
- Documentation is current
- Release tag created
- GitHub release published
- Registry updated
- Post-release verification complete

**Next Steps:**
- Announce release
- Update documentation if needed
- Monitor for issues

---

### Post-Installation Verification

**Purpose:** Verify packages installed correctly

**Duration:** 5 minutes

**When to use:**
- After installing packages with sc-manage
- After manual package installation
- When troubleshooting installation issues

#### Prerequisites

- Packages installed using sc-manage or manual installation
- Repository access

#### Step 1: Verify .claude Directory Exists

**Command:**
```bash
ls -la .claude/
```

**Expected Output:**
```
total 0
drwxr-xr-x  6 user  staff  192 Dec  2 10:00 .
drwxr-xr-x 25 user  staff  800 Dec  2 10:00 ..
drwxr-xr-x  4 user  staff  128 Dec  2 10:00 commands
drwxr-xr-x  5 user  staff  160 Dec  2 10:00 skills
drwxr-xr-x 17 user  staff  544 Dec  2 10:00 agents
drwxr-xr-x  3 user  staff   96 Dec  2 10:00 scripts
```

**Success Criteria:** .claude directory and subdirectories exist

#### Step 2: Check Installed Commands

**Command:**
```bash
ls -la .claude/commands/
```

**Expected Output:**
```
delay.md  sc-git-worktree.md  sc-repomix-nuget.md  sc-manage.md
```

**Success Criteria:** Expected command files are present

#### Step 3: Check Installed Skills

**Command:**
```bash
ls -la .claude/skills/
```

**Expected Output:**
```
delaying-tasks/  managing-worktrees/  generating-nuget-context/  managing-sc-packages/
```

**Success Criteria:** Expected skill directories are present

#### Step 4: Check Installed Agents

**Command:**
```bash
ls -la .claude/agents/ | wc -l
```

**Expected Output:**
```
16 (or expected number)
```

**Success Criteria:** Expected number of agent files

#### Step 5: Verify Agent Content

**Command:**
```bash
# Check a sample agent has proper content
head -20 .claude/agents/delay-once.md
```

**Expected Output:**
```yaml
---
name: delay-once
description: Execute a command after a delay period
version: 0.4.0
---

# Agent: delay-once
...
```

**Success Criteria:** Agent file has proper YAML frontmatter

#### Step 6: Check Installed Scripts

**Command:**
```bash
ls -la .claude/scripts/
```

**Expected Output:**
```
delay-run.py  generate.sh  validate-registry.sh
```

**Success Criteria:** Expected script files are present

#### Step 7: Verify Script Permissions

**Command:**
```bash
ls -l .claude/scripts/*.sh
```

**Expected Output:**
```
-rwxr-xr-x  1 user  staff  1234 Dec  2 10:00 .claude/scripts/generate.sh
-rwxr-xr-x  1 user  staff  2345 Dec  2 10:00 .claude/scripts/validate-registry.sh
```

**Success Criteria:** Scripts have execute permissions

#### Step 8: Test a Sample Command

**Command:**
```bash
# Check command file is readable
cat .claude/commands/delay.md | head -30
```

**Success Criteria:** Command file has proper structure

#### Post-Installation Verification Complete!

**Summary Checklist:**
- .claude directory structure exists
- Commands installed
- Skills installed
- Agents installed
- Scripts installed
- Permissions correct
- Content verified

---

### Version Mismatch Investigation

**Purpose:** Identify and resolve version inconsistencies

**Duration:** 10-15 minutes

**When to use:**
- When audit-versions.py reports failures
- When compare-versions.py shows mismatches
- After updating package versions
- When preparing for release

#### Prerequisites

- Repository access
- Write permissions (to fix issues)

#### Step 1: Identify Mismatches

**Command:**
```bash
python3 scripts/compare-versions.py --verbose --mismatches
```

**Example Output (with issues):**
```
=== Synaptic Canvas Version Comparison ===

Marketplace Version: 0.4.0

Package: sc-delay-tasks (manifest: 0.4.0)
  ✓ command/delay: 0.4.0
  ✗ skill/delaying-tasks: 0.3.0
  ✓ agent/delay-once: 0.4.0
  ✗ agent/delay-poll: 0.3.0

Version mismatches found
```

**Note:** Record which artifacts have mismatches

#### Step 2: Verify Package Manifest Version

**Command:**
```bash
# Check the package manifest
grep "^version:" packages/sc-delay-tasks/manifest.yaml
```

**Output:**
```
version: 0.4.0
```

**Note:** This is the target version for all artifacts

#### Step 3: Check Individual Artifact Versions

**Command:**
```bash
# Check the skill version
grep "^version:" packages/sc-delay-tasks/skills/delaying-tasks/SKILL.md

# Check the agent version
grep "^version:" packages/sc-delay-tasks/agents/delay-poll.md
```

**Output:**
```
version: 0.3.0
version: 0.3.0
```

**Analysis:** These artifacts need to be updated to 0.4.0

#### Step 4: Determine Fix Strategy

**Option A: Use set-package-version.py (Recommended)**

For package-wide updates:
```bash
python3 scripts/set-package-version.py sc-delay-tasks 0.4.0 --dry-run
```

**Option B: Manual Update**

For single artifact updates:
```bash
# Edit the file manually
vim packages/sc-delay-tasks/skills/delaying-tasks/SKILL.md
# Update version: 0.3.0 -> version: 0.4.0
```

#### Step 5: Apply Fix (Automated Method)

**Command:**
```bash
# Sync all artifacts in sc-delay-tasks package
python3 scripts/set-package-version.py sc-delay-tasks 0.4.0

# Verify changes
git diff
```

**Expected Output:**
```
Syncing sc-delay-tasks to version 0.4.0...
  ✓ Updated: packages/sc-delay-tasks/manifest.yaml
  ✓ Updated: packages/sc-delay-tasks/skills/delaying-tasks/SKILL.md
  ✓ Updated: packages/sc-delay-tasks/agents/delay-poll.md
Updated 3 file(s) in sc-delay-tasks
```

#### Step 6: Verify Fix

**Command:**
```bash
python3 scripts/compare-versions.py --verbose
```

**Expected Output:**
```
=== Synaptic Canvas Version Comparison ===

Marketplace Version: 0.4.0

Package: sc-delay-tasks (manifest: 0.4.0)
  ✓ command/delay: 0.4.0
  ✓ skill/delaying-tasks: 0.4.0
  ✓ agent/delay-once: 0.4.0
  ✓ agent/delay-poll: 0.4.0

All versions consistent!
```

**Success Criteria:** No mismatches reported

#### Step 7: Run Full Audit

**Command:**
```bash
./scripts/audit-versions.py
```

**Expected Output:**
```
=== Synaptic Canvas Version Audit ===
...
=== Audit Results ===
Total checks: 42
Passed: 42
Failed: 0
Warnings: 0

All checks passed!
```

**Success Criteria:** All checks pass

#### Step 8: Commit Changes

**Command:**
```bash
# Review changes
git diff

# Stage changes
git add packages/sc-delay-tasks/

# Commit
git commit -m "fix(sc-delay-tasks): sync artifact versions to 0.4.0"

# Push
git push origin main
```

**Success Criteria:** Changes committed and pushed

#### Version Mismatch Investigation Complete!

**Summary Checklist:**
- Mismatches identified
- Target version determined
- Fix strategy selected
- Changes applied
- Fix verified
- Audit passes
- Changes committed

---

### Registry Integrity Check Workflow

**Purpose:** Validate registry structure and content

**Duration:** 5 minutes

**When to use:**
- Before publishing registry
- After updating registry
- When troubleshooting registry issues
- As part of release process

#### Prerequisites

- Registry file exists
- Python 3 installed
- Schema file available

#### Step 1: Verify Registry File Exists

**Command:**
```bash
ls -l docs/registries/nuget/registry.json
```

**Expected Output:**
```
-rw-r--r--  1 user  staff  5673 Dec  2 09:25 docs/registries/nuget/registry.json
```

**Success Criteria:** File exists and is readable

#### Step 2: Validate JSON Syntax

**Command:**
```bash
python3 -m json.tool docs/registries/nuget/registry.json > /dev/null
```

**Expected Output:**
```
(no output - success)
```

**Success Criteria:** No syntax errors

**Common Issues:**

If JSON is invalid:
```
Expecting ',' delimiter: line 42 column 5 (char 1234)
```

**Fix:** Edit registry.json and fix syntax error at indicated line

#### Step 3: Run Registry Validation

**Command:**
```bash
python3 docs/registries/nuget/validate-registry.py --verbose
```

**Expected Output:**
```
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
...
```

**Success Criteria:** Status is VALID

#### Step 4: Check Registry Version

**Command:**
```bash
python3 -c "import json; print('Registry version:', json.load(open('docs/registries/nuget/registry.json'))['version'])"
```

**Expected Output:**
```
Registry version: 0.4.0
```

**Success Criteria:** Version matches marketplace version

#### Step 5: Verify Package Count

**Command:**
```bash
# Count packages in registry
python3 -c "import json; print('Registry packages:', len(json.load(open('docs/registries/nuget/registry.json'))['packages']))"

# Count actual packages
echo "Actual packages: $(ls -d packages/*/ | wc -l)"
```

**Expected Output:**
```
Registry packages: 4
Actual packages: 4
```

**Success Criteria:** Counts match

#### Step 6: Validate Package Metadata

**Command:**
```bash
# Check each package has required fields
python3 << 'EOF'
import json

registry = json.load(open('docs/registries/nuget/registry.json'))
required_fields = ['name', 'version', 'description', 'author', 'license']

for pkg_name, pkg_data in registry['packages'].items():
    print(f"\n{pkg_name}:")
    for field in required_fields:
        if field in pkg_data:
            print(f"  ✓ {field}: {pkg_data[field]}")
        else:
            print(f"  ✗ {field}: MISSING")
EOF
```

**Success Criteria:** All packages have required fields

#### Step 7: Check Registry Statistics

**Command:**
```bash
python3 -c "import json; import pprint; pprint.pprint(json.load(open('docs/registries/nuget/registry.json'))['metadata'])"
```

**Expected Output:**
```python
{'categories': {...},
 'registryVersion': '0.4.0',
 'schemaVersion': '1.0.0',
 'totalAgents': 16,
 'totalCommands': 4,
 'totalPackages': 4,
 'totalScripts': 2,
 'totalSkills': 6}
```

**Success Criteria:** Statistics look reasonable

#### Step 8: Validate Against Schema

**Command:**
```bash
python3 docs/registries/nuget/validate-registry.py --json | python3 -m json.tool
```

**Expected Output:**
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

**Success Criteria:** valid is true, error_count is 0

#### Registry Integrity Check Complete!

**Summary Checklist:**
- Registry file exists
- JSON syntax valid
- Schema validation passes
- Version correct
- Package count matches
- Metadata complete
- Statistics accurate

---

### CI/CD Validation Workflow

**Purpose:** Verify CI/CD pipeline configuration

**Duration:** 10 minutes

**When to use:**
- Setting up new CI/CD workflows
- Debugging CI failures
- After updating workflow files
- Before major releases

#### Prerequisites

- GitHub Actions workflows configured
- Repository access
- GitHub CLI (gh) installed (optional)

#### Step 1: Check Workflow Files Exist

**Command:**
```bash
ls -la .github/workflows/
```

**Expected Output:**
```
version-audit.yml
tests.yml
```

**Success Criteria:** Workflow files present

#### Step 2: Validate Workflow YAML Syntax

**Command:**
```bash
for workflow in .github/workflows/*.yml; do
    echo "Validating $workflow..."
    python3 -c "import yaml; yaml.safe_load(open('$workflow'))"
    if [ $? -eq 0 ]; then
        echo "  ✓ Valid YAML"
    else
        echo "  ✗ Invalid YAML"
    fi
done
```

**Success Criteria:** All workflows have valid YAML

#### Step 3: Check Recent CI Runs

**Command:**
```bash
# Using GitHub CLI
gh run list --limit 5

# Or check on web
# https://github.com/randlee/synaptic-canvas/actions
```

**Expected Output:**
```
STATUS  TITLE                           WORKFLOW        BRANCH  EVENT  ID
✓       Version audit                   version-audit   main    push   123456
✓       Tests                           tests           main    push   123455
```

**Success Criteria:** Recent runs are passing

#### Step 4: Test Version Audit Locally

**Command:**
```bash
# Run the same command that CI runs
./scripts/audit-versions.py
```

**Expected Output:**
```
=== Synaptic Canvas Version Audit ===
...
All checks passed!
```

**Success Criteria:** Passes locally (will likely pass in CI)

#### Step 5: Test Registry Validation Locally

**Command:**
```bash
# Run the same validation CI uses
python3 docs/registries/nuget/validate-registry.py --json
```

**Expected Output:**
```json
{
  "valid": true,
  ...
}
```

**Success Criteria:** Valid locally

#### Step 6: Check CI Environment

**Command:**
```bash
# View workflow file to see environment
cat .github/workflows/version-audit.yml
```

**Check for:**
- Correct runner (ubuntu-latest, macos-latest, etc.)
- Required dependencies installed
- Correct checkout action
- Proper permissions

#### Step 7: Trigger Manual CI Run (Optional)

**Command:**
```bash
# Using GitHub CLI
gh workflow run version-audit.yml

# Check status
gh run list --workflow=version-audit.yml --limit 1
```

**Success Criteria:** Workflow runs successfully

#### CI/CD Validation Complete!

**Summary Checklist:**
- Workflow files exist
- YAML syntax valid
- Recent runs passing
- Local tests pass
- Environment configured correctly
- Manual run successful (if tested)

---

### Dependency Resolution Workflow

**Purpose:** Verify and resolve dependency issues

**Duration:** 10-20 minutes

**When to use:**
- Setting up new development environment
- Troubleshooting installation issues
- After system updates
- Before contributing

#### Prerequisites

- System access
- Installation permissions

#### Step 1: Check Git Installation

**Command:**
```bash
git --version
```

**Expected:** >= 2.7.0

**Fix if needed:**
```bash
# macOS
brew install git

# Linux
sudo apt-get install git

# Windows
# Download from git-scm.com
```

#### Step 2: Check Python Installation

**Command:**
```bash
python3 --version
```

**Expected:** >= 3.6

**Fix if needed:**
```bash
# macOS
brew install python3

# Linux
sudo apt-get install python3

# Windows
# Download from python.org
```

#### Step 3: Check Node.js (for sc-repomix-nuget)

**Command:**
```bash
node --version
npm --version
```

**Expected:** Node >= 18.0

**Fix if needed:**
```bash
# Using nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# macOS (Homebrew)
brew install node

# Linux
sudo apt-get install nodejs npm
```

#### Step 4: Verify All Dependencies

**Command:**
```bash
# Create dependency check script
cat > /tmp/check-deps.sh << 'EOF'
#!/bin/bash

echo "=== Dependency Check ==="
echo ""

# Git
git_version=$(git --version 2>/dev/null | awk '{print $3}')
if [[ -n "$git_version" ]]; then
    echo "✓ Git: $git_version"
else
    echo "✗ Git: NOT FOUND"
fi

# Python 3
python_version=$(python3 --version 2>/dev/null | awk '{print $2}')
if [[ -n "$python_version" ]]; then
    echo "✓ Python 3: $python_version"
else
    echo "✗ Python 3: NOT FOUND"
fi

# Node.js (optional)
node_version=$(node --version 2>/dev/null)
if [[ -n "$node_version" ]]; then
    echo "✓ Node.js: $node_version"
else
    echo "⚠ Node.js: NOT FOUND (optional, needed for sc-repomix-nuget)"
fi

# npm (optional)
npm_version=$(npm --version 2>/dev/null)
if [[ -n "$npm_version" ]]; then
    echo "✓ npm: $npm_version"
else
    echo "⚠ npm: NOT FOUND (optional, needed for sc-repomix-nuget)"
fi

echo ""
EOF

chmod +x /tmp/check-deps.sh
/tmp/check-deps.sh
```

**Success Criteria:** All required dependencies present

#### Dependency Resolution Complete!

**Summary Checklist:**
- Git installed and correct version
- Python 3 installed and correct version
- Node.js installed (if using sc-repomix-nuget)
- npm installed (if using sc-repomix-nuget)

See [DEPENDENCY-VALIDATION.md](DEPENDENCY-VALIDATION.md) for more details.

---

### Emergency Diagnostics

**Purpose:** Quick issue identification

**Duration:** 2-5 minutes

**When to use:**
- Something is broken
- Need quick status check
- Before asking for help

#### Quick Diagnostic Commands

```bash
# 1. Check Git status
git status

# 2. Quick version check
./scripts/audit-versions.py

# 3. Check registry
python3 docs/registries/nuget/validate-registry.py

# 4. Check dependencies
git --version && python3 --version

# 5. Check recent commits
git log --oneline -5
```

**Collect output and report issues**

---

### Full System Audit

**Purpose:** Comprehensive system health check

**Duration:** 20-30 minutes

**When to use:**
- Periodic maintenance
- Before major changes
- Troubleshooting complex issues
- Documentation updates

#### Run All Diagnostics

```bash
echo "=== FULL SYSTEM AUDIT ===" > audit-report.txt
echo "Date: $(date)" >> audit-report.txt
echo "" >> audit-report.txt

echo "=== Git Version ===" >> audit-report.txt
git --version >> audit-report.txt
echo "" >> audit-report.txt

echo "=== Python Version ===" >> audit-report.txt
python3 --version >> audit-report.txt
echo "" >> audit-report.txt

echo "=== Version Audit ===" >> audit-report.txt
./scripts/audit-versions.py --verbose >> audit-report.txt
echo "" >> audit-report.txt

echo "=== Version Comparison ===" >> audit-report.txt
python3 scripts/compare-versions.py --verbose >> audit-report.txt
echo "" >> audit-report.txt

echo "=== Registry Validation ===" >> audit-report.txt
python3 docs/registries/nuget/validate-registry.py --verbose >> audit-report.txt
echo "" >> audit-report.txt

echo "Audit complete. See audit-report.txt"
```

**Review audit-report.txt for any issues**

---

## Available Tools

### Core Diagnostic Scripts

#### 1. `scripts/audit-versions.py`

**Purpose:** Verify version consistency across packages and artifacts

**Location:** `/Users/randlee/Documents/github/synaptic-canvas/scripts/audit-versions.py`

**Usage:**
```bash
./scripts/audit-versions.py [OPTIONS]

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
$ ./scripts/audit-versions.py

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
$ ./scripts/audit-versions.py

=== Synaptic Canvas Version Audit ===

Checking commands...
✗ FAIL Command: delay: Missing version frontmatter

Checking skills...
Checking agents...
Checking version consistency...
✗ FAIL Command in sc-delay-tasks: Version mismatch: command=0.3.0, package=0.4.0

Checking CHANGELOGs...
⚠ WARN CHANGELOG for sc-repomix-nuget: No CHANGELOG.md found

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
✗ FAIL Command in sc-delay-tasks: Version mismatch: command=0.3.0, package=0.4.0
```
**Fix:** Use set-package-version.py to update:
```bash
python3 scripts/set-package-version.py sc-delay-tasks 0.4.0
```

⚠️ **Missing CHANGELOG:**
```
⚠ WARN CHANGELOG for sc-repomix-nuget: No CHANGELOG.md found
```
**Fix:** Create CHANGELOG.md in package directory following template.

---

#### 2. `scripts/set-package-version.py`

**Purpose:** Set package versions and regenerate all registry files

**Location:** `/Users/randlee/Documents/github/synaptic-canvas/scripts/set-package-version.py`

**Usage:**
```bash
python3 scripts/set-package-version.py <package> <version>
python3 scripts/set-package-version.py --all <version>
python3 scripts/set-package-version.py --all --marketplace <version>

Options:
  --dry-run            Show changes without applying
  --force              Allow version decrement (use with caution)
```

**Examples:**

**Update single package:**
```bash
# Update sc-delay-tasks to version 0.9.0
python3 scripts/set-package-version.py sc-delay-tasks 0.9.0

# Output:
Setting version to 0.9.0
============================================================
sc-delay-tasks: 0.8.0 -> 0.9.0
  ✓ packages/sc-delay-tasks/manifest.yaml
  ✓ packages/sc-delay-tasks/.claude-plugin/plugin.json
  ✓ packages/sc-delay-tasks/commands/delay.md
  ...
============================================================
Regenerating registry files...
  ✓ .claude-plugin/marketplace.json
  ✓ .claude-plugin/registry.json
  ✓ docs/registries/nuget/registry.json
```

**Update all packages:**
```bash
# Update ALL packages to version 1.0.0
python3 scripts/set-package-version.py --all 1.0.0
```

**Update all packages AND marketplace version:**
```bash
# Update all packages and marketplace platform version
python3 scripts/set-package-version.py --all --marketplace 1.0.0
```

**Dry run (preview changes):**
```bash
python3 scripts/set-package-version.py --all 0.9.0 --dry-run

# Shows what would be updated without making changes
```

**Exit Codes:**
- `0` - Success
- `1` - Validation error or version decrement attempted

**Safety Features:**
- **Version decrement protection**: Errors if you try to set a lower version
- **Dry-run mode**: Preview all changes before applying
- **Skip detection**: Packages already at target version are skipped

**What It Updates:**

For each package:
- ✅ `packages/<name>/manifest.yaml`
- ✅ `packages/<name>/.claude-plugin/plugin.json`
- ✅ `packages/<name>/commands/*.md` (version frontmatter)
- ✅ `packages/<name>/skills/*/SKILL.md` (version frontmatter)
- ✅ `packages/<name>/agents/*.md` (version frontmatter)

Registry files (regenerated automatically):
- ✅ `.claude-plugin/marketplace.json`
- ✅ `.claude-plugin/registry.json`
- ✅ `docs/registries/nuget/registry.json`

If `--marketplace`:
- ✅ `version.yaml`

**Version Format:**

Must be semantic version (SemVer):
- ✅ Valid: `0.4.0`, `1.0.0`, `2.1.3`
- ❌ Invalid: `0.4`, `v0.4.0`, `1.0.0-beta` (pre-release tags not supported)

---

#### 3. `scripts/compare-versions.py`

**Purpose:** Compare version numbers across packages and display discrepancies

**Location:** `/Users/randlee/Documents/github/synaptic-canvapython3 scripts/compare-versions.py`

**Usage:**
```bash
python3 scripts/compare-versions.py [OPTIONS]

Options:
  --by-package    Show versions grouped by package (default)
  --mismatches    Only show packages with version mismatches
  --verbose       Show all artifact versions individually
  --json          Output as JSON
```

**Examples:**

**Basic comparison:**
```bash
python3 scripts/compare-versions.py

# Output:
=== Synaptic Canvas Version Comparison ===

Marketplace Version: 0.4.0

Package: sc-delay-tasks (manifest: 0.4.0)

Package: sc-git-worktree (manifest: 0.4.0)

Package: sc-manage (manifest: 0.4.0)

Package: sc-repomix-nuget (manifest: 0.4.0)

All versions consistent!
```

**Show only mismatches:**
```bash
python3 scripts/compare-versions.py --mismatches

# Output:
=== Synaptic Canvas Version Comparison ===

Marketplace Version: 0.4.0

Package: sc-delay-tasks (manifest: 0.4.0)

(No other output if all versions consistent)
```

**Verbose output (show all artifacts):**
```bash
python3 scripts/compare-versions.py --verbose

# Output:
=== Synaptic Canvas Version Comparison ===

Marketplace Version: 0.4.0

Package: sc-delay-tasks (manifest: 0.4.0)
  ✓ command/delay: 0.4.0
  ✓ skill/delaying-tasks: 0.4.0
  ✓ agent/delay-once: 0.4.0
  ✓ agent/delay-poll: 0.4.0
  ✓ agent/git-pr-check-delay: 0.4.0

Package: sc-git-worktree (manifest: 0.4.0)
  ✓ command/sc-git-worktree: 0.4.0
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
python3 scripts/compare-versions.py --verbose

# Output:
=== Synaptic Canvas Version Comparison ===

Marketplace Version: 0.4.0

Package: sc-delay-tasks (manifest: 0.4.0)
  ✓ command/delay: 0.4.0
  ✗ skill/delaying-tasks: 0.3.0
  ✓ agent/delay-once: 0.4.0

Package: sc-git-worktree (manifest: 0.4.0)
  ✓ command/sc-git-worktree: 0.4.0

Version mismatches found
```

**JSON output:**
```bash
python3 scripts/compare-versions.py --json

# Output:
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

  1. Package 'sc-delay-tasks': Invalid version format '0.4'
  2. Package 'sc-git-worktree': Missing required field: 'description'
  3. Package 'sc-repomix-nuget': Invalid repo URL (must be https://github.com/...)

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
    "Package 'sc-delay-tasks': Invalid version format '0.4'",
    "Package 'sc-git-worktree': Missing required field: 'description'"
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
Package 'sc-delay-tasks': Invalid version format '0.4'
```
**Fix:** Use three-part SemVer: `0.4.0`

❌ **Invalid package name:**
```
Invalid package name: 'DelayTasks' (must be lowercase with hyphens)
```
**Fix:** Use lowercase with hyphens: `sc-delay-tasks`

❌ **Invalid status:**
```
Package 'sc-delay-tasks': Invalid status 'production'
```
**Fix:** Use valid status: `alpha`, `beta`, `stable`, `deprecated`, or `archived`

❌ **Invalid tier:**
```
Package 'sc-delay-tasks': Tier must be integer 0-5, got 10
```
**Fix:** Use tier between 0-5

❌ **Invalid URL:**
```
Package 'sc-delay-tasks': Invalid repo URL (must be https://github.com/...)
```
**Fix:** Use proper GitHub URL format

❌ **Missing tags:**
```
Package 'sc-delay-tasks': 'tags' must have at least 1 item
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

**Required for:** `sc-repomix-nuget` package

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
sc-delay-tasks/  sc-git-worktree/  sc-repomix-nuget/  sc-manage/
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
delay.md  sc-git-worktree.md  sc-repomix-nuget.md  sc-manage.md
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
ls -l scripts/audit-versions.py

# Expected output:
-rwxr-xr-x  1 user  staff  6045 Dec  2 09:22 scripts/audit-versions.py
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
chmod +x scripts/audit-versions.py

# Add execute permission to all shell scripts
find scripts/ -name "*.sh" -type f -exec chmod +x {} \;
```

**Check Python scripts are readable:**
```bash
ls -l scripts/set-package-version.py

# Expected output:
-rwxr-xr-x  1 user  staff  9163 Dec  2 09:23 scripts/set-package-version.py
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
sc-delay-tasks: 0.4.0
sc-git-worktree: 0.4.0
sc-repomix-nuget: 0.4.0
sc-manage: 0.4.0
```

**Check specific package version:**
```bash
# Check sc-delay-tasks version
grep "^version:" packages/sc-delay-tasks/manifest.yaml | awk -F': *' '{print $2}' | tr -d '"'

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
sc-delay-tasks/delay: 0.4.0
sc-git-worktree/sc-git-worktree: 0.4.0
sc-repomix-nuget/sc-repomix-nuget: 0.4.0
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
sc-delay-tasks/delaying-tasks: 0.4.0
sc-git-worktree/managing-worktrees: 0.4.0
sc-repomix-nuget/generating-nuget-context: 0.4.0
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
./scripts/audit-versions.py

# Or check manually for a specific package
package_name="sc-delay-tasks"
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
sc-delay-tasks
sc-git-worktree
sc-repomix-nuget
sc-manage
```

---

### Check Registry Metadata

**View registry metadata:**
```bash
python3 -c "import json; import pprint; pprint.pprint(json.load(open('docs/registries/nuget/registry.json'))['metadata'])"

# Output:
{'categories': {'automation': ['sc-delay-tasks'],
                'git': ['sc-git-worktree'],
                'management': ['sc-manage'],
                'nuget': ['sc-repomix-nuget'],
                'workflow': ['sc-delay-tasks', 'sc-git-worktree']},
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
# Check sc-delay-tasks package
package="sc-delay-tasks"

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
Checking sc-delay-tasks structure...
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
python3 -c "import yaml; yaml.safe_load(open('packages/sc-delay-tasks/manifest.yaml'))"

if [ $? -eq 0 ]; then
    echo "✓ Manifest is valid YAML"
else
    echo "✗ Manifest has invalid YAML syntax"
fi
```

**Check required manifest fields:**
```bash
package="sc-delay-tasks"
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
package="sc-delay-tasks"

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
package="sc-delay-tasks"
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
./scripts/audit-versions.py

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
1.2M    packages/sc-delay-tasks
800K    packages/sc-git-worktree
2.5M    packages/sc-repomix-nuget
1.0M    packages/sc-manage
```

---

### Check Execution Times

**Measure audit script performance:**
```bash
# Time the audit script
time ./scripts/audit-versions.py

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
time python3 scripts/set-package-version.py --package sc-delay-tasks --version 0.4.0 --dry-run

# Output:
Syncing sc-delay-tasks to version 0.4.0...
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
sh scripts/audit-versions.py

# If it works, scripts are POSIX compatible
```

---

## JSON Output Examples

### Audit Script JSON

Currently, `audit-versions.py` does not output JSON. Consider using `compare-versions.py --json` for structured output.

**Feature request:** Add `--json` flag to `audit-versions.py`

---

### Compare Versions JSON

```bash
python3 scripts/compare-versions.py --json
```

**Output:**
```json
{
  "marketplace": "0.4.0",
  "packages": [
    {
      "name": "sc-delay-tasks",
      "version": "0.4.0",
      "consistent": true
    },
    {
      "name": "sc-git-worktree",
      "version": "0.4.0",
      "consistent": true
    },
    {
      "name": "sc-manage",
      "version": "0.4.0",
      "consistent": true
    },
    {
      "name": "sc-repomix-nuget",
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
      "name": "sc-delay-tasks",
      "version": "0.4.0",
      "consistent": false
    },
    {
      "name": "sc-git-worktree",
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
    "Package 'sc-delay-tasks': Invalid version format '0.4'",
    "Package 'sc-git-worktree': Missing required field: 'description'",
    "Package 'sc-repomix-nuget': Invalid repo URL (must be https://github.com/...)"
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
$ ./scripts/audit-versions.py
-bash: ./scripts/audit-versions.py: Permission denied
```

**Solution:**
```bash
# Add execute permission
chmod +x scripts/audit-versions.py

# Run again
./scripts/audit-versions.py
```

---

#### 2. Python Script Fails to Run

**Problem:**
```bash
$ python3 scripts/set-package-version.py
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
python scripts/set-package-version.py
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
$ ./scripts/audit-versions.py
✗ FAIL Command in sc-delay-tasks: Version mismatch: command=0.3.0, package=0.4.0
```

**Solution:**
```bash
# Use sync script to fix
python3 scripts/set-package-version.py --package sc-delay-tasks --version 0.4.0

# Verify fix
./scripts/audit-versions.py
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
        run: ./scripts/audit-versions.py

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
- [ ] Run `./scripts/audit-versions.py`
- [ ] Run `python3 scripts/compare-versions.py`
- [ ] Check no uncommitted version changes

**Pre-Release Checklist:**
- [ ] Run `./scripts/audit-versions.py --verbose`
- [ ] Run `python3 docs/registries/nuget/validate-registry.py --verbose`
- [ ] Verify all package versions match
- [ ] Check all CHANGELOGs are updated
- [ ] Validate registry metadata
- [ ] Test on macOS, Linux, and Windows

---

## Related Documentation

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
| Node.js | 18.0 | 18.17+ | sc-repomix-nuget |
| npm | 8.0 | 9.6+ | Package management |
| Bash | 4.0 | 5.0+ | Shell scripts |

---

### Exit Code Reference

| Exit Code | Meaning | Tools |
|-----------|---------|-------|
| 0 | Success | All |
| 1 | Validation failure | audit-versions.py, compare-versions.py, validate-registry.py |
| 2 | Critical error | audit-versions.py |

---

**End of Diagnostic Tools Reference Guide**
