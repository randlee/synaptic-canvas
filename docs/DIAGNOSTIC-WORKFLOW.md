# Diagnostic Workflow Guide

**Version:** 0.4.0
**Last Updated:** 2025-12-02
**Repository:** [synaptic-canvas](https://github.com/randlee/synaptic-canvas)

---

## Table of Contents

1. [Overview](#overview)
2. [New User Setup Verification](#new-user-setup-verification)
3. [Pre-Release Verification Workflow](#pre-release-verification-workflow)
4. [Post-Installation Verification](#post-installation-verification)
5. [Version Mismatch Investigation](#version-mismatch-investigation)
6. [Registry Integrity Check](#registry-integrity-check)
7. [CI/CD Validation Workflow](#cicd-validation-workflow)
8. [Dependency Resolution Workflow](#dependency-resolution-workflow)
9. [Emergency Diagnostics](#emergency-diagnostics)
10. [Full System Audit](#full-system-audit)

---

## Overview

This guide provides step-by-step workflows for common diagnostic scenarios in the Synaptic Canvas marketplace. Each workflow includes:

- **Prerequisites:** What you need before starting
- **Steps:** Detailed command sequences
- **Expected Output:** What success looks like
- **Troubleshooting:** How to fix common issues
- **Success Criteria:** How to know you're done

### Quick Reference

| Workflow | Duration | When to Use |
|----------|----------|-------------|
| New User Setup | 5-10 min | First time cloning repository |
| Pre-Release Verification | 15-20 min | Before creating a release |
| Post-Installation | 5 min | After installing packages |
| Version Mismatch | 10-15 min | When versions don't match |
| Registry Integrity | 5 min | Before publishing registry |
| CI/CD Validation | 10 min | Setting up or debugging CI |
| Dependency Resolution | 10-20 min | Missing or incompatible dependencies |
| Emergency Diagnostics | 2-5 min | Quick issue identification |
| Full System Audit | 20-30 min | Comprehensive health check |

---

## New User Setup Verification

**Purpose:** Verify a fresh clone of the repository is properly configured

**Duration:** 5-10 minutes

**When to use:**
- First time cloning the repository
- After resetting local repository
- When onboarding new contributors
- After switching machines

---

### Prerequisites

- Git installed (>= 2.7.0)
- Python 3 installed (>= 3.6)
- Repository cloned

---

### Step 1: Verify Repository Clone

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

**✅ Success Criteria:** Git recognizes the repository and shows a clean working tree

**❌ Common Issues:**

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

---

### Step 2: Verify Remote Configuration

**Command:**
```bash
git remote -v
```

**Expected Output:**
```
origin  https://github.com/randlee/synaptic-canvas.git (fetch)
origin  https://github.com/randlee/synaptic-canvas.git (push)
```

**✅ Success Criteria:** Origin remote points to correct GitHub repository

**❌ Common Issues:**

If remote is missing or incorrect:
```bash
# Add or update remote
git remote add origin https://github.com/randlee/synaptic-canvas.git
# or
git remote set-url origin https://github.com/randlee/synaptic-canvas.git
```

---

### Step 3: Check Git Version

**Command:**
```bash
git --version
```

**Expected Output:**
```
git version 2.39.0 (or higher)
```

**✅ Success Criteria:** Git version >= 2.7.0

**❌ Common Issues:**

If version is too old:
```bash
# macOS
brew upgrade git

# Linux (Ubuntu/Debian)
sudo apt-get update && sudo apt-get upgrade git

# Check new version
git --version
```

---

### Step 4: Check Python Version

**Command:**
```bash
python3 --version
```

**Expected Output:**
```
Python 3.11.5 (or higher)
```

**✅ Success Criteria:** Python version >= 3.6

**❌ Common Issues:**

If Python 3 is not found:
```bash
# macOS
brew install python3

# Linux (Ubuntu/Debian)
sudo apt-get install python3

# Verify
python3 --version
```

---

### Step 5: Verify Repository Structure

**Command:**
```bash
ls -d packages/ scripts/ docs/ .claude/ version.yaml
```

**Expected Output:**
```
packages/  scripts/  docs/  .claude/  version.yaml
```

**✅ Success Criteria:** All core directories and files exist

**❌ Common Issues:**

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

---

### Step 6: Verify All Packages Exist

**Command:**
```bash
ls packages/
```

**Expected Output:**
```
sc-delay-tasks/  sc-git-worktree/  sc-repomix-nuget/  sc-manage/
```

**✅ Success Criteria:** All 4 packages are present

**❌ Common Issues:**

If packages are missing, pull latest changes:
```bash
git pull origin main
```

---

### Step 7: Check Script Permissions

**Command:**
```bash
ls -l scripts/*.sh
```

**Expected Output:**
```
-rwxr-xr-x  1 user  staff  6045 Dec  2 09:22 scripts/audit-versions.py
-rwxr-xr-x  1 user  staff  5411 Dec  2 09:23 scripts/compare-versions.py
```

**✅ Success Criteria:** Scripts have execute permission (x flag)

**❌ Common Issues:**

If scripts are not executable:
```bash
# Add execute permission to all shell scripts
chmod +x scripts/*.sh

# Verify
ls -l scripts/*.sh
```

---

### Step 8: Run Initial Version Audit

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

**✅ Success Criteria:** All checks pass (0 failures)

**❌ Common Issues:**

If audit fails, see [Version Mismatch Investigation](#version-mismatch-investigation) workflow

---

### Step 9: Validate Registry

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

**✅ Success Criteria:** Registry validation passes

**❌ Common Issues:**

If validation fails, see [Registry Integrity Check](#registry-integrity-check) workflow

---

### Step 10: Check for Node.js (Optional)

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

**✅ Success Criteria:** Node.js >= 18.0.0 and npm are installed

**⚠️ Note:** This is optional unless you plan to use sc-repomix-nuget

**❌ Common Issues:**

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

---

### New User Setup Complete!

**Summary Checklist:**
- ✅ Repository cloned and clean
- ✅ Git remote configured correctly
- ✅ Git version >= 2.7.0
- ✅ Python 3 installed and working
- ✅ All directories and packages present
- ✅ Scripts are executable
- ✅ Version audit passes
- ✅ Registry validation passes
- ✅ Node.js installed (optional, for sc-repomix-nuget)

**Next Steps:**
- Read [DIAGNOSTIC-TOOLS.md](DIAGNOSTIC-TOOLS.md) for available tools
- Read [VERSION-CHECKING-GUIDE.md](VERSION-CHECKING-GUIDE.md) for version management
- Install packages using sc-manage

---

## Pre-Release Verification Workflow

**Purpose:** Comprehensive checks before creating a new release

**Duration:** 15-20 minutes

**When to use:**
- Before creating a new release tag
- Before publishing to marketplace
- Before merging major changes
- As part of release process

---

### Prerequisites

- All changes committed
- Working tree clean
- All tests passing locally

---

### Step 1: Ensure Clean Working Tree

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

**✅ Success Criteria:** No uncommitted changes

**❌ Common Issues:**

If there are uncommitted changes:
```bash
# Commit changes
git add .
git commit -m "chore: prepare for release"

# Or stash for later
git stash
```

---

### Step 2: Pull Latest Changes

**Command:**
```bash
git pull origin main
```

**Expected Output:**
```
Already up to date.
```

**✅ Success Criteria:** Local branch is up to date

---

### Step 3: Check Current Versions

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

**✅ Success Criteria:** All versions are consistent

**❌ Common Issues:**

If versions are inconsistent, see [Version Mismatch Investigation](#version-mismatch-investigation)

---

### Step 4: Run Comprehensive Version Audit

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

**✅ Success Criteria:** All checks pass with 0 failures and 0 warnings

**❌ Common Issues:**

See troubleshooting in [DIAGNOSTIC-TOOLS.md](DIAGNOSTIC-TOOLS.md#2-scripts-audit-versionssh)

---

### Step 5: Validate Registry

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

**✅ Success Criteria:** Registry is valid

---

### Step 6: Check All CHANGELOGs Updated

**Command:**
```bash
for pkg in packages/*/; do
    pkg_name=$(basename "$pkg")
    echo "=== $pkg_name CHANGELOG ==="
    head -20 "$pkg/CHANGELOG.md"
    echo ""
done
```

**✅ Success Criteria:** All CHANGELOGs have entries for current version

**❌ Common Issues:**

If CHANGELOG is missing or outdated:
```bash
# Update CHANGELOG.md for the package
# Follow template in docs/RELEASE-NOTES-TEMPLATE.md
```

---

### Step 7: Verify Package Manifests

**Command:**
```bash
for pkg in packages/*/; do
    pkg_name=$(basename "$pkg")
    echo "=== $pkg_name manifest ==="
    cat "$pkg/manifest.yaml"
    echo ""
done
```

**✅ Success Criteria:** All manifests have correct version and metadata

---

### Step 8: Check README Files

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

**✅ Success Criteria:** All packages have READMEs

---

### Step 9: Run Tests (if applicable)

**Command:**
```bash
# If you have tests
pytest tests/
# or
npm test
# or
./scripts/run-tests.sh
```

**✅ Success Criteria:** All tests pass

---

### Step 10: Check CI/CD Status

**Command:**
```bash
# View recent CI runs
gh run list --limit 5

# Or check on GitHub
# https://github.com/randlee/synaptic-canvas/actions
```

**✅ Success Criteria:** Latest CI runs are passing

---

### Step 11: Verify Documentation

**Command:**
```bash
# Check documentation index is up to date
cat docs/DOCUMENTATION-INDEX.md

# Verify all links work (manual check)
```

**✅ Success Criteria:** Documentation is current and complete

---

### Step 12: Create Release Tag (if all checks pass)

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

**✅ Success Criteria:** Tag created and pushed successfully

---

### Step 13: Create GitHub Release

**Command:**
```bash
# Using GitHub CLI
gh release create "v$version" \
    --title "Synaptic Canvas v$version" \
    --notes-file docs/RELEASE-NOTES.md

# Or create manually on GitHub
# https://github.com/randlee/synaptic-canvas/releases/new
```

**✅ Success Criteria:** Release published on GitHub

---

### Step 14: Update Registry (if needed)

**Command:**
```bash
# If registry generation script exists
./scripts/generate-registry.sh

# Commit and push
git add docs/registries/nuget/registry.json
git commit -m "chore(registry): update for v$version release"
git push origin main
```

**✅ Success Criteria:** Registry updated and published

---

### Step 15: Post-Release Verification

**Command:**
```bash
# Verify tag exists
git tag -l "v$version"

# Verify release on GitHub
gh release view "v$version"

# Check registry is accessible
curl -s https://raw.githubusercontent.com/randlee/synaptic-canvas/main/docs/registries/nuget/registry.json | python3 -m json.tool | head -20
```

**✅ Success Criteria:** Release is accessible and registry is updated

---

### Pre-Release Verification Complete!

**Summary Checklist:**
- ✅ Working tree is clean
- ✅ Local branch is up to date
- ✅ All versions are consistent
- ✅ Version audit passes
- ✅ Registry validation passes
- ✅ All CHANGELOGs updated
- ✅ All manifests correct
- ✅ All READMEs present
- ✅ Tests pass
- ✅ CI/CD is green
- ✅ Documentation is current
- ✅ Release tag created
- ✅ GitHub release published
- ✅ Registry updated
- ✅ Post-release verification complete

**Next Steps:**
- Announce release
- Update documentation if needed
- Monitor for issues

---

## Post-Installation Verification

**Purpose:** Verify packages installed correctly

**Duration:** 5 minutes

**When to use:**
- After installing packages with sc-manage
- After manual package installation
- When troubleshooting installation issues

---

### Prerequisites

- Packages installed using sc-manage or manual installation
- Repository access

---

### Step 1: Verify .claude Directory Exists

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

**✅ Success Criteria:** .claude directory and subdirectories exist

---

### Step 2: Check Installed Commands

**Command:**
```bash
ls -la .claude/commands/
```

**Expected Output:**
```
delay.md  sc-git-worktree.md  sc-repomix-nuget.md  sc-manage.md
```

**✅ Success Criteria:** Expected command files are present

---

### Step 3: Check Installed Skills

**Command:**
```bash
ls -la .claude/skills/
```

**Expected Output:**
```
delaying-tasks/  managing-worktrees/  generating-nuget-context/  managing-sc-packages/
```

**✅ Success Criteria:** Expected skill directories are present

---

### Step 4: Check Installed Agents

**Command:**
```bash
ls -la .claude/agents/ | wc -l
```

**Expected Output:**
```
16 (or expected number)
```

**✅ Success Criteria:** Expected number of agent files

---

### Step 5: Verify Agent Content

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

**✅ Success Criteria:** Agent file has proper YAML frontmatter

---

### Step 6: Check Installed Scripts

**Command:**
```bash
ls -la .claude/scripts/
```

**Expected Output:**
```
delay-run.py  generate.sh  validate-registry.sh
```

**✅ Success Criteria:** Expected script files are present

---

### Step 7: Verify Script Permissions

**Command:**
```bash
ls -l .claude/scripts/*.sh
```

**Expected Output:**
```
-rwxr-xr-x  1 user  staff  1234 Dec  2 10:00 .claude/scripts/generate.sh
-rwxr-xr-x  1 user  staff  2345 Dec  2 10:00 .claude/scripts/validate-registry.sh
```

**✅ Success Criteria:** Scripts have execute permissions

---

### Step 8: Test a Sample Command

**Command:**
```bash
# Check command file is readable
cat .claude/commands/delay.md | head -30
```

**✅ Success Criteria:** Command file has proper structure

---

### Post-Installation Verification Complete!

**Summary Checklist:**
- ✅ .claude directory structure exists
- ✅ Commands installed
- ✅ Skills installed
- ✅ Agents installed
- ✅ Scripts installed
- ✅ Permissions correct
- ✅ Content verified

---

## Version Mismatch Investigation

**Purpose:** Identify and resolve version inconsistencies

**Duration:** 10-15 minutes

**When to use:**
- When audit-versions.py reports failures
- When compare-versions.py shows mismatches
- After updating package versions
- When preparing for release

---

### Prerequisites

- Repository access
- Write permissions (to fix issues)

---

### Step 1: Identify Mismatches

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

**📝 Note:** Record which artifacts have mismatches

---

### Step 2: Verify Package Manifest Version

**Command:**
```bash
# Check the package manifest
grep "^version:" packages/sc-delay-tasks/manifest.yaml
```

**Output:**
```
version: 0.4.0
```

**📝 Note:** This is the target version for all artifacts

---

### Step 3: Check Individual Artifact Versions

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

**📋 Analysis:** These artifacts need to be updated to 0.4.0

---

### Step 4: Determine Fix Strategy

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

---

### Step 5: Apply Fix (Automated Method)

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

---

### Step 6: Verify Fix

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

**✅ Success Criteria:** No mismatches reported

---

### Step 7: Run Full Audit

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

**✅ Success Criteria:** All checks pass

---

### Step 8: Commit Changes

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

**✅ Success Criteria:** Changes committed and pushed

---

### Version Mismatch Investigation Complete!

**Summary Checklist:**
- ✅ Mismatches identified
- ✅ Target version determined
- ✅ Fix strategy selected
- ✅ Changes applied
- ✅ Fix verified
- ✅ Audit passes
- ✅ Changes committed

---

## Registry Integrity Check

**Purpose:** Validate registry structure and content

**Duration:** 5 minutes

**When to use:**
- Before publishing registry
- After updating registry
- When troubleshooting registry issues
- As part of release process

---

### Prerequisites

- Registry file exists
- Python 3 installed
- Schema file available

---

### Step 1: Verify Registry File Exists

**Command:**
```bash
ls -l docs/registries/nuget/registry.json
```

**Expected Output:**
```
-rw-r--r--  1 user  staff  5673 Dec  2 09:25 docs/registries/nuget/registry.json
```

**✅ Success Criteria:** File exists and is readable

---

### Step 2: Validate JSON Syntax

**Command:**
```bash
python3 -m json.tool docs/registries/nuget/registry.json > /dev/null
```

**Expected Output:**
```
(no output - success)
```

**✅ Success Criteria:** No syntax errors

**❌ Common Issues:**

If JSON is invalid:
```
Expecting ',' delimiter: line 42 column 5 (char 1234)
```

**Fix:** Edit registry.json and fix syntax error at indicated line

---

### Step 3: Run Registry Validation

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

**✅ Success Criteria:** Status is VALID

---

### Step 4: Check Registry Version

**Command:**
```bash
python3 -c "import json; print('Registry version:', json.load(open('docs/registries/nuget/registry.json'))['version'])"
```

**Expected Output:**
```
Registry version: 0.4.0
```

**✅ Success Criteria:** Version matches marketplace version

---

### Step 5: Verify Package Count

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

**✅ Success Criteria:** Counts match

---

### Step 6: Validate Package Metadata

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

**✅ Success Criteria:** All packages have required fields

---

### Step 7: Check Registry Statistics

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

**✅ Success Criteria:** Statistics look reasonable

---

### Step 8: Validate Against Schema

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

**✅ Success Criteria:** valid is true, error_count is 0

---

### Registry Integrity Check Complete!

**Summary Checklist:**
- ✅ Registry file exists
- ✅ JSON syntax valid
- ✅ Schema validation passes
- ✅ Version correct
- ✅ Package count matches
- ✅ Metadata complete
- ✅ Statistics accurate

---

## CI/CD Validation Workflow

**Purpose:** Verify CI/CD pipeline configuration

**Duration:** 10 minutes

**When to use:**
- Setting up new CI/CD workflows
- Debugging CI failures
- After updating workflow files
- Before major releases

---

### Prerequisites

- GitHub Actions workflows configured
- Repository access
- GitHub CLI (gh) installed (optional)

---

### Step 1: Check Workflow Files Exist

**Command:**
```bash
ls -la .github/workflows/
```

**Expected Output:**
```
version-audit.yml
tests.yml
```

**✅ Success Criteria:** Workflow files present

---

### Step 2: Validate Workflow YAML Syntax

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

**✅ Success Criteria:** All workflows have valid YAML

---

### Step 3: Check Recent CI Runs

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

**✅ Success Criteria:** Recent runs are passing

---

### Step 4: Test Version Audit Locally

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

**✅ Success Criteria:** Passes locally (will likely pass in CI)

---

### Step 5: Test Registry Validation Locally

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

**✅ Success Criteria:** Valid locally

---

### Step 6: Check CI Environment

**Command:**
```bash
# View workflow file to see environment
cat .github/workflows/version-audit.yml
```

**Check for:**
- ✓ Correct runner (ubuntu-latest, macos-latest, etc.)
- ✓ Required dependencies installed
- ✓ Correct checkout action
- ✓ Proper permissions

---

### Step 7: Trigger Manual CI Run (Optional)

**Command:**
```bash
# Using GitHub CLI
gh workflow run version-audit.yml

# Check status
gh run list --workflow=version-audit.yml --limit 1
```

**✅ Success Criteria:** Workflow runs successfully

---

### CI/CD Validation Complete!

**Summary Checklist:**
- ✅ Workflow files exist
- ✅ YAML syntax valid
- ✅ Recent runs passing
- ✅ Local tests pass
- ✅ Environment configured correctly
- ✅ Manual run successful (if tested)

---

## Dependency Resolution Workflow

**Purpose:** Verify and resolve dependency issues

**Duration:** 10-20 minutes

**When to use:**
- Setting up new development environment
- Troubleshooting installation issues
- After system updates
- Before contributing

---

### Prerequisites

- System access
- Installation permissions

---

### Step 1: Check Git Installation

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

---

### Step 2: Check Python Installation

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

---

### Step 3: Check Node.js (for sc-repomix-nuget)

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

---

### Step 4: Verify All Dependencies

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

**✅ Success Criteria:** All required dependencies present

---

### Dependency Resolution Complete!

**Summary Checklist:**
- ✅ Git installed and correct version
- ✅ Python 3 installed and correct version
- ✅ Node.js installed (if using sc-repomix-nuget)
- ✅ npm installed (if using sc-repomix-nuget)

See [DEPENDENCY-VALIDATION.md](DEPENDENCY-VALIDATION.md) for more details.

---

## Emergency Diagnostics

**Purpose:** Quick issue identification

**Duration:** 2-5 minutes

**When to use:**
- Something is broken
- Need quick status check
- Before asking for help

---

### Quick Diagnostic Commands

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

## Full System Audit

**Purpose:** Comprehensive system health check

**Duration:** 20-30 minutes

**When to use:**
- Periodic maintenance
- Before major changes
- Troubleshooting complex issues
- Documentation updates

---

### Run All Diagnostics

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

## Related Documentation

- [DIAGNOSTIC-TOOLS.md](DIAGNOSTIC-TOOLS.md) - Detailed tool reference
- [VERSION-CHECKING-GUIDE.md](VERSION-CHECKING-GUIDE.md) - Version management guide
- [DEPENDENCY-VALIDATION.md](DEPENDENCY-VALIDATION.md) - Dependency requirements
- [RELEASE-PROCESS.md](RELEASE-PROCESS.md) - Release procedures

---

**End of Diagnostic Workflow Guide**
