# Dependency Validation Guide

**Version:** 0.4.0
**Last Updated:** 2025-12-02
**Repository:** [synaptic-canvas](https://github.com/randlee/synaptic-canvas)

---

## Table of Contents

1. [Overview](#overview)
2. [Global Dependencies](#global-dependencies)
3. [Package-Specific Dependencies](#package-specific-dependencies)
4. [Dependency Verification Procedures](#dependency-verification-procedures)
5. [Dependency Installation](#dependency-installation)
6. [Dependency Conflicts](#dependency-conflicts)
7. [Continuous Validation](#continuous-validation)
8. [Platform-Specific Dependencies](#platform-specific-dependencies)

---

## Overview

Synaptic Canvas has a minimal dependency footprint designed for maximum compatibility. This guide documents all dependencies, how to validate them, and how to resolve issues.

### Dependency Philosophy

- **Minimal:** Only essential dependencies required
- **Standard:** Prefer standard tools (Git, Python, Bash)
- **Optional:** Advanced features have optional dependencies
- **Portable:** Work across macOS, Linux, and Windows (WSL)

### Dependency Hierarchy

```
Core (Required for all packages):
├─ Git >= 2.7.0
├─ Python 3 >= 3.6
└─ Bash/POSIX shell

Package-Specific (Optional):
├─ Node.js >= 18.0 (sc-repomix-nuget only)
├─ npm >= 8.0 (sc-repomix-nuget only)
└─ .NET SDK (sc-repomix-nuget, for C# projects)
```

---

## Global Dependencies

### Git

**Purpose:** Version control and repository management

**Minimum Version:** 2.7.0 (for worktree support)

**Recommended Version:** 2.30.0 or higher

**Check Installation:**
```bash
git --version
```

**Expected Output:**
```
git version 2.39.0 (or higher)
```

**Why This Version:**
- Git 2.7.0+ required for `git worktree` command
- Earlier versions don't support worktree functionality
- Used by: sc-git-worktree package, all version control operations

**Validation Command:**
```bash
# Check if Git version is sufficient
git_version=$(git --version | awk '{print $3}')
required="2.7.0"

if [[ "$(printf '%s\n' "$required" "$git_version" | sort -V | head -n1)" = "$required" ]]; then
    echo "✓ Git version OK: $git_version >= $required"
else
    echo "✗ Git version too old: $git_version < $required"
fi
```

**Test Git Worktree Support:**
```bash
# Check if worktree command exists
git worktree --help > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✓ Git worktree support available"
else
    echo "✗ Git version too old for worktree support"
fi
```

**Installation:**

**macOS:**
```bash
# Using Homebrew
brew install git

# or upgrade existing
brew upgrade git

# Verify
git --version
```

**Linux (Ubuntu/Debian):**
```bash
# Install or upgrade
sudo apt-get update
sudo apt-get install git

# or for latest version
sudo add-apt-repository ppa:git-core/ppa
sudo apt-get update
sudo apt-get install git

# Verify
git --version
```

**Linux (RHEL/CentOS/Fedora):**
```bash
# Install or upgrade
sudo yum install git

# or
sudo dnf install git

# Verify
git --version
```

**Windows:**
- Download Git for Windows from https://git-scm.com/download/win
- Or use Windows Subsystem for Linux (WSL)

---

### Python 3

**Purpose:** Running utility scripts for version management and validation

**Minimum Version:** 3.6

**Recommended Version:** 3.11 or higher

**Check Installation:**
```bash
python3 --version
```

**Expected Output:**
```
Python 3.11.5 (or higher)
```

**Why This Version:**
- Python 3.6+ has f-strings and pathlib
- Modern type hints and syntax
- Wide availability across platforms

**Used By:**
- `scripts/sync-versions.py` - Version synchronization
- `docs/registries/nuget/validate-registry.py` - Registry validation
- Various package scripts

**Validation Command:**
```bash
# Check if Python 3 version is sufficient
python_version=$(python3 --version 2>&1 | awk '{print $2}')
major=$(echo $python_version | cut -d. -f1)
minor=$(echo $python_version | cut -d. -f2)

if [[ $major -ge 3 ]] && [[ $minor -ge 6 ]]; then
    echo "✓ Python version OK: $python_version >= 3.6"
else
    echo "✗ Python version too old: $python_version < 3.6"
fi
```

**Check Required Modules:**
```bash
# Check standard library modules
python3 -c "import sys, os, re, json, pathlib, argparse, subprocess" && echo "✓ Required modules available"

# Check optional modules
python3 -c "import yaml" 2>/dev/null && echo "✓ YAML module available" || echo "⚠ YAML module not available (optional)"
python3 -c "import jsonschema" 2>/dev/null && echo "✓ jsonschema module available" || echo "⚠ jsonschema module not available (optional)"
```

**Installation:**

**macOS:**
```bash
# Using Homebrew
brew install python3

# or upgrade existing
brew upgrade python3

# Verify
python3 --version
```

**Linux (Ubuntu/Debian):**
```bash
# Install or upgrade
sudo apt-get update
sudo apt-get install python3 python3-pip

# Verify
python3 --version
```

**Linux (RHEL/CentOS/Fedora):**
```bash
# Install or upgrade
sudo yum install python3 python3-pip

# or
sudo dnf install python3 python3-pip

# Verify
python3 --version
```

**Windows:**
- Download Python from https://www.python.org/downloads/
- Or use Windows Subsystem for Linux (WSL)

**Using pyenv (Recommended for Development):**
```bash
# Install pyenv
curl https://pyenv.run | bash

# Install Python 3.11
pyenv install 3.11

# Set as global version
pyenv global 3.11

# Verify
python3 --version
```

---

### Bash/POSIX Shell

**Purpose:** Running shell scripts

**Minimum Version:** Bash 4.0 or compatible POSIX shell

**Recommended:** Bash 5.0 or higher

**Check Installation:**
```bash
bash --version
```

**Expected Output:**
```
GNU bash, version 5.2.15(1)-release (or higher)
```

**Why This Version:**
- Bash 4.0+ has associative arrays
- POSIX compatibility for maximum portability
- Standard on most Unix-like systems

**Used By:**
- `scripts/audit-versions.sh` - Version auditing
- `scripts/compare-versions.sh` - Version comparison
- Various package installation scripts

**Validation Command:**
```bash
# Check shell type
echo "Current shell: $SHELL"

# Check Bash version
bash --version | head -1

# Check if scripts can run
./scripts/audit-versions.sh --help 2>/dev/null && echo "✓ Scripts can execute" || echo "✗ Scripts cannot execute"
```

**Check POSIX Compatibility:**
```bash
# Try running script with sh
sh -c "echo 'POSIX shell available'" && echo "✓ POSIX shell works"

# Check if scripts work with sh
sh scripts/audit-versions.sh 2>&1 | grep -q "not found" && echo "⚠ Scripts may need Bash" || echo "✓ Scripts POSIX compatible"
```

**Installation:**

**macOS:**
```bash
# Bash is pre-installed, but may be old
bash --version

# Upgrade with Homebrew
brew install bash

# Verify
bash --version
```

**Linux:**
```bash
# Usually pre-installed
bash --version

# If not installed (Ubuntu/Debian)
sudo apt-get install bash

# (RHEL/CentOS/Fedora)
sudo yum install bash
```

**Windows:**
- Use Git Bash (comes with Git for Windows)
- Or use Windows Subsystem for Linux (WSL)

---

### Summary: Global Dependency Check

**Quick validation script:**

```bash
#!/bin/bash
# check-global-deps.sh - Validate all global dependencies

echo "=== Global Dependency Check ==="
echo ""

FAILED=0

# Check Git
echo "Checking Git..."
if command -v git > /dev/null 2>&1; then
    git_version=$(git --version | awk '{print $3}')
    echo "  ✓ Git installed: $git_version"

    # Check version is sufficient
    required="2.7.0"
    if [[ "$(printf '%s\n' "$required" "$git_version" | sort -V | head -n1)" = "$required" ]]; then
        echo "  ✓ Version sufficient (>= $required)"
    else
        echo "  ✗ Version too old (< $required)"
        FAILED=1
    fi
else
    echo "  ✗ Git not found"
    FAILED=1
fi
echo ""

# Check Python 3
echo "Checking Python 3..."
if command -v python3 > /dev/null 2>&1; then
    python_version=$(python3 --version 2>&1 | awk '{print $2}')
    echo "  ✓ Python 3 installed: $python_version"

    # Check version is sufficient
    major=$(echo $python_version | cut -d. -f1)
    minor=$(echo $python_version | cut -d. -f2)

    if [[ $major -ge 3 ]] && [[ $minor -ge 6 ]]; then
        echo "  ✓ Version sufficient (>= 3.6)"
    else
        echo "  ✗ Version too old (< 3.6)"
        FAILED=1
    fi
else
    echo "  ✗ Python 3 not found"
    FAILED=1
fi
echo ""

# Check Bash
echo "Checking Bash..."
if command -v bash > /dev/null 2>&1; then
    bash_version=$(bash --version | head -1 | awk '{print $4}')
    echo "  ✓ Bash installed: $bash_version"
else
    echo "  ✗ Bash not found"
    FAILED=1
fi
echo ""

if [ $FAILED -eq 0 ]; then
    echo "=== All global dependencies satisfied ==="
    exit 0
else
    echo "=== Some dependencies missing or outdated ==="
    exit 1
fi
```

**Usage:**
```bash
chmod +x check-global-deps.sh
./check-global-deps.sh
```

---

## Package-Specific Dependencies

### sc-delay-tasks

**Description:** Schedule delayed one-shot or bounded polling actions

**Required Dependencies:**
- Python 3 (>= 3.6)
- Bash or POSIX shell

**Optional Dependencies:**
- None

**Platform Requirements:**
- ✅ macOS
- ✅ Linux
- ✅ Windows (Git Bash or WSL)

**Validation:**
```bash
echo "=== sc-delay-tasks Dependencies ==="

# Check Python 3
python3 --version && echo "✓ Python 3 available" || echo "✗ Python 3 missing"

# Check bash
bash --version | head -1 && echo "✓ Bash available" || echo "✗ Bash missing"

# Test delay script
python3 packages/sc-delay-tasks/scripts/delay-run.py --help > /dev/null 2>&1 && echo "✓ delay-run.py works" || echo "✗ delay-run.py failed"
```

**Installation Test:**
```bash
# Test if package can be installed
if [[ -f "packages/sc-delay-tasks/manifest.yaml" ]]; then
    echo "✓ Package files present"

    # Check scripts are executable
    if [[ -x "packages/sc-delay-tasks/scripts/delay-run.py" ]]; then
        echo "✓ Scripts are executable"
    else
        echo "⚠ Scripts need execute permission"
        chmod +x packages/sc-delay-tasks/scripts/delay-run.py
    fi
fi
```

---

### sc-git-worktree

**Description:** Manage git worktrees with optional tracking

**Required Dependencies:**
- Git (>= 2.7.0) - **Critical for worktree support**
- Python 3 (>= 3.6)
- Bash or POSIX shell

**Optional Dependencies:**
- None

**Platform Requirements:**
- ✅ macOS
- ✅ Linux
- ✅ Windows (WSL recommended)
- ⚠️ Windows (Git Bash may have issues with worktrees)

**Platform Notes:**

**Windows:**
- Worktrees work best in WSL
- Git Bash may have path issues
- Consider using WSL 2 for full compatibility

**Validation:**
```bash
echo "=== sc-git-worktree Dependencies ==="

# Check Git version (critical)
git_version=$(git --version | awk '{print $3}')
echo "Git version: $git_version"

required="2.7.0"
if [[ "$(printf '%s\n' "$required" "$git_version" | sort -V | head -n1)" = "$required" ]]; then
    echo "✓ Git version sufficient for worktree (>= $required)"
else
    echo "✗ Git version too old for worktree (< $required)"
fi

# Test worktree command
git worktree --help > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Git worktree command available"
else
    echo "✗ Git worktree command not available (upgrade Git)"
fi

# Check Python 3
python3 --version && echo "✓ Python 3 available" || echo "✗ Python 3 missing"

# Check bash
bash --version | head -1 && echo "✓ Bash available" || echo "✗ Bash missing"
```

**Test Worktree Functionality:**
```bash
# Test if worktrees can be created (safe test)
cd /tmp
git init test-worktree-repo
cd test-worktree-repo
git commit --allow-empty -m "Initial commit"
git worktree add ../test-worktree-branch test-branch 2>&1

if [ $? -eq 0 ]; then
    echo "✓ Worktrees can be created"
    # Cleanup
    git worktree remove ../test-worktree-branch 2>/dev/null
    cd ..
    rm -rf test-worktree-repo test-worktree-branch
else
    echo "✗ Worktree creation failed"
    cd ..
    rm -rf test-worktree-repo
fi
```

---

### sc-manage

**Description:** Manage Synaptic Canvas Claude packages

**Required Dependencies:**
- Python 3 (>= 3.6)
- Git
- Bash or POSIX shell

**Optional Dependencies:**
- None

**Platform Requirements:**
- ✅ macOS
- ✅ Linux
- ✅ Windows (Git Bash or WSL)

**Validation:**
```bash
echo "=== sc-manage Dependencies ==="

# Check Python 3
python3 --version && echo "✓ Python 3 available" || echo "✗ Python 3 missing"

# Check Git
git --version && echo "✓ Git available" || echo "✗ Git missing"

# Check bash
bash --version | head -1 && echo "✓ Bash available" || echo "✗ Bash missing"

# Check network access (needed for package installation)
curl -s --connect-timeout 5 https://github.com > /dev/null
if [ $? -eq 0 ]; then
    echo "✓ Network access to GitHub"
else
    echo "⚠ Cannot reach GitHub (needed for remote packages)"
fi
```

**Test Package Management:**
```bash
# Check if package manifest is valid
if [[ -f "packages/sc-manage/manifest.yaml" ]]; then
    python3 -c "import yaml; yaml.safe_load(open('packages/sc-manage/manifest.yaml'))"
    if [ $? -eq 0 ]; then
        echo "✓ Package manifest is valid YAML"
    else
        echo "✗ Package manifest has invalid YAML"
    fi
fi
```

---

### sc-repomix-nuget

**Description:** Generate AI-optimized NuGet package context using Repomix

**Required Dependencies:**
- Node.js (>= 18.0.0) - **Critical**
- npm (>= 8.0.0) - **Critical**
- Bash or POSIX shell

**Optional Dependencies:**
- .NET SDK (for C# projects)
- Various NuGet framework support

**Platform Requirements:**
- ✅ macOS
- ✅ Linux
- ✅ Windows (WSL recommended)
- ⚠️ Windows (Git Bash may have issues with npm)

**File Encoding:**
- UTF-8 support required

**Validation:**
```bash
echo "=== sc-repomix-nuget Dependencies ==="

# Check Node.js (critical)
if command -v node > /dev/null 2>&1; then
    node_version=$(node --version | sed 's/v//')
    echo "Node.js version: $node_version"

    required="18.0.0"
    if [[ "$(printf '%s\n' "$required" "$node_version" | sort -V | head -n1)" = "$required" ]]; then
        echo "✓ Node.js version sufficient (>= $required)"
    else
        echo "✗ Node.js version too old (< $required)"
    fi
else
    echo "✗ Node.js not found"
fi

# Check npm (critical)
if command -v npm > /dev/null 2>&1; then
    npm_version=$(npm --version)
    echo "npm version: $npm_version"

    required="8.0.0"
    if [[ "$(printf '%s\n' "$required" "$npm_version" | sort -V | head -n1)" = "$required" ]]; then
        echo "✓ npm version sufficient (>= $required)"
    else
        echo "✗ npm version too old (< $required)"
    fi
else
    echo "✗ npm not found"
fi

# Check .NET SDK (optional but recommended)
if command -v dotnet > /dev/null 2>&1; then
    dotnet_version=$(dotnet --version)
    echo "✓ .NET SDK available: $dotnet_version"
else
    echo "⚠ .NET SDK not found (optional, needed for C# projects)"
fi

# Check bash
bash --version | head -1 && echo "✓ Bash available" || echo "✗ Bash missing"
```

**Test npm Functionality:**
```bash
# Check if npm can install packages
cd /tmp
mkdir npm-test
cd npm-test
npm init -y > /dev/null 2>&1
npm install lodash > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✓ npm can install packages"
    cd ..
    rm -rf npm-test
else
    echo "✗ npm package installation failed"
    cd ..
    rm -rf npm-test
fi
```

**Node.js Installation:**

**Using nvm (Recommended):**
```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Load nvm
source ~/.bashrc  # or ~/.zshrc

# Install Node.js 18
nvm install 18

# Use Node.js 18
nvm use 18

# Set as default
nvm alias default 18

# Verify
node --version
npm --version
```

**macOS (Homebrew):**
```bash
# Install Node.js
brew install node

# or install specific version
brew install node@18

# Verify
node --version
npm --version
```

**Linux (Ubuntu/Debian):**
```bash
# Using NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify
node --version
npm --version
```

**Linux (using package manager):**
```bash
# Ubuntu/Debian
sudo apt-get install nodejs npm

# RHEL/CentOS/Fedora
sudo yum install nodejs npm
# or
sudo dnf install nodejs npm

# Verify
node --version
npm --version
```

**Windows:**
- Download Node.js from https://nodejs.org/
- Or use Windows Subsystem for Linux (WSL)
- Or use nvm-windows

---

### Dependency Summary Table

| Package | Git | Python 3 | Bash | Node.js | npm | .NET SDK |
|---------|-----|----------|------|---------|-----|----------|
| **sc-delay-tasks** | ⚠️ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **sc-git-worktree** | ✅ >= 2.7.0 | ✅ | ✅ | ❌ | ❌ | ❌ |
| **sc-manage** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **sc-repomix-nuget** | ⚠️ | ⚠️ | ✅ | ✅ >= 18 | ✅ >= 8 | ⚠️ optional |

**Legend:**
- ✅ Required
- ⚠️ Optional or for specific features
- ❌ Not needed

---

## Dependency Verification Procedures

### Quick Dependency Check (All Packages)

**One-command check:**

```bash
#!/bin/bash
# quick-dep-check.sh

echo "=== Quick Dependency Check ==="
echo ""

# Core dependencies
command -v git > /dev/null 2>&1 && echo "✓ Git" || echo "✗ Git"
command -v python3 > /dev/null 2>&1 && echo "✓ Python 3" || echo "✗ Python 3"
command -v bash > /dev/null 2>&1 && echo "✓ Bash" || echo "✗ Bash"

# Optional dependencies
command -v node > /dev/null 2>&1 && echo "✓ Node.js" || echo "⚠ Node.js (optional)"
command -v npm > /dev/null 2>&1 && echo "✓ npm" || echo "⚠ npm (optional)"
command -v dotnet > /dev/null 2>&1 && echo "✓ .NET SDK" || echo "⚠ .NET SDK (optional)"

echo ""
echo "For detailed check, run: ./check-all-deps.sh"
```

---

### Comprehensive Dependency Check

**Complete validation script:**

```bash
#!/bin/bash
# check-all-deps.sh - Comprehensive dependency validation

echo "========================================"
echo "COMPREHENSIVE DEPENDENCY CHECK"
echo "========================================"
echo ""

ERRORS=0
WARNINGS=0

# ===== CORE DEPENDENCIES =====

echo "=== Core Dependencies ==="
echo ""

# Git
echo "Checking Git..."
if command -v git > /dev/null 2>&1; then
    git_version=$(git --version | awk '{print $3}')
    echo "  ✓ Git installed: $git_version"

    required="2.7.0"
    if [[ "$(printf '%s\n' "$required" "$git_version" | sort -V | head -n1)" = "$required" ]]; then
        echo "  ✓ Version sufficient (>= $required)"
    else
        echo "  ✗ Version too old (< $required)"
        ERRORS=$((ERRORS + 1))
    fi

    # Test worktree support
    git worktree --help > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "  ✓ Worktree support available"
    else
        echo "  ⚠ Worktree support not available"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo "  ✗ Git not found"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Python 3
echo "Checking Python 3..."
if command -v python3 > /dev/null 2>&1; then
    python_version=$(python3 --version 2>&1 | awk '{print $2}')
    echo "  ✓ Python 3 installed: $python_version"

    major=$(echo $python_version | cut -d. -f1)
    minor=$(echo $python_version | cut -d. -f2)

    if [[ $major -ge 3 ]] && [[ $minor -ge 6 ]]; then
        echo "  ✓ Version sufficient (>= 3.6)"
    else
        echo "  ✗ Version too old (< 3.6)"
        ERRORS=$((ERRORS + 1))
    fi

    # Test standard library modules
    python3 -c "import sys, os, re, json, pathlib, argparse, subprocess" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "  ✓ Required modules available"
    else
        echo "  ✗ Some required modules missing"
        ERRORS=$((ERRORS + 1))
    fi

    # Test optional modules
    python3 -c "import yaml" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "  ✓ YAML module available"
    else
        echo "  ⚠ YAML module not available (optional)"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo "  ✗ Python 3 not found"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Bash
echo "Checking Bash..."
if command -v bash > /dev/null 2>&1; then
    bash_version=$(bash --version | head -1 | awk '{print $4}')
    echo "  ✓ Bash installed: $bash_version"

    # Test if scripts can execute
    if [[ -f "scripts/audit-versions.sh" ]]; then
        bash scripts/audit-versions.sh --help > /dev/null 2>&1
        if [ $? -ne 127 ]; then
            echo "  ✓ Scripts can execute"
        else
            echo "  ✗ Scripts cannot execute"
            ERRORS=$((ERRORS + 1))
        fi
    fi
else
    echo "  ✗ Bash not found"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# ===== OPTIONAL DEPENDENCIES =====

echo "=== Optional Dependencies ==="
echo ""

# Node.js (for sc-repomix-nuget)
echo "Checking Node.js (optional, for sc-repomix-nuget)..."
if command -v node > /dev/null 2>&1; then
    node_version=$(node --version | sed 's/v//')
    echo "  ✓ Node.js installed: $node_version"

    required="18.0.0"
    if [[ "$(printf '%s\n' "$required" "$node_version" | sort -V | head -n1)" = "$required" ]]; then
        echo "  ✓ Version sufficient (>= $required)"
    else
        echo "  ⚠ Version older than recommended (< $required)"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo "  ⚠ Node.js not found (optional, needed for sc-repomix-nuget)"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# npm (for sc-repomix-nuget)
echo "Checking npm (optional, for sc-repomix-nuget)..."
if command -v npm > /dev/null 2>&1; then
    npm_version=$(npm --version)
    echo "  ✓ npm installed: $npm_version"

    required="8.0.0"
    if [[ "$(printf '%s\n' "$required" "$npm_version" | sort -V | head -n1)" = "$required" ]]; then
        echo "  ✓ Version sufficient (>= $required)"
    else
        echo "  ⚠ Version older than recommended (< $required)"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo "  ⚠ npm not found (optional, needed for sc-repomix-nuget)"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# .NET SDK (for C# projects with sc-repomix-nuget)
echo "Checking .NET SDK (optional, for C# projects)..."
if command -v dotnet > /dev/null 2>&1; then
    dotnet_version=$(dotnet --version)
    echo "  ✓ .NET SDK installed: $dotnet_version"
else
    echo "  ⚠ .NET SDK not found (optional, needed for C# projects)"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# ===== SUMMARY =====

echo "========================================"
echo "SUMMARY"
echo "========================================"
echo ""
echo "Errors: $ERRORS"
echo "Warnings: $WARNINGS"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo "✓ All required dependencies satisfied"
    if [ $WARNINGS -gt 0 ]; then
        echo "⚠ Some optional dependencies missing"
        echo ""
        echo "Optional dependencies can be installed later if needed."
    fi
    exit 0
else
    echo "✗ Some required dependencies missing or outdated"
    echo ""
    echo "Please install missing dependencies and try again."
    exit 1
fi
```

**Usage:**
```bash
chmod +x check-all-deps.sh
./check-all-deps.sh
```

---

### Per-Package Dependency Checking

**Check dependencies for specific package:**

```bash
#!/bin/bash
# check-package-deps.sh - Check dependencies for specific package

package="$1"

if [ -z "$package" ]; then
    echo "Usage: $0 PACKAGE_NAME"
    echo "Example: $0 sc-delay-tasks"
    exit 1
fi

if [[ ! -d "packages/$package" ]]; then
    echo "Error: Package not found: $package"
    exit 1
fi

echo "=== Checking Dependencies for $package ==="
echo ""

# Read manifest
manifest="packages/$package/manifest.yaml"

if [[ ! -f "$manifest" ]]; then
    echo "Error: Manifest not found: $manifest"
    exit 1
fi

# Extract requirements
echo "Requirements from manifest:"
grep -A 10 "^requires:" "$manifest" | grep "^  - " | sed 's/^  - /  /'
echo ""

# Validate based on package
case "$package" in
    "sc-delay-tasks")
        echo "Checking sc-delay-tasks dependencies..."
        python3 --version && echo "  ✓ Python 3" || echo "  ✗ Python 3"
        bash --version | head -1 && echo "  ✓ Bash" || echo "  ✗ Bash"
        ;;

    "sc-git-worktree")
        echo "Checking sc-git-worktree dependencies..."
        git_version=$(git --version | awk '{print $3}')
        if [[ "$(printf '%s\n' "2.7.0" "$git_version" | sort -V | head -n1)" = "2.7.0" ]]; then
            echo "  ✓ Git >= 2.7.0"
        else
            echo "  ✗ Git >= 2.7.0 (found $git_version)"
        fi
        python3 --version && echo "  ✓ Python 3" || echo "  ✗ Python 3"
        bash --version | head -1 && echo "  ✓ Bash" || echo "  ✗ Bash"
        ;;

    "sc-manage")
        echo "Checking sc-manage dependencies..."
        python3 --version && echo "  ✓ Python 3" || echo "  ✗ Python 3"
        git --version && echo "  ✓ Git" || echo "  ✗ Git"
        bash --version | head -1 && echo "  ✓ Bash" || echo "  ✗ Bash"
        ;;

    "sc-repomix-nuget")
        echo "Checking sc-repomix-nuget dependencies..."
        node_version=$(node --version 2>/dev/null | sed 's/v//')
        if [[ -n "$node_version" ]] && [[ "$(printf '%s\n' "18.0.0" "$node_version" | sort -V | head -n1)" = "18.0.0" ]]; then
            echo "  ✓ Node.js >= 18"
        else
            echo "  ✗ Node.js >= 18 (found ${node_version:-not installed})"
        fi
        npm --version && echo "  ✓ npm" || echo "  ✗ npm"
        bash --version | head -1 && echo "  ✓ Bash" || echo "  ✗ Bash"
        dotnet --version && echo "  ✓ .NET SDK (optional)" || echo "  ⚠ .NET SDK not found (optional)"
        ;;

    *)
        echo "Unknown package: $package"
        ;;
esac
```

**Usage:**
```bash
chmod +x check-package-deps.sh
./check-package-deps.sh sc-delay-tasks
./check-package-deps.sh sc-git-worktree
./check-package-deps.sh sc-repomix-nuget
```

---

## Dependency Installation

### Installing Missing Dependencies

**macOS (Homebrew):**

```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install core dependencies
brew install git python3 bash

# Install optional dependencies
brew install node

# Verify
git --version
python3 --version
bash --version
node --version
npm --version
```

**Linux (Ubuntu/Debian):**

```bash
# Update package list
sudo apt-get update

# Install core dependencies
sudo apt-get install -y git python3 python3-pip bash

# Install optional dependencies
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify
git --version
python3 --version
bash --version
node --version
npm --version
```

**Linux (RHEL/CentOS/Fedora):**

```bash
# Install core dependencies
sudo yum install -y git python3 python3-pip bash
# or
sudo dnf install -y git python3 python3-pip bash

# Install optional dependencies
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs
# or
sudo dnf install -y nodejs

# Verify
git --version
python3 --version
bash --version
node --version
npm --version
```

**Windows:**

1. **Git:**
   - Download from https://git-scm.com/download/win
   - Includes Git Bash

2. **Python:**
   - Download from https://python.org/downloads/
   - Check "Add Python to PATH" during installation

3. **Node.js (optional):**
   - Download from https://nodejs.org/
   - Includes npm

4. **Alternative: Use WSL**
   ```powershell
   # Install WSL 2
   wsl --install

   # Then follow Linux instructions inside WSL
   ```

---

### Version Management with nvm, pyenv, etc.

**Using nvm for Node.js:**

```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Load nvm
source ~/.bashrc  # or ~/.zshrc

# List available versions
nvm ls-remote

# Install specific version
nvm install 18

# Use version
nvm use 18

# Set default
nvm alias default 18

# Verify
node --version
```

**Using pyenv for Python:**

```bash
# Install pyenv
curl https://pyenv.run | bash

# Add to shell profile (~/.bashrc or ~/.zshrc)
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# Reload shell
source ~/.bashrc

# List available versions
pyenv install --list

# Install specific version
pyenv install 3.11

# Set global version
pyenv global 3.11

# Verify
python3 --version
```

---

### CI/CD Dependency Configuration

**GitHub Actions dependency setup:**

```yaml
# .github/workflows/tests.yml

name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Git
        run: |
          git --version
          # Git is pre-installed

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Verify Python
        run: |
          python3 --version
          pip3 --version

      - name: Set up Node.js (for sc-repomix-nuget)
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Verify Node.js
        run: |
          node --version
          npm --version

      - name: Install optional dependencies
        run: |
          pip3 install pyyaml jsonschema

      - name: Run dependency check
        run: |
          chmod +x check-all-deps.sh
          ./check-all-deps.sh

      - name: Run version audit
        run: |
          chmod +x scripts/audit-versions.sh
          ./scripts/audit-versions.sh
```

---

### Docker/Container Dependency Setup

**Dockerfile for Synaptic Canvas:**

```dockerfile
FROM ubuntu:22.04

# Install core dependencies
RUN apt-get update && apt-get install -y \
    git \
    python3 \
    python3-pip \
    bash \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (optional, for sc-repomix-nuget)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Install optional Python packages
RUN pip3 install pyyaml jsonschema

# Verify installations
RUN git --version && \
    python3 --version && \
    bash --version && \
    node --version && \
    npm --version

# Set working directory
WORKDIR /workspace

# Copy repository
COPY . /workspace

# Run dependency check
RUN chmod +x check-all-deps.sh && ./check-all-deps.sh

CMD ["/bin/bash"]
```

**Build and run:**

```bash
# Build image
docker build -t synaptic-canvas .

# Run container
docker run -it --rm -v $(pwd):/workspace synaptic-canvas

# Inside container, verify
./check-all-deps.sh
./scripts/audit-versions.sh
```

---

## Dependency Conflicts

### Identifying Conflicts

**Common conflict scenarios:**

1. **Multiple Python versions:**
   ```bash
   # Check all Python installations
   which -a python python3 python3.11

   # Verify which is used
   python3 --version
   ```

2. **Multiple Git installations:**
   ```bash
   # Check all Git installations
   which -a git

   # Verify which is used
   git --version
   ```

3. **Node.js version conflicts:**
   ```bash
   # Check all Node.js installations
   which -a node

   # Verify which is used
   node --version
   ```

---

### Resolution Strategies

**Strategy 1: Use PATH priority**

```bash
# Add preferred location to PATH
export PATH="/usr/local/bin:$PATH"

# Verify
which git
which python3
which node
```

**Strategy 2: Use version managers**

```bash
# Use pyenv for Python
pyenv global 3.11

# Use nvm for Node.js
nvm use 18

# Verify
python3 --version
node --version
```

**Strategy 3: Use absolute paths**

```bash
# Use specific Python
/usr/local/bin/python3 --version

# Use specific Git
/usr/bin/git --version

# Update scripts to use absolute paths
```

**Strategy 4: Uninstall conflicting versions**

```bash
# macOS - uninstall Homebrew version
brew uninstall python3

# or uninstall system version (not recommended)

# Linux - remove package
sudo apt-get remove python3
```

---

### Workarounds

**Python version issues:**

```bash
# Create alias
alias python3='/usr/local/bin/python3.11'

# or use virtual environment
python3 -m venv venv
source venv/bin/activate
```

**Git version issues:**

```bash
# Use newer Git from Homebrew on macOS
export PATH="/usr/local/bin:$PATH"

# or compile from source
```

**Node.js version issues:**

```bash
# Use nvm to switch versions
nvm use 18

# or create .nvmrc file
echo "18" > .nvmrc
nvm use
```

---

### Reporting Dependency Issues

**Gather information for issue reports:**

```bash
#!/bin/bash
# dependency-report.sh - Generate dependency report for issue reporting

echo "=== Synaptic Canvas Dependency Report ==="
echo ""
echo "Generated: $(date)"
echo ""

echo "=== System Information ==="
uname -a
echo ""

echo "=== Installed Dependencies ==="
echo ""

echo "Git:"
git --version
which git
echo ""

echo "Python 3:"
python3 --version
which python3
python3 -c "import sys; print(f'Path: {sys.executable}')"
echo ""

echo "Bash:"
bash --version | head -1
which bash
echo ""

echo "Node.js:"
node --version 2>/dev/null || echo "Not installed"
which node 2>/dev/null
echo ""

echo "npm:"
npm --version 2>/dev/null || echo "Not installed"
which npm 2>/dev/null
echo ""

echo "=== Python Modules ==="
python3 -c "import sys, os, re, json, pathlib, argparse, subprocess; print('Standard library: OK')" 2>/dev/null || echo "Standard library: MISSING MODULES"
python3 -c "import yaml; print('yaml: OK')" 2>/dev/null || echo "yaml: Not installed"
python3 -c "import jsonschema; print('jsonschema: OK')" 2>/dev/null || echo "jsonschema: Not installed"
echo ""

echo "=== PATH ==="
echo "$PATH" | tr ':' '\n'
echo ""

echo "=== Synaptic Canvas Version Check ==="
if [[ -f "version.yaml" ]]; then
    grep "^version:" version.yaml
else
    echo "version.yaml not found"
fi
echo ""

echo "=== End of Report ==="
```

**Usage:**
```bash
chmod +x dependency-report.sh
./dependency-report.sh > dependency-report.txt

# Attach dependency-report.txt to issue report
```

---

## Continuous Validation

### Pre-Commit Hooks for Dependencies

**Create pre-commit hook:**

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running pre-commit dependency check..."

# Check critical dependencies
if ! command -v git > /dev/null 2>&1; then
    echo "Error: Git not found"
    exit 1
fi

if ! command -v python3 > /dev/null 2>&1; then
    echo "Error: Python 3 not found"
    exit 1
fi

# Check if scripts can run
if [[ -f "scripts/audit-versions.sh" ]]; then
    ./scripts/audit-versions.sh > /dev/null
    if [ $? -ne 0 ]; then
        echo "Warning: Version audit failed"
        echo "Run './scripts/audit-versions.sh' for details"
        # Don't block commit, just warn
    fi
fi

echo "Dependency check passed"
exit 0
```

**Install hook:**
```bash
cp scripts/pre-commit-hook .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

---

### CI/CD Dependency Checks

**Add to GitHub Actions:**

```yaml
# .github/workflows/dependency-check.yml

name: Dependency Check

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  schedule:
    # Run daily at 9 AM UTC
    - cron: '0 9 * * *'

jobs:
  check-dependencies:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Run dependency check
        run: |
          chmod +x check-all-deps.sh
          ./check-all-deps.sh

      - name: Report results
        if: failure()
        uses: actions/github-script@v6
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'Dependency Check Failed',
              body: 'Dependency validation failed on ${{ matrix.os }}. Please check the workflow logs.'
            })
```

---

### Runtime Dependency Verification

**Add to package scripts:**

```bash
#!/bin/bash
# verify-deps-before-run.sh

# Check dependencies before running package functionality

package="${1:-unknown}"

echo "Verifying dependencies for $package..."

case "$package" in
    "sc-delay-tasks")
        python3 --version > /dev/null 2>&1 || { echo "Error: Python 3 required"; exit 1; }
        ;;
    "sc-git-worktree")
        git worktree --help > /dev/null 2>&1 || { echo "Error: Git >= 2.7.0 required for worktree support"; exit 1; }
        python3 --version > /dev/null 2>&1 || { echo "Error: Python 3 required"; exit 1; }
        ;;
    "sc-repomix-nuget")
        node --version > /dev/null 2>&1 || { echo "Error: Node.js >= 18 required"; exit 1; }
        npm --version > /dev/null 2>&1 || { echo "Error: npm required"; exit 1; }
        ;;
    *)
        echo "Unknown package: $package"
        exit 1
        ;;
esac

echo "✓ Dependencies satisfied for $package"
exit 0
```

---

## Platform-Specific Dependencies

### macOS

**System Requirements:**
- macOS 10.15 (Catalina) or higher recommended
- Xcode Command Line Tools (for Git)

**Install Command Line Tools:**
```bash
xcode-select --install
```

**Common Issues:**

**Issue:** System Git is outdated
```bash
# Check system Git
/usr/bin/git --version

# Install newer Git with Homebrew
brew install git

# Verify Homebrew Git is used
which git  # Should be /usr/local/bin/git
```

**Issue:** Python 2 vs Python 3
```bash
# macOS may have Python 2 as 'python'
python --version  # May be Python 2.7

# Use python3 explicitly
python3 --version  # Python 3.x
```

---

### Linux

**Distribution-Specific Notes:**

**Ubuntu/Debian:**
- Use `apt-get` or `apt`
- May need `sudo` for installations
- Git and Python usually available in default repos

**RHEL/CentOS/Fedora:**
- Use `yum` or `dnf`
- May need EPEL repository for some packages
- Node.js requires NodeSource repository

**Arch Linux:**
```bash
# Install dependencies
sudo pacman -S git python bash nodejs npm
```

**Common Issues:**

**Issue:** Old package versions in repos
```bash
# Add PPA for latest Git (Ubuntu)
sudo add-apt-repository ppa:git-core/ppa
sudo apt-get update
sudo apt-get install git

# Use NodeSource for Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install nodejs
```

---

### Windows

**Recommended Setup:**
- Use Windows Subsystem for Linux (WSL 2)
- Or use Git Bash + native Windows tools

**WSL 2 Setup:**
```powershell
# Install WSL 2
wsl --install

# Update to WSL 2
wsl --set-default-version 2

# Install Ubuntu
wsl --install -d Ubuntu

# Then follow Linux instructions inside WSL
```

**Git Bash Setup:**
- Download Git for Windows: https://git-scm.com/download/win
- Includes Git Bash, which provides Unix-like environment
- Install Python and Node.js separately

**Common Issues:**

**Issue:** Path separators (\ vs /)
- Git Bash uses Unix-style paths (/)
- Windows native uses backslashes (\)
- Git Bash handles conversion automatically

**Issue:** Line endings (CRLF vs LF)
```bash
# Configure Git to handle line endings
git config --global core.autocrlf true  # Windows
git config --global core.autocrlf input  # macOS/Linux
```

**Issue:** Worktrees in Git Bash
- Worktrees may have issues with Git Bash on Windows
- WSL 2 is strongly recommended for worktree functionality

---

## Related Documentation

- [DIAGNOSTIC-TOOLS.md](DIAGNOSTIC-TOOLS.md) - Diagnostic tools reference
- [DIAGNOSTIC-WORKFLOW.md](DIAGNOSTIC-WORKFLOW.md) - Step-by-step workflows
- [VERSION-CHECKING-GUIDE.md](VERSION-CHECKING-GUIDE.md) - Version verification
- [versioning-strategy.md](versioning-strategy.md) - Versioning policy

---

## Quick Reference

### Dependency Check Commands

```bash
# Quick check
git --version && python3 --version && bash --version

# Comprehensive check
./check-all-deps.sh

# Per-package check
./check-package-deps.sh PACKAGE_NAME

# Generate report
./dependency-report.sh > report.txt
```

### Installation Commands

```bash
# macOS (Homebrew)
brew install git python3 node

# Linux (Ubuntu/Debian)
sudo apt-get install git python3 nodejs npm

# Linux (RHEL/CentOS)
sudo yum install git python3 nodejs npm
```

---

**End of Dependency Validation Guide**
